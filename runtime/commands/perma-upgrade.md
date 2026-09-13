---
description: Upgrade Permanence's machinery to the latest template release — shows the plan, negotiates any customization conflicts, proposes (never auto-applies) any stream-affecting migration notes, then applies on your say-so. One command, always interactive — there's no unattended/scheduled variant.
---

# Permanence — Upgrade

The single entry point for pulling a new Permanence release: shows you what's changing before anything
changes, handles the case where you've customized a machinery file the template also touched, and reads
`CHANGELOG.md` for anything that needs a look at your own streams — proposing, never applying, per
SPEC.md invariant 5 (human ratification for state-changing maintenance).

This is always interactive — there's no separate plan/apply split like `/perma-consolidate` +
`/perma-consolidate-review`. That split exists because consolidation runs unattended on a schedule and
needs a later review step; an upgrade is something you deliberately run and sit through once, so showing
the plan and applying it belong in the same conversation.

## Phase 1 — Run the dry-run

Run `~/permanence/runtime/update.sh` (no `--apply` — dry-run is the default). This is pure git + shell,
no judgment needed yet: it reports the installed version vs. the latest tag, the changed machinery files,
which of those (if any) you've customized since your recorded version, and whether `CHANGELOG.md` changed
in the range.

If it says "No update source set", tell the owner and point at `runtime/.update-source` (pre-filled on a
fresh clone of the public template; only needs setting by hand on a private fork). If it says "Already up
to date", say so plainly and stop — nothing else to do.

## Phase 2 — Orient

Give a one-line summary before diving in: the version jump, the file count, and counts of conflicts and
whether migration notes are in range — e.g. *"v1.0.0 → v1.2.0: 6 machinery files changed, 1 customized
file needs a decision, CHANGELOG.md has a migration note to check."*

## Phase 3 — Negotiate conflicts, one at a time (only if `update.sh` flagged any)

For each customized file `update.sh` flagged, show a 3-way comparison: what you started from (the file at
your recorded `_meta/VERSION` tag), what you have now (your customized version), and what the template
wants it to become (the file at the latest tag). Ask, per file:

- **Take theirs** — discard your customization, adopt the template's version.
- **Keep mine** — leave your version exactly as it is; skip this file this upgrade.
- **I'll merge by hand** — you want both changes; don't touch the file, note it in the summary as needing
  manual reconciliation after the upgrade.

This is a discussion, not a menu dump — describe what actually changed in each version in plain terms so
the owner can decide without reading a raw diff themselves, the same spirit as `/perma-consolidate-review`
Phase 2. Record each decision; don't touch any file yet.

## Phase 4 — Read CHANGELOG.md for migration notes (only if `update.sh` flagged CHANGELOG.md changed)

Read the entries between the installed version and the latest tag. For each one with a **Migration
notes** section:

1. Understand what convention or shape changed and why.
2. Check the owner's actual streams (via `~/permanence/_meta/REGISTRY.md` → the registered stream folders)
   for whether it applies to them at all — many migration notes won't touch every stream.
3. Where it does apply, propose the concrete edit — classify it **mechanical** (safe, reversible, quote
   the exact `old → new`) or **judgement** (needs the owner's call), exactly the same split
   `/perma-consolidate` uses for its own proposals.
4. Propose only. Nothing here is ever applied without the owner explicitly accepting it in Phase 5 — this
   is the one place an upgrade could otherwise silently rewrite stream content, and SPEC.md invariant 5
   forbids that.

If there's nothing applicable to this owner's actual streams, say so and move on — don't invent work.

## Phase 5 — Final confirm, then apply

Summarize everything that will happen: the machinery paths being updated, each conflict's resolution, and
each accepted migration-note edit. One go-ahead: **apply as summarised** / **adjust something first** /
**cancel** (nothing changes). Loop until the owner is satisfied — the same catch-mistakes gate as
`/perma-consolidate-review` Phase 3, just inline instead of a separate command.

On go-ahead:

1. Run `~/permanence/runtime/update.sh --apply` — it checks out the non-conflicted machinery paths,
   re-runs `install.sh`, commits the change, and writes `_meta/VERSION`.
2. **Verify it actually finished — don't trust the printed "✅" alone.** Run
   `~/permanence/runtime/update.sh` again (plain dry-run). If it says "Already up to date," the apply
   genuinely completed. This closes a real gap: a release that adds a whole new tracked path can, on an
   install whose currently-running `update.sh` predates that fix, report success while quietly leaving
   that new path undelivered, because the script decided "am I done?" using its own file list from
   *before* it updated itself — treat this verification as a standing step, not a one-time check.
   If the dry-run instead reports more changed files, one of two things is true, and the dry-run's own
   output tells you which: if it lists them as plain changes with no "⚠️ file(s) need review," run
   `--apply` once more — that finishes it. If it flags them as needing review instead, treat them exactly
   like any Phase 3 conflict (a brand-new file the owner never touched reads the same to `update.sh` as
   one they deliberately removed, so it asks rather than guessing): they were never applied on your
   original install, so "take theirs" is almost always the right call — negotiate quickly, then apply.
3. For each "take theirs" conflict: check out that specific path from the latest tag and add it to the
   same commit (or a clearly-labeled follow-up commit — never silently folded in with no trace).
4. For each accepted migration-note edit: apply it to the relevant stream file(s), in a separate commit
   from the machinery update (a stream edit and a machinery refresh are different kinds of change and
   should be revertable independently).
5. Anything the owner chose "keep mine" or "I'll merge by hand" on: leave untouched, and say so plainly in
   the close-out so it isn't forgotten.

## Guardrails

- **Never touch a stream without an explicit accept.** Migration-note proposals are exactly that —
  proposals — until Phase 5's go-ahead.
- **Never silently overwrite a customization.** That's the entire reason Phases 1 and 3 exist.
- **One-way flow, gentle register, append-don't-rewrite** — the same conventions as every other
  Permanence-writing pass, since a migration-note edit can touch `PEOPLE.md`/`PROJECT.md` like any other.
- **Start a fresh session after applying** so the refreshed hooks/commands load.

If `~/permanence` is missing, or `update.sh` isn't present (a very old install), say so plainly rather than
improvising a substitute procedure.
