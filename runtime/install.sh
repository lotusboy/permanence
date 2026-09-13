#!/bin/bash
# Bind Permanence's runtime to this machine's AI-harness bindings.
# Idempotent — run after clone, after pulling runtime changes, or any time to verify.

set -u
PERMA="${PERMA_DIR:-$HOME/permanence}"
SHA=$(git -C "$PERMA" rev-parse --short HEAD 2>/dev/null || echo "unversioned")

# Tracks whether a step that matters actually succeeded, so the final line can say so honestly.
# Without this, install.sh printed "done." unconditionally — an unparseable settings.json or a
# broken harness-binding wire script all left the install silently incomplete while reporting
# success. Not every possible failure in this script is caught (a full `set -e` audit was judged
# riskier — several lines here rely on an expected, harmless failure via `2>/dev/null` or `||`,
# and blanket -e risks a NEW silent-abort mode instead of fixing this one); this covers the
# concrete cases most likely to leave hooks unwired.
INSTALL_FAILED=0

echo "Permanence install — runtime @ $SHA"

# 1. Executable bits + git hooks path (re-run needed once after any re-clone)
chmod +x "$PERMA/runtime/"*.sh "$PERMA/.githooks/"* "$PERMA/runtime/bindings/"*/detect "$PERMA/runtime/bindings/"*/wire 2>/dev/null
git -C "$PERMA" config core.hooksPath .githooks
echo "  hooks: core.hooksPath=.githooks (pre-commit people-guard + post-commit contents refresh)"

# 2. Scheduled tasks — cross-platform via schedule-task.sh (launchd/cron/schtasks, per OS)
mkdir -p "$PERMA/runtime/logs"
source "$PERMA/runtime/schedule-task.sh"
# $PERMA is embedded here inside its own literal double-quotes ("$PERMA"), not bare — this
# string is re-parsed as a shell command line a second time, by launchd/cron/schtasks, once the
# scheduled job actually fires. A bare, unquoted $PERMA containing a space (a real macOS
# possibility — "/Users/Anna Smith") word-splits at that second parse: launchd tried to run
# "/Users/Anna" as the command with "Smith/permanence/..." as its argument, confirmed by running
# it. Embedding the quote characters now is what survives that second parse.
schedule_task "perma-consolidate" "\"$PERMA\"/runtime/nightly-consolidate.sh >> \"$PERMA\"/runtime/logs/nightly-consolidate.log 2>&1" "daily 05:30"

# Cognitive-debt scan removed (v1.2.0) — nothing here can reschedule it anymore, so clean up a
# job an earlier install may have left behind. Gated on a job actually existing so this stays
# silent for everyone who never had it (the common case going forward).
if [ -n "$(_existing_job_command "perma-cogdebt" 2>/dev/null)" ]; then
  echo "  cogdebt scan: no longer supported, removing its scheduled job"
  unschedule_task "perma-cogdebt"
fi

