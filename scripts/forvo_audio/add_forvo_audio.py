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

from workflows.pending_audio import (
    resolve_headed_mode as _resolve_headed_mode,
    run_pending_workflow as _run_pending_workflow,
)
from core.forvo_download import download_audio_map


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pending-file", required=True, help="TSV containing rows to append, with a target_tsv column")
    parser.add_argument("--temp-dir", default="forvo_mp3")
    parser.add_argument("--audio-dir", default="docs/assets/audio/forvo_no")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--query-timeout-sec", type=int, default=60)
    parser.set_defaults(headed=None)
    # parser.add_argument("--headed", dest="headed", action="store_true")
    # parser.add_argument("--no-headed", dest="headed", action="store_false")
    args = parser.parse_args()

    base_dir = Path.cwd()
    # args.headed = _resolve_headed_mode(args)
    return _run_pending_workflow(args, base_dir=base_dir, download_audio_map_fn=download_audio_map)


if __name__ == "__main__":
    raise SystemExit(main())
