#!/usr/bin/env python3
"""Download Norwegian audio from Forvo and update vocab TSV files.

Rules:
- noun: remove leading article en/ei/et
- verb: use infinitive only (first comma segment, strip leading "å ")
- adjective/adverb: use value as-is
- expression: skip
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import re
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from scrape_forvo import scrape

AUDIO_COLUMN = "audio_file"
SUPPORTED = {"noun", "verb", "adjective", "adverb"}
SKIP = {"expression"}


@dataclass
class RowWork:
    category: str
    norwegian: str
    query: str | None


def extract_query(category: str, norwegian: str) -> str | None:
    c = category.strip().lower()
    n = norwegian.strip()
    if not n or c in SKIP:
        return None
    if c not in SUPPORTED:
        return None

    if c == "noun":
        # Keep the lexical noun without the article prefix.
        n = re.sub(r"^(en|ei|et)\s+", "", n, flags=re.IGNORECASE)
        return n.strip() or None

    if c == "verb":
        # Input shape: "å ta, tar, tok, har tatt" -> "ta"
        head = n.split(",", 1)[0].strip()
        head = re.sub(r"^å\s+", "", head, flags=re.IGNORECASE)
        return head.strip() or None

    # adjective/adverb
    return n


def iter_vocab_files(pattern: str) -> list[Path]:
    return sorted(Path(p) for p in glob.glob(pattern))


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"Missing header in {path}")
        rows = list(reader)
        return list(reader.fieldnames), rows


def ensure_audio_column(fieldnames: list[str]) -> list[str]:
    if AUDIO_COLUMN not in fieldnames:
        return [*fieldnames, AUDIO_COLUMN]
    return fieldnames


def build_query_set(vocab_paths: list[Path]) -> set[str]:
    queries: set[str] = set()
    for path in vocab_paths:
        _, rows = read_rows(path)
        for row in rows:
            q = extract_query(row.get("lexical-category", ""), row.get("norwegian", ""))
            if q:
                queries.add(q)
    return queries


def scrape_query(query: str, temp_dir: Path, headed: bool) -> Path | None:
    result = scrape(
        query,
        outdir=str(temp_dir),
        limit=1,
        no_head=True,
        lang="no",
        use_playwright=True,
        headed=headed,
    )
    if result.downloaded_count <= 0:
        return None

    candidates = [c for c in result.candidates if c.out_path]
    if not candidates:
        return None

    out = Path(candidates[0].out_path)
    return out if out.exists() else None


def load_json(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    if not isinstance(data, dict):
        return {}
    out: dict[str, str] = {}
    for k, v in data.items():
        if isinstance(k, str) and isinstance(v, str):
            out[k] = v
    return out


def save_json(path: Path, data: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(sorted(data.items())), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def hydrate_from_existing_files(audio_dir: Path, mapping: dict[str, str]) -> None:
    # Parse labels from filenames like no_butikk_623378_001.mp3 for resume support.
    pat = re.compile(r"^no_(.+)_\d+_\d{3}\.mp3$")
    for p in sorted(audio_dir.glob("no_*.mp3")):
        m = pat.match(p.name)
        if not m:
            continue
        label = m.group(1).replace("_", " ").strip().casefold()
        if label and label not in mapping:
            mapping[label] = p.as_posix()


def download_audio_map(
    queries: set[str],
    temp_dir: Path,
    audio_dir: Path,
    headed: bool,
    cache_path: Path,
    workers: int,
) -> dict[str, str]:
    temp_dir.mkdir(parents=True, exist_ok=True)
    audio_dir.mkdir(parents=True, exist_ok=True)

    mapping: dict[str, str] = load_json(cache_path)
    hydrate_from_existing_files(audio_dir, mapping)
    query_list = sorted(queries)
    total = len(query_list)
    for idx, query in enumerate(query_list, start=1):
        qkey = query.casefold()
        existing = mapping.get(qkey)
        if existing and Path(existing).exists():
            print(f"[{idx}/{total}] reuse: {query} -> {existing}")
        elif qkey in mapping and not existing:
            print(f"[{idx}/{total}] reuse-miss: {query}")
        else:
            break
    else:
        return mapping

    pending = []
    for idx, query in enumerate(query_list, start=1):
        qkey = query.casefold()
        existing = mapping.get(qkey)
        if existing and Path(existing).exists():
            continue
        if qkey in mapping and not existing:
            continue
        pending.append((idx, query))

    def run_one(query: str) -> tuple[str, Path | None, str | None]:
        try:
            downloaded = scrape_query(query, temp_dir=temp_dir, headed=headed)
            return query, downloaded, None
        except Exception as exc:  # noqa: BLE001
            return query, None, str(exc)

    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = {executor.submit(run_one, query): (idx, query) for idx, query in pending}
        for future in as_completed(futures):
            idx, query = futures[future]
            qkey = query.casefold()
            query, downloaded, err = future.result()
            if err:
                print(f"[{idx}/{total}] failed: {query}: {err}")
                mapping[qkey] = ""
                save_json(cache_path, mapping)
                continue

            if not downloaded:
                print(f"[{idx}/{total}] no-download: {query}")
                mapping[qkey] = ""
                save_json(cache_path, mapping)
                continue

            target = audio_dir / downloaded.name
            if target.resolve() != downloaded.resolve():
                shutil.move(str(downloaded), str(target))
            mapping[qkey] = str(target.as_posix())
            print(f"[{idx}/{total}] saved: {query} -> {mapping[qkey]}")
            save_json(cache_path, mapping)

    return mapping


def update_tsv(path: Path, audio_map: dict[str, str]) -> tuple[int, int]:
    fieldnames, rows = read_rows(path)
    out_fields = ensure_audio_column(fieldnames)

    filled = 0
    skipped = 0
    for row in rows:
        query = extract_query(row.get("lexical-category", ""), row.get("norwegian", ""))
        row[AUDIO_COLUMN] = audio_map.get(query.casefold(), "") if query else ""
        if row[AUDIO_COLUMN]:
            filled += 1
        else:
            skipped += 1

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)

    return filled, skipped


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vocab-glob", default="vocab/*.tsv")
    parser.add_argument("--temp-dir", default="forvo_mp3")
    parser.add_argument("--audio-dir", default="audio/forvo_no")
    parser.add_argument("--cache-file", default="scripts/forvo_audio/audio_index.json")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--headed", action="store_true", default=False)
    args = parser.parse_args()

    vocab_paths = iter_vocab_files(args.vocab_glob)
    if not vocab_paths:
        print("No vocab files found.")
        return 1

    queries = build_query_set(vocab_paths)
    print(f"Unique queries: {len(queries)}")

    audio_map = download_audio_map(
        queries=queries,
        temp_dir=Path(args.temp_dir),
        audio_dir=Path(args.audio_dir),
        headed=args.headed,
        cache_path=Path(args.cache_file),
        workers=args.workers,
    )
    print(f"Downloaded audio for {len(audio_map)} queries")

    total_filled = 0
    total_skipped = 0
    for path in vocab_paths:
        filled, skipped = update_tsv(path, audio_map)
        total_filled += filled
        total_skipped += skipped
        print(f"updated {path}: filled={filled} empty={skipped}")

    print(f"Done. Total rows with audio: {total_filled}, without audio: {total_skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
