---
name: add-new-words
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
- In vocab TSVs, write `audio_file` as either:
  - plain relative text under `docs/assets/audio/forvo_no/` when audio exists, or
  - literal `null` when audio is unavailable.
- During pending audio staging only, empty `audio_file` is allowed as a temporary "needs lookup" state.
- Do not insert Markdown links in TSV fields.

## Canonical Rules (DRY)

- Treat `.agents/rules/vocab_rules.md` as the single source of truth for:
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
4. Build staged rows in a temporary file first (do not write target TSV yet).
- Fill all six vocab columns for each new entry.
- Include `target_tsv` per row so each staged entry knows its destination file.
- Write the temp TSV `<tmp_pending.tsv>` with this exact header:
  `target_tsv	lexical-category	english	norwegian	pronunciation	example_sentence	audio_file`
- Set staged `audio_file` to empty (`""`) before lookup.
5. Download audio for staged words using `add_forvo_audio.py` (it uses `scrape_forvo` internally).
- Run:
  - `uv run python scripts/forvo_audio/add_forvo_audio.py --pending-file <tmp_pending.tsv>`
- If audio is found, store the downloaded file under `docs/assets/audio/forvo_no/` and keep the TSV value as the corresponding relative path.
- If no audio is found, set `audio_file` to literal `null` rather than leaving it empty or inventing a path.
6. Apply staged rows to target TSV file(s).
- `--pending-file` flow appends rows into each `target_tsv` and creates missing target TSV files when needed.
- Resolved audio is written as plain relative paths under `docs/assets/audio/forvo_no/`.
- Unresolved audio is written as literal `null`.
7. Validate before finishing.
- Header matches repository standard.
- Rows comply with `.agents/rules/vocab_rules.md`.
- `audio_file` is either a plain relative path under `docs/assets/audio/forvo_no/` or literal `null`.
8. Recheck correctness explicitly.
  - Confirm staged row count equals appended row count across all targets.
  - Confirm every appended row has `audio_file` as path or `null` (no blanks).
  - Confirm each non-null audio path exists on disk.
9. Cleanup temporary artifacts.
  - After the operation is done, remove the pending TSV and the temporary download directory (default: `forvo_mp3/`) if you do not need them.
10. ensure the sync between `.tsv` file and `.md` by running `uv run pre-commit run --all-files`
11. run git add, commit, and push for all the updated files.
  - write descriptive commit message -- concise summary, followed by detailed comments. 


## Generation Guidance

- Mix lexical categories only when useful; otherwise keep category focused for learnability.
- Keep English and Norwegian pairs practically equivalent.
- Use short, plausible example sentences suited to beginner/intermediate learners.

## Safety Checks

- If user intent is ambiguous (existing file vs new file), infer from phrasing:
  "add to <topic>" means update existing TSV, "create/make a file for <topic>" means new TSV.
- If the requested topic is too broad, pick a coherent sub-scope and proceed.
- Avoid changing unrelated existing rows unless user asks for cleanup.
