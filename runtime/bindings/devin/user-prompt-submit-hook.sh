#!/bin/bash
# devin/user-prompt-submit-hook.sh — translates session-load.sh's plain-text output into Devin's
# UserPromptSubmit hookSpecificOutput envelope. Reads Devin's real stdin payload for session_id
# (present on every Devin hook payload, per design/devin-binding.md §2) and $DEVIN_PROJECT_DIR for
# the working directory, then feeds session-load.sh a synthetic Claude-Code-shaped payload so its
# own existing once-per-session gate and stream-resolution logic just work, unchanged.
PERMA="${PERMA_DIR:-$HOME/permanence}"
[ -d "$PERMA" ] || { echo '{}'; exit 0; }

INPUT="$(cat 2>/dev/null)"
SID="$(printf '%s' "$INPUT" | python3 -c '
import json, sys
try: d = json.load(sys.stdin)
except Exception: d = {}
print(d.get("session_id") or "nosid")
' 2>/dev/null)"
[ -n "$SID" ] || SID="nosid"

CWD="${DEVIN_PROJECT_DIR:-$PWD}"
PAYLOAD="$(python3 -c 'import json,sys; print(json.dumps({"cwd": sys.argv[1], "session_id": sys.argv[2]}))' "$CWD" "$SID" 2>/dev/null)"
[ -n "$PAYLOAD" ] || PAYLOAD="{}"

LOAD="$(printf '%s' "$PAYLOAD" | PERMA_DIR="$PERMA" bash "$PERMA/runtime/session-load.sh" 2>/dev/null)"

if [ -z "$LOAD" ]; then
  echo '{}'
  exit 0
fi

python3 -c '
import json, sys
print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": sys.stdin.read()}}))
' <<< "$LOAD"
