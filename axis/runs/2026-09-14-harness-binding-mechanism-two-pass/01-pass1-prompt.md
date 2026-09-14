You are doing Pass 1 (Wide Net — analytical) of an Axis Engineering Two-Pass code review. You have
no prior context on this task or codebase beyond what's in this prompt — that's intentional.

## Axes to apply

- **Dispositional**: Seven Factors of Awakening + Genba — go to the actual source, verify claims
  against real code, don't trust summaries (including this prompt's own framing).
- **Pattern-oriented**: Fowler's Refactoring Catalog + SOLID — code smells, responsibility
  violations, duplication.
- **Adversarial**: Pre-mortem + Muda — imagine this in production and failing; find waste
  (dead code, redundant logic, unnecessary complexity).
- **Structural**: MECE + Pyramid Principle — is the review itself complete and non-overlapping;
  structure your output BLUF-first, findings ranked by severity.

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

**Secondary target** (spot-check for internal consistency, not exhaustive): `design/*.md`,
`docs/TOOL-SUPPORT.md`, `SPEC.md`, `CHANGELOG.md`. Flag claims that the code doesn't actually
support, or that contradict each other — not claims about live testing outside this repo (you
can't verify those from a diff, and shouldn't guess).

## What to look for

- Correctness bugs in the shell scripts — quoting, exit-code propagation, unset-variable handling,
  JSON parsing edge cases in the Python heredocs.
- Idempotency: does re-running `wire` on an already-wired install produce the same result, or
  duplicate entries / corrupt existing config?
- Data safety: does any `wire` script overwrite a user's existing config without backing it up
  first? Does any script write outside the paths it claims to (project-level vs global config,
  invariant violations)?
- Consistency across the five binding implementations — do they follow the same idempotent-merge
  pattern, or has one drifted and introduced a different (possibly worse) approach?
- Whether `install.sh`'s generic loop correctly reports failures (a binding's `wire` exiting
  non-zero) rather than silently swallowing them.
- Dead code, leftover debug instrumentation, or docs/comments that no longer match the code they
  describe.

## Evidence rule

Every finding must cite `file:line`. Quote the actual problematic code, don't paraphrase it.
Maintain a running Verified/Unknown ledger — if you assume something about how a hook is invoked
(e.g. what JSON a tool sends on stdin) rather than confirming it from the code/docs in this repo,
mark it Unknown, not Verified.

## Stop condition (Andon)

If you find a data-loss or security defect (e.g., a write that can destroy user data without a
backup path, a credential logged or handled unsafely, a destructive operation with no
confirmation), flag it as CRITICAL at the very top of your output, above the BLUF.

## Output

Write your complete findings, verbatim, to:
`/Users/lotusboy/workspaces/permanence/axis/runs/2026-09-14-harness-binding-mechanism-two-pass/04-pass1-output.md`

Structure: BLUF (2-4 sentences), then findings ranked most-severe-first, each with a one-line
summary, `file:line` citation(s), the concrete failure scenario, and a suggested fix. End with your
Verified/Unknown ledger.

Do not edit any file in the repository other than writing your own output file above. This is a
read-only review.
