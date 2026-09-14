#!/bin/bash
# cursor/stop-hook.sh — the standing-instruction fix. Live-fire confirmed 2026-09-14, interactive
# mode only: forcing an extra turn via `stop`'s followup_message causes a genuine, unprompted
# stream write, reversing seven straight negatives from context-injection approaches
# (sessionStart alone, a stronger wording, postToolUse reinforcement — see
# design/cursor-binding.md §3.3). Confirmed separately, and still true: this hook never fires at
# all in headless (`-p`) mode, so this fix only reaches interactive Cursor use — the normal way
# most people actually use it day to day, not an edge case.
#
# Gated on loop_count == 0 so this fires once per real user turn, not on the follow-up turn it
# itself triggers — an ungated version re-triggered itself indefinitely during live testing.
PERMA="${PERMA_DIR:-$HOME/permanence}"
[ -d "$PERMA" ] || { echo '{}'; exit 0; }

INPUT="$(cat 2>/dev/null)"
LOOP_COUNT="$(printf '%s' "$INPUT" | python3 -c '
import json, sys
try: d = json.load(sys.stdin)
except Exception: d = {}
print(d.get("loop_count", 0))
' 2>/dev/null)"
[ -n "$LOOP_COUNT" ] || LOOP_COUNT=0

if [ "$LOOP_COUNT" != "0" ]; then
  echo '{}'
  exit 0
fi

CWD="$(printf '%s' "$INPUT" | python3 -c '
import json, sys
try: d = json.load(sys.stdin)
except Exception: d = {}
roots = d.get("workspace_roots") or []
print(roots[0] if roots else "")
' 2>/dev/null)"
[ -n "$CWD" ] || CWD="$PWD"

STREAM="$(PERMA_DIR="$PERMA" bash "$PERMA/runtime/resolve-stream.sh" "$CWD" 2>/dev/null)"

if [ -z "$STREAM" ] || [ "$STREAM" = "perma-meta" ]; then
  echo '{}'
  exit 0
fi

STREAM_DIR="$PERMA/$STREAM"
python3 -c '
import json, sys
stream_dir = sys.argv[1]
msg = (
    "Before finishing: if anything material shifted in this conversation (a decision, a scope "
    "change, a fact worth remembering), update " + stream_dir + "/PROJECT.md and/or " + stream_dir +
    "/LOG.md now, using a real shell command, then confirm in one line what you wrote. If nothing "
    "material came up, just say so in one line."
)
print(json.dumps({"followup_message": msg}))
' "$STREAM_DIR"
