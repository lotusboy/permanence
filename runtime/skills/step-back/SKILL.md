---
name: step-back
description: >-
  Call a step back and give a helicopter view when a chain of work shows tension, before spending
  more. Use this skill whenever any tension signal fires: an estimate overruns by 1.5x or more twice
  in a row; a fix round produces a new finding of the same kind; a review finds a second defect in
  code written to fix the first; a third agent is dispatched on one item; work drifts from the
  stated goal or plan item; a ceiling is raised for the same item twice; the owner asks "are you
  finding a way", "is everything OK", "why so many", "scattergun", "rabbit hole", "remember
  seesaw", "screenshot it"; or you notice yourself writing "one more round". Also use it before
  dispatching any fix round whose finding came from the previous fix round.
---

# Step back — the helicopter view

A chain of fixes can feel like progress while it is circling. The signals below are cheap to see
and expensive to ignore: on 2026-10-06 a chain spent about 1.4M tokens with no premium or rule moved,
and on 2026-10-07 four consecutive rounds ran at about twice their estimates. The rule: **when a
signal fires, stop dispatching and give the owner the view from above, with options, before the next
round.**

## 1. Name the signals that fired

Count them; do not paraphrase. Each with its evidence in one line:

| Signal | Fires when |
|---|---|
| Overrun | actual ≥ 1.5 × estimate, twice in a row on one item or chain |
| Finding from a fix | a review finding sits in code written to fix the previous finding |
| Agent count | a third agent (engineer, reviewer, fixer) is about to start on one item |
| Ceiling creep | the ceiling has been raised twice for the same item |
| Drift | the work no longer serves the goal or plan item stated at the start |
| Same class again | a fix needs its second guard, or the same failure class returns |
| Owner nudge | the owner asks how it is going, names a method, or names a feeling |
| Compensation pile | a per-product correction, override or declaration file grew this round, or the same kind of correction is being added a second time. The progress measure fell because something was recorded, not because the cause was fixed |

**Compensation pile is never one of many.** On its own it stops the next dispatch. Seesaw the step
that produced the defects, and fix that step instead of adding the next correction. Learned
2026-10-09: a falling gap count hid about 270 hand corrections on one product.

One signal: mention it in the next update. **Two or more, or any owner nudge: run the rest of this
skill before the next dispatch.**

## 2. The helicopter view

Write it in plain logic-level sentences, one idea per sentence:

1. **Goal.** What we set out to do, and the plan item it serves.
2. **Where we are.** What is done and proven, as counts. What is still open.
3. **What the chain has cost.** Tokens per round, against each estimate.
4. **Where the tension is.** The signals that fired, and the one place they point to.

## 3. Options — always the first three, each with a cost and what it would show

- **Seesaw.** Name the layers from the raw document to the output (raw → pre-processor → extracted
  → AI pass → assembler → rater → page). Ask which layer actually owns the cause. Repeated failure at
  one layer is evidence the cause sits upstream of it. Say which layer you now suspect, and why.
- **Look at the raw item (Live Prism).** Render it: an xlsx sheet with qlmanage, a PDF page, a DOCX
  page, a screenshot. Compare what a person sees with what the failing layer was given. Name the
  exact file, sheet, page or cell you would render.
- **Park or re-scope.** Stop here, record the state and the open question in the backlog, and
  return to the plan. Say what is lost by parking and what is saved.

- **Architecture (offer when the tension concentrates in one part).** Offer it when the same
  file took two or more consecutive fix rounds in this chain, or when the repo's reshape signal shows
  the part `ready` or `ready-again`. Measure both before offering:
  - the chain's own count: `git log --since=<chain start> --oneline -- <file> | wc -l` for each
    file the rounds touched. Count every commit, not only `fix`-prefixed ones: work-order commits
    (`A<n>: …`) are invisible to the reshape signal;
  - the repo's health signal, where its binding names one: run `/perma-health`, which reads the
    signal and lists the parts that are `ready` or `ready-again`.
  Give the figures, then offer `/perma-refactor <part>`: the architect lays out restructure or
  accept, and the owner decides. Never start a refactor from a step back.
  - **When the Compensation pile signal fired, offer the architect in REDESIGN mode.** Fix commits
    will not show this problem, because it lives in correction files and in a step's method. Give
    the correction count, and the file it grew in, as the figure. The architect counts the
    corrections by cause and traces each cause to the step that produced it.

Add another option only when a real one exists (for example, an owner decision that would end the chain).

## 4. Recommend one, and ask

State the recommendation outright: "do X". Ask one question. Do not dispatch the next round until
the owner answers, unless the owner has already said to keep going for this item; then say which
signals fired and carry on with the Seesaw or the render first, not another fix round.

Where the owner keeps the decision ledger, record the question with `~/permanence/runtime/decision.sh
ask` before sending it (category, the options, the recommendation and your confidence), and record the
owner's reply with `decision.sh answer`. See the PM role's records section (`runtime/roles/pm.md` §8).

## Hard rules

- Never answer a tension signal with another fix round alone. The next action is a Seesaw, a render
  or a park.
- Brief every engineer and reviewer to run Seesaw and render the raw input before any fix. This is
  the same rule as the live-prism skill.
- Report the signals honestly, including your own estimating misses.
