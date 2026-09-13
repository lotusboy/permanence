# Design — an Antigravity binding for Permanence

> Status: **proposed, not started.** No code in this repo implements any of this yet.
> Written 2026-09-13. See [ROADMAP.md](../ROADMAP.md) for where this sits relative to other work,
> and [gemini-cli-binding.md](./gemini-cli-binding.md) — **read that one first**: Antigravity
> shares a `~/.gemini/` path prefix with Gemini CLI, which looks like shared branding, not a
> shared mechanism (see §2). The two need genuinely separate bindings.

**Owner carries:** unresolved, provisionally everything. None of the five binding-contract
questions are confirmed yet (§3). Best case, if `PreInvocation` turns out to fire once per turn
and a standing-instruction file exists: questions 1+2 collapse into one hook with nothing left
for the owner on the read side, same shape as the "forcing subsumes passive" case in `SPEC.md`
§3. Worst case, none of the five land, and Antigravity gets no automated binding at all — the
owner carries orientation, writing, and command invocation entirely by hand, same as a tool
Permanence doesn't support.

## 1. Why

Same owner motivation as the Gemini CLI design: Antigravity is explicitly on the wish list
alongside Claude Code/Desktop and Gemini CLI/Mac. Unlike Gemini CLI, Antigravity's hook system
turned out to be its **own, third vocabulary** — not a variant of Gemini CLI's — discovered only
by fetching Antigravity's own hook docs directly rather than assuming the shared `~/.gemini/`
path prefix meant a shared mechanism. That's the main reason this is a separate design doc
rather than a section of the Gemini CLI one.

## 2. What's verified, and against what

Checked directly against Antigravity's own docs (`antigravity.google/docs/hooks/`) on
2026-09-13:

