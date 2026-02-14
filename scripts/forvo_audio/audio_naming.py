from __future__ import annotations

import re

_FORVO_NO_AUDIO_PATTERN = re.compile(r"^no_(.+)_\d+_\d{3}\.mp3$")


def query_from_forvo_filename(filename: str) -> str | None:
    match = _FORVO_NO_AUDIO_PATTERN.match(filename)
    if not match:
        return None
    label = match.group(1).replace("_", " ").strip().casefold()
    return label or None
