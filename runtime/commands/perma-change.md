---
description: "Make the current repo's tool do something new, or fix a defect, from one work order — preflight, the work order as the decision, then one engineer step behind the binding's predicted-moves gates, a reviewer the PM dispatches, a fix round and one pull request. The engineer writes every expected output move before its first edit; any move not predicted stops the job. Every repo fact comes from the repo's binding and the work order. Usage: /perma-change <work-order id> [--dry-run [--from <file>]], where the id is the tracker item that holds the work order. Trigger phrases: \"make the change in <id>\", \"run work order <id>\", the owner approving a work order."
harness: claude-code, antigravity
---

# Permanence — Change

The `change` job for *this* repo, on one work order. You are the PM. Agents do the building and the
reviewing. The owner takes every decision.

A change makes the tool do something new, or fixes a defect. Its behaviour changes on purpose. So its
gate is **predicted moves**: the engineer writes every expected output move before its first edit,
and any move it did not predict stops the job. A restructure that changes no output is not a change;
it is `/perma-refactor`.

**The work order is the decision.** It lives in the repo's tracker item. Someone wrote it before this
job starts: the owner, or a repo procedure that found the tool must change. Its eight fields are
below. This job never invents a field. If a field is missing, stop and name it.

**Facts come from the binding and the work order.** Every repo path, command, gate, branch form,
tracker, record folder and owner rule comes from the repo's binding, `<stream>/repo/binding.json`,
from the repo files its pointers name, or from the tracker item. Never use a path, command, gate or
figure from anywhere else. A copied fact would bind every repo to the one it came from. If a step
needs a fact that none of these gives, stop and name the missing field.

**No dispatch without the owner's go on the spend.** Before each agent dispatch, state the estimated
tokens and wait for the owner's go.

## The work order

Eight fields, each written in the tracker item as its name followed by a colon (`need:` and so on).

| Field | Holds | Used in |
|---|---|---|
| `id` | the tracker id; it must equal this job's argument | everything |
| `need` | one sentence: what the tool must do that it does not do now | the engineer brief, the pull request |
| `evidence` | where the failure shows: document, page, table, run, output, count | the engineer brief; the reviewer re-runs it |
| `layer` | the owning layer the requester's root-cause check found | the engineer brief: the fix goes there |
| `gates` | gate ids from the repo's gate list that prove the change; never a copied command | the engineer and reviewer briefs, resolved through the binding |
| `expected` | the moves the requester expects; the prediction must cover each one | the prediction check (step 6) |
| `mustNotMove` | outputs that must stay byte-identical | the prediction check, the gates |
| `decided` | who decided the tool must change, as a role, and the date | the engineer brief, the pull request |

Beside the eight fields, the item carries a **`branch:` line**: the branch the change is made on.
Whoever writes the work order may write it; a repo procedure that writes a work order during its own
work names its own working branch there. If the item has no `branch:` line, the job writes one when
it opens its own branch (step 5). The job works only on the branch that line names. It never opens a
second branch for the same item, and it never copies a work order from one branch to another.

The job writes back to the same item, on that branch: `BASE`, the record folder, the prediction file,
the owner's go on the prediction, each gate's result, the commits and the pull request. The item is
the job's re-entry state. The stream holds only a pointer to it, in `WIP.md`.

## Words used below

- **`{root}`**: the repo root, `git rev-parse --show-toplevel`. Stay in it. Run every Permanence git
  command as `git -C ~/permanence …`; never `cd` away from the repo.
- **The binding**: `~/permanence/<stream>/repo/binding.json`. `<stream>` comes from
  `~/permanence/runtime/resolve-stream.sh {root}`.
- **The default branch**: run `git fetch` first. Then `git rev-parse --abbrev-ref origin/HEAD` gives
  `origin/<default>`. Every "merged" and every "on the default branch" below means on
  `origin/<default>`, never a local branch. If `origin/HEAD` is not set, ask the owner which branch
  pull requests go into.
- **The tracker item**: the lines in `<binding.tracker.file>` that carry `{id}`, where `{id}` matches
  `binding.tracker.id`. An item may span a register row and a section under its own heading; read
  every place that carries `{id}` and a field label. Until its branch merges, the item may exist
  only on that branch. To find it on any ref: `git for-each-ref --format='%(refname)' refs/heads
  refs/remotes`, then `git grep -n -E '<{id} as a whole word>' <ref> -- <binding.tracker.file>` per
  ref.
