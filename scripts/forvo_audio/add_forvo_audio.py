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
import sys
from pathlib import Path

# Support direct script execution (`python scripts/forvo_audio/add_forvo_audio.py`).
if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parent))

from audio_paths import normalize_audio_path, resolve_audio_path
from audio_queries import extract_query, extract_row_query
from forvo_download import (
    download_audio_map,
    scrape_query,
)
from pending_words import (
    PENDING_TARGET_COLUMN,
    append_pending_rows_to_vocab,
    read_pending_rows,
    write_pending_rows,
)
from vocab_tsv import (
    AUDIO_COLUMN,
    build_audio_map_from_vocab,
    build_query_set,
    ensure_audio_column,
    iter_vocab_files,
    read_rows,
    update_tsv,
)

NULL_AUDIO = "null"


def _pending_target_paths(pending_rows: list[dict[str, str]], *, base_dir: Path) -> list[Path]:
    targets: set[Path] = set()
    for row in pending_rows:
        target_ref = row.get(PENDING_TARGET_COLUMN, "").strip()
        if not target_ref:
            continue
        target = Path(target_ref)
        targets.add(target if target.is_absolute() else base_dir / target)
    return sorted(targets)


def _verify_pending_rows(
    pending_rows: list[dict[str, str]],
    *,
    base_dir: Path,
    expected_count_by_target: dict[Path, int],
) -> bool:
    for target, expected in expected_count_by_target.items():
        _fieldnames, rows = read_rows(target)
        actual_tail = rows[-expected:] if expected else []
        if len(actual_tail) != expected:
            print(f"verify failed: {target} expected {expected} appended rows, got {len(actual_tail)}")
            return False

    if not pending_rows:
        return True

    for row in pending_rows:
        audio_value = row.get(AUDIO_COLUMN, "").strip()
        if not audio_value:
            print(f"verify failed: missing {AUDIO_COLUMN} value in pending rows")
            return False
        if audio_value == NULL_AUDIO:
            continue
        resolved = resolve_audio_path(audio_value, base_dir=base_dir)
        if not resolved.exists():
            print(f"verify failed: missing audio file {audio_value}")
            return False
    return True


def _run_pending_workflow(args: argparse.Namespace, *, base_dir: Path) -> int:
    pending_file = Path(args.pending_file)
    pending_rows = read_pending_rows(pending_file)
    if not pending_rows:
        print(f"No pending rows in {pending_file}")
        return 1

    target_paths = _pending_target_paths(pending_rows, base_dir=base_dir)
    existing_targets = [path for path in target_paths if path.exists()]

    existing_map = build_audio_map_from_vocab(existing_targets, base_dir=base_dir)
    queries = {query for row in pending_rows if (query := extract_row_query(row))}
    print(f"Pending rows: {len(pending_rows)}")
    print(f"Unique queries: {len(queries)}")
    if not queries:
        print("No audio-eligible queries in pending rows. All staged rows will use audio_file=null.")

    workers = max(1, args.workers)
    if args.headed and workers > 1:
        print("Headed mode requires workers=1 to avoid Playwright popup contention. Using workers=1.")
        workers = 1

    audio_map = download_audio_map(
        queries=queries,
        temp_dir=Path(args.temp_dir),
        audio_dir=Path(args.audio_dir),
        headed=args.headed,
        workers=workers,
        base_dir=base_dir,
        query_timeout_sec=args.query_timeout_sec,
        initial_map=existing_map,
    )
    print(f"Resolved audio for {len(audio_map)} queries")

    for row in pending_rows:
        query = extract_row_query(row)
        resolved_audio = audio_map.get(query.casefold(), "") if query else ""
        row[AUDIO_COLUMN] = resolved_audio if resolved_audio else NULL_AUDIO

    write_pending_rows(pending_file, pending_rows)
    appended_counts = append_pending_rows_to_vocab(pending_rows, base_dir=base_dir)
    for path, count in sorted(appended_counts.items()):
        print(f"updated {path}: appended={count}")

    ok = _verify_pending_rows(
        pending_rows,
        base_dir=base_dir,
        expected_count_by_target=appended_counts,
    )
    if not ok:
        print("Verification failed.")
        return 1

    print("Done. Pending workflow completed and verified.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vocab-glob", default="vocab/*.tsv")
    parser.add_argument("--pending-file", help="TSV containing rows to append, with a target_tsv column")
    parser.add_argument("--temp-dir", default="forvo_mp3")
    parser.add_argument("--audio-dir", default="audio/forvo_no")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--query-timeout-sec", type=int, default=60)
    parser.set_defaults(headed=None)
    parser.add_argument("--headed", dest="headed", action="store_true")
    parser.add_argument("--no-headed", dest="headed", action="store_false")
    args = parser.parse_args()

    base_dir = Path.cwd()
    if args.headed is None:
        # Pending flow defaults to visible browser for interactive Forvo scraping.
        args.headed = bool(args.pending_file)

    if args.pending_file:
        return _run_pending_workflow(args, base_dir=base_dir)

    vocab_paths = iter_vocab_files(args.vocab_glob)
    if not vocab_paths:
        print("No vocab files found.")
        return 1

    queries = build_query_set(vocab_paths)
    print(f"Unique queries: {len(queries)}")

    existing_map = build_audio_map_from_vocab(vocab_paths, base_dir=base_dir)
    workers = max(1, args.workers)
    if args.headed and workers > 1:
        print("Headed mode requires workers=1 to avoid Playwright popup contention. Using workers=1.")
        workers = 1

    audio_map = download_audio_map(
        queries=queries,
        temp_dir=Path(args.temp_dir),
        audio_dir=Path(args.audio_dir),
        headed=args.headed,
        workers=workers,
        base_dir=base_dir,
        query_timeout_sec=args.query_timeout_sec,
        initial_map=existing_map,
    )
    print(f"Resolved audio for {len(audio_map)} queries")

    total_filled = 0
    total_empty = 0
    for path in vocab_paths:
        filled, empty = update_tsv(path, audio_map)
        total_filled += filled
        total_empty += empty
        print(f"updated {path}: filled={filled} empty={empty}")

    print(f"Done. Total rows with audio: {total_filled}, without audio: {total_empty}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
