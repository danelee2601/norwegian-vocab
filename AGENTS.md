# Repository Guidelines

## Project Structure & Module Organization
- Vocabulary data lives in topic-based TSV files at the repo root (e.g., `school.tsv`, `grocery_store.tsv`).
- Each TSV uses the same columns: `lexical-category`, `english`, `norwegian`, `pronunciation`, `example_sentence`.
- There is no separate source code or test directory in this repository.

## Build, Test, and Development Commands
- No build system or test runner is configured.
- Useful checks can be done with ad‑hoc scripts, for example:
  - `python3 - <<'PY' ... PY` for validating column formats or counting entries.

## Data Style & Naming Conventions
- TSV format with tab separators and a single header row.
- Keep entries one per line; avoid embedded newlines in fields.
- Norwegian nouns should include an article: `en/ei/et` (e.g., `en bil`).
- Norwegian verbs should be in the form: `å <verb>, present, past, past perfect` (e.g., `å spise, spiser, spiste, har spist`).
- Pronunciation should reflect the infinitive form only.

## Testing Guidelines
- There are no formal tests.
- Suggested lightweight validation:
  - Ensure all files have the same header.
  - Ensure every noun starts with `en/ei/et`.
  - Ensure every verb contains exactly four comma‑separated forms.

## Commit & Pull Request Guidelines
- Use clear, scoped commit messages, e.g., `Normalize verb forms in school.tsv`.
- Keep commits focused on one logical change when possible.
- Default branch is `main`; push to a feature branch if you plan a PR.
- For PRs, include a brief summary of changed files, any bulk transformations applied, and examples of before/after if translations were updated.

## Agent Notes
- Changes should be consistent across all TSV files to keep formats uniform.
- When adjusting translations, update example sentences to match the revised Norwegian terms.
