# The project team (experimental)

> **Status: experimental, added in v1.6.0.** Built and used on one repository so far. The file
> shapes below may change in a later release; a change that affects an existing file will carry a
> **Migration notes** section in `CHANGELOG.md`.
>
> **Claude Code only.** The team uses subagents and three Claude Code hooks. The Antigravity, Devin
> and Cursor bindings get neither the agents nor the role enforcement. Everything else in Permanence
> works on those tools as before.
>
> **Opt-in by file.** A repository takes part only when its stream holds a `binding.json`. With no
> binding, the team commands stop and say so, and nothing else in Permanence changes.

## What it is

The PM role (`runtime/roles/pm.md`) holds the thread for one owner. The project team is what the PM
hands work to: named roles, filled by agents, running two jobs behind gates, plus a health watch
that says where to look.

| Command | What it does |
|---|---|
| `/perma-health` | Rewrites the repo's health register and lists the parts that are ready for a refactor. It never starts work. |
| `/perma-refactor <part>` | Restructures one part. Every step must leave outputs byte-identical, except a meaning change the owner named in advance. |
| `/perma-change <work-order id>` | Makes the tool do something new, or fixes a defect. The engineer writes every expected output move before its first edit; any move not predicted stops the job. |

Each command runs a preflight first and stops before any work if the binding is wrong.

## The rule that shapes everything

**No project may require Permanence.** A repository never names Permanence, its commands or its
agents (SPEC §2 invariant 1). So everything the team needs to know about a repo lives in the owner's
stream for that repo, under `<stream>/repo/`, and the team finds it by resolving the working
directory through `_meta/REGISTRY.md`.

| File in `<stream>/repo/` | Holds | Written by |
|---|---|---|
| `binding.json` | the repo's facts for the team | the owner, with the PM |
| the register (the binding names its path) | each part's health signal, state and decision | the signal command; decisions by the owner |
| `ops/events.jsonl`, `ops/OPERATIONS.md` | the ops ledger and its rules | `runtime/ops-event.sh` only |
| `approvals.json` | approvals for work in a repo another party owns | the owner, with the PM |
| `programme/` | a programme group's report, when it is the owner's own working file (SPEC §2 invariant 8) | the group's task doc |

## Roles

A role names a job. An agent fills a role. A job dispatches `role:<job>:<role>`, for example
`role:refactor:engineer`.

| Role | Does | Shipped agent |
|---|---|---|
| `architect` | lays out a restructure-or-accept decision for one part | `architect` |
| `engineer` | makes the change behind its job's gate | `refactor-engineer` |
| `reviewer` | reviews the diff and runs the risky case | `refactor-reviewer` |
| `absence-check`, `count-check`, `blast-radius` | check a claim of absence, a count, the reach of a change | the agent of the same name |
| `design-author`, `design-reviewer` | write and review a design | the agent of the same name |
| `code-review` | single-pass code review | none shipped; falls back to the built-in `general-purpose` agent |

Resolution checks these levels in order. At each level the key `<job>:<role>` is tried before
`<role>`. A level that names only agents that are not installed is skipped, and the skip is logged.

1. The repo binding's `roles`.
2. `_personal/agent-roles.json` — the owner's own table. Put an employer's or a private plugin's
   agent here. `_personal/` is never part of the template, so an upgrade never overwrites it.
3. The shipped table, `runtime/agent-roles.json`.

A review role never falls to the session that did the work: with no match it goes to
`general-purpose`. `runtime/team_roles.py` is the one implementation of these rules;
`runtime/agent-roles.py` enforces them as hooks and logs every change to
`runtime/logs/agent-roles.log`. The hook fails open.

Outside a repository with a binding, the shipped table acts only on a `role:` dispatch. It does not
change a dispatch made by plain agent name, and it never sends an agent back for a run record. The
owner's own table in `_personal/` is the owner's explicit choice and applies everywhere.

The shipped agents have plain names (`architect`, `design-author`, …). If the owner already has
their own agent with one of those names, the install leaves theirs in place and says so; that role
is then filled by the owner's agent.

## The binding

`<stream>/repo/binding.json`. JSON, read with the standard library only. An `_about` key carries
comments. Paths are relative to the repo root, except `register`, which is relative to
`<stream>/repo/`.

Every gate and command is either a command, or a pointer to the repo file that holds it:
`file#key`, or `file#key.id` for the list item under `key` whose `id` is `id`. Prose is not allowed
in the binding, because preflight cannot check it.

