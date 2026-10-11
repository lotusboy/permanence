---
description: "Refactor one part of the current repo — preflight, the architect's restructure-or-accept decision for the owner, then one engineer step at a time behind the binding's gates, a reviewer the PM dispatches, a fix round and one pull request per step. Steps are byte-identical, except meaning changes the owner named in the decision, which are gated by predicted moves. Every repo fact comes from the repo's binding. Usage: /perma-refactor <part>, where <part> is a part id from the repo's health register. Trigger phrases: \"refactor <part>\", \"restructure <part>\", the owner accepting a ready part from /perma-health."
harness: claude-code
---

# Permanence — Refactor

The `refactor` job for *this* repo, on one part. You are the PM. Agents do the building and the
reviewing. The owner takes every decision.

A refactor has two kinds of step:

- a **byte-identical** step restructures code and changes no output;
- a **meaning-change** step changes an output on purpose. It runs only when the owner named that
  meaning, and the moves it expects, in the decision. It is gated by predicted moves.

A part's shape changes as more of the problem is uncovered. A refactor is growth, not failure.

**Facts come from the binding.** Every repo path, command, gate, branch form, tracker, record folder
and owner rule comes from the repo's binding, `<stream>/repo/binding.json`, from the repo files its
pointers name, from the health register, or from the tracker item. Never use a path, command,
threshold, gate or part name from anywhere else. A copied fact would bind every repo to the one it
came from. If a step needs a fact that none of these gives, stop and name the missing field.

**A ready part is an offer, never an order.** This command starts only when the owner has said
`/perma-refactor <part>`, or has asked for the part to be refactored. Nothing here runs on the
signal alone.

**No dispatch without the owner's go on the spend.** Before each agent dispatch, state the estimated
tokens and wait for the owner's go.

## Words used below

- **`{root}`**: the repo root, `git rev-parse --show-toplevel`. Stay in it. Run every Permanence git
  command as `git -C ~/permanence …`; never `cd` away from the repo.
- **The binding**: `~/permanence/<stream>/repo/binding.json`. `<stream>` comes from
  `~/permanence/runtime/resolve-stream.sh {root}`.
- **The register**: `~/permanence/<stream>/repo/<binding.register>`.
- **The default branch**: run `git fetch` first. Then `git rev-parse --abbrev-ref origin/HEAD` gives
  `origin/<default>`. Every "merged" and every "on the default branch" below means on
  `origin/<default>`, never a local branch. If `origin/HEAD` is not set, ask the owner which branch
  pull requests go into.
- **The tracker item**: the item in `<binding.tracker.file>` whose id matches `binding.tracker.id`
  and equals the part's `decision.backlogId` in the register. It is the job's re-entry state. It holds
  the plan: each step's kind, target and gate type; for a meaning-change step, the meaning and the
  expected moves. Each step's entry records its record folder, its commits, each gate's result and
  its done-mark. The stream holds only a pointer to it, in `WIP.md`.
- **`BASE`** of a step: the head of `origin/<default>` when the step's branch is opened. Record it in
  the step's entry. Later, recompute it as `git merge-base origin/<default> <step branch>`.
- **A pointer** (`file#key` or `file#key.id`): open `file` in the repo root. `file#key` means the
  whole list under the top-level `key`. `file#key.id` means the one item under `key` whose `id` is
  `id`. Each gate item gives its `id`, `command`, `pass` and, if present, `when` and `per`. A gate
  whose `command` is prose, not a command, is a **prose gate**; preflight lists them (check 4).
- **Placeholders.** `{root}`; `{register}` (the register's full path); `{part}`; `{id}` (the tracker
  id); `{n}` (the step number); `{date}` (fixed once, when step `{n}` starts, as `YYYY-MM-DD`; never
  refilled on a later day); `{name}` (a short step name the PM chooses when it opens the branch).
  Leave every `<…>` in a repo-held command for the agent that runs it; the reviewer checks it was
  filled.
- **The record folder** of step `{n}`: `<binding.reviews>` + `<binding.reviewName>`, filled with the
  step's fixed `{date}`. Defaults when the binding omits them: `reviews` is `axis/runs/`;
  `reviewName` is `{date}-{id}-step{n}-review`. The folder sits directly under `reviews`: the role
  hook sends a reviewer back once if no new file appears in a folder there. To find an existing
  folder, match `reviewName` with `*` for `{date}`.
