# Design — a Cursor binding for Permanence

> Status: **proposed, not started.** No code in this repo implements any of this yet — but every
> claim below is live-verified against the real installed product (Cursor Agent CLI
> 2026.09.10-fd3934a), not read from docs alone. One finding reverses an initial, docs-based
> worry; one real gap (no working global standing-instruction file) survived three separate live
> tests and stayed a gap.
> Written 2026-09-14. See [harness-binding-mechanism.md](./harness-binding-mechanism.md) for the
> `detect`/`wire` interface this assumes rather than re-deriving.

**Owner carries, once built: possibly just the ongoing half of the standing instruction.** Three
of five binding-contract questions have real, live-tested answers, one of them (`sessionStart`)
answering passive orientation *and* the forcing read at once — simpler than every other binding
built so far, not more complex. Command invocation is fully confirmed working. The standing
instruction is the one genuinely open question — see §3.3.

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
- **A real mitigating factor**: `session-start.sh`'s own output already carries the standing-rule
  instruction ("Update it whenever something material shifts... without being asked") as part of
  the same content already proven to be genuinely acted upon for the *read* side (§2 above). Not
  yet confirmed whether that carries through to the *write* side mid-session (does the model
  actually update the stream later, unprompted, purely because `sessionStart` told it to at the
  very beginning) — that needs a longer, multi-turn live test this pass didn't include. See §5.

**Headless invocation — confirmed:**

- `agent -p`/`--print` runs non-interactively. `--trust` is needed to skip the interactive
  workspace-trust prompt, which print mode can't display.

## 3. Trigger mapping — the five binding-contract questions

Per `SPEC.md` §3's binding contract, independent questions, not a ladder.

1. **Passive orientation.** Answered by `sessionStart`, alongside question 2 — see below.
2. **Forcing read. Live-confirmed, decisively** (§2) — the one finding that reverses this
   binding's original docs-based worry. `sessionStart` alone demonstrably causes unprompted,
   accurate action on real Permanence content, not just passive availability.
3. **Standing instruction. The one genuinely open question.** `session-start.sh`'s existing
   content already carries this instruction and is proven read/acted-on once; whether it's
   acted on for updates *mid-session*, unprompted, is unconfirmed — no working global rules file
   was found despite three real attempts (§2). See §5.
4. **Command invocation. Live-confirmed**, including literal `/name` syntax from a genuinely
   global path (§2) — the cleanest result of any binding built this session.
5. **Headless invocation. Confirmed** (§2), needing `--trust` for non-interactive use.

Material-shift is what (2) and (3) produce together, not a sixth question — see `SPEC.md` §3.

## 4. Proposed shape (not file-final — a sketch to react to)

The `detect`/`wire` interface is specified once in
[`harness-binding-mechanism.md`](./harness-binding-mechanism.md) — not restated here.

```
runtime/bindings/cursor/
  detect                 # exit 0 iff `agent` (Cursor's CLI binary) is on PATH
  wire                   # merges a sessionStart hook into the GLOBAL ~/.cursor/hooks.json
                          # "hooks" object — NOT the project-level .cursor/hooks.json, which
                          # would violate invariant 1 if written into an open repo. No second
                          # hook needed unless §5's mid-session write question comes back
                          # negative. Command invocation: writes runtime/commands/*.md,
                          # translated to Skill frontmatter, into the global
                          # ~/.cursor/skills/<name>/SKILL.md — confirmed real, confirmed
                          # globally invokable by literal /name syntax.
  session-start-hook.sh  # translator: reads workspace_roots off stdin (present on every hook
                          # payload per Cursor's own docs), calls session-start.sh with a
                          # translated {"cwd": ...} payload, wraps its output as
                          # {"additional_context": <that output>}
```

Unlike Antigravity's and Devin's bindings, this one has **no confirmed need for a once-per-
conversation cursor file** — `sessionStart` fires exactly once per session by its own nature,
unlike Antigravity's `PreInvocation` (fires multiple times per turn) or the general pattern the
other two bindings had to guard against.

## 5. Must verify before writing any code

1. **The mid-session standing-instruction question** — does the model actually update Permanence
   stream files later in a session, unprompted, purely because `sessionStart`'s injected content
   told it to at the start? This needs a real multi-turn session with something material
   happening partway through, not a single `-p` one-shot. If this turns out to work, question 3
   may be free, the same surprising way question 2 turned out to be. If not, a genuine gap
   remains and needs its own mechanism — worth checking `postToolUse` as a periodic reinforcement
   channel before assuming a dead end.
2. **Whether `~/.agents/skills/` (the documented cross-tool alternative global skills path) is
   worth using instead of or alongside `~/.cursor/skills/`** — only the Cursor-specific path was
   live-tested.
3. **Confirm `workspace_roots` is genuinely present on `sessionStart`'s own stdin payload**, not
   just on the generic "every hook receives" list — the live tests so far fed a synthetic payload
   rather than inspecting Cursor's own real stdin directly.

## 6. Non-goals

- Not building a `postToolUse` or `beforeSubmitPrompt`-based mechanism — confirmed unnecessary
  (the former) or genuinely incapable (the latter) for the forcing-read question, which
  `sessionStart` alone already answers.
- Not assuming the standing-instruction gap is unfixable — `sessionStart`'s own content already
  carries the instruction and was proven to work for the read side; §5 item 1 is what decides
  whether that's the whole answer or only half of one.
