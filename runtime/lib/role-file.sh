#!/usr/bin/env bash
# role-file.sh — sourced, never run directly. The one place Permanence resolves runtime/.role to a
# file, so the file a session loads (session-start.sh) and the file the install run checks
# (install.sh) can never differ.
#
# runtime/.role holds one line: `none` (or no file at all) = no role; `pm` = the shipped
# runtime/roles/pm.md; anything else = a path to the owner's own role file. PERMA_ROLE overrides the
# file, as PERMA_UPDATE_SOURCE does for .update-source.

# The moved names (v1.13.1): what v1.12.0 deleted from Permanence when the project team moved to
# bakehouse (`git diff --diff-filter=D v1.11.0 v1.12.0`). A role file of the owner's own, written
# before then, can still tell every session to use them. Each tool is listed in its .sh and .py
# forms. Left out: `architect`, the one agent whose name is a common word. `role:` stands for the
# old `role:<name>` dispatch (a lowercase name right after the colon); the matcher treats it apart.
# One line, spaces only: awk -v takes no newline.
_PERMA_MOVED_NAMES='decision.sh decision.py spend.sh spend.py ratify.sh ratify.py'
_PERMA_MOVED_NAMES="$_PERMA_MOVED_NAMES save-report.sh save-report.py predict-gate.sh predict-gate.py"
_PERMA_MOVED_NAMES="$_PERMA_MOVED_NAMES health-signal ops-event.sh ops-gap.sh repo-hooks.sh agent-roles agent-roles-hook"
_PERMA_MOVED_NAMES="$_PERMA_MOVED_NAMES agents-install team-preflight team_roles role:"
_PERMA_MOVED_NAMES="$_PERMA_MOVED_NAMES perma-change perma-refactor perma-health"
_PERMA_MOVED_NAMES="$_PERMA_MOVED_NAMES absence-check count-check blast-radius design-author design-reviewer"
_PERMA_MOVED_NAMES="$_PERMA_MOVED_NAMES human-expert refactor-engineer refactor-reviewer"
_PERMA_MOVED_NAMES="$_PERMA_MOVED_NAMES dev-team step-back live-prism PROJECT-TEAM.md PREDICT-GATE.md"

_perma_role_file() {  # prints the role file's path, or nothing when there is no role
  local role
  role="${PERMA_ROLE:-$(grep -v '^[[:space:]]*$' "$PERMA/runtime/.role" 2>/dev/null | head -n1)}"
  # Trim the ends only. Before v1.13.1 every space was deleted, so a path holding one never loaded.
  role="$(printf '%s' "$role" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')"
  # shellcheck disable=SC2088  # the "~/"* branch below deliberately matches a literal "~/"
  # prefix stored in .role (a config value, not a shell word) and expands it via $HOME itself.
  case "$role" in
    ""|none) return 0 ;;
    pm)      printf '%s\n' "$PERMA/runtime/roles/pm.md" ;;
    "~/"*)   printf '%s\n' "$HOME/${role#\~/}" ;;
    /*)      printf '%s\n' "$role" ;;
    *)       # A bare relative value (e.g. "roles/custom.md", by analogy with the shipped "pm" ->
             # runtime/roles/pm.md convention) resolves against $PERMA/runtime, where "pm" itself
             # resolves, never against the cwd of whichever process reads it (for the SessionStart
             # hook that is the project workspace, so it silently never resolved). Found by
             # adversarial review, 2026-09-28, live-reproduced.
             printf '%s\n' "$PERMA/runtime/$role" ;;
  esac
}

_perma_role_check() {  # install.sh: warn when the owner's own role file names a moved tool. Read-only.
  local file size
  file="$(_perma_role_file)"
  # No role, the shipped role, or a missing file (session start already says so).
  [ -n "$file" ] && [ "$file" != "$PERMA/runtime/roles/pm.md" ] && [ -f "$file" ] && [ -r "$file" ] || return 0
  # A role file is a few hundred lines. A .role that points at something huge by mistake is not
  # read, so it cannot slow the install.
  size=$(wc -c < "$file" 2>/dev/null | tr -d ' ')
  if [ "${size:-0}" -gt 1048576 ]; then
    echo "  role file: $file is over 1 MB, so it was not checked for the tools that moved to bakehouse."
    return 0
  fi
  # One awk pass prints "<name>\t<line numbers>" for each moved name the file mentions. A name counts
  # only as a whole word: the character before it is not a letter, digit, _, . or -, and the one after
  # it is not a letter, digit, _ or -. A mention written as `bakehouse:<name>` is the new home, so it
  # does not count. At most 10 line numbers are listed per name.
  # shellcheck disable=SC2016  # the awk program is single-quoted on purpose
  awk -v names="$_PERMA_MOVED_NAMES" '
    function strip(s, p,   i, out) { out = ""; while ((i = index(s, p)) > 0) { out = out substr(s, 1, i - 1); s = substr(s, i + length(p)) } return out s }
    function word(s, t,   i, pos, b, a) {
      pos = 0
      while ((i = index(substr(s, pos + 1), t)) > 0) {
        pos += i
        b = (pos > 1) ? substr(s, pos - 1, 1) : ""
        a = substr(s, pos + length(t), 1)
        if (b !~ /[A-Za-z0-9_.-]/ && a !~ /[A-Za-z0-9_-]/) return 1
      }
      return 0
    }
    BEGIN { n = split(names, N, " ") }
    {
      for (k = 1; k <= n; k++) {
        line = strip($0, "bakehouse:" N[k])
        hit = (N[k] == "role:") ? match(" " line, /[^A-Za-z0-9_]role:[a-z][a-z0-9-]*/) : word(line, N[k])
        if (!hit) continue
        C[k]++
        if (C[k] <= 10) L[k] = (k in L) ? L[k] ", " NR : NR
      }
    }
    END {
      for (k = 1; k <= n; k++) if (k in L) {
        label = (N[k] == "role:") ? "a role:<name> dispatch" : N[k]
        more = (C[k] > 10) ? sprintf(" and %d more", C[k] - 10) : ""
        printf "%s\t%s%s\n", label, L[k], more
      }
    }
  ' "$file" 2>/dev/null | {
    found=0
    while IFS="$(printf '\t')" read -r name lines; do
      [ -n "$name" ] || continue
      found=1
      echo "  role file: ATTENTION — $name, line(s) $lines"
    done
    if [ "$found" -eq 1 ]; then
      echo "  role file: ATTENTION — your role file ($file) still refers to tools that moved to bakehouse; edit it, or point those parts at the \`bakehouse:pm\` skill, or switch runtime/.role to pm. Permanence never edits it."
    fi
  }
  return 0
}
