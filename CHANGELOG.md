# Changelog

Releases of Permanence **machinery** — `runtime/`, `.githooks/`, `templates/`, the
docs, and the forward-looking `design/` docs for work substantial enough to need one.
Your own streams, `_meta/REGISTRY.md`, and notes are never part of a release; they're
yours, not the template's.

Tagged `vMAJOR.MINOR.PATCH`. `/perma-upgrade` diffs your installed version (recorded
in `_meta/VERSION`) against the latest tag here and walks you through what changed.

A release entry gets a **Migration notes** section only when it changes something
that existing streams may need to adapt to (a `SPEC.md` convention, a canonical file's
expected shape). No section = nothing for your streams to do; `/perma-upgrade` just
refreshes machinery as usual. Migration notes are read and *proposed* against your
streams, never applied without your say-so (SPEC.md invariant 5).

## [Unreleased]

## [1.4.0] — the binding contract: decoupling Permanence from any one AI tool's mechanics

**New in `SPEC.md` §3: the binding contract.** Permanence's support for an AI tool is now defined
as five independent questions — passive orientation, forcing read, standing instruction, command
invocation, headless invocation — rather than a tool being labelled wholesale. Two properties
that weren't previously written down anywhere:

- **Forcing subsumes passive.** A harness with only one usable injection point binds it to the
  forcing read and omits passive orientation entirely. That is a *complete* binding, not a
  degraded one.
- **The standing-instruction question is the one whose absence is silent.** Without it the model
  never learns to update streams unprompted, nothing raises an error, and the failure surfaces
  only as an empty `LOG.md` weeks later. It should be verified first, not last.

Also recorded: material-shift is not a separate question (it's what the forcing read and the
standing instruction produce together), and on-commit/on-schedule are not harness questions at
all — git fires one, the OS scheduler the other.

**Numbered tiers (Tier 1/Tier 2) are retired.** A tier is ordinal; the five questions are a set.
Two tools with opposite failure modes — one reads manually but writes automatically, one reads
automatically but silently never writes — collapsed to the same "Tier 2" label, hiding exactly
the difference that matters most. Each binding now states plainly **what the owner carries**.
`docs/TOOL-SUPPORT.md` gains a capability table; `README.md` keeps its plain-English "fully
automated on Claude Code", now phrased as what you carry rather than a tier number. Historical
CHANGELOG entries still mention tiers and are deliberately left alone — they record what those
releases actually said.

**A binding is now a directory.** `runtime/bindings/<harness>/` holds `detect` and `wire`, plus
any small translators that harness's hook contract needs; the core (`session-start.sh`,
`session-load.sh`, `runtime/commands/*.md`, the block files) emits harness-neutral text and never
varies. The intent is that `runtime/install.sh` iterates `runtime/bindings/*/`, so **adding a
harness adds a directory and changes no existing file.** *(Contract and structure only — the
iteration in `install.sh` is not implemented in this release.)*

**New: `design/harness-binding-mechanism.md`** gives that mechanism its own design, separate
from either tool binding — the `detect`/`wire` interface, the proposed `install.sh` loop, and the
decision the two tool docs were each silently assuming: Claude Code's existing wiring stays
outside this mechanism, deliberately, rather than migrating for symmetry alone — a real
regression risk (its wiring carries real hardening: backup-before-edit, a mismatched-marker
refusal, the different-Permanence-owns-this-job warning) for a benefit that's aesthetic, not
functional. `runtime/bindings/` is for what's genuinely optional; Claude Code isn't. Both tool
docs' shape sections now reference this doc instead of each re-deriving the same mechanism.

**Two corrections to `docs/TOOL-SUPPORT.md`, found while researching the above.** Both were
shipped inaccuracies: Gemini CLI was listed among tools reading `AGENTS.md` (it reads `GEMINI.md`
and does not support `AGENTS.md` — confirmed against its own configuration reference), and
Antigravity was described as reading `AGENTS.md` when its context-file convention isn't confirmed
either way. Anyone who tried Permanence on Gemini CLI expecting that path to work would have got
nothing, with no error.

**New: `design/`**, tracked by `runtime/update.sh` so a future edit reaches existing installs via
`/perma-upgrade`. First three entries are design docs for the harness-binding mechanism itself, a
Gemini CLI binding, and an Antigravity binding — proposed, unbuilt, each verified against that
tool's own docs and explicit about what remains unverified. Despite a shared `~/.gemini/` path
prefix, Gemini CLI and Antigravity need genuinely separate bindings: their hook vocabularies are
entirely different.

**Fixed a real correctness bug in `update.sh`, found by actually testing this release before
shipping it, not just by lint/link checks.** Adding `design` to the tracked paths above surfaced
it: `update.sh` decides "am I fully caught up?" using its own currently-installed file list, which
can't know a release added a brand new tracked path until *after* it's finished updating itself.
Reproduced directly against a real scratch install: `_meta/VERSION` reached `v1.4.0` — full
agreement, nothing pending — while `design/` was never delivered and never would be, since the
next `/perma-upgrade` would see `v1.4.0 → v1.4.0` and stop at "already up to date" before checking
again. Silent, permanent, and reported as success.

Fixed at two layers. **`update.sh` now notices when it has just updated itself** and re-execs the
updated script before deciding anything, rather than finishing on stale in-memory state — verified
against a live simulated future release: one `--apply` invocation, no manual re-run, reaches the
target version and delivers the new path. This protects every release from this one on.

