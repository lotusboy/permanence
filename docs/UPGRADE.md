# Upgrading Permanence

Two separate things, easy to conflate:

- **Installing for the first time** — see [QUICKSTART.md](../QUICKSTART.md). You get the latest release
  the moment you clone.
- **Pulling a new release into an install you already have** — this page.

## The command

```
/perma-upgrade
```

Run it from a session with `~/permanence` set up. It:

1. Checks your installed version (`_meta/VERSION`) against the latest tag in the configured source
   (`runtime/.update-source` — pre-filled if you cloned the public template).
2. Shows you what machinery would change — file by file — before touching anything.
3. Flags any machinery file you've customized that the new release also changed, and asks what you want
   to do about each one (take the new version, keep yours, or merge by hand). Nothing is silently
   overwritten.
4. Reads `CHANGELOG.md` for anything in the version range that might affect your own streams — a
   **Migration notes** section — and proposes concrete edits if any apply. These are proposed for you to
   accept, never applied automatically.
5. Applies whatever you accept, in one or a few clearly-labeled, revertable commits, and updates
   `_meta/VERSION`.

That's the whole thing — one command, one guided conversation, ending with either a clean upgrade or
nothing changed at all if you cancel partway through.

## What a conflict looks like

If you've edited a machinery file directly (say, you customized `runtime/commands/perma-shutdown.md`) and
a new release also changes that file, `/perma-upgrade` won't pick a winner for you. It shows you what you
started from, what you have now, and what the release wants — then asks. This is the only place an
upgrade needs your judgment; everything else is mechanical.

## Why `/perma-upgrade` double-checks itself after applying

Occasionally a release adds a whole new tracked file or folder, not just a change to an existing
one. `update.sh` decides what's changed using the copy of itself already sitting on your machine
— which can't know about a brand new path until *after* it's finished updating itself. Left
alone, that could report success while quietly leaving the new path undelivered.

You don't need to do anything about this — `/perma-upgrade` already handles it, by re-running
`update.sh` once more after every apply and applying again if that second pass finds more to do.
It's a standing safety check, not something you'll normally notice.

## Migrating from an old `~/brain` install

If you're on a pre-rename install (the folder is `~/brain`, commands are `/brain-*`), that's a one-time
move, not something `/perma-upgrade` does automatically — clone this repo somewhere (or download a
release), then run:

```
bash runtime/migrate-from-brain.sh
```

It renames `~/brain` to `~/permanence`, refreshes its machinery, cleans up the old commands/launchd
jobs/`CLAUDE.md` block/settings.json entries, and re-runs `install.sh`. Your git history is untouched —
only the working-tree copies of the machinery paths are refreshed, same as any other upgrade. Run it once
per install; after that you're on the same footing as a fresh install and `/perma-upgrade` works normally
from then on.

## If something goes wrong

Every apply lands as a normal git commit in your own `~/permanence` history — `git log` shows exactly what
changed, and `git revert` undoes it like any other commit. Nothing here is a special, harder-to-undo kind
of change.
