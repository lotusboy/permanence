# Design — a Cursor binding for Permanence

> Status: **built and shipped, five of five.** `runtime/bindings/cursor/` implements passive
> orientation + the forcing read (one `sessionStart` hook, per §2), command invocation (Skills),
> and the standing instruction (a `stop` hook, per §3.3.1) — all live-fire tested end-to-end
> against the real installed product, including a real `/perma-help` invocation that executed its
> full logic correctly and a real, unprompted `stop`-hook write to the real production stream.
> Two findings reversed initial, docs-based or negative-testing-based worries: the forcing read
> (§2) and, after seven straight negative tests, the standing instruction itself — the `stop`
> hook that was confirmed dead in headless mode turned out to work in genuinely interactive use,
> the normal way most people actually run Cursor (§3.3.1).
> Written 2026-09-14, extended the same day after two further rounds of live testing — the second
> reversing the first's conclusion. See
> [harness-binding-mechanism.md](./harness-binding-mechanism.md) for the `detect`/`wire` interface
> this implements rather than re-deriving.

**Owner carries: nothing outstanding on the binding-contract questions.** All five are shipped
and live-fire tested — `sessionStart` answering passive orientation *and* the forcing read at
once, simpler than every other binding built so far, not more complex; command invocation
confirmed via a real `/perma-help` run that executed its actual logic (checked scheduled tasks,
read real registry data) rather than just echoing text; and the standing instruction confirmed via
a real interactive session where the `stop` hook fired unprompted and wrote a genuine LOG.md entry
to the real production stream, with no user instruction to do so. The one caveat: this only
reaches interactive use — `stop` is separately confirmed to never fire at all in headless (`-p`)
mode, so a headless/scripted Cursor session still gets no standing-instruction coverage. See §3.3.1.

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
    structural property of how Cursor's agent decides when to use tools on its own initiative
    from injected context alone — reversed one layer up, though, by forcing an actual extra turn
    instead of injecting context into the current one (§3.3.1).

### 3.3.1 Reversal: `stop` works, in interactive mode

The owner ran the genuinely-untested case from §5 item 1 — `stop` in real interactive Cursor use,
which this session has no TTY to test itself. Two runs:

- **First run: an ungated test script looped indefinitely.** A bug in the test script, not a
  Cursor or Permanence defect — it had no `loop_count` gate, so the `followup_message` it returned
  triggered another `stop` firing, which fired again, and so on. Notable on its own terms, though:
  it proved `stop` fires repeatedly and reliably in interactive mode, the opposite of headless.
- **Second run, gated on `loop_count == 0`: complete success.** A fresh interactive session, a
  material throwaway fact stated in the first turn, no instruction to update anything. The agent
  replied once, then — unprompted, with nothing typed by the user — a second automatic turn
  appeared: `stop`'s `followup_message` had fired, the agent recognized it, and ran a real shell
  command that wrote an accurate LOG.md entry describing the fact, then confirmed what it wrote.
  Genuine forced action, not shaped conversation — the first time any write-side mechanism tried
  for this binding produced one.
- **Production confirmation, same day**: the shipped `stop-hook.sh` (§4) was wired for real
  against this machine's actual `~/.cursor/hooks.json` and the real production Permanence stream
  (not a disposable test stream) — same result, a real unprompted LOG.md write, immediately
  reverted since it was only a test fact.
- **What changed the conclusion**: every earlier test injected `additional_context` and hoped the
  model would act on it unprompted within the turn it was already in — that never worked. `stop`
  doesn't inject context into the current turn; it ends the turn and forces a **new** one, with
  the model explicitly told to check for material shifts and write if needed. That's a
  structurally different lever from everything tried in §3.3, and it's the one that worked.
  Headless mode's `stop` is still separately, definitively dead (confirmed via debug logging,
  §3.3) — this reversal is specific to interactive use.

**Headless invocation — confirmed:**

- `agent -p`/`--print` runs non-interactively. `--trust` is needed to skip the interactive
  workspace-trust prompt, which print mode can't display.

## 3. Trigger mapping — the five binding-contract questions

Per `SPEC.md` §3's binding contract, independent questions, not a ladder.

1. **Passive orientation.** Answered by `sessionStart`, alongside question 2 — see below.
2. **Forcing read. Live-confirmed, decisively** (§2) — the one finding that reverses this
   binding's original docs-based worry. `sessionStart` alone demonstrably causes unprompted,
   accurate action on real Permanence content, not just passive availability.
