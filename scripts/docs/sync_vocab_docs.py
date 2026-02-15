#!/usr/bin/env python3
"""Sync vocab TSV files to MkDocs markdown pages."""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    import mdformat
except ImportError:  # pragma: no cover
    mdformat = None

EXPECTED_HEADER = [
    "lexical-category",
    "english",
    "norwegian",
    "pronunciation",
    "example_sentence",
    "audio_file",
]
AUTO_NAV_START = "  # AUTO-GENERATED VOCAB NAV START"
AUTO_NAV_END = "  # AUTO-GENERATED VOCAB NAV END"
AUDIO_PREFIX = "docs/assets/audio/forvo_no/"


@dataclass(frozen=True)
class Paths:
    root: Path
    vocab_dir: Path
    docs_dir: Path
    docs_vocab_dir: Path
    mkdocs_yml: Path


def make_paths() -> Paths:
    root = Path(__file__).resolve().parents[2]
    return Paths(
        root=root,
        vocab_dir=root / "vocab",
        docs_dir=root / "docs",
        docs_vocab_dir=root / "docs" / "vocab",
        mkdocs_yml=root / "mkdocs.yml",
    )


def title_from_stem(stem: str) -> str:
    return stem.replace("_", " ").title()


def escape_md_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def read_tsv_rows(tsv_path: Path) -> list[dict[str, str]]:
    with tsv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        if reader.fieldnames != EXPECTED_HEADER:
            raise ValueError(
                f"{tsv_path}: header mismatch. expected={EXPECTED_HEADER} actual={reader.fieldnames}"
            )
        return [dict(row) for row in reader]


def render_audio_cell(audio_value: str) -> str:
    if audio_value == "null" or not audio_value:
        return "null"

    if not audio_value.startswith(AUDIO_PREFIX):
        return escape_md_cell(audio_value)

    filename = Path(audio_value).name
    src = f"../../assets/audio/forvo_no/{filename}"
    return f'<audio controls preload="none" src="{src}"></audio>'


def render_topic_markdown(stem: str, rows: list[dict[str, str]]) -> str:
    lines = [
        f"# {title_from_stem(stem)}",
        "",
        f"Source: `vocab/{stem}.tsv`",
        "",
        "| lexical-category | english | norwegian | pronunciation | example_sentence | audio_file |",
        "|---|---|---|---|---|---|",
    ]

    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    escape_md_cell(row["lexical-category"]),
                    escape_md_cell(row["english"]),
                    escape_md_cell(row["norwegian"]),
                    escape_md_cell(row["pronunciation"]),
                    escape_md_cell(row["example_sentence"]),
                    render_audio_cell(row["audio_file"]),
                ]
            )
            + " |"
        )

    lines.append("")
    content = "\n".join(lines)
    if mdformat is not None:
        return mdformat.text(content)
    return content


def expected_nav_block(stems: list[str]) -> list[str]:
    lines = [AUTO_NAV_START, "  - Vocabulary:"]
    for stem in stems:
        lines.append(f"      - {title_from_stem(stem)}: vocab/{stem}.md")
    lines.append(AUTO_NAV_END)
    return lines


def replace_nav_block(mkdocs_text: str, stems: list[str]) -> str:
    current_lines = mkdocs_text.splitlines()

    try:
        start = current_lines.index(AUTO_NAV_START)
        end = current_lines.index(AUTO_NAV_END)
    except ValueError as exc:
        raise ValueError(
            "mkdocs.yml missing nav markers. Add AUTO-GENERATED VOCAB NAV START/END markers."
        ) from exc

    if end <= start:
        raise ValueError("mkdocs.yml nav markers are in invalid order")

    new_lines = current_lines[:start] + expected_nav_block(stems) + current_lines[end + 1 :]
    return "\n".join(new_lines).rstrip() + "\n"


def collect_stems(paths: Paths) -> list[str]:
    return sorted(p.stem for p in paths.vocab_dir.glob("*.tsv"))


