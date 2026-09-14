# Design — a Gemini CLI binding for Permanence

> Status: **proposed, not started.** No code in this repo implements any of this yet.
> Written 2026-09-13. Paused, not abandoned — see §5 and `docs/TOOL-SUPPORT.md` for why.

**Owner carries:** unresolved, pending §5 — best case (all five questions land, matching Claude
Code's binding), nothing; worst case (no custom-command mechanism, no reason to write a
`GEMINI.md` block), the owner still carries command invocation and possibly the standing
instruction by hand. See §3 for the current state of each question.

## 1. Why

`SPEC.md` §3 separates the harness-independent contract (six triggers) from the binding
contract — five questions any harness answers, plus a per-binding note of what the owner still
carries by hand. Gemini CLI is the closest structural match to Claude Code's binding of anything
checked so far — real hooks, a `settings.json`-shaped config, and a headless mode suited to the
scheduled consolidate — so it's a strong candidate to answer most or all five questions, not a
tool that only ever reaches the `AGENTS.md`-only binding (question 3 alone, nothing else).

**Owner's stated reason for wanting this:** primary personal account is Gmail with a Gemini
Pro subscription; Claude Code/Desktop is the starting point on this laptop, but Gemini CLI
(and, separately, Antigravity — see its own design doc) should work just as natively.

## 2. What's verified, and against what

Checked directly against Gemini CLI's own docs on 2026-09-13 (not inferred from a third-party
summary):

- **Hook events** (`docs/hooks/index.md`): `SessionStart`, `SessionEnd`, `BeforeAgent`,
  `AfterAgent`, `BeforeModel`, `AfterModel`, `BeforeToolSelection`, `BeforeTool`, `AfterTool`,
  `PreCompress`, `Notification`.
- **Config file**: `~/.gemini/settings.json` (user level; also `.gemini/settings.json` at
  project level and `/etc/gemini-cli/settings.json` at system level, project taking highest
  precedence). Hooks are nested under a `"hooks"` key, each entry carrying `matcher`, `name`,
  `type`, `command`, `timeout`.
- **Hook I/O contract**: input arrives on stdin; a hook **must print only the final JSON
  object to stdout** — any other stdout text breaks the contract, debug output must go to
  stderr. The doc shows response fields like `"decision": "deny"` for at least one hook type,
  but does not fully specify the JSON schema per event — see §5, this is the first thing to
  verify with a real install before writing code.
- **Headless mode** (`docs/cli/headless.md`): `gemini -p "<prompt>"` (or any non-TTY
  invocation) runs non-interactively; output as plain text, a single JSON object, or streaming
  JSONL; real exit codes (`0` success, `1` general error, `42` input error, `53` turn-limit
  exceeded) — genuinely fit for a cron/launchd job the way the nightly consolidate needs.
- **Context file** (`docs/reference/configuration.md`): Gemini CLI reads **`GEMINI.md`**,
  discovered upward from cwd to a boundary marker (default `.git`); configurable via
  `context.fileName`. **It does not read `AGENTS.md`** — confirmed by its absence anywhere in
  the configuration reference. This means Permanence's existing `AGENTS.md`-reading-tools
  binding (SPEC.md §3, question 3 only) gives Gemini CLI **nothing** today; it needs its own
  binding, built fresh, same as Claude Code got.

## 3. Trigger mapping — the five binding-contract questions

Per `SPEC.md` §3's binding contract, these five questions are answered independently, not as a
ladder. Material-shift and on-commit/on-schedule are not separate questions — see the note after
question 5.

1. **Passive orientation.** `SessionStart` hook (confirmed to exist, §2) is the candidate —
   wraps `session-start.sh`'s output as Gemini's session-start JSON envelope. Whether this is
   worth building at all depends on question 2: if `BeforeAgent` turns out to fire reliably
   once per turn, forcing subsumes passive per the contract, and this question can be answered
   by omission rather than built.
2. **Forcing read.** `BeforeAgent` hook — fires before the agent turn begins, the closest
   analogue to Claude Code's `UserPromptSubmit`. Candidate mechanism only: its firing
   cardinality (once per user turn, or more often — e.g. an internal tool-loop continuation
   within one turn) is unverified, and the exact JSON response shape it expects back is
   unconfirmed by the doc. See §5.
3. **Standing instruction.** `GEMINI.md` — **confirmed** (§2, `docs/reference/configuration.md`):
   discovered upward from cwd to a `.git` boundary, configurable via `context.fileName`,
   and confirmed to *not* fall back to `AGENTS.md`. The mechanism exists; what's still open is
   whether Permanence's material-shift rule needs its own written block there at all, or
   whether the forcing read (question 2) alone already carries it every turn — see §5, this is
   now the first thing to resolve, not the last. **Update 2026-09-13**: the global
   `~/.gemini/GEMINI.md` was live-tested for the Antigravity binding (its own design doc §2) and
   confirmed working there too, on the same underlying file — the two bindings may be able to
   share one standing-instruction block instead of each writing a separate one. Worth designing
   for deliberately once this binding is actually built, not assumed away in either direction.
