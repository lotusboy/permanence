# Design — an Antigravity binding for Permanence

> Status: **proposed, not started.** No code in this repo implements any of this yet — but the
> read-side mechanism (§3 question 2) is now live-verified, not just designed.
> Written 2026-09-13, substantially revised the same day after live testing. See
> [ROADMAP.md](../ROADMAP.md) for where this sits relative to other work, and
> [gemini-cli-binding.md](./gemini-cli-binding.md) — Antigravity shares a `~/.gemini/` path
> prefix with Gemini CLI, which is shared branding, not a shared mechanism (confirmed below,
> not just assumed): the two need genuinely separate bindings.

**Owner carries, as of the live testing below:** likely just command invocation and the
standing-instruction question, not the whole read/write side. The forcing read (question 2) is
now proven working end-to-end. Standing instruction (question 3) and command invocation
(question 4) are still genuinely open — see §3.

## 1. Why

Same owner motivation as the Gemini CLI design: Antigravity is on the wish list alongside Claude
Code/Desktop and Gemini CLI/Mac. Unlike Gemini CLI, Antigravity's hook system is its **own,
third vocabulary** — not a variant of Gemini CLI's — confirmed by both reading its docs and
running it for real. That's why this is a separate design doc, not a section of the Gemini CLI
one. **Priority flipped to Antigravity over Gemini CLI on 2026-09-13** (see
`design/harness-binding-mechanism.md` §5): personal Google-account sign-in to Gemini CLI is
being actively rejected server-side, reproduced twice, with Google's own message pointing
individual users at Antigravity instead. Antigravity was also already installed and
authenticated on this machine, which is what made the live testing below possible in the first
place.

## 2. What's verified, and against what

