#!/usr/bin/env bash
# block-merge.sh — sourced, never run directly. Defines _perma_block_merge, the one place
# Permanence splices a delimited block into a file it doesn't own outright (CLAUDE.md, AGENTS.md,
# and any AI-harness binding's own standing-instruction file). Shared because the safety net
# (refuse a mismatched begin/end pair, back up before any in-place replace) must not drift between
# call sites — duplicating this function was the risk, not the fix.
#
# Sourced by: runtime/install.sh (the AGENTS.md step, for OTHER AGENTS.md-reading tools) and
# runtime/bindings/claude-code/wire (CLAUDE.md). Any future binding's own standing-instruction
# write should source this too, rather than reimplementing the splice.

_perma_block_merge() {  # _perma_block_merge <target-file> <block-source-file>
  local dst="$1" src="$2" begins ends begin_line end_line
  [ -f "$src" ] || return 0
  mkdir -p "$(dirname "$dst")"
  if [ -f "$dst" ] && grep -q '<!-- perma:begin' "$dst" 2>/dev/null; then
    begins=$(grep -c '<!-- perma:begin' "$dst")
    ends=$(grep -c '<!-- perma:end -->' "$dst")
    begin_line=$(grep -n '<!-- perma:begin' "$dst" | head -1 | cut -d: -f1)
    end_line=$(grep -n '<!-- perma:end -->' "$dst" | head -1 | cut -d: -f1)
    if [ "$begins" -ne "$ends" ] || [ -z "$end_line" ] || [ "$end_line" -le "$begin_line" ]; then
      echo "  WARN — $dst has a perma:begin marker with no matching perma:end after it (or a mismatched count). Left COMPLETELY UNTOUCHED — writing here would delete everything after the marker. Fix or remove the marker(s) by hand, then re-run install.sh."
      return 1
    fi
    cp "$dst" "$dst.perma-bak"
    awk -v s="$src" '
      /<!-- perma:begin/ {while ((getline line < s) > 0) print line; close(s); skip=1; next}
      /<!-- perma:end -->/ {skip=0; next}
      !skip {print}' "$dst" > "$dst.tmp" && mv "$dst.tmp" "$dst"
  else
    # No existing marker: this can only ever ADD content (prepend), never destroy any — no
    # backup needed, because nothing here can lose data.
    # `cat "$dst" 2>/dev/null || true` on a truly fresh install ($dst doesn't exist yet): the
    # redirect hides cat's error message but NOT its exit code, and that code is what the `{ }`
    # group reports — left unguarded, it silently skipped the `mv` below via `&&`, leaving a
    # correctly-written `.tmp` file that never became the real file. Found live-testing this
    # extraction (2026-09-13), reproduced against the original unmodified code too.
    { cat "$src"; echo; cat "$dst" 2>/dev/null || true; } > "$dst.tmp" && mv "$dst.tmp" "$dst"
  fi
}
