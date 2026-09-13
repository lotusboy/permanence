#!/usr/bin/env bash
# perma-help.sh — what this Permanence can do, and what is actually switched on.
#
# Deterministic and free: it reads the INSTALLED commands' own `description:` frontmatter and probes
# the live machine, so it cannot drift as commands are added, removed or renamed. A command with no
# group mapping still appears (under "Other"), so nothing silently goes missing.
set -uo pipefail
PERMA="${PERMA_DIR:-$HOME/permanence}"
CMDS="$HOME/.claude/commands"
SETTINGS="$HOME/.claude/settings.json"

on()  { printf '  \033[32m✅\033[0m %s\n' "$1"; }
off() { printf '  \033[90m○\033[0m  %s\n' "$1"; }

# --- description for an installed command (first line of its frontmatter description) -------------
# A description containing a bare "word: " (e.g. "Trigger phrases: ...", "Pub/sub: ...") has to be
# YAML double-quoted in the frontmatter — a plain scalar can't hold that unambiguously. desc() and
# triggers() below unwrap that one layer of quoting/escaping so the extracted text stays plain either
# way; they never do full YAML parsing, just enough to match how these files are actually written.
desc() {
  local f="$CMDS/$1.md" d
  [ -f "$f" ] || return 1
  d="$(awk -F': *' '/^description:/{sub(/^description: */,""); print; exit}' "$f")"
  d="${d#\"}"           # drop a leading quote, if the value was YAML-quoted
  d="${d//\\\"/\"}"     # unescape \" back to " now that we're not YAML-parsing
  # trim to the first sentence, drop any trailing "Trigger phrases:" clause
  d="${d%%Trigger phrases:*}"
  d="${d%% — *}"
  printf '%s' "${d%%.*}"
}

triggers() {
  local f="$CMDS/$1.md" t
  [ -f "$f" ] || return 0
  t="$(sed -n 's/.*Trigger phrases: *\(.*\)/\1/p' "$f" | head -1)"
  t="${t//\\\"/\"}"     # unescape \" back to "
  t="${t%\"}"           # drop a trailing quote, if the value was YAML-quoted
  printf '%s' "$t"
}

show() {  # show <command> [override blurb]
  local c="$1" blurb="${2:-}" t
  [ -f "$CMDS/$c.md" ] || return 0
  [ -n "$blurb" ] || blurb="$(desc "$c")"
  t="$(triggers "$c")"
  if [ -n "$t" ]; then printf '  \033[1m/%s\033[0m — %s  \033[90m(or: %s)\033[0m\n' "$c" "$blurb" "${t%.}"
  else printf '  \033[1m/%s\033[0m — %s\n' "$c" "$blurb"; fi
  SEEN="$SEEN $c"
}

hook_has() { [ -f "$SETTINGS" ] && python3 - "$SETTINGS" "$1" <<'PY' 2>/dev/null
import json,sys
try: d=json.load(open(sys.argv[1]))
except Exception: sys.exit(1)
needle=sys.argv[2]
sys.exit(0 if any(needle in h.get("command","") for v in d.get("hooks",{}).values()
                  for e in v for h in e.get("hooks",[])) else 1)
PY
}
# Cross-platform: checks whichever backend schedule-task.sh actually used for this OS.
# No pipe on the launchd branch: `launchctl list | grep -q` looks right but lies under `pipefail` —
# grep exits on the first match, launchctl takes SIGPIPE, and the pipeline reports failure. That
# reported loaded jobs as off.
job_loaded() {
  case "$(uname -s)" in
    Darwin)
      local out; out="$(launchctl list 2>/dev/null)"
      case "$out" in *"com.$(id -un).$1"*) return 0;; *) return 1;; esac ;;
    Linux)
      crontab -l 2>/dev/null | grep -qF "# $1" ;;
    MINGW*|MSYS*|CYGWIN*)
      MSYS_NO_PATHCONV=1 schtasks /Query /TN "$1" >/dev/null 2>&1 ;;
    *) return 1 ;;
  esac
}

SEEN=""
printf '\n\033[1m🧠 What this Permanence can do\033[0m   \033[90m(%s)\033[0m\n' "$PERMA"

printf '\n\033[1mDaily rhythm\033[0m\n'
show perma-startup  "this project: where you left off + a couple of next-task options"
show perma-brief    "all streams: the cross-project morning briefing"
show perma-shutdown "wind-down: today's open loops out of your head and into the stream"

printf '\n\033[1mKeeping it honest\033[0m\n'
show perma-consolidate        "read-only tidy pass — writes a report, changes nothing"
show perma-consolidate-review "walk that report, decide each item, apply what you accept"
show perma-contents           "regenerate the file inventory"
show perma-orchestrate        "find ideas converging across streams you had not connected"

printf '\n\033[1mSetting things up\033[0m\n'
show perma-register       "turn a project into a Permanence stream"
show perma-unregister     "completely remove a stream — folder + registry row, one step"
show perma-register-group "several repos → one shared programme folder (plan + RAG status)"
show perma-upgrade         "pull the latest machinery from your team template"

printf '\n\033[1mFinding and talking\033[0m\n'
show perma-list   "every registered stream — name, what it is, when it moved, its path"
show perma-emit   "send a note to another project's Claude"

