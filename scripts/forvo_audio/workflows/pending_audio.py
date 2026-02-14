from __future__ import annotations

import argparse
from pathlib import Path
from typing import Callable

from core.audio_paths import resolve_audio_path
from core.audio_queries import extract_row_query
from core.pending_words import (
    PENDING_TARGET_COLUMN,
    append_pending_rows_to_vocab,
    read_pending_rows,
    resolve_pending_target,
    write_pending_rows,
)
from core.vocab_tsv import (
    AUDIO_COLUMN,
    LEGACY_NULL_AUDIO,
    build_audio_map_from_vocab,
    read_rows,
)


def resolve_headed_mode(args: argparse.Namespace) -> bool:
    if args.headed is not None:
        return args.headed
    # Pending flow defaults to visible browser for interactive Forvo scraping.
    return True


def effective_workers(*, workers: int, headed: bool) -> int:
    normalized = max(1, workers)
    if headed and normalized > 1:
        print("Headed mode requires workers=1 to avoid Playwright popup contention. Using workers=1.")
        return 1
    return normalized


def pending_target_paths(pending_rows: list[dict[str, str]], *, base_dir: Path) -> list[Path]:
    targets: set[Path] = set()
    for row in pending_rows:
        target_ref = row.get(PENDING_TARGET_COLUMN, "").strip()
        if not target_ref:
            continue
        targets.add(resolve_pending_target(target_ref, base_dir=base_dir))
    return sorted(targets)


def verify_pending_rows(
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
        if audio_value == LEGACY_NULL_AUDIO:
            continue
        resolved = resolve_audio_path(audio_value, base_dir=base_dir)
        if not resolved.exists():
            print(f"verify failed: missing audio file {audio_value}")
            return False
    return True


def run_pending_workflow(
    args: argparse.Namespace,
    *,
    base_dir: Path,
    download_audio_map_fn: Callable[..., dict[str, str]],
) -> int:
    pending_file = Path(args.pending_file)
    pending_rows = read_pending_rows(pending_file)
    if not pending_rows:
        print(f"No pending rows in {pending_file}")
        return 1

    target_paths = pending_target_paths(pending_rows, base_dir=base_dir)
    existing_targets = [path for path in target_paths if path.exists()]

    existing_map = build_audio_map_from_vocab(existing_targets, base_dir=base_dir)
    queries = {query for row in pending_rows if (query := extract_row_query(row))}
    print(f"Pending rows: {len(pending_rows)}")
    print(f"Unique queries: {len(queries)}")
    if not queries:
        print("No audio-eligible queries in pending rows. All staged rows will use audio_file=null.")

    audio_map = download_audio_map_fn(
        queries=queries,
        temp_dir=Path(args.temp_dir),
        audio_dir=Path(args.audio_dir),
        headed=args.headed,
        workers=effective_workers(workers=args.workers, headed=args.headed),
        base_dir=base_dir,
        query_timeout_sec=args.query_timeout_sec,
        initial_map=existing_map,
    )
    print(f"Resolved audio for {len(audio_map)} queries")

    for row in pending_rows:
        query = extract_row_query(row)
        resolved_audio = audio_map.get(query.casefold(), "") if query else ""
        row[AUDIO_COLUMN] = resolved_audio if resolved_audio else LEGACY_NULL_AUDIO

    write_pending_rows(pending_file, pending_rows)
    appended_counts = append_pending_rows_to_vocab(pending_rows, base_dir=base_dir)
    for path, count in sorted(appended_counts.items()):
        print(f"updated {path}: appended={count}")

    ok = verify_pending_rows(
        pending_rows,
        base_dir=base_dir,
        expected_count_by_target=appended_counts,
    )
    if not ok:
        print("Verification failed.")
        return 1

    print("Done. Pending workflow completed and verified.")
    return 0
