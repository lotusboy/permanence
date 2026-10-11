# Updating the programme folder

> **Scaffold.** Copy this into the programme folder (conventionally the target repo's
> `docs/programme/UPDATING.md`, or the owner's stream when the report is personal: SPEC §2 invariant 8), then fill in
> every `<PLACEHOLDER>`. Delete this blockquote and the `» localise` notes as you go.
>
> Two kinds of content live here, and the difference matters:
>
> - **FIXED — do not change.** The report shape, the RAG rules, and the integrity gates are identical in
>   every programme, so that one person can scan many programmes side by side and have each word mean the
>   same thing. Localising these quietly destroys that.
> - **» localise.** Roles, phase numbering, document names, domain specifics. Yours to set.
>
> **REPORT SPEC v1** — quote this version in the folder's `status.md` footer. If you ever revise the
> fixed parts, bump it, so a reader can tell which groups are on which spec.
>
> **Scope.** This mechanism is for one owner spanning several of their own repos (`members` are read via
> local `git log`, and the update lock is per-clone) — it does not coordinate genuinely separate people on
> separate machines. If that's what you need, this isn't yet the tool for it.

The procedure for refreshing this folder. Written to be followed by an assistant at the end of a work
session, from **any** of the participating repos.

## Who this is for, and what follows from it — FIXED

This folder is written **for a reader outside the project** — a programme manager, or a director who wants
plan and status without taking the project's time to extract it. The people who build the work do not read
it back.

That single fact sets the standard: **nobody who knows the ground truth checks this before a stakeholder
sees it.** So the report cannot rely on being corrected. Getting something wrong is worse than being a day
behind, because a wrong number reaches a decision before anyone notices.

Two rules follow, and they are not optional:

- **Every claim traces to a source** — a commit, a file, or a measured output. If it cannot be traced, cut
  it or mark it unverified.
- **Self-audit before committing** (step 7).

## Execution — model and effort

Accuracy matters more than speed. Run the update as a dedicated subagent with:

| Setting | Value |
|---|---|
| model | `<MODEL>` |
| effort | `high` |

» localise the values; keep the declaration. If the caller cannot honour them, run anyway and say so in
the summary — a report that names its own limits is still useful; a silent downgrade is not.

The reading is the bulk of the work, not the writing. High effort earns more here than a larger model does.

## Inputs the caller supplies — FIXED

This procedure looks up **no configuration of its own**. The caller passes in:

- **`role`** — which asset this session is working in. » localise the set: `<ROLE-A>`, `<ROLE-B>`, …
- **`members`** — the current roles and their local repo paths.

If the caller cannot supply these, stop and say so. Do not guess. *(This inputs contract is what keeps the
pointer one-way: nothing in this repo names or reads the caller's own configuration.)*

## The model — FIXED

**Any member may write updates for the whole group.** A run fills whatever gaps it can see and leaves the
rest. The next run, from any member, fills more. The folder converges to complete.

- Reads of other members' repos are **opportunistic, never required**. If a repo is missing or unreadable,
  record it as unreachable and carry on. Do not fail the run.
- **Unreachable and up-to-date must look different.** The model is only trustworthy if you can tell
  "nothing happened there" from "nobody has looked".

## What is derived, and what needs a human — FIXED

| File | How it updates |
|---|---|
| `status.md` | **Generated.** Overwrite every run. Never hand-edit. |
| `progress/<role>/<date>.md` | Generated per role per calendar date with activity. |
| `watermarks.json` | Generated. Records the last commit recorded per role. |
| `<PLAN-DOC>` | **Human-owned.** Only phase status words change, and rarely. Never renumber phases. |
| `<RATIFIED-DOC>` | **Human-ratified.** Propose candidates in the summary; never append them yourself. |

» localise the last two names (e.g. `build-plan.md`, `source-complexity.md`), and drop the second row if
the programme has no such document.

## Procedure

### 1. Take the lock — FIXED

Create `.updating.lock` in this folder, containing the role, an ISO timestamp, and the session id. Add it
to `.gitignore` — it is never committed.

If it already exists:

- **Younger than 30 minutes** — another session is mid-run. Stop, report that an update is underway,
  change nothing.
- **Older than 30 minutes** — the holder died. Break it, and say in the summary that you did. *(Without
  this staleness break, one dead session freezes the group's updates with no error anyone would see.)*

### 2. Read the watermarks — FIXED

`watermarks.json` maps each role to the last commit already recorded for it. That is the definition of
"already reported" — **not** the dates of files in `progress/`, which cannot tell a 3pm run from commits
that landed at 6pm.

### 3. Find the gaps — FIXED

For each member in `members`, if the repo is reachable:

```
git -C <path> log <watermark-sha>..HEAD --pretty="%h %ad %s" --date=short
```

No output means that role is up to date. Nothing to write for it.

Read the checked-out branch's history only — do **not** add `--all`. A watermark is a single commit sha and
step 5 advances it to the one `HEAD` you read, so it cannot bound a read across every ref: `--all` pulls in
other branches' copies of the same work and the same change gets reported twice. Work on an unmerged branch
is picked up when it merges, which is the converging model working as intended.

If the watermark sha is unknown to the repo (history rewritten, or a fresh clone), fall back to the last
recorded date and say in the summary that you did.

### 4. Write the entries — FIXED shape

For each role with new commits, group them by calendar date and write or refresh
`progress/<role>/<YYYY-MM-DD>.md`. Several days of commits produce several entries — that is how a missed
session catches up.

Each entry states **what the plan expected, what landed, and the numbers**. Plain language: these are read
by people who do not open the code. Refreshing today's existing entry is normal — rewrite it rather than
appending a second one.

» localise: if the folder has pre-existing entries in a different layout, name them here and say
"do not restructure", so a later run leaves them alone.

### 5. Advance the watermarks — FIXED

Set each written role's watermark to the `HEAD` you actually read. Leave unreachable roles untouched.

### 6. Regenerate `status.md` — FIXED

Overwrite it. For each **current** member (one whose `left` is empty) give, in this order:

| Field | Content |
|---|---|
| Asset | the role |
| RAG | per the rules below — with a reason on any amber or red |
| Phase | the phase reached, from `<PLAN-DOC>` |
| Last landed | what most recently completed |
| Next | what is being worked on now |
| Last reported | the date this asset last had activity recorded |
| Help needed | what it needs and from whom — or "nothing" |

Mark unreachable members as unreachable with their last recorded date. Members that have **left** are
excluded from `status.md`; their `progress/` entries stay exactly as they are. Footer: the REPORT SPEC
version and the date generated.

#### Setting RAG — FIXED, and identical in every programme

RAG is the field a programme manager scans across projects, so it has to mean the same thing everywhere.
Set it by these rules, not by impression:

| Status | When |
|---|---|
| **Red** | Blocked with no route forward. Or a committed date missed with no new date. Or something known to be wrong is in a stakeholder's hands. |
| **Amber** | A decision or input is needed from someone outside the project. Or a phase is at risk. Or an asset expected to be active has not reported in 10 working days. |
| **Green** | Proceeding. Nothing needed from anyone else. |

Two clarifications that stop RAG becoming noise:

- **Waiting by design is green.** An asset waiting on a planned dependency is proceeding as intended.
  Amber is for waiting that was *not* planned.
- **An asset cannot be green if it names anything under "help needed".** If it needs something, that is at
  least amber. This is the check that stops everything sitting on green until it suddenly turns red.

State the reason beside any amber or red. "Amber" with no reason is worse than no RAG at all.

### 7. Self-audit — FIXED

Before committing, re-read what you wrote and check each of these:

- Every number traces to a commit, a file, or a measured output. Numbers copied from a design doc may be
  stale — prefer the source they came from.
- No claim rests on inference presented as fact.
- Anything unverified says so.
- Every RAG value follows the rules above, and every amber or red carries a reason.
- Nothing describes work that is not in the git history you read.

Fix what fails. If something cannot be checked, say so in the file rather than dropping it silently.

### 8. Commit — FIXED

Commit on whichever branch is checked out here. Docs only. **Never push** — pushing is a separate,
deliberate act. Then delete the lock.

## Rules — FIXED

- **Read the private working notes for the *why*; let none of them reach these files.** Git says what
  changed; the working notes say what it was for, what was decided, and what was ruled out — read them,
  because a report without the why is just a changelog. But this folder is team-visible, so no private
  phrasing, path, reference, or read-on-a-person may appear in it. Write from the same events, in this
  folder's own register. The risk is highest during an end-of-day run, when those notes are freshest.
- **Gentle, accurate register.** Record behaviour and impact as fact; label a read of *why* as a
  provisional inference. No commentary on people beyond their work and conduct.
- **No hedging that hides a gap.** If something is not done, write "not done". If a number is unverified,
  say so.
- **Never rewrite history.** Correct a fact in an old entry if it is wrong. Do not re-narrate it.
