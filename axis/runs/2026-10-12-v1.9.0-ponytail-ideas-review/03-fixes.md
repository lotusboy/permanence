# v1.9.0 adversarial review — what was done with each finding

All fixed on the same branch before the pull request, 2026-10-12. Machine-specific paths in
`01-review-prompt.md` and `02-review-output.md` were replaced with `<repo>` and `<scratch>`; nothing
else in them was edited.

| Finding | Done |
|---|---|
| A1 — the two brief rules contradicted the refactor engineer's verbatim rule, and were in no brief template | Fixed. `pm.md` now says where the rules apply: new or changed code, never a byte-identical refactor step. Each list line has its action. The codebase's own structure is kept. The `/perma-change` engineer brief carries a short form of both rules, and `pm.md` says a command's template wins. A shortcut is defined, so it is distinct from a cut corner. |
| A2 — three tokens identical to the source while the notes said nothing was copied | Fixed. The CHANGELOG now names exactly what is kept the same and why (the marker format, the `no-trigger` tag, the order of the list). The heading and the two identical phrases were reworded. |
| A3 — step 8 broke the file's "facts from the binding" and "no AI spend" lines | Fixed. Both lines now name step 8 as the one exception. |
| F4 — noise in a repo with keyboard-shortcut settings; commas; no cap | Fixed. The pattern needs a comment opener before the word. Re-run on the reviewer's scratch repos: 4,001 matching lines became 1, and the string, URL, YAML and README hits are gone. The upgrade condition is the last clause. Over 200 lines, only per-file counts are given. Long lines are cut at 300 characters. Other errors are shown. |
| F5 — false statements about `git grep`; "every marker" | Fixed. The search now includes new files not yet added (`--untracked`). The text lists what it does and does not see, and says to report "found", never "all". The CHANGELOG and both doc rows no longer say "every". |
| F6 — a Permanence command name inside text carried into briefs | Fixed. The sentence naming the health watch is outside the carried text, with the reason. The `/perma-change` brief lines name nothing of Permanence. |
| F7 — step 8 ran after some stops and not others | Fixed. Step 3 is back to its original wording. Step 8 says when it runs: whenever step 1 passed, including after a stop in step 3 or 4, and never as part of another command's "steps 3 and 4". |
| F8 — refactor-reviewer: "every finding in the report" | Fixed: "every finding in `findings.md`, and each one you list in the report". The sentence does not change the severity. |
| F9 — design-reviewer: new column against "the format of the previous runs" | Fixed: "plus the 'if not fixed' column". |
| F10 — "opt-in files" was loose for the agents | Fixed: the CHANGELOG says the agent bodies load only when the agent is dispatched. |

## Not changed

- Whether the six-step list needs the MIT notice beside it. The list's order is credited to Ponytail
  by name and link in the CHANGELOG; the wording is this project's.
- `refactor-reviewer.md:16`, flagged as resembling a line in the source. It was on `main` before
  this release and is outside its diff.
- Everything in the review's Unknown ledger. In particular, no agent was run against the new text.
