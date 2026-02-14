from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from .audio_paths import resolve_path_ref
from .vocab_tsv import AUDIO_COLUMN, VOCAB_FIELDS, ensure_audio_column, read_rows

PENDING_TARGET_COLUMN = "target_tsv"
PENDING_HEADER = [
    PENDING_TARGET_COLUMN,
    *VOCAB_FIELDS,
]


def resolve_pending_target(target_ref: str, *, base_dir: Path) -> Path:
    return resolve_path_ref(target_ref, base_dir=base_dir)


def read_pending_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"Missing header in pending file: {path}")
        if reader.fieldnames != PENDING_HEADER:
            raise ValueError(
                f"Unexpected pending header in {path}. Expected: {PENDING_HEADER}, got: {reader.fieldnames}"
            )

        return [dict(row) for row in reader]


def write_pending_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PENDING_HEADER, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def append_pending_rows_to_vocab(
    pending_rows: list[dict[str, str]],
    *,
    base_dir: Path,
) -> dict[Path, int]:
    grouped: dict[Path, list[dict[str, str]]] = defaultdict(list)
    for row in pending_rows:
        target_ref = row.get(PENDING_TARGET_COLUMN, "").strip()
        if not target_ref:
            raise ValueError(f"Pending row missing {PENDING_TARGET_COLUMN}: {row}")
        grouped[resolve_pending_target(target_ref, base_dir=base_dir)].append(row)

    appended_counts: dict[Path, int] = {}
    for target, new_rows in grouped.items():
        if target.exists():
            fieldnames, existing_rows = read_rows(target)
        else:
            fieldnames, existing_rows = VOCAB_FIELDS, []
            target.parent.mkdir(parents=True, exist_ok=True)
        out_fields = ensure_audio_column(fieldnames)

        rows_to_append: list[dict[str, str]] = []
        for row in new_rows:
            payload = {key: row.get(key, "") for key in out_fields}
            rows_to_append.append(payload)

        with target.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=out_fields, delimiter="\t")
            writer.writeheader()
            writer.writerows(existing_rows)
            writer.writerows(rows_to_append)
        appended_counts[target] = len(rows_to_append)

    return appended_counts