- **The job's branch**: the branch the item's `branch:` line names.
- **One step.** A change is one work step on one branch, so `{n}` is `1`. Work that needs more than
  one step is more than one work order.
- **`BASE`**: the commit the change starts from. On a branch the job opens, it is the head of
  `origin/<default>` when the branch is opened. On a branch the job did not open, it is that
  branch's head when step 5 runs. Record it in the item; never recompute it.
- **A pointer** (`file#key` or `file#key.id`): open `file` in the repo root. `file#key` means the
  whole list under the top-level `key`. `file#key.id` means the one item under `key` whose `id` is
  `id`. Each gate item gives its `id`, `command`, `pass` and, if present, `when` and `per`. A gate
  whose `command` is prose, not a command, is a **prose gate**; preflight lists them (check 4).
- **The job's gate list**: `binding.gates.predictedMoves.gates`, resolved. Every gate in it passes,
  each under its own `when`. The work order's `gates` names the ones that prove the need; each must
  be in this list.
- **Placeholders.** `{root}`; `{id}`; `{n}` (`1`); `{date}` (fixed once, when step 5 runs,
  as `YYYY-MM-DD`; never refilled on a later day); `{name}` (a short name the PM chooses when it
  opens the branch). Leave every `<…>` in a repo-held command for the agent that runs it; the
  reviewer checks it was filled.
- **The record folder**: `<binding.reviews>` + `<binding.reviewName>`, filled with the fixed
  `{date}`. Defaults when the binding omits them: `reviews` is `axis/runs/`; `reviewName` is
  `{date}-{id}-step{n}-review`. The folder sits directly under `reviews`: the role hook sends a
  reviewer back once if no new file appears in a folder there. To find an existing folder, match
  `reviewName` with `*` for `{date}`.
- **The prediction file**: `binding.gates.predictedMoves.prediction`, inside the record folder.
- **Commit trailer.** Every commit this job makes or asks for ends with the session's own
  `Co-Authored-By` line, taken from its attribution instructions. Never hardcode a model.

## Dry run

