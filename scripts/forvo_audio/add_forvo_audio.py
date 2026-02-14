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
from vocab_tsv import (
    AUDIO_COLUMN,
    build_audio_map_from_vocab,
    build_query_set,
    ensure_audio_column,
    iter_vocab_files,
    read_rows,
    update_tsv,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vocab-glob", default="vocab/*.tsv")
    parser.add_argument("--temp-dir", default="forvo_mp3")
    parser.add_argument("--audio-dir", default="audio/forvo_no")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--headed", action="store_true", default=False)
    args = parser.parse_args()

    base_dir = Path.cwd()
    vocab_paths = iter_vocab_files(args.vocab_glob)
    if not vocab_paths:
        print("No vocab files found.")
        return 1

    queries = build_query_set(vocab_paths)
    print(f"Unique queries: {len(queries)}")

    existing_map = build_audio_map_from_vocab(vocab_paths, base_dir=base_dir)
    audio_map = download_audio_map(
        queries=queries,
        temp_dir=Path(args.temp_dir),
        audio_dir=Path(args.audio_dir),
        headed=args.headed,
        workers=args.workers,
        base_dir=base_dir,
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