# anything installed that no group above claimed
for f in "$CMDS"/perma-*.md; do
  [ -f "$f" ] || continue
  c="$(basename "$f" .md)"
  case " $SEEN " in *" $c "*) ;; *) [ -z "${OTHER_HDR:-}" ] && { printf '\n\033[1mOther\033[0m\n'; OTHER_HDR=1; }; show "$c";; esac
done

printf '\n\033[1mRunning in the background\033[0m\n'
job_loaded perma-consolidate     && on "nightly consolidate (05:30) — writes a report for you to review" \
                                 || off "nightly consolidate — not loaded"
job_loaded perma-shutdown-nudge  && on "weekday nudge to run /perma-shutdown — $PERMA/runtime/shutdown-nudge.sh --uninstall to stop" \
                                 || off "weekday /perma-shutdown nudge — off ($PERMA/runtime/shutdown-nudge.sh --install 17:00)"
hook_has session-start.sh        && on "session-start hook — loads the right stream when you open a project" \
                                 || off "session-start hook — not wired"
hook_has session-load.sh         && on "auto context-load on your first prompt (no need to say 'refer to Permanence')" \
                                 || off "auto context-load — not wired"
if hook_has events-listen.sh || hook_has stop-listen.sh; then
  hook_has events-listen.sh && on "cross-project events: delivered on your next prompt" || off "cross-project events: next-prompt delivery not wired"
  hook_has stop-listen.sh   && on "cross-project events: also caught mid-turn, before a session goes idle" || off "cross-project events: mid-turn catch not wired"
else
  off "cross-project events — receiving is off (emitting still works)"
fi
[ -s "$PERMA/runtime/.update-source" ] && on "/perma-upgrade source set — $(tr -d '[:space:]' < "$PERMA/runtime/.update-source")" \
                                      || off "/perma-upgrade — no source set, so it exits immediately (put your template repo URL in runtime/.update-source)"

printf '\n\033[1mReporting outward\033[0m  \033[90m(plan + RAG status for someone outside the work)\033[0m\n'
python3 - "$PERMA" <<'PY'
import os, re, sys
perma = sys.argv[1]
p = os.path.join(perma, "_meta", "GROUPS.md")
G, B, D = "\033[32m✅\033[0m", "\033[1m", "\033[90m"
R, O = "\033[0m", "\033[90m○\033[0m "
if not os.path.exists(p):
    print(f"  {O} no _meta/GROUPS.md — programme reporting is off (optional; /perma-register-group sets it up){R}")
    raise SystemExit
def cells(l): return [c.strip().strip("`") for c in l.strip().strip("|").split("|")]
def real(c):  # ignore header rows and the shipped illustrative rows
    return c and not c[0].lower().startswith(("group", "#")) \
       and "example-programme" not in c[0] and not any("/Users/you" in x for x in c)
# Track which table we're in. Cell count can't discriminate: a Membership row (group|path|role|joined|
# left) and a Groups row (group|target|folder|task doc) can both present 4-5 cells, so counting made
# members overwrite the group.
groups, members, table = {}, {}, None
for l in open(p):
    s = l.strip()
    if s.lower().startswith("## group"):      table = "g"; continue
    if s.lower().startswith("## membership"): table = "m"; continue
    if s.startswith("##"):                    table = None; continue
    if not s.startswith("|") or re.match(r"^\|\s*-", s): continue
    c = cells(s)
    if not real(c) or len(c) < 3 or not c[1].startswith("/"): continue
    if table == "g":   groups[c[0]] = (c[1], c[2])
    elif table == "m": members.setdefault(c[0], []).append((c[2], (c[4] if len(c) > 4 else "").strip()))
if not groups and not members:
    print(f"  {O} no programme groups configured yet — /perma-register-group to set one up{R}")
else:
    for g in sorted(set(list(groups) + list(members))):
        tgt, folder = groups.get(g, ("?", "?"))
        cur = [r for r, lf in members.get(g, []) if not lf]
        gone = [r for r, lf in members.get(g, []) if lf]
        print(f"  {G} {B}{g}{R} — {len(cur)} current: {', '.join(cur) or 'none'}"
              + (f"  {D}(left: {', '.join(gone)}){R}" if gone else ""))
        print(f"     folder: {D}{os.path.join(tgt, folder) if tgt != '?' else 'unknown'}{R}")
    print(f"     {D}a goodnight in any member repo refreshes the whole folder — it converges{R}")
PY

printf '\n\033[1mHolding the day together\033[0m  \033[90m(externalised memory, time anchors, re-entry points)\033[0m\n'
printf '  the /perma-startup ↔ /perma-shutdown bookends, the weekday nudge above,\n'
printf '  and "remind me at …" for stopping times, meetings and breaks.\n'
printf '  The point: the loops come back when you want them, not at 11pm.\n'

streams=$(find "$PERMA" -mindepth 2 -maxdepth 3 -name PROJECT.md -not -path '*/.git/*' 2>/dev/null | wc -l | tr -d ' ')
printf '\n\033[90m%s streams · %s commands · full reference: %s/SPEC.md\033[0m\n\n' \
  "$streams" "$(ls -1 "$CMDS"/perma-*.md 2>/dev/null | wc -l | tr -d ' ')" "$PERMA"
