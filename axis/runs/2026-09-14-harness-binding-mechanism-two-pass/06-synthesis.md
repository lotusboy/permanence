# Synthesis — harness-binding-mechanism Two-Pass review

PR #13 (`add-roadmap-and-adapter-designs` vs `main`, 33 files, ~2,700 insertions, 41 commits).
Merged per the Merge Contract in `03-synthesis-prompt.md` from `04-pass1-output.md` (analytical,
structural read) and `05-pass2-output.md` (adversarial, live-reproduced against a scratch
directory). Every finding below cites its origin pass(es).

## BLUF

Pass 1 (structural read) concluded there was no critical finding. Pass 2 (adversarial,
live-executed) found one real, reproducible data-loss defect that Pass 1's structural read missed
entirely — this is the Two-Pass method working as designed: the defect *reads* as safe from the
code alone (the comment beside it asserts "nothing here can lose data") and only breaks under a
condition Pass 1 had no reason to manufacture by reading. **Fix the CRITICAL and the two HIGH
correctness bugs (JSON-shape crash, Skills-translation abort-on-read) before merge.** Everything
else is real but not merge-blocking: three factual doc/code contradictions (cheap, user-facing,
fix alongside), and a set of lower-severity consistency/coverage gaps worth a tracked follow-up
rather than blocking this PR.

---

## CRITICAL — fix before merge

### C1. `block-merge.sh`'s "no marker" branch can silently destroy an existing standing-instruction file, with zero backup, if reading it fails at write time
**Source:** Pass 2 (live-verified), independently missed by Pass 1's structural read.
**Citation:** `runtime/lib/block-merge.sh:30-38`

```
30    else
31      # No existing marker: this can only ever ADD content (prepend), never destroy any — no
32      # backup needed, because nothing here can lose data.
...
38      { cat "$src"; echo; cat "$dst" 2>/dev/null || true; } > "$dst.tmp" && mv "$dst.tmp" "$dst"
39    fi
```

This branch runs on every real user's very first install, for every binding (`CLAUDE.md`,
`AGENTS.md` ×4 call sites, `GEMINI.md`, Devin's `AGENTS.md`) — the moment it matters most. The
comment's safety claim assumes `cat "$dst"` always succeeds when `$dst` has real content; `2>/dev/null || true` converts *any* read failure (permission oddity, transient I/O/NFS glitch, or a
same-second race with a concurrent writer — Pass 2's Finding 11 confirms this isn't only a
contrived precondition, a second install run creates the same race window) into "the file was
empty," and the subsequent `mv` unconditionally overwrites `$dst` with just the new block. Live
reproduced with `chmod 000`: the original content vanished, no `.perma-bak` created. The
marker-found branch three lines above (line 25) does back up first — this branch does not.

**Fix:** back up unconditionally before this write too (mirroring line 25), or fail closed (like
the mismatched-marker branch) when `cat "$dst"` returns non-zero, instead of swallowing it with
`|| true`.

---

## HIGH — real correctness bugs, fix before merge or immediately after

### H1. `_perma_block_merge` reports success when it did nothing, if the source block file is missing — converts a real failure into a false "refreshed" message
**Source:** Pass 1 (Finding 8, flagged low-severity) + Pass 2 (Finding 1, live-verified, escalated).
Merged per the severity rule: `max(pass1=low, pass2=high) = HIGH`. Pass 2's evidence is stronger
(live repro plus a direct citation to `SPEC.md`'s own explicit warning) and is the version to act
on.
**Citation:** `runtime/lib/block-merge.sh:14` — `[ -f "$src" ] || return 0`; every call site
(`claude-code/wire:39-41`, `install.sh:56-63`, `antigravity/wire:77-79`, `devin/wire:89-91`) prints
a "refreshed" success message on that same `0` return.

`SPEC.md` names the standing instruction explicitly as *"the capability whose absence is
silent... nothing raises an error, and the failure surfaces only as an empty LOG.md weeks later.
Verify this one first, not last."* This exact code path is the one place the mechanism could
verify that and currently doesn't — a missing/mistyped source block file (plausible: this PR's own
`update.sh` history shows newly-added tracked paths that an older install's `PATHS` array didn't
yet cover) silently no-ops while the terminal says "CLAUDE.md: Permanence block refreshed."

