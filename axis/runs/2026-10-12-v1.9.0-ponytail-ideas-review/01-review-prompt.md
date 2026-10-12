You are doing an adversarial review using the Axis Engineering method. You have no context beyond
this prompt; that is intentional. Read the contract first: <repo>/axis/runs/2026-10-12-v1.9.0-ponytail-ideas-review/00-contract.md

Repo: <repo> (branch v1.9.0-shortcuts). The diff under review: `git -C <repo> diff main...v1.9.0-shortcuts`.
The release changes instruction text that AI agents will follow. Nothing executable changed.

The source of the three ideas is the public repo https://github.com/dietrichgebert/ponytail (MIT):
skills/ponytail/SKILL.md, skills/ponytail-review/SKILL.md, skills/ponytail-debt/SKILL.md. You may read
those three files with `gh api repos/dietrichgebert/ponytail/contents/<path> -q .content | base64 -d`
to check ONE thing: that this branch reworded the ideas and copied no passage. Do not install it.

Attack these, in this order:

1. runtime/commands/perma-health.md, new step 8. Run `git grep -nI 'shortcut:'` yourself in scratch
   repos you build: no markers; a marker with and without an upgrade condition; a marker whose limit
   itself contains a comma; the word in documentation, in a string literal, in a URL
   (`keyboard-shortcut:`), in a minified or vendored tracked file; a repo with thousands of hits; a
   non-git folder; a binary file. Does the instruction tell the agent what to do in each case, and is
   anything it says about git grep false? Does step 8 fit the rest of the file: the step-3 clean stop,
   the "skip step 6" rule in step 5, the guardrails, the rule that a repo another party owns is
   read-only, and the numbering other files refer to (grep the repo for references to perma-health's
   step numbers, including runtime/bindings/antigravity/team-note.md and docs/)?
2. runtime/roles/pm.md, the two new brief rules. Read them as an engineer agent that obeys literally.
   Can the ordered list be followed into a wrong result (for example: "does it need to exist" used
   to skip work the owner asked for; "already in this codebase" used to couple to an unrelated
   module)? Do the stated limits cover that? Does anything contradict the rest of pm.md or
   runtime/agents/refactor-engineer.md (which must move code verbatim)? Is pm.md still generic: no
   person's name, no project name?
3. The two reviewer agents. Does the new "if not fixed" sentence fit each agent's existing report
   contract and severity table, and anything that reads their findings afterwards
   (runtime/commands/perma-refactor.md, perma-change.md, runtime/agent-roles.py's run-record check)?
4. CHANGELOG.md [1.9.0] and the two doc rows: is every claim true of the diff? Is the credit right?
5. Constraints the owner set: runtime/claude-md-block.md and every other file all sessions load are
   untouched; no hook added; pm.md generic. Verify each from the diff.

Rules: do every reproduction in a scratch directory under
<scratch>/review-190
Never write to the real $HOME, to ~/permanence, or to any real repo. Do not edit any file in <repo>
except the one output file. Do not read other folders under axis/runs/. Do not spawn subagents.

Write your full findings, verbatim, to: <repo>/axis/runs/2026-10-12-v1.9.0-ponytail-ideas-review/02-review-output.md
Shape: any ANDON first; BLUF in 2-4 sentences; findings most severe first, each with file:line, the
exact case (and the command output where you ran one), a suggested fix, and one sentence headed
"If not fixed:" saying what happens if it is left; then a Verified/Unknown ledger. A rule that holds
under attack goes in the ledger. Report back in under 250 words.
