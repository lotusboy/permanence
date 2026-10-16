---
name: dev-team
description: How to run a piece of work as a team rather than alone — whether to do it yourself, hand it to one agent or to several, which model, and which checker to pass before a finding or a change ships. Use when starting a substantial piece of work (a refactor, an investigation, a build spanning several files), when about to report a finding or a number as fact, or when about to change something other code depends on. Also triggers on "use the dev team", "spin up agents for this", "who should do this", and on any request to fan work out across agents.
---

# Running work as a team

You are the one talking to the owner. You do not hand that over. Everything below is about **which
work leaves your hands**, **who takes it**, and **which checks it passes on the way out**.

The owner decides *what* is done. You decide *who does it*, and say so. A project's own rules
(branches, isolation, review gates) live in that project's instructions and win over anything here.
Permanence's team — its roles, its agents and the jobs that use them — is described in
`docs/PROJECT-TEAM.md`.

## The rule that matters most

**An agent is for a unit of work you could hand to a person. Not for a step.**

Measured in September 2026: two subagents each cost **206k and 269k tokens** for one task apiece,
against a weekly limit. A `grep` costs nothing. Delegating a step burns a task's budget on a step.

The reverse error is real too. The most valuable findings of that week — a circular check, a positional
reference scheme, a hidden field in a document — all came from **tight loops**: run a command, read the
output, adjust, in seconds. An agent round-trip breaks that loop and the finding never happens.

## Who does it: yourself, one agent, or several

- **Yourself.** A known file or fact, one small edit, one command, a question whose answer fits in a
  line, diagnosis that needs iteration, or a decision. Also anything small enough that delegating costs
  more than doing.
- **One agent.** A coherent task that reads several files or produces bulky output, where you need the
  conclusion and not the contents. A fresh agent reads what the task needs and nothing else, and your
  context grows only by its report. `Explore` exists for wide read-only searches.
- **Several agents.** Only when the parts are genuinely independent: no two agents edit the same file,
  and no agent needs another's output. Otherwise one agent, or a sequence.
- **Follow-ups go to the same agent** (`SendMessage`), which keeps its context. A new agent starts cold.

Two cases always justify an agent, and are the most neglected:

- **Fresh eyes on your own output.** You cannot check your own blind spot; an agent with no shared
  context can.
- **A second opinion that must be independent.** Judgement where agreement is the evidence — and then
  the readers must differ genuinely (see *Independence* below).

**The brief is the lever.** A thin brief gives a confident wrong answer. Every brief carries the goal and
what "done" means; what is already known; where to start; what must not change and how to check it;
what the agent must not do (commit, push, start further agents); and the shape of the report. The PM
role (`runtime/roles/pm.md` §2) adds what a brief for new or changed code carries.

**An agent's report is a claim, not a result.** Check it before it is reported or committed.

## The checks

Three checker agents ship with Permanence. Each is `sonnet`, each is called at a gate and watches
nothing, and each answers one mechanical question about an artefact. **Run the check before the thing
it guards leaves your hands** — before a commit, a reply to the owner, a backlog entry, or anything a
customer or another team will see.

| checker | run it before | the one question |
|---|---|---|
| `absence-check` | reporting that something is not there | was the search shown capable of finding it? |
| `count-check` | a number goes in a reply, a commit message, a ticket or a client document | was it counted a second, independent way? |
| `blast-radius` | changing a producer, a format, a key scheme, or anything other code or documents depend on | who consumes this, and does the change hold for them? |

Dispatch them by role (`subagent_type: "role:blast-radius"`, and so on), as the PM role describes:
`runtime/agent-roles.json` says which installed agent fills each role and how it must run.

Each checker was written from real failures, and each names them. Read the agent file before deciding a
check does not apply — the failure it catches is usually more specific than it sounds. **A check that
finds nothing is a good result**, and the common one. It is not evidence the check was unnecessary.

## Choosing a model

- **`sonnet`** — the default for a delegated task, and for mechanical work: searches, sizing, the three
  checkers. Applying a positive control, counting a second way and listing consumers do not need a
  bigger model.
- **`opus`** — design, debugging, an unfamiliar reader or input, work needing judgement across a large
  surface, or code whose correctness is hard to test.
- **`haiku`** — bulk mechanical reads where the answer is a list.
- **The most expensive model** — only when the owner explicitly asks.

**Effort cannot be set per agent**; the Agent tool takes `model` only. Do not promise it.

## Independence, when agreement is the evidence

If the point of running several agents is that they agree, they must be able to disagree.

Measured in September 2026: the same model, in the same mode, on the same document, run twice, returned
**24 of 28 identical verdicts** — 85%, with four borderline items flipping. And two readers from one
model family agreed on a conclusion that a different family overturned.

So: **two runs of one model are one reader.** Where independence is the point, reach for different model
families. Where the owner has another family available at no cost, use it; never spend the owner's usage
limit on a second reader of the same family for a judgement pass.

## Fanning out

For several independent units, start them **in one message** so they run at the same time. Say in one
line what you have delegated and why, so the owner can interject.

**Never poll a running agent.** Reading its output file writes the whole transcript into your context.
The completion notification arrives on its own.

For deterministic multi-stage orchestration — phases, a pipeline, a controller that manages its own
agents — the `Workflow` tool exists, and it needs the owner's explicit opt-in every time. Do not reach
for it because a task merely looks parallel.

**When a chain of agents starts to strain** — a third agent on one item, a fix round that produces a new
finding of the same kind, an estimate overrunning twice — stop and use the `step-back` skill before
dispatching anything more.

## Before spending

The spend rule is the PM role's (`runtime/roles/pm.md` §2): **one agent** for a bounded task — say so and
go, unless the owner has asked to approve every one; **more than one agent, or any fan-out** — name the
agents, the rough cost and the alternative, and wait for a yes. **A yes to the work is not a yes to the
fan-out.** Never retry a failed fan-out automatically. The owner's usage limit is usually the binding
constraint, not money.

## Writing a new agent

Four properties make the shipped checkers work. Copy them.

1. **One question, mechanically answerable.** Not "review this".
2. **No shared context.** It reads artefacts and never asks how the work is going — that returns the
   author's own account of itself, which is the thing already known not to work.
3. **The cheapest model that can answer it.**
4. **An explicit refusal to broaden.** State that it must not comment on the work, the author or the
   session, and that finding nothing is a good outcome.

**Then check the frontmatter parses before you ship it.** A `description` containing a colon and a space
reads as a nested mapping, and the file silently fails to load — which happened to all three checkers in
September 2026, written in one sitting from the same broken template. Either quote the description or
use a `>-` block, and prove it:

```
python3 -c "import re,yaml,pathlib; yaml.safe_load(re.match(r'^---.n(.*?).n---',
  pathlib.Path('<file>').read_text(), re.S).group(1)); print('parses')"
```

Ground it in failures that actually happened, quoted. An agent built from imagined failure modes catches
imagined failures.