- **Commit trailer.** Every commit this job makes or asks for ends with the session's own
  `Co-Authored-By` line, taken from its attribution instructions. Never hardcode a model.

## The steps

Each step says who does it. "PM" is this session.

### 1. Preflight (PM)

From the repo root, run:

```
python3 ~/permanence/runtime/team-preflight.py refactor <part> --repo "$(git rev-parse --show-toplevel)"
```

- It exits non-zero: show its output and stop. Change nothing. A missing binding means the team does
  not apply to this repo. Say that plainly. Never guess a repo's commands.
- It exits 0: carry on. A `note` line is not a failure. Keep two kinds of note:
  - the prose gates (`check 4`), by id;
  - the role lines (`check 5`): which agent fills `refactor:architect`, `refactor:engineer` and
    `refactor:reviewer`. "The session does it" means you do that role's work yourself and say so in
    the report. The reviewer role never falls to the session.

Then read the binding and the register. The part must be a key under the register's `parts`. If it
is not, stop and list the nearest part ids. Do not invent a part.

### 2. Ownership (PM)

Read `binding.owned`.

- **`true`**: carry on.
- **`false`**: say this to the owner first, before any work:
  - preflight check 6 has confirmed an unconsumed approval in `<stream>/repo/approvals.json` whose
    scope is exactly `{"part": "<part>"}`. Without one, preflight failed: offer to draft a proposal
    for `binding.approver`, as `/perma-health` step 6 does, naming the approver by role, never by a
    person's name;
  - the job can run steps 3 to 5 (re-entry, architect, decision). It stops before step 6, because
    step 6 writes the tracker item, and where a job in another party's repo keeps its plan and step
    state is not yet decided. It stays stopped until that is decided; a binding alone does not
    unblock it;
  - no approval scope covers a meaning change. A meaning-change step in another party's repo is
    offered as its own proposal, never run under this approval;
  - an `accept` decision consumes the approval (step 5);
  - the only output is a pull request. The repo's tracker, hooks and other branches are never
    written. The ops ledger refuses this repo; do not work around it.

### 3. Re-entry (PM)

Find where this part's job stands before doing anything else. Run `git fetch` first.

1. Read `parts.<part>` in the register: its `state` and its `decision`.
2. **`decision.decision` is `restructure`, and `state` is not `ready-again`**: the job is in progress.
   Take `{id}` from `decision.backlogId`.
   1. Read the tracker item on `origin/<default>`. If it is not there, look for step 1's branch (next
      item). If step 1's branch does not exist either, the plan was never opened: go to step 6.
   2. For each step `n` in the plan, in order, decide its status:
      - **done**: its entry on `origin/<default>` carries the done-mark, or its branch is merged
        into `origin/<default>`. The done-mark covers a squash merge, which leaves the branch
        unmerged.
      - **in flight**: not done, and a branch matching `binding.branches.refactor` exists (fill
        `{id}` and `{n}`, use `*` for `{name}`, and run
        `git branch -a -i --list '<pattern>' '*/<pattern>'`; `-i` ignores case, because old branches spell ids in lower case; the second pattern finds the remote).
      - **not started**: neither.
   3. The first step that is not done decides what happens:
      - **in flight**: resume on its branch, at the first output missing, in this order. Never start
        the step again.
        1. Step 1 only: the branch carries no tracker item with the plan → step 6.3, on that
           branch. Never open the branch again.
        2. No step entry from the engineer in the tracker item on the branch → step 7.
        3. No `findings.md` in the record folder (the folder named in the entry; else match the
           folder with `*` for the date) → step 8. A folder without `findings.md` is a review that
           did not finish.
        4. Findings with no `disposition.md` beside them → step 9.
        5. No pull request for the branch → step 10.
        6. A pull request open, not merged → wait for the merge. Say so and stop.
      - **not started**: go to step 6 for that step.
      - **every step done**: go to step 11.
3. **`decision.decision` is `accept`, and `state` is not `ready-again`**: the part was accepted on
   `decision.date` for the reason in `decision.reason`. Say so and stop. Ask the owner whether to
   reopen it; a yes goes to step 4.
4. **`state` is `reshaped`** with an older decision: the earlier refactor is finished. Treat the part
   as ready again only when the register's `state` says `ready-again`. Otherwise say it is finished
   and stop.
5. **Otherwise** (`ready`, `ready-again`, `settled` with no decision, or a reopen): go to step 4.