def write_outputs(paths: Paths) -> None:
    """Generate docs outputs from vocab TSV files.

    Produces one markdown page per TSV stem under `docs/vocab/`, removes
    orphaned markdown pages that no longer have a TSV source, and rewrites the
    vocabulary nav block in `mkdocs.yml` to match the current stems.
    """
    stems = collect_stems(paths)
    rows_by_stem: dict[str, list[dict[str, str]]] = {
        stem: read_tsv_rows(paths.vocab_dir / f"{stem}.tsv") for stem in stems
    }

    paths.docs_vocab_dir.mkdir(parents=True, exist_ok=True)
    # Write/update topic pages.
    expected_md_names = {f"{stem}.md" for stem in stems}
    for stem in stems:
        md_path = paths.docs_vocab_dir / f"{stem}.md"
        md_path.write_text(render_topic_markdown(stem, rows_by_stem[stem]), encoding="utf-8")

    # Remove docs with no source TSV.
    for md_path in paths.docs_vocab_dir.glob("*.md"):
        if md_path.name not in expected_md_names:
            md_path.unlink()

    # Update mkdocs navigation block.
    mkdocs_text = paths.mkdocs_yml.read_text(encoding="utf-8")
    updated = replace_nav_block(mkdocs_text, stems)
    paths.mkdocs_yml.write_text(updated, encoding="utf-8")


def check_outputs(paths: Paths) -> list[str]:
    """Validate docs/vocab pages and mkdocs nav are in sync with vocab TSV files.

    Checks:
    - Each vocab TSV has a corresponding docs/vocab/{stem}.md page
    - No orphan docs pages exist (md without TSV source)
    - Each docs page content matches the rendered form of its TSV
    - mkdocs.yml vocabulary nav block matches the TSV stems

    Returns:
        List of error messages. Empty list means all checks passed.
    """
    errors: list[str] = []
    stems = collect_stems(paths)

    rows_by_stem: dict[str, list[dict[str, str]]] = {}
    for stem in stems:
        try:
            rows_by_stem[stem] = read_tsv_rows(paths.vocab_dir / f"{stem}.tsv")
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc))

    actual_stems = sorted(p.stem for p in paths.docs_vocab_dir.glob("*.md")) if paths.docs_vocab_dir.exists() else []
    missing = sorted(set(stems) - set(actual_stems))
    extra = sorted(set(actual_stems) - set(stems))

    if missing:
        errors.append(f"missing docs/vocab pages for TSV files: {', '.join(missing)}")
    if extra:
        errors.append(f"extra docs/vocab pages without TSV source: {', '.join(extra)}")

    for stem in stems:
        md_path = paths.docs_vocab_dir / f"{stem}.md"
        if not md_path.exists() or stem not in rows_by_stem:
            continue
        expected = render_topic_markdown(stem, rows_by_stem[stem])
        actual = md_path.read_text(encoding="utf-8")
        if actual != expected:
            errors.append(f"stale docs page content: {md_path}")

    if paths.mkdocs_yml.exists():
        mkdocs_text = paths.mkdocs_yml.read_text(encoding="utf-8")
        try:
            expected_mkdocs = replace_nav_block(mkdocs_text, stems)
            if mkdocs_text != expected_mkdocs:
                errors.append("mkdocs.yml vocabulary nav block is out of sync")
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc))
    else:
        errors.append("mkdocs.yml is missing")

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync vocab TSV files to docs markdown pages")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="check whether docs are in sync")
    mode.add_argument("--write", action="store_true", help="write/update docs from TSV")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths = make_paths()

    if args.write:
        write_outputs(paths)
        print("docs sync completed")
        return 0

    errors = check_outputs(paths)
    if errors:
        for err in errors:
            print(f"sync check failed: {err}", file=sys.stderr)
        return 1

    print("docs are in sync")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
