# Axis Contract — v1.5.0 adversarial review (PR #14)

```
AXES:         Dispositional: Genba (go to the actual source) + Shoshin (read fresh, don't trust
              the release's own testing notes). Adversarial: Andon (stop on first critical
              finding) + Chaos Engineering (null/empty/malformed/concurrent inputs). Contextual:
              Poka-yoke (are the claimed safety guards actually in place?).
TARGET:       PR #14 (`v1.5.0` vs `ecbc5b9`/v1.4.0) in /Users/lotusboy/workspaces/permanence.
              12 files, ~360 insertions. Primary: runtime/update.sh (claims: never deletes
              owner-added files, applies renames instead of dropping them, stops flagging
              owner-only customizations "needs review"), runtime/nightly-consolidate.sh (the new
              awake gate + caffeinate wrapping), runtime/install.sh (the new HH:MM time-parsing
              for the nightly setting). Secondary: runtime/session-start.sh's new role_lines()
              (a real ShellCheck bug was already found and fixed here in commit a2b4ab3 — check
              whether that was the only defect or a symptom of a wider one), runtime/roles/pm.md
              (prose, not logic — skim only).
STRUCTURE:    BLUF, then findings ranked most-severe-first, each with file:line, the concrete
              failure scenario, and a suggested fix
EVIDENCE:     file:line for every finding, verbatim snippet where the defect is non-obvious.
              Live-reproduce every hypothesis against a scratch directory before writing it down
              — do not report a theoretical concern as a finding without testing it first.
ASSUMPTIONS:  Maintain a Verified/Unknown ledger. The release's own "How this was tested" section
              (INSTRUCTIONS.md, now folded into the CHANGELOG's [1.5.0] entry) is a claim from
              another Claude session on a different machine, not independent verification —
              treat every one of its test-case claims as Unknown until reproduced here.
STOP:         Andon — halt and flag immediately on any data-loss defect (update.sh silently
              deleting or overwriting content it claims to preserve), since that is the entire
              reason this review exists.
```

## Why this review, and why single-pass rather than Two-Pass

This PR was built entirely on a different machine (by another Claude Code session, per the
owner's own account and a photo of that session's final report) and applied here by copying
files in per a signed set of instructions, without this session doing any of the design or
implementation. The owner asked whether the changes were understood and whether a review was
worth it — the honest answer was no: only the file hashes, syntax, `_meta/VERSION`, and one
smoke-test line were checked before opening the PR, exactly per that release's own instructions
("nothing here needs building or designing").

`runtime/update.sh` makes explicit data-safety claims about a mechanism every future upgrade runs
through — the highest-cost place for an untested claim to be wrong. One real bug (a ShellCheck
false-negative in the new role-resolution code) already survived the other session's own stated
testing pass and only surfaced when this session's CI ran — direct evidence that "tested on the
work laptop" is not the same as independently verified.

Single-pass rather than the full Two-Pass this repo used for PR #13: this PR is a third the size
(12 files vs. 33) and isn't a rewrite of shared install machinery the way the harness-binding
mechanism was — it's incremental behavior changes to two existing scripts plus one small new
feature (roles). The adversarial cocktail alone (Pass 2's axes from the Two-Pass strategy) is the
right tool for verifying specific safety claims under edge cases; the structural/completeness
half of Two-Pass (Pass 1's axes) has less to add when there's no new architecture to assess for
completeness.
