# Design — the harness-binding mechanism itself

> Status: **built and shipped.** The mechanism below is real — `install.sh`'s generic loop, plus
> Claude Code's own binding fully migrated into it (§2's decision below was reopened and
> reversed after being written). Verified on real GitHub Actions across all three OS legs,
> including a real broken-`wire` failure path.
> Written 2026-09-13. Read this *before*
> [gemini-cli-binding.md](./gemini-cli-binding.md) or [antigravity-binding.md](./antigravity-binding.md)
> — both assume the mechanism this doc specifies, rather than each defining their own.

## 1. Why this needed its own doc

`SPEC.md` §3's binding contract states five questions a harness answers and says, in a few
sentences, that a binding is a directory `install.sh` discovers. That's the right *contract* —
but the two tool-specific docs had each started sketching their own version of the actual
mechanism underneath it (directory layout, what `install.sh` does with it), which is exactly the
two-sources-of-truth pattern that caused real bugs elsewhere in this project (`update.sh`'s
tracked-paths list, most recently). This doc is the one place that mechanism is decided; the
tool docs reference it instead of re-deriving it.

## 2. The decision this doc actually turns on: does Claude Code migrate?

Before any directory layout matters, one question has to be answered: does Claude Code's
existing, working, hardened wiring in `install.sh` get rewritten to live in
`runtime/bindings/claude-code/` too — making all three harnesses genuinely symmetric — or does
it stay exactly where it is, as a deliberate, named special case?

**Original decision: it stays.** Reasoning, at the time:

- Claude Code's current wiring isn't simple glue — it's accumulated real hardening this session
  alone: back-up-before-in-place-edit, refuse-on-a-mismatched-`perma:begin`-marker, the
  different-Permanence-owns-this-scheduled-job warning, the `INSTALL_FAILED` tracking that makes
  `install.sh`'s closing line honest. Moving that into a new indirection layer risks a regression
  in something that works today, for a benefit — symmetry — that's aesthetic, not functional.
- Claude Code isn't actually a peer of the other two anyway: it's the one harness every install
  already has, by construction — you need *some* AI tool with shell access just to run
  `install.sh` in the first place. Treating it as "just another detected binding" would be
  modelling a false symmetry, not removing a real one.
- The concrete need for migrating it doesn't exist yet. Nothing about Gemini CLI or Antigravity's
  designs requires Claude Code to move — refactoring working code with no consumer asking for it
  is exactly the pattern this project's own conventions warn against.

**Reopened and reversed, same day, on request.** The owner weighed the regression risk against
genuine symmetry — one pattern, no special case to explain or remember when adding a fourth or
fifth harness later — and chose to accept the risk. **It migrated.** Every step of the old
inline wiring moved into `runtime/bindings/claude-code/{detect,wire}` verbatim (the four
hardening mechanisms preserved exactly, not rewritten): commands, the `CLAUDE.md` block, and the
`settings.json` hook merge. What did **not** move — because it turned out to be generic,
shared infrastructure rather than Claude-Code-specific — stayed inline in `install.sh`: exec
bits/git hooks path, the scheduled `perma-consolidate` job, and the `AGENTS.md` writer for
*other* `AGENTS.md`-reading tools. `claude-code/detect` itself ended up trivial (`exit 0`,
unconditionally) after a real CI failure proved that any heuristic check (`~/.claude` existing,
a `claude` binary on `PATH`) is circular on a genuinely fresh install — `wire` itself is what
creates `~/.claude`, and CI has neither signal, the same as some real first-time users won't.

So the "genuine symmetry" the original reasoning called aesthetic turned out to have one real
payoff: it gave the mechanism itself a live, working binding to test against immediately,
without inventing a synthetic fake one (see §6).

## 3. The `detect` / `wire` interface

Each `runtime/bindings/<harness>/` directory holds up to two executables:

- **`detect`** — no arguments, no side effects. Exit `0` iff this harness is usable on this
  machine (a binary on `PATH`, a config directory existing, whatever's cheapest and safest to
  check). Must never install, prompt, or write anything — `install.sh` runs every binding's
  `detect` unconditionally, so a slow or destructive one would cost every install, not just
  installs that use it.
- **`wire`** — performs the actual merge for that harness: hook registration, a standing-
  instruction block, whatever its own design doc's five-question answers call for. Runs with
  `PERMA` already exported by `install.sh` (same convention every other script in `runtime/`
  already follows via `PERMA_DIR`) — `wire` doesn't need to re-derive it. Must be **idempotent**
  (safe to re-run, matching `install.sh`'s own overall guarantee) and must never touch anything
  outside that harness's own config — never another binding's files, never a project-level file
  (invariant 1 still applies). Exit `0` on success, including a no-op "already wired"; non-zero
  on a real failure, which `install.sh` surfaces rather than swallowing.

A binding with only `detect` (no `wire` yet) is valid — useful for landing "we can tell this
tool is present" before the wiring itself is finished, though neither tool doc is proposing that
as a real interim state.

## 4. What `install.sh` actually does with it

Per §2's reversal, this is no longer "wire any *other* detected harness" — it's the whole
mechanism, Claude Code included. `install.sh` reduces to this loop plus whatever turned out to
be generic and not harness-specific (exec bits, scheduled tasks, the other-tools' `AGENTS.md`
writer). Shipped as-is:

```bash
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
```

Matches the existing per-step status-line style and folds into the same `INSTALL_FAILED`
tracking `install.sh` already uses, rather than inventing a second failure-reporting convention.

## 5. Sequencing — what actually happened

Built in order: the loop itself (verified as a true no-op with `runtime/bindings/` empty), then
Claude Code's migration (§2) — which, per §6 below, turned out to double as the mechanism's real
test case — then Antigravity's binding (hooks.json + `GEMINI.md`; its Skills/command layer is
still deliberately unbuilt, see its own design doc). Each step verified against real GitHub
Actions logs before the next was built on top of it, not just local success.

**Gemini CLI first was the original plan, on unknown-count alone.** Reversed 2026-09-13 after a
real, reproduced (twice) usability finding: personal Google-account sign-in to Gemini CLI is
being actively rejected server-side — *"This client is no longer supported for Gemini Code Assist
for individuals... migrate to the Antigravity suite"* — even though the same account
authenticates successfully for other Google products, Antigravity included. **Gemini CLI's
binding is now permanently declined**, not just paused: a metered API key would route around the
block, but that's a cost decision the owner explicitly turned down. Its design doc stays as
reference only. Antigravity was already installed and working on this machine, and is the path
Google itself points individual users toward — built first, and the only one of the two actually
shipped.

## 6. Non-goals

- Not building a synthetic test-only binding to exercise the loop in isolation — this held even
  after Gemini CLI (the originally planned real test case) was declined, because migrating
  Claude Code in (§2) supplied a real one instead. A fake binding would have been extra surface
  serving no purpose the real one didn't already cover.
- Not specifying anything about *what* either tool binding's `wire` script actually does beyond
  the generic interface here — that's each tool doc's own job.
