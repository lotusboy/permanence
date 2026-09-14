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
  if [ ! -f "$src" ]; then
    echo "  WARN — block source file $src is missing; $dst was NOT touched. This usually means a stale/partial Permanence checkout — re-run runtime/update.sh or re-clone."
    return 1
  fi
  mkdir -p "$(dirname "$dst")"
  if [ -f "$dst" ] && grep -q '<!-- perma:begin' "$dst" 2>/dev/null; then
    begins=$(grep -c '<!-- perma:begin' "$dst")
    ends=$(grep -c '<!-- perma:end -->' "$dst")
    begin_line=$(grep -n '<!-- perma:begin' "$dst" | head -1 | cut -d: -f1)
    end_line=$(grep -n '<!-- perma:end -->' "$dst" | head -1 | cut -d: -f1)
    # Require EXACTLY one begin and one end, not just equal counts — the splice below reacts to
    # every begin/end line it sees (a single boolean `skip` flag, not a counter), so two or more
    # pairs (even cleanly-separated, well-formed ones) duplicate the injected block, and
    # overlapping/nested pairs do too. Refuse anything but the single-pair case rather than trying
    # to validate nesting. Found by adversarial testing (Two-Pass review, 2026-09-14, Pass 2
    # Finding 10) — a mismatched-count-only check let a malformed overlapping pair through.
    if [ "$begins" -ne 1 ] || [ "$ends" -ne 1 ] || [ -z "$end_line" ] || [ "$end_line" -le "$begin_line" ]; then
      echo "  WARN — $dst has $begins perma:begin marker(s) and $ends perma:end marker(s); expected exactly one matched pair. Left COMPLETELY UNTOUCHED — writing here could delete real content or duplicate the injected block. Fix or remove the marker(s) by hand, then re-run install.sh."
      # A deliberate soft warning, never a wire failure (see claude-code/wire's header) — but
      # still real and easy to miss scrolling past a long install log, so surface it in
      # install.sh's own final summary too. PERMA_ATTENTION_FILE is exported by install.sh and
      # inherited by every binding's wire subprocess; harmless no-op if unset (e.g. this function
      # called standalone, outside install.sh).
      [ -n "${PERMA_ATTENTION_FILE:-}" ] && echo "$dst" >> "$PERMA_ATTENTION_FILE" 2>/dev/null
      return 1
    fi
    cp "$dst" "$dst.perma-bak"
    awk -v s="$src" '
      /<!-- perma:begin/ {while ((getline line < s) > 0) print line; close(s); skip=1; next}
      /<!-- perma:end -->/ {skip=0; next}
      !skip {print}' "$dst" > "$dst.tmp" && mv "$dst.tmp" "$dst"
  else
    # No existing marker: this only ever prepends content. If $dst doesn't exist yet (a fresh
    # install), there's nothing to lose. If it DOES exist, back it up first and fail closed on a
    # read failure instead of silently treating it as empty — `cat "$dst" 2>/dev/null || true`
    # used to swallow ANY read failure (a permission oddity, a transient I/O glitch, a same-second
    # race with a concurrent writer) as "the file was empty," discarding real content with no
    # backup and no recovery. Found by adversarial testing, not by reading the code (the comment
    # this replaced asserted "nothing here can lose data" and that assumption was false) — Two-Pass
    # review, 2026-09-14, Pass 2 CRITICAL finding.
    if [ -f "$dst" ]; then
      if ! cp "$dst" "$dst.perma-bak" 2>/dev/null; then
        echo "  WARN — $dst exists but could not be backed up before merging into it. Left COMPLETELY UNTOUCHED. Investigate the permission/read issue, then re-run install.sh."
        return 1
      fi
      if ! { cat "$src"; echo; cat "$dst"; } > "$dst.tmp" 2>/dev/null; then
        rm -f "$dst.tmp"
        echo "  WARN — $dst exists but could not be read while merging into it. Left COMPLETELY UNTOUCHED (backup already saved to $dst.perma-bak). Investigate the read failure, then re-run install.sh."
        return 1
      fi
    else
      { cat "$src"; echo; } > "$dst.tmp"
    fi
    mv "$dst.tmp" "$dst"
  fi
}