**The "already up to date" shortcut is also gone** — it used to trust `_meta/VERSION == latest tag`
outright; now it always confirms against a real diff first. That mattered for a reason beyond this
release: without it, even `/perma-upgrade`'s own verification dry-run (added to Phase 5) would have
kept trusting the same lying string and reported nothing wrong.

**Honest limit, found by testing this exact upcoming transition, not assumed:** the bash-level fix
can't protect an install upgrading *from before this fix shipped* — that one upgrade runs the
*old*, unfixed script, which has no way to know to re-exec itself. Confirmed what actually happens
instead: `/perma-upgrade`'s verification pass correctly notices the new paths are missing (thanks
to the shortcut removal above), but then treats them as needing review, the same as a genuine
customization — a missing file and a deliberately-deleted one look structurally identical to a
per-file diff. So this specific transition surfaces one small, safe, one-time decision — "take
theirs" on 3 new files, via the existing negotiation flow — rather than either silently losing them
(the original bug) or silently completing (which isn't actually achievable here). Every release
after this one goes fully automatic, proven separately.

**The harness-binding mechanism is now real, not just designed — and Claude Code is part of it.**
`design/harness-binding-mechanism.md` originally decided Claude Code's wiring should stay a
permanent special case in `install.sh`, for real hardening-preservation reasons. That decision
was reopened and reversed on request: `install.sh` now reduces to one generic loop over
`runtime/bindings/<harness>/`, Claude Code included, no special case left. All four hardening
mechanisms (backup-before-edit, refuse-on-mismatched-marker, the cross-install scheduling guard,
honest failure reporting) moved with it, unchanged. `_perma_block_merge` was extracted into a new
sourced-only `runtime/lib/block-merge.sh` so both the migrated Claude Code binding and the
existing AGENTS.md writer (unmoved — confirmed generic, not Claude-Code-specific) share one copy.

**A real bug found live-testing this, not by reasoning:** `_perma_block_merge`'s "no existing
marker" branch silently never wrote `CLAUDE.md` on a genuinely fresh install (no prior file at
all) — the branch's own exit code was accidentally poisoned by a harmless `cat` on a nonexistent
file, which skipped the file rename via `&&`. Fixed with one `|| true`. A second, separate bug
surfaced the same way: `claude-code/detect`'s heuristic check (`~/.claude` exists, or `claude` is
on `PATH`) failed on every real CI runner, since neither is true this early in a fresh install —
`wire` itself is what creates `~/.claude`. Fixed by making `detect` unconditional, matching what
`design/harness-binding-mechanism.md` §2 already said about Claude Code: it's the one harness
every install already has, by construction, with nothing left to gate.

**New: Antigravity's binding, shipped for four of five questions.**
`runtime/bindings/antigravity/` wires the forcing read + passive orientation (one `PreInvocation`
hook carries both — no separate event exists or is needed) and the standing instruction (a
managed block in the global `~/.gemini/GEMINI.md`, via a new dedicated `gemini-md-block.md`
rather than reusing the generic AGENTS.md-tools block, whose "Tier 2, no forcing read" framing
doesn't match what Antigravity actually does). Verified live, end-to-end, not just with piped
JSON: wired for real on the machine that built it, then a real `agy --print` session's actual
reply demonstrably reflected the injected `[perma]` content. Command invocation (Skills) is
deliberately not built yet — the design doc's own research flagged it as needing one live-fire
test before its shape is committed to, and this pass didn't include that.

**CI**: a real, previously-silent gap fixed — the lint job's three checks (`bash -n`, an embedded
Python-heredoc compile check, ShellCheck) all matched `*.sh` only, so the new `detect`/`wire`
scripts (extensionless, like `.githooks/pre-commit`) were invisible to all three; confirmed by
deliberately breaking one locally and watching the old glob miss it. New coverage added to
`install-matrix`: the migrated Claude Code binding's actual content (not just file existence),
and a real failure-path test that temporarily breaks `claude-code/wire` and confirms
`INSTALL_FAILED` correctly reaches `install.sh`'s final line — using Claude Code's own real
binding as the mechanism's test case, exactly as the design doc intended once a synthetic
Gemini-CLI-shaped test case became unnecessary.