| Field | Holds | Required |
|---|---|---|
| `owned` | `true` when the owner owns the repo | always |
| `approver` | who approves work when `owned` is false — a role, never a name | when `owned` is false |
| `register` | the register's path | always |
| `signal` | what rewrites the register: a command, a pointer, or rules for the shipped script (see "The signal") | always |
| `tracker` | `file`: where a job opens or reads its item; `id`: the id form, as a regular expression | when owned |
| `measure` | `commands`: what the architect runs; `layerRules`: where the layer rules are (optional) | `commands` when owned |
| `gates.byteIdentical` | the gate list for `refactor` | when owned |
| `gates.predictedMoves` | `gates`: the gate list for `change`; `prediction`: the prediction file's name | when owned |
| `gates.oneAtATime` | runs that must not run in parallel | no |
| `branches` | the branch form per job: `refactor`, `change` | when owned |
| `roles` | role → agent overrides for this repo | no |
| `reviews` | the folder of review records; default `axis/runs/` | no |
| `reviewName` | one step's record folder name; default `{date}-{id}-step{n}-review` | no |
| `leaveAlone` | files no step may edit | no |

Placeholders are `{…}` only, from this closed list: `{root}`, `{register}`, `{id}`, `{n}`, `{date}`,
`{part}`, `{name}`. Anything else fails preflight.

No field may hold a person's name or any private context: a field's text reaches agent briefs, and
briefs reach committed review records.

### An example

A small repo the owner owns, with tests as its gate and a markdown tracker:

```json
{
  "_about": "Repository facts for the project team. Lives in the owner's stream, never in the repository.",
  "owned": true,
  "register": "health.json",
  "signal": "python3 tools/health.py --register {register}",
  "tracker": {"file": "docs/TRACKER.md", "id": "^T[0-9]+$"},
  "measure": {
    "commands": ["git log --no-merges --numstat -- src/{part}"]
  },
  "gates": {
    "byteIdentical": "Makefile#check",
    "predictedMoves": {"gates": "Makefile#check", "prediction": "prediction.md"}
  },
  "branches": {"refactor": "refactor/{id}-step{n}-{name}", "change": "fix/{id}-{name}"}
}
```

## The signal

`/perma-health` and `/perma-refactor` need something that writes the register: each part's fix
pressure and state. `/perma-change` does not need the register to run. The binding's `signal` takes
one of three forms:

- **a command** the repo already has, such as `python3 tools/health.py --register {register}`;
- **a pointer** to the repo file that holds that command (`file#key.id`);
- **rules for the shipped script**, `runtime/health-signal.py` (added in v1.7.0). Use this when the
  repo has no signal command of its own, or belongs to another party so that none can be added.

The shipped script uses the Python standard library only. It reads the repository with read-only
git commands at one ref and writes one file, a JSON register in the stream.

```json
"register": "health.json",
"signal": {
  "script": "health-signal",
  "ref": "HEAD",
  "fix": "(?i)^fix\\b",
  "codeRoots": ["src/", "scripts/"],
  "part": "^src/([^/]+)/"
}
```

| Rule | Holds | Required |
|---|---|---|
| `script` | `health-signal` | yes |
| `ref` | the commit or ref that is measured. For a repo another party owns, name a remote ref such as `origin/main`, so no branch is ever switched | yes |
| `codeRoots` | the folders whose lines count as code. A fix's lines in tests, docs or data are left out, so they do not hide where the code was fixed | yes |
| `part` | one pattern; group 1 is the part id of a file | `part` or `parts` |
| `parts` | a list of `{"kind", "match", "id"}`; the first `match` that fits a file decides. `id` is optional and builds the part id from the groups, for example `"config/{1}"` | `part` or `parts` |
| `fix` | a commit whose subject matches is a fix. Default: starts with `fix` | no |
| `extensions` | only files ending in one of these belong to a part | no |
| `reviewFinding` | what marks a review finding worth counting. Default: `\bP1\b` | no |

The script measures three things per part:

1. **Fix pressure.** Each fix commit's changed code lines are shared out over the parts they fall
   in. A part's `signal` is the sum of its shares over the window. This is the only input that
   decides `state`.
