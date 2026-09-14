# Design — a Cursor binding for Permanence

> Status: **built and shipped, four of five — the standing instruction is a confirmed, likely
> structural limitation, not an open question.** `runtime/bindings/cursor/` implements passive
> orientation + the forcing read (one `sessionStart` hook, per §2) and command invocation
> (Skills) — both live-fire tested end-to-end against the real installed product, including a real
> `/perma-help` invocation that executed its full logic correctly. One finding reversed an initial,
> docs-based worry; the standing instruction was tested **seven** separate ways across two rounds
> (three file locations, a real mid-session write test, a much stronger imperative wording, the
> `stop` hook, and `postToolUse` reinforcement) and failed all seven — see §5.
> Written 2026-09-14, extended the same day after a second round of live testing. See
> [harness-binding-mechanism.md](./harness-binding-mechanism.md) for the `detect`/`wire` interface
> this implements rather than re-deriving.

**Owner carries: the standing instruction, confirmed across seven real tests, not just
suspected.** Four of five binding-contract questions are shipped and live-fire tested —
`sessionStart` answering passive orientation *and* the forcing read at once, simpler than every
other binding built so far, not more complex, and command invocation confirmed via a real
`/perma-help` run that executed its actual logic (checked scheduled tasks, read real registry
data) rather than just echoing text. **Every mechanism tried for the write side came back
negative, consistently**: a material fact mentioned mid-conversation is reliably acknowledged in
the reply but never written back to the stream, unprompted — true whether the instruction is
worded normally, worded as a forceful imperative, or repeated after every tool call. See §5.

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
  read-a-file-then-summarize prompt reliably ended in an injected word) — reliably steers replies,
  but tested later as a reinforcement mechanism for the standing instruction specifically and
  found *not* to help there either (§3.3) — the injection mechanism works, it just doesn't solve
  this particular problem.
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
  unchanged.
- **Second round, same day: three more mechanisms tried, three more negatives, applying Seesaw
  first (is this my content's fault, or the platform's?) before building anything new.**
  - **A much stronger, imperative wording** ("you MUST update... before you finish replying... Do
    not just acknowledge it") prepended ahead of the real orientation content — same result,
    unchanged files. This rules out weak wording as the cause: it's not that the instruction was
    too soft, since a maximally direct version failed identically.
  - **The `stop` hook** (fires when the agent is about to end its turn; can return
    `followup_message` to auto-submit an additional turn) looked like the most targeted candidate
    — a forced extra turn dedicated to "check and update," not a hope that a buried instruction
    gets noticed. **It never fired at all in headless (`-p`) mode** — confirmed directly with a
    debug-instrumented hook that logs to a file on every invocation: zero log entries across a
    real test run. This matches a real bug report found during initial research (§1) claiming the
    CLI omits `stop` and other hooks. Genuinely untested: whether `stop` fires in *interactive*
    use, which this sandboxed environment has no way to test (no real terminal available) — this
    finding is specific to headless mode, not a claim about Cursor generally.
  - **`postToolUse` reinforcement** — wired alongside `sessionStart`, injecting the same
    "check and update" reminder after every tool call within the turn, confirmed to actually fire
    (§2 above already proved `postToolUse` injects correctly). Same result again: the fact was
    acknowledged conversationally, files unchanged.
  - **What this pattern means**: `sessionStart`- and `postToolUse`-injected `additional_context`
    consistently and reliably shapes what the model *says* — every single test's reply correctly
    referenced the material fact — but never once caused it to *act* by running a write command
    unprompted, across three different content strategies and two different injection points.
    That consistency across genuinely different approaches is itself the finding: this reads as a
    structural property of how Cursor's agent decides when to use tools on its own initiative, not
    a fixable wording or placement problem on Permanence's side.

**Headless invocation — confirmed:**

- `agent -p`/`--print` runs non-interactively. `--trust` is needed to skip the interactive
  workspace-trust prompt, which print mode can't display.

## 3. Trigger mapping — the five binding-contract questions

Per `SPEC.md` §3's binding contract, independent questions, not a ladder.

1. **Passive orientation.** Answered by `sessionStart`, alongside question 2 — see below.
2. **Forcing read. Live-confirmed, decisively** (§2) — the one finding that reverses this
   binding's original docs-based worry. `sessionStart` alone demonstrably causes unprompted,
   accurate action on real Permanence content, not just passive availability.
3. **Standing instruction. A confirmed, likely structural limitation, not an unknown.** No working
   global rules file was found despite three real attempts, and four separate write-side
   mechanisms all came back negative too — normal wording, a forceful imperative wording, the
   `stop` hook (which turned out not to fire headlessly at all), and `postToolUse` reinforcement
   (§2). Seven tests, seven negatives, consistent enough to read as a real property of how
   Cursor's agent decides when to act versus merely acknowledge. See §5.
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
                          # hook wired — seven attempts at the standing-instruction gap all came
                          # back negative (§3.3), including postToolUse reinforcement, so there's
                          # currently no known mechanism left to wire for it (§5 item 1).
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

1. **A real fix for the standing-instruction gap** — still unsolved after seven real attempts
   (§2, §3.3). What's left, roughly in order of promise:
   - **`stop` in genuinely interactive use** — confirmed dead in headless `-p` mode, but never
     tested interactively, since this sandboxed environment has no real terminal. If it fires
     interactively, `followup_message` is still the most structurally direct mechanism tried (a
     forced extra turn, not a hope that injected context gets acted on) — worth a real terminal
     test before ruling it out entirely.
   - **A tool-based approach instead of context injection** — every test so far relied on
     `additional_context`, which reliably shapes replies but never once triggered unprompted tool
     use. `preToolUse`'s `updated_input` (rewriting a tool call's arguments before it runs) or
     `PermissionRequest`'s auto-approve mechanism weren't tried — genuinely different levers from
     "inject text and hope," not yet explored.
   - Otherwise, this may be a real, permanent limitation for Cursor's `additional_context`
     mechanism specifically, not a solvable wiring problem — worth accepting as documented rather
     than continuing to try wording variations, since three different ones already failed
     identically.
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
did — tested directly, it doesn't (§2, §3.3); whether weak wording, `stop`, or `postToolUse`
reinforcement fix the write side — all three tried and all three failed (§2, §3.3).

## 6. Non-goals

- Not building a `postToolUse` or `beforeSubmitPrompt`-based mechanism for the *forcing-read*
  question — confirmed unnecessary (the former) or genuinely incapable (the latter) there, since
  `sessionStart` alone already answers it.
- Not treating `postToolUse` as an untried candidate for the *standing-instruction* question
  anymore — it was tried, wired alongside `sessionStart` with a real reinforcement message, and
  came back negative just like every other context-injection approach (§3.3).
- Not treating the standing-instruction gap as merely unresearched — seven real tests ran and all
  seven came back negative (§2, §3.3). It's a confirmed, likely structural limitation of the
  shipped binding, not an open question waiting on more investigation via the same approach.
