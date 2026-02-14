#!/usr/bin/env python3
"""Convert vocab TSV files to Markdown tables with GitHub-safe audio links."""

from __future__ import annotations

import csv
import glob
import re
from pathlib import Path

MD_LINK_RE = re.compile(r"^\[([^\]]+)\]\(([^)]+)\)$")


def escape_md(text: str) -> str:
    return text.replace("\\", "\\\\").replace("|", r"\|").replace("\n", " ")


def normalize_audio_src(raw: str, output_dir: Path) -> str:
    raw = raw.strip()
    if not raw:
        return ""

    m = MD_LINK_RE.match(raw)
    src = m.group(2).strip() if m else raw

    if src.startswith(("http://", "https://", "/")):
        return src
    if src.startswith("audio/"):
        # TSV paths are repo-root-relative; Markdown files are in vocab/.
        return f"../{src}"
    return src


def audio_cell(raw: str, output_dir: Path) -> str:
    src = normalize_audio_src(raw, output_dir)
    if not src:
        return ""
    return f"[Play audio]({src})"


def convert_tsv(tsv_path: Path) -> None:
    md_path = tsv_path.with_suffix(".md")
    with tsv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        headers = list(reader.fieldnames or [])
        rows = list(reader)

    if not headers:
        return

    lines: list[str] = []
    lines.append("| " + " | ".join(escape_md(h) for h in headers) + " |")
    lines.append("| " + " | ".join("---" for _ in headers) + " |")

    for row in rows:
        cells: list[str] = []
        for h in headers:
            raw = row.get(h, "") or ""
            if h == "audio_file":
                cells.append(audio_cell(raw, md_path.parent))
            else:
                cells.append(escape_md(raw.strip()))
        lines.append("| " + " | ".join(cells) + " |")

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    for file in sorted(glob.glob("vocab/*.tsv")):
        convert_tsv(Path(file))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
