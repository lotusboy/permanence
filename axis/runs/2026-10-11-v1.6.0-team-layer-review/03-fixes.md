# v1.6.0 adversarial review — what was done with each finding

Fixed in the same pull request (PR #16), 2026-10-11. Each fix was checked by re-running the finding's
own reproduction in a scratch HOME. Tests: 147 pass (140 before, 7 new in `TestNoBinding`).

| Finding | Done | How it was checked |
|---|---|---|
| C1 — cleanup deletes a user's own agent | Fixed. The marker must be the file's last line and name that file. An orphan is moved to `<name>.perma-removed`, never deleted. Same rule for the commands cleanup. In the Antigravity, Devin and Cursor wires the marker must name the skill, and files a user added beside `SKILL.md` are kept. | Re-ran both variants: the renamed copy and the file quoting the marker both survive. A real orphan is moved aside. A marked skill folder with a user's note keeps the note. |
| H1 — SubagentStop demands a record with no binding | Fixed. The shipped table demands a record only where a binding exists and says `owned: true` (or names `reviews`). | New tests: no binding, and `owned: false`, both return nothing. |
| H2 — plain agent names rewritten with no binding | Fixed. Without a `role:` dispatch the shipped table acts only where a binding exists. The owner's `_personal/` table still applies everywhere. CHANGELOG claim reworded to say exactly what an install gains. | New tests for each case. |
| H3 — a user's same-named agent replaced | Fixed. An unmarked same-named agent is left as it is and reported. An installed copy edited in place is kept as `.perma-bak` (a second one gets a timestamp) before replacement. | Re-ran: the user's `architect.md` is untouched across three runs; the third run changes nothing. |
| M1 — `GIT_DIR` redirects the hook write | Fixed: git's own variables are unset at the top of `repo-hooks.sh`. | Re-ran: the hook lands in the owned repo, not the other one. |
| M2 — wire exits 1 without python3 | Fixed: wire skips repo hooks when python3 is absent. | Re-ran with no python3 on PATH: exit 0. |
| M3 — parallel `decision.sh ask` corrupts QUESTIONS.md | Fixed: one lock per stream around each read-modify-write, and whole-file replace. | 40 parallel asks, three rounds: 40 ledger rows, 40 headings, 40 pointers each time. |
| L1 — `--check-new` nags after agents are removed | Fixed: a missing shipped agent is reported only in a repository with a binding. | Tests pass. |
| L2 — a non-UTF-8 agent file disables resolution | Fixed: read as UTF-8 with replacement. | Tests pass. |
| L3 — traceback when REGISTRY.md is missing | Fixed: exits 0 quietly. | Re-ran. |
| L4 — registered sub-folder gets the hook in the outer repo | Fixed: the registered folder must be the repository root. | Re-ran: skipped with a plain line. |
| L5 — `--stream` accepts `..` | Fixed in `spend.py` and `decision.py`. | Tests pass. |
| L6 — strict `harness:` parser | Fixed: tolerates a comment, indent, quotes, capital letter and a byte-order mark. | Six inputs checked. |
| L7 — non-string `model` passed through | Fixed: ignored. | New test. |
| L8 — "offer ONCE" prints every session | Reworded to "once in this session … do not ask again if they decline". | Read. |

## Not changed

- M3's related note: a QUESTIONS.md with Windows line endings is rewritten with Unix ones. The
  docstring no longer claims byte-for-byte.
- L8's second half: `session-load.sh` and `agent-roles.py` resolve the stream from the working
  directory only, while `session-start.sh` also tries `CLAUDE_PROJECT_DIR`.
- H2's note on `permissionDecision: "allow"` in a rewrite: left as measured on the machine the hook
  was built on. Its effect on a user's own Agent permission rules is still unknown.
- H3's first suggestion, renaming the shipped agents with a prefix: not done. It would change every
  role table and binding already written. Leaving the user's agent in place removes the harm.
- Everything in the review's Unknown ledger stays unknown.

Machine-specific paths in `01-review-prompt.md` and `02-review-output.md` were replaced with
`<checkout>` and `<scratch>` before commit. Nothing else in them was edited.
