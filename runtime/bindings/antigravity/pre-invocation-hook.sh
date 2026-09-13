#!/bin/bash
# antigravity/pre-invocation-hook.sh — the forcing-read + passive-orientation mechanism for
# Antigravity (SPEC.md §3's binding contract, questions 1+2). Antigravity has no separate
# SessionStart-equivalent event, so this one hook carries both jobs, matching SPEC.md §3's
# "forcing subsumes passive" — confirmed for this binding by live testing, not assumed
# (design/antigravity-binding.md §3.1).
#
# PreInvocation fires more than once per turn (invocationNum 0, 1, ... within a single exchange,
# live-confirmed) — this needs a once-per-conversation cursor, keyed on conversationId, the same
# role /tmp/.perma-loaded-<session-id> plays for Claude Code's own session-load.sh.
PERMA="${PERMA_DIR:-$HOME/permanence}"
[ -d "$PERMA" ] || { echo '{}'; exit 0; }

INPUT="$(cat 2>/dev/null)"

CONV_ID="$(printf '%s' "$INPUT" | python3 -c '
import json, sys
try: d = json.load(sys.stdin)
except Exception: d = {}
print(d.get("conversationId") or "noconv")
' 2>/dev/null)"
[ -n "$CONV_ID" ] || CONV_ID="noconv"

if [ "$CONV_ID" != "noconv" ]; then
  MARKER="/tmp/.perma-loaded-agy-$(printf '%s' "$CONV_ID" | tr -c 'A-Za-z0-9' _)"
  if [ -f "$MARKER" ]; then
    echo '{}'
    exit 0
  fi
  touch "$MARKER"
fi

# Translate Antigravity's payload (workspacePaths[]) into the "cwd" field session-start.sh and
# session-load.sh already expect from Claude Code's own hook contract — reuses their existing
# stream-resolution logic (via resolve-stream.sh) rather than reimplementing it here. CLI usage
# needs an explicit --add-dir for workspacePaths to be populated at all; the GUI IDE populates it
# automatically (design/antigravity-binding.md §3.5, live-tested both ways).
PAYLOAD="$(printf '%s' "$INPUT" | python3 -c '
import json, sys
try: d = json.load(sys.stdin)
except Exception: d = {}
paths = d.get("workspacePaths") or []
print(json.dumps({"cwd": paths[0] if paths else ""}))
' 2>/dev/null)"
[ -n "$PAYLOAD" ] || PAYLOAD="{}"

ORIENT="$(printf '%s' "$PAYLOAD" | PERMA_DIR="$PERMA" bash "$PERMA/runtime/session-start.sh" 2>/dev/null)"
LOAD="$(printf '%s' "$PAYLOAD" | PERMA_DIR="$PERMA" bash "$PERMA/runtime/session-load.sh" 2>/dev/null)"

MESSAGE="$(printf '%s\n%s\n' "$ORIENT" "$LOAD" | sed '/^[[:space:]]*$/d')"

if [ -z "$MESSAGE" ]; then
  echo '{}'
  exit 0
fi

python3 -c '
import json, sys
print(json.dumps({"injectSteps": [{"ephemeralMessage": sys.stdin.read()}]}))
' <<< "$MESSAGE"
