# Design — a Cursor binding for Permanence

> Status: **built and shipped, four of five — the standing instruction is a confirmed, permanent
> gap, not an open question.** `runtime/bindings/cursor/` implements passive orientation + the
> forcing read (one `sessionStart` hook, per §2) and command invocation (Skills) — both live-fire
> tested end-to-end against the real installed product, including a real `/perma-help` invocation
> that executed its full logic correctly. One finding reversed an initial, docs-based worry; the
> standing instruction was tested four separate ways (three file locations, plus a real mid-session
> write test 2026-09-14) and failed all four — see §5.
> Written 2026-09-14. See [harness-binding-mechanism.md](./harness-binding-mechanism.md) for the
> `detect`/`wire` interface this implements rather than re-deriving.

**Owner carries: the standing instruction, confirmed, not just suspected.** Four of five
binding-contract questions are shipped and live-fire tested — `sessionStart` answering passive
orientation *and* the forcing read at once, simpler than every other binding built so far, not
more complex, and command invocation confirmed via a real `/perma-help` run that executed its
actual logic (checked scheduled tasks, read real registry data) rather than just echoing text.
**A real mid-session test settled the standing-instruction question with a clean negative**: a
material fact mentioned mid-conversation was acknowledged in the reply but never written back to
the stream, unprompted — see §5.

## 1. Why

