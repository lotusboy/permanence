#!/bin/bash
# Nightly read-only /perma-consolidate (hardening item 3), run by launchd
# (the launchd plist install.sh generates — installed by install.sh).
# Generation is pure analysis: it writes only a report under ~/permanence/.consolidation/ (gitignored).
# The scoped --allowedTools list below is the "scoped permission profile" — the run is
# unattended, so it gets read access + report-write + git log, and nothing else.

export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
# Load Claude auth. launchd's bash sources no shell config, so the token must be loaded explicitly —
# this was the cause of the prior 401s. Checked in order; the first file that exists is sourced.
# Keeping the token in its own file (rather than the global shell env) stops it leaking into VS Code
# and shadowing Claude Code's own login.
#   1. $PERMA_TOKEN_ENV                                  — explicit override, set it to any path
#   2. ~/.config/perma/claude-code-oauth-token.env        — the documented default
#   3. ~/.zshenv                                          — legacy fallback (grepped, not sourced)
for _tok in "${PERMA_TOKEN_ENV:-}" \
            "$HOME/.config/perma/claude-code-oauth-token.env"; do
  # shellcheck disable=SC1090
  [ -n "$_tok" ] && [ -f "$_tok" ] && { . "$_tok"; break; }
done
[ -z "${CLAUDE_CODE_OAUTH_TOKEN:-}" ] && [ -f "$HOME/.zshenv" ] && \
  eval "$(grep -E '^[[:space:]]*export (CLAUDE_CODE_OAUTH_TOKEN|ANTHROPIC_AUTH_TOKEN|ANTHROPIC_BASE_URL)=' "$HOME/.zshenv")"
# Permanence runs on your Claude CODE SUBSCRIPTION, never an API key. This loads a subscription/OAuth
# token only — generate one with `claude setup-token` (→ CLAUDE_CODE_OAUTH_TOKEN). It deliberately does
# NOT load ANTHROPIC_API_KEY (keep any API key for other tools; Permanence never uses it).
PERMA="${PERMA_DIR:-$HOME/permanence}"
LOG_DIR="$PERMA/runtime/logs"; mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/nightly-consolidate.log"

note() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$LOG"; }

# Best-effort failure alert via the events outbox — so a failure surfaces in the next session you open,
# instead of being buried in a log nobody reads. Emitted as source "nightly" (not a real stream) so every
# open session surfaces it and none is skipped by the no-echo rule. No-ops harmlessly if events aren't
# enabled. Guarded with || true: a failed alert must never mask the original error.
alert() {
  [ -x "$PERMA/runtime/emit-event.sh" ] && \
    PERMA_EMIT_SOURCE="nightly" "$PERMA/runtime/emit-event.sh" all "$1" >/dev/null 2>&1 || true
}

CLAUDE_BIN="$(command -v claude)"
if [ -z "$CLAUDE_BIN" ]; then note "ERROR: claude CLI not found on PATH"; alert "Nightly consolidate FAILED: claude CLI not on PATH. See runtime/logs/nightly-consolidate.log."; exit 1; fi
if [ ! -d "$PERMA/.git" ]; then note "ERROR: ~/permanence is not a git repo"; exit 1; fi

# Pre-flight auth assert — a missing subscription token is a HARD STOP, never a reason to use an API key.
# Makes the failure loud + unambiguous instead of letting claude attempt an unauthenticated run.
if [ -z "$CLAUDE_CODE_OAUTH_TOKEN" ] && [ -z "$ANTHROPIC_AUTH_TOKEN" ]; then
  note "ERROR: no Claude subscription token loaded (CLAUDE_CODE_OAUTH_TOKEN empty) — ABORTING. Will NOT fall back to an API key. FIX: run 'claude setup-token', then save the token as a single line — export CLAUDE_CODE_OAUTH_TOKEN=<token> — in ~/.config/perma/claude-code-oauth-token.env (or set PERMA_TOKEN_ENV to wherever you keep it)."
  alert "Nightly consolidate ABORTED $(date '+%Y-%m-%d'): no Claude subscription token loaded — it will NOT use an API key. FIX: run 'claude setup-token', then put 'export CLAUDE_CODE_OAUTH_TOKEN=<token>' in ~/.config/perma/claude-code-oauth-token.env (chmod 600)."
  exit 78
fi

