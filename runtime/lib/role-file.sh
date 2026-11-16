#!/usr/bin/env bash
# role-file.sh — sourced, never run directly. The one place Permanence reads runtime/.role, so the
# file a session loads (session-start.sh) and the file the install run checks (install.sh) can never
# differ.
#
# runtime/.role holds one line: `none` (or no file at all) = no role; `pm` = the shipped
# runtime/roles/pm.md; anything else = a path to the owner's own role file. PERMA_ROLE overrides the
# file, as PERMA_UPDATE_SOURCE does for .update-source.

# The moved names (v1.13.1): the project team's tools, which moved to bakehouse in v1.12.0. A role
# file of the owner's own, written before then, can still tell every session to use them.
# `role:` stands for the old `role:<name>` dispatch, so it only counts when a name follows it.
# One line, spaces only: awk -v takes no newline.
_PERMA_MOVED_NAMES='decision.sh spend.sh ratify.sh save-report.sh predict-gate.sh health-signal'
_PERMA_MOVED_NAMES="$_PERMA_MOVED_NAMES ops-event.sh ops-gap.sh repo-hooks.sh agent-roles role:"
_PERMA_MOVED_NAMES="$_PERMA_MOVED_NAMES /perma-change /perma-refactor /perma-health absence-check"
_PERMA_MOVED_NAMES="$_PERMA_MOVED_NAMES count-check blast-radius dev-team step-back live-prism"
_PERMA_MOVED_NAMES="$_PERMA_MOVED_NAMES PROJECT-TEAM.md PREDICT-GATE.md"

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
  local file
  file="$(_perma_role_file)"
  # No role, the shipped role, or a missing file (session-start.sh already says so each session).
  [ -n "$file" ] && [ "$file" != "$PERMA/runtime/roles/pm.md" ] && [ -f "$file" ] && [ -r "$file" ] || return 0
  # One awk pass prints "<name>\t<line numbers>" for each moved name the file mentions. A mention
  # written as `bakehouse:<name>` is the new home, so it does not count.
  # shellcheck disable=SC2016  # the awk program is single-quoted on purpose
  awk -v names="$_PERMA_MOVED_NAMES" '
    function strip(s, p,   i, out) { out = ""; while ((i = index(s, p)) > 0) { out = out substr(s, 1, i - 1); s = substr(s, i + length(p)) } return out s }
    BEGIN { n = split(names, N, " ") }
    {
      for (k = 1; k <= n; k++) {
        line = strip($0, "bakehouse:" N[k])
        hit = (N[k] == "role:") ? match(line, /role:[^ \t]/) : index(line, N[k])
        if (hit) L[k] = (k in L) ? L[k] ", " NR : NR
      }
    }
    END { for (k = 1; k <= n; k++) if (k in L) printf "%s\t%s\n", N[k], L[k] }
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
