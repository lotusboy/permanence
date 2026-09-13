# Design — Gemini CLI as a second Tier 1 harness

> Status: **proposed, not started.** No code in this repo implements any of this yet.
> Written 2026-09-13. See [ROADMAP.md](../ROADMAP.md) for where this sits relative to other work.

## 1. Why

`SPEC.md` §3 already separates the harness-independent contract (six triggers) from one
concrete binding (Claude Code, Tier 1). Gemini CLI is the closest structural match to that
binding of anything checked so far — real hooks, a `settings.json`-shaped config, and a
headless mode suited to the scheduled consolidate — so it's the natural second Tier 1 harness,
not a stretch fit forced into Tier 2's `AGENTS.md` fallback.

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
  the configuration reference. This means Permanence's existing Tier 2 (`agents-md-block.md`
  written into a global `AGENTS.md`) gives Gemini CLI **nothing** today; it needs its own
  binding, built fresh, same as Claude Code got.

## 3. Proposed trigger mapping

| SPEC.md trigger | Gemini CLI mechanism | Reuses |
|---|---|---|
| Session-start (read) | `SessionStart` hook | `runtime/session-start.sh`'s resolution logic, wrapped — see §4 |
| Material-shift (write) / the forcing trigger | `BeforeAgent` hook (fires before the agent turn begins — the closest analogue to Claude's `UserPromptSubmit`) | `runtime/session-load.sh`'s resolution logic, wrapped |
| Wind-down, On-upgrade | `/perma-shutdown`, `/perma-upgrade` — these are commands the owner invokes, not hook-driven. Works as-is once Gemini CLI can read `runtime/commands/*.md` as its own slash commands (needs checking — does Gemini CLI have a custom-commands mechanism at all, or would these stay Claude-Code-only and Gemini users type the underlying steps by hand?) | Genuinely unverified — see §5 |
| On-schedule (consolidate) | `runtime/schedule-task.sh` (already cross-platform) invoking `gemini -p "<the same prompt perma-consolidate.md describes>"` instead of `claude -p` | `nightly-consolidate.sh`'s shape, with the invoked binary swapped behind a config flag |
| On-commit (guard + refresh) | Unaffected — a git hook, not an AI-harness hook. No adapter needed. | as-is |

## 4. Proposed shape (not file-final — a sketch to react to)

Keep `runtime/session-start.sh` / `session-load.sh` as the **one** canonical implementation of
"resolve the stream, produce the orientation text" — the harness-specific piece is only the I/O
envelope around that, which differs from Claude Code's (Claude's hook can apparently just emit
text that becomes context; Gemini's hook contract wants a specific JSON shape back). Proposed:

```
runtime/
  session-start.sh          # unchanged — the actual logic
  session-load.sh           # unchanged
  adapters/
    gemini-cli/
      session-start-hook.sh # thin: calls session-start.sh, wraps its output as Gemini's JSON envelope
      before-agent-hook.sh  # thin: calls session-load.sh, same wrapping
      settings-block.json   # the hooks{} fragment install.sh merges into ~/.gemini/settings.json
      GEMINI-block.md       # Gemini's equivalent of agents-md-block.md, if a standing-instruction
                             # file turns out to matter for Gemini the way CLAUDE.md does for Claude
```

`install.sh` gains a detection-gated step (`command -v gemini` found → offer to wire it,
mirroring exactly how the AGENTS.md step already works structurally) rather than an
unconditional one — most installs won't have Gemini CLI, and a silent no-op keeps that free.

## 5. Must verify before writing any code

In priority order — these are the things that would make an implementation attempt go
sideways if assumed rather than checked, learned the hard way twice already this session
(the `update.sh` top-level-path bug, the `templates/` discovery bug — both were exactly this
kind of "the doc said one thing, the actual behavior was slightly different" gap):

1. **The exact JSON response schema per hook event** — `SessionStart` and `BeforeAgent`
   specifically. The fetched doc confirmed the *rule* (stdout must be pure JSON) but not the
   *shape* for these two events. Needs a real Gemini CLI install and a deliberately verbose
   test hook to observe actual behavior, not just the doc prose.
2. **Whether Gemini CLI has any custom-slash-command mechanism** comparable to
   `~/.claude/commands/*.md`. If not, the twelve `/perma-*` commands have no home on Gemini CLI
   at all, and the whole command layer (not just the two hooks) needs a different design —
   this could be the single biggest gap, bigger than the hooks themselves.
3. **Whether `BeforeAgent` fires once per user turn or more often** (e.g. also on an internal
   tool-loop continuation within one turn) — cardinality matters for a per-session "read once"
   guarantee the same way `session-load.sh`'s existing once-per-session marker does for Claude.
4. **Whether a `GEMINI.md`-equivalent standing-instruction file is worth writing at all**, or
   whether the hook-injected context alone is sufficient — Claude Code's design leans on both
   (`CLAUDE.md` for the "update the stream when something shifts" standing rule, hooks for the
   per-turn forcing read); Gemini might need the equivalent, might not.

## 6. Non-goals

- Not attempting feature parity with Claude Code on day one — a working `SessionStart` +
  `BeforeAgent` pair (read path) is the meaningful first milestone; the write/command layer can
  follow once §5's unknowns are resolved.
- Not touching the Gemini Mac app — see `ROADMAP.md`, out of scope for a separate, verified
  reason.
