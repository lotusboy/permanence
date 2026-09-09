---
description: Register an existing project as a Permanence stream — read its README, create the stream (seeded from the README), and add it to the registry. Use when the owner says "register this project", "register `<path>`", or passes a path to a README.
---

# /perma-register — turn an existing project into a Permanence stream

Argument: `$ARGUMENTS` — a path to the project folder **or its README**, **or just a name** if there's no path at all yet (empty → use the current working directory). The owner typically says *"register this project, here's the README: `<path>`"* — or, with nothing to point at, *"start a new project called kitchen renovation"*.

**Read-only on the project, with one exception.** The only things this writes are the new stream + one registry row (both inside `~/permanence`), and — only if the resolved path doesn't exist yet — the empty folder itself (step 1). Never write *into* an existing project repo, and never write Permanence content into the project (one-way flow).

## Steps

0. **Refuse container folders.** If `$ARGUMENTS` (or the cwd, if empty) is a home directory, `/`, `/Users`, or the bare `Desktop` / `Documents` / `Downloads` root, **stop and do not register it** — say so plainly and explain: a session opened without its working folder set lands in the home folder, so registering that would make every such session load a meaningless stream and the wind-down would start writing state into it. Tell them to set the session's working folder to the project's own folder and re-run. *(A folder **inside** `Documents` is fine — it's the container roots that are wrong. Not applicable to a name-only registration — step 1 always picks a fresh, non-container folder for those.)*

1. **Resolve the project — a path, or just a name.**
   - **`$ARGUMENTS` is empty, or looks like a path** (starts with `/` or `~`), or **is an existing file or directory**: resolve it the normal way — a README file → the project root is its directory; a directory → find its README (`README.md`, `readme`, etc.); empty → use the current directory. **If the resolved path doesn't exist on disk yet, create it** (`mkdir -p`) rather than failing. State the project root you resolved (and whether you created it). *(No README and none findable? Skip to step 2 using whatever the owner described — a stream can be seeded from a plain description.)*
   - **Otherwise — `$ARGUMENTS` is just a name, no path at all** (the owner has nothing to point at, e.g. a topic-only desktop-app conversation): don't ask them for a path — most people who'd say this have no idea what one is. Instead:
     1. Derive a slug from the name, the same way step 3 does.
     2. **Check whether that name is already a registered stream first** (same discovery `/perma-list` uses). If it is, this is a *resume*, not a new registration — stop here, say so plainly, and point at `/perma-startup <name>` instead of creating anything.
     3. **No match → pick the real folder for them:** `~/Permanence Projects/<slug>` (create parent folders as needed). If that exact folder already exists on disk, disambiguate deterministically — `<slug>-2`, `<slug>-3`, … — and say so plainly rather than silently picking one.
     4. `mkdir -p` it. This is now the resolved project root — continue at step 2 using whatever the owner described (there's no README to look for).

   Either way, this is the only case where this command writes outside `~/permanence` — and only the empty folder itself, never files inside it.

2. **Understand the project — README-level, not a deep dive.** Read the README (skim the top-level layout / `package.json` / `pyproject` only if quick). Enough to write an honest one-paragraph "what it is" + a read of its current state.

3. **Propose a stream name, then confirm.** Suggest a stream path — `<area>/<slug>` (e.g. `home/<slug>`, `work/<slug>`) or just `<slug>`, derived from the project name. Ask one plain question: *"Register it as `<stream>`? (or tell me a different name/area.)"* Don't proceed until the owner confirms.
   - If the project's **path** is already in `_meta/REGISTRY.md`, say so and offer to refresh the existing stream instead of duplicating.
   - If `~/permanence/<stream>/` already **exists for a different path**, don't write into it — that would silently merge two unrelated projects' notes into one stream. Say so plainly and ask for a different name instead.

4. **Create the stream** at `~/permanence/<stream>/` (use `~/permanence/templates/*.template.md` skeletons if present; otherwise write the canonical files directly):
   - `PROJECT.md` — `> Last updated <today>` header, a "What it is" paragraph, current phase/state as best read from the README, and an "Open" section for anything it flags as TODO/roadmap.
   - `LOG.md` — one dated entry: *"Stream created + registered from `<project path>`."*
   - `QUESTIONS.md`, `PEOPLE.md` — light skeletons, ready to grow.
   Write in the owner's voice as far as the README reveals it; gentle, accurate register. **Capture the *shape* + state, never a wholesale dump of the project's contents.**

5. **Register it.** Append a row to `~/permanence/_meta/REGISTRY.md`: `| <project absolute path> | <stream> | <one-line note> |`. Keep the longest-prefix ordering note intact.

6. **Commit** the new stream + the registry row in `~/permanence` as one commit (`register <stream> from <project>`).

7. **Confirm.** Tell the owner: the stream is at `~/permanence/<stream>`, registered to `<path>` — **next time they open that project, Permanence loads its context automatically.** Suggest they just start talking to Claude about the project to grow the stream. If step 1 picked the real folder for them (the name-only case), say plainly where it ended up — e.g. *"I've made a folder for this at `~/Permanence Projects/kitchen-renovation`, in case you ever want to open it directly"* — a project shouldn't live somewhere its owner would be surprised to find it. This stream is now **the active stream for the rest of this conversation** — every standing "update the stream when something material shifts" write targets it, until changed by a `/perma-startup <name>` or another `/perma-register` call.

## Guardrails
- Read-only on an *existing* project; the only write outside `~/permanence` is creating a
  not-yet-existing folder in step 1, and only that — never files inside it.
- README-level understanding only — don't trawl the whole codebase.
- Never copy confidential project content wholesale; capture the shape + current state.
