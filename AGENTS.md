# Repository Guidelines

## Project Structure & Module Organization
- Vocabulary data lives in topic-based TSV files under `vocab/` (e.g., `vocab/school.tsv`, `vocab/grocery_store.tsv`).
- Each TSV uses the same columns: `lexical-category`, `english`, `norwegian`, `pronunciation`, `example_sentence`, `audio_file`.
- Audio assets are stored under `audio/forvo_no/`.
- Audio tooling lives in `scripts/forvo_audio/`:
  - `add_forvo_audio.py` updates TSV `audio_file` values.
  - `audio_index.json` stores the query-to-audio lookup map.
- Python metadata/dependencies are defined in `pyproject.toml` and locked in `uv.lock`.

## Build, Test, and Development Commands
- This project uses [uv](https://github.com/astral-sh/uv) for Python dependency management and installation. Typical commands:

## Data Style & Naming Conventions
- TSV format with tab separators and a single header row.
- Keep entries one per line; avoid embedded newlines in fields.
- Norwegian nouns should include an article: `en/ei/et` (e.g., `en bil`).
- Norwegian verbs should be in the form: `å <verb>, present, past, past perfect` (e.g., `å spise, spiser, spiste, har spist`).
- Pronunciation should reflect the infinitive form only.
- `audio_file` should be a plain relative path (for example, `audio/forvo_no/no_bank_744497_001.mp3`), not a Markdown link.

## Guidelines for the vocabulary files (vocab/*.tsv)
- There are no formal tests.
- Suggested lightweight validation:
  - Ensure all files have the same header.
  - Ensure every noun starts with `en/ei/et`.
  - Ensure every verb contains exactly four comma‑separated forms.
  - Ensure `audio_file` paths are relative, plain text, and point into `audio/forvo_no/`.
  - Ensure `audio_file` paths are specified for an entry/row if the entry's vocabulary word contains a valid audio file according to scripts/forvo_audio/audio_index.json (= cache file for the word <-> audio_file pairs)

## Agent Notes
- Changes should be consistent across all TSV files to keep formats uniform.
- When adjusting translations, update example sentences to match the revised Norwegian terms.
- Keep `scripts/forvo_audio/audio_index.json` and TSV `audio_file` values in sync when running audio updates.
