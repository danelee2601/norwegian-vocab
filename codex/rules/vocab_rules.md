# Norwegian Vocab Rules

Scope: TSV vocabulary data at repo root (topic files) and vocab/ copies.

## File layout
- One TSV per topic (e.g., `school.tsv`, `grocery_store.tsv`).
- Single header row:
  - lexical-category, english, norwegian, pronunciation, example_sentence, audio_file
- Tab-separated fields; no embedded newlines inside any field.

## Entry patterns
- One entry per line after the header.
- `lexical-category` values: noun, verb, adjective, adverb, expression.
- `english`: lowercase phrase preferred; may include parenthetical clarifiers (e.g., "class (lesson)").
- English nouns should be singular unless there is a strong reason to use plural.
- `norwegian` patterns:
  - Noun: includes article `en/ei/et` (e.g., `en skole`).
  - Verb: `å <infinitive>, present, past, past perfect` (comma + space separated),
    e.g., `å lære, lærer, lærte, har lært`.
  - Other categories: plain Norwegian term or phrase.
- `pronunciation`: IPA for the infinitive/base form only; use slashes (e.g., `/ˈskuːlə/`).
- `example_sentence`: full Norwegian sentence that matches the entry term/form.
- `audio_file`: either a plain relative path under `audio/forvo_no/` (for example, `audio/forvo_no/no_skole_293669_001.mp3`) or the literal `null` when unavailable.

## Consistency checks
- All topic files must share the same header and column order.
- Every noun must start with `en`, `ei`, or `et` in the Norwegian field.
- Every verb must contain exactly four comma-separated forms.
- Keep format uniform across files (spacing after commas, slashes around IPA).
- `audio_file` values must be either:
  - plain text relative paths under `audio/forvo_no/`, or
  - literal `null` when audio is not available.
- Never leave `audio_file` empty and do not use markdown links.

## Audio file policy for new entries
- When adding new vocabulary entries, run `scripts/forvo_audio/add_forvo_audio.py` to search Forvo audio and populate `audio_file` when available.
- Recommended command:
  - `uv run python scripts/forvo_audio/add_forvo_audio.py --vocab-glob 'vocab/*.tsv'`
- If audio is found, store the downloaded file under `audio/` (default `audio/forvo_no/`) and keep the TSV value as the corresponding relative path.
- If no audio is found, set `audio_file` to literal `null` rather than leaving it empty or inventing a path.
- Because the updater writes unresolved rows as empty values, do a normalization pass after running it so empty/missing `audio_file` cells become `null`.

## When editing translations
- Update the example sentence to align with the updated Norwegian term.
- Preserve the one-line, tab-separated format.
