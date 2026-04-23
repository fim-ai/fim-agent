#!/usr/bin/env bash
# Idempotent deploy wrapper for fim-one.
#
# Fixes the recurring "Conflict. The container name ... is already in use"
# error on `docker compose up -d`. Root cause: the sandbox service runs in
# Docker-outside-of-Docker (DooD) mode — when it spawns user-code child
# containers that outlive a restart, the daemon refuses to delete the parent
# and leaves a zombie renamed to `<hash>_fim-one-sandbox-1`. The next deploy
# then collides on that hash-prefixed name.
#
# This script removes those zombies (and any stray DooD child containers)
# before invoking compose. Safe to run repeatedly.

set -euo pipefail

cd "$(dirname "$0")"

COMPOSE="docker compose"

log() { printf '\033[1;34m[deploy]\033[0m %s\n' "$*"; }

# --- 1. Kill any DooD child containers spawned by the sandbox -------------
# The sandbox mounts /var/run/docker.sock and spawns short-lived user-code
# containers. If any are still running they hold mounts that block the
# parent's removal. Best-effort label match; falls back to image match.
log "Sweeping DooD sandbox child containers..."
docker ps -aq --filter "ancestor=fim-sandbox:python" 2>/dev/null \
  | xargs -r docker rm -f >/dev/null || true

# --- 2. Remove hash-prefixed zombie containers ----------------------------
# Docker renames containers it can't delete to `<12-hex>_<original-name>`.
# Match that exact pattern for our compose project so we don't touch
# unrelated containers.
log "Sweeping hash-prefixed zombie containers..."
ZOMBIES=$(docker ps -a --format '{{.Names}}' \
  | grep -E '^[0-9a-f]{12}_fim-one-(sandbox|fim-one|postgres|redis)-[0-9]+$' \
  || true)
if [[ -n "${ZOMBIES}" ]]; then
  echo "${ZOMBIES}" | xargs -r docker rm -f >/dev/null || true
  echo "${ZOMBIES}" | sed 's/^/  removed: /'
fi

# --- 3. Stop+remove current compose services cleanly ----------------------
# `rm -f -s -v` ensures the expected names are free before `up` runs, which
# is the whole point of making this idempotent.
log "Stopping current compose services..."
$COMPOSE rm -f -s -v sandbox >/dev/null 2>&1 || true

# --- 4. Bring the stack up ------------------------------------------------
log "Building and starting services..."
$COMPOSE up -d --build --remove-orphans "$@"

log "Done."
$COMPOSE ps