3. **Standing instruction. Live-confirmed, interactive mode only.** Seven straight negatives from
   every context-injection approach (normal wording, a forceful imperative wording, `postToolUse`
   reinforcement, and `stop` in headless mode — §2, §3.3) were reversed by an eighth test: the
   `stop` hook's `followup_message`, run in genuinely interactive use, forces a real extra turn
   that causes an unprompted, accurate write to the stream — confirmed both in an isolated test
   and against the real production stream (§3.3.1). Headless (`-p`) sessions still get no
   coverage here — `stop` is confirmed to never fire there at all.
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
  wire                   # merges sessionStart + stop hooks into the GLOBAL ~/.cursor/hooks.json
                          # "hooks" object — NOT the project-level .cursor/hooks.json, which
                          # would violate invariant 1 if written into an open repo.
                          # Command invocation: translates runtime/commands/*.md into the global
                          # ~/.cursor/skills/<name>/SKILL.md, reusing each command's own existing
                          # `description:` frontmatter field directly rather than re-deriving it
                          # (one file, perma-contents.md, has none — falls back to its first
                          # heading).
  session-start-hook.sh  # translator: reads workspace_roots off stdin, calls session-start.sh
                          # with a translated {"cwd": ...} payload, wraps its output as
                          # {"additional_context": <that output>}
  stop-hook.sh            # the standing-instruction fix (§3.3.1). Gated on loop_count == 0 so it
                          # fires once per real user turn, not on the follow-up turn it itself
                          # triggers. Resolves the real stream via resolve-stream.sh and returns
                          # {"followup_message": ...} asking the model to check for material
                          # shifts and write to PROJECT.md/LOG.md if anything came up, or say so
                          # if not. Returns {} (no-op) for an unregistered/perma-meta path, or when
                          # loop_count != 0.
```

Live-fire verified end-to-end, not just dry I/O: wired for real on this machine, then a real
`agent -p` session (a prompt that never mentioned Permanence) spontaneously read and accurately
reported real stream content — including noticing this very binding's own code was still
untracked in git — and a real `/perma-help` invocation executed its full logic correctly
(checked actual scheduled tasks, read real registry data). The `stop` hook was additionally
live-fired in a real interactive session, wired against the real production stream: an unprompted
follow-up turn correctly wrote a (test) LOG.md entry, immediately reverted.

Unlike Antigravity's and Devin's bindings, this one has **no once-per-conversation cursor
file** — `sessionStart` fires exactly once per session by its own nature, unlike Antigravity's
`PreInvocation` (fires multiple times per turn) or the general pattern the other two bindings
had to guard against.

## 5. Still open — none of these block anything shipped

1. **Headless (`-p`) sessions get no standing-instruction coverage** — `stop` is confirmed dead
   there (§3.3), and no other mechanism was found across seven tries (§2, §3.3). Not currently
   pursued further: headless use is the minority case for Cursor, and every context-injection
   lever available in headless mode was already tried and failed. Would need a genuinely
   different mechanism (e.g. `preToolUse`'s `updated_input`, or `PermissionRequest`'s auto-approve)
   to revisit.
2. **Whether `~/.agents/skills/` (the documented cross-tool alternative global skills path) is
   worth using instead of or alongside `~/.cursor/skills/`** — only the Cursor-specific path was
   live-tested and shipped.
3. **Whether `workspace_roots` is genuinely present on `sessionStart`'s own real stdin payload**,
   not just the generic "every hook receives" list — the live end-to-end test (§4) succeeded, but
   couldn't distinguish between the real payload carrying it and the hook's own `$PWD` fallback
   silently doing the work instead, since both would resolve to the same directory in that test.
   Worth confirming precisely (e.g. logging the raw stdin during a real session) before relying on
   it for a workspace that differs from the hook subprocess's own working directory. `stop-hook.sh`
   inherits the same open question via the same `workspace_roots`-with-`$PWD`-fallback pattern.

Retired by live testing, no longer open: whether `sessionStart` alone answers the forcing read;
whether weak wording, headless `stop`, or `postToolUse` reinforcement fix the write side — all
three tried and all three failed (§2, §3.3); whether `stop` in interactive use fixes the write
side — tried and confirmed working (§3.3.1), reversing the standing-instruction conclusion this
doc held earlier the same day.

## 6. Non-goals

- Not building a `postToolUse` or `beforeSubmitPrompt`-based mechanism for the *forcing-read*
  question — confirmed unnecessary (the former) or genuinely incapable (the latter) there, since
  `sessionStart` alone already answers it.
- Not treating `postToolUse` as an untried candidate for the *standing-instruction* question
  anymore — it was tried, wired alongside `sessionStart` with a real reinforcement message, and
  came back negative just like every other context-injection approach (§3.3).
- Not treating the standing-instruction question as unsolved anymore for interactive use — `stop`
  is shipped and live-fire confirmed against the real production stream (§3.3.1, §4). Not
  building a second, redundant write-side mechanism on top of it.
- Not claiming standing-instruction coverage for headless (`-p`) sessions — `stop` is confirmed
  dead there, and no other lever was found; §5 item 1 tracks this honestly rather than papering
  over it.
