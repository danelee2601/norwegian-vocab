from __future__ import annotations

from pathlib import Path


def resolve_path_ref(path_ref: str, *, base_dir: Path) -> Path:
    path = Path(path_ref)
    return path if path.is_absolute() else base_dir / path


def resolve_audio_path(path_ref: str, *, base_dir: Path) -> Path:
    return resolve_path_ref(path_ref, base_dir=base_dir)


def normalize_audio_path(path: Path, *, base_dir: Path) -> str:
    abs_path = path.resolve()
    try:
        return abs_path.relative_to(base_dir.resolve()).as_posix()
    except ValueError:
        return abs_path.as_posix()
