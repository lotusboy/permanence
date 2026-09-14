#!/bin/bash
# cursor/session-start-hook.sh — translates session-start.sh's plain-text output into Cursor's
# sessionStart additional_context envelope. Live-confirmed (design/cursor-binding.md §2) this
# hook alone answers both passive orientation and the forcing read: a prompt that never mentioned
# Permanence still caused the agent to spontaneously read and accurately report real stream
# content, purely because this injected instruction told it to. No once-per-conversation cursor
# needed — sessionStart fires exactly once per session by its own nature, unlike Antigravity's
# PreInvocation or the general pattern the other bindings had to guard against.
PERMA="${PERMA_DIR:-$HOME/permanence}"
[ -d "$PERMA" ] || { echo '{}'; exit 0; }

INPUT="$(cat 2>/dev/null)"
CWD="$(printf '%s' "$INPUT" | python3 -c '
import json, sys
try: d = json.load(sys.stdin)
except Exception: d = {}
roots = d.get("workspace_roots") or []
print(roots[0] if roots else "")
' 2>/dev/null)"
[ -n "$CWD" ] || CWD="$PWD"

PAYLOAD="$(python3 -c 'import json,sys; print(json.dumps({"cwd": sys.argv[1]}))' "$CWD" 2>/dev/null)"
[ -n "$PAYLOAD" ] || PAYLOAD="{}"

ORIENT="$(printf '%s' "$PAYLOAD" | PERMA_DIR="$PERMA" bash "$PERMA/runtime/session-start.sh" 2>/dev/null)"

if [ -z "$ORIENT" ]; then
  echo '{}'
  exit 0
fi

python3 -c '
import json, sys
print(json.dumps({"additional_context": sys.stdin.read()}))
' <<< "$ORIENT"