4. **Command invocation.** Needed for the human-triggered triggers — `/perma-shutdown`,
   `/perma-upgrade`, and the rest of `runtime/commands/*.md`. Whether Gemini CLI has any
   custom-slash-command mechanism comparable to `~/.claude/commands/*.md` is **unverified** —
   if it doesn't, the whole command layer has no home on Gemini CLI, and this is likely the
   single biggest gap in the whole binding.
5. **Headless invocation.** `gemini -p "<prompt>"` — **confirmed** (§2, `docs/cli/headless.md`):
   real exit codes, plain/JSON/JSONL output, non-interactive by construction. This one is
   already answered: it's a capability check plus a config value, swapping the binary
   `runtime/schedule-task.sh` / `nightly-consolidate.sh` invokes, not a translator to build.

Material-shift is what (2) and (3) produce together, not a sixth question — see `SPEC.md` §3.
On-commit (guard + refresh) is unaffected: a git hook, not an AI-harness hook, no binding needed.

## 4. Proposed shape (not file-final — a sketch to react to)

The `detect`/`wire` interface, and what `install.sh` does with this directory, are specified
once in [`design/harness-binding-mechanism.md`](./harness-binding-mechanism.md) — not restated
here. What's specific to Gemini CLI is the file layout underneath that interface:

```
runtime/bindings/gemini-cli/
  detect                 # exit 0 iff `gemini` (or its config dir) is present on this machine
  wire                   # merges the hooks{} fragment into ~/.gemini/settings.json, and —
                          # only if §5 item 1 concludes it's needed — writes GEMINI-block.md's
                          # contents into GEMINI.md
  session-start-hook.sh  # thin translator: calls session-start.sh, wraps its output as
                          # Gemini's SessionStart JSON envelope
  before-agent-hook.sh   # thin translator: calls session-load.sh, same wrapping for
                          # BeforeAgent's envelope
  GEMINI-block.md        # Gemini's equivalent of agents-md-block.md — only built if §5 item 1
                          # concludes a standing-instruction file is worth writing
```

`session-start.sh` / `session-load.sh` themselves are unchanged — the harness-specific piece is
only the I/O envelope around their existing output, which differs from Claude Code's (Claude's
hook can apparently just emit text that becomes context; Gemini's hook contract wants a specific
JSON shape back).

## 5. Must verify before writing any code

Reordered so the standing-instruction question goes first: per `SPEC.md` §3, it's the capability
whose absence is silent — nothing errors, the model just never learns to update the stream
unprompted, and the gap only surfaces as an empty `LOG.md` weeks later. Verify it first, not
last. The remaining items keep their original relative order, learned the hard way twice already
this session (the `update.sh` top-level-path bug, the `templates/` discovery bug — both were
exactly this kind of "the doc said one thing, the actual behavior was slightly different" gap):

1. **Whether a `GEMINI.md`-equivalent standing-instruction file is worth writing at all** (the
   file's existence and discovery rule are already confirmed, §2), or whether the hook-injected
   context alone is sufficient — Claude Code's design leans on both (`CLAUDE.md` for the
   "update the stream when something shifts" standing rule, hooks for the per-turn forcing
   read); Gemini might need the equivalent, might not.
2. **The exact JSON response schema per hook event** — `SessionStart` and `BeforeAgent`
   specifically. The fetched doc confirmed the *rule* (stdout must be pure JSON) but not the
   *shape* for these two events. Needs a real Gemini CLI install and a deliberately verbose
   test hook to observe actual behavior, not just the doc prose.
3. **Whether Gemini CLI has any custom-slash-command mechanism** comparable to
   `~/.claude/commands/*.md`. If not, the twelve `/perma-*` commands have no home on Gemini CLI
   at all, and the whole command layer (not just the two hooks) needs a different design —
   this could be the single biggest gap, bigger than the hooks themselves.
4. **Whether `BeforeAgent` fires once per user turn or more often** (e.g. also on an internal
   tool-loop continuation within one turn) — cardinality matters for a per-session "read once"
   guarantee the same way `session-load.sh`'s existing once-per-session marker does for Claude.

## 6. Non-goals

- Not attempting feature parity with Claude Code on day one — answering questions 1+2 (a working
  `SessionStart` + `BeforeAgent` pair) is the meaningful first milestone; the write/command layer
  can follow once §5's unknowns are resolved.
- Not touching the Gemini Mac app ("Gemini Spark") — verified 2026-09-13 it runs agentic work on
  Google's own cloud servers against Workspace APIs, not local shell/git execution, so it's
  architecturally unlike Claude Code/Antigravity and out of scope for a separate reason from
  Gemini CLI's pause.
