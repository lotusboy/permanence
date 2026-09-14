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
| **Antigravity** | ✅ | ✅ | ✅ | 🔧 | ✅ | Command invocation — Skills need one live-fire test against the real product before `wire`'s command layer is written; see `design/antigravity-binding.md` §5 |
| **Devin CLI** | ✅ | ✅ | ✅ | 🔧 | ✅ | Command invocation — Skills need one live-fire test before `wire`'s command layer is written; see `design/devin-binding.md` §5 |
| **Cursor** | ✅ | ✅ | ❌ | ✅ | ✅ | Standing instruction — no working global rules/`AGENTS.md` file exists for Cursor despite three real attempts; see `design/cursor-binding.md` §5 |
| **AGENTS.md-reading tools** (Codex, droid, Amp, GitHub Copilot, Aider, Zed, Windsurf, Google Jules, ...) | ❌ | ❌ | ✅ | ❌ | ❓ | Orientation — say "good morning Permanence" (or run `/perma-startup <name-or-path>`) at the start of a session |
| **Any other tool** (manual fallback) | ❌ | ❌ | ❌ | ❌ | ❓ | Everything — the fallback prompt has to be pasted in at the start of every session |
| **Gemini CLI** (designed, permanently declined) | ❓ | 🔧 | 🔧 | ❓ | 🔧 | Everything, indefinitely — personal-account sign-in is rejected server-side by Google (reproduced twice 2026-09-13); a metered API key would route around it but is a cost decision explicitly declined — see `design/gemini-cli-binding.md` |

**Legend**: ✅ shipped and verified — real `runtime/bindings/` code, live-fire tested against the actual
product, not just reasoning about docs. 🔧 confirmed real — either live-tested or confirmed against the
installed product's own bundled documentation — but no code wires it in yet, and (Gemini CLI only) may
never, given the access block. ❓ genuinely still unknown.

## Claude Code

Hooks wire `runtime/session-start.sh` and `runtime/session-load.sh` into every session automatically —
see `SPEC.md` §3. This is what `runtime/bindings/claude-code/` sets up (still driven by
`runtime/install.sh`, like every binding). Nothing else to do.

## Antigravity

A `PreInvocation` hook (`runtime/bindings/antigravity/`) carries the forcing read and the passive
orientation in one — Antigravity has no separate session-start-style event, and doesn't need one, per
`SPEC.md` §3's "forcing subsumes passive." The standing instruction lands in the global `~/.gemini/GEMINI.md`.
Live-fire verified: wired for real and tested against an actual `agy` session, not just reasoned about.
Command invocation (Skills) isn't built yet — see `design/antigravity-binding.md` §5. **Owner carries:
nothing but the `/perma-*` commands themselves**, which have no home here until that's built.

## Devin CLI

`SessionStart` and `UserPromptSubmit` hooks (`runtime/bindings/devin/`) carry the passive orientation
and the forcing read — the same event names Claude Code uses, but a genuinely different JSON contract
(`hookSpecificOutput.additionalContext`, not plain text), confirmed by live testing that Devin does
**not** actually execute Claude Code's own hooks despite one of its own bundled docs claiming it does.
The standing instruction lands in a dedicated global `~/.config/devin/AGENTS.md` — written directly
rather than relying on Devin's separate (real, but conditional on Claude Code's binding also being
installed) pickup of `~/.claude/CLAUDE.md`. Live-fire verified: wired for real and tested against an
actual `devin -p` session, not just reasoned about. Command invocation (Skills) isn't built yet — see
`design/devin-binding.md` §5. **Owner carries: nothing but the `/perma-*` commands themselves**, which
have no home here until that's built.

## Cursor

A single `sessionStart` hook (`runtime/bindings/cursor/`) answers both the passive orientation and the
forcing read — live-confirmed the more surprising way round from the other bindings: a prompt that
never mentioned Permanence at all still caused the agent to spontaneously read and accurately report
real stream content, purely because the injected instruction told it to. Command invocation is fully
shipped too — commands translate into `~/.cursor/skills/<name>/SKILL.md`, confirmed invokable by literal
`/name` syntax from a completely unrelated project, the cleanest command-invocation result of any
binding built so far. **The standing instruction is the one real gap**: no working global rules or
`AGENTS.md` file was found for Cursor despite three separate live attempts — "User Rules" appear to be
account-synced through Cursor's own UI, not a local file. See `design/cursor-binding.md` §5. **Owner
carries: the ongoing half of the standing instruction** — whether unprompted mid-session stream updates
happen is still unconfirmed, so updating the stream when something shifts mid-session may need doing by
hand.

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

**Gemini CLI, Antigravity, Devin CLI, and Cursor are deliberately not on this list.** Antigravity,
Devin, and Cursor all have their own real binding now (above) — Devin does read `AGENTS.md`, but
through its own binding's dedicated global file, not this generic mechanism; Cursor's real
binding doesn't use `AGENTS.md` at all, since no working global path was found for it (see the
Cursor section above). Gemini CLI reads `GEMINI.md`, not `AGENTS.md`, confirmed directly against
its own docs, and its binding is permanently declined (personal-account sign-in is rejected
server-side by Google, reproduced twice 2026-09-13 — a metered API key would route around it but
is a cost decision explicitly declined, see `design/gemini-cli-binding.md`), so it falls under
the manual fallback below, same as any unimplemented tool.

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