- **Hook events**: `PreToolUse`, `PostToolUse`, `PreInvocation`, `PostInvocation`, `Stop`.
  **No `SessionStart` and no direct `UserPromptSubmit`/`BeforeAgent` analogue.** The closest fit
  for "something fires before the model responds" is `PreInvocation` ("fires before the model
  is called") — but see §5, its cardinality within one turn is unverified.
- **Config file**: `hooks.json` (not `settings.json`), in a "customization directory" — either
  workspace-local `.agents/` or global `~/.gemini/config/`, with workspace taking precedence
  over global when both exist.
- **The shared `~/.gemini/` path**: Antigravity's own paths reference
  `~/.gemini/antigravity` (Antigravity 2.0) and `~/.gemini/antigravity-cli`, and the hooks
  customization directory can also sit at `~/.gemini/config/`. This looks like the two products
  share a top-level namespace/family branding under Google's Gemini umbrella, **not** that they
  share a hook engine — the event names and the config filename (`hooks.json` vs
  `settings.json`) are both different. Direct confirmation of "these are unrelated mechanisms"
  wasn't found in Antigravity's docs (they simply don't mention Gemini CLI at all) — treat this
  as the working assumption until someone with both installed actually checks whether a Gemini
  CLI `settings.json` hook and an Antigravity `hooks.json` hook can coexist or conflict.
- **No context-file convention was confirmed** (no `CLAUDE.md`/`GEMINI.md`/`AGENTS.md`
  equivalent found in what's been checked so far) — an open question, not a "confirmed absent."

**Update, 2026-09-13 — live-tested against a real install**, not just vendor docs (the CLI
variant, `antigravity-cli`, installed via `brew install --cask antigravity-cli`; already
authenticated on this machine, so real sessions were run, not simulated):

- **`hooks.json` at `~/.gemini/config/hooks.json` is confirmed correct** — proven by a real Go
  parse error from the binary itself (`hooks_manager.go`) when the schema was wrong, then a real
  "loaded N named hooks" log line once corrected. Not inferred from docs; read from the actual
  running code's own log output.
- **The real per-event schema is a single object, not an array** — `{"EventName": {"command":
  ..., "timeout": ...}}`. The vendor docs didn't specify this precisely enough to get right on
  the first try; the binary's own parse error did.
- **Headless mode exists and is confirmed real**: `agy --print "<prompt>"` (alias `-p`) runs
  non-interactively, with `--output-format text|json|stream-json`. Resolves item 5 below to
  "yes, it exists" — but see the finding right after this list, which complicates what that's
  actually worth.
- **A real, negative, reproduced finding on `PreInvocation`/`PostInvocation`/`PreToolUse`/
  `PostToolUse`**: all four loaded successfully (confirmed via the log) but **none fired**
  across two separate `--print` runs — one a plain text reply, one a prompt that provably ran a
  real shell tool call (its output appeared in the response). Zero hook-execution log lines
  either time. This was not expected going in, and changes item 5 below from "does headless
  exist" to a sharper, more consequential question — see §5.

None of this came from re-reading the vendor docs harder; it came from installing the real
binary and watching what it actually logs when given a wrong answer and then a right one.

## 3. Trigger mapping — the five binding-contract questions

Per `SPEC.md` §3's binding contract, these five questions are answered independently, not as a
ladder. Antigravity starts from a meaningfully weaker verified base than the Gemini CLI design —
that's a real, load-bearing difference between the two, not an oversight here.

1. **Passive orientation.** No direct `SessionStart`-equivalent event exists in Antigravity's
   documented hook set (§2). This is not treated as a gap on its own: per `SPEC.md` §3,
   "forcing subsumes passive" — if question 2 (`PreInvocation`) turns out to be a reliable
   forcing read, this question is correctly answered by omission, not left unbuilt.
2. **Forcing read.** `PreInvocation` is still the only candidate event name, and the config side
   is now fully verified (§2) — but a live test moved the open question from "what's its firing
   cardinality" to something more basic: **it didn't fire at all**, across two real `--print`
   sessions (plain text, and a real tool call). Cardinality is now moot until presence is
   explained — see §5, which now leads with this instead of the schema question it used to.
3. **Standing instruction.** No context-file convention confirmed either way — no
   `CLAUDE.md`/`GEMINI.md`/`AGENTS.md` equivalent found in what's been checked so far. This is
   an open question, not a confirmed absence (§2). Per `SPEC.md` §3, this is the question whose
   absence is silent — nothing errors, the model just never learns to update the stream
   unprompted, and the gap only shows up as an empty `LOG.md` weeks later — so it's the first
   thing to resolve in §5, not the last.
4. **Command invocation.** Same open question as the Gemini CLI design, checked independently
   since there's no reason to assume Antigravity and Gemini CLI answer it the same way: does
   Antigravity have a custom-slash-command layer at all for `/perma-*` to live in? Unverified.
5. **Headless invocation.** Confirmed: `agy --print`/`-p` is real, with `text`/`json`/
   `stream-json` output — the nightly-consolidate use case is buildable on its own terms. **But
   it may be a *different, non-overlapping* capability from question 2, not a mode that also
   carries hooks** — the live test that found `PreInvocation` silent (item 2) used exactly this
   headless mode. If hooks turn out to be interactive-session-only, "headless invocation" and
   "forcing read" stop being two independent yes/no answers and become a real either/or: a
   scheduled `--print` run would never carry the forcing-read instruction the way Claude Code's
   nightly consolidate and session hooks both do today. Worth resolving deliberately, not
   assumed away.

Material-shift is what (2) and (3) produce together, not a sixth question — see `SPEC.md` §3.
On-commit (guard + refresh) is unaffected: a git hook, not an AI-harness hook, no binding needed.

Compare this list to the Gemini CLI design's §3 — three of Antigravity's five questions are
fully open (1 by way of 2, 3, 5), against Gemini's two. That's the weaker verified base referred
to above.

## 4. Proposed shape (a sketch, contingent on §5)

The `detect`/`wire` interface, and what `install.sh` does with this directory, are specified once
in [`design/harness-binding-mechanism.md`](./harness-binding-mechanism.md) — not restated here.
Only one translator is sketched below, because only one trigger (`PreInvocation`) is plausible
today — a command layer or standing-instruction block isn't worth designing file-by-file while §3
questions 3–5 are still open:

```
runtime/bindings/antigravity/
  detect                   # exit 0 iff Antigravity's CLI or config dir is present
  wire                     # merges the hooks fragment into hooks.json — workspace .agents/
                            # or global ~/.gemini/config/, per §5 item 5
  pre-invocation-hook.sh   # thin translator: calls session-start.sh + session-load.sh's
                            # combined logic, wraps output as Antigravity's expected
                            # PreInvocation hook response
```

## 5. Must verify before writing any code

Reordered so the standing-instruction question goes first, per `SPEC.md` §3: it's the capability
whose absence is silent, so it needs verifying before anything else, not last. More open overall
than the Gemini CLI design:

1. **Does Antigravity read any global standing-instructions file** — needed for the
   "update the stream when something shifts" rule the way `CLAUDE.md` carries it for Claude
   Code. If not, that rule would need to be re-injected by the hook itself on every
   `PreInvocation`, which is a different (heavier) design than Claude Code's. This goes first
   because, unlike the other four questions, a wrong or missing answer here produces no error —
   just a stream that silently stops updating.
2. **Does `PreInvocation` fire at all, in a real interactive session** — no longer a cardinality
   question, a presence one. Live-tested 2026-09-13 (§2): config loads correctly, but across two
   real `--print` (headless) runs, zero hook-execution log lines. Not yet tested in a genuine
   interactive session, which is the next concrete step, not more config-reading — if it still
   doesn't fire there, `PreInvocation` may not be a usable trigger at all, and the binding has no
   read-side candidate left. *If* it does fire, cardinality (once per turn vs. more often) is
   still the follow-up question, per the original reasoning: once per turn is a complete answer
   to both question 1 and question 2 together (forcing subsumes passive, `SPEC.md` §3); more
   often needs its own once-per-session cursor, reusable from `session-load.sh`'s existing
   pattern for Claude Code.
3. **Whether headless mode and hooks are mutually exclusive.** `agy --print` is confirmed real
   (§2) — but the same live test that left item 2 unresolved used exactly this mode, so it's
   live evidence, not speculation, that headless and hook-carrying might be two different
   execution paths rather than one capability with two names. If so, the nightly consolidate
   (headless, no hooks needed) and the forcing-read trigger (needs hooks) end up on genuinely
   different footing for this harness, unlike Claude Code where the same session type carries
   both.
4. **Does a custom-slash-command mechanism exist** for the `/perma-*` command layer — same open
   question as the Gemini CLI design, checked independently since there's no reason to assume
   Antigravity and Gemini CLI answer it the same way.
5. **Whether a Gemini CLI hook and an Antigravity hook can coexist on one machine** without
   collision, given the shared `~/.gemini/` path prefix — relevant the moment someone tries to
   install both bindings on the same laptop, which is exactly this owner's stated situation.

## 6. Non-goals

- Not attempting to build anything here until at least §5 items 1–2 are answered — unlike the
  Gemini CLI design, there isn't yet a confirmed forcing-read mechanism (`PreInvocation`'s
  firing cardinality is unverified) to build a first milestone around.
- Not assuming Antigravity and Gemini CLI can share one binding just because of the path
  overlap — treat them as fully independent until proven otherwise (§2).
