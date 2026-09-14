# SPEC — Permanence, harness-independently

> The contract that lets any capable agent rebuild and operate this system: clone → read this → bind §3 to the target harness. Three layers: data model, invariants, runtime contract. The Claude Code binding (the current implementation) is noted at the end of §3. Conventions in full: [README.md](./README.md). Written 2026-06-11 (hardening item 5).

## 1. Data model

- **Permanence is one git repository** at `~/permanence`, local-first, owned by exactly one human (the owner). It is his externalised working memory: project state that must survive across sessions, days, and context loss.
- **A stream** is a directory holding one ongoing concern, in one of two shapes:
  - **Customer stream** — `<customer>/<division-or-project>/` (e.g. `home/bathroom/`): engagement-scoped. The test: is this *about the customer*?
  - **Asset/internal stream** — `<area>/<asset>/` (e.g. `home/kitchen/`): reusable across customers. The test: is this *about the asset*?
- **Canonical files per stream** (only these at a stream root; other docs go in named subfolders): `README.md` (orientation), `PROJECT.md` (shape + current state; carries a `Last updated` date), `STRATEGY.md` (fronts + plays), `PEOPLE.md` (who's who), `QUESTIONS.md` (open questions; closed ones keep `[CLOSED YYYY-MM-DD: answer]` markers), `LOG.md` (chronological, append-only).
- **A stream exists iff it has a `PROJECT.md`** — that file is the discovery key for every automated pass. `_meta/` (the perma-evolution stream) participates; its chronology is the **root** `LOG.md`. A folder deliberately kept outside stream discovery (no `PROJECT.md`) is simply exempt from maintenance passes — nothing requires every folder under Permanence to be a stream.
- **The registry** — `_meta/REGISTRY.md` — maps workspace absolute paths → streams (longest-prefix match). Pointer direction is load-bearing: Permanence references projects, never the reverse.
- **The group registry (optional)** — `_meta/GROUPS.md` — maps workspace absolute paths → a **programme group** and a `role` within it (same longest-prefix match). Answers a different question from the registry: not "which stream does this workspace load?" but "which programme does it report into, and as what?". A group names a **target repo**, a **programme folder** inside it, and a **task doc** owning the procedure. The folder is the one *outward-facing* artefact in this system — a plan-and-status trail for a reader who is not in the work (a programme manager or director) — and therefore the only place Permanence's private register does not apply. Absent file, or example rows only, = feature off.
- **Derived artefacts** (gitignored, rebuilt freely): `CONTENTS.md` indexes, `.consolidation/` reports, `runtime/logs/`, `.perma-lock`.
- **Staleness model:** `PROJECT.md` carries *current* truth and is overwritten section-wise with a bumped date; `LOG.md` carries *chronology* and only grows. A LOG entry dated after its stream's PROJECT `Last updated` = the project file is behind — the primary decay signal.

## 2. Invariants

1. **One-way flow.** No committed file in any project repository may reference Permanence's paths, names, or contents. Permanence reads team-facing context; nothing references back. (Machine-local harness config under `~/.claude/` is perma-adjacent and exempt — it is in no repo.)
2. **Append, don't rewrite.** LOGs grow; questions close with markers, not deletion; superseded claims are marked superseded (the one sanctioned deletion is pruning a stale inference during ratified consolidation).
3. **The people-rule.** Notes on identifiable colleagues: observable behaviour + work impact as fact; the *why* as an explicitly dated, provisional inference, revisited and closed (confirmed / revised / wrong / pruned); never commentary on protected characteristics or fixed character; written as if the subject will one day read it. Enforced socially by convention, mechanically by a heuristic pre-commit guard, and historically by the pre-remote rewrite policy (README → "The four conventions", bullet 1).
4. **Voice transposition.** Conversation may be blunt; anything *persisted* is rendered in a gentle, accurate register — same substance, safer key.
5. **Human ratification for state-changing maintenance.** Automated passes propose; only a human-reviewed apply changes Permanence, as a single revertable `--no-ff` envelope. The procedure — take `.perma-lock` before editing, release it after, work in an isolated worktree — is followed by the model executing the prompted steps in `perma-consolidate-review.md`; nothing currently checks the lock mechanically before a write, so it is a convention this system relies on the model to honour, not a guarantee enforced independently of it. Nightly generation passes are scoped to write only under `.consolidation/` via the tool grant they run with (`Write($PERMA/.consolidation/*)` in `nightly-consolidate.sh`) — a real permission boundary, though enforced by that grant rather than by the filesystem itself.
6. **Dates are arbitrated by git commit timestamps**, not memory or context clues.
7. **Custody.** Permanence and any backup of it live only on infrastructure the owner personally controls; any off-machine copy is encrypted such that the provider never holds plaintext (see the hardening plan's item 6 — gated).
8. **Programme groups converge; they never couple.** This is a **single-owner, multi-repo** mechanism, not a multi-person one: `members` are read via `git -C <path> log`, which only works for repos the person running the update has checked out locally, and the update lock (`.updating.lock`) is per-clone, not shared — it cannot coordinate two different people's separate machines. Use it for one owner spanning several of their own repos (e.g. related internal assets); it is not a substitute for real team collaboration across separate laptops, which this system does not yet attempt. Where `_meta/GROUPS.md` is in use: a project belongs to **exactly one** group, so resolution is unambiguous. **Any current member may write for the whole group** — a run fills whatever gaps it can see and leaves the rest, and reads of sibling repos are **opportunistic, never required** (an unreachable member is recorded as unreachable, never silently skipped, and never a reason to fail). Progress is watermarked on a **commit sha, not a date**, so same-day re-runs cannot miss work. Leaving sets a `left` date and **never deletes the row** — a departed member keeps every entry it wrote; only the aggregate stops including it (invariant 2 applied to membership). The **report shape and RAG rules are fixed across all groups** (versioned in the task-doc template), because their whole purpose is being scannable side by side; roles, phase numbering and document names are per-programme. Nothing written into the folder may carry private phrasing, a Permanence path, or a read on a person — invariant 1 governs it, and the task doc receives `role` and `members` as inputs precisely so no project file needs to look anything up.

## 3. Runtime contract

**Precondition, independent of any harness:** operating Permanence means actually executing
shell commands against `~/permanence` — `git` (every write ends in a commit), `mkdir`,
`find` — not merely reading and writing files. A harness limited to structured file I/O
(read/write/list, no command execution) cannot honour any of the six triggers below, no
matter how it's bound. This is a capability check to make before binding a harness at all,
not a detail of any one binding.

Any harness operating this Permanence must honour six triggers:

- **Session-start (read).** Resolve the session's working directory through the registry. Match → instruct the session to read that stream's operational files (PROJECT/STRATEGY/PEOPLE/QUESTIONS + LOG tail) and surface any consolidation lock. No match → perma-meta only, plus a one-time offer to register the workspace. Implemented in `runtime/session-start.sh` — harnesses with hooks run it; harnesses without are instructed via a pointer block to read it.
- **Material-shift (write).** During work, update the *active* stream whenever something material changes — decisions, meetings, scope, exchanges that move the picture — without being asked, honouring §2. The active stream is normally the one the working directory maps to; a harness with no meaningful working directory (a desktop AI app) instead sets it by name or by an explicit path (`/perma-startup <name-or-path>`), or creates one from just a name with no path at all (`/perma-register`, which then picks and creates the real folder itself), and it holds until changed.
- **Wind-down (write, human-triggered).** At the end of a working day (`/perma-shutdown`, optionally given a stream name for a working-directory-less session): refresh the active stream's *current state* — `PROJECT.md` surgically, `QUESTIONS.md` for newly-open threads, deliberately **not** `LOG.md` (chronology is captured elsewhere; a daily rewrite would churn it). Resume points must carry an exact re-entry anchor, since their purpose is that tomorrow's reader need not reconstruct where the work stopped. Then, if the workspace resolves to a group under `_meta/GROUPS.md`, follow that group's task doc with `role` + `members` as inputs. Strictly a wind-down: no new work, no investigation, no fixes. Its morning counterpart (`/perma-startup`) is read-only orientation for the same stream. Switching the active stream mid-session must not silently drop whatever the conversation surfaced about the one being left — offer to wind it down first.
- **On-schedule (consolidate).** Nightly read-only convergent pass (`/perma-consolidate`) producing a report under `.consolidation/`; a human-in-the-loop review (`/perma-consolidate-review`) applies accepted items under invariant 5. Unreviewed reports and failed runs are surfaced by the morning brief — the schedule must never depend on remembering.
- **On-commit (guard + refresh).** Pre-commit: the people-rule heuristic guard. Post-commit: regenerate derived `CONTENTS.md` indexes. (Reserved, deliberately unbuilt: an orchestration pressure gauge that would trigger `/perma-orchestrate` automatically instead of leaving it human-triggered.)
- **On-upgrade (read + propose, human-triggered).** User-triggered (`/perma-upgrade`), never scheduled — pulling a new template release is a deliberate act, not ambient maintenance. Reads the configured source (`runtime/.update-source`) and the installed version (`_meta/VERSION`), fetches and diffs against the latest release, and proposes a plan: machinery changes to apply, any file the owner has customized that the template also changed (negotiated per file, never silently overwritten), and any `CHANGELOG.md` migration note that may apply to the owner's actual streams. Applies only on explicit accept, under invariant 5 — machinery and any accepted stream-content migration land as separate, clearly-labeled commits. Implemented in `runtime/update.sh` (the mechanical dry-run/apply engine) + `runtime/commands/perma-upgrade.md` (the negotiation and migration-notes judgment layer).

A separate, divergent pass — `/perma-orchestrate` — is **event/human-triggered, never scheduled** (an automatic trigger would need the pressure gauge noted above, which doesn't exist yet): it proposes cross-stream emergent hypotheses into `_meta/emergent.md` and never edits source streams.

### The binding contract

A harness is bound by answering five questions. They are **not a ladder** — each is answered
independently, and the answers determine only one thing worth reporting to the owner: *what
they still have to do by hand.*

1. **Passive orientation.** Is there a point at session open where text can be placed into
   context?
2. **Forcing read.** Is there a point *before the model answers* where text can be placed into
   context? This is the reliable one — a passive note at session open is easy for a model to
   skim past. **Forcing subsumes passive**: a harness with only one usable injection point
   binds it here and omits (1) entirely. That is a complete binding, not a degraded one.
3. **Standing instruction.** Is there a persistent, per-machine file the harness always reads
   (`CLAUDE.md`, `GEMINI.md`, an `AGENTS.md`-style global) into which the material-shift rule
   can be written once? **This is the capability whose absence is silent.** Without it the
   model never learns to update the stream unprompted, nothing raises an error, and the failure
   surfaces only as an empty `LOG.md` weeks later. Verify this one first, not last.
4. **Command invocation.** Can the owner invoke a named procedure (`/perma-shutdown`)? Required
   only for the human-triggered triggers; the ambient ones ride (2) and (3).
5. **Headless invocation.** Is there a non-interactive CLI (`<tool> -p "<prompt>"`) the
   scheduler can call? A capability check and one config value — not a translator.

**Material-shift is not a sixth question.** It is what (2) and (3) produce together: the forcing
read carries current state, the standing instruction carries the rule, and the harness's
ordinary file/git tools do the rest. **On-commit and on-schedule are not harness questions at
all** — git fires the first, the OS scheduler the second; neither consults an AI tool's config.

**A binding is a directory**, `runtime/bindings/<harness>/`, discovered and wired by
`runtime/install.sh` without editing it — Claude Code included, no special case. The mechanism
itself is specified in `design/harness-binding-mechanism.md`, not restated here. The core —
`session-start.sh`, `session-load.sh`, `runtime/commands/*.md`, the block files — emits
harness-neutral text and never varies per harness regardless of which binding wires it in.

Numbered tiers are deliberately not used: a tier is ordinal, but these five are a set, so two
harnesses with opposite failure modes (one reads manually and writes automatically; one reads
automatically and silently never writes) would collapse to the same label — hiding exactly the
difference that matters most. Each binding below instead states plainly what the owner carries.

**Claude Code binding (the reference implementation — all five answered).** Implemented as `runtime/bindings/claude-code/{detect,wire}`, like any other binding. (1) SessionStart hook in `~/.claude/settings.json` → `runtime/session-start.sh`; (2) UserPromptSubmit hook → `runtime/session-load.sh`, forcing the actual read of PROJECT/QUESTIONS/LOG-tail onto the first message; (3) `CLAUDE.md` carries a managed delimited block (also the fallback for Desktop/Cowork); (4) commands installed from `runtime/commands/` (copy-on-install + version marker); (5) the `claude` CLI, called by `runtime/nightly-consolidate.sh` under a cross-platform scheduler (`runtime/schedule-task.sh`: launchd on macOS, cron on Linux/WSL, `schtasks.exe` on native Windows via Git Bash). `permissions.additionalDirectories` includes `~/permanence`. Material-shift writing rides (2) + (3), per the contract above. **Owner carries: nothing.** **Rebuild elsewhere = clone → run `runtime/install.sh`, which wires both hooks and the permission itself — only a machine with no `python3` needs the printed snippet pasted by hand.**

**Antigravity binding (four of five answered).** Implemented as `runtime/bindings/antigravity/`. (1)+(2) a `PreInvocation` hook carries both — no separate passive-orientation event exists, and none is needed (forcing subsumes passive, confirmed live for this binding); (3) a managed delimited block in the global `~/.gemini/GEMINI.md`; (5) `agy`'s headless mode. (4) command invocation via Skills is not yet built — see `design/antigravity-binding.md` §5. **Owner carries: the command layer** (`/perma-*` commands have no home here yet).

**Devin CLI binding (four of five answered).** Implemented as `runtime/bindings/devin/`. (1) a `SessionStart` hook; (2) a `UserPromptSubmit` hook, forcing the actual read; (3) a managed delimited block in the global `~/.config/devin/AGENTS.md`, written directly rather than relying on Devin's own (confirmed, but conditional on Claude Code's binding also being present) pickup of `~/.claude/CLAUDE.md`; (5) `devin -p`'s headless mode. (4) command invocation via Skills is not yet built — see `design/devin-binding.md` §5. **Owner carries: the command layer** (`/perma-*` commands have no home here yet).

**Cursor binding (four of five answered).** Implemented as `runtime/bindings/cursor/`. (1)+(2) one `sessionStart` hook carries both — live-confirmed by a prompt that never mentioned Permanence still causing an unprompted, accurate read of real stream content; (4) commands translated into `~/.cursor/skills/<name>/SKILL.md`, confirmed invokable by literal `/name` syntax. (3) standing instruction is not answered by a dedicated mechanism — no working global rules/`AGENTS.md` file was found despite three live attempts, see `design/cursor-binding.md` §5. (5) `agent -p`'s headless mode. **Owner carries: the ongoing half of the standing instruction** (whether unprompted mid-session updates work is still unconfirmed).

**`AGENTS.md`-reading tools (question 3 only).** `runtime/install.sh` also writes a delimited pointer block (`runtime/agents-md-block.md`) into whichever *global*, per-machine `AGENTS.md`-style config paths already exist on the machine — never into a project-committed `AGENTS.md`, which invariant 1 forbids (that file is meant to be shared with every contributor). This answers question 3 and nothing else: the standing rule lands, so the write side works, but there is no forcing read and no command layer. **Owner carries: orientation** — say *"good morning Permanence"* (or run `/perma-startup <name-or-path>`) at the start of a session, since nothing injects it automatically. A tool reading none of these files carries everything: the manual pointer is the whole binding. See `docs/TOOL-SUPPORT.md`.
