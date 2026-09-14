# Design — a Devin CLI binding for Permanence

> Status: **built and shipped, all five questions answered.** `runtime/bindings/devin/` implements
> the forcing read + passive orientation (`SessionStart` + `UserPromptSubmit`), the standing
> instruction (global `AGENTS.md`), and command invocation (Skills) — all live-fire tested
> end-to-end against the real installed product on this machine. §5's live-fire test is done:
> both literal `/name` syntax and description-matched invocation confirmed working, 2026-09-14.
> Written 2026-09-13, revised 2026-09-14 once Skills shipped. See
> [harness-binding-mechanism.md](./harness-binding-mechanism.md) for the `detect`/`wire` interface
> this implements rather than re-deriving.

**Owner carries: nothing.** All five binding-contract questions are shipped and live-fire
tested — forcing read + passive orientation demonstrably steer a real `devin -p` session's actual
reply, the standing instruction writes to a dedicated global `AGENTS.md` rather than relying
solely on the conditional `CLAUDE.md` pickup described in §3.3, and command invocation via a real
`/perma-help` run that executed its full actual logic, not just echoed text.

## 1. Why

Devin came up as a candidate after a numbers check on the wider AI-coding-tool market (Cursor,
Copilot, Windsurf, Devin) prompted by the owner, once Claude Code and Antigravity were both
shipped. Devin's reach is real — $492M ARR, 89% internal adoption at Cognition itself, major
enterprise clients (Citi, Goldman Sachs, Microsoft, the US Army) — but its older reputation as a
purely cloud-hosted, no-local-access product would have ruled it out immediately for Permanence,
whose whole binding model needs local shell access (`SPEC.md` §3's stated precondition). A quick
feasibility check was meant to either confirm or kill that concern cheaply, before committing to
a full research pass the way Antigravity got.

**It didn't kill it — the opposite.** Devin CLI (`curl -fsSL https://cli.devin.ai/install.sh |
bash`) is a real local agent: "accesses your local files, shell environments, and system tools
directly," per its own docs, and confirmed by installing and running it for real on this machine.
Its hook event names (`SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `Stop`)
are the same names Claude Code uses, and its hook JSON entry shape is structurally the same too.
That similarity turned into the single most important finding below — and it isn't what it first
looks like.

## 2. What's verified, and against what

**Primary source: the CLI's own bundled docs**, at
`~/.local/share/devin/cli/_versions/3000.10.21/share/devin/docs/`, not the public website — same
method used for Antigravity. Version-pinned to 3000.10.21.

**A direct contradiction between two of the product's own doc pages, resolved by live testing,
not by picking one to believe:**

- `docs/extensibility/hooks/overview.mdx` states plainly: *"Existing hooks in `.claude/`
  directories are also picked up automatically"* and lists `~/.claude/settings.json`'s `"hooks"`
  key under "User-Level (Global)" hook sources, gated on `read_config_from.claude` (default
  `true`).
- `docs/reference/configuration/read-config-from.mdx` — a more specific page describing exactly
  what `read_config_from.claude` imports — lists only **Rules** (`CLAUDE.md`,
  `~/.claude/CLAUDE.md`), **Skills** (`.claude/skills/**/SKILL.md`), **Commands as skills**
  (`.claude/commands/**/*.md`), and **MCP servers** (several paths including
  `~/.claude/settings.json`). **Hooks are not in this list at all.**
