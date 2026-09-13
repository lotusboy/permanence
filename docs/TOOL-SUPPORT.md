# Tool support

Permanence itself — the streams, the conventions, the git history — is just plain markdown and shell
scripts. Nothing about it requires Claude Code. What differs between tools is how much of the *automatic*
part (loading the right stream when you start a session, without being asked) each one can do for you.

`SPEC.md` §3's "The binding contract" names five questions that decide this for any harness — passive
orientation, a forcing read, a standing instruction, command invocation, headless invocation — as a set,
not a ladder: two tools can fail in opposite ways (one reads but never writes; one writes but only when
told to read) and still land at the same score, hiding exactly the difference that matters. So each tool
below states plainly what its owner carries — what's still done by hand — instead of a tier number.

## Capability table

| Tool | Passive orientation | Forcing read | Standing instruction | Command invocation | Headless invocation | Owner carries |
|---|---|---|---|---|---|---|
| **Claude Code** | ✅ | ✅ | ✅ | ✅ | ✅ | Nothing |
| **AGENTS.md-reading tools** (Devin, Codex, droid, Amp, Cursor, GitHub Copilot, Aider, Zed, Windsurf, Google Jules, ...) | ❌ | ❌ | ✅ | ❌ | ❓ | Orientation — say "good morning Permanence" (or run `/perma-startup <name-or-path>`) at the start of a session |
| **Any other tool** (manual fallback) | ❌ | ❌ | ❌ | ❌ | ❓ | Everything — the fallback prompt has to be pasted in at the start of every session |
| **Gemini CLI** (proposed, not built) | ❓ | ❓ | ❓ | ❓ | ❓ | Everything today — see `design/gemini-cli-binding.md` |
| **Antigravity** (proposed, not built) | ❓ | ❓ | ❓ | ❓ | ❓ | Everything today — see `design/antigravity-binding.md` |

Only Claude Code's row is fully verified end to end — it's the reference implementation `SPEC.md` §3
binds explicitly. Every ❓ above is a genuine open question, not a guess dressed up as a checkmark.

## Claude Code

Hooks wire `runtime/session-start.sh` and `runtime/session-load.sh` into every session automatically —
see `SPEC.md` §3. This is what `runtime/install.sh` sets up. Nothing else to do.

## AGENTS.md-reading tools (standing instruction only)

`AGENTS.md` is a cross-tool standard (donated to the Agentic AI Foundation, a Linux Foundation project,
in December 2025) that 30+ agents read, including **Devin**, Cursor, GitHub Copilot, Aider, Zed,
Windsurf, and Google Jules.

Most of these tools also support a **global, per-machine** config file, separate from the one you'd
commit into a project repo — the same slot Claude Code's own `~/.claude/CLAUDE.md` occupies. That
distinction matters: `runtime/install.sh` writes a Permanence pointer block into your *global* AGENTS.md
locations only — it never writes into a project-level `AGENTS.md`, because that file is meant to be
shared with every contributor to that repo, and a shared file is exactly the wrong place to reference a
private memory system (see `SPEC.md` invariant 1, one-way flow).

Paths `install.sh` manages automatically, if the tool's own config directory already exists on your
machine:

| Tool | Global config path |
|---|---|
| (unifying standard, any adopting tool) | `~/.config/agents/AGENTS.md` |
| OpenAI Codex | `~/.codex/AGENTS.md` |
| droid | `~/.factory/AGENTS.md` |
| Amp | `~/.config/AGENTS.md` (only if it already exists) |

This mechanism answers question 3 (standing instruction) and nothing else — the write side works, but
there is no forcing read and no command layer. **This is the silent failure mode the binding contract
warns about:** without question 3 a tool never learns to update a stream unprompted at all; *with* only
question 3, the model can still update a stream once told to look, but nothing tells it to look on its
own. Either way, nothing errors — the only symptom is an empty `LOG.md` weeks later. The owner's
remaining job here is orientation, by hand, every session.

**Devin:** confirmed to read `AGENTS.md`, but its global-config path wasn't confirmed at the time this
was written — check its current docs and add it to `runtime/install.sh`'s list once confirmed. Until
then, use the manual fallback below.

**Gemini CLI and Antigravity are deliberately not on this list — and neither is built yet.** Gemini CLI
reads `GEMINI.md`, not `AGENTS.md` — confirmed directly against its own docs
(`design/gemini-cli-binding.md` §2) — so this bucket gives it nothing; Antigravity's context-file
convention isn't confirmed either way (`design/antigravity-binding.md` §2: "an open question, not a
confirmed absent"). Both need their own binding. Gemini CLI is the closer structural match today (real
hooks, a confirmed headless mode); Antigravity's hook vocabulary turned out to be entirely its own,
separate from Gemini CLI's despite a shared `~/.gemini/` path prefix. Until either ships, both fall
under the manual fallback below.

## Claude Desktop specifically (for IT/Ops: what to grant)

The underlying requirement here isn't a Claude Desktop quirk — `SPEC.md` §3 states it as a
precondition for *any* harness: operating Permanence means actually executing shell commands
(`git`, `mkdir`), not just reading and writing files. The table below is what that
requirement looks like specifically on Claude Desktop's three tabs, for whoever manages the
machine:

| Tab | File/shell access | What's needed |
|---|---|---|
| **Code** | Full — this tab *is* Claude Code, embedded in the desktop app | Nothing extra — same binding as Claude Code above, same as the CLI/VS Code extension. |
| **Cowork** | Real, native file-system access via a folder-scoped permission model | The Cowork session needs to be granted permission to run `git` and `mkdir` in its mounted folder(s) — the same baseline a developer already has on the CLI. Structured file read/write alone isn't enough; Permanence commits to git and creates folders. |
| **Chat** | None persistent | Not supported. No file or shell access means no way to read or write a stream at all. |

**The one-line ask for IT/Ops:** for a user on the Code or Cowork tab, grant the same
`git`/`mkdir` execution permission a developer already has on the CLI — nothing more exotic
than that, and nothing Permanence-specific to install or approve beyond it. Users who only
have the Chat tab available aren't supported by this open-source tool today.

## Manual fallback (any tool, no setup required)

For any tool without a confirmed global-config mechanism, tell it directly at the start of a session:

> Run `~/permanence/runtime/session-start.sh` and follow its output. If you can't run shell commands,
> read `~/permanence/_meta/REGISTRY.md` to find which stream this project maps to, then read that
> stream's `PROJECT.md`, `QUESTIONS.md`, and the recent tail of `LOG.md` before starting work.

This always works, for any AI that can read files — it's just not automatic, and it answers none of
the five questions on its own: every session starts cold unless a human says this out loud, and
nothing gets written back unless a human asks for that too.

## What never changes, regardless of tool

- Never write anything referencing Permanence's paths or contents into a file committed to a project
  repository — that's true for every tool, every row in the table above, no exceptions.
- The stream files themselves (`PROJECT.md`, `LOG.md`, `PEOPLE.md`, `QUESTIONS.md`) are plain markdown —
  any tool that can read a file can use them once pointed at the right stream.