Cursor came up in the same numbers check that led to Devin: $2B ARR, 1M+ paying users, 64% of
Fortune 500 — the clearest remaining reach candidate after Claude Code, Antigravity, and Devin.
Docs research surfaced a real worry before any code was written: Cursor's hook documentation
states plainly that `beforeSubmitPrompt` (the closest analogue to Claude Code's `UserPromptSubmit`,
the hook every other binding's forcing read depends on) is **read-only — it cannot inject context
or communicate back**, and a real bug report on Cursor's own community forum claims the CLI
specifically omits that hook and others. That combination looked like a genuine capability gap,
not just an unresearched one, so live testing started from a position of real doubt rather than
confidence — worth stating plainly, since the doubt turned out to be resolved in Cursor's favor,
not confirmed.

## 2. What's verified, and against what

**No bundled docs ship with this CLI** (unlike Devin's `.mdx` files) — it's a compiled Node.js
package. Primary source: the public docs at `cursor.com/docs/hooks` and
`cursor.com/help/customization/skills`, cross-checked against live behavior on every claim that
mattered, the same discipline as the other three bindings.

**Hooks (`hooks.json`) — location and schema confirmed against docs, injection behavior confirmed
live:**

- Global: `~/.cursor/hooks.json` (scripts conventionally in `~/.cursor/hooks/`). Project-level:
  `<project>/.cursor/hooks.json`. Enterprise/team locations exist but don't apply here. Priority:
  Enterprise → Team → Project → User.
- Schema: `{"version": 1, "hooks": {"eventName": [{"command": ..., "type": "command", "timeout":
  ..., "matcher": ...}]}}`.
- **`sessionStart` fires once per session and its `additional_context` output is real and
  live-confirmed** — a scratch-project test (`additional_context: "Always end your reply with the
  word BANANA51"`) produced a reply ending in "BANANA51."
- **The decisive test, not just a word-injection check**: wired `session-start.sh`'s own real
  output into `sessionStart`, globally, then asked the agent — from a fresh session, in the
  actual Permanence repo, with a prompt that never mentioned Permanence at all ("What's the
  current state of this project? Give me a brief summary.") — and the agent **spontaneously read
  the real `PROJECT.md`/`LOG.md` content and reported it accurately** (PR #13's status, PR #11
  still unmerged, the `templates/` gap), purely because the injected instruction told it to. This
  is genuine forcing-read behavior, not passive context the model might ignore — reversing the
  docs-based worry from §1. Per `SPEC.md` §3's "forcing subsumes passive," `sessionStart` alone
  plausibly answers both question 1 and question 2, and no second hook was needed to prove it.
- `postToolUse` **also** genuinely injects `additional_context`, confirmed live (a
  read-a-file-then-summarize prompt reliably ended in an injected word) — a viable secondary
  reinforcement mechanism if `sessionStart` alone ever proves insufficient in practice, but not
  required by anything confirmed so far.
- `beforeSubmitPrompt` **confirmed via docs to be genuinely read-only** (`continue` boolean only,
  no context field) — not live-tested further since it turned out unnecessary, not because the
  docs claim went unchecked.

**Skills (`~/.cursor/skills/<name>/SKILL.md`) — the command-invocation question, live-confirmed,
including literal slash syntax:**

- Real global path confirmed by inspecting the fresh install: a separate, reserved
  `~/.cursor/skills-cursor/` ships Cursor's own built-in skills (same YAML-frontmatter
  `SKILL.md` format — `name`, `description`, an optional `disable-model-invocation` flag);
  `~/.cursor/skills/<name>/SKILL.md` is the real, confirmed path for a user's own. `~/.agents/skills/`
  also exists as a documented cross-tool global alternative, not yet tested.
- **A real test skill, placed at the global path, was invoked with literal `/perma-test` syntax
  from a completely unrelated scratch project** and correctly fired — proving both the mechanism
  and that it's genuinely global, not scoped to one repo. This is a cleaner result than either
  Antigravity's (description-matched only, no confirmed literal syntax) or Devin's (not yet
  live-fired) command-invocation findings.

**Standing instruction — the one real, surviving gap:**

- Docs describe project-level rules (`<project>/.cursor/rules/*.mdc`, or `AGENTS.md` in a
  project) but state "User Rules are global preferences defined in Customize → Rules" with **no
  file path given** — strongly suggesting they're account-synced, not a local file at all.
- **Three plausible global-file candidates were tested live and none worked**: `~/.agents/rules/*.md`
  (the cross-tool convention Antigravity's own docs also named as a candidate), `~/.cursor/AGENTS.md`,
  and `~/.config/agents/AGENTS.md` (the path Permanence's own existing generic `AGENTS.md` writer
  already targets, for the "emerging unifying standard"). None of the three caused an injected
  test string to appear in a reply. This is a real, tested-away gap, not an unresearched one.
- **The mid-session write test, run 2026-09-14 — a clean negative, not a maybe.** A disposable
  test stream and a scratch project were registered temporarily (backed up and restored
  afterward). `session-start.sh`'s own output — which already carries the standing-rule
  instruction ("Update it whenever something material shifts... without being asked") — was wired
  in for real. A fresh session's very first turn mentioned a genuinely material fact ("we've
  decided to deprecate the old export-to-CSV feature entirely") without asking Permanence to be
  updated. The agent acknowledged the fact in its reply ("Noted on the CSV export deprecation")
  but never touched `PROJECT.md` or `LOG.md` — confirmed by file checksums before and after,
  unchanged. `sessionStart`'s content is genuinely read and acted on for orientation (§2), but not
  for the ongoing write side, at least not on the freshest possible turn, when the injected
  instruction is closest in context and easiest to act on. This settles the question rather than
  leaving it open: the standing instruction is a real, permanent gap for Cursor as currently
  bound, not an untested maybe.

**Headless invocation — confirmed:**

- `agent -p`/`--print` runs non-interactively. `--trust` is needed to skip the interactive
  workspace-trust prompt, which print mode can't display.

## 3. Trigger mapping — the five binding-contract questions

Per `SPEC.md` §3's binding contract, independent questions, not a ladder.

1. **Passive orientation.** Answered by `sessionStart`, alongside question 2 — see below.
2. **Forcing read. Live-confirmed, decisively** (§2) — the one finding that reverses this
   binding's original docs-based worry. `sessionStart` alone demonstrably causes unprompted,
   accurate action on real Permanence content, not just passive availability.
3. **Standing instruction. A confirmed gap, not an unknown.** No working global rules file was
   found despite three real attempts, and a real mid-session write test came back negative too —
   a material fact was acknowledged in conversation but never written back, unprompted (§2). Four
   separate tests, four negatives. See §5.
4. **Command invocation. Live-confirmed**, including literal `/name` syntax from a genuinely
   global path (§2) — the cleanest result of any binding built this session.
5. **Headless invocation. Confirmed** (§2), needing `--trust` for non-interactive use.

Material-shift is what (2) and (3) produce together, not a sixth question — see `SPEC.md` §3.

## 4. Shape — as actually shipped

The `detect`/`wire` interface is specified once in
[`harness-binding-mechanism.md`](./harness-binding-mechanism.md) — not restated here.

```
runtime/bindings/cursor/
  detect                 # exit 0 iff `cursor-agent` (the specific binary name, not the generic
                          # `agent` symlink it also installs) is on PATH
  wire                   # merges a sessionStart hook into the GLOBAL ~/.cursor/hooks.json
                          # "hooks" object — NOT the project-level .cursor/hooks.json, which
                          # would violate invariant 1 if written into an open repo. No second
                          # hook wired — the standing-instruction gap is real and confirmed
                          # (§3.3), and a postToolUse-based fix for it is still just a candidate,
                          # not yet designed (§5 item 1).
                          # Command invocation: translates runtime/commands/*.md into the global
                          # ~/.cursor/skills/<name>/SKILL.md, reusing each command's own existing
                          # `description:` frontmatter field directly rather than re-deriving it
                          # (one file, perma-contents.md, has none — falls back to its first
                          # heading).
  session-start-hook.sh  # translator: reads workspace_roots off stdin, calls session-start.sh
                          # with a translated {"cwd": ...} payload, wraps its output as
                          # {"additional_context": <that output>}
```

Live-fire verified end-to-end, not just dry I/O: wired for real on this machine, then a real
`agent -p` session (a prompt that never mentioned Permanence) spontaneously read and accurately
reported real stream content — including noticing this very binding's own code was still
untracked in git — and a real `/perma-help` invocation executed its full logic correctly
(checked actual scheduled tasks, read real registry data).

Unlike Antigravity's and Devin's bindings, this one has **no once-per-conversation cursor
file** — `sessionStart` fires exactly once per session by its own nature, unlike Antigravity's
`PreInvocation` (fires multiple times per turn) or the general pattern the other two bindings
had to guard against.

## 5. Still open — none of these block anything shipped

1. **A real fix for the standing-instruction gap** — confirmed real and permanent (§2, §3.3),
   not yet solved. `postToolUse` — confirmed live to genuinely inject `additional_context` (§2) —
   is the most promising untried mechanism: since it fires after every tool call, wiring it to
   periodically re-inject the standing-rule reminder (rather than relying on one injection at
   session start that fades from context) might succeed where `sessionStart` alone didn't. Not
   attempted yet — a real design decision (how often, what content) is needed first, not just a
   quick test.
2. **Whether `~/.agents/skills/` (the documented cross-tool alternative global skills path) is
   worth using instead of or alongside `~/.cursor/skills/`** — only the Cursor-specific path was
   live-tested and shipped.
3. **Whether `workspace_roots` is genuinely present on `sessionStart`'s own real stdin payload**,
   not just the generic "every hook receives" list — the live end-to-end test (§4) succeeded, but
   couldn't distinguish between the real payload carrying it and the hook's own `$PWD` fallback
   silently doing the work instead, since both would resolve to the same directory in that test.
   Worth confirming precisely (e.g. logging the raw stdin during a real session) before relying on
   it for a workspace that differs from the hook subprocess's own working directory.

Retired by live testing, no longer open: whether `sessionStart` alone answers the forcing read;
whether the standing instruction might turn out free the same surprising way the forcing read
did — tested directly, it doesn't (§2, §3.3).

## 6. Non-goals

- Not building a `postToolUse` or `beforeSubmitPrompt`-based mechanism for the *forcing-read*
  question — confirmed unnecessary (the former) or genuinely incapable (the latter) there, since
  `sessionStart` alone already answers it. `postToolUse` remains a live candidate for the
  *standing-instruction* question specifically (§5 item 1) — a different job.
- Not treating the standing-instruction gap as merely unresearched — a real mid-session test ran
  and came back negative (§2, §3.3). It's a confirmed limitation of the shipped binding, not an
  open question waiting on more investigation.