# Respect the consolidation lock: a live review owns Permanence right now — UNLESS it's stale.
# The lock is only taken and released by a MODEL following prompt instructions
# (perma-consolidate-review.md), not by anything mechanical; a crash, Ctrl-C, or context
# exhaustion between those two steps leaves it in place forever, and a bare `exit 0` here would
# then silently disable this job every night, indefinitely, with nothing surfaced anywhere. That
# is exactly the "silent-green is worse than a loud failure" principle this script states for
# itself a few lines below the artefact-assert further down — applied here too. Same 240-minute
# staleness threshold session-start.sh already uses for the same lock file.
if [ -f "$PERMA/.perma-lock" ]; then
  LOCK_TS=$(head -n1 "$PERMA/.perma-lock" 2>/dev/null)
  case "$LOCK_TS" in (*[!0-9]*|"") LOCK_TS=0;; esac
  AGE_MIN=$(( ($(date +%s) - LOCK_TS) / 60 ))
  if [ "$AGE_MIN" -gt 240 ]; then
    note "SKIPPED: .perma-lock present but STALE (${AGE_MIN}m old, >4h) — most likely a consolidation review crashed or was interrupted without releasing it. Not removed automatically."
    alert "Nightly consolidate SKIPPED $(date '+%Y-%m-%d'): .perma-lock is ${AGE_MIN}m old (stale, >4h) — every future night will keep skipping until this is resolved. Check whether a /perma-consolidate-review is genuinely still running; if not, it is safe to remove ~/permanence/.perma-lock."
  else
    note "SKIPPED: .perma-lock present (${AGE_MIN}m old, within the 4h window) — a review is genuinely in progress."
  fi
  exit 0
fi

# ── Awake gate ───────────────────────────────────────────────────────────────────────────────
# Wait until the machine is genuinely IN USE before starting, and skip the day if it never is.
#
# WHY: launchd fires on schedule regardless of what the Mac is doing. At that moment it may be in
# a Power Nap dark wake rather than properly awake. A run started in a dark wake gets a few minutes
# before the machine sleeps again; every fanned-out subagent then stalls mid-analysis and the parent
# retries each one on the next wake. That is exactly what happened on 16 September: 32 agent runs to
# complete 5 of 16 streams, and no report written at all — double the spend for no artefact. Six of
# the seven runs from 10-16 September produced no report.
#
# HOW: HIDIdleTime is nanoseconds since the last keyboard or trackpad input. Nobody types during a
# dark wake, so it climbs; a machine being worked at reads seconds. That makes it a better "safe to
# start" signal than any power-state probe, because it answers "is a human here to keep this awake"
# rather than merely "is the CPU executing right now".
#
# The poll loop doubles as the sleep-waiter. A sleeping Mac suspends this process entirely and
# resumes it on wake, so one `sleep 60` spans the whole nap and the next check lands after the
# machine is back. Nothing needs to schedule a wake or detect one.
AWAKE_IDLE_MAX=600        # seconds since last input that still counts as "in use"
AWAKE_DEADLINE_MIN=180    # give up and skip the day if still not in use after this long

_idle_seconds() {
  # Absolute path: ioreg lives in /usr/sbin, which is NOT on the PATH this script sets for launchd.
  # A bare `ioreg` worked in an interactive shell and failed under launchd — which blocked every
  # run from 16 to 22 September, each logged as "machine not in use".
  /usr/sbin/ioreg -c IOHIDSystem 2>/dev/null |
    awk -F'= ' '/HIDIdleTime/ {print int($2/1000000000); exit}'
}

GATE_UNTIL=$(( $(date +%s) + AWAKE_DEADLINE_MIN * 60 ))
GATE_WAITED=0
while :; do
  IDLE="$(_idle_seconds)"
  # Unreadable idle time must mean "do not start", never "start anyway" — a broken probe should
  # cost a skipped day, not another stalled 32-agent run.
  case "$IDLE" in (*[!0-9]*|"") IDLE=999999;; esac
  [ "$IDLE" -le "$AWAKE_IDLE_MAX" ] && break
  if [ "$(date +%s)" -ge "$GATE_UNTIL" ]; then
    if [ "$IDLE" -eq 999999 ]; then
      note "ERROR: the awake gate could not read idle time (/usr/sbin/ioreg returned nothing) for ${AWAKE_DEADLINE_MIN}m — the probe is broken, not the machine idle. No run started."
      alert "Nightly consolidate BLOCKED $(date '+%Y-%m-%d'): the awake gate cannot read idle time, so it will skip every day until fixed. See runtime/logs/nightly-consolidate.log."
      exit 1
    fi
    note "SKIPPED: machine not in use in the ${AWAKE_DEADLINE_MIN}m after the scheduled start (idle ${IDLE}s) — declined to start a run that would stall on sleep. Nothing is wrong; the next attempt is tomorrow's schedule."
    alert "Nightly consolidate SKIPPED $(date '+%Y-%m-%d'): the laptop was not in use during the ${AWAKE_DEADLINE_MIN}-minute window after its scheduled start, so no report was written today. This is the awake gate working as intended, not a failure."
    exit 0
  fi
  [ "$GATE_WAITED" -eq 0 ] && note "waiting: machine idle ${IDLE}s — holding until it is in use (deadline ${AWAKE_DEADLINE_MIN}m)"
  GATE_WAITED=1
  sleep 60
done
[ "$GATE_WAITED" -eq 1 ] && note "resumed: machine in use again (idle ${IDLE}s) — starting"

note "run start"
cd "$PERMA" || exit 1

# Marker for the artefact assert below: any REPORT written by THIS run is newer than this file.
MARKER="$(mktemp "${TMPDIR:-/tmp}/perma-consolidate.marker.XXXXXX")"
mkdir -p "$PERMA/.consolidation"

