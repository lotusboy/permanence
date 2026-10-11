---
description: "End-of-day wind-down — capture where things stand into this project's Permanence stream (PROJECT + QUESTIONS) and hand back a Done / in-flight / first-move-tomorrow summary, so the open loops leave your head instead of coming home with you. Optional argument: a Permanence stream/project name, OR an absolute path to a registered project — either works, for sessions with no meaningful working folder (desktop AI apps). Trigger phrases: \"good night Permanence\", \"night Permanence\"."
---

# Permanence — Shutdown

The evening bookend to `/perma-brief`. When I'm wrapping up for the day, get every open loop out of my head and into this project's Permanence stream, so tomorrow's `/perma-brief` hands them straight back — and I'm not carrying half-finished threads home to 11pm. This is **strictly a wind-down**: do NOT start new work, open investigations, or fix anything.

## How to run it

1. **Find the stream.**
   - **No argument (`$ARGUMENTS` empty):** run `~/permanence/runtime/resolve-stream.sh "$(pwd -P)"` to get the stream for this workspace. If it comes back empty (unregistered) or `perma-meta`, skip the writes — just give me the chat summary (step 6) and note the workspace isn't a registered stream.
   - **Argument looks like a path** (starts with `/` or `~`): run `~/permanence/runtime/resolve-stream.sh "<the given path>"` — it accepts any path, not just the working directory. Empty result → say so plainly, same as the no-argument case.
   - **Argument looks like a name** (anything else): treat it as a stream name directly. Confirm `~/permanence/<name>/PROJECT.md` exists. If there's no exact match, run `/perma-list` to see what's registered, and if more than one name looks close, list the candidates and ask which one — never guess.
2. **Light pass over today — no deep digging.**
   - **Resolved via cwd or a given path:** that path *is* the real project repo — read `git status` and today's commits (`git log --since=midnight --pretty=format:"%h %s"`) there.
   - **Resolved by name:** look up the real path with `~/permanence/runtime/resolve-path.sh <stream>`. No match → skip this pass and say so plainly (the stream may be topic-only, with no project repo attached). One match → run the same `git status`/`git log` there. More than one match → list them and ask which folder first.
   - Either way, take stock of where the current session left off. **Include uncommitted changes and in-flight session state** — the resume point must reflect where I *really* am, not just the last commit (much of my work runs through agent batches / uncommitted edits, so last-commit alone under-captures it).
3. **Update the stream gently — surgical edits, preserve the curated content:**
   - `PROJECT.md` → refresh only "where things stand" (what moved today, what's mid-flight). Edit the affected lines, leave the rest intact, and bump the `Last updated YYYY-MM-DD` header to today. Do **not** regenerate the file.
   - `QUESTIONS.md` → add any genuinely new open threads that surfaced today, in the file's existing format/numbering. Don't duplicate ones already there; don't close anything.
   - Do **NOT** write `LOG.md`. The wind-down is about current state + open threads, not a chronological entry — this keeps the daily run from churning the log and colliding with the nightly consolidate. (If I ever want a daily log line, that's a deliberate add.)
4. **Programme group task, if this workspace is in one.** *(Optional feature — if `~/permanence/_meta/GROUPS.md` doesn't exist, or its tables hold only the example rows, skip this step silently.)* Look up the workspace in `~/permanence/_meta/GROUPS.md` (longest-prefix match on cwd, same as the registry; a project is in exactly one group). If it has a row and no `left` date, read the group's **task doc** (in the target repo, or at the absolute path the row gives) and follow it, passing in this workspace's `role` and the group's current members with their local paths. The task doc owns the whole procedure — Permanence holds only the pointer, so no project file ever names Permanence. If the workspace is in no group, skip this step silently.
5. **Commit Permanence writes.** In `~/permanence`, `git add` **only this stream's files** (the ones you touched in step 3) and commit them — message `shutdown(<stream>): <one line on what moved>`. Do **not** `git add -A`: another session may have its own writes in flight elsewhere in Permanence, and sweeping those into this commit would mix unrelated work. Nothing to commit is a normal outcome — say so rather than making an empty commit. Never push (Permanence is local-first; if it has a remote at all, pushing is a separate deliberate act). *This step is the whole point of the wind-down: an uncommitted write is the one state git cannot recover, so a shutdown that leaves changes loose has not actually put the day away.*
6. **Hand me a short summary — in chat, NOT saved to Permanence:**
   - ✅ **Done today** — what actually got finished.
   - 🔄 **In-flight** — each with an exact resume point (`file:line`) + the next action, so tomorrow-me doesn't have to reconstruct where I was.
   - 🎯 **One first move for tomorrow** — the single best thing to pick up first.
   - 🤝 **Waiting on / handoffs** — anything blocked on someone else, or emitted to another stream.
   - 💾 **Last backup** — one line: `ls -1t ~/Backups/perma-*.bundle.age | head -1`, its date from the filename, and "N days ago". No file → "no backup found". This is the last local backup `runtime/make-backup.sh` wrote; the off-machine copy is manual, so it may be older. At 7 days or more, add: run `runtime/make-backup.sh` after this commit, then copy the newest files in `~/Backups/` to the Drive.
7. **Close gently.** Tell me it's fine to stop and close my tabs — the loops are in Permanence now **and committed**, and `/perma-brief` will hand them back when I want them, not tonight. Only say this once step 5 has actually committed (or confirmed there was nothing to commit); if the commit failed, say that plainly instead — a false "it's safe to stop" is worse than no reassurance.

## Guardrails

- **Wind-down only.** No new work, no investigations, no fixes, no refactors — if something's tempting, note it as a first-move or an open question and leave it.
- **One-way flow.** Write to Permanence stream (that's its job); never write Permanence paths or references into the project repo's own files.
- **People.** If an open thread involves a person, follow the people-rule: observable behaviour + impact as fact, any read of *why* as a dated provisional inference, gentle accurate register — never fixed character.
- **Gentle register.** Internal phrasing can be blunt; what lands in the files is rendered kind and accurate — same meaning, safer key.

If `~/permanence` is missing or this workspace has no stream, say so plainly rather than inventing content.
