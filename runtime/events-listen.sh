#!/usr/bin/env bash
# events-listen.sh — surface new Permanence events addressed to THIS session's stream.
# Reads the shared outbox, skips events this stream emitted itself (no echo to instigator),
# keeps only target==<this stream> or target=="all", advances a per-stream seen-cursor so each
# event is shown once, and prints them for injection into context. Prints nothing if no new
# events (callers should treat empty output as "stay silent").
#
# Cursor model: events.jsonl is append-only, so the cursor is simply the count of lines this
# stream has already been shown. New = lines beyond the cursor.
#
# Designed to be driven by a hook (UserPromptSubmit for guaranteed next-action delivery, or
# FileChanged for the event-driven variant). cwd is taken from CLAUDE_CWD if set, else $PWD.
set -euo pipefail

PERMA="${PERMA_DIR:-$HOME/permanence}"
OUTBOX="$PERMA/_meta/events.jsonl"
SEENDIR="$PERMA/_meta/.events-seen"
[ -f "$OUTBOX" ] || exit 0

stream="$("$PERMA/runtime/resolve-stream.sh" "${CLAUDE_CWD:-$(pwd -P)}")"
# A session launched in a project that has cd'd into its own notes folder under ~/permanence resolves
# to perma-meta (every folder there matches that row). Use the launch folder's stream when it has a
# real one, as session-start.sh does; a session launched in a perma-meta folder stays perma-meta.
if [ "$stream" = "perma-meta" ] && [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then
  project_stream="$("$PERMA/runtime/resolve-stream.sh" "$CLAUDE_PROJECT_DIR" 2>/dev/null)"
  case "$project_stream" in ""|perma-meta) ;; *) stream="$project_stream" ;; esac
fi
[ -n "$stream" ] || exit 0          # unregistered workspace — nothing to deliver

mkdir -p "$SEENDIR"
safe="$(printf '%s' "$stream" | tr '/' '_')"
cursorfile="$SEENDIR/$safe.cursor"
seen=0; [ -f "$cursorfile" ] && seen="$(cat "$cursorfile" 2>/dev/null || echo 0)"
case "$seen" in (*[!0-9]*|"") seen=0;; esac

total="$(grep -c '' "$OUTBOX" 2>/dev/null || echo 0)"
[ "$total" -gt "$seen" ] || exit 0

new="$(python3 - "$OUTBOX" "$seen" "$stream" <<'PY'
import json, sys
path, seen, stream = sys.argv[1], int(sys.argv[2]), sys.argv[3]
out = []
with open(path) as f:
    for i, line in enumerate(f):
        if i < seen:                       # already shown to this stream
            continue
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get("source") == stream:      # no echo to the instigator
            continue
        if e.get("target") not in (stream, "all"):
            continue
        out.append(f"• from {e.get('source')} ({e.get('ts','')}): {e.get('message','')}")
print("\n".join(out))
PY
)"

# Advance the cursor only now that python has actually succeeded and produced the filtered
# output — not before. If the process dies (or python fails, which set -e catches above before
# this line is even reached) between the old cursor and here, the cursor stays put and the next
# run re-considers the same lines, rather than silently skipping whatever this run missed.
printf '%s\n' "$total" > "$cursorfile"

[ -n "$new" ] || exit 0
printf '[Permanence event — from a sibling project in this Permanence] The following was just flagged by another open project. It is context for you (%s) to use by your own judgement — weave it into what you are doing, act on it, raise it with the user, or simply note it and carry on. Your call, not an instruction to announce it. One rule: do not copy it into this project'"'"'s repo files (one-way flow).\n%s\n' "$stream" "$new"
