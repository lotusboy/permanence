#!/usr/bin/env bash
# stop-listen.sh — Stop hook. When a Claude finishes a turn and would go idle, surface any NEW Permanence
# events addressed to THIS session's stream that arrived DURING the turn, and block the stop so the
# model reads/acts on them instead of falling idle unaware. The twin of events-listen.sh (which
# fires on the next user prompt): together they close the gap where a sibling's message lands mid-turn.
#
# Cost: a pure local file read — costs a model turn ONLY when there's genuinely a new message.
# Shares the per-stream cursor with events-listen.sh, so each message is delivered exactly once
# across both hooks.
#
# Loop-safety: a Stop hook receives a JSON object on stdin (incl. `stop_hook_active`) and may print
# {"decision":"block","reason":...} to keep the turn going. We NEVER block when stop_hook_active is
# true, and we advance the cursor whenever we surface — so the same message can never re-block.
# One-way flow: events reach context only, never the repo files.
set -euo pipefail
PERMA="${PERMA_DIR:-$HOME/permanence}"
OUTBOX="$PERMA/_meta/events.jsonl"
SEENDIR="$PERMA/_meta/.events-seen"
[ -f "$OUTBOX" ] || exit 0

input="$(cat 2>/dev/null || true)"
read -r STOP_ACTIVE CWD < <(printf '%s' "$input" | python3 -c '
import json,sys,os
try: d=json.load(sys.stdin)
except Exception: d={}
print("true" if d.get("stop_hook_active") else "false", d.get("cwd") or os.environ.get("CLAUDE_CWD") or os.environ.get("PWD",""))
' 2>/dev/null || echo "false ")
[ "$STOP_ACTIVE" = "true" ] && exit 0        # already continuing due to a stop hook — never chain-block
[ -n "${CWD:-}" ] || CWD="$(pwd -P)"

stream="$("$PERMA/runtime/resolve-stream.sh" "$CWD" 2>/dev/null)"
# A session launched in a project that has cd'd into its own notes folder under ~/permanence resolves
# to perma-meta (every folder there matches that row). Use the launch folder's stream when it has a
# real one, as session-start.sh does; a session launched in a perma-meta folder stays perma-meta.
if [ "$stream" = "perma-meta" ] && [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then
  project_stream="$("$PERMA/runtime/resolve-stream.sh" "$CLAUDE_PROJECT_DIR" 2>/dev/null)"
  case "$project_stream" in ""|perma-meta) ;; *) stream="$project_stream" ;; esac
fi
[ -n "$stream" ] || exit 0                    # unregistered workspace
[ "$stream" = "perma-meta" ] && exit 0        # brief-level session — surface on next prompt, don't block its stop

mkdir -p "$SEENDIR"
safe="$(printf '%s' "$stream" | tr '/' '_')"
cursorfile="$SEENDIR/$safe.cursor"
seen=0; [ -f "$cursorfile" ] && seen="$(cat "$cursorfile" 2>/dev/null || echo 0)"
case "$seen" in (*[!0-9]*|"") seen=0;; esac
total="$(grep -c '' "$OUTBOX" 2>/dev/null || echo 0)"

new="$(python3 - "$OUTBOX" "$seen" "$stream" <<'PY'
import json, sys
path, seen, stream = sys.argv[1], int(sys.argv[2]), sys.argv[3]
out=[]
with open(path) as f:
    for i,line in enumerate(f):
        if i < seen: continue
        line=line.strip()
        if not line: continue
        try: e=json.loads(line)
        except Exception: continue
        if e.get("source")==stream: continue                 # no echo to the instigator
        if e.get("target") not in (stream,"all"): continue
        out.append(f"• from {e.get('source')} ({e.get('ts','')}): {e.get('message','')}")
print("\n".join(out))
PY
)"

printf '%s\n' "$total" > "$cursorfile"        # considered everything up to total — advance either way
[ -n "$new" ] || exit 0

python3 - "$stream" "$new" <<'PY'
import json,sys
stream,new=sys.argv[1],sys.argv[2]
reason=("[Permanence event — from a sibling project] New message(s) arrived for you ("+stream+") during this turn. "
        "Read and act on them now rather than going idle unaware — reply via /perma-emit if warranted, or note and continue. "
        "Do not copy them into this project's repo files (one-way flow).\n"+new)
print(json.dumps({"decision":"block","reason":reason}))
PY