**Primary source, as of the 2026-09-13 update below: a file bundled with the actual installed
product**, not the public web docs — `~/.gemini/antigravity-ide/builtin/skills/agy-customizations/docs/hooks.md`,
shipped locally with `antigravity-cli` 1.2.2 (installed via `brew install --cask antigravity-cli`).
This is more authoritative than `antigravity.google/docs/hooks/` (the original source for this
doc's first pass) because it's the literal spec the installed binary implements — but it's
version-pinned to 1.2.2, not guaranteed to match any other version. Where the two sources
differ, the local one wins below, and the difference is called out.

**Original pass, against the public docs (still true):**

- **Hook events**: `PreToolUse`, `PostToolUse`, `PreInvocation`, `PostInvocation`, `Stop`. No
  `SessionStart` event exists.
- **The shared `~/.gemini/` path is branding, not a shared engine** — confirmed further below:
  Gemini CLI and Antigravity use different config files (`settings.json` vs `hooks.json`) and,
  now confirmed live, different discovery behavior even within Antigravity's own two candidate
  locations (see next section).

**2026-09-13 — live-tested against the real, already-authenticated install, not simulated:**

- **Config location: the global `~/.gemini/config/hooks.json` is confirmed correct** — proven
  by a real Go parse error from the binary itself (`hooks_manager.go`) on a wrong schema, then a
  real "loaded N named hooks" success line once corrected. **The workspace-local `.agents/hooks.json`
  path the docs present as the primary example was tried and NOT discovered at all** by this CLI
  version — "loaded 0 named hooks from 0 hooks.json file(s)," even with a file genuinely present
  there. A real discrepancy between the generic docs and this specific installed version, not
  assumed away.
- **The real schema has one more layer than either doc source states plainly**: the top level of
  `hooks.json` is **arbitrary hook *names*** (e.g. `"perma-binding"`), each optionally carrying
  `"enabled"` plus the event names as sub-keys — not event names directly at the top level.
  `PreToolUse`/`PostToolUse` are **grouped**: `[{"matcher": "...", "hooks": [{"command": ...}]}]`.
  `PreInvocation`/`PostInvocation`/`Stop` are **flat**: `[{"command": ..., "timeout": ...}]` — an
  array of handler objects directly, no `matcher`, no extra `hooks` wrapper.
- **`PreInvocation` genuinely fires, live-confirmed, and its context-injection mechanism
  genuinely works.** A real test: registered a `PreInvocation` hook returning
  `{"injectSteps":[{"ephemeralMessage":"...say the word BANANA..."}]}`, then asked `agy --print`
  for a one-sentence greeting. **The model's real reply contained the word "BANANA."** This is
  not a config-loading confirmation — it's proof the actual forcing-read mechanism Permanence
  needs (inject an instruction, have the model act on it) works end-to-end on this harness.
- **`PreInvocation` fires more than once per turn** — captured payloads carried
  `"invocationNum":0` then `"invocationNum":1` within a single simple exchange. Cardinality
  question resolved: **not** once per turn, so a once-per-conversation cursor is required before
  this is a real binding, not just a proof of concept. `conversationId` is present in every
  payload and is the natural cursor key — same role `session-load.sh`'s
  `/tmp/.perma-loaded-<session-id>` plays for Claude Code.
- **`PreToolUse` genuinely fires too, and fails closed correctly**: a hook returning a bare `{}`
  (not a valid `{"decision": "allow"|"deny"|"ask"|"force_ask", ...}`) caused the tool call to be
  denied automatically — a real, sensible safety default, and a concrete reminder that a real
  `wire` script must return a proper decision object, not just acknowledge receipt.
- **The earlier "headless mode excludes hooks" finding (this doc's first pass, same day) was
  wrong, and now traceably so**: at the time, both the schema (missing the hook-name wrapper)
  and the tested location (`.agents/`, never discovered) were wrong simultaneously. Once both
  were corrected, hooks fired correctly inside plain `agy --print` (headless) sessions — headless
  and hook-carrying are **not** mutually exclusive on this harness. That concern is retired.
- **A real, still-open caveat**: `workspacePaths` came back as an empty array in every captured
  payload, even when `agy --print` was run from inside a real directory. A plain `--print`
  invocation may not attach real workspace/project context automatically — possibly needs
  `--add-dir` (a real CLI flag) or an actually-opened project, the way the GUI IDE works. This
  matters directly for stream resolution (which Permanence stream a session belongs to) and is
  the next concrete thing to check, not assumed either way.
- **No context-file convention confirmed either way still** — no `CLAUDE.md`/`GEMINI.md`/
  `AGENTS.md` equivalent found in the local hooks doc or elsewhere checked so far. Genuinely open,
  not just under-researched — the local doc that resolved everything else above doesn't mention
  one.

## 3. Trigger mapping — the five binding-contract questions

Per `SPEC.md` §3's binding contract, these five questions are answered independently, not as a
ladder.

1. **Passive orientation.** No `SessionStart`-equivalent event exists, and none is needed:
   `PreInvocation` fires reliably (§2), so per `SPEC.md` §3's "forcing subsumes passive," this
   question is correctly answered by omission — confirmed, not just assumed.
2. **Forcing read.** **Confirmed working, live-tested, not just designed.** `PreInvocation`
   fires on every model call within a conversation (`invocationNum` 0, 1, 2...), and its
   `injectSteps`/`ephemeralMessage` field demonstrably steers the model's real output (§2's
   BANANA test). Building this for real needs one addition beyond the proof of concept: a
   once-per-conversation cursor keyed on `conversationId`, so the orientation/forcing text is
   injected once per session, not on every single model call within it.
3. **Standing instruction.** Still genuinely unresolved — no context-file convention found.
   This is the question whose absence is silent (`SPEC.md` §3: nothing errors, the model just
   never learns to update the stream unprompted, and the gap only shows up as an empty `LOG.md`
   weeks later) — now the clear top priority for further verification, since question 2 no
   longer is.
4. **Command invocation.** Still unverified: does Antigravity have a custom-slash-command layer
   for `/perma-*` to live in? Not checked in this round of live testing.
5. **Headless invocation.** Confirmed real (`agy --print`), **and confirmed to carry hooks
   correctly** — the earlier concern that headless and hook-carrying might be separate
   capabilities was live-tested and retired (§2). One caveat remains: `workspacePaths` came back
   empty in headless mode, so headless invocation may not carry real project context without an
   explicit `--add-dir` — relevant to the nightly-consolidate use case specifically, not to the
   forcing-read mechanism itself.

Material-shift is what (2) and (3) produce together, not a sixth question — see `SPEC.md` §3.
On-commit (guard + refresh) is unaffected: a git hook, not an AI-harness hook, no binding needed.

## 4. Proposed shape

The `detect`/`wire` interface, and what `install.sh` does with this directory, are specified once
in [`design/harness-binding-mechanism.md`](./harness-binding-mechanism.md) — not restated here.

```
runtime/bindings/antigravity/
  detect                   # exit 0 iff `agy` (or ~/.gemini/antigravity-cli) is present
  wire                     # merges a named hook block into ~/.gemini/config/hooks.json —
                            # NOT workspace .agents/, confirmed undiscovered by this version (§2)
  pre-invocation-hook.sh   # real job now known precisely (§2/§3): read the invocationNum +
                            # conversationId off stdin; if this conversationId's cursor
                            # (~/.gemini/perma-test-style per-conversation marker) hasn't fired
                            # yet, call session-start.sh + session-load.sh's combined logic and
                            # return {"injectSteps":[{"ephemeralMessage": <that output>}]};
                            # otherwise return {} and mark the cursor
```

## 5. Must verify before writing any code

Sharply shorter than before this round of live testing — most of what blocked a first milestone
is now resolved.

1. **Does Antigravity read any global standing-instructions file** — still the top question,
   unchanged reasoning: its absence is silent, so it's verified first, not last.
2. **Does `--add-dir` (or an actually-opened project) make `workspacePaths` non-empty** — needed
   to confirm stream resolution is possible at all from a `PreInvocation` payload; not yet
   checked.
3. **Does a custom-slash-command mechanism exist** for the `/perma-*` command layer — unchanged,
   still open, checked independently since there's no reason to assume Antigravity and Gemini
   CLI answer it the same way.
4. **Whether a Gemini CLI hook and an Antigravity hook can coexist on one machine** without
   collision — lower priority now that Gemini CLI's own binding is paused (see
   `harness-binding-mechanism.md` §5), but still relevant if that pauses ends.

Retired by live testing, no longer open: `PreInvocation`'s existence and cardinality, whether
headless mode excludes hooks, the exact I/O schema for `PreInvocation`/`PreToolUse`.

## 6. Non-goals

- Not building the full binding yet — items 1–2 above still block a real `wire` script that
  correctly resolves which stream a session belongs to. But a minimal proof-of-concept
  `pre-invocation-hook.sh` (inject a fixed test string once per conversation) is now buildable
  today if useful as a next step, unlike before this round of testing.
- Not assuming Antigravity and Gemini CLI can share one binding just because of the path overlap
  — confirmed as two separate config files and, now, two separate discovery behaviors.