**Fix:** have `_perma_block_merge` return a distinct non-zero (or print its own warning) when
`$src` is missing; callers should not print "refreshed" on that path.

### H2. All four JSON-hook-merge `wire` scripts crash with an uncaught exception on a validly-parsed but wrong-shaped config file, contradicting the explicit "checks presence before writing" design claim
**Source:** Pass 2 only (Finding 2, live-verified). Not found by Pass 1.
**Citation:** 7 call sites across all four bindings — `claude-code/wire:60-63`,
`antigravity/wire:38-57`, `devin/wire:43-67`, `cursor/wire:38-50`.

`design/claude-code-binding.md` claims the merge "checks presence before writing." The
`try/except` around `json.load` only catches genuinely-invalid JSON — it doesn't protect against
Permanence's own key existing with the wrong *type* (e.g. `"hooks": {"SessionStart":
"not-a-list"}`), which `setdefault`/`.get()` chains don't guard against. Live-reproduced:
`AttributeError: 'str' object has no attribute 'append'`, an unhandled traceback rather than the
clean "present but unparseable — NOT touched" message the same script already gives for
actually-invalid JSON three lines earlier. Fails safe (no corruption, `WIRE_FAILED=1` does get set
via the outer non-zero exit) but gives the user a raw traceback instead of a diagnosis, and
contradicts the stated design.

**Fix:** wrap the shape-assumption in `try/except (AttributeError, TypeError)`, falling back to
the same warn-and-skip message already used for JSON-parse failures, at all 7 sites.

### H3. Skills-translation: one unreadable command file aborts translation of every other command file, in three bindings simultaneously
**Source:** Pass 2 only (Finding 3, live-verified). Related to, but distinct from, Pass 1's
Finding 4 (different symptom — see M-tier below) — kept separate per the dedupe key.
**Citation:** `antigravity/wire:114-132`, `devin/wire:126-144`, `cursor/wire:97-116` — identical
loop triplicated across all three, `content = open(src_path).read()` sits **outside** the
per-file `try/except` that visually reads as fault-isolating.

Live-reproduced with 3 files (one invalid-UTF-8, two valid): zero of the two valid files were
translated once the bad one raised `UnicodeDecodeError` ahead of them alphabetically. Does
correctly propagate as `WIRE_FAILED=1` (not silent), but the blast radius is every Skill for that
harness, not the one bad file — and it's the same bug independently duplicated three times, the
exact "duplicating this function was the risk" pattern `block-merge.sh`'s own extraction was
supposed to guard against, reintroduced here.

**Fix:** move `content = open(src_path).read()` inside the existing `try:` block — a one-line fix,
×3 files.

### H4. Skill/command files are overwritten with no backup, unlike every other file these wire scripts touch — a same-named pre-existing file is destroyed silently on collision
**Source:** Pass 1 only (Finding 4). Adjacent to H3 (same code region) but a different symptom/root
cause — H3 is abort-on-read-failure; this is silent-overwrite-on-name-collision — so kept as a
separate finding per the dedupe key, cross-referenced.
**Citation:** `claude-code/wire:27` (`cp "$f" "$CMD_DST/$name"`, unconditional), and
`antigravity/wire:127`, `devin/wire:139`, `cursor/wire:111` (`open(..., "w")`, unconditional) — no
existence check, no backup, unlike every JSON-merge path in the same diff which does back up first.

**Failure scenario:** a user's own, unrelated skill/command sharing a name with one of
Permanence's (`perma-startup`, etc.) is silently destroyed on the next `wire` run, no backup, no
warning.

**Fix:** back up an existing file before overwrite the same way the JSON merges do, or at minimum
detect a pre-existing, non-Permanence-authored file (e.g. no `installed-from:` marker) and warn
before clobbering.

---

## MEDIUM — real, fix soon, not merge-blocking

### M1. Three user-facing docs contradict the shipped code (and each other) about what's built
**Source:** Pass 1 only (Findings 1–3). Pass 2 scoped docs as secondary/spot-check only.
- `README.md:137` — claims Antigravity "is designed... not yet built," false; contradicted by
  `docs/TOOL-SUPPORT.md`, `SPEC.md`, `design/antigravity-binding.md`, and `CHANGELOG.md` in this
  same diff. Root cause confirmed via `git log`: written before Antigravity's Skills layer shipped
  (`9330252`), never updated since.
- `design/harness-binding-mechanism.md:120-121` — same stale-doc bug: claims Antigravity's Skills
  layer is "still deliberately unbuilt," contradicted by `runtime/bindings/antigravity/wire:81-140`
  and the binding's own design doc.
- `docs/TOOL-SUPPORT.md:20` — the Cursor capability-table cell has the interactive/headless
  standing-instruction claim **backwards**, contradicting the same file's own prose 60 lines later,
  `SPEC.md`, and `stop-hook.sh`'s own code comment. Reads as a copy/paste error, not a substantive
  disagreement — everywhere else in the diff the gap is consistently described the other way
  round.

**Fix:** three small, mechanical text corrections — cite the contradicting doc/code each time so
the fix is unambiguous (see Pass 1's full findings for exact suggested replacement text).

### M2. Missing `python3`-availability guard, two different places
**Source:** Pass 1 (Finding 5, install-time `wire` scripts) + Pass 2 (Finding 9, runtime hook
scripts). Related but distinct artifacts — kept as two findings.
- Pass 1: `antigravity/wire`, `devin/wire`, `cursor/wire` skip the `command -v python3` guard +
  manual-fallback message that `claude-code/wire:46,85-94` has — on a `python3`-less machine, these
  three fail with a raw shell error instead of an actionable fallback, and their own "see message
  above" text (referencing a message that was never printed) makes it worse.
- Pass 2: the *runtime* hook-translator scripts (`stop-hook.sh`, `session-start-hook.sh`, etc.)
  have no equivalent guard on their final JSON-emitting step — if `python3` is present at install
  time but later unavailable (uninstalled, PATH change, a differently-sandboxed hook execution
  environment), that step silently produces empty stdout instead of `{}`, an untested/unspecified
  condition given `pre-tool-use-hook.sh`'s own header says a bare `{}` "fails closed."

**Fix:** mirror `claude-code/wire`'s guard+fallback pattern in the other three `wire` scripts
(2 call sites each); consider an explicit `{}`-on-any-failure wrapper for the runtime hooks' final
output step.

### M3. `install.sh`'s discovery loop can't distinguish "harness not installed" from "this binding's `detect` is broken" — such a binding vanishes with no error
**Source:** Pass 2 only (Finding 4).
**Citation:** `runtime/install.sh:74-88`. A missing/non-executable `detect` silently `continue`s
with no output line at all; a `detect` that crashes for the wrong reason is treated identically to
"not installed" (any non-zero exit). CI's own failure-path test (`ci.yml:450-462`) only exercises
`wire` failing *after* `detect` already succeeded — this gap has zero coverage.

**Fix:** log missing/non-executable `detect` explicitly rather than silently skipping; treat a
`detect` exit code other than 0 or 1 as itself a reportable failure.

### M4. Inconsistent failure-propagation: Claude Code's own command-copy step is deliberately non-fatal on a per-file failure; the newer bindings' analogous Skills-translation step is fatal
**Source:** Pass 2 only (Finding 5).
**Citation:** `claude-code/wire:8-12` (own header, explicitly documents the choice) vs. the fatal
behavior in the three newer bindings (same code path as H3). A real, acknowledged inconsistency
in the mechanism's own stated contract (`design/harness-binding-mechanism.md:77-78`: "non-zero on
a real failure... rather than swallowing"), applied differently to the binding every install
depends on most.

**Fix:** a product decision, not just a code fix — decide whether a partial command-copy failure
should be fatal everywhere or nowhere, and make Claude Code's binding match.

### M5. Orphaned Skills/commands are never cleaned up — `wire` only ever grows the installed set, never converges to what's currently in `runtime/commands/`
**Source:** Pass 1 only (Finding 6).
**Citation:** all four bindings' command/Skills-writing loops — none enumerates the destination
directory to remove an entry with no matching source. Pre-existing pattern for Claude Code, now
tripled in surface area by replication into three new Skills directories.

**Fix (tracked follow-up, not urgent):** diff destination against current source list per `wire`
run, deleting only entries carrying Permanence's own "managed by" marker.

### M6. Corrects Pass 1's Finding 7: the real marker-merge gap is overlapping/nested pairs, not clean sequential pairs
**Source:** Pass 2 (Finding 10, live-verified) — **supersedes Pass 1's Finding 7**, which
hypothesized clean sequential pairs would duplicate content; Pass 2 tested that exact case and
found it works correctly. See `03-synthesis-prompt.md` for the resolution.
**Citation:** `runtime/lib/block-merge.sh:17-29`. Live-reproduced: an overlapping `begin1, begin2,
old inner, end1, end2` structure passes the count/ordering check but the `awk` splice's single
`skip` flag (not a counter) duplicates the injected block. Recoverable via the `.perma-bak` that
branch does create (unlike C1), so lower severity than a data-loss finding, but a genuine gap in
what the guard actually catches.

**Fix:** track nesting with a counter, or reject any structure with more than one begin/end pair
outright.

---

## LOW — worth a tracked note, not urgent

- **L1** (Pass 2, Finding 6): a mismatched-marker WARN never affects a `wire` script's exit code or
  `install.sh`'s "done." vs "done, WITH FAILURES" summary line — intentional per
  `claude-code/wire`'s own header, but easy to miss scrolling past a long install log given
  `SPEC.md`'s own "verify this first" framing for this exact capability.
- **L2** (Pass 2, Finding 7): malformed YAML frontmatter (missing closing `---`) silently produces
  the literal Skill description `"---"` rather than a rejection or warning.
- **L3** (Pass 2, Finding 8): Antigravity's once-per-conversation dedup marker is a non-atomic
  check-then-act (`[ -f "$MARKER" ]` then `touch`) — a real TOCTOU under genuinely concurrent
  `PreInvocation` firing, though Pass 2 could not confirm true concurrency is reachable in practice
  (only documented sequential-looking multiple firings). Low impact if it does fire: redundant
  context injection, not corruption.
- **L4** (Pass 1, Finding 9): CI never exercises the actual `wire` success path for
  Antigravity/Devin/Cursor (only their correct `detect`-absent path, since CI runners don't have
  those tools installed) — the JSON-merge and Skills-translation logic for three of five bindings
  has zero automated regression coverage; correctness currently rests entirely on one-time live-fire
  testing outside CI. Suggested fix: a no-op shim binary on `PATH` to get `detect` to pass in CI.
- **L5** (Pass 2, Finding 12): `.perma-bak` files are single-generation (each overwritten on the
  next real change) — fine for the common case, worth knowing before relying on it to undo
  something from two installs ago.

---

## What the disagreement between passes actually shows

Pass 1's own BLUF stated "no CRITICAL finding... every config write goes through a
backup-before-in-place-edit discipline, consistently applied." That conclusion was reasonable given
a structural read — the no-marker branch's own comment states the safety argument directly, and the
branch does structurally look like a prepend-only operation. Pass 2's adversarial pass didn't take
that comment at face value, manufactured the one precondition (a read failure) the comment's claim
depends on, and found it false. This is close to the textbook case the Two-Pass method's own
documentation describes: a structural review reads intent and coherence; an adversarial review
constructs the conditions where intent and implementation diverge. Recommend keeping both passes as
standard practice for future infrastructure-scale PRs on this mechanism, not simplifying to a single
cocktail — this run is direct evidence for why.

## Full Verified/Unknown ledger

See each raw output's own ledger (`04-pass1-output.md`, `05-pass2-output.md`) for the complete
list. Summary of what remains genuinely unverified by either pass: the real JSON payload shapes
Antigravity/Devin/Cursor send to their hooks on stdin in live use (both passes correctly declined
to re-verify this from a static diff — it was live-fire tested outside this repo, per the design
docs and commit history, and neither pass had a live instance of these tools to re-check against).
