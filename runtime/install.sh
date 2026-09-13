#!/bin/bash
# Bind Permanence's runtime to this machine's Claude Code harness (hardening item 5 / F2).
# Idempotent — run after clone, after pulling runtime changes, or any time to verify.
# Copy-on-install (NOT symlinks): installed copies carry a version marker; symlinked
# commands would track whatever ref the working tree has checked out.

set -u
PERMA="${PERMA_DIR:-$HOME/permanence}"
CMD_SRC="$PERMA/runtime/commands"
CMD_DST="$HOME/.claude/commands"
SHA=$(git -C "$PERMA" rev-parse --short HEAD 2>/dev/null || echo "unversioned")

# Tracks whether a step that matters actually succeeded, so the final line can say so honestly.
# Without this, install.sh printed "done." unconditionally — a failed cp, an unparseable
# settings.json, or a missing python3 all left the install silently incomplete while reporting
# success. Not every possible failure in this script is caught (a full `set -e` audit was judged
# riskier — several lines here rely on an expected, harmless failure via `2>/dev/null` or `||`,
# and blanket -e risks a NEW silent-abort mode instead of fixing this one); this covers the two
# concrete cases most likely to leave hooks unwired: the command copy and the settings.json write.
INSTALL_FAILED=0

echo "Permanence install — runtime @ $SHA"

# 1. Commands: copy with version marker appended
mkdir -p "$CMD_DST"
for f in "$CMD_SRC"/*.md; do
  name=$(basename "$f")
  if cp "$f" "$CMD_DST/$name"; then
    printf '\n<!-- installed-from: ~/permanence/runtime/commands/%s @ %s — edit the source in Permanence, then re-run ~/permanence/runtime/install.sh -->\n' "$name" "$SHA" >> "$CMD_DST/$name"
    echo "  command: $name"
  else
    echo "  command: $name — FAILED to copy"
    INSTALL_FAILED=1
  fi
done

# 2. Executable bits + git hooks path (re-run needed once after any re-clone)
chmod +x "$PERMA/runtime/"*.sh "$PERMA/.githooks/"* "$PERMA/runtime/bindings/"*/detect "$PERMA/runtime/bindings/"*/wire 2>/dev/null
git -C "$PERMA" config core.hooksPath .githooks
echo "  hooks: core.hooksPath=.githooks (pre-commit people-guard + post-commit contents refresh)"

# 3. Scheduled tasks — cross-platform via schedule-task.sh (launchd/cron/schtasks, per OS)
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

# 4. CLAUDE.md + AGENTS.md: manage ONLY the delimited Permanence block, never the rest of a
#    file we don't own. `_perma_block_merge` (runtime/lib/block-merge.sh) is the one place that
#    splices into someone else's file, so it carries the safety net there: refuse to touch a
#    mismatched begin/end pair (writing through one would delete everything after it) and back up
#    before any in-place replace.
source "$PERMA/runtime/lib/block-merge.sh"

CMD_MD="$HOME/.claude/CLAUDE.md"
BLOCK_SRC="$PERMA/runtime/claude-md-block.md"
if _perma_block_merge "$CMD_MD" "$BLOCK_SRC"; then
  echo "  CLAUDE.md: Permanence block refreshed"
fi

# 4b. AGENTS.md (Tier 2 — other AI tools): same delimited-block merge, into GLOBAL per-machine
#     paths ONLY — never a project-committed AGENTS.md, which invariant 1 forbids (that file is
#     meant to be shared with every contributor). Only touches a tool's config path if that tool's
#     own config directory already exists (real signal it's installed) — never invents one. The
#     emerging unifying standard path is written unconditionally since it's dedicated to exactly
#     this purpose, not a directory shared by unrelated tools.
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
# then they fall back to the manual pointer (see docs/TOOL-SUPPORT.md).

# 5. settings.json: safely MERGE the SessionStart hook + ~/permanence permission
#    (add only if absent; preserve everything else; back up before writing).
SETTINGS="$HOME/.claude/settings.json"
if command -v python3 >/dev/null 2>&1; then
  if ! python3 - "$SETTINGS" "$PERMA" <<'PY'
import json, sys, os, shutil
path, perma = sys.argv[1], sys.argv[2]
os.makedirs(os.path.dirname(path), exist_ok=True)
data = {}
if os.path.exists(path):
    try:
        data = json.load(open(path))
    except Exception:
        print("  settings.json: present but unparseable — NOT touched. Add the hook + permission by hand.")
        sys.exit(1)
