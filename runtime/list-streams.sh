#!/bin/bash
# list-streams.sh — the one list of Permanence's streams (v1.13.3). Every command and script that
# needs "every stream" reads it here, so they can never disagree again.
#
# The definition (SPEC.md, README.md): a folder is a stream exactly when it has a PROJECT.md.
#   - perma-meta, Permanence's own stream, is always listed first, as `perma-meta`. Its folder is
#     `_meta` (its log is the root LOG.md). `_meta` is never listed a second time under its own name.
#   - Hidden folders (.git, .consolidation, ...) are never searched.
#   - A REGISTRY.md row does not make a stream: the registry links workspaces to streams, and a
#     notes-only stream has no workspace at all.
#   - Symlinked folders are not followed (find without -L, so a link to a large tree cannot slow
#     every command). A registered stream reached only through a symlink shows up in --check.
#   - A folder name holding a tab or a newline is not supported.
#
# Usage:
#   list-streams.sh          one line per stream: <name><TAB><folder, relative to ~/permanence>
#   list-streams.sh --count  the number of streams, perma-meta not counted
#   list-streams.sh --check  each stream a REGISTRY.md row names, for a workspace that exists on this
#                            machine, that is not in the list, one per line; no other command will
#                            see it until its folder has a PROJECT.md. A row for a workspace not on
#                            this machine (another laptop's, or the template's example row) is skipped.
# Read-only. Prints nothing, and exits 0, when ~/permanence is missing.

PERMA="${PERMA_DIR:-$HOME/permanence}"
[ -d "$PERMA" ] || exit 0

streams() {  # stream folders, relative to $PERMA, sorted; the root _meta left out
  (cd "$PERMA" && find . \( -name '.*' ! -name . \) -prune -o -name PROJECT.md -type f -print 2>/dev/null) \
    | sed 's|^\./||;s|/PROJECT\.md$||' | grep -v -x -e '_meta' -e 'PROJECT.md' | LC_ALL=C sort
}

case "${1:-}" in
  --count)
    streams | grep -c .
    ;;
  --check)
    reg="$PERMA/_meta/REGISTRY.md"
    [ -f "$reg" ] || exit 0
    listed="$(streams)"
    # Same row rule as resolve-stream.sh: a row starts with "|" and its first cell is a path.
    while IFS= read -r line; do
      trimmed="${line#"${line%%[![:space:]]*}"}"
      case "$trimmed" in ('|'*) ;; (*) continue ;; esac
      IFS='|' read -r _ ws stream _ <<< "$line"
      ws=$(printf '%s' "$ws" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
      stream=$(printf '%s' "$stream" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
      case "$ws" in (/*) ;; (*) continue ;; esac
      case "$ws" in (?*/) ws="${ws%/}" ;; esac
      [ -d "$ws" ] || continue
      stream="${stream%/}"
      [ -n "$stream" ] && [ "$stream" != "perma-meta" ] || continue
      printf '%s\n' "$stream"
    done < "$reg" | LC_ALL=C sort -u | while IFS= read -r stream; do
      # Judged against the list itself, so --check and every command always agree.
      printf '%s\n' "$listed" | grep -q -x -F -- "$stream" || printf '%s\n' "$stream"
    done
    ;;
  *)
    printf 'perma-meta\t_meta\n'
    streams | while IFS= read -r s; do printf '%s\t%s\n' "$s" "$s"; done
    ;;
esac
exit 0
