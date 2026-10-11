# Can the project team run on Antigravity, Devin and Cursor?

**Status:** findings, 2026-10-11. The Antigravity part was built from them the same day and shipped
in v1.8.0 (`docs/PROJECT-TEAM.md`, "On Antigravity"). Cursor and Devin are still findings only.

## The question

The project team (see [docs/PROJECT-TEAM.md](../docs/PROJECT-TEAM.md)) needs three things from a
harness:

1. **Subagents.** The harness can launch a second agent with its own task.
2. **A hook before the launch that can rewrite it.** `runtime/agent-roles.py` uses this to turn
   `role:<job>:<role>` into a real agent.
3. **A hook when a subagent stops.** `runtime/agent-roles.py` uses this to log the run.

Each tool was tested on one machine. Every row says how the fact was learned:

- **Live** — the tool was run, a logging hook was attached, and the hook's input was read.
- **Tool's own text** — the tool's own error message or built-in documentation says so.
- **Program code** — read from the tool's installed program files. The tool was not run.
- **Unknown** — not established.

## Antigravity CLI 1.2.2 — has all three

| Need | Answer | How learned |
|---|---|---|
| Subagents | Yes. Tool `invoke_subagent`. Arguments: `Subagents: [{TypeName, Role, Prompt, Model}]`. | Live |
| Hook before launch | Yes. `PreToolUse` with `matcher: "invoke_subagent"` receives the full arguments. | Live |
| That hook can rewrite | Yes. Returning `{"decision":"allow","overwrite":{"Subagents":[…]}}` replaced the subagent's prompt. The launching agent is told a hook changed the arguments. `overwrite` is a shallow merge: the whole `Subagents` list must be returned. | Live |
| That hook can block | Yes: `"decision":"deny"`. | Tool's own text |
| Hook when a subagent stops | Partly. `Stop` fires once in the subagent's conversation and once in the parent's. The input carries `conversationId` and `terminationReason`. It does not say the conversation is a subagent, and it does not name the parent. | Live |
| Named custom agents | Yes. A folder per agent holding `agent.md`: YAML frontmatter (`name`, `description`, `tools`, `subagent`, `model` as a tier such as `flash` or `pro`), then the instructions under one H1. `~/.gemini/config/agents/<name>/` is loaded for every workspace and listed by `agy agents`. `TypeName` selects one by name. | Live |
| A name that is not an agent reaches the hook | Yes. `TypeName: "role:reviewer"` arrived in `PreToolUse` unchanged and unvalidated; the hook replaced it with a real agent and the call ran. | Live |
| A subagent's shell commands | Ask for permission like any other. With no one to answer (print mode), they are refused. | Live |

Side finding: every Antigravity hook also fires inside a subagent's conversation, under the
subagent's own `conversationId`. The existing Permanence `PreInvocation` hook loads the stream on the
first call of each new conversation, so today it loads the stream into every subagent as well.

## Cursor CLI 2026.09.10 — looks close; not live-tested

The account on the test machine had reached its usage limit, so no prompt ran. Only `sessionStart`
was seen live.

| Need | Answer | How learned |
|---|---|---|
| Subagents | Yes. Custom agents are read from `.cursor/agents/**/*.md`, and from `.claude/agents/**/*.md` when third-party config is on. | Program code |
| Hook before launch | Yes: `subagentStart`. Input: `subagent_type`, `task`, `parent_conversation_id`, `subagent_model`. The hook's matcher is tested against `subagent_type`. | Program code |
| That hook can rewrite | No. `subagentStart` returns only `permission`, `user_message`, `additional_context`. It can allow or deny. | Program code |
| Rewrite through `preToolUse` instead | Unknown. `preToolUse` accepts `updated_input`, but only for tools that support it. Whether the subagent tool does is not established. | Program code |
| Hook when a subagent stops | Yes: `subagentStop`. Input: `subagent_type`, `status`, `summary`, `duration_ms`, `modified_files`, `agent_transcript_path`. | Program code |

## Devin CLI 3000.10.21 — no subagent hooks

The account on the test machine had no model available, so no prompt ran.

| Need | Answer | How learned |
|---|---|---|
| Subagents | Yes. Tool `run_subagent`; a `subagents_enabled` setting; `devin doctor` reports "custom subagent profiles". | Program code; `devin doctor` output |
| Hook before launch | No dedicated event. Devin rejects `SubagentStart` in its config and lists the events it accepts: `PreToolUse`, `PostToolUse`, `UserPromptSubmit`, `Stop`, `PostCompaction`, `SessionStart`, `SessionEnd`, `PermissionRequest`. | Tool's own text |
| `PreToolUse` fires for `run_subagent` and can rewrite it | Unknown. | — |
| Hook when a subagent stops | No `SubagentStop` event (same list). Whether `Stop` or `PostToolUse` fires for a subagent is unknown. | Tool's own text |

Two facts for anyone re-running this on Devin: print mode (`-p`) refuses an untrusted folder, and
the config key that lifts it is `skip_workspace_trust: true`, not the key the error message names.

## What this means

- **Antigravity is the first candidate.** It has all three needs. The open work is a port of
  `agent-roles.py`'s rewrite to the `overwrite` shape, a way to tell a subagent's `Stop` from the
  parent's, and the answer on named custom agents.
- **Cursor cannot rewrite at `subagentStart`.** A port would either deny-and-explain (the launching
  agent retries with the right agent) or depend on the unknown `preToolUse` row.
- **Devin is furthest.** With no subagent events, role enforcement would rest on one unknown row.
- The team's commands are also written against Claude Code's `Agent` tool and its
  `subagent_type` argument. A port has to cover the command text, not only the hooks.

## To finish the unknown rows

Cursor and Devin each need an account that can run one prompt. The test is the one used for
Antigravity: attach a logging hook to every candidate event, ask the agent to launch one subagent
that replies with one word, read the log, then repeat with a hook that rewrites the launch.