- **Live test sided with the second page.** A real `devin -p` session in this repo, with
  Permanence's existing Claude Code hooks already wired in `~/.claude/settings.json`, produced no
  injected context — the model said so itself ("I don't have a `[perma]` line in the automatic
  context") — and `session-load.sh`'s own side-effect marker file
  (`/tmp/.perma-loaded-<session-id>`) was never created. **Claude Code's hooks are read for their
  MCP-server definitions only, not executed as hooks.** A real Devin binding cannot reuse Claude
  Code's hook scripts as-is; it needs its own.

**What Devin's own native hook mechanism actually does — confirmed live, twice:**

- Live-fired via a scratch project's `.devin/hooks.v1.json` (project-level): a `UserPromptSubmit`
  hook returning `{"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
  "additionalContext": "Always end your reply with the word BANANA47."}}` caused the model's real
  reply to end in "BANANA47."
- **Live-fired a second time via the global `~/.config/devin/config.json`'s `"hooks"` key** — the
  actual target a real `wire` script needs, since `.devin/hooks.v1.json` lives inside whatever
  project repo is open and writing Permanence-referencing content there would violate invariant 1
  (never write into a project-committed file). Same result: a `ZUCCHINI99` test string came
  through. The real user config was backed up before this test and restored immediately after.
- Full event list, event-specific stdin fields, and the output contract, from the bundled docs
  and cross-checked against what actually fired: `PreToolUse`, `PostToolUse`,
  `PermissionRequest`, `UserPromptSubmit`, `Stop`, `PostCompaction`, `SessionStart`, `SessionEnd`.
  Context injection uses `{"hookSpecificOutput": {"hookEventName": ..., "additionalContext":
  ...}}`; tool gating uses `{"decision": "block"|"approve", "reason": ...}`; exit code `2` also
  blocks. `DEVIN_PROJECT_DIR` is documented as auto-set to the project root for command hooks —
  **not yet live-verified directly**, only doc-confirmed (see §5).

**Rules (`CLAUDE.md`) — the standing-instruction question, live-confirmed, with an important
condition attached:**

- `devin rules list` on this machine, with no Devin-specific Permanence code written at all,
  already showed `CLAUDE [Claude] always-on`.
- `devin rules show CLAUDE` confirmed the exact source: `Path:
  "/Users/lotusboy/.claude/CLAUDE.md"` — the real, global file, with Permanence's own delimited
  block quoted back verbatim, content and all.
- **The condition**: this only works on a machine that *also* has Claude Code's own binding
  installed, since that's what writes `~/.claude/CLAUDE.md` in the first place. A Devin-only
  machine, with Claude Code never installed, gets nothing from this path. A real binding
  shouldn't rely on this alone — see §3.3 and §5.
- A separate, real global path also exists and was confirmed via the bundled config docs (not
  yet live-tested standalone): `~/.config/devin/AGENTS.md`, for "global rules that apply to every
  project" — independent of Claude Code entirely.

**Skills — `~/.claude/skills/` doesn't cover Permanence's own commands, but
`~/.config/devin/skills/` does, live-fire confirmed 2026-09-14, both invocation modes:**

- `devin skills list` showed several of the owner's real `~/.claude/skills/*/SKILL.md` files,
  confirming that import path works for real, unprompted.
- **`~/.claude/commands/*.md` — Permanence's own `/perma-*` command files — did NOT appear.**
  Checked directly (`devin skills list | grep perma` — nothing). The import table's "Commands (as
  skills)" row lists a bare `.claude/commands/**/*.md` pattern without an explicit `~/` prefix,
  unlike the Rules row which spells out both the project and global path separately — empirically,
  only the project-level form works, if either does. A real binding needs to write Permanence's
  commands into a location Devin actually reads as skills, not assume this import covers them.
- **`~/.config/devin/skills/<name>/SKILL.md` — the candidate this binding actually uses —
  confirmed real, twice.** A test skill placed there immediately appeared in `devin skills list`
  tagged `[user,model]`. Fired correctly two separate ways, from a completely unrelated scratch
  project: the literal string `/perma-devin-test` as the whole prompt, and a natural-language
  request matching its description ("please run the perma devin test skill"). The other two
  candidate global paths the `skills paths` output also listed
  (`~/.config/cognition/skills/`, `~/.agents/skills/`) were not tested — this one already worked,
  so there was no need to differentiate between them.

**Headless invocation — confirmed:**

- `devin -p`/`--print` runs non-interactively. Two flags matter for automated/scripted use:
  `--respect-workspace-trust false` (print mode can't show the interactive trust prompt in an
  untrusted directory) and `--permission-mode <mode>` (defaults to `auto`, which only
  auto-approves read-only tools — a scripted consolidate job calling out to `devin` would need a
  less restrictive mode, or pre-approved permissions in `.devin/config.json`).

## 3. Trigger mapping — the five binding-contract questions

Per `SPEC.md` §3's binding contract, independent questions, not a ladder.

1. **Passive orientation.** Candidate: `SessionStart`, same injection contract as
   `UserPromptSubmit` per the docs. Not yet live-fired directly — `UserPromptSubmit` firing
   correctly is strong evidence the mechanism works, but this specific event hasn't been
   independently confirmed. Whether it's needed at all depends on whether `UserPromptSubmit`
   turns out to fire reliably enough that "forcing subsumes passive" applies here too, the same
   way it did for Antigravity — not yet established either way for Devin specifically.