# --allowedTools entries are matched as LITERAL PREFIXES, so a granted "$HOME/permanence" path can never
# match a command the model writes as "~/permanence" (and the bare "git log:*" fallback misses too, because
# the command begins "git -C"). Headless there is nobody to approve the prompt, so the call is simply
# denied and the model gives up. Grant all THREE spellings of every path: the two literal ones plus
# "$PERMA" itself — the first two alone silently broke any install using PERMA_DIR to point somewhere
# other than $HOME/permanence, since neither literal matches a custom location.
#
# File writes are scoped to .consolidation/ ONLY — this pass is documented (SPEC.md,
# perma-consolidate.md) as read-only except for its own report file, and an unscoped grant would let
# an unattended, nobody-watching run touch anything, not just its report. Same three-spelling reason
# as the Bash grants below.
#
# The rule MUST be spelled Edit(path), not Write(path). File-permission checks only evaluate
# Edit(...) rules, and an Edit rule covers every file-editing tool (Write, Edit, NotebookEdit). A
# Write(path) rule grants the tool NAME but its path spec is silently ignored, so the write falls
# through to a prompt — and headless there is nobody to approve it. That is exactly what broke the
# 10, 11 and 12 September runs: all three analysed fine, then could not save the report.
# The 12 September run fanned out to three background analysis agents, hit the default 600s wait
# ceiling, and was terminated mid-flight before it could assemble the report. The documented escape
# is CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0 (wait indefinitely) — but this is an unattended launchd
# job with no `timeout` on macOS to bound it, so an indefinite wait risks a job that never returns.
# 30 minutes is generous for a fan-out over ~14 streams and still guarantees the run ends.
export CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=1800000

# caffeinate -i holds off IDLE sleep for the duration of the run. The gate above already proved a
# human was present when this started; this covers them walking away mid-run. It deliberately does
# NOT try to fight a closed lid — nothing in userspace can, which is why the gate exists at all.
#
# Checked explicitly, with its own distinct log/alert line, rather than letting a missing
# `caffeinate` fall through as a plain nonzero exit from this whole pipeline: the generic handler
# below (`RC -ne 0`) says "most likely the subscription token expired" — actively wrong and
# misleading for this specific cause, sending the owner to re-authenticate when the real fix is
# unrelated. Found by adversarial review, 2026-09-28
# (axis/runs/2026-09-28-v1.5.0-update-sh-review), live-reproduced (RC 127, generic message fired).
if ! command -v caffeinate >/dev/null 2>&1; then
  note "ERROR: caffeinate not found on PATH — cannot hold off idle sleep for this run, so it did not start"
  alert "Nightly consolidate did NOT run on $(date '+%Y-%m-%d') — caffeinate is not on PATH (macOS-only tool; check PATH or the machine itself). NOT a token/auth problem. Log: runtime/logs/nightly-consolidate.log."
  exit 69
fi

caffeinate -i "$CLAUDE_BIN" -p "/perma-consolidate" \
  --permission-mode default --model sonnet \
  --allowedTools "Read" "Glob" "Grep" \
    "Edit($PERMA/.consolidation/*)" "Edit($HOME/permanence/.consolidation/*)" "Edit(~/permanence/.consolidation/*)" \
    "Bash(git -C $PERMA log:*)" "Bash(git -C $HOME/permanence log:*)" "Bash(git -C ~/permanence log:*)" "Bash(git log:*)" \
    "Bash(date:*)" "Bash(ls:*)" \
    "Bash(mkdir -p $PERMA/.consolidation:*)" "Bash(mkdir -p $HOME/permanence/.consolidation:*)" "Bash(mkdir -p ~/permanence/.consolidation:*)" \
  >> "$LOG" 2>&1
RC=$?

# Assert the ARTEFACT, not just the exit code. A denied tool makes the model give up while `claude`
# still exits 0 — which used to be logged as "run complete" with no report written. The morning brief
# then saw an empty .consolidation/ and read it as "nothing to do", when it meant "nothing ran".
# Silent-green is worse than a loud failure, so an absent report is now an error in its own right.
NEW_REPORT="$(find "$PERMA/.consolidation" -maxdepth 1 -name 'REPORT-*.md' -newer "$MARKER" -print -quit 2>/dev/null)"
rm -f "$MARKER"

if [ $RC -ne 0 ]; then
  note "ERROR: run failed (exit $RC)"
  alert "Nightly consolidate FAILED (exit $RC) on $(date '+%Y-%m-%d'). NOT an API-key fallback — most likely the subscription token expired; re-run 'claude setup-token'. Log: runtime/logs/nightly-consolidate.log."
  exit $RC
elif [ -z "$NEW_REPORT" ]; then
  note "ERROR: run exited 0 but wrote NO report to .consolidation/ — treating as a failure. Most likely a tool call was denied (check the log for permission errors); the model cannot work and gives up while still exiting 0."
  alert "Nightly consolidate produced NO REPORT on $(date '+%Y-%m-%d') despite exiting 0 — almost certainly a denied tool call, so nothing actually ran. An empty .consolidation/ means NOT-RUN, not caught-up. Log: runtime/logs/nightly-consolidate.log."
  exit 70
else
  note "run complete (exit 0) — wrote $(basename "$NEW_REPORT")"
  exit 0
fi
