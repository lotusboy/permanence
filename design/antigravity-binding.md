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

## 3. Trigger mapping — the five binding-contract questions

Per `SPEC.md` §3's binding contract, these five questions are answered independently, not as a
ladder. Antigravity starts from a meaningfully weaker verified base than the Gemini CLI design —
that's a real, load-bearing difference between the two, not an oversight here.

1. **Passive orientation.** No direct `SessionStart`-equivalent event exists in Antigravity's
   documented hook set (§2). This is not treated as a gap on its own: per `SPEC.md` §3,
   "forcing subsumes passive" — if question 2 (`PreInvocation`) turns out to be a reliable
   forcing read, this question is correctly answered by omission, not left unbuilt.
2. **Forcing read.** `PreInvocation` ("fires before the model is called") is the only
   candidate. Under the binding contract, **one forcing-capable hook can be a complete answer
   to questions 1 and 2 together** — not a compromise standing in for a missing `SessionStart`.
   Whether it actually is one depends entirely on its firing cardinality: once per user turn
   would make it exactly that; more often (e.g. also firing on internal tool-loop
   continuations within a turn) would make it too noisy to use without its own once-per-session
   cursor. **Unverified — this is the single highest-priority thing to check, see §5.**
3. **Standing instruction.** No context-file convention confirmed either way — no
   `CLAUDE.md`/`GEMINI.md`/`AGENTS.md` equivalent found in what's been checked so far. This is
   an open question, not a confirmed absence (§2). Per `SPEC.md` §3, this is the question whose
   absence is silent — nothing errors, the model just never learns to update the stream
   unprompted, and the gap only shows up as an empty `LOG.md` weeks later — so it's the first
   thing to resolve in §5, not the last.
4. **Command invocation.** Same open question as the Gemini CLI design, checked independently
   since there's no reason to assume Antigravity and Gemini CLI answer it the same way: does
   Antigravity have a custom-slash-command layer at all for `/perma-*` to live in? Unverified.
5. **Headless invocation.** Depends entirely on whether Antigravity has a headless/
   non-interactive CLI mode comparable to `gemini -p`. **Not checked yet** — no equivalent of
   Gemini's `docs/cli/headless.md` has been fetched for Antigravity. Unverified — check before
   assuming this trigger is buildable at all.

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
2. **Does `PreInvocation` fire once per user turn, or once per model call** (including internal
   tool-loop continuations within a turn)? This is the most consequential open question for
   whether Antigravity gets a clean binding at all: if it fires reliably once per turn, it is by
   itself a complete answer to both question 1 (passive orientation) and question 2 (forcing
   read) — one hook doing the whole read side, per the "forcing subsumes passive" rule in
   `SPEC.md` §3, not a stopgap standing in for a missing `SessionStart`. If instead it fires
   more often, it needs its own once-per-session cursor (`session-load.sh` already has this
   pattern for Claude Code — `/tmp/.perma-loaded-<session-id>` — reusable if Antigravity exposes
   a comparable session identifier).
3. **Does Antigravity have a headless/non-interactive CLI mode** for the nightly consolidate?
   Unchecked — this entire trigger may simply not be buildable until confirmed.
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
