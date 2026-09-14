You are doing Pass 2 (Focused Verification — adversarial) of an Axis Engineering Two-Pass code
review. You have no prior context on this task or codebase beyond what's in this prompt — that's
intentional. **Do not read anything under `axis/runs/` in this repository before writing your own
output.** A separate Pass 1 review of the same target already ran; you must not read it, reference
it, or let it anchor your analysis. Approach the code completely fresh. If you happen to see the
`axis/runs/2026-09-14-harness-binding-mechanism-two-pass/` folder while exploring the repo, do not
open any file in it other than to write your own output at the end.

## Axes to apply

- **Dispositional**: Genba (go to the actual source, verify against real code) + Shoshin (beginner's
  mind — read fresh, don't assume you already know what this code does).
- **Adversarial**: Andon (stop and flag immediately on the first critical finding) + Chaos
  Engineering — actively ask: what if this field is null/empty/missing? What if this file doesn't
  exist? What if this JSON is malformed? What if this runs twice? What if two processes run it at
  once? What if the tool it's wiring isn't actually installed?
- **Contextual**: Poka-yoke — are mistake-proofing guards actually in place (backups before
  writes, existence checks before reads, idempotency checks before appending)? Where are they
  missing?

## Target

Repo: `/Users/lotusboy/workspaces/permanence` (a git repo on disk — use `git` and normal file
tools directly, read-only).

Review the full diff introduced by branch `add-roadmap-and-adapter-designs` against `main`:

```
git diff main...add-roadmap-and-adapter-designs
```

or view file-by-file with `git show add-roadmap-and-adapter-designs:<path>` and
`git show main:<path>` to compare. 33 files changed, ~2,700 insertions, 41 commits.

**Primary target** (review in depth):
- `runtime/lib/block-merge.sh` — a shared idempotent-merge helper (backup-before-write,
  marker-mismatch handling) used by multiple binding `wire` scripts.
- `runtime/install.sh` — reduced to a generic loop that discovers `runtime/bindings/*/`, runs each
  binding's `detect` then `wire`, and tracks failures.
- `runtime/bindings/claude-code/{detect,wire}` — Claude Code's binding, migrated from
  previously-inline code in `install.sh`.
- `runtime/bindings/antigravity/{detect,wire,pre-invocation-hook.sh,pre-tool-use-hook.sh}`
- `runtime/bindings/devin/{detect,wire,session-start-hook.sh,user-prompt-submit-hook.sh}`
- `runtime/bindings/cursor/{detect,wire,session-start-hook.sh,stop-hook.sh}`
- `.github/workflows/ci.yml` — CI coverage added for all of the above.

**Secondary target** (spot-check, not exhaustive): `design/*.md`, `docs/TOOL-SUPPORT.md`,
`SPEC.md`, `CHANGELOG.md`.

## What this pass is specifically for

Pass 1 (which you must not read) covers structural quality, SOLID, waste, and completeness. Your
job is different: verify the implementation actually does what it claims under adversarial
conditions, not whether it's well-organized.

Focus on:
- **Process compliance**: does each `wire` script actually follow the idempotent-merge discipline
  every design doc for this mechanism claims (load-if-present, warn-and-skip on unparseable,
  back up before writing)? Check each of the five bindings individually — don't assume consistency,
  verify it.
- **Trigger/cascade effects**: `install.sh`'s discovery loop runs `detect` then `wire` for every
  directory under `runtime/bindings/`. What happens if a `detect` script is missing, not
  executable, or exits with an unexpected code? What happens if `wire` partially succeeds (writes
  one file, then fails on a second)?
- **Null/empty/malformed edge cases**: an empty or missing `hooks.json`/`settings.json`/
  `config.json`; a JSON file that's valid JSON but not the expected shape (e.g. `hooks` is a string,
  not an object); a `runtime/commands/*.md` file with malformed YAML frontmatter; stdin that isn't
  valid JSON at all for the hook translator scripts.
- **Missing guards**: anywhere a script assumes a directory exists, a command is on `PATH`, or a
  file is readable/writable, without checking first.
- **Concurrent/repeated execution**: what if `install.sh` (or a single binding's `wire`) runs twice
  in a row, or two installs run at the same time? Does anything corrupt, duplicate, or race?

## Evidence rule

Every finding must cite `file:line`. Quote the actual problematic code, don't paraphrase it.
Maintain a running Verified/Unknown ledger.

## Stop condition (Andon)

If you find a data-loss or security defect (e.g., a write that can destroy user data without a
backup path, a credential logged or handled unsafely, a destructive operation with no
confirmation), flag it as CRITICAL at the very top of your output, above the BLUF, and stop
elaborating on lower-severity findings until it's documented clearly.

To force genuine re-examination rather than passive agreement with a review you haven't seen: at
the end of your output, explicitly note any finding you'd expect a purely structural/completeness
review to miss because it only shows up under adversarial/runtime conditions.

## Output

Write your complete findings, verbatim, to:
`/Users/lotusboy/workspaces/permanence/axis/runs/2026-09-14-harness-binding-mechanism-two-pass/05-pass2-output.md`

Structure: BLUF (2-4 sentences), then findings ranked most-severe-first, each with a one-line
summary, `file:line` citation(s), the concrete failure scenario, and a suggested fix. End with your
Verified/Unknown ledger.

Do not edit any file in the repository other than writing your own output file above. This is a
read-only review.
