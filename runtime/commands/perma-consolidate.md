---
description: Read-only consolidation pass over Permanence — analyse every stream and write a report of proposed changes. Changes nothing on disk or in git; a separate interactive review (/perma-consolidate-review) applies what you accept.
---

# Permanence — Consolidation Pass (analysis → report)

The **slow retrospective maintenance path** for Permanence at `~/permanence`.
`perma-brief` is the read path; the live pairing edits are the fast write path.
This is the third leg: a periodic pass that spots stale state, unclosed
inferences, contradictions, and clutter — and writes them up as a report.

**This pass changes nothing.** It reads Permanence and writes a single report to
`~/permanence/.consolidation/` (untracked). No edits, no branch, no commits, no git
state. That makes it safe to run anytime — mid-edit, on a schedule, several times
a day. Exactly the Claude Dreams shape (Anup Pt 3 §4): read the input store,
emit a *separate* output the human reviews; the input store is untouched. Applying
the accepted items is a deliberate, interactive second step: `/perma-consolidate-review`.

This is a maintenance analysis, not a work session. Don't start new project work,
answer open questions, or introduce facts the LOGs don't already contain. You
surface what's there to reconcile; you don't invent.

## Preconditions

1. Confirm `~/permanence` exists and is a git repo with exactly `ls -d ~/permanence/.git`. If not, say so plainly and stop.
   (Use that command, not `git rev-parse` or `git status`: the unattended nightly run grants
   `ls` but not those, and a denied command there waits on a prompt nobody can answer.)
2. That's it — no clean-tree requirement, because this pass writes nothing into the
   repo. (If the working tree has uncommitted edits, just note that the analysis
   reflects current file contents, committed or not.)

## Phase 0 — Orient

1. **Timeline first**, exactly as `perma-brief` does: `git -C ~/permanence log --pretty=format:"%ad  %s" --date=short -30`. The canonical chronology — read it before the per-stream reads so supersessions and staleness land in context.
2. **Run id for the filename:** `RUN_ID=$(date +%Y-%m-%d-%H%M)`. The timestamp (not just the date) means several runs a day — or a scheduled nightly run plus a manual one — each get their own report without colliding.
3. **Discover the streams**, don't assume them: every `~/permanence/<...>/` directory containing a `PROJECT.md`, plus the root perma-meta (`~/permanence/LOG.md`). New streams appear automatically.

## Phase 1 — Analyse each stream

For each stream, read `PROJECT.md`, `STRATEGY.md`, `PEOPLE.md`, `QUESTIONS.md`, and
the **tail** of `LOG.md` (recent entries — don't re-read full history; git carries
it). Look for the six decay modes:

| # | Mode | What to look for |
|---|---|---|
| **1. PROJECT behind LOG** | A `PROJECT.md` whose current-state blocks lag what the LOG already records. The fix is to refresh the block **from existing LOG entries** and bump `Last updated`. |
| **2. Stale inferences** | Dated reads on people (in `PEOPLE.md` etc.) older than ~3 weeks that were never closed. The README's people-rule: revisit and mark confirmed / revised / wrong / prune. |
| **3. Superseded claims** | A `PROJECT`/`STRATEGY`/`PEOPLE` claim a later LOG entry contradicts (the cheese-recipe failure). Internal contradictions inside one file count too. |
| **4. QUESTIONS hygiene** | `[CLOSED]` markers older than ~3 weeks that should move to an `## Archive`/`Answered` section; near-duplicate open questions; closed answers worth folding up into PROJECT/STRATEGY; stale relative dates ("tomorrow"). |
| **5. Eviction / relocation** | the owner-wide content sitting in a customer stream; reference notes that belong elsewhere; archive candidates. |
| **6. Cross-stream entity drift** | The same person (e.g. Dan, or two "Nina"s) described inconsistently across streams. |

There is **no apply step here** and so no apply/propose split — everything is a
*proposal* the reviewer will decide. But classify each proposal by **risk**, because
the reviewer treats them differently:

- **Mechanical** — a safe, reversible edit that adds no new claim (refresh a block from a quoted LOG line; sweep a closed question; fix an unambiguous date). For these, the report must carry the **exact edit**: the file path, and the precise `old → new` text, so the reviewer can apply it verbatim and verify it still matches. Recommend these.
- **Judgement** — needs the owner's knowledge of what actually happened (inference verdicts, which contradicting claim wins, evictions, entity reconciliation). For these, quote the conflicting material and lay out the options; don't pre-decide.

## Phase 2 — Write the report

Write `~/permanence/.consolidation/REPORT-$RUN_ID.md` **and** print it to the chat. Give
every actionable item a **stable label** (`Mechanical 1`, `Verdict 3`,
`Supersession 2`, `Move 1`) — `/perma-consolidate-review` references these. Structure:

- **Mechanical edits (ready to apply, recommended)** — each with file path, the exact `old → new` text, and the **source LOG line(s) quoted** so the compaction is auditable. These are the easy yeses in review.
- **Needs a verdict** — the inference close-the-loop list (mode 2): each inference, its date, options confirm / revise / wrong / prune.
- **Proposed supersessions** — mode 3: claim vs contradicting LOG entry, both quoted, with the competing versions named.
- **Proposed moves** — modes 4-fold-up, 5, 6.
- **History flags** — if any *committed* content looks like a genuine people-rule breach, name it as a candidate for the README's history-rewrite policy. **Never rewrite history** — surface only; that's a separate, the owner-authorised action.

If a section is empty, omit it. If the whole pass found nothing, say so plainly.

## Phase 3 — Hand back

Tell the owner the report is ready (give the path + the counts) and that the next step
is **`/perma-consolidate-review`** — the interactive walkthrough that decides each
item, shows a final summary to catch mistakes + dependencies, and applies the
accepted ones on `main` via a single audit branch. Make clear **nothing has changed
yet** — Permanence is exactly as it was.

## Guardrails

- **Read-only.** This pass must not edit, stage, commit, branch, or checkout anything in `~/permanence`. Its only output is the report file under the gitignored `.consolidation/`.
- **Voice.** The report is a persisted file — write it in the gentle, accurate register per `~/.claude/CLAUDE.md`. Same meaning, safer key.
- **Writing about people.** Mode-2 analysis is the people-rule maintenance surface. Apply the fact/inference split and behaviour-not-identity to anything you write about a person; propose verdicts, never assert them.
- **One-way flow.** Stay entirely inside `~/permanence`; introduce no reference that would leak its paths/contents outward.
- **No invention.** If you can't source a proposed change to existing content, don't propose it — flag the gap instead.

If `~/permanence` is missing or has no streams, say so plainly rather than inventing content.
