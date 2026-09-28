#!/bin/bash
# Permanence session-start: emits context for the Claude Code SessionStart hook.
# All logic lives here, in Permanence — the hook entry in settings.json is just this path.
# Output contract: short instructions (the session then Reads the files itself);
# never dump file contents into context from here.

PERMA="${PERMA_DIR:-$HOME/permanence}"

[ -d "$PERMA" ] || exit 0   # no Permanence on this machine — stay silent

# cwd: read the SessionStart hook's own JSON payload on stdin — Claude Code's hooks guide
# documents `cwd` as a common field on every hook event, the same one session-load.sh (the
# UserPromptSubmit hook) reads. Reading that SAME field, rather than this script independently
# computing its own `pwd -P`, is what actually guarantees the two hooks agree: under a symlinked
# workspace they previously could (and did, on testing) disagree, leaving one session with
# contradictory registration status from its own two hooks in the same turn.
INPUT="$(cat 2>/dev/null)"
CWD="$(printf '%s' "$INPUT" | python3 -c '
import json,sys
try: d=json.load(sys.stdin)
except Exception: d={}
print(d.get("cwd") or "")
' 2>/dev/null)"
[ -n "$CWD" ] || CWD="$(pwd -P)"   # no JSON / no python3 — fall back to the old physical-path behavior

# --- consolidation lock check (writer-side guard, hardening item 4) ---
LOCK="$PERMA/.perma-lock"
if [ -f "$LOCK" ]; then
  NOW=$(date +%s)
  LOCK_TS=$(head -n1 "$LOCK" 2>/dev/null)
  case "$LOCK_TS" in (*[!0-9]*|"") LOCK_TS=0;; esac
  AGE_MIN=$(( (NOW - LOCK_TS) / 60 ))
  if [ "$AGE_MIN" -gt 240 ]; then
    echo "[perma] STALE consolidation lock: .perma-lock is ${AGE_MIN}m old (>4h limit). Tell the owner; it is safe to remove after confirming no consolidation review is genuinely running."
  else
    echo "[perma] CONSOLIDATION IN PROGRESS: .perma-lock present (${AGE_MIN}m old). Do not edit, commit, or branch in ~/permanence until it is released — read-only access is fine."
  fi
fi

# --- registry lookup: delegate to resolve-stream.sh rather than re-parsing REGISTRY.md here.
#     This file used to carry its own independent copy of the same longest-prefix parser — a fix
#     to the shared one (trailing-slash handling, malformed-row rejection) would have silently
#     missed this, the one path every session actually goes through first.
BEST_STREAM="$("$PERMA/runtime/resolve-stream.sh" "$CWD" 2>/dev/null)"

if [ -z "$BEST_STREAM" ]; then
  # Is this a container folder rather than a project? A session opened without its working folder set
  # lands in $HOME, and registering THAT as a stream is the classic wrong turn: every home-defaulted
  # session then loads a meaningless "stream" and the wind-down starts writing state into it. So for
  # these paths, never offer registration — tell them to point the session at the project instead.
  case "$CWD" in
    "$HOME"|"$HOME"/|/|/Users|/home|"$HOME"/Desktop|"$HOME"/Documents|"$HOME"/Downloads)
      echo "[perma] This session's working folder is $CWD — a home/container folder, not a project. Perma-meta is available (/perma-brief, /perma-contents). Do NOT offer to register this path as a stream: set the session's working folder to the project's own folder first, then register that. If the owner asks to register, explain this rather than proceeding."
      exit 0
      ;;
  esac
  echo "[perma] This workspace ($CWD) is NOT registered in ~/permanence/_meta/REGISTRY.md. Perma-meta remains available (/perma-brief, /perma-contents full). If this looks like real project work, offer the owner ONCE to register it (one row: path -> stream; new stream folders need at least README/PROJECT/LOG per ~/permanence/README.md). Do not load any customer stream content unprompted."
  exit 0
fi

# --- role (v1.5.0): an optional standing role for Claude, chosen per install ---
# runtime/.role holds one line: `none` (or no file at all) = no role, exactly as before v1.5.0;
# `pm` = the shipped runtime/roles/pm.md; anything else = a path to the owner's own role file.
# PERMA_ROLE overrides the file, as PERMA_UPDATE_SOURCE does for .update-source. The template never
# ships a .role file, so an owner's choice is theirs and survives every upgrade untouched.
# Output stays within this script's contract: one short pointer line, never the role file's contents.
role_lines() {  # role_lines <dir-whose-WIP.md-to-mention>
  local role file
  role="${PERMA_ROLE:-$(grep -v '^[[:space:]]*$' "$PERMA/runtime/.role" 2>/dev/null | head -n1 | tr -d '[:space:]')}"
  # shellcheck disable=SC2088  # the "~/"* branch below deliberately matches a literal "~/"
  # prefix stored in .role (a config value, not a shell word) and expands it via $HOME itself.
  case "$role" in
    ""|none) return 0 ;;
    pm)      file="$PERMA/runtime/roles/pm.md" ;;
    "~/"*)   file="$HOME/${role#\~/}" ;;
    *)       file="$role" ;;
  esac
  if [ ! -f "$file" ]; then
    echo "[perma] runtime/.role names a role file that does not exist ($file) — no role applied. Tell the owner once."
    return 0
  fi
  echo "[perma] ROLE: read $file now and follow it for the whole session — the owner chose this role for Claude in runtime/.role."
  [ -f "$1/WIP.md" ] && echo "[perma] This workspace's working board is $1/WIP.md."
  return 0
}

if [ "$BEST_STREAM" = "perma-meta" ]; then
  echo "[perma] Perma-meta context (this workspace matched a perma-meta row in the registry). No customer stream loads here. /perma-brief, /perma-consolidate, /perma-orchestrate, /perma-contents are available; Permanence root is ~/permanence."
  role_lines "$PERMA/_meta"
  exit 0
fi

STREAM_DIR="$PERMA/$BEST_STREAM"
echo "[perma] Registered stream for this workspace: $BEST_STREAM ($STREAM_DIR)"
echo "[perma] At session start, read the stream's operational files now: PROJECT.md and QUESTIONS.md, plus STRATEGY.md / PEOPLE.md if present, and the most recent entries of LOG.md (tail, not full history)."
echo "[perma] Standing rule: this stream is the owner's externalised working memory. Update it whenever something material shifts (meetings, decisions, scope changes, Slack exchanges that move the picture) — without being asked. Never copy Permanence content or paths into team-facing artefacts or project repos (one-way flow). Anything persisted to Permanence is written in a gentle, accurate register."
role_lines "$STREAM_DIR"
exit 0