**New: Devin CLI's binding, shipped for four of five questions.** Real market numbers (Cursor $2B
ARR / 1M+ paying users, Copilot ~42% market share, Devin $492M ARR / 89% internal adoption at
Cognition itself) prompted a feasibility check on Devin specifically — its older reputation as
purely cloud-hosted turned out stale; Devin CLI runs locally with real shell access, and its hook
event names are the same ones Claude Code uses. That similarity was misleading in one important
way: a live test caught two of Devin's own bundled docs contradicting each other on whether
Claude Code's hooks get imported — one says yes, a more specific page's own import table lists
only rules/skills/commands-as-skills/MCP servers, no hooks. The live test sided with the second
page (no injected context, no `session-load.sh` marker file created). `runtime/bindings/devin/`
therefore ships its own translator hooks (`SessionStart` + `UserPromptSubmit`, wrapping
`session-start.sh`/`session-load.sh` output in Devin's own `hookSpecificOutput` JSON envelope),
not a reuse of Claude Code's. The standing instruction writes a dedicated global
`~/.config/devin/AGENTS.md` rather than relying solely on Devin's separate (real, but conditional
on Claude Code's binding also being present) pickup of `~/.claude/CLAUDE.md`. Verified live,
end-to-end: wired for real, then a real `devin -p` session's actual reply quoted the injected
`[perma]` content verbatim. Command invocation (Skills) deliberately not built yet — needs its
own live-fire test first, the same discipline Antigravity's Skills layer is held to.

**Gemini CLI's decline upgraded from a cost decision to a settled fact.** Google's own developer
blog confirms free/individual access to Gemini CLI ended 2026-06-18 — consumer, Pro, and Ultra
users are pointed at Antigravity CLI (the product already bound this session), enterprise access
is unaffected. `docs/TOOL-SUPPORT.md` and the design docs already reflected the practical
consequence (rejected server-side sign-in); this is the reason why, found afterward, not a
change in what was already documented.

**New: `design/claude-code-binding.md`**, written retrospectively so every binding — including
the original, most-hardened one that predates `design/` as a convention — is documented to the
same standard.

**New: Cursor's binding, shipped for four of five questions — the cleanest result of any binding
this session.** A docs-based worry started this one: Cursor's own hook documentation says
`beforeSubmitPrompt` (the closest analogue to every other binding's forcing-read hook) is
read-only, and a real community bug report claims the CLI omits it and others. Live testing
reversed the worry instead of confirming it: `sessionStart`'s context injection is real, and —
proven with a prompt that never mentioned Permanence at all — the agent spontaneously read the
real `PROJECT.md`/`LOG.md` content and reported it accurately, including noticing this very
binding's own code was still untracked in git, purely because the injected instruction told it
to. One hook, firing exactly once per session, answers both passive orientation and the forcing
read — simpler than every other binding built this session, not more complex. Command invocation
is fully shipped too: commands translate into `~/.cursor/skills/<name>/SKILL.md`, confirmed
invokable by literal `/name` syntax from a completely unrelated project — a real `/perma-help`
run executed its full actual logic (checked real scheduled tasks, read real registry data), not
just echoed text. The one real gap: no working global standing-instruction file was found for
Cursor despite three separate live attempts — a tested-away gap, not an unresearched one.

**Antigravity's command layer, closed out — all five binding-contract questions now answered.**
The live-fire test its design doc had flagged as the one remaining blocker finally ran: a real
test skill fired correctly both by description-matching *and* by literal `/name` syntax — the
bundled docs undersold this, describing only the former. `wire` now translates
`runtime/commands/*.md` into `~/.gemini/config/skills/<name>/SKILL.md`, confirmed via a real
`/perma-help` invocation that executed its full actual logic. Antigravity is now the second
binding (after Claude Code) with nothing left for the owner to carry by hand.

**Devin's command layer, closed out — all five binding-contract questions now answered.** A real
test skill fired correctly two ways from a completely unrelated scratch project: literal
`/perma-devin-test` syntax and a natural-language request matching its description. `~/.claude/skills/`
never covered Permanence's own commands, but `~/.config/devin/skills/<name>/SKILL.md` does —
confirmed via `devin skills list` showing the test skill tagged `[user,model]` immediately.
`wire` now translates `runtime/commands/*.md` there, reusing the same description-extraction
logic already shared with Cursor's and Antigravity's bindings. Verified via a real `/perma-help`
invocation that executed its full actual logic. Devin is now the third binding, after Claude Code
and Antigravity, with nothing left for the owner to carry.

**Cursor's standing-instruction question settled — a real, confirmed gap, not an open one.** A
disposable test stream and scratch project were registered temporarily (backed up and restored
afterward) to run the one test the design doc had flagged as still needed: does a material fact
mentioned mid-conversation get written back to the stream unprompted, purely because
`sessionStart`'s injected content told the model to at session start? It doesn't — the agent
acknowledged the fact in its reply but never touched `PROJECT.md` or `LOG.md`, confirmed by file
checksums before and after. Four separate tests now agree: three global-file locations that don't
exist, and a real write test that came back negative. `postToolUse` — already confirmed live to
inject context correctly — is the most promising untried fix, since it fires repeatedly rather
than once, but designing it is new work, not something this pass attempted.

No **Migration notes** — nothing in any existing stream changes shape; this is all machinery.

## [1.3.0] — `/perma-unregister`: completely remove a stream in one step

**New command.** `/perma-register` never had an inverse — removing a stream meant a manual
`git rm -r`, which only takes git-tracked files with it. Each stream's own `CONTENTS.md` is
derived and gitignored (regenerated by `generate-contents.sh` / `.githooks/post-commit`), so it
survives a plain `git rm` untouched, leaving an orphaned, near-empty folder behind — reported via
this project's own events outbox by a session that hit it directly.

`/perma-unregister <name-or-path>` does the full removal properly: confirms what's about to be
lost (folder contents, every matching `_meta/REGISTRY.md` row, and whether it's a `_meta/GROUPS.md`
member — asked about separately, since group membership has its own `left`-date lifecycle under
invariant 8 and should never be touched silently), checks for uncommitted work first, then
`rm -rf`s the folder (not `git rm`, specifically so the gitignored `CONTENTS.md` goes too),
removes the registry row(s), and commits both as one change. Wired into `/perma-help` and
README's command list.

No **Migration notes** — a new command, nothing existing changes shape.

## [1.2.2] — `templates/` is no longer mistaken for a project stream

**Fixed: `templates/` was being discovered as a stream.** Stream discovery is "every directory
containing a `PROJECT.md`", and one of the shipped skeletons was named exactly that — so every
pass that walks streams counted the template directory as a project, reporting its `YYYY-MM-DD`
placeholder as permanent staleness. Confirmed affected: `/perma-consolidate`, `/perma-list`,
`/perma-orchestrate`, `/perma-brief`, and `/perma-help`'s stream count (`runtime/perma-help.sh`'s
`find -name PROJECT.md`, which matches on path depth alone and carries no reference to
`templates/` by name — worth noting since a plan drafted for this fix initially missed it,
having only grepped for the string `templates/`).

The four discovered skeletons are now `templates/*.template.md`. Renamed with `git mv`, so their
history is intact. `perma-register` already looked for these "if present", so registration was
never at risk either way; its wording and README's file table now say `*.template.md` explicitly.
`programme-task-doc.md` is unchanged — it's copied by name and was never discoverable as a stream.

Deliberately not folded in: `templates/` still ships only four of `SPEC.md`'s six canonical
stream files — no `STRATEGY.md` or stream `README.md` skeleton, so a newly registered project
is missing both by default. Same directory, same underlying `axis` review finding (tracked
internally as F27) as the fix above, but a separate defect. Left open on purpose, not fixed here.

No **Migration notes** — machinery only; no existing stream's shape changes, and nothing under
`templates/` is ever a real user's own content.

## [1.2.1] — a marketing + fact-check pass over the docs

A blind review (fresh agent, no prior context) read README/QUICKSTART/SPEC as a cold prospect
would, then fact-checked every checkable claim against the actual source rather than the docs'
own word. The positioning held up; a handful of specific claims didn't.

- **Fixed the dead link on the docs' own key evidence.** README pointed to
  `example/.consolidation/REPORT-example.md` to back up its biggest caveat ("this is
  instruction-following, not a guarantee") — the file never shipped, though `.gitignore` already
  carried a rule promising it would. It now exists, grounded in the example streams already
  there (the bathroom LOG's deliberately-planted PROJECT-behind-LOG gap, Jamie's dated inference
  in the kitchen `PEOPLE.md`, and the kitchen `QUESTIONS.md` deadline that's since passed).
- **QUICKSTART now discloses what `install.sh` actually touches**: the global `~/.claude/CLAUDE.md`
  and `~/.config/agents/AGENTS.md` blocks, and the UserPromptSubmit hook — previously undisclosed,
  despite the safety engineering around them (backup before any in-place edit, refuse on a
  mismatched marker) being worth advertising, not hiding.
- **Fixed the backup section's central claim.** README/QUICKSTART called `make-backup.sh`'s output
  an "off-machine" backup; it writes to `~/Backups` on the same disk, and the script's own last
  line tells you to upload it yourself. Also documented the undisclosed `age` dependency and that
  a second blob it writes contains `~/.claude` credentials.
- **Fixed four checkable overclaims**, each previously wrong in a way a sceptical reader would
  catch in the first ten minutes: "you'll never be nagged twice" (nothing persists that state —
  it's once per session, not once ever), "before your first message lands" (contradicted the
  doc's own later, correct explanation of the UserPromptSubmit hook), the pre-commit guard
  "nudges" (it `exit 1`s and blocks the commit), and "the only thing that talks to a network is
  the optional nightly tidy" (`/perma-upgrade` fetches too, and the nightly is scheduled by
  default, not opt-in).
- **Brought SPEC.md's Claude Code binding up to date** — it omitted `session-load.sh` entirely,
  despite README calling it "the reliable trigger." Also repointed three dangling references
  (`_meta/generative-orchestration-pass.md`, a `_personal/` folder that never shipped, and
  `README → "Writing about people"`, a section that doesn't exist under that name) — including
  the one `.githooks/pre-commit` prints to a user whose commit was just rejected, at the exact
  moment they go looking for the rule it's citing.
- **Smaller fixes**: pluralized "Optional extra" → "Optional extras" and added the shutdown
  nudge, which shipped but was undocumented outside `install.sh`'s own output; added `session-load.sh`
  and the untracked `axis/` folder to README's file table; reconciled the install-time estimate
  (5 vs. 10 minutes) and the `QUESTIONS.md` close-marker format (`[CLOSED YYYY-MM-DD]` vs.
  `[CLOSED YYYY-MM-DD: answer]`) between README and QUICKSTART/SPEC; moved QUICKSTART's
  `rm -rf example/` from step 3 (before the example's exhibits are ever used) to the end, since
  step 3 was deleting reference material steps 5-6 still point at.

No **Migration notes** — docs and comment text only; no stream shape, invariant, or script
behavior changed.

## [1.2.0] — trim the optional extras; a real fix for how upgrades handle removed files

Two of the four "optional extras" are gone, for opposite-sounding but related reasons: neither
one actually served this tool's job of helping you and the AI pick up where you left off.

- **Removed `cogdebt-scan.sh`** (the weekly cognitive-debt check). It's a code-quality monitor,
  not a memory/continuity tool.
- **Removed semantic search (`/perma-search`)**. Its premise — grep misses paraphrases — is a
  human-search problem; an AI agent doesn't need a pre-built embedding index to notice two notes
  are related, it just reads the files and reasons. A bolted-on search layer was solving a
  problem an AI-native tool mostly doesn't have.
- **Programme groups stay, reframed.** Not removed — it has real, proven use and a clear,
  correctly-scoped persona once named properly: a tech lead's own Permanence, tracking a team's
  repos from one vantage point, without anyone else needing to run Permanence. Moved out of
  "Optional extras" in the docs (it never had a real install-time toggle the way events/search
  did, so it never belonged there) and into the base command description.

Removing two shipped features properly meant fixing how upgrades handle a file the template no
longer ships, which `update.sh` had never actually done:

- **Fixed: `update.sh` silently failed to remove a file the template deleted.** It only ever
  did `git checkout $TARGET -- $path`, which does nothing when `$path` no longer exists at
  `$TARGET` — so anyone who already had `cogdebt-scan.sh` or `runtime/search/` would have kept
  an orphaned copy forever after upgrading, with `/perma-upgrade` never mentioning it. A deleted
  path is now always removed on upgrade — customized or not, no negotiation. (Considered, and
  rejected: treating a customized deleted file as a negotiated conflict like a modified one.
  Conflict detection here is purely per-file with no concept of "feature," so a multi-release
  upgrade could surface several unrelated customized files as one flat, ungrouped list to
  reason about individually — tolerable for an ordinary modified file, not worth it for a file
  the template doesn't support at all anymore.) `install.sh` also now cleans up an orphaned
  `perma-cogdebt` scheduled job left by an earlier install, since nothing can reschedule it
  anymore.
- **Fixed the same class of gap in `migrate-from-brain.sh`**, which had no conflict detection at
  all — it wipes and replaces `runtime/`, `.githooks/`, `templates/`, and the root docs
  unconditionally, and its only safety check (no *uncommitted* changes) lets a committed
  customization sail straight through. It now backs up the old versions of those exact paths,
  unconditionally, every time, before replacing them — the standard, ordinary practice of
  keeping the previous version before installing a new one over it, not feature-specific
  detection. Verified against a real reproduction (a scratch install with a customized
  `cogdebt-scan.sh`), not just reasoning.

No **Migration notes** — nothing here changes a stream's shape; the file removal and scheduled-
job cleanup happen automatically as part of the mechanical apply, not as stream content to
migrate.

## [1.1.2] — a stale local tag could break `/perma-upgrade`'s fetch outright

**Fixed: `update.sh` could fail with a misleading "check the URL/access" error.** Its fetch step
pulled tags from the update source without `--force`. If a local tag ever collided by name with a
real release tag pointing at a different commit — the update source's history was ever rewritten
(rebase, `git filter-repo`, a force-pushed tag), or an install had tagged something locally before
ever pulling upstream's tags — the fetch failed outright, and the error message pointed at
network/access, not the real cause. `_machinery` is single-purpose (only ever used to check for
updates); nothing in an install relies on a *local* tag under one of these names, so its tags are
always authoritative here. `--force` on the tags fetch makes that fetch succeed the way it always
should have. Verified against a real reproduction: a scratch install with a deliberately
conflicting local tag now upgrades cleanly instead of failing.

No migration notes — this only changes how the fetch step behaves, not any file shape.

## [1.1.1] — catching up the docs `v1.1.0` left stale

Wording only — no behaviour change, no migration notes.

`v1.1.0` shipped name-based project resolution but left several docs describing only the
old cwd-only behavior:

- **README's "The loops" section and diagram** described only the Claude Code hook-based
  path (SessionStart/UserPromptSubmit), with no mention of the by-name alternative for
  hookless harnesses (desktop apps) that `v1.1.0` actually built. Added a paragraph
  explaining what happens instead when no hooks exist, pointing at QUICKSTART/TOOL-SUPPORT
  for detail. The diagram itself is unchanged and still accurate for the path it shows.
- **The `/perma-register` explanation** didn't mention name-only creation (picking and
  creating a real folder from just a name, with no path at all).
- **The command list** in "What's in here" was missing `/perma-list`.
- **The machine-generated pointer blocks** (`runtime/claude-md-block.md`,
  `runtime/agents-md-block.md`) — injected into `CLAUDE.md`/`AGENTS.md` for harnesses
  without a SessionStart hook — still only described cwd-based resolution. This was the
  most consequential gap: these are the literal instructions Claude Desktop/Cowork and
  Tier 2 tools receive, and neither ever mentioned the by-name path built specifically for
  a harness with no meaningful working directory. Both now say to ask for the project by
  name instead when there's nothing to resolve from cwd.

## [1.1.0] — projects by name, not just by folder

Desktop AI apps (Claude Desktop, ChatGPT Desktop, etc.) have no working-folder hook and no
way for Permanence to set one — that's host-app UI state, and there's no shared mechanism
across vendors for it. Until now, `/perma-startup` and `/perma-shutdown` only worked if the
app's folder happened to be pointed at the right project, which desktop-app users have no
natural reason to remember (unlike VS Code/CLI users, whose folder is already open for the
work itself) — and `/perma-register` still required *someone* to supply a real folder path,
which is a harder blocker for a non-technical user who has never had a reason to think about
folders, but can easily come up with a project name.

- **`/perma-startup <name-or-path>` and `/perma-shutdown <name-or-path>`** now take either a
  Permanence stream/project name *or* an absolute path, resolving straight to that stream
  instead of the current working directory — whichever one you remember. A new
  `runtime/resolve-path.sh` looks up a stream's registered real-world path (if any) for the
  "cross-check the real repo" step; a stream with no registered path just skips that step
  rather than failing.
- **`/perma-register` now works from a name alone, no path required.** Given a path (or a
  path that doesn't exist yet), it behaves as before — creating the folder if needed. Given
  just a name with nothing to point at (*"start a new project called kitchen renovation"*),
  it picks the real folder itself, under `~/Permanence Projects/`, and says where — so
  someone who's never thought about folders never has to. If the name already matches a
  registered stream, it refuses to create a duplicate and points at `/perma-startup <name>`
  instead, since that's a resume, not a new project.
- **Renamed `docs/OTHER-TOOLS.md` → `docs/TOOL-SUPPORT.md`** — the old name promised
  "something other than Claude Code" but the file opens by explaining Claude Code (Tier 1)
  as the baseline, and now covers Claude Desktop too, which isn't cleanly "other than"
  either (its Code tab *is* Claude Code). The new name matches what the file actually is: a
  tool-by-tool support matrix, Claude Code included.
- **`docs/TOOL-SUPPORT.md` now covers Claude Desktop specifically**, for whoever
  configures the machine. Claude Desktop has three tabs, not one plain chat surface — the
  Code tab is Claude Code itself (already fully supported, nothing to grant); Cowork has
  real file access but needs explicit `git`/`mkdir` execution permission granted, the same
  baseline a CLI developer already has; the Chat tab has no persistent file/shell access and
  isn't supported. README's tool-support line points here.
- **The resolved stream is now the active stream for the rest of the conversation** —
  every standing "update the stream when something shifts" write targets it. Switching to a
  different project mid-session (via `/perma-startup <other-name>`) checks first whether the
  one being left has anything undiscussed-in-its-files, and asks before switching rather than
  silently dropping it.
- **New `/perma-list`** — a read-only index of every registered stream (name, what it is,
  when it last moved, its path if any), so a project can be named correctly on the first try
  instead of guessed. Listed in `/perma-help`'s "Finding and talking" section.
- **Fixed: invalid frontmatter YAML in five command files.** A `description:` value
  containing a bare `word:` (colon, then a space) elsewhere in the sentence (`Trigger
  phrases:`, `Pub/sub:`) isn't valid as an unquoted YAML plain scalar — any strict YAML reader (a code editor's
  markdown preview, for one) fails to parse it. Found while adding `perma-list.md`'s own
  frontmatter and confirmed pre-existing in `perma-emit.md` and `perma-help.md`, unrelated
  to this release otherwise. Fixed by YAML-quoting the five affected `description:` values
  (`perma-startup.md`, `perma-shutdown.md`, `perma-list.md`, `perma-emit.md`,
  `perma-help.md`) and teaching `runtime/perma-help.sh`'s plain-text extraction to unwrap
  that one layer of quoting, so `/perma-help`'s own output is unaffected either way.
- **Fixed: `/perma-register` could silently merge two unrelated projects into one stream.**
  Step 3 only checked whether the *path* being registered already existed in
  `_meta/REGISTRY.md` — it never checked whether the proposed *stream name* was already in
  use by a different path. Register project A as `home/kitchen`, then register an unrelated
  project B under the same name, and step 4 would write straight into A's existing
  `PROJECT.md`/`LOG.md`, merging their notes. Found while testing this release's name-based
  lookup, which makes a collision more likely to actually bite (picking a stream by name
  instead of always landing on the right one via cwd). Fixed: step 3 now also refuses and
  asks for a different name if the target stream folder already exists for a different path.

A project registered once is reachable either way from now on — open its folder in VS Code,
or say its name in a desktop app — no per-app setup needed.

No migration notes: purely additive, nothing about existing streams' shape changes, and
cwd-based resolution (VS Code/CLI) behaves exactly as before.

## [1.0.10] — backup is loud now, and registration matches how people actually work

Wording only — no behaviour change, no migration notes.

The local-only, no-automated-backup nature of Permanence was true from the start (see
SPEC.md invariant 7) but easy to miss in the two places people actually read first:

- **README.md** now says it plainly, right next to the `.git` re-init step: nothing
  is backed up unless `runtime/make-backup.sh` is run, there's no remote, and losing
  the machine loses everything if that's the only copy.
- **QUICKSTART.md** gives backup its own early numbered step (right after putting
  Permanence at `~/permanence`), instead of burying it as the last item in a long
  "Optional —" list near the bottom, where someone would only find it after already
  accumulating notes worth losing.

QUICKSTART.md's registration step (previously "4. Set the session's working folder —
then register" / "4b. Register your first project") assumed one specific UI — a
"folder chip in the composer" — that doesn't describe how VS Code or Claude Code CLI
users work (their working directory already is the project) and doesn't map cleanly
onto other desktop apps either. It's now split by actual audience: VS Code/CLI users
need no special step at all, and desktop-app users (Claude Desktop, ChatGPT Desktop,
etc.) are told to just say the project's explicit path when registering — leaning on
`/perma-register`'s existing explicit-path argument, which already supported this and
needed no code change. The container-folder-refusal and "deleting a session is safe"
guidance is kept, reframed as universal rather than tied to one app's UI terminology.

## [1.0.9] — the origin story starts at the actual origin

Wording only — no behaviour change, no migration notes.

The "Why 'Permanence'" section previously opened at "object permanence" as if that
were the tool's first name. It wasn't: this started life as **the brain** — the
author's own daily-driver, in use and shared with colleagues for months before any
of it was public — and only took the "object permanence" name (then Permanence)
during the 2026-08-29 rebrand. The section now says so, and names the GitHub
repo's own brief detour through `object-permanence` as exactly that: a few-day,
repo-naming-only choice that never touched the install folder or product name,
confirmed by checking `migrate-from-brain.sh`'s own header — it was always written
to migrate `brain` → `permanence` directly, never via `object-permanence`, because
nothing structural changed in that window. No new migration script needed as a
result; the existing brain-migration path already covers the real case.

## [1.0.8] — README opening, revisited

Wording only — no behaviour change, no migration notes.

Added a one-line tagline right after the title, naming what the tool is before the
problem narrative makes the case for it (matching the pattern `axis-engineering`'s
README already uses). Broadened the opening problem paragraph: it previously framed
the whole problem as the AI's amnesia; it now also names that the owner forgets too
across several fast-moving projects, and that nothing previously handed the same
picture back to *them*, not just to the AI. "Is the fix" now says "both you and the
AI" instead of burying that in a parenthetical.

## [1.0.7] — the repo is renamed to `permanence`

Wording and repo-identity only — no behaviour change, no migration notes.

`object-permanence` was itself a rename, made in a hurry to stop the repo name,
the `~/permanence` install folder, and the product name all colliding. On
reflection it solved a problem that didn't need solving that way: the repo,
the install folder, and the product are now all simply **Permanence** —
matching what `~/permanence`, `/perma-*`, and the running instance were
already called throughout every doc. The "Why 'Object Permanence'" section
becomes the origin story instead of the current name: the phrase is where the
name came from (the ADHD-community term for the failure mode this tool
exists to fix), not what the tool is called today.

The two README/QUICKSTART bullets explaining why the repo name differed from
the install path are removed — that confusion no longer exists now that
`git clone .../permanence.git` lands in a folder that's already correctly
named. `runtime/.update-source` now points at the new repo URL.

Historical records are untouched on purpose: past CHANGELOG entries and the
`axis/runs/2026-08-30-object-permanence-two-pass/` and
`axis/runs/2026-08-31-object-permanence-deep-review/` folders correctly keep
the old name — that's what the repo was actually called when those releases
shipped and those reviews ran, and rewriting them would falsify the record.

GitHub redirects the old `object-permanence` URL automatically, so existing
clones and links keep working.

## [1.0.6] — fixes from a second independent Axis Engineering review

Google Antigravity ran its own Two-Pass Axis Engineering review of this repo — the
same methodology and protocol as the `v1.0.3` review, independently applied by a
different tool — and shared seven findings. The run is documented at
`axis/runs/2026-08-31-object-permanence-deep-review/`. Each finding was
independently re-verified against the actual code before anything was changed
here; six were real and are fixed (one, on inspection, turned out to already be
fixed in `stop-listen.sh` — only `events-listen.sh` had the gap). No migration
notes — bug fixes only, no change to the data model or canonical file shapes.

- **`cogdebt-scan.sh`** crashed with an unhandled Python `ValueError` when scanning
  a repository with zero `.py` files (true for several genuinely-watchable repos,
  including this one). Now defaults cleanly to an empty report instead.
- **`nightly-consolidate.sh`**'s `--allowedTools` grant hardcoded `$HOME/permanence`
  instead of the `$PERMA` variable that actually respects `PERMA_DIR` — a custom
  install location got permission-denied on every unattended run. This was a gap
  in my own `v1.0.3` fix, which copied a pre-existing pattern without checking it.
- **`update.sh`**'s remote setup (`get-url && set-url || add`) could fall through
  to `add` — which then fails, "remote already exists" — whenever the remote
  existed but `set-url` failed for an external reason. Now an explicit `if/else`.
- **`generate-contents.sh`** word-split on any space in a stream directory name via
  an unquoted `for d in $(...)`. Now piped into a `while read` loop, matching the
  same fix already applied to `.githooks/post-commit` in `v1.0.3`.
- **CI's redaction scan** passed an unquoted file list to `grep`, with the same
  space-splitting exposure. Now null-delimited via `git ls-files -z | xargs -0`.
- **`events-listen.sh`** advanced its delivery cursor *before* confirming the
  message was actually parsed and surfaced — a crash between those two steps
  silently dropped that cross-project event forever. Now advances only after
  the parse succeeds; `stop-listen.sh` already had the correct order.

## [1.0.5] — README polish

Wording and structure only — no behaviour change, no migration notes.

- Dropped the "— a starter" subtitle.
- Added an attribution/license line under the title.
- Added a concrete before/after example right under the pitch, showing what
  opening a session looks like without this tool versus with it.
- Added a small diagram to "The loops" showing the SessionStart →
  UserPromptSubmit → read → (material shift) → write cycle.
- Added a "Why 'Object Permanence'" section — the ADHD-community origin of
  the name, and the author's own reason for building it, matching what
  axis-engineering's README already says about him.

## [1.0.4] — the product is named Object Permanence

Wording only — no behaviour change, no migration notes. Titles, the README's
opening pitch, and mentions of pulling a machinery release now say **Object
Permanence** — the actual product name, matching the repo. Everywhere else
(operational text: "your Permanence", "at `~/permanence`", "Permanence reads
your project context", trigger phrases like "good night Permanence") still
says **Permanence** on purpose — that's the data store itself, a different
thing from the product, and the shorter word is what you'd actually type or
say to it day to day.

## [1.0.3] — fixes from an Axis Engineering Two-Pass review

A Two-Pass review (`axis/runs/2026-08-30-object-permanence-two-pass/`) found 29
issues in the machinery; this release fixes everything through P2 (19 of them).
No migration notes — nothing here requires a stream to change shape, and every
fix degrades safely for an already-configured install (see the review's own
synthesis for exactly what changed and why).

**P0 — data loss / scope escapes:**
- `install.sh` and `migrate-from-brain.sh` could silently delete everything
  after a `<!-- perma:begin -->` marker in `~/.claude/CLAUDE.md` or a global
  `AGENTS.md` file if the matching end marker was missing or malformed, with
  no backup. Both now verify the marker pair before touching the file, and
  back up first.
- The unattended nightly consolidate held an unscoped `Write` tool despite
  `SPEC.md` documenting the pass as read-only. Scoped to `.consolidation/*`.
- `make-backup.sh` could report a verified success while silently omitting
  uncommitted notes, then prune the previous (actually complete) backup. It
  now checks the tree is clean first, says so loudly if not, and skips
  pruning on an incomplete run.

**P1:**
- `install.sh` could report `done.` after a real failure (an unparseable
  `settings.json`, a failed command copy) — now tracks and reports failures.
- `migrate-from-brain.sh`'s machinery refresh could delete uncommitted local
  edits with no warning — now requires a clean tree first.
- A stale `.perma-lock` (left behind by a crashed review) silently disabled
  the nightly job forever — now ages out with a loud alert past 4 hours.
- `update.sh`'s conflict detection matched by directory prefix, so one
  customized file under `runtime/` excluded the *entire* directory — ~20
  scripts — from an upgrade, and could bump `_meta/VERSION` anyway, hiding
  the gap from every future run. Now matches per file, and only advances
  `VERSION` when nothing was left conflicted. Also fixed a real bash-3.2
  (macOS's `/bin/bash`) crash on an all-conflicted upgrade.
- `_meta/REGISTRY.md` rows with a trailing slash matched nothing; rows
  missing a leading `|` were silently dropped. `resolve-stream.sh` now
  normalizes trailing slashes and validates row shape; `session-start.sh`'s
  own duplicate copy of this parser is gone — it calls the shared script.
- A space in `$HOME` (e.g. `/Users/Anna Smith`) broke every scheduled job
  silently — the generated command re-parses as a second shell command line
  when the job fires, and an unquoted path there word-splits on the space.

**P2:**
- `session-start.sh` and `session-load.sh` resolved "the current workspace"
  two different ways and could disagree under a symlink — both now read the
  same hook-provided `cwd`.
- The pre-commit people-rule guard exempted *every* `README.md`, including a
  stream's own (a canonical file that can hold real content about real
  people) — narrowed to just this repo's own top-level README. A git-quoted
  path header (non-ASCII filenames) silently skipped the whole file — now
  handled. Three benign false positives narrowed.
- `generate-contents.sh` used BSD-only `stat -f`, breaking silently on
  Linux — now tries BSD then GNU.
- The generated launchd plist embedded the scheduled command unescaped;
  `plutil -lint` rejected it. Now XML-escaped.
- `session-load.sh` never set its once-per-session marker without `python3`,
  so the auto-load text repeated on every prompt instead of just the first.
  Now has a non-Python fallback.
- A filename with a space broke `post-commit`'s search-index update via a
  bare `xargs` — now null-delimited throughout.
- The cognitive-debt scan shipped scheduled weekly by default against a
  placeholder watch-list, contradicting its own "opt-in" docs, and could
  silently misreport (or emit false breach events) if pointed at something
  real but non-Python. Now refuses to run unconfigured, and `install.sh`
  only schedules it once it's actually set up. Also fixed an unescaped-JSON
  embedding that let a hostile git commit author name run arbitrary Python
  inside the scan.
- `make-backup.sh` — the only implementation of the custody invariant — was
  referenced by nothing in the documented setup flow; added to QUICKSTART.
- `SPEC.md`'s invariant 5 claimed lock-fencing and worktree-isolation as
  mechanical guarantees; they are conventions the model follows via prompted
  steps, not code that enforces them. Reworded to say so.

**Deliberately not done in this release:** F20 (stream discovery is
implemented three slightly different ways across `perma-help.sh`,
`perma-brief.md`, and `generate-contents.sh`) needs an actual design
decision on the one shared definition, not a mechanical fix — left for a
follow-up.

## [1.0.2] — scheduled tasks can't be hijacked by a second install

Both changes are in `runtime/schedule-task.sh`. No migration notes; existing
installs keep their scheduled jobs exactly as they are.

- **Ownership guard.** A scheduled task's identifier is built from the task name
  and your username, not the install path — deliberately, because one Permanence
  per machine is the intended model and a stable identifier is what makes a
  re-install replace its own job instead of piling up duplicates. The cost was
  that a *second* Permanence on the same machine (most often a test install)
  silently took over the first one's job and repointed it at the wrong directory,
  printing nothing to say so. `schedule_task` and `unschedule_task` now check
  which Permanence an existing job actually runs from and leave it alone if it
  belongs to a different one, explaining what they found and why they stopped.
  Re-installing over your own job is unchanged.
- **Scheduling now says where the job will run from.** The success line named the
  task but not the directory, so a takeover would have been invisible even to
  someone reading the output closely.

## [1.0.1] — installable from GitHub

Documentation and one bug fix. No change to how the machinery behaves, and nothing
for existing streams to adapt to.

- **README**: an install section near the top, with the real clone URL. Two routes —
  hand your AI the repo URL and one instruction, or run three commands yourself.
  Previously the only onboarding note assumed you had been sent a zip, so someone
  finding the repo on GitHub had no stated way in.
- **README + QUICKSTART**: say plainly that the repo is named `object-permanence`
  while the install directory is `~/permanence`, so the clone command names its
  target explicitly instead of landing in the wrong folder. Explain why `.git` is
  discarded and re-initialised, and note that `/perma-upgrade` still works
  afterwards because the upstream URL lives in `runtime/.update-source`.
- **QUICKSTART**: replaced the unusable `git clone <your fork>` placeholder.
- **Install**: both documented paths now make an initial commit. Without one,
  `install.sh` stamped every command `unversioned` and the git hooks never armed.
- **Fix** (`runtime/install.sh`): the fallback printed when `python3` is missing
  hardcoded `$HOME/permanence` in its settings snippet, ignoring `PERMA_DIR`, while
  the main path honoured it.

## [1.0.0] — first public release

Baseline: streams (`PROJECT`/`LOG`/`PEOPLE`/`QUESTIONS`), the four conventions,
`/perma-*` commands, `/perma-upgrade`, opt-in events/search/cognitive-debt-scan,
programme groups. No migration notes — this is the starting point.