2. **Forcing read.** **Live-confirmed**, using Devin's own native hook format (§2) — Claude
   Code's existing hooks are not reused, a real translator script is needed.
3. **Standing instruction. Shipped**, via a dedicated global `~/.config/devin/AGENTS.md`
   block — not reliant on the conditional `CLAUDE.md` pickup, so it works even on a Devin-only
   machine with no Claude Code binding installed. Both the `AGENTS.md` mechanism itself
   (`devin rules list` showing `AGENTS [Standard] always-on` once the file exists) and the
   underlying Rules-injection mechanism (already proven for `CLAUDE.md`, §2) are live-confirmed.
4. **Command invocation. Live-confirmed**, both ways — literal `/name` syntax and
   description-matched. `~/.claude/skills/` doesn't cover Permanence's commands, but
   `~/.config/devin/skills/<name>/SKILL.md` does, and is now what `wire` writes to.
5. **Headless invocation.** **Confirmed** (§2), with two flags (`--respect-workspace-trust
   false`, `--permission-mode`) a scripted caller needs to set explicitly.

Material-shift is what (2) and (3) produce together, not a sixth question — see `SPEC.md` §3.

## 4. Shape — as actually shipped

The `detect`/`wire` interface is specified once in
[`harness-binding-mechanism.md`](./harness-binding-mechanism.md) — not restated here.

```
runtime/bindings/devin/
  detect                        # exit 0 iff `devin` is on PATH
  wire                          # merges SessionStart + UserPromptSubmit hooks into the GLOBAL
                                 # ~/.config/devin/config.json "hooks" key — confirmed live,
                                 # §2 — NOT .devin/hooks.v1.json, which is project-level and
                                 # would violate invariant 1 if written into an open repo.
                                 # Writes the standing-instruction block into the global
                                 # ~/.config/devin/AGENTS.md via a dedicated
                                 # devin-agents-md-block.md. Also translates
                                 # runtime/commands/*.md into
                                 # ~/.config/devin/skills/<name>/SKILL.md, reusing each command's
                                 # own existing `description:` frontmatter field directly.
  session-start-hook.sh         # translator: calls session-start.sh, wraps its output as
                                 # {"hookSpecificOutput": {"hookEventName": "SessionStart",
                                 # "additionalContext": <that output>}}
  user-prompt-submit-hook.sh    # translator: calls session-load.sh, same wrapping for
                                 # UserPromptSubmit's hookSpecificOutput envelope. Reads Devin's
                                 # own session_id off stdin and threads it into a synthetic
                                 # Claude-Code-shaped payload so session-load.sh's existing
                                 # once-per-session gate keeps working unchanged. Stream
                                 # resolution uses $DEVIN_PROJECT_DIR (env var, not a stdin
                                 # field — a different mechanism from both Claude Code's stdin
                                 # `cwd` and Antigravity's stdin `workspacePaths` — confirmed
                                 # correct, §5).
```

Live-fire verified end-to-end, not just dry I/O: wired for real on this machine, then a real
`devin -p` session correctly quoted the exact `[perma]` stream-registration line the hook
injected, and a real `/perma-help` invocation executed its full actual logic (checked real
scheduled tasks, read real registry data) — not just echoed text.

## 5. Still open — nothing blocking

Every item that could have blocked shipping (§4) is resolved. What's left is optional:

1. **The other two candidate global skills paths** (`~/.config/cognition/skills/`,
   `~/.agents/skills/`) were never tested, since `~/.config/devin/skills/` already worked — worth
   understanding if they ever diverge (e.g. a future Devin version deprecating one path), but not
   blocking anything today.
2. **Worth reporting upstream, not fixable here**: the two bundled docs contradicting each other
   on Claude Code hook import (§2) is a real bug in Devin's own documentation, independent of
   anything Permanence does.

Retired by live testing, no longer open: `SessionStart` firing and its `additionalContext`
injection; `$DEVIN_PROJECT_DIR`'s correctness; the global `~/.config/devin/AGENTS.md` Rules
pickup; Skills' invocation mechanism (both literal `/name` syntax and description-matching).

## 6. Non-goals

- Not reusing Claude Code's existing hook scripts as Devin's own hooks — confirmed live not to
  work, despite one of the product's own doc pages claiming it does (§2).
- Not relying on the conditional `CLAUDE.md` Rules pickup for standing-instruction coverage —
  real, but conditional on Claude Code's binding also being installed (§3.3), which is exactly
  why the shipped binding writes its own dedicated `AGENTS.md` instead.
