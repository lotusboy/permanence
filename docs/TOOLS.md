# Every command and script, on one page

Two groups. **Core** is Permanence itself: streams, session loading, the daily and periodic
commands. It works on every supported tool. **Team** is the experimental project team added in
v1.6.0. It works in Claude Code only, and only in a repository whose stream holds a
`repo/binding.json` ([PROJECT-TEAM.md](./PROJECT-TEAM.md)).

`/perma-help` prints the commands installed on your machine and which background pieces are
switched on. This page is the fixed reference.

## Commands

| Command | Group | What it does |
|---|---|---|
| `/perma-startup` | core | Morning: where you left off in this project, and two or three next options. Read-only. |
| `/perma-shutdown` | core | Evening: writes where things stand into the stream and hands back done, in flight, first move tomorrow. |
| `/perma-brief` | core | Current state across all your streams. Read-only. |
| `/perma-list` | core | Lists every registered stream. Read-only. |
| `/perma-register` | core | Registers an existing project as a stream, seeded from its README. |
| `/perma-unregister` | core | Removes a stream and its registry row. Asks first. |
| `/perma-register-group` | core | Registers several repos as one programme group with a shared plan-and-status folder. |
| `/perma-consolidate` | core | Periodic tidy, part one: reads every stream and writes a report of proposed changes. Changes nothing. |
| `/perma-consolidate-review` | core | Periodic tidy, part two: you decide each proposal, then the accepted ones are applied. |
| `/perma-orchestrate` | core | Looks for ideas converging across streams and proposes them. Never edits a stream. |
| `/perma-contents` | core | Regenerates the `CONTENTS.md` file inventories. |
| `/perma-emit` | core, opt-in | Sends a note from this project to your other open sessions. |
| `/perma-upgrade` | core | Upgrades the machinery to the latest release; shows the plan first. |
| `/perma-help` | core | Lists the installed commands and what is switched on. |
| `/perma-health` | team | Rewrites the repo's health register and lists the parts that are ready. Never starts work. |
| `/perma-refactor` | team | Restructures one part behind byte-identical gates. |
| `/perma-change` | team | Makes one change from a work order behind predicted-moves gates. |

## Scripts in `runtime/`

You rarely run these by hand: hooks, commands and the installer call them. Each script's header
comment is its full reference.

Five tools are a `.sh` file you call and a `.py` file beside it that does the work: `decision`,
`spend`, `ratify`, `save-report` and `predict-gate`. The tables name the `.sh`.

### Core: session and streams

| Script | What it is for |
|---|---|
| `session-start.sh` | Session-start hook: resolves the stream for the working folder and says what to load. |
| `session-load.sh` | First-prompt hook: forces the read of the stream's files. |
| `resolve-stream.sh`, `resolve-path.sh` | Look up a folder's stream, or a stream's folder, in `_meta/REGISTRY.md`. |
| `generate-contents.sh` | Rebuilds the `CONTENTS.md` inventories. |
| `perma-help.sh` | What `/perma-help` prints. |

### Core: install, upgrade, backup, schedule

| Script | What it is for |
|---|---|
| `install.sh` | Wires Permanence into each AI tool found on the machine. Safe to re-run. |
| `bindings/<tool>/detect`, `wire` | One pair per supported tool; `install.sh` runs them ([TOOL-SUPPORT.md](./TOOL-SUPPORT.md)). |
| `update.sh` | The engine behind `/perma-upgrade` ([UPGRADE.md](./UPGRADE.md)). |
| `make-backup.sh` | Makes one encrypted backup file of the whole Permanence. |
| `nightly-consolidate.sh`, `schedule-task.sh` | The scheduled read-only consolidation, and the helper that schedules it. |
| `shutdown-nudge.sh` | Optional weekday reminder to run `/perma-shutdown`. |
| `migrate-from-brain.sh` | One-time migration for an install from before the rename. |

### Core: optional extras

| Script | What it is for |
|---|---|
| `emit-event.sh`, `events-listen.sh`, `stop-listen.sh` | Events between your open sessions (`/perma-emit`). Off until you add the two hooks. |
| `predict-gate.sh` | The predicted-moves gate: refuses any measured move nobody predicted ([PREDICT-GATE.md](./PREDICT-GATE.md)). Usable in any repo, with or without the team. |
| `save-report.sh` | Saves an agent's report to a file byte for byte. |

### Team (experimental, Claude Code only)

| Script | What it is for | Writes |
|---|---|---|
| `agent-roles.py`, `team_roles.py`, `agent-roles.json` | The role table and the three hooks that enforce it. | `runtime/logs/agent-roles.log` |
| `team-preflight.py` | Checks a repo's binding before a job or the health watch. | nothing |
| `health-signal.py` | Writes a repo's health register from rules in the binding. | the register, in the stream |
| `decision.sh` | Records each question put to the owner, the recommendation, the answer and the outcome. | `<stream>/decisions/ledger.jsonl`, `DECISIONS.md` |
| `spend.sh` | Records measured tokens per agent, grouped into waves with a ceiling. | `<stream>/spend/ledger.jsonl` |
| `ratify.sh` | Records which entries of a closed vocabulary two blind readers agreed on. | `<stream>/ratifications/ledger.jsonl` |
| `ops-event.sh` | Appends one event to the repo's ops ledger. | `<stream>/repo/ops/events.jsonl` |
| `ops-gap.sh` | Says how many commits the ops ledger is behind. | nothing |
| `repo-hooks.sh` | Writes the post-commit hook that calls `ops-gap.sh`, in repos the owner owns. | `.git/hooks/post-commit` in those repos |

`runtime/agents/` holds the eight agents the team's roles are filled by, and `runtime/roles/` holds
the role an owner can give the main session (`pm.md`).
