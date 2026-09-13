# Design — an Antigravity binding for Permanence

> Status: **built and shipped, except the command layer.** `runtime/bindings/antigravity/`
> implements the forcing read + passive orientation (`PreInvocation`) and the standing
> instruction (`GEMINI.md`) — live-fire tested end-to-end against the real installed product on
> this machine, not just dry I/O. Skills/command invocation is still deliberately unbuilt — see
> §5 item 1, unchanged: it needs its own live-fire test before its `wire` shape is committed to.
> Written 2026-09-13, substantially revised twice the same day after live testing. See
> [gemini-cli-binding.md](./gemini-cli-binding.md) — Antigravity shares a `~/.gemini/` path
> prefix with Gemini CLI, which is shared branding, not a shared mechanism for hooks (confirmed
> below), though the two may genuinely share one standing-instruction file (also below).

**Owner carries: nothing, for the read/write side that's built.** Four of five binding-contract
questions (§3) are shipped — forcing read + passive orientation and standing instruction
live-fire tested against a real `agy --print` session, the model's actual reply demonstrably
reflecting the injected content. Command invocation (Skills) is the one still open — see §5.

## 1. Why

Same owner motivation as the Gemini CLI design: Antigravity is on the wish list alongside Claude
Code/Desktop and Gemini CLI/Mac. **Priority flipped to Antigravity over Gemini CLI on 2026-09-13**
(see `design/harness-binding-mechanism.md` §5): personal Google-account sign-in to Gemini CLI is
being actively rejected server-side, reproduced twice, with Google's own message pointing
individual users at Antigravity instead. Antigravity was already installed and authenticated on
this machine, which is what made all the live testing below possible.

## 2. What's verified, and against what

