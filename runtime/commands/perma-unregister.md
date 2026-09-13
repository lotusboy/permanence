---
description: Remove a registered Permanence stream — deletes its folder (including gitignored derived files like CONTENTS.md) and its _meta/REGISTRY.md row in one step, so nothing is left orphaned. Destructive; always confirms first. Use when the owner says "unregister this project", "remove the <name> stream", or "delete the <name> project from Permanence".
---

# /perma-unregister — completely remove a Permanence stream

Argument: `$ARGUMENTS` — a stream name or its registered real-world path (same name-or-path
duality as `/perma-startup`/`/perma-shutdown`). Empty → resolve the current working directory
the same way `/perma-shutdown` does.

**Destructive.** This permanently deletes a stream's folder and its history. There is no undo
except `git revert` on the commit this makes — and even that only restores what was
git-tracked, never anything gitignored that happened to be sitting there uncommitted.

## Steps

1. **Resolve the stream** — same rule as `/perma-startup`: if `$ARGUMENTS` looks like a path or
   is empty (resolve the cwd via `resolve-stream.sh`), map it through `_meta/REGISTRY.md`;
   otherwise treat it as a stream name directly (exact match — use `/perma-list` first if
   unsure). Not found → say so plainly and stop.

2. **Check for uncommitted work first.** `git -C ~/permanence status --short -- <stream>/` — if
   anything shows, stop and say so; don't delete uncommitted content silently.

3. **Show what will be removed, then confirm — don't proceed without an explicit yes.** Tell the
   owner:
   - The stream's folder, `~/permanence/<stream>/`, and roughly how much is in it (file count,
     or the LOG's date range — enough to make the loss concrete, not just a path).
   - Every `_meta/REGISTRY.md` row that points at this stream (a stream can have more than one).
   - Whether it appears in `_meta/GROUPS.md` as a member of a programme group — if so, say so
     and ask **separately** whether to also drop it from there. Don't fold this into the same
     yes/no: group membership has its own lifecycle (a `left` date, never outright deletion, per
     `SPEC.md` invariant 8), so silently touching it either way would be wrong.

   Ask plainly: *"Delete `<stream>` and its history? This can't be undone except by reverting
   the commit."* Stop here on anything but a clear yes.

4. **Delete the folder outright** — `rm -rf ~/permanence/<stream>/`, not `git rm -r`. A plain
   `git rm -r` only removes git-tracked files; it leaves the stream's own gitignored
   `CONTENTS.md` behind as an orphaned, near-empty folder — the exact bug this command exists to
   stop recurring. `rm -rf` clears the whole folder, tracked and gitignored content alike.

5. **Remove every matching row** from `_meta/REGISTRY.md` (all of them from step 3, not just the
   first).

6. **Stage and commit as one commit.** `git -C ~/permanence add -A` (this picks up both the
   folder's now-deleted tracked files and the `REGISTRY.md` edit in one pass), then commit:
   `unregister <stream> — removed by request`.

7. **Confirm.** Tell the owner it's gone, the commit hash, and that reverting that commit
   restores the git-tracked files (CONTENTS.md won't come back — it was never committed, and
   regenerates instantly for any other stream that still exists).

## Guardrails

- **Confirm before deleting, always.** This is the one command in this system that destroys
  committed history; every other command only appends or edits state.
- **Never silently touch `_meta/GROUPS.md`.** Ask about group membership separately from the
  stream-deletion confirmation — see step 3.
- **`rm -rf`, not `git rm`.** The whole point is removing gitignored derived files
  (`CONTENTS.md`) too, which `git rm` cannot touch.

If `~/permanence` is missing, or the resolved stream doesn't exist, say so plainly rather than
inventing content.
