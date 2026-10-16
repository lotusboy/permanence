# v1.11.0 adversarial review — what was done with each finding

Fixed on the same branch before the pull request, 2026-10-16. Machine-specific paths in the review files
were replaced with `<repo>`, `<scratch>` and `<os-temp>`; nothing else in them was edited. 212 tests pass
(206 before; 6 new or extended regression tests cover the cases below).

| Finding | Done |
|---|---|
| ANDON 1, H1 — decision.sh refused its own header example | Fixed. `--read` is not required for categories in the new config key `groundingExempt` (default spend, process, scope): no source file settles those. The header example passes, and a test runs it. |
| ANDON 1, H2 — spend.sh refused its own examples; breaking change not stated | Fixed. Both examples now pass (a test runs one). The CHANGELOG says plainly that a first record needs five flags. Empty values are refused. |
| ANDON 2, H3 — gates passed with "." or a folder; repeated round numbers dodged the count | Fixed. `--read` must be a regular file. `--read-what` needs a word; `--upstream`, `--rechecked` and `--stepped-back` need a statement of three words. Fix rounds are counted from the ledger: an earlier number is refused, and a fix on a task must name its round. `--recheck` needs an existing round. Rounds below 1 are refused. spend: an architect run needs `--task`, and the task match ignores case. |
| H3, the architect gate fires at record time | Stated, not changed: spend.sh runs after an agent finishes, so it gates the record. The PM role and the step-back skill put the step-back before the dispatch. A dispatch-time gate in the role hook is a possible later change. |
| ANDON 3, M2 — PM role and step-back skill disagreed on when to step back | Fixed. One list, in the skill, with the PM role's signals added (nothing moved, upstream cause, second architect, third fix round). Five signals stop the next dispatch on their own; the rest act at two. The PM role points at the skill instead of restating it. |
| ANDON 3, M3 — habits against the PM role's own rules | Fixed. A defect is written in the stream at once, and in the team tracker where the owner has said so. A spend wave is opened where the owner uses the spend ledger. The step-back skill's briefing rule defers to a command's own template. |
| H4 — a failed move reported "kept", nested a copy, exited 0 | Fixed. Each kept or retired copy gets a folder of its own (two runs in one second cannot collide). A failed move is reported as FAILED, the copy is left in place, and nothing is installed over it. Tests for both triggers. |
| M1 — untouched copies called "edited" after every upstream change | Fixed. A fingerprint of each installed skill is kept outside the skills folder; "edited" means the files no longer match it. Test. |
| M4 — ordinary questions refused; one `guess:` switched the check off | Fixed. A sentence-opening "should" and the word "pattern" are not counted; "fixed" and "patch" do not mean a fix is proposed; a `.pdf` or `.csv` is never an agent's record. `guess:` clears only its own sentence. Tests. |
| M5 — the expert role pinned to the top model | Kept, on the owner's decision (2026-10-16). The dev-team skill now says a role table may pin the top model, and names this role. |
| L1 — a nested SKILL.md edit not detected | Fixed by the fingerprint, and by the fallback comparing every file. Test. |
| L2 — the installer and its test wrote into the OS temp folder | Fixed: an unedited copy is removed, not moved to temp; the test points TMPDIR at a folder that does not exist. The five temp folders the reviewer's first run left behind were not removed. |
| L3 — domain wording in the skills; "him" in the PM role | Fixed: neutral wording; `qlmanage` marked as the macOS way; "the owner". |
| L4 — a binding field nothing reads | Fixed: the PM role says to use the kinds the repo's docs name. |
| L5 — the frontmatter check snippet was broken and needed PyYAML | Fixed: standard library only; run on all 12 shipped agents and skills (all pass) and on a broken file (caught). |
| L6 — small doc errors | Fixed: TOOLS.md on Antigravity and on spend's lesson stubs; the tier mapping names `fable`; the CHANGELOG says Claude Code where it said every install; the no-invented-data habit is scoped to reports about real work. |
