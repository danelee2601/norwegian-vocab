---
name: edit-delete-vocab
description: Edit or delete vocabulary data in this repo. Use when asked to remove or modify specific entries in `vocab/*.tsv` (by category name like `<topic>.tsv` or by file path), or when asked to delete an entire topic TSV file. Always run `uv run pre-commit run --all-files` to resync generated docs after changes.
---

# Edit/Delete Vocab

## Scope

- Edit mode: remove or update specific rows in an existing `vocab/*.tsv`.
- Delete mode: delete an entire topic TSV file under `vocab/`.
- After any change, run `uv run pre-commit run --all-files` to sync `.tsv` and generated `.md` docs.

## Assumptions (Ask If Unclear)

- If the user provides a category name like `school` or `school.tsv`, target `vocab/school.tsv` if unsure, ask a question.
- If the user provides a path, use that path (must be under `vocab/`).
- User must not ask to delete any .md file since the sync is done from .tsv to .md, so deleting any entry in .md won't do anything. <basename.tsv> is the single source of truth for word data.
- If a removal request is ambiguous (multiple matching rows, partial matches, similar words), ask the user which exact row(s) to remove by showing the candidate rows.
- Do not delete audio assets under `docs/assets/audio/forvo_no/` unless the user explicitly asks. Audio files may be shared across topics.

## TSV Rules

- Keep the header and column order unchanged:
  `lexical-category	english	norwegian	pronunciation	example_sentence	audio_file`
- Preserve tab separators and keep one entry per line (no embedded newlines).
- Prefer exact matching on `norwegian` and/or `english` when removing rows.

## Workflow (Edit: Remove/Modify Rows)

1. Identify the target TSV.
  - Map `<topic>` or `<topic>.tsv` to `vocab/<topic>.tsv`.
  - If the file does not exist, ask whether they meant a different category.
2. Locate the row(s) to change.
  - Use exact matches first (e.g., find rows where `norwegian` equals the provided string).
  - If multiple matches exist, present the matching rows and ask which ones to remove/update.
3. Apply the change.
  - Remove: delete the entire line(s) for the selected row(s).
  - Modify: update only the requested fields; if changing `english`/`norwegian`, also update `example_sentence` to stay consistent.
4. Run the docs sync hook via pre-commit.
  - Run: `uv run pre-commit run --all-files`
  - Note: the repo’s local hook may auto-write docs and then exit non-zero, which is OK; if it does, re-run the same command until it passes cleanly.
5. Validate the result.
  - Confirm the target TSV still has the correct header and no malformed rows.
  - Confirm generated docs changes are present (if any) and pre-commit passes.

## Workflow (Delete: Remove a Topic File)

1. Confirm the target.
  - Map `<topic>` or `<topic>.tsv` to `vocab/<topic>.tsv`.
  - If the request could match multiple files, ask which one to delete.
2. Delete only the TSV file.
  - Remove `vocab/<topic>.tsv`.
  - Do not delete audio files unless explicitly requested.
3. Delete the corresponding MD file -- `docs/vocab/<topic>.md` using `rm docs/vocab/<topic>.md`. 
4. Validate the result.
  - Confirm delete of the TSV and MD files with the same basename.

## When To Ask Questions (Hard Stops)

- The user specifies a word but not whether to match `english` vs `norwegian`.
- Multiple rows match the provided word(s) and the correct target rows are unclear.
- The user asks to delete “the category” but there are multiple similarly named TSVs.
- The user wants “delete everything related” (confirm whether that includes audio assets and/or any docs pages beyond what pre-commit auto-sync touches).

