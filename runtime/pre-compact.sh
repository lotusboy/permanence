#!/usr/bin/env bash
# Permanence pre-compact (PreCompact hook) — a record of each compaction, and the summary's instructions.
# ---------------------------------------------------------------------------------
# Two jobs, before Claude Code compacts a conversation (by /compact or automatically):
#   1. Append one line to ~/.claude/compaction-log.txt: time (UTC), trigger, session id, folder. When a
#      session feels like a fresh start, the log says whether a compaction really happened.
#   2. Print standing instructions for the compaction summary. Claude Code uses this hook's stdout as
#      instructions for the summary (docs: https://code.claude.com/docs/en/hooks, "PreCompact output").
#      runtime/.compact-instructions (plain text), when it has any text, is printed instead of the
#      default below. The docs ask for under 10,000 characters per hook, so longer text is cut to fit.
# Permanence's SessionStart hook re-loads the stream after a compaction, so the summary need not carry
# what the stream files already hold.
#
# Plain bash: no jq, no python3. Fail silent: it always exits 0 (exit 2 would block the compaction).
PERMA="${PERMA_DIR:-$HOME/permanence}"
input="$(cat 2>/dev/null)"
# One string field from the hook's one-line JSON, kept to safe characters (trigger and session_id are
# plain words and ids).
field() {
  printf '%s' "$input" | sed -n "s/.*\"$1\"[[:space:]]*:[[:space:]]*\"\([^\"]*\)\".*/\1/p" | head -n1 | tr -cd 'A-Za-z0-9._-'
}
TRIGGER="$(field trigger)"
SESSION="$(field session_id)"
TS="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
printf '%s  trigger=%s  session=%s  cwd=%s\n' "$TS" "${TRIGGER:-unknown}" "${SESSION:-unknown}" "$(pwd -P)" \
  2>/dev/null >> "$HOME/.claude/compaction-log.txt"   # stderr first: a failed open stays silent

OWN="$(cat "$PERMA/runtime/.compact-instructions" 2>/dev/null)"
if [ -n "$(printf '%s' "$OWN" | tr -d '[:space:]')" ]; then
  printf '%s\n' "${OWN:0:9998}"   # 9,998 + the newline: under 10,000
else
  cat <<'EOF'
Keep: the task in progress and its step status; every open decision and who owns it; branch names,
commit ids and counts exactly as written; anything the owner said to do or not do.
List separately: anything decided or done in this conversation that is not yet written to the
stream files, so it is written down first after the compaction.
Drop: tool output and file contents (they can be re-read). Work from the stream files, not this summary.
EOF
fi
exit 0
