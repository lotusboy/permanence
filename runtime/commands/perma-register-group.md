---
description: Register a programme group — several repos that report into one shared plan-and-status folder. Adds the GROUPS.md rows and scaffolds the task doc + folder into the target repo. Use when the owner says "register a group", "these repos are one programme", or "set up a programme folder".
---

# /perma-register-group — make several repos report into one programme folder

Argument: `$ARGUMENTS` — optionally the group name and/or the target repo. Ask for whatever is missing.

`/perma-register` maps one repo to one Permanence *stream* (private working memory). **This** maps several repos
to one shared *programme folder* (a stakeholder-facing plan-and-status trail). A repo can have both, and
they're independent.

**Writes in two places, deliberately:** the group rows go in `~/permanence/_meta/GROUPS.md`; the procedure and
the folder go in the **target repo**. Nothing written into any repo may name or reference Permanence — the
task doc receives what it needs as inputs instead. That is what keeps the pointer one-way.

## Steps

1. **Establish the shape.** Confirm with the owner, one question at a time:
   - the **group name** — it should describe the *programme*, not any one repo in it;
   - the **target repo** — where the shared folder lives (usually the customer-facing or coordinating repo; it is normally a member in its own right);
   - the **members** — each repo's absolute path and a short `role` name for what that asset *is* (`engine`, `manager`, `ui`, `model`…);
   - each member's **`joined`** date — that asset's own start point, not today, so the trail reads truthfully.

   Sanity-check before writing: every path exists and is a git repo; no path is already in `GROUPS.md`
   (a project belongs to exactly one group); a one-member group is fine.

   **Scope check — ask this explicitly, don't assume.** This mechanism is for **one owner spanning
   several of their own repos** — the update reads `members` via local `git -C <path> log`, and the
   `.updating.lock` is per-clone, so it cannot coordinate two different people's separate machines. If
   the owner describes the members as belonging to different people/laptops (a dev team on a shared
   customer project, say), say plainly that this won't coordinate safely across machines and will
   produce conflicting/diverging writes if more than one person runs it — this isn't what the mechanism
   does today. Confirm every member path is reachable from *this* machine before proceeding.

2. **Add the rows** to `~/permanence/_meta/GROUPS.md` — one row in **Groups** (group, target repo, programme
   folder, task doc) and one row per member in **Membership**. If the file still holds the shipped example
   rows, replace them. Keep the rules section intact.

3. **Scaffold the task doc into the target repo.** Copy `~/permanence/templates/programme-task-doc.md` to the
   path named in the Groups row (conventionally `docs/programme/UPDATING.md`) and fill in every
   `<PLACEHOLDER>`: the role set, the model, the plan-document name, and any human-ratified document.
   - **Do not touch anything marked FIXED** — the report shape, the RAG rules, and the integrity gates are
     identical across every programme so one reader can scan them side by side. Localising them silently
     destroys that. Keep the REPORT SPEC version line.
   - Strip the scaffold's own instructional blockquote and the `» localise` notes once filled in.
   - **When the report is the owner's own working file**, the Groups row names a folder in the owner's
     stream for the target repo (`<stream>/repo/programme/`) instead of the repo. Scaffold the task doc
     there; in steps 4 and 6, "the target repo" then means that stream folder, and nothing goes in the
     repo (SPEC §2 invariant 8).

4. **Scaffold the initial folder** beside it, in the target repo:
   - `<PLAN-DOC>` (e.g. `build-plan.md`) — **human-owned**: seed the phase skeleton with the owner, or leave a clearly-marked stub. Never invent phases.
   - `status.md` — a stub noting it is generated and will be overwritten on the first run.
   - `progress/` — an empty directory (`.gitkeep`).
   - `watermarks.json` — one entry per role. **Seed each at that repo's current `HEAD`** so the first run reports only genuinely new work rather than replaying all of history. Record the seed date.
   - Add the lock to the repo's `.gitignore`: `docs/programme/.updating.lock`.

5. **State the expected first run, then stop.** Tell the owner exactly what the next "good night Permanence" in
   any member repo should produce — normally *nothing*, since every watermark is at HEAD. That prediction is
   what makes the first real run verifiable instead of merely plausible. Do **not** run the procedure now.

6. **Commit.** The `GROUPS.md` rows in `~/permanence` as one commit; the scaffolded folder in the target repo as
   another (docs only, never push). Two repos, two commits — never one that spans both.

## Guardrails

- **One-way flow.** No file written into any project repo may name Permanence, a Permanence path, or a stream.
- **A project belongs to exactly one group.** If a path is already registered, say so and offer to move it
  (set `left` on the old row, add a new one) rather than adding a second membership.
- **Unregister sets `left`; it never deletes a row.** A departed member keeps every entry it wrote; only the
  aggregate stops including it. Purging would make the trail untrue, and the trail is the point.
- **Don't seed watermarks at zero** unless the owner explicitly wants the whole history reported.
- **Gentle, accurate register** in anything written, and nothing private in the project-side files.