2. **Size.** Files, lines and the longest file, at the ref. Reported only.
3. **Review findings.** In each review folder (the binding's `reviews`) whose name starts with a
   date inside the window, each paragraph that matches `reviewFinding` and names one of the part's
   files adds one. Reported only. It is a text match, so read it as a pointer to go and look.

A part at or over the threshold with no decision is `ready`. A person writes a part's `decision`
(`restructure`, `redesign` or `accept`); the script never overwrites it, and raises the part again
(`ready-again`) only when its signal reaches `signalAtDecision` times `regrowth`. The window,
threshold and regrowth live in the register's own `settings` block, which the script also never
overwrites. Defaults: 30 days, 8.0, 1.5.

Run it by hand to try rules before trusting them; `--no-write` prints the block and leaves the
register as it is:

```bash
python3 ~/permanence/runtime/health-signal.py --binding <stream>/repo/binding.json \
    --register health.json --repo <repo> --no-write
```

## Ownership

- **`owned: true`** — jobs run, the ops ledger records them, and `wire` (through
  `runtime/repo-hooks.sh`) writes a post-commit hook into the repo's local hooks folder, which git
  never commits. A hook without Permanence's marker is never overwritten.
- **`owned: false`** — the repo belongs to another party. The health watch drafts a proposal for
  the `approver`; it offers no job. A job runs only inside a recorded approval of that exact scope
  in `approvals.json`, and its only output is a pull request. The ops ledger refuses the repo.

`approvals.json` is a list. Each record has a `scope` — `{"part": "<part>"}` or
`{"workOrder": "<id>"}` — and a `consumed` field the job fills in. A consumed approval never starts
a job again.

## Preflight

`runtime/team-preflight.py <refactor <part> | change <id> | health | startup>`. It reads files and
runs read-only git commands; it writes nothing. One line per failure; exit 1 on any failure.

1. The binding exists.
2. It parses, has the fields its `owned` value requires, and uses only the closed placeholder list.
3. Every path field exists in the checkout.
4. Every pointer finds its key. A gate the repo wrote as prose is listed, not failed.
5. Every role the job dispatches resolves.
6. For a job when `owned` is false: an unconsumed approval of this exact scope exists.

`/perma-startup` runs `startup` mode (checks 1 to 4) when it knows the repo folder, and carries any
failure into its hand-back without stopping.

## The ledgers

All are append-only JSON lines in the stream. A wrong row is never edited; a correcting row follows
it. `runtime/README.md` and each tool's header comment are the full reference.

| Ledger | Written by | What it is for |
|---|---|---|
| `<stream>/repo/ops/events.jsonl` | `ops-event.sh` | how the work was run: agent runs, fan-outs, loops, gates refused, decisions asked. `ops-gap.sh` reports how many commits it has fallen behind. |
| `<stream>/decisions/ledger.jsonl` | `decision.sh` | every question put to the owner, the recommendation, the answer, and later the outcome. `DECISIONS.md` beside it is the generated view. Scores agreement per category. |
| `<stream>/spend/ledger.jsonl` | `spend.sh` | measured tokens per agent, grouped into waves with a ceiling. |
| `<stream>/ratifications/ledger.jsonl` | `ratify.sh` | which entries of a closed vocabulary two blind readers agreed are right. |

`predict-gate.sh` and `save-report.sh` keep no ledger: the first compares a written prediction with
measured outputs and refuses any move nobody predicted; the second saves an agent's report
byte-for-byte.

## The working board

`<stream>/WIP.md` is the PM's board, with four sections: **Now**, **Blocked**, **Parked**, **Done
today**. It is the one file that answers "what was I doing?". A stream gains one the first time it
needs one; when a role is set and the stream has none, session start says so, so the PM can offer
it once.

## Known limits in this release

- Only one repository has run the jobs. The binding's field list is complete for that repo and a
  hypothesis for any other.
- A job in a repo another party owns stops before it writes any plan or step state: where that
  state is kept is not yet decided.
- The binding has no default-branch field and no pull-request tool field. Jobs read the default
  branch from `origin/HEAD` and open a pull request with the repo host's own tool, or hand the owner
  the branch name and the pull request text.
- The decision ledger scores calibration only for asks recorded with `--confidence`.
- The shipped signal script reports file length but not the longest function, and it does not
  count layer-rule breaks: both need a per-language rule the binding does not have yet.
- The shipped signal script has been checked against one repository's own signal script, where it
  gave the same result for every part. Its part rules for other kinds of repository are untested.
- The shipped signal script reads and writes a JSON register. A register in another format has to
  be converted once, keeping `settings` and every `decision`.
