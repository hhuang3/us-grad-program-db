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
SLOW_SECONDS=900   # 07 §10.1: warn when a run takes longer than 15 minutes

# One-line power summary, e.g. "Battery Power; 11%; discharging; 2:10 remaining".
power() {
  pmset -g batt 2>/dev/null | awk '
    NR == 1 { sub(/^Now drawing from /, ""); gsub(/\047/, ""); src = $0 }
    NR == 2 { sub(/^.*\)[ \t]*/, ""); sub(/ present:.*/, ""); batt = $0 }
    END { print src (batt != "" ? "; " batt : "") }'
}

# Number of "Entering Sleep state" entries in the power log between two local times (YYYY-MM-DD HH:MM:SS).
sleeps_between() {
  pmset -g log 2>/dev/null | awk -v from="$1" -v to="$2" '
    /Entering Sleep state/ { t = substr($0, 1, 19); if (t >= from && t <= to) n++ }
    END { print n + 0 }'
}

echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) snapshot run ==="
echo "power: $(power)"
start_local="$(date '+%Y-%m-%d %H:%M:%S')"
start_s=$(date +%s)
rc=0
# caffeinate -i blocks idle sleep while the run lasts; it does not prevent lid-close sleep (07 §10.1).
caffeinate -i uv run gradprog snapshot run || rc=$?
end_local="$(date '+%Y-%m-%d %H:%M:%S')"
elapsed=$(( $(date +%s) - start_s ))
sleeps="$(sleeps_between "$start_local" "$end_local")"
echo "power: $(power)"
echo "elapsed ${elapsed} s; sleeps during run: ${sleeps}; exit ${rc}"
if (( sleeps > 0 || elapsed > SLOW_SECONDS )); then
  echo "WARNING: the Mac went to sleep or the run took longer than ${SLOW_SECONDS} s; check power and lid (see ops/launchd/README.md)"
fi
exit $rc
