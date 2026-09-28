You are doing an adversarial code review, applying the Axis Engineering methodology. You have no
prior context on this task or codebase beyond what's in this prompt — that's intentional. Read
fresh; do not assume anything about this repo's quality from its name or its other documentation.

## Axes to apply

- **Dispositional**: Genba (go to the actual source, verify claims against real code) + Shoshin
  (beginner's mind — read fresh, don't assume you already know what this code does).
- **Adversarial**: Andon (stop and flag immediately on the first critical/data-loss finding) +
  Chaos Engineering — actively ask: what if this file is null/empty/missing? What if two releases
  touch the same path differently? What if the user renamed a file AND edited it? What if the
  script runs twice? What if a path has spaces or starts with a dash?
- **Contextual**: Poka-yoke — are the specific safety guards this PR claims to add actually in
  place and actually correct, or do they only work for the happy-path case that was tested?

## Target

Repo: `/Users/lotusboy/workspaces/permanence` (a git repo on disk — use `git` and normal file
tools directly, read-only).

Review the diff introduced by `v1.5.0` against `ecbc5b9` (tagged `v1.4.0`):

```
git diff ecbc5b9 v1.5.0
```

**Primary target — review in depth, with live reproduction of every hypothesis:**

- `runtime/update.sh` — this PR's CHANGELOG claims: "never deletes files the owner added; applies
  renames instead of dropping them; a file only the owner customised is kept and no longer
  flagged 'needs review' on every run." Verify each of these three claims directly: construct a
  scratch template + scratch install matching the scenarios the claims describe (an owner-added
  file, a file only the owner changed, a file both the template and the owner changed, a
  template-only change, a template-added file, a template deletion, a template rename) and confirm
  the actual behavior matches the claim in each case. Do not trust the release's own "How this was
  tested" notes — reproduce independently.
- `runtime/nightly-consolidate.sh` — the new awake-gate (checks `/usr/sbin/ioreg` before running)
  and `caffeinate -i` wrapping. Check: what if `ioreg` isn't at that absolute path on some macOS
  version? What if the check itself fails/errors rather than returning a clean yes/no? What if
  `caffeinate` isn't available? Does a failure in the gate silently skip a real nightly run
  forever, or fail loudly?
- `runtime/install.sh` — the new HH:MM time-parsing for the nightly consolidate setting. Test the
  actual parsing logic against edge cases: missing value, malformed value (`abc`), out-of-range
  (`24:00`, `25:99`), single-digit hour (`7:30`), padded whitespace, and confirm the documented
  fallback (05:30) actually triggers correctly and is reported to the user, not silently applied.

**Secondary target — spot-check, one known issue already fixed:**

- `runtime/session-start.sh`'s new `role_lines()` function (role resolution: `.role` = `none` /
  `pm` / a path). A ShellCheck warning (SC2088, a false positive for a deliberate literal-tilde
  match) was already found via CI and fixed in commit `a2b4ab3` on this branch. Check whether that
  was an isolated false-positive or whether the underlying role-resolution logic has a real
  defect nearby — test `.role` missing, `none`, `pm`, an absolute path, a `~/` path, padded
  whitespace, a path to a missing file, and `PERMA_ROLE` overriding the file (the release's own
  claimed test matrix) — reproduce each, don't just read the code and assume it's fine because it
  was "already tested."
- `runtime/roles/pm.md` — skim only, this is prose content for the model to read, not executable
  logic. Flag only if something is actively wrong (e.g., it instructs unsafe behavior), not for
  style.

## Evidence rule

Every finding must cite `file:line`. Quote the actual problematic code, don't paraphrase it. Every
finding must be backed by a live reproduction you actually ran — describe the exact repro steps
inline so they're re-runnable, the same discipline as this repo's prior Two-Pass reviews
(`axis/runs/2026-09-14-harness-binding-mechanism-two-pass/05-pass2-output.md` is the reference
example of this style, if you want to see the bar). Maintain a running Verified/Unknown ledger —
if you couldn't independently reproduce a claim, mark it Unknown, not Verified, and say so
explicitly rather than accepting the release's own testing notes at face value.

## Stop condition (Andon)

If you find a data-loss defect — `update.sh` silently deleting, overwriting, or failing to
preserve content it claims to protect — flag it as CRITICAL at the very top of your output, above
the BLUF.

## Output

Write your complete findings, verbatim, to:
`/Users/lotusboy/workspaces/permanence/axis/runs/2026-09-28-v1.5.0-update-sh-review/02-review-output.md`

Structure: BLUF (2-4 sentences — does the PR's central safety claim hold up or not?), then
findings ranked most-severe-first, each with a one-line summary, `file:line` citation(s), the
concrete failure scenario with its exact reproduction steps, and a suggested fix. End with your
Verified/Unknown ledger, explicitly listing which of the release's own testing-notes claims you
did and did not independently confirm.

Do not edit any file in the repository other than writing your own output file above. This is a
read-only review. Use a scratch directory for all reproduction work — never touch this repo's own
real files or the owner's real `~/permanence` install.
