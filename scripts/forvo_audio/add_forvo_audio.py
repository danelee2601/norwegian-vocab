#!/usr/bin/env python3
"""Download Norwegian audio from Forvo for pending rows and append to vocab TSV files.

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

from audio_paths import resolve_audio_path
from audio_queries import extract_row_query
from forvo_download import (
    download_audio_map,
)
from pending_words import (
    PENDING_TARGET_COLUMN,
    append_pending_rows_to_vocab,
    read_pending_rows,
    resolve_pending_target,
    write_pending_rows,
)
from vocab_tsv import (
    AUDIO_COLUMN,
    build_audio_map_from_vocab,
    read_rows,
)

NULL_AUDIO = "null"


def _resolve_headed_mode(args: argparse.Namespace) -> bool:
    if args.headed is not None:
        return args.headed
    # Pending flow defaults to visible browser for interactive Forvo scraping.
    return True


def _effective_workers(*, workers: int, headed: bool) -> int:
    normalized = max(1, workers)
    if headed and normalized > 1:
        print("Headed mode requires workers=1 to avoid Playwright popup contention. Using workers=1.")
        return 1
    return normalized


def _pending_target_paths(pending_rows: list[dict[str, str]], *, base_dir: Path) -> list[Path]:
    targets: set[Path] = set()
    for row in pending_rows:
        target_ref = row.get(PENDING_TARGET_COLUMN, "").strip()
        if not target_ref:
            continue
        targets.add(resolve_pending_target(target_ref, base_dir=base_dir))
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

    audio_map = download_audio_map(
        queries=queries,
        temp_dir=Path(args.temp_dir),
        audio_dir=Path(args.audio_dir),
        headed=args.headed,
        workers=_effective_workers(workers=args.workers, headed=args.headed),
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
    parser.add_argument("--pending-file", required=True, help="TSV containing rows to append, with a target_tsv column")
    parser.add_argument("--temp-dir", default="forvo_mp3")
    parser.add_argument("--audio-dir", default="audio/forvo_no")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--query-timeout-sec", type=int, default=60)
    parser.set_defaults(headed=None)
    parser.add_argument("--headed", dest="headed", action="store_true")
    parser.add_argument("--no-headed", dest="headed", action="store_false")
    args = parser.parse_args()

    base_dir = Path.cwd()
    args.headed = _resolve_headed_mode(args)
    return _run_pending_workflow(args, base_dir=base_dir)


if __name__ == "__main__":
    raise SystemExit(main())
