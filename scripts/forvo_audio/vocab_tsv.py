from __future__ import annotations

import csv
import glob
from pathlib import Path

from audio_paths import normalize_audio_path, resolve_audio_path
from audio_queries import extract_row_query

AUDIO_COLUMN = "audio_file"
NULL_AUDIO = "null"


def iter_vocab_files(pattern: str) -> list[Path]:
    return sorted(Path(p) for p in glob.glob(pattern))


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


def build_query_set(vocab_paths: list[Path]) -> set[str]:
    queries: set[str] = set()
    for path in vocab_paths:
        _, rows = read_rows(path)
        for row in rows:
            query = extract_row_query(row)
            if query:
                queries.add(query)
    return queries


def build_audio_map_from_vocab(vocab_paths: list[Path], *, base_dir: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for path in vocab_paths:
        _, rows = read_rows(path)
        for row in rows:
            query = extract_row_query(row)
            audio_path_ref = row.get(AUDIO_COLUMN, "").strip()
            if not query or not audio_path_ref or audio_path_ref.casefold() == NULL_AUDIO:
                continue

            resolved_path = resolve_audio_path(audio_path_ref, base_dir=base_dir)
            if not resolved_path.exists():
                continue

            mapping.setdefault(
                query.casefold(),
                normalize_audio_path(resolved_path, base_dir=base_dir),
            )
    return mapping


def update_tsv(path: Path, audio_map: dict[str, str]) -> tuple[int, int]:
    fieldnames, rows = read_rows(path)
    out_fields = ensure_audio_column(fieldnames)

    filled = 0
    empty = 0
    for row in rows:
        query = extract_row_query(row)
        resolved_audio = audio_map.get(query.casefold(), "") if query else ""
        row[AUDIO_COLUMN] = resolved_audio if resolved_audio else NULL_AUDIO
        if row[AUDIO_COLUMN] != NULL_AUDIO:
            filled += 1
        else:
            empty += 1

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=out_fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)

    return filled, empty
