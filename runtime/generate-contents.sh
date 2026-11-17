#!/bin/bash
# Regenerate Permanence's CONTENTS.md inventories.
#   generate-contents.sh            -> regenerate all stream inventories + the full-Permanence one
#   generate-contents.sh <stream>   -> regenerate one stream (path relative to ~/permanence) + the full one
# CONTENTS.md files are derived output: gitignored, rebuilt freely (also via .githooks/post-commit).
#
# PLAIN, NO LINKS — on purpose. VS Code's markdown preview sanitizes file:// links (renders them
# non-clickable), the chat panel mangles them, and relative links mis-resolve across workspaces.
# Clickable links never worked reliably. Navigation lives in the VS Code Explorer instead
# (add ~/permanence as a folder). These files are a *readable dated inventory*: what's in a stream and
# when each thing was last touched (newest first). You read them; you click files in the Explorer.

PERMA="${PERMA_DIR:-$HOME/permanence}"
cd "$PERMA" || exit 1
TS="$(date '+%Y-%m-%d %H:%M')"

# stat's flags differ entirely between BSD (macOS, what's shipped here) and GNU (most Linux) —
# `-f` means "format string" on BSD but "filesystem status" on GNU, so a BSD-flavor call either
# errors or silently prints nothing on Linux, which post-commit's `2>/dev/null || true` then
# swallows: the inventory rendered with blank dates in arbitrary order, with no error anywhere,
# against QUICKSTART's stated "works on macOS and Linux with no changes." Try BSD, then GNU.
_perma_mtime_epoch() {  # <file> -> epoch seconds mtime, or empty
  stat -f '%m' "$1" 2>/dev/null || stat -c '%Y' "$1" 2>/dev/null
}
_perma_mtime_date() {  # <file> -> YYYY-MM-DD, or empty
  local d
  d="$(stat -f '%Sm' -t '%Y-%m-%d' "$1" 2>/dev/null)"
  [ -n "$d" ] && { printf '%s' "$d"; return; }
  stat -c '%y' "$1" 2>/dev/null | cut -d' ' -f1   # GNU's %y is "YYYY-MM-DD HH:MM:SS.nnn ±ZZZZ"
}

stream_index() {  # $1 = stream dir (relative to Permanence root) — list newest-first by mtime
  local dir="$1"
  {
    printf '# Contents — %s\n\n' "$dir"
    printf '> Generated %s by runtime/generate-contents.sh — derived, gitignored, do not edit.\n' "$TS"
    printf '> Dated inventory (newest first). **Navigate by clicking files in the VS Code Explorer** (add `~/permanence` as a folder); this file is the at-a-glance "what is here + when".\n\n'
    find "$dir" \( -name .git -o -name .consolidation -o -name node_modules \) -prune -o \
      -type f ! -name 'CONTENTS.md' ! -name '.DS_Store' ! -name '.perma-lock' -print 2>/dev/null \
      | while IFS= read -r f; do
          rel="${f#"$dir"/}"; [ "$rel" = "$f" ] && rel="$f"
          printf '%s\t%s\t%s\n' "$(_perma_mtime_epoch "$f")" "$(_perma_mtime_date "$f")" "$rel"
        done | sort -rn | while IFS=$'\t' read -r _ d rel; do
          printf -- '- %s — %s\n' "$rel" "$d"
        done
  } > "$dir/CONTENTS.md"
}

full_index() {  # whole Permanence, grouped by folder, alphabetical
  {
    printf '# Contents — full Permanence\n\n'
    printf '> Generated %s by runtime/generate-contents.sh — derived, gitignored, do not edit.\n' "$TS"
    printf '> Dated inventory. **Navigate via the VS Code Explorer** (add `~/permanence` as a folder).\n\n'
    printf '## Root\n'
    find . -maxdepth 1 -type f ! -name 'CONTENTS.md' ! -name '.DS_Store' ! -name '.perma-lock' -print | sed 's|^\./||' | sort \
      | while IFS= read -r f; do printf -- '- %s — %s\n' "$f" "$(_perma_mtime_date "$f")"; done
    # Piped into a while-read, not `for d in $(...)`: the old unquoted command substitution
    # word-split on any space in a stream directory name, truncating it before it ever reached
    # `find "$d"`. Same fix pattern already used for the Root listing two lines above.
    find . \( -name .git -o -name .consolidation \) -prune -o -maxdepth 2 -mindepth 1 -type d -print | sed 's|^\./||' | sort \
      | while IFS= read -r d; do
          case "$d" in (.git*|.consolidation*|runtime/*) continue;; esac
          [ -z "$(find "$d" -maxdepth 1 -type f ! -name 'CONTENTS.md' ! -name '.DS_Store' | head -1)" ] && continue
          printf '\n## %s\n' "$d"
          find "$d" -maxdepth 1 -type f ! -name 'CONTENTS.md' ! -name '.DS_Store' -print | sort \
            | while IFS= read -r f; do printf -- '- %s — %s\n' "$f" "$(_perma_mtime_date "$f")"; done
        done
  } > "CONTENTS.md"
}

if [ -n "$1" ] && [ "$1" != "--quiet" ]; then
  [ -d "$1" ] && stream_index "$1"
else
  # Every stream from the one list (runtime/list-streams.sh), perma-meta's folder (_meta) included.
  PERMA_DIR="$PERMA" bash "$PERMA/runtime/list-streams.sh" | cut -f2 | while IFS= read -r s; do
    [ -d "$s" ] && stream_index "$s"
  done
fi
full_index
[ "$1" = "--quiet" ] || [ "$2" = "--quiet" ] || echo "CONTENTS.md regenerated (plain inventory; streams + full)."
exit 0
