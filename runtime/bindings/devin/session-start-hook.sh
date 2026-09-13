#!/bin/bash
# devin/session-start-hook.sh — translates session-start.sh's plain-text output into Devin's
# SessionStart hookSpecificOutput envelope. Stream resolution uses $DEVIN_PROJECT_DIR (live-
# confirmed correct, design/devin-binding.md §2/§5) rather than a stdin field — Devin's
# SessionStart payload only carries `source`, no cwd-equivalent, unlike Claude Code's own.
PERMA="${PERMA_DIR:-$HOME/permanence}"
[ -d "$PERMA" ] || { echo '{}'; exit 0; }

CWD="${DEVIN_PROJECT_DIR:-$PWD}"
PAYLOAD="$(python3 -c 'import json,sys; print(json.dumps({"cwd": sys.argv[1]}))' "$CWD" 2>/dev/null)"
[ -n "$PAYLOAD" ] || PAYLOAD="{}"

ORIENT="$(printf '%s' "$PAYLOAD" | PERMA_DIR="$PERMA" bash "$PERMA/runtime/session-start.sh" 2>/dev/null)"

if [ -z "$ORIENT" ]; then
  echo '{}'
  exit 0
fi

python3 -c '
import json, sys
print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": sys.stdin.read()}}))
' <<< "$ORIENT"
