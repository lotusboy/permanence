# Every command and script, on one page

Everything here is Permanence's core: streams, session loading, the daily and periodic commands. It
works on every supported tool. The project team (the team commands, the gate and the ledgers) was a
second group here until v1.12.0. It moved to [bakehouse](https://github.com/lotusboy/bakehouse), a plugin for Claude Code.

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

## Scripts in `runtime/`

You rarely run these by hand: hooks, commands and the installer call them. Each script's header
comment is its full reference.

### Core: session and streams

| Script | What it is for |
|---|---|
| `session-start.sh` | Session-start hook: resolves the stream for the working folder and says what to load. |
| `session-load.sh` | First-prompt hook: forces the read of the stream's files. |
| `context-meter.sh` | Every-prompt hook: from 40% of a 1M window or 60% of a 200k one (`runtime/.context-warn` changes it), or at a drift count of 5, says to write back and compact. |
| `pre-compact.sh` | Compaction hook: logs each compaction, and gives the summary standing instructions (`runtime/.compact-instructions` replaces them). |
| `resolve-stream.sh`, `resolve-path.sh` | Look up a folder's stream, or a stream's folder, in `_meta/REGISTRY.md`. |
| `list-streams.sh` | The one list of streams: every folder with a `PROJECT.md`, `perma-meta` first. `--count` counts them; `--check` names a registered stream with no `PROJECT.md`. |
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

### Core: git hooks (`.githooks/`)

| Hook | What it is for |
|---|---|
| `pre-commit` | The people-rule guard: checks what you are about to commit in your notes. |
| `post-commit` | Refreshes the `CONTENTS.md` inventories. |
| `pre-push` | Stops a push to the public template when a commit it would add contains a word from your private list, `~/permanence/_personal/private-words.txt`. Does nothing without that file, and ignores a push to anywhere else. |

### Core: optional extras

| Script | What it is for |
|---|---|
| `emit-event.sh`, `events-listen.sh`, `stop-listen.sh` | Events between your open sessions (`/perma-emit`). Off until you add the two hooks. |

`runtime/roles/` holds the role an owner can give the main session (`pm.md`). Permanence ships no
agents and no skills since v1.12.0: they moved to bakehouse with the team.
