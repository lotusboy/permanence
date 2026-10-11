---
description: "Morning bookend to /perma-shutdown — project-specific \"where you left off\" plus a small (2-3) set of next-task options for the current repo's Permanence stream. Optional argument: a Permanence stream/project name, OR an absolute path to a registered project — either works, for sessions with no meaningful working folder (desktop AI apps) or to switch projects mid-session. Trigger phrases: \"good morning Permanence\", \"morning Permanence\"."
---

# Permanence — Morning

The morning bookend to `/perma-shutdown`, scoped to *this* project only — not the cross-stream `/perma-brief`. When I open a project and say "good morning Permanence" (or "morning Permanence"), get me oriented fast: where I left off, and a short list of what to pick up next. This is strictly orientation — do NOT start work, investigate, or fix anything.

## How to run it

1. **Find the stream.**
   - **No argument (`$ARGUMENTS` empty):** run `~/permanence/runtime/resolve-stream.sh "$(pwd -P)"`. If it comes back empty (unregistered) or `perma-meta`, say so plainly and stop there — don't fall back to a generic brief, and don't invent project content for an unregistered workspace.
   - **Argument looks like a path** (starts with `/` or `~`): run `~/permanence/runtime/resolve-stream.sh "<the given path>"` — it accepts any path, not just the working directory. Empty result → say so plainly, same as the no-argument case.
   - **Argument looks like a name** (anything else): treat it as a stream name directly. Confirm `~/permanence/<name>/PROJECT.md` exists. If there's no exact match, run `/perma-list` to see what's registered, and if more than one name looks close, list the candidates and ask which one — never guess.
2. **Read the stream:**
   - `PROJECT.md` — the "Current state" / "where things stand" block, and its `Last updated` date.
   - `QUESTIONS.md` — only the still-open items with an actual next action for me (skip ones purely waiting on someone else).
   - The **tail** of `LOG.md` — last few entries only, to catch anything since PROJECT.md was last touched.
3. **Staleness check** — same as `/perma-brief`: if `LOG.md`'s most recent entry is dated after `PROJECT.md`'s `Last updated` header, flag it (the headline may be behind).
4. **Cross-check the real repo, not just Permanence.**
   - **Resolved via cwd or a given path:** that path *is* the real project repo — `git status` and recent commits (`git log --pretty=format:"%h %s" -10`) there.
   - **Resolved by name:** look up the real path with `~/permanence/runtime/resolve-path.sh <stream>`. No match → skip this cross-check and say so plainly (the stream may be topic-only, with no project repo attached). One match → run the same `git status`/`git log` there. More than one match → list them and ask which folder before cross-checking.
   - Either way: if there are uncommitted changes or a resume point `/perma-shutdown` captured recently, that's the ground truth for "where I left off" — Permanence stream gives the why, the repo gives the exact state.
   - **Check the repo's team binding.** Once step 4 has settled on one repo folder (the cwd, the given path, the single match, or the folder the owner picked), run `python3 ~/permanence/runtime/team-preflight.py startup --repo "<that folder>"` with the path quoted. It reads files only and costs no AI spend. Exit 0 means the binding is fine or the stream has none: say nothing about it, including any `note` lines it printed. Exit 1 means the binding is broken or has drifted from the repo (most often a renamed gate id): carry each `FAIL` line into the hand-back. Any other exit is a usage error: mention it in one line. In every case, carry on — preflight never stops the orientation.
5. **Set the active stream.** This stream is now **the active stream for the rest of this conversation** — every standing "update the stream when something material shifts" write targets it, until changed by another `/perma-startup <name>` or `/perma-register` call.
   - **If a different stream was already active this session**, don't switch silently: ask first — *"You haven't wound `<old-stream>` down — want me to run the shutdown flow for it before switching to `<new-stream>`, or switch anyway?"* Only proceed once answered. If they say switch anyway, say plainly that anything this conversation surfaced about `<old-stream>` is only in this conversation until captured.
6. **Hand back a short, scannable orientation — chat only, nothing written to Permanence:**
   - 📍 **Where you left off** — one or two lines, concrete (file/ticket/resume point from step 4), not a history recap.
   - 🎯 **Next task options** — 2, at most 3. Each one line: what it is, why it's a candidate. If one is obviously the right next move, just say so plainly instead of forcing a choice between equals.
   - 🤝 Only if relevant: anything that unblocked overnight (a handoff or open question now answered).
   - 🔧 Only if preflight failed: each failure line, and that team jobs (`/perma-change`, `/perma-refactor`, `/perma-health`) will refuse to start until the binding is fixed.

## Guardrails

- **Small, not exhaustive.** Cap at 3 options, ranked if there's an obvious first. If the stream has a long open-questions list, that's a `/perma-brief`-scale problem, not a morning-orientation one — surface only what has a real next action today.
- **One project only.** Don't pull in other streams — that's `/perma-brief`'s job. Scoped strictly to the one stream resolved in step 1, whether that came from `pwd` or a given name.
- **Read-only.** Like `/perma-brief`, this doesn't write anything to Permanence. Preflight is read-only too.
- **Orientation only.** No new work, no investigation, no fixes — even if something looks quick.
- **Gentle register**, same as the rest of Permanence.

If `~/permanence` is missing or this workspace has no stream, say so plainly rather than inventing content.
