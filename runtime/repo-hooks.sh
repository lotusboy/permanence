#!/usr/bin/env bash
# repo-hooks.sh [repo ...] — write the ops-ledger post-commit hook into each repository the owner owns.
# Called by the Claude Code binding's wire; safe to run on its own. With arguments, only those
# repositories are considered (each must still qualify below).
#
# A repository qualifies when _meta/REGISTRY.md maps it to a stream whose repo/binding.json says
# "owned": true. Another party's repository never gets a hook: its commits are not the owner's to log
# (docs/PROJECT-TEAM.md, "Ownership").
#
# The hook goes in the repository's local hooks folder, which git never commits, so no committed
# file changes (SPEC §2 invariant 1). It is recognised by its marker line. A hook without the marker
# is never overwritten: it is reported and the repository is skipped. A repository that sets
# core.hooksPath is reported and skipped, because git then ignores the local hooks folder.
#
# Exit: 0 when every qualifying repository was written or deliberately skipped; 1 on a write error.
set -u
command -v python3 >/dev/null 2>&1 || { echo "$(basename "$0"): python3 not found on PATH — this tool needs it (standard library only)." >&2; exit 127; }
PERMA="${PERMA_DIR:-$HOME/permanence}"
MARKER="# installed-by: permanence runtime/repo-hooks.sh"
FAILED=0

owned_repos() {
  python3 - "$PERMA" <<'PY'
import json, os, sys
perma = sys.argv[1]
for line in open(os.path.join(perma, "_meta", "REGISTRY.md"), encoding="utf-8"):
    cells = [c.strip() for c in line.strip().split("|")]
    if len(cells) < 4 or not line.lstrip().startswith("|") or not cells[1].startswith("/"):
        continue
    binding = os.path.join(perma, cells[2], "repo", "binding.json")
    try:
        if json.load(open(binding)).get("owned") is True:
            print(cells[1].rstrip("/"))
    except (OSError, ValueError, AttributeError):
        pass
PY
}

ONLY=("$@")
MATCHED=()
while IFS= read -r repo; do
  [ -n "$repo" ] || continue
  if [ ${#ONLY[@]} -gt 0 ]; then
    hit=0
    for o in "${ONLY[@]}"; do
      if [ "$(cd "$o" 2>/dev/null && pwd -P)" = "$repo" ]; then hit=1; MATCHED+=("$o"); fi
    done
    [ $hit = 1 ] || continue
  fi
  if ! git -C "$repo" rev-parse --git-dir >/dev/null 2>&1; then
    echo "  repo hook: $repo — not a git repository here; skipped"
    continue
  fi
  if hp="$(git -C "$repo" config --get core.hooksPath)"; then
    echo "  repo hook: $repo — sets core.hooksPath ($hp), so git ignores .git/hooks; skipped"
    continue
  fi
  hooks="$(git -C "$repo" rev-parse --path-format=absolute --git-path hooks)"
  hook="$hooks/post-commit"
  if [ -e "$hook" ] || [ -L "$hook" ]; then
    if ! grep -qF "$MARKER" "$hook" 2>/dev/null; then
      echo "  repo hook: $repo — post-commit exists and was not written by Permanence; left alone, skipped"
      continue
    fi
  fi
  mkdir -p "$hooks"
  # Never write through a symlink: replace our own hook, whatever it is, with a plain file.
  rm -f "$hook"
  if cat > "$hook" <<HOOK
#!/bin/sh
$MARKER
# Reports how far the owner's ops ledger has drifted behind this repository's commits. Reports only:
# never blocks, never writes. Rewritten by wire; delete this file to remove it.
[ -x "$PERMA/runtime/ops-gap.sh" ] && "$PERMA/runtime/ops-gap.sh" 5 2>/dev/null
exit 0
HOOK
  then
    chmod +x "$hook"
    echo "  repo hook: $repo — post-commit written"
  else
    echo "  repo hook: $repo — FAILED to write $hook"
    FAILED=1
  fi
done < <(owned_repos)
for o in ${ONLY[@]+"${ONLY[@]}"}; do
  found=0
  for m in ${MATCHED[@]+"${MATCHED[@]}"}; do [ "$m" = "$o" ] && found=1; done
  [ $found = 1 ] || echo "  repo hook: $o — not registered to a stream whose binding says owned: true; skipped"
done
exit "$FAILED"
