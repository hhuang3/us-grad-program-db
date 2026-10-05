#!/bin/zsh
# Weekly snapshot run for launchd (docs/spec/07_snapshots.md §10.1).
# launchd does not read ~/.zshrc, so the contact email comes from ~/.config/gradprog/env
# (outside the repository, permissions 600, one line: GRADPROG_CONTACT_EMAIL=you@example.com).
set -eu
ENV_FILE="$HOME/.config/gradprog/env"
if [[ ! -r "$ENV_FILE" ]]; then
  echo "missing $ENV_FILE (see ops/launchd/README.md)" >&2
  exit 1
fi
GRADPROG_CONTACT_EMAIL="$(sed -n 's/^GRADPROG_CONTACT_EMAIL=//p' "$ENV_FILE" | head -n 1)"
if [[ -z "$GRADPROG_CONTACT_EMAIL" ]]; then
  echo "GRADPROG_CONTACT_EMAIL is not set in $ENV_FILE" >&2
  exit 1
fi
export GRADPROG_CONTACT_EMAIL
cd "$(dirname "$0")/../.."
mkdir -p data/snapshots/logs
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) snapshot run ==="
uv run gradprog snapshot run