### 4. Signal and architect (PM, then `role:refactor:architect`)

1. **Signal.** Refresh the register exactly as `/perma-health` steps 3 and 4 do: get the command
   from `binding.signal`, fill it, run it once from the repo root, and show its output. Commit the
   register: `git -C ~/permanence add <register path>`, then
   `git -C ~/permanence commit -m "health(<stream>): register as of <computed.asOf>" -- <register path>`.
   Never `git add -A`. If the part is now `settled`, say so and ask the owner whether to go on.
2. **Architect.** Fill the [architect brief](#architect-brief). Check that no `{…}` and no `[…]`
   field is left. Name the mode in the brief: `RESTRUCTURE` when the part was flagged by fix
   pressure, `REDESIGN` when it was flagged by correction, override or declaration files piling up
   (the step-back Compensation pile signal). State the token estimate and wait for the owner's go.
   Dispatch it with
   `subagent_type: "role:refactor:architect"`. The architect reads and measures only.
3. Record the run (owned repos only):
   `~/permanence/runtime/ops-event.sh agent-run - "architect: <part>" <model> - - <tokens> <seconds> <outcome>`.

### 5. The decision (PM → owner)

Bring the architect's answer to the owner as **one message**, in this order:

1. the problem;
2. its cause;
3. the options — restructure in steps, a smaller part of it, and accept — each with its gate type,
   its size in hours and tokens, and what it leaves unsolved;
4. one recommendation, stated as "do X";
5. one question.

Include a concrete example table: one real input, the output today, the output after each option.
Ask one decision per message. A meaning the owner must define is asked on its own, one meaning at a
time.

If `binding.gates.oneAtATime` is empty, add one line: the binding names no heavy run that must run
alone, so any heavy output check the repo runs outside its gate list is not one of this job's gates.

Before the owner answers `restructure`, show the plan the answer approves: the numbered steps, each
with its kind, target and gate type. Each meaning-change step also names its meaning, as the owner
defined it, and the moves it expects. **A meaning-change step that the plan does not name never
runs.**

When the owner answers, record it:

- **Register.** Write `parts.<part>.decision` as
  `{date: <today>, decision: restructure | redesign | accept, reason: "<the owner's own words>", backlogId: <id>}`.
  Leave `signalAtDecision` to the signal script. Commit the register by its path, with `git -C
  ~/permanence`.
- **`accept`**: `backlogId` is empty unless the owner names an item. When `owned` is false, write
  `"accepted <today>"` into the approval's `consumed` field and commit `approvals.json` by its path.
  Stop here, and say what was recorded.
- **`restructure`**: when `owned` is false, stop here (step 2) once the register is written: no
  tracker id is reserved, because nothing is written to another party's tracker. Otherwise reserve
  the tracker id. Run `git fetch`. Find the highest id matching
  `binding.tracker.id` in `<binding.tracker.file>` on `origin/<default>` and on every branch
  (`git for-each-ref --format='%(refname)' refs/heads refs/remotes`, then `git grep -E` per ref),
  and in every branch name. Take the next one in that sequence. If the form does not make the next
  id obvious, ask the owner. Add one pointer line to the stream's `WIP.md`: the part, the id, and
  "re-entry: the tracker item". Commit `WIP.md` by its path, with `git -C ~/permanence`.
- **`redesign`**: a redesign changes a step's method, so its outputs move on purpose. That is a
  change, not a restructure. Its route is `/perma-change`, not steps 6 to 11 here. Write the
  architect's redesign option into the tracker as a work order: the step it changes, the small-slice
  proof as the first gate, and the corrections it should make unnecessary as the predicted moves.
  Record its id as `backlogId`. Then stop here, and offer `/perma-change <id>`. The owner's go on the
  work order is a separate go.

Order the steps by kind. Each step is merged alone before the next starts.

1. **Pure move**: code moves to the module that owns its job; names and bodies unchanged.
2. **Phase split**: a long function becomes named phases, called in the same order.
3. **Meaning change**: a meaning the owner defined, with its expected moves, named in the plan.
4. **Vocabulary**: one declared table, read by every place that had its own copy.

### 6. Open the step (PM)

Owned repos only. Run `git fetch`.

1. Fix `{date}` for this step. Choose `{name}`. `BASE` is the head of `origin/<default>`.
2. Open the step's branch from `BASE`: `binding.branches.refactor`, filled.
3. **Step 1 only:** the branch's first commit writes the tracker item in `<binding.tracker.file>`:
   the problem, the owner's words, and the plan from step 5 — each step's kind, target and gate type;
   for each meaning-change step, its meaning and expected moves; each step's done-mark empty. Commit
   it by path, with the trailer.
4. Fill the [engineer brief](#engineer-brief) from the tracker item on this branch. Go to step 7.

### 7. Engineer, one step (PM, then `role:refactor:engineer`)

1. Check that no `{…}` and no `[…]` field is left in the brief. State the token estimate and wait
   for the owner's go. Dispatch it with `subagent_type: "role:refactor:engineer"`, on the step's
   branch.
2. **A meaning-change step** runs only when the plan names it. The engineer writes its prediction
   and stops. Bring the prediction to the owner as one decision, before any site is switched. On the
   owner's go, tell the engineer to continue (SendMessage).
3. **An andon** from the engineer — an unpredicted move, a gate that cannot pass, a meaning nobody
   defined — goes to the owner as one decision. The step waits.
4. The engineer cannot start agents. Never ask it to start the reviewer.
5. Record the run (owned repos only), with `{id}` as the task.

### 8. Review (PM, then `role:refactor:reviewer`)

Dispatch the reviewer from this session as soon as the engineer reports. A reviewer started inside
another agent dies when that agent hands back. Fill the [reviewer brief](#reviewer-brief). State the
token estimate and wait for the owner's go. Dispatch it with
`subagent_type: "role:refactor:reviewer"`. Record the run (owned repos only).

Before you treat any agent's work as lost, check its record folder for `findings.md`, its branch and
the ops ledger. An empty folder alone is not proof.

### 9. Fix round (PM, then an engineer)

Send the findings to the same engineer with SendMessage, if it is still running. Otherwise dispatch a
fresh `role:refactor:engineer` with the findings, the branch and the step's brief.

- Fix every ANDON, P0 and P1 finding before the pull request.
- Fix real P2 and P3 findings too. Skip only the cosmetic.
- The engineer re-runs every command gate after the fixes.
- Each prose gate in the step's gate list is re-run on the fix commits by a reviewer: SendMessage to
  the same reviewer if it is still running, otherwise a fresh `role:refactor:reviewer` given only
  the fix diff. Its result goes into the record folder.
- The engineer updates step {n}'s entry in the tracker item with the fix commits and the re-run gate
  results.
- Write `disposition.md` in the record folder: each finding, what was done, and the commit.
- The PM commits the record folder — the reviewer's files and `disposition.md` — on the step's
  branch, by path, with the trailer. The reviewer writes them; it never commits.

### 10. Gates and pull request (PM)

1. Every gate in the step's list has passed after the last commit. Each gate's own `when` applies.
   Each prose gate has a recorded result. The engineer's step entry in the tracker item gives `BASE`,
   the record folder, each gate's result and the step's commits.
2. Push the step's branch and open a pull request into `origin/<default>`, with the repo host's own
   tool. If no tool is available, give the owner the branch name and the pull request text.
3. The owner merges. In another party's repo, that party merges, and may ask for changes first.
4. Tell the owner the result as a win: what now holds, measured.
5. When the step's pull request has merged, go to step 6 for the next step. If this was the last
   step, go to step 11.

### 11. Close (PM)

After the last step's pull request **has merged**:

- **Another party's repo**: write the merged pull request's link into the approval's `consumed`
  field in `approvals.json`, and commit that one file by its path. A consumed approval never starts
  a job again.
- **The owner's repo**: the last step's entry, written by the engineer, marks the whole tracker item
  done. Check that it is there on `origin/<default>`.
- Replace the stream's `WIP.md` pointer line with one line: the part, the tracker id, done. Commit
  `WIP.md`, and the ops ledger when it changed, each by its path, with `git -C ~/permanence`.

## The two gate types

Every step passes one of these. Before any change, run BASE against BASE and prove it identical. A
gate that differs from itself is not a gate.

**Byte-identical** — pure move, phase split, vocabulary. The gate list is
`binding.gates.byteIdentical`. Code moves verbatim. Every gate passes, and no output changes. Any
output change stops the step. Never edit a test or an output to make a gate pass. Where a gate's
`pass` text allows a "predicted", "intended" or "named" move, transition or flip, that allowance does
not apply: 0 moves, 0 transitions, 0 flips.

**Predicted moves** — a meaning-change step named in the plan. The gate list is
`binding.gates.predictedMoves.gates`. The prediction file is
`binding.gates.predictedMoves.prediction`, inside the step's record folder.

1. Write the prediction before switching any site, using both methods:
   - a **shadow run**: the old rule and the new rule side by side over the repo's real inputs, the old
     result returned, every disagreement recorded, the calls per site counted, and every site no
     input reaches listed;
   - a **static scan** of every stated value in the latest outputs and their data files, rows
     included, for the cases no input reaches.
2. The prediction goes to the owner before any site is switched. Every predicted move must be one
   the plan named; a move the plan did not name is a new decision for the owner.
3. Then measure, and read the result back exactly. Every moved line must be one the prediction named.
4. An unpredicted move stops the step. It goes to the owner, not into a test fix.

## Rhythm with the owner

- One decision at a time, each with a concrete example table.
- State spend in tokens before each dispatch, and wait for the owner's go. If the owner tracks usage,
  ask for a reading at each step's stop point. A usage reading never goes into the repo: not into a
  branch, a commit, a review record or the tracker.
- Recommend the proper fix. Never offer a stopgap as an equal option.
- Say the result as a win: what now holds, measured, not what changed.

## Lessons

- The reviewer must **run** the risky case, not only read it. A reordered stage or a widened rule can
  pass every test and still move an output that only a run shows.
- The reviewer writes its record early and keeps within its turn budget. A reviewer that hits its cap
  keeps only what is already on disk.
- Dispatch the reviewer from this session. A reviewer started inside the engineer dies when the
  engineer hands back.
- If the Write tool is refused, write the file with a shell heredoc.
- Never declare an agent's work lost without checking its output and the ops ledger.
- A latent change that no real input reaches is still a change. Name it, run it on a constructed case,
  and pin it with a test.
- A meaning change found mid-step that is out of the step's scope gets its own tracker item. It is not
  fixed inside the step.

## Brief templates

Fill every field. A `{…}` field is a placeholder from the list above. A `[…]` field names its source:
`binding.<field>`, `register.<field>`, `tracker`, `git`, `preflight`, the architect's or the
engineer's report, or `PM` (your own estimate or choice, stated to the owner first). Leave every
`<…>` that sits inside a repo-held command for the agent. A filled brief has no `{…}` and no `[…]`
left.

Keep each brief short: the agent's own definition already holds the method. Briefs reach committed
review records, so a brief never carries a person's name, a usage reading or a working-style note.

### Architect brief

```text
Repo: the working directory's repository; every path below is relative to its root. Branch
[git: current branch], head [git: short head]. Read only.
Part: {part} (kind [register: parts.{part}.kind]).
Mode: {RESTRUCTURE | REDESIGN}. If your measurements show the other mode fits better, say so.
Why flagged: the health signal [binding.signal, resolved to its command], [register: computed.windowDays]
days to [register: computed.asOf] at [register: computed.head]: signal [register: parts.{part}.signal]
(threshold [register: computed.threshold]), [register: parts.{part}.fixCommits] fix commits,
[register: parts.{part}.inPassing] in passing, [register: parts.{part}.linesChanged] lines changed,
top ids [register: parts.{part}.topIds]. State: [register: parts.{part}.state]; earlier decision:
[register: parts.{part}.decision, or "none"]. Treat this as a claim to test.
Ids behind the signal: [register: ids.<each top id>.fixCommits and .topParts].
Measure with: [binding.measure.commands, each filled]. Layer rules: [binding.measure.layerRules].
Framing: a part's shape changes as the problem is uncovered; a restructure is growth, not failure.
Recommend the proper fix. Write the answer as problem → cause → options → one recommendation → one
question, with one concrete example row (a real input, the output today, the output after).
Options must include: restructure (in steps: pure move, phase split, meaning changes, vocabulary),
in REDESIGN mode a redesign of the owning step, a smaller part of it, and accept. For each: the
gate (byte-identical or predicted moves), hours,
tokens, what it leaves unsolved, and any meaning the owner must define first, with the moves it
would cause.
Budget: [PM: tokens].
```

### Engineer brief

Use the gate block for the step's kind.

```text
Repo: the working directory's repository; every path below is relative to its root.
Branch: [binding.branches.refactor, filled], opened by the PM from BASE [git: BASE]. Work on it. Do not push or open a pull request.
Decision: {id}, step {n} of [tracker: step count]: [tracker: the step's one line]. The owner's
words: "[register: parts.{part}.decision.reason]".
Kind: [tracker: pure move | phase split | meaning change | vocabulary].
Target: [tracker: what moves where / what becomes one table / which meaning changes].
Record folder: [binding.reviews + binding.reviewName, filled].
Gate (byte-identical): every gate in [binding.gates.byteIdentical, resolved: each gate's id,
command, pass and when].
  Move code verbatim. Stop on any output change. Never edit a test or an output to make a gate
  pass. Any "predicted", "intended" or "named" allowance in a gate's pass text does not apply:
  0 moves, 0 transitions, 0 flips.
Gate (predicted moves): every gate in [binding.gates.predictedMoves.gates, resolved].
  The owner's meaning: [tracker: the meaning as the owner defined it].
  Moves the plan names: [tracker: the step's expected moves].
  Write the prediction (shadow run with calls per site and the unreached sites; static scan of
  every stated value, data rows included) to the record folder as
  [binding.gates.predictedMoves.prediction]. Then STOP and report it. Switch no site until the PM
  says go. Afterwards read it back exactly; stop on any unpredicted move.
Both: run BASE against BASE first. Scratch dir: [PM: a folder under the system temp directory,
  outside the repo, named by the tracker id, never by the user's name].
  Runs that must not run in parallel: [binding.gates.oneAtATime, or "none named"].
Previous step's pre-mortem: [tracker: step {n}-1's pre-mortem, or "first step"] — each item needs a
test that fails on the mutation.
Leave alone: [binding.leaveAlone, or "none named"].
Tracker (only when the binding says owned is true): in your last commit, write step {n}'s entry in
the item {id} in [binding.tracker.file]: BASE, the record folder, result, commits, each gate's
result, found-not-fixed, the pre-mortem for the next step, and the done-mark. [Last step only:
also mark the whole item done.]
Commits: one job each; end each with this trailer: [PM: the session's own Co-Authored-By line].
Report: result line, what moved where with line counts, each gate's result, tests, commits,
found-not-fixed, pre-mortem for the next step. Andon: stop and report. Budget: [PM: tokens].
```

### Reviewer brief

```text
Repo: the working directory's repository; every path below is relative to its root.
Diff: [git: merge-base origin/<default> and the step's branch]..[git: the branch
head] on [git: the step's branch]. Do not edit code. Do not commit.
Decision: {id} step {n}: [tracker: the step's one line]. Engineer's report: [the engineer's report,
pasted, or tracker: step {n}'s entry].
Claim: ["nothing changed: 0 moves, 0 transitions, 0 flips" for byte-identical | "exactly the
predicted moves", with the prediction file's path], and the new checks catch what the old structure
let through.
Gate commands: [as given to the engineer, resolved from the binding].
Prose gates to run and record: [preflight: check 4 ids, read from the binding's gate list, or "none"].
Known suspects: [the engineer's report: its pre-mortem and its found-not-fixed list].
RUN the risky case on real inputs in a scratch dir (a constructed case is fine); say "read, not run"
where you could not run it.
Write contract.md first, then each pass file as you finish it, then findings.md, into
[binding.reviews + binding.reviewName, filled]. If Write is refused, use a shell heredoc.
Turn budget: [PM: turns] of your cap. Leave 15 turns to write findings.md.
```

## Guardrails

- **The owner decides.** The job never restructures, accepts, or changes a meaning without the
  owner's answer, and never runs a meaning change the approved plan does not name.
- **One step, one branch, one pull request.** A step starts only after the one before it is merged.
- **Behaviour is preserved unless the plan names the change.** Any output move not predicted stops
  the step.
- **The reviewer did not do the work.** The PM dispatches it; the engineer never does; the session
  that built the step never reviews it.
- **One-way flow.** The register, the approval record and the ops ledger live in the stream. Never
  write a Permanence path or name into the repo's files, branches, commits or review records.
- **Commit by path.** In `~/permanence`, add only the files this job changed, each by its path, with
  `git -C ~/permanence`. Never `git add -A`: other sessions may have writes in flight.
- **Plain report.** Counts, not adjectives. Say what holds, what is next, and why.

If `~/permanence` is missing or this workspace has no stream, say so plainly rather than inventing content.
