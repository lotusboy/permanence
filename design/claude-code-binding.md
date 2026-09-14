# Design — the Claude Code binding for Permanence

> Status: **built and shipped — the reference implementation.** This is Permanence's original,
> most-hardened binding, predating the `runtime/bindings/` mechanism itself. Written 2026-09-13,
> retrospectively, once Antigravity's and Devin's own design docs existed — added for the same
> reason those two got one: so a reader browsing `design/` sees every binding documented to the
> same standard, not every binding except the one everything else was modelled on.

**Owner carries: nothing.** All five binding-contract questions are answered, all five have been
working in production use of Permanence since before this session, and the migration into
`runtime/bindings/claude-code/` (§4) changed where the code lives, not what it does — confirmed
byte-for-byte against the pre-migration behavior.

## 1. Why this doc exists

`design/harness-binding-mechanism.md`, `design/antigravity-binding.md`, and
`design/devin-binding.md` each document their binding's five answers, their verification method,
and their shape. Claude Code's binding — the one every other binding's design was checked
against for plausibility — had no equivalent doc, because it was never designed in one sitting
the way the others were; it accreted, hardened, over many sessions before `design/` existed as a
convention. This doc is that missing piece, written after the fact from the real, shipped code
and `SPEC.md` §3's existing description of it, not from fresh research.

## 2. What's verified, and against what

Everything here has a different evidence base than the other two bindings: not a single research
session, but sustained real use — this is the binding every `/perma-*` command, every session
hook, and this entire multi-week project has been built and tested against, continuously,
including the very session that wrote this doc. Two real bugs specific to the mechanics below
were found and fixed on 2026-09-13, during the migration into `runtime/bindings/claude-code/`
(§4) — both are noted where they apply, since they're part of this binding's own verified
history, not incidental.

**Hooks (`~/.claude/settings.json`) — the forcing read and passive orientation:**

- `SessionStart` → `runtime/session-start.sh`, appended to the hook list.
- `UserPromptSubmit` → `runtime/session-load.sh`, inserted first in the hook list — the reliable
  forcing mechanism, since `SessionStart`'s context is passive and the model doesn't reliably act
  on it until a later hook makes it load-bearing.
- Both registered as `{"hooks": [{"type": "command", "command": "<script>", "timeout": 10}]}`,
  merged in by a Python3 heredoc that checks presence before writing (idempotent), backs up the
  file before any change, and falls back to printing the exact JSON for manual entry if `python3`
  is absent.
- `permissions.additionalDirectories` gets `~/permanence` appended, so the hook scripts can
  actually read Permanence's own files.

**`CLAUDE.md` — the standing instruction:**

- A delimited `<!-- perma:begin -->...<!-- perma:end -->` block, managed by the shared
  `_perma_block_merge()` helper (now `runtime/lib/block-merge.sh`, extracted 2026-09-13 — see
  §4), never touching anything outside the markers.
- Refuses to touch a file with a mismatched marker count rather than risk deleting content after
  it — a real hardening decision, not a hypothetical edge case guarded against speculatively.
- **A real bug, found and fixed 2026-09-13**: on a genuinely fresh install (no prior `CLAUDE.md`
  at all), the "no existing marker" branch's compound shell command had its exit status
  accidentally poisoned by a harmless `cat` on a nonexistent file, silently skipping the final
  rename and leaving the correct content sitting in a `.tmp` file forever, on every subsequent
  run. Reproduced against the original, unmodified code — not introduced by the migration, just
  found while verifying it. Fixed with one `|| true`.

**Commands (`~/.claude/commands/*.md`) — command invocation:**

- Copy-on-install (not symlinked, so an installed copy carries a stable version marker rather
  than tracking whatever the working tree has checked out), from `runtime/commands/`.
- Each file gets an appended `<!-- installed-from: ... -->` comment noting the source path and
  the git SHA it was installed from.

**Scheduling (`claude` CLI + `nightly-consolidate.sh`) — headless invocation:**

- `runtime/nightly-consolidate.sh` runs under a cross-platform scheduler
  (`runtime/schedule-task.sh`: launchd on macOS, cron on Linux/WSL, `schtasks.exe` on native
  Windows via Git Bash), invoking the `claude` CLI directly.
- Scheduling carries its own real hardening, independent of this binding specifically: an
  ownership guard (`_perma_owns_job`) refuses to touch a scheduled job that belongs to a
  *different* Permanence install on the same machine, rather than silently repointing it.

## 3. Trigger mapping — the five binding-contract questions

All five answered, all five in production use.

1. **Passive orientation.** `SessionStart` hook → `session-start.sh` — resolves the current
   directory through `_meta/REGISTRY.md` (via `resolve-stream.sh`) and states the registered
   stream, or says plainly that none is registered.
2. **Forcing read.** `UserPromptSubmit` hook → `session-load.sh` — fires on the user's actual
   first message, so the model acts on the injected instruction rather than merely seeing it.
   Gated by a once-per-session marker (`/tmp/.perma-loaded-<session-id>`) so it doesn't re-inject
   on every prompt.
3. **Standing instruction.** The `CLAUDE.md` delimited block, refreshed on every `install.sh` /
   `wire` run.
4. **Command invocation.** `runtime/commands/*.md`, copied verbatim into
   `~/.claude/commands/`.
5. **Headless invocation.** The `claude` CLI itself, called by the nightly consolidate job under
   a cross-platform scheduler.

Material-shift is what (2) and (3) produce together, not a sixth question — see `SPEC.md` §3.

## 4. Shape — as actually shipped, and the migration that put it here

```
runtime/bindings/claude-code/
  detect    # exit 0 unconditionally — see below for why this isn't a real gate
  wire      # commands copy, CLAUDE.md block merge, settings.json hook merge — in that order,
            # matching the original inline step order in install.sh before the migration
```

**`detect` is trivial on purpose.** Claude Code is the one harness every Permanence install
already has, by construction — you need some AI tool with shell access just to run `install.sh`
in the first place (`harness-binding-mechanism.md` §2). A heuristic check (`~/.claude` existing,
a `claude` binary on `PATH`) was tried first and **found broken live**, on real CI: neither
signal is true this early in a genuinely fresh install, since `wire` itself is what creates
`~/.claude`. Fixed by making `detect` unconditional — there was nothing real left to gate.

**Migration history, 2026-09-13**: this binding's code originally lived inline in `install.sh`
itself, hand-wired, predating `runtime/bindings/` entirely. `design/harness-binding-mechanism.md`
§2 originally decided it should *stay* that way permanently — the regression risk to already-
hardened code was judged not worth a symmetry benefit that's aesthetic, not functional. That
decision was reopened and reversed the same day, on request: every hardening mechanism (backup-
before-edit, the mismatched-marker refusal, `INSTALL_FAILED` tracking) moved with it, unchanged,
and the shared `_perma_block_merge()` helper was extracted into `runtime/lib/block-merge.sh` so
both this binding and the separate, still-inline `AGENTS.md` writer (for *other* tools) share one
copy rather than drift apart. Verified byte-for-byte: a pre-migration and post-migration scratch
install produce identical `~/.claude/` trees, aside from the expected differing repo paths
embedded in the version-marker comments.

## 5. Non-goals

- Not re-litigating the migration decision — see `harness-binding-mechanism.md` §2 for the actual
  reasoning and reversal; this doc just describes the resulting shape.
- Not documenting the generic `AGENTS.md`-writer mechanism (for *other* AI tools that read
  `AGENTS.md`) here — it's a separate, already-existing binding, not Claude-Code-specific, and
  stays inline in `install.sh`. See `docs/TOOL-SUPPORT.md`.
