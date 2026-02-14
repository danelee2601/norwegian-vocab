# Repository Guidelines

## Project Structure & Module Organization
- Vocabulary data lives in topic-based TSV files under `vocab/` (e.g., `vocab/school.tsv`, `vocab/grocery_store.tsv`).
- Each TSV uses the same columns: `lexical-category`, `english`, `norwegian`, `pronunciation`, `example_sentence`, `audio_file`.
- Audio assets are stored under `docs/assets/audio/forvo_no/`.
- Audio tooling lives in `scripts/forvo_audio/`:
  - `add_forvo_audio.py` updates TSV `audio_file` values.
  - helper modules split query extraction, path handling, TSV I/O, and Forvo download orchestration.
- Python metadata/dependencies are defined in `pyproject.toml` and locked in `uv.lock`.

## Build, Test, and Development Commands
- This project uses [uv](https://github.com/astral-sh/uv) for Python dependency management and installation. Typical commands:
  - `uv sync` to install runtime + dev dependencies.
  - `uv run pytest -q` to run tests.
  - `uv run pytest --cov=. --cov-report=term-missing -q` to run tests with coverage.
  - `uv run python scripts/forvo_audio/add_forvo_audio.py --pending-file tmp/pending.tsv` to process staged rows and append them to target vocab files.

## Testing Guide
- Run tests before committing:
  - `uv run pytest -q`
- Run coverage when changing Python logic:
  - `uv run pytest --cov=. --cov-report=term-missing -q`
- Recommended data sanity checks for TSV changes:
  - Confirm header/order matches across all `vocab/*.tsv`.
  - Confirm noun rows start with `en/ei/et`.
  - Confirm verb rows have 4 comma-separated forms.
  - Confirm `audio_file` is a plain relative path under `docs/assets/audio/forvo_no/` when present.
- If tests fail:
  - Fix root causes first; avoid weakening assertions unless requirements changed.
  - Re-run full test command (not only a subset) before finalizing.

## Data Style & Naming Conventions
- TSV format with tab separators and a single header row.
- Keep entries one per line; avoid embedded newlines in fields.
- Norwegian nouns should include an article: `en/ei/et` (e.g., `en bil`).
- Norwegian verbs should be in the form: `å <verb>, present, past, past perfect` (e.g., `å spise, spiser, spiste, har spist`).
- Pronunciation should reflect the infinitive form only.
- `audio_file` should be a plain relative path (for example, `docs/assets/audio/forvo_no/no_bank_744497_001.mp3`), not a Markdown link.

## Everyday Vocabulary Policy (for AI-generated additions)
- Prioritize high-frequency words used in daily life in Norway: home, family, school, work, shopping, food, transport, health, weather, social conversation, and common public services.
- Favor practical communicative value over lexical novelty. If a beginner/intermediate learner is likely to need the word in normal weekly conversation, it is in scope.
- Avoid rare, highly technical, domain-specific, literary, archaic, or regionally narrow terms unless a file explicitly targets that domain.
- Prefer neutral Bokmal forms that are broadly understood.
- Prefer concrete words and short expressions that can be used immediately in real-world situations.
- Example sentences should reflect plausible everyday situations and reinforce the same practical meaning as the `english` and `norwegian` fields.
- When multiple candidate words exist, choose the one that is more common in everyday speech.
- Keep difficulty progression practical: foundational daily-life words first, then moderately common extensions.

## Guidelines for the vocabulary files (vocab/*.tsv)
- There are no formal tests.
- Suggested lightweight validation:
  - Ensure all files have the same header.
  - Ensure every noun starts with `en/ei/et`.
  - Ensure every verb contains exactly four comma‑separated forms.
  - Ensure `audio_file` paths are relative, plain text, and point into `docs/assets/audio/forvo_no/`.

## Agent Notes
- Changes should be consistent across all TSV files to keep formats uniform.
- When adjusting translations, update example sentences to match the revised Norwegian terms.
- Treat TSV `audio_file` values as the source of truth for persisted audio mappings.
