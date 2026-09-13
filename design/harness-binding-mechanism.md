# Design — the harness-binding mechanism itself

> Status: **proposed, not started.** No code in this repo implements any of this yet.
> Written 2026-09-13. See [ROADMAP.md](../ROADMAP.md), and read this *before*
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

Before any directory layout matters, one question has to be answered, and it wasn't anywhere
before now: does Claude Code's existing, working, hardened wiring in `install.sh` get rewritten
to live in `runtime/bindings/claude-code/` too — making all three harnesses genuinely symmetric —
or does it stay exactly where it is, as a deliberate, named special case?

**Decision: it stays.** Reasoning:

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

So: **`runtime/bindings/` is for optional, detected-if-present harnesses only.** Claude Code's
wiring stays exactly as it is, unconditional, in `install.sh` itself, under a comment that says
so and points here — a documented asymmetry, not an oversight. This does narrow what
"rearchitecture" means here: it's a genuine, real extensibility point for everything *beyond* the
one mandatory harness, not a rewrite of the mandatory one for the sake of consistency.

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

A new step, proposed to sit right after today's step 5 (`settings.json`) and before step 6
(events) — conceptually "wire any *other* detected harness the same way," ahead of the
Claude-Code-specific optional extras that follow it:

```bash
# 6. Optional harness bindings — anything beyond the mandatory Claude Code wiring above (see
#    design/harness-binding-mechanism.md for why Claude Code itself isn't one of these). Each
#    subdirectory is self-contained: its own detect script decides whether it applies to this
#    machine, its own wire script does the actual merge. install.sh knows nothing about any
#    specific harness here — adding one is a new directory, not an edit to this file.
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

## 5. Sequencing — this before either tool binding, and which tool first

Build this mechanism (the loop above, exercised by at least one real `detect`/`wire` pair) before
either tool-specific binding claims to be "built" — a design that only exists in two independent
proposals isn't proven, and the cheapest way to prove it is against whichever tool binding is
actually usable to build against, not just whichever has fewer open design questions on paper.

**Originally recommended Gemini CLI first**, on unknown-count alone. Reversed 2026-09-13 after a
real, reproduced (twice) usability finding: personal Google-account sign-in to Gemini CLI is
being actively rejected server-side — *"This client is no longer supported for Gemini Code Assist
for individuals... migrate to the Antigravity suite"* — even though the same account
authenticates successfully for other Google products, Antigravity included. Paying for a metered
API key instead is a real option but a separate cost/product decision, declined for now. Fewer
open *design* questions doesn't help if the harness can't actually be driven end-to-end on the
account available. **Antigravity is the priority now** — already installed and working on this
machine, and the path Google itself is pointing individual users toward. Build its binding first;
bring Gemini CLI's back in later only if its access situation changes.

## 6. Non-goals

- Not migrating Claude Code's wiring — see §2's decision.
- Not building a synthetic test-only binding to exercise the loop in isolation — once Gemini
  CLI's binding exists, it's both a real feature and the mechanism's own test case; a fake one
  would be extra surface serving no other purpose.
- Not specifying anything about *what* either tool binding's `wire` script actually does beyond
  the generic interface here — that's each tool doc's own job.
