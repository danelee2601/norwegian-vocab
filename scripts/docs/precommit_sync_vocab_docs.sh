#!/usr/bin/env bash
set -euo pipefail

if uv run python scripts/docs/sync_vocab_docs.py --check; then
  exit 0
fi

echo "sync_vocab_docs check failed; running auto-sync..." >&2
uv run python scripts/docs/sync_vocab_docs.py --write

echo "Docs were auto-synced. Stage generated changes and re-run commit." >&2
exit 1