**Primary source: files bundled with the actual installed product**
(`~/.gemini/antigravity-ide/builtin/skills/agy-customizations/`), not the public web docs. This
is the literal spec the installed binary (`antigravity-cli` 1.2.2, via
`brew install --cask antigravity-cli`) implements, discovered by browsing the install rather than
re-reading the public site harder. Version-pinned to 1.2.2, not guaranteed to match any other
version. The bundle's own overview (`SKILL.md`) states the full customization system precisely
enough that most of what follows is *read*, not inferred — the live tests exist to confirm the
docs match reality, and in every case here, they did (after correcting one schema error, itself
also caught by the binary's own error message, not by guessing).

**Discovery locations, per the bundle's own overview — three, each with a distinct scope:**

1. **Workspace** (`.agents/`, or `.agent/`/`_agents/`/`_agent/`) — walked from cwd up to the
   repository root (the `.git` boundary). Covers skills, plugins, and — per the generic docs,
   though **live-tested and not observed working for hooks specifically in 1.2.2** (see below).
2. **Directory & Project Rules** (`GEMINI.md`, `AGENTS.md`, `.agents/rules/*.md`) — a *separate*
   walk, from the current file's directory up to the repository root. This is the standing-
   instruction mechanism (§3 question 3).
3. **Global** (`~/.gemini/config/`) — machine-wide, applies to every project. Confirmed by
   testing to be where `hooks.json` actually lives for this version, contradicting the generic
   docs' workspace-first framing.

Priority when names collide: workspace > workspace-declared JSON config > global > built-in >
global-declared JSON config.

**Hooks (`hooks.json`) — live-tested, config confirmed by the binary's own error messages:**

- **Location: the global `~/.gemini/config/hooks.json` is what this version actually reads** —
  proven by a real Go parse error from the binary (`hooks_manager.go`) on a wrong schema, then a
  real "loaded N named hooks" line once corrected. **Workspace-local `.agents/hooks.json` was
  tried and not discovered at all** — "loaded 0 named hooks from 0 hooks.json file(s)," despite a
  file genuinely present there. Plausible explanation, not yet confirmed: the test directory
  wasn't a git repository, and location 1's walk-up needs a `.git` boundary to anchor on — a real
  registered Permanence project normally would be one, so this may not matter in practice, but
  it's a real gap between the generic docs and what was observed, not assumed away.
- **Schema, precisely**: the top level of `hooks.json` is **arbitrary hook *names***, each
  optionally carrying `"enabled"` plus event names as sub-keys — not event names directly at the
  top level. `PreToolUse`/`PostToolUse` are **grouped**: `[{"matcher": "...", "hooks":
  [{"command": ...}]}]`. `PreInvocation`/`PostInvocation`/`Stop` are **flat**: `[{"command": ...,
  "timeout": ...}]`.
- **`PreInvocation` fires, and its context-injection mechanism genuinely works — live-proven, not
  just config-loading confirmed.** A hook returning
  `{"injectSteps":[{"ephemeralMessage":"...say the word BANANA..."}]}` caused the model's real
  reply to actually contain "BANANA." This is the literal forcing-read mechanism Permanence needs.
- **`PreInvocation` fires more than once per turn** — captured payloads carried
  `"invocationNum":0` then `"invocationNum":1` within one simple exchange. A once-per-conversation
  cursor is required; `conversationId` is present in every payload and is the natural key, the
  same role `session-load.sh`'s `/tmp/.perma-loaded-<session-id>` plays for Claude Code.
- **`PreToolUse` fires and fails closed correctly**: a hook returning a bare `{}` (not a valid
  `{"decision": "allow"|"deny"|"ask"|"force_ask", ...}`) caused the tool call to be denied
  automatically — a real, sensible safety default.
- **Headless mode (`agy --print`) does carry hooks** — an earlier same-day finding that it didn't
  was wrong, traced to the schema and location bugs above being simultaneously wrong, not a real
  product limitation. Retested clean once both were fixed.

**Rules (`GEMINI.md`/`AGENTS.md`) — the standing-instruction question, live-tested and
confirmed:**

- The bundle's `rules.md` states plainly: these files are discovered walking up from the current
  file's directory to the repository root, no frontmatter needed, always active for their scope.
- **Live-tested at the global level, and it works.** `~/.gemini/GEMINI.md` already exists on this
  machine (empty, pre-existing). Wrote a test instruction into it ("end every reply with the word
  ZUCCHINI"), ran a real `agy --print` session with **no hooks involved at all** — the reply
  genuinely ended in "ZUCCHINI." Restored the file to empty immediately after.
- **This is the same file Gemini CLI reads** (confirmed independently in that design doc's own
  research: `GEMINI.md`, discovered upward from cwd to `.git`, not `AGENTS.md`). One global file
  may be able to carry the standing instruction for both bindings at once — worth designing for
  deliberately rather than writing two separate blocks that could drift apart.
- Not yet tested: a project-level `GEMINI.md`/`AGENTS.md` (only the global one was tried) — the
  mechanism doc's own precedence order says workspace would win if both existed, consistent with
  Claude Code's own CLAUDE.md-block pattern.

**Skills (`skills/<name>/SKILL.md`) — the command-invocation question, confirmed against the
bundled docs, not yet live-tested:**

- A skill is a directory (`skills/<name>/`) containing `SKILL.md` with YAML frontmatter (`name`,
  `description`) plus the procedure body — structurally very close to what
  `runtime/commands/*.md` already are, minus the frontmatter.
- **Invocation is description-matched, not literal slash syntax.** Per the bundle's overview:
  "Skills are not loaded into the context window by default. Only their names and descriptions
  are injected. The full content of a skill is only loaded if the model (or the user) explicitly
  decides to activate it." This is a genuinely different invocation model from Claude Code's
  `/perma-shutdown` — no confirmed literal command syntax was found — but it's functionally
  equivalent for the human-triggered triggers: saying something matching a skill's description
  (e.g. "wind down for the day") should activate it, the same job a slash command does.
- Discovery follows the same workspace/global split as hooks (§ above) — `skills/` under
  `.agents/` in a workspace, or under `~/.gemini/config/` globally; `skills.json` exists for
  registering non-standard locations (e.g. pointing at a shared, version-controlled skills
  directory), per `json_configs.md`.

## 3. Trigger mapping — the five binding-contract questions

Per `SPEC.md` §3's binding contract, these five questions are answered independently, not as a
ladder. **All five now have real answers.**

1. **Passive orientation.** No `SessionStart`-equivalent event exists, and none is needed:
   `PreInvocation` fires reliably (§2), so per `SPEC.md` §3's "forcing subsumes passive," this
   question is correctly answered by omission — confirmed, not assumed.
2. **Forcing read.** **Live-confirmed.** `PreInvocation` + `ephemeralMessage` injection
   demonstrably steers model output (§2's BANANA test). Needs a once-per-conversation cursor
   keyed on `conversationId` before it's a real binding, not just a proof of concept.
3. **Standing instruction.** **Live-confirmed**, and the one question whose absence would have
   been silent (`SPEC.md` §3) — verified rather than assumed for exactly that reason. Global
   `~/.gemini/GEMINI.md` genuinely works (§2's ZUCCHINI test), and is very plausibly shareable
   with the Gemini CLI binding rather than needing its own separate file.
4. **Command invocation.** Confirmed to exist via **Skills** (§2), against the bundled docs —
   not yet live-tested with a real skill firing. Different invocation model from Claude Code
   (description-matched, not literal `/command`), but structurally close to
   `runtime/commands/*.md` already and functionally does the same job.
5. **Headless invocation.** Confirmed real (`agy --print`), and confirmed to carry hooks
   correctly — live-tested, the earlier same-day concern that it might not was wrong (§2).
   `workspacePaths` needs the explicit `--add-dir` flag in headless mode; **the GUI IDE
   populates it automatically** just from opening a real folder (live-tested: opening
   `~/workspaces/modo` produced `"workspacePaths":["/Users/lotusboy/workspaces/modo"]`) — the
   realistic day-to-day case works with zero configuration.

Material-shift is what (2) and (3) produce together, not a sixth question — see `SPEC.md` §3.
On-commit (guard + refresh) is unaffected: a git hook, not an AI-harness hook, no binding needed.

## 4. Shape — as actually shipped

The `detect`/`wire` interface, and what `install.sh` does with this directory, are specified once
in [`design/harness-binding-mechanism.md`](./harness-binding-mechanism.md) — not restated here.

```
runtime/bindings/antigravity/
  detect                   # exit 0 iff `agy` (or ~/.gemini/antigravity-cli) is present
  wire                     # merges two NAMESPACED hook names into ~/.gemini/config/hooks.json
                            # (global, not workspace .agents/ — confirmed undiscovered by this
                            # version); writes the standing-instruction block into
                            # ~/.gemini/GEMINI.md via runtime/gemini-md-block.md (a dedicated
                            # block, not agents-md-block.md's Tier-2 framing, which doesn't match
                            # this binding's actual capability). The Skills/command layer is NOT
                            # in wire yet — see §5 item 1.
  pre-invocation-hook.sh   # reads invocationNum + conversationId off stdin; if this
                            # conversationId's cursor hasn't fired yet, calls session-start.sh +
                            # session-load.sh's combined output (fed a translated {"cwd": ...}
                            # payload derived from workspacePaths[0], reusing their existing
                            # resolve-stream.sh-based stream resolution rather than reimplementing
                            # it) and returns it as {"injectSteps":[{"ephemeralMessage": ...}]};
                            # otherwise returns {} and marks the cursor.
  pre-tool-use-hook.sh     # returns a real {"decision": "allow", ...} object, not a bare {}
                            # — confirmed the latter fails closed and blocks the tool (§2)
```

Live-fire verified end-to-end, not just dry I/O: wired for real on this machine, then a real
`agy --print` session correctly reported the exact `[perma]` stream-registration line the hook
injected — the model's own answer, not a log line.

## 5. Still open — the command layer only

Everything blocking the read/write half shipped (§4). What's left is narrower, and only item 1
actually blocks more code from being written:

1. **Live-fire an actual Skill**, not just read the docs on how they work — confirm the
   description-matching invocation behaves as documented, and check whether there's also a
   literal explicit-invocation syntax (a `/name` or `@name` mention) the docs didn't surface.
   This is the one open item that's still load-bearing — `wire`'s Skills/command-invocation logic
   isn't written until this is checked.
2. **Confirm the `.git`-boundary hypothesis for workspace discovery** — does `.agents/hooks.json`
   (or `skills/`) work once the test directory is a real git repo, unlike the non-repo scratch
   folder tested? Matters for whether project-scoped bindings are viable at all, versus
   global-only. Not blocking — the shipped binding uses the confirmed global path.
3. **Whether a project-level `GEMINI.md`/`AGENTS.md` is worth using instead of (or alongside) the
   global one** — only the global file was live-tested and shipped; per-project rules were not
   tried.
4. **Whether a Gemini CLI hook and an Antigravity hook, and a shared `GEMINI.md`, coexist
   cleanly** on one machine — moot for now: Gemini CLI's binding is permanently declined
   (`harness-binding-mechanism.md` §5), not just paused. Revisit only if that changes.

Retired by live testing or authoritative local docs, no longer open: `PreInvocation`'s existence,
cardinality, and injection mechanism; `PreToolUse`'s fail-closed behavior; `workspacePaths`
resolution on both CLI and GUI; whether headless mode excludes hooks; the standing-instruction
question; the existence (though not yet the exact invocation syntax) of a command layer.

## 6. Non-goals

- Not building the command-invocation layer yet — item 1 (live-firing a real Skill) is worth
  doing before committing to the exact `wire` shape for it, since the description-match
  invocation model is confirmed to exist but not yet exercised for real. Everything else shipped.
- Not assuming Antigravity and Gemini CLI's hook engines are related just because of the path
  overlap — confirmed as two separate config files and two separate discovery behaviors. Their
  standing-instruction file may genuinely be shared, which is the opposite finding, and both are
  now evidence-based rather than assumed either way.
