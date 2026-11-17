---
description: "List every registered Permanence stream — name, what it is, when it was last touched, and its real-world path if it has one. Read-only. Trigger phrases: \"list my projects\", \"list permanence projects\", \"what's registered in Permanence\"."
---

# /perma-list — see what's registered

A quick read-only index of every Permanence stream, mainly so a project **name** can be
found before it's used with `/perma-startup <name>` or `/perma-shutdown <name>` — those
commands need an exact match, and this is how you get one instead of guessing.

## How to run it

1. **Discover the streams:** run `~/permanence/runtime/list-streams.sh`. Each line is a stream name, a tab, and its folder
   under `~/permanence/`; `perma-meta` comes first. New streams show up automatically — don't rely
   on a stale list from memory. Then run it with `--check`: each name it prints is registered in
   `_meta/REGISTRY.md` but has no `PROJECT.md`, so no command sees it. List those last, under
   "registered, but not a stream yet: check the name in `_meta/REGISTRY.md`, or add a PROJECT.md".
2. **For each stream**, gather:
   - The stream name (its path relative to `~/permanence`).
   - A one-line "what it is", read from `PROJECT.md`'s opening description.
   - Its `Last updated` date from `PROJECT.md`'s header.
   - Its registered real-world path, if any — check `~/permanence/_meta/REGISTRY.md` (or run
     `~/permanence/runtime/resolve-path.sh <stream>`; a stream can have zero, one, or more
     rows). No path is a normal outcome (a topic-only project), not an error.
3. **Mark the active stream, if there is one.** If a stream is currently the active stream
   for this conversation (set by an earlier `/perma-startup` or `/perma-register` call this
   session), mark it plainly — e.g. a leading `→` — so it's obvious at a glance which one
   the conversation is currently in.
4. **List them**, most-recently-updated first, one line each: name, the active marker if
   any, the one-line description, the path (or "no registered path").

## Guardrails

- **Read-only.** Never writes anything to Permanence — same class as `/perma-brief`.
- **Don't editorialise.** Just the facts pulled from each stream's own `PROJECT.md`/registry
  row — no opinions on which project to work on next (that's `/perma-startup`'s job, scoped
  to one stream).

If `~/permanence` is missing, say so plainly rather than inventing content.
