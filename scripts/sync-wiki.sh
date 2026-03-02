#!/usr/bin/env bash
# Sync local wiki/ directory to the GitHub Wiki repository.
#
# Usage:
#   ./scripts/sync-wiki.sh          # clone wiki repo to /tmp, copy, commit, push
#   ./scripts/sync-wiki.sh --dry    # show diff without pushing
#
# How it works:
#   1. Clones (or pulls) the wiki repo to /tmp/fim-agent-wiki
#   2. Copies all wiki/*.md files over
#   3. Commits and pushes changes
#
# This is a one-way sync: local wiki/ -> GitHub Wiki.
# The local wiki/ directory is the source of truth.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WIKI_SRC="$REPO_ROOT/wiki"
WIKI_REPO="git@github.com:fim-ai/fim-agent.wiki.git"
WIKI_DIR="/tmp/fim-agent-wiki"
DRY_RUN="${1:-}"

# Clone or pull
if [ -d "$WIKI_DIR/.git" ]; then
  git -C "$WIKI_DIR" pull --quiet
else
  git clone --quiet "$WIKI_REPO" "$WIKI_DIR"
fi

# Remove files in wiki repo that no longer exist locally, then copy
for f in "$WIKI_DIR"/*.md; do
  base="$(basename "$f")"
  if [ ! -f "$WIKI_SRC/$base" ]; then
    rm "$f"
  fi
done
cp "$WIKI_SRC"/*.md "$WIKI_DIR/"

# Check for changes
cd "$WIKI_DIR"
if git diff --quiet && git diff --cached --quiet && [ -z "$(git ls-files --others --exclude-standard)" ]; then
  echo "Wiki is already up to date."
  exit 0
fi

# Show diff
git add -A
echo "=== Changes ==="
git diff --cached --stat
echo ""

if [ "$DRY_RUN" = "--dry" ]; then
  echo "(dry run — not pushing)"
  git reset HEAD --quiet
  exit 0
fi

# Commit and push
git commit -m "sync: update wiki from local wiki/ directory"
git push --quiet
echo "Wiki synced successfully."
