---
name: vocab-tsv-manager
description: Add or generate Norwegian vocabulary entries in this repository's TSV format. Use when asked to update an existing `vocab/*.tsv` file with user-provided words, infer and propose suitable words for a requested topic, or create a new topic TSV and populate it with practical everyday Bokmal vocabulary that matches repository rules.
---

# Vocab Tsv Manager

## Overview

Update existing vocabulary TSV files and create new topic TSV files that follow the repository schema and style. Handle both direct user word lists and broad requests where the assistant must propose the words.

## Required Format

- Operate on TSV files under `vocab/`.
- Keep this exact header and order:
  `lexical-category	english	norwegian	pronunciation	example_sentence	audio_file`
- Keep one entry per line and no embedded newlines.
- Write `audio_file` as either:
  - plain relative text under `audio/forvo_no/` when audio exists, or
  - literal `null` when audio is unavailable.
- Do not insert Markdown links in TSV fields.

## Canonical Rules (DRY)

- Treat `codex/rules/vocab_rules.md` as the single source of truth for:
  - TSV schema and header order
  - word-form constraints (noun articles, verb 4-form pattern, etc.)
  - pronunciation/example/audio formatting rules
- Do not restate or invent alternative form rules inside this skill; follow `vocab_rules.md`.

## Everyday Vocabulary Filter

- Prefer high-frequency daily-life words: home, family, school, work, shopping, food, transport, health, weather, social conversation, public services.
- Avoid rare, technical, archaic, literary, or narrow regional terms unless the file explicitly needs that domain.
- Choose the more common everyday option when synonyms compete.

## Workflow

1. Identify target file mode.
- Existing file update: use the requested TSV in `vocab/`.
- New file creation: create `vocab/<topic>.tsv` with the standard header.
2. Confirm target entry count for this run.
- Ask the user for the approximate number of words to add.
- Also suggest a practical default that covers high-frequency vocabulary for the topic:
  - narrow topic: suggest 25-35 words
  - standard everyday topic: suggest 100-150 words
  - broad topic: suggest 200-300 words, preferably split into multiple passes/files
- If the user does not specify a number, proceed with your suggested default and state it.
3. Determine source of candidate words.
- If user supplies words, use those and normalize forms to repository rules.
- If user gives only a topic or broad request, generate practical daily-use words for that topic.
4. Build rows.
- Fill all six columns.
- Use `audio_file=null` as the initial placeholder unless a confirmed relative audio path is already known.
5. Generate and sync `audio_file` values.
- After adding/updating rows, run:
  - `uv run python scripts/forvo_audio/add_forvo_audio.py --vocab-glob 'vocab/*.tsv'`
- This step is required for new entries so `audio_file` is searched and filled when audio exists.
- Follow `scripts/forvo_audio/vocab_tsv.py` behavior:
  - ensure `audio_file` column exists (`ensure_audio_column`)
  - update each row from the query->audio map (`update_tsv`)
  - unresolved entries may remain empty after this step
- Audio files must be stored under `audio/` (default `audio/forvo_no/`) and TSV values must remain plain relative paths.
6. Normalize unavailable audio values.
- Convert any empty or missing `audio_file` values to literal `null` so unavailable audio is explicit.
- Do not leave blank `audio_file` cells in final TSV output.
7. Validate before finishing.
- Header matches repository standard.
- Rows comply with `codex/rules/vocab_rules.md`.
- `audio_file` is either a plain relative path under `audio/forvo_no/` or literal `null`.
8. Apply edits directly.
- For existing files: append new rows unless user requests reordering.
- For new files: include header then rows.
- Preserve TSV tab separators.

## Generation Guidance

- Mix lexical categories only when useful; otherwise keep category focused for learnability.
- Keep English and Norwegian pairs practically equivalent.
- Use short, plausible example sentences suited to beginner/intermediate learners.

## Safety Checks

- If user intent is ambiguous (existing file vs new file), infer from phrasing:
  "add to <topic>" means update existing TSV, "create/make a file for <topic>" means new TSV.
- If the requested topic is too broad, pick a coherent sub-scope and proceed.
- Avoid changing unrelated existing rows unless user asks for cleanup.
