from __future__ import annotations

import csv
from pathlib import Path

from audio_paths import normalize_audio_path, resolve_audio_path
from audio_queries import extract_row_query

AUDIO_COLUMN = "audio_file"
VOCAB_FIELDS = [
    "lexical-category",
    "english",
    "norwegian",
    "pronunciation",
    "example_sentence",
    AUDIO_COLUMN,
]
NULL_AUDIO = ""
LEGACY_NULL_AUDIO = "null"
NO_AUDIO_VALUES = {NULL_AUDIO.casefold(), LEGACY_NULL_AUDIO.casefold()}


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"Missing header in {path}")
        return list(reader.fieldnames), list(reader)


def ensure_audio_column(fieldnames: list[str]) -> list[str]:
    if AUDIO_COLUMN not in fieldnames:
        return [*fieldnames, AUDIO_COLUMN]
    return fieldnames


def build_audio_map_from_vocab(vocab_paths: list[Path], *, base_dir: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for path in vocab_paths:
        _, rows = read_rows(path)
        for row in rows:
            query = extract_row_query(row)
            audio_path_ref = row.get(AUDIO_COLUMN, "").strip()
            if not query or not audio_path_ref:
                continue
            if audio_path_ref.casefold() in NO_AUDIO_VALUES:
                continue

            resolved_path = resolve_audio_path(audio_path_ref, base_dir=base_dir)
            if not resolved_path.exists():
                continue

            mapping.setdefault(
                query.casefold(),
                normalize_audio_path(resolved_path, base_dir=base_dir),
            )
    return mapping