cmd = f"{perma}/runtime/session-start.sh"
changed = False
ad = data.setdefault("permissions", {}).setdefault("additionalDirectories", [])
if perma not in ad:
    ad.append(perma); changed = True
ss = data.setdefault("hooks", {}).setdefault("SessionStart", [])
present = any(isinstance(e, dict) and any(h.get("command") == cmd for h in e.get("hooks", [])) for e in ss)
if not present:
    ss.append({"hooks": [{"type": "command", "command": cmd, "timeout": 10}]}); changed = True
# UserPromptSubmit: session-load — RELIABLE per-session context auto-load (SessionStart context is
# passive; this fires on the user's first prompt so the model actually reads the stream). Core, so
# auto-wired (unlike events, which is opt-in).
cmd_load = f"{perma}/runtime/session-load.sh"
ups = data.setdefault("hooks", {}).setdefault("UserPromptSubmit", [])
if not any(isinstance(e, dict) and any(h.get("command") == cmd_load for h in e.get("hooks", [])) for e in ups):
    ups.insert(0, {"hooks": [{"type": "command", "command": cmd_load, "timeout": 10}]}); changed = True
if changed:
    if os.path.exists(path): shutil.copy(path, path + ".perma-bak")
    json.dump(data, open(path, "w"), indent=2)
    print("  settings.json: SessionStart + session-load (auto context) hooks + ~/permanence permission merged in (backup: settings.json.perma-bak)")
else:
    print("  settings.json: hook + permission already present")
PY
  then
    echo "  settings.json: FAILED to configure automatically — add the hook + permission by hand (see message above)"
    INSTALL_FAILED=1
  fi
else
  cat <<SETTINGS
  settings.json: python3 not found — add these by hand to ~/.claude/settings.json (MERGE, don't overwrite):
      "permissions": { "additionalDirectories": ["$PERMA"] },
      "hooks": {
        "SessionStart": [ { "hooks": [ { "type": "command", "command": "$PERMA/runtime/session-start.sh", "timeout": 10 } ] } ],
        "UserPromptSubmit": [ { "hooks": [ { "type": "command", "command": "$PERMA/runtime/session-load.sh", "timeout": 10 } ] } ]
      }
SETTINGS
fi

# 6. Optional harness bindings — any AI tool beyond Claude Code that has a
#    runtime/bindings/<harness>/ directory. Each subdirectory is self-contained: its own detect
#    script decides whether it applies to this machine, its own wire script does the actual
#    merge. install.sh knows nothing about any specific harness here — adding one is a new
#    directory, not an edit to this file. See design/harness-binding-mechanism.md.
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

# 7. Events (cross-project notifications) — OPT-IN. The scripts (emit-event / events-listen /
#    stop-listen / resolve-stream) + the /perma-emit command are installed by steps 1-2. *Emitting*
#    works now; *receiving* uses two machine-wide hooks we DON'T auto-wire (your call):
#      • UserPromptSubmit → events-listen.sh  — delivers waiting messages on a session's next prompt
#      • Stop            → stop-listen.sh     — catches messages that land mid-turn, right as a session
#                                               would go idle (blocks the stop so it reads them). FREE:
#                                               a local file read; costs a turn only when there IS a message.
#    Both share one per-stream cursor, so each message is delivered exactly once across them.
echo "  events: scripts + /perma-emit installed. To ENABLE delivery (opt-in), add BOTH to ~/.claude/settings.json hooks:"
echo "      \"UserPromptSubmit\": [ { \"hooks\": [ { \"type\": \"command\", \"command\": \"$PERMA/runtime/events-listen.sh\", \"timeout\": 10 } ] } ],"
echo "      \"Stop\":             [ { \"hooks\": [ { \"type\": \"command\", \"command\": \"$PERMA/runtime/stop-listen.sh\",  \"timeout\": 10 } ] } ]"

# 8. Shutdown nudge (macOS) — OPT-IN. A weekday end-of-day notification reminding you to run
#    /perma-shutdown. Not installed automatically (a desktop ping is a personal choice).
echo "  shutdown nudge: to get a weekday reminder to run /perma-shutdown, enable it:"
echo "      $PERMA/runtime/shutdown-nudge.sh --install 17:00   (change the time, or --uninstall to remove)"

if [ "$INSTALL_FAILED" -eq 0 ]; then
  echo "done."
else
  echo "done, WITH FAILURES — see the lines above marked FAILED. Fix those, then re-run install.sh (safe to re-run any time)."
fi