`/perma-change <id> --dry-run` runs steps 1 to 4 as reads only, then fills the
[engineer brief](#engineer-brief) and the [reviewer brief](#reviewer-brief) as far as they can be
filled before any work exists. It writes the briefs into a scratch folder outside the repo and shows
them. It opens no branch, commits nothing, writes nothing to the repo or the stream, records no ops
event and dispatches nothing. It reports what step 3 finds and carries on to step 4 whatever that
is, so a finished work order can be dry-run. A field that only exists after the engineer runs (its report, the
diff) is left as `[after the engineer]`. Every other `{…}` and `[…]` must be filled; any left is a
defect of the work order or the binding, and the dry run names it.

`--from <file>` reads the work order from that file instead of the tracker item, for a past change
written up as a work order after the fact. It is allowed only with `--dry-run`.

## The steps

Each step says who does it. "PM" is this session.

### 1. Preflight (PM)

From the repo root, run:

```
python3 ~/permanence/runtime/team-preflight.py change <id> --repo "$(git rev-parse --show-toplevel)"
```

- It exits non-zero: show its output and stop. Change nothing. A missing binding means the team does
  not apply to this repo. Say that plainly. Never guess a repo's commands.
- It exits 0: carry on. A `note` line is not a failure. Keep two kinds of note:
  - the prose gates (`check 4`), by id;
  - the role lines (`check 5`): which agent fills `change:engineer` and `change:reviewer`. "The
    session does it" means you do that role's work yourself, behind the same gates, and say so in
    the report. The reviewer role never falls to the session.

Then, when the binding has a `tracker`, check the argument: `<id>` must match `binding.tracker.id`.
If it does not, stop and show the form. When the binding has no `tracker`, skip this check.

### 2. Ownership (PM)

Read `binding.owned`.

- **`true`**: carry on.
- **`false`**: stop after this step. Say this to the owner:
  - preflight check 6 has confirmed an unconsumed approval in `<stream>/repo/approvals.json` whose
    scope is exactly `{"workOrder": "<id>"}`. Without one, preflight failed: offer to draft a
    proposal for `binding.approver`, as `/perma-health` step 6 does, naming the approver by role,
    never by a person's name;
  - the blocker is design question Q8: where a job in another party's repo keeps its work order and
    step state is not yet decided. This job reads and writes the work order in the repo's tracker,
    and in another party's repo it may write only a pull request. So it runs no further than this
    step until Q8 is decided and the binding says where the work order lives;
  - when it does run, the approval covers this work order only, the only output is a pull request,
    and the repo's tracker, hooks and other branches are never written. The ops ledger refuses this
    repo; do not work around it.

### 3. Re-entry (PM)

Find where this work order stands before doing anything else. Run `git fetch` first.

1. **Find the item.** Read it on `origin/<default>`. If it is not there, find it on any ref (see
   "The tracker item"). If no ref holds it, stop: there is no work order to run.
2. **Find the job's branch.** Read the item's `branch:` line. If there is none, look for a branch
   matching `binding.branches.change`, ignoring case (fill `{id}`, use `*` for `{name}`, and run
   `git branch -a -i --list '<pattern>' '*/<pattern>'`; the second pattern finds the remote).
3. **Done**: the item on `origin/<default>` carries the done-mark, or the job's branch is merged into
   `origin/<default>`. The done-mark covers a squash merge, which leaves the branch unmerged. Say it
   is done, with its pull request, and stop.
4. **In flight**: not done, and the job's branch exists. Work on that branch, at the first output
   missing, in this order. Never open another branch; never start the job again.
   1. No `BASE` and record folder in the item on the branch → step 5, on that branch.
   2. No prediction file in the record folder (the folder named in the item on the branch; else
      match the folder with `*` for the date) → step 6.1.
   3. A prediction file, and no owner's go on it in the item on the branch → step 6.2.
   4. The owner's go, and no engineer's result entry in the item on the branch → step 6.3.
   5. No `findings.md` in the record folder → step 7. A folder without `findings.md` is a review that
      did not finish.
   6. Findings with no `disposition.md` beside them → step 8.
   7. No pull request that carries the branch → step 9.
   8. A pull request open, not merged → wait for the merge. Say so and stop.
5. **Fulfilled outside the job**: the item's branch has no `BASE` or record-folder line, but the item
   already holds a prediction, or the branch holds commits that name this id. The session that wrote
   the work order did the work itself. This is in flight, not "not started". Never dispatch the
   engineer. Say what was found, and go to step 7 (review) on that branch, with `BASE` set to the
   branch's merge base with `origin/<default>`.
6. **Not started**: no job's branch yet, or a `branch:` line whose branch has no job lines, no
   prediction in the item and no commits that name this id. Go to step 4.

### 4. The work order (PM → owner)

1. **Read it.** Read the item where step 3 found it: on `origin/<default>`, or on the ref that holds
   it. With `--from`, read the file.
2. **Check it.** Each check that fails stops the job and names the field:
   - all eight fields are present and not empty;
   - `id` equals the argument;
   - every id in `gates` is a gate in the job's gate list;
   - `expected` lists at least one move, or says `none` with a reason;
   - `mustNotMove` names outputs, or says `none` with a reason;
   - `decided` names who decided, as a role, and a date;
   - when the part being changed has an architecture decision on record (a restructure or redesign
     decision in the health register, or an architect's report the work order or binding names), the
     work order names the design step or stage the change belongs to. A change that fits no stage, or
     does a stage's job in a different place, stops here and goes to the architect before the owner.
     This applies to fix rounds that add a new mechanism, too.

   Never fill `expected`, `mustNotMove` or `decided` yourself. They belong to whoever wrote the work
   order. Offer to write the missing field with them.
3. **Put it to the owner** as one message, in this order: the `need`; the `evidence`; the `layer`;
   the gates that prove it and the rest of the job's list; the `expected` moves and the `mustNotMove`
   outputs; the branch the job will work on (the `branch:` line, or the one it will open); the size in hours and tokens; one question: go or not. A
   work order from a repo procedure was already decided there; the go here is the go on the spend
   and the branch.
4. **Record the pointer.** On the owner's go, add one pointer line to the stream's `WIP.md`: the id
   and "re-entry: the tracker item". Commit `WIP.md` by its path, with `git -C ~/permanence`.
   A dry run stops here and fills the briefs.

### 5. The branch (PM)

Owned repos only. Run `git fetch`. Fix `{date}`.

- **The item has a `branch:` line**: check that branch out and work on it. Do not open a branch.
  `BASE` is its head now.
- **It has none**: choose `{name}`. `BASE` is the head of `origin/<default>`. Open the branch from
  `BASE`: `binding.branches.change`, filled. The item must be on `origin/<default>` for this; if it
  exists only on another branch without a `branch:` line, stop and ask the owner which branch the
  change belongs on. Never copy the work order.

Then commit the job lines into the item on the branch: the `branch:` line (when the job opened the
branch), `BASE` and the record folder. Commit by path, with the trailer. Fill the
[engineer brief](#engineer-brief) from the work order and the binding. Go to step 6.

### 6. Engineer (PM, then `role:change:engineer`)

1. **Dispatch.** Check that no `{…}` and no `[…]` field is left in the brief. State the token
   estimate and wait for the owner's go. Dispatch it with `subagent_type: "role:change:engineer"`,
   on the branch. The engineer writes the prediction file before its first edit, then stops and
   reports.
2. **The prediction check (PM → owner).** Compare the prediction with the work order:
   - every move in `expected` appears in the prediction;
   - every move in the prediction appears in `expected`;
   - no output in `mustNotMove` is predicted to move.

   Bring the prediction to the owner as one decision, before any site is switched, with each failed
   check named. A predicted move that `expected` does not name is a new decision, never a detail. On
   the owner's go, commit one line into the item on the branch: the prediction file and "approved by
   the owner, {date}". Then tell the engineer to continue (SendMessage).
3. **Continue.** If the engineer is no longer running, dispatch a fresh `role:change:engineer` with
   the same brief, the approved prediction and "switch now".
4. **An andon** from the engineer — an unpredicted move, a gate that cannot pass, a `mustNotMove`
   output that moved, a need the evidence does not show — goes to the owner as one decision. The job
   waits.
5. The engineer cannot start agents. Never ask it to start the reviewer.
6. Record each run (owned repos only), with `{id}` as the task:
   `~/permanence/runtime/ops-event.sh agent-run - "engineer: <id>" <model> - - <tokens> <seconds> <outcome>`.

### 7. Review (PM, then `role:change:reviewer`)

Dispatch the reviewer from this session as soon as the engineer reports. A reviewer started inside
another agent dies when that agent hands back. Fill the [reviewer brief](#reviewer-brief). State the
token estimate and wait for the owner's go. Dispatch it with
`subagent_type: "role:change:reviewer"`. Record the run (owned repos only).

Before you treat any agent's work as lost, check its record folder for `findings.md`, its branch and
the ops ledger. An empty folder alone is not proof.

### 8. Fix round (PM, then an engineer)

Send the findings to the same engineer with SendMessage, if it is still running. Otherwise dispatch a
fresh `role:change:engineer` with the findings, the branch and the brief.

- Fix every ANDON, P0 and P1 finding before the pull request.
- Fix real P2 and P3 findings too. Skip only the cosmetic.
- A fix that moves an output the approved prediction did not name is a new prediction, and goes to
  the owner first (step 6.2).
- The engineer re-runs every command gate after the fixes.
- Each prose gate in the job's gate list is re-run on the fix commits by a reviewer: SendMessage to
  the same reviewer if it is still running, otherwise a fresh `role:change:reviewer` given only the
  fix diff. Its result goes into the record folder.
- The engineer updates its result entry in the item with the fix commits and the re-run gate
  results.
- Write `disposition.md` in the record folder: each finding, what was done, and the commit.
- The PM commits the record folder — the reviewer's files and `disposition.md` — on the branch, by
  path, with the trailer. The reviewer writes them; it never commits.

### 9. Gates and pull request (PM)

1. Every gate in the job's list has passed after the last commit. Each gate's own `when` applies.
   Each prose gate has a recorded result. Every moved output is one the approved prediction named.
   Every `mustNotMove` output is byte-identical. The engineer's result entry in the item gives each
   gate's result and the commits.
2. **A branch the job opened**: push it and open a pull request into `origin/<default>`, with the
   repo host's own tool. Its text opens with the `need` and `decided`, then the measured moves
   against the prediction. Then commit the pull request's link into the item, by path, with the
   trailer, and push the branch again. If no tool is available, give the owner the branch name and
   the pull request text.
3. **A branch the job did not open** (the `branch:` line named it): open no pull request. The
   branch's own pull request carries the change. Tell the owner the change is done on that branch,
   with its commits and gate results.
4. The owner merges. In another party's repo, that party merges, and may ask for changes first.
5. Tell the owner the result as a win: what the tool now does, measured.

### 10. Close (PM)

After the pull request that carries the job's branch **has merged**:

- **Another party's repo**: write the merged pull request's link into the approval's `consumed`
  field in `approvals.json`, and commit that one file by its path. A consumed approval never starts
  a job again.
- **The owner's repo**: the engineer's result entry marks the item done. Check that it is there on
  `origin/<default>`.
- Replace the stream's `WIP.md` pointer line with one line: the id, done. Commit `WIP.md`, and the
  ops ledger when it changed, each by its path, with `git -C ~/permanence`.

## The predicted-moves gate

Before any change, run BASE against BASE and prove it identical. A gate that differs from itself is
not a gate.

1. Write the prediction before the first edit, using both methods:
   - a **shadow run**: the old rule and the new rule side by side over the repo's real inputs, the old
     result returned, every disagreement recorded, the calls per site counted, and every site no
     input reaches listed;
   - a **static scan** of every stated value in the latest outputs and their data files, rows
     included, for the cases no input reaches.
2. Each predicted move names the output, the case, the value before and the value after. Each
   `mustNotMove` output is listed as unchanged.
3. The prediction goes to the owner before any site is switched (step 6.2).
4. Then measure into `moves.measured.json` (the binding's measurement, flat key → value), with
   `moves.baseline.json` measured on BASE, and run `~/permanence/runtime/predict-gate.sh check
   --prediction <record>/moves.prediction.json --measured <record>/moves.measured.json`. A non-zero
   exit is an andon. The pass is the gate's exit 0, not the engineer's reading. The prediction file
   `moves.prediction.json` (format: Permanence README, "Predicted-moves gate") sits next to the prose;
   each `expected` and `mustNotMove` entry of the work order appears in it by key.
5. An unpredicted move stops the job. It goes to the owner, not into a test fix. Never edit a test or
   an output to make a gate pass.

Where a gate's `pass` text allows a "predicted", "intended" or "named" move, it means a move in the
approved prediction file, and nothing else.

## Rhythm with the owner

- One decision at a time, each with a concrete example: one real input, the output today, the output
  after.
- State spend in tokens before each dispatch, and wait for the owner's go. If the owner tracks usage,
  ask for a reading at each stop point. A usage reading never goes into the repo: not into a branch,
  a commit, a review record or the tracker.
- Recommend the proper fix. Never offer a stopgap as an equal option.
- Say the result as a win: what now holds, measured, not what changed.

## Lessons

- The reviewer must **run** the risky case, not only read it. A widened rule can pass every test and
  still move an output that only a run shows.
- The reviewer re-runs the work order's `evidence` on the new code. A change that passes its gates
  and leaves the evidence unchanged has not met the need.
- The reviewer writes its record early and keeps within its turn budget. A reviewer that hits its cap
  keeps only what is already on disk.
- Dispatch the reviewer from this session. A reviewer started inside the engineer dies when the
  engineer hands back.
- If the Write tool is refused, write the file with a shell heredoc.
- Never declare an agent's work lost without checking its output and the ops ledger.
- A latent change that no real input reaches is still a change. Name it, run it on a constructed case,
  and pin it with a test.
- A defect found mid-job that the work order does not name gets its own tracker item. It is not fixed
  inside this job.

## Brief templates

Fill every field. A `{…}` field is a placeholder from the list above. A `[…]` field names its source:
`work order: <field>`, `binding.<field>`, `tracker`, `git`, `preflight`, the engineer's report, or
`PM` (your own estimate or choice, stated to the owner first). Leave every `<…>` that sits inside a
repo-held command for the agent. A filled brief has no `{…}` and no `[…]` left.

Keep each brief short: the agent's own definition already holds the method. Briefs reach committed
review records, so a brief never carries a person's name, a usage reading or a working-style note.

### Engineer brief

```text
Repo: the working directory's repository; every path below is relative to its root.
Branch: [tracker: the item's branch: line] from BASE [tracker: BASE]. Work on it. Do not push or
open a pull request.
Work order {id}: [work order: need]
Decided: [work order: decided].
Evidence: [work order: evidence]. Reproduce it on BASE first.
Owning layer: [work order: layer]. Fix it there; a fix in another layer is an andon.
Least change that is still complete: in that layer, stop at the first of these that fully meets the
  need — the need is already met (build nothing, report it); code this repo already has there; the
  standard library or the platform; a dependency already installed; one plain line; otherwise the
  least code that works. Never leave out a check at a trust boundary, error handling that keeps data
  from being lost, anything security depends on, or anything the work order asks for. Finish what
  the change reaches: callers, tests, fixtures.
A shortcut taken on purpose (right for today's inputs, with a known limit) gets a comment at its
  line: shortcut: <the limit>, <when to upgrade>. Never without the upgrade condition.
Expected moves: [work order: expected].
Must not move: [work order: mustNotMove].
Record folder: [binding.reviews + binding.reviewName, filled].
Gate (predicted moves): every gate in [binding.gates.predictedMoves.gates, resolved: each gate's id,
command, pass and when]. The gates that prove the need: [work order: gates].
  Before your first edit, write the prediction (shadow run with calls per site and the unreached
  sites; static scan of every stated value, data rows included) to the record folder as
  [the file name in binding.gates.predictedMoves.prediction]: every expected move with its case and its value before
  and after, and every must-not-move output as unchanged. Then STOP and report it. Switch no site
  until the PM says go. Afterwards read it back exactly; stop on any unpredicted move. Never edit a
  test or an output to make a gate pass.
Run BASE against BASE first. Scratch dir: [PM: a folder under the system temp directory, outside
the repo, named by the work order id, never by the user's name].
  Runs that must not run in parallel: [binding.gates.oneAtATime, or "none named"].
Leave alone: [binding.leaveAlone, or "none named"].
Tracker (only when the binding says owned is true): in your last commit, write your result entry in
the item {id} in [binding.tracker.file]: the record folder, the prediction file, each gate's result,
the moves measured against the prediction, the commits, found-not-fixed, and the done-mark.
Commits: one job each; end each with this trailer: [PM: the session's own Co-Authored-By line].
Report: result line, what moved against the prediction, each gate's result, tests, commits,
found-not-fixed. Andon: stop and report. Budget: [PM: tokens].
```

### Reviewer brief

```text
Repo: the working directory's repository; every path below is relative to its root.
Diff: [tracker: BASE]..[git: the branch head] on [tracker: the item's branch: line]. Do not edit
code. Do not commit.
Work order {id}: [work order: need]. Evidence: [work order: evidence]. Owning layer: [work order:
layer]. Expected moves: [work order: expected]. Must not move: [work order: mustNotMove].
Engineer's report: [the engineer's report, pasted, or tracker: the engineer's result entry].
Claim: exactly the moves in the approved prediction, [binding.reviews + binding.reviewName, filled,
+ binding.gates.predictedMoves.prediction]; every
must-not-move output byte-identical; the evidence no longer shows the failure.
Gate commands: [as given to the engineer, resolved from the binding].
Prose gates to run and record: [preflight: check 4 ids, read from the binding's gate list, or "none"].
Known suspects: [the engineer's report: its found-not-fixed list].
RUN the risky case and the work order's evidence on real inputs in a scratch dir (a constructed case
is fine); say "read, not run" where you could not run it.
Write contract.md first, then each pass file as you finish it, then findings.md, into
[binding.reviews + binding.reviewName, filled]. If Write is refused, use a shell heredoc.
Turn budget: [PM: turns] of your cap. Leave 15 turns to write findings.md.
```

## Guardrails

- **The owner decides.** The job never starts without the owner's go on the work order, never
  switches a site before the owner's go on the prediction, and never runs a move the work order and
  the approved prediction do not name.
- **One work order, one branch.** The branch is the item's `branch:` line; the job never opens a
  second one and never copies a work order between branches.
- **Behaviour changes only as predicted.** Any output move not predicted stops the job.
- **The reviewer did not do the work.** The PM dispatches it; the engineer never does; the session
  that built the change never reviews it.
- **One-way flow.** The approval record, the pointer and the ops ledger live in the stream. Never
  write a Permanence path or name into the repo's files, branches, commits or review records.
- **Commit by path.** In `~/permanence`, add only the files this job changed, each by its path, with
  `git -C ~/permanence`. Never `git add -A`: other sessions may have writes in flight.
- **Plain report.** Counts, not adjectives. Say what holds, what is next, and why.

If `~/permanence` is missing or this workspace has no stream, say so plainly rather than inventing content.
