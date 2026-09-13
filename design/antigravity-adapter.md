# Design — Google Antigravity as a third Tier 1 harness

> Status: **proposed, not started.** No code in this repo implements any of this yet.
> Written 2026-09-13. See [ROADMAP.md](../ROADMAP.md) for where this sits relative to other work,
> and [gemini-cli-adapter.md](./gemini-cli-adapter.md) — **read that one first**: Antigravity
> shares a `~/.gemini/` path prefix with Gemini CLI, which looks like shared branding, not a
> shared mechanism (see §2). The two need genuinely separate adapters.

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

## 3. Proposed trigger mapping

| SPEC.md trigger | Antigravity mechanism | Confidence |
|---|---|---|
| Session-start (read) | No direct event. Candidate: treat the **first** `PreInvocation` of a session as session-start, if Antigravity exposes any per-session state to distinguish "first" from "nth" — otherwise this trigger may have no clean home at all on Antigravity as currently documented. | Low — needs a real install to test |
| Material-shift (write) / the forcing trigger | `PreInvocation`, same event doing double duty with the above — genuinely uncertain whether one event can honestly cover both jobs, or whether they collapse into one anyway (arguably no bad thing — Claude Code needs two hooks partly because its `SessionStart` is documented as easy for the model to skim past; if `PreInvocation` fires reliably every time, one hook might be *enough*, not a compromise) | Low — needs verification, see §5 |
| Wind-down, On-upgrade | Owner-invoked commands, same open question as Gemini CLI: does Antigravity have a custom-slash-command layer at all for `/perma-*` to live in? | Unverified |
| On-schedule (consolidate) | Depends entirely on whether Antigravity CLI has a headless/non-interactive invocation mode comparable to `gemini -p` — **not checked yet**, no equivalent of Gemini's `docs/cli/headless.md` has been fetched for Antigravity | Unverified — check before assuming this trigger is buildable at all |
| On-commit (guard + refresh) | Unaffected — a git hook, not an AI-harness hook | as-is |

Compare this table's confidence column to the Gemini CLI design's §3 — Antigravity starts from a
meaningfully weaker verified base. That's a real, load-bearing difference between the two designs,
not an oversight here.

## 4. Proposed shape (a sketch, contingent on §5)

```
runtime/
  adapters/
    antigravity/
      pre-invocation-hook.sh   # thin: calls session-start.sh + session-load.sh's combined logic,
                                # wraps output as Antigravity's expected hook response
      hooks.json               # the fragment install.sh merges into ~/.gemini/config/hooks.json
                                # (or .agents/hooks.json — global vs workspace, TBD per §5)
```

Deliberately not sketching a command layer or a context-file block yet — too much of §3 is
still unverified to be worth designing file-by-file; the shape above covers only the one trigger
(`PreInvocation`) that's plausible today.

## 5. Must verify before writing any code

More open than the Gemini CLI design, in priority order:

1. **Does `PreInvocation` fire once per user turn, or once per model call** (including internal
   tool-loop continuations within a turn)? This decides whether it can safely double as both
   "session start" and "the forcing read" or whether it fires far too often to be usable
   without its own once-per-session cursor (`session-load.sh` already has this pattern for
   Claude Code — `/tmp/.perma-loaded-<session-id>` — reusable if Antigravity exposes a
   comparable session identifier).
2. **Does Antigravity have a headless/non-interactive CLI mode** for the nightly consolidate?
   Unchecked — this entire trigger may simply not be buildable until confirmed.
3. **Does Antigravity read any global standing-instructions file** — needed for the
   "update the stream when something shifts" rule the way `CLAUDE.md` carries it for Claude
   Code. If not, that rule would need to be re-injected by the hook itself on every
   `PreInvocation`, which is a different (heavier) design than Claude Code's.
4. **Does a custom-slash-command mechanism exist** for the `/perma-*` command layer — same open
   question as the Gemini CLI design, checked independently since there's no reason to assume
   Antigravity and Gemini CLI answer it the same way.
5. **Whether a Gemini CLI hook and an Antigravity hook can coexist on one machine** without
   collision, given the shared `~/.gemini/` path prefix — relevant the moment someone tries to
   install both adapters on the same laptop, which is exactly this owner's stated situation.

## 6. Non-goals

- Not attempting to build anything here until at least §5 items 1–3 are answered — unlike the
  Gemini CLI design, there isn't yet a confirmed read-path (`SessionStart`-equivalent) to build
  a first milestone around.
- Not assuming Antigravity and Gemini CLI can share one adapter just because of the path
  overlap — treat them as fully independent until proven otherwise (§2).
