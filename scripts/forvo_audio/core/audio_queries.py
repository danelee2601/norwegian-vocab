from __future__ import annotations

import re

SUPPORTED_CATEGORIES = {"noun", "verb", "adjective", "adverb"}
SKIPPED_CATEGORIES = {"expression"}


def extract_query(category: str, norwegian: str) -> str | None:
    normalized_category = category.strip().lower()
    normalized_text = norwegian.strip()

    if not normalized_text or normalized_category in SKIPPED_CATEGORIES:
        return None
    if normalized_category not in SUPPORTED_CATEGORIES:
        return None

    if normalized_category == "noun":
        # Keep lexical noun and drop leading article.
        noun = re.sub(r"^(en|ei|et)\s+", "", normalized_text, flags=re.IGNORECASE)
        return noun.strip() or None

    if normalized_category == "verb":
        # Input shape: "å ta, tar, tok, har tatt" -> "ta"
        infinitive = normalized_text.split(",", 1)[0].strip()
        infinitive = re.sub(r"^å\s+", "", infinitive, flags=re.IGNORECASE)
        return infinitive.strip() or None

    return normalized_text


def extract_row_query(row: dict[str, str]) -> str | None:
    return extract_query(row.get("lexical-category", ""), row.get("norwegian", ""))