# 3. AGENTS.md (other AI tools that read it — Claude Code has its own binding, step 4 below):
#    the same delimited-block merge, into GLOBAL per-machine paths ONLY — never a project-
#    committed AGENTS.md, which invariant 1 forbids (that file is meant to be shared with every
#    contributor). Only touches a tool's config path if that tool's own config directory already
#    exists (real signal it's installed) — never invents one. The emerging unifying standard path
#    is written unconditionally since it's dedicated to exactly this purpose, not a directory
#    shared by unrelated tools. `_perma_block_merge` (runtime/lib/block-merge.sh) is the one
#    place that splices into someone else's file, so it carries the safety net there: refuse to
#    touch a mismatched begin/end pair (writing through one would delete everything after it) and
#    back up before any in-place replace.
source "$PERMA/runtime/lib/block-merge.sh"
AGENTS_BLOCK_SRC="$PERMA/runtime/agents-md-block.md"
merge_agents_block() {  # merge_agents_block <target-file>
  local dst="$1"
  _perma_block_merge "$dst" "$AGENTS_BLOCK_SRC" && echo "  AGENTS.md: Permanence block refreshed at $dst"
}
merge_agents_block "$HOME/.config/agents/AGENTS.md"                 # emerging unifying standard — always
[ -d "$HOME/.codex" ]   && merge_agents_block "$HOME/.codex/AGENTS.md"    # OpenAI Codex, if installed
[ -d "$HOME/.factory" ] && merge_agents_block "$HOME/.factory/AGENTS.md" # droid, if installed
[ -f "$HOME/.config/AGENTS.md" ] && merge_agents_block "$HOME/.config/AGENTS.md"  # Amp, if it already exists
# Devin's and Google Antigravity's own global-config paths weren't confirmed at time of writing —
# verify and add here before relying on automatic Tier 2 coverage for those specifically; until
# then they fall back to the manual pointer (see docs/TOOL-SUPPORT.md). (Antigravity has its own
# real binding now — see runtime/bindings/antigravity/ — this note is about the generic
# AGENTS.md-only fallback other, not-yet-bound tools get.)

# 4. AI-harness bindings — every runtime/bindings/<harness>/ directory, Claude Code included:
#    its own detect script decides whether it applies to this machine, its own wire script does
#    the actual merge. install.sh knows nothing about any specific harness here — adding one is a
#    new directory, not an edit to this file. See design/harness-binding-mechanism.md.
for b in "$PERMA/runtime/bindings/"*/; do
  [ -d "$b" ] || continue
  name="$(basename "$b")"
  [ -x "$b/detect" ] || continue
  if "$b/detect" >/dev/null 2>&1; then
    if [ -x "$b/wire" ] && "$b/wire"; then
      echo "  binding: $name wired"
    elif [ -x "$b/wire" ]; then
      echo "  binding: $name — FAILED to wire (see above)"
      INSTALL_FAILED=1
    else
      echo "  binding: $name detected, no wire script yet"
    fi
  fi
done

# 5. Events (cross-project notifications) — OPT-IN. The scripts (emit-event / events-listen /
#    stop-listen / resolve-stream) + the /perma-emit command are installed by Claude Code's own
#    binding above. *Emitting* works now; *receiving* uses two machine-wide hooks we DON'T
#    auto-wire (your call):
#      • UserPromptSubmit → events-listen.sh  — delivers waiting messages on a session's next prompt
#      • Stop            → stop-listen.sh     — catches messages that land mid-turn, right as a session
#                                               would go idle (blocks the stop so it reads them). FREE:
#                                               a local file read; costs a turn only when there IS a message.
#    Both share one per-stream cursor, so each message is delivered exactly once across them.
echo "  events: scripts + /perma-emit installed. To ENABLE delivery (opt-in), add BOTH to ~/.claude/settings.json hooks:"
echo "      \"UserPromptSubmit\": [ { \"hooks\": [ { \"type\": \"command\", \"command\": \"$PERMA/runtime/events-listen.sh\", \"timeout\": 10 } ] } ],"
echo "      \"Stop\":             [ { \"hooks\": [ { \"type\": \"command\", \"command\": \"$PERMA/runtime/stop-listen.sh\",  \"timeout\": 10 } ] } ]"

# 6. Shutdown nudge (macOS) — OPT-IN. A weekday end-of-day notification reminding you to run
#    /perma-shutdown. Not installed automatically (a desktop ping is a personal choice).
echo "  shutdown nudge: to get a weekday reminder to run /perma-shutdown, enable it:"
echo "      $PERMA/runtime/shutdown-nudge.sh --install 17:00   (change the time, or --uninstall to remove)"

if [ "$INSTALL_FAILED" -eq 0 ]; then
  echo "done."
else
  echo "done, WITH FAILURES — see the lines above marked FAILED. Fix those, then re-run install.sh (safe to re-run any time)."
fi
