You are doing an adversarial review using the Axis Engineering method. You have no context beyond
this prompt; that is intentional. Read the contract first: <repo>/axis/runs/2026-10-16-v1.11.0-skills-and-gates-review/00-contract.md

Repo: <repo>, branch v1.11.0. Diff: `git -C <repo> diff main...v1.11.0` (three commits; read their messages).

Attack, in this order:

1. runtime/bindings/claude-code/wire, the new skills block, and runtime/tests/test_claude_code_skills.py.
   In a scratch HOME: a user's own skill with the same name as a shipped one; a user's own skill
   containing the installed-from marker text; an installed copy the user edited, re-installed twice
   (is the earlier kept copy overwritten?); a shipped skill removed from runtime/skills/; extra files a
   user added inside an installed skill folder; a skills folder that is a symlink; names with spaces.
   Prove that nothing the block moves can end up inside ~/.claude/skills/ (any folder there holding a
   SKILL.md loads as a skill). Run the wire twice: idempotent?
2. runtime/decision.py and runtime/spend.py: the new refusals (--read, guess-word labelling, --upstream,
   --rechecked, --stepped-back, --recheck; spend's architect gate). Can each be passed with an empty or
   meaningless value? Does any refuse a call that the shipped instructions themselves tell an agent to
   make (grep runtime/roles/pm.md, runtime/commands/*.md, runtime/skills/*/SKILL.md, runtime/agents/*.md,
   docs/ for every decision.sh / spend.sh example and check each against the new rules)? Does a ledger
   written before this change still read and score? Guess-word detection: false positives on ordinary
   text, quoted words, words inside code identifiers?
3. runtime/roles/pm.md as a whole, read as the agent that must obey it: contradictions, duplicated rules
   saying different things, the spend rule here against runtime/skills/dev-team/SKILL.md, the step-back
   rule against runtime/skills/step-back/SKILL.md and runtime/commands/perma-change.md, the five new
   habits against the rest (for example "investigate before asking" against "puts big things on the
   table and waits"). Is it still generic: no person's or project's name?
4. The human-expert agent and the new 'expert' role in runtime/agent-roles.json: does role resolution
   and preflight handle it (runtime/team_roles.py, runtime/team-preflight.py)? Does the Antigravity
   binding translate it correctly (runtime/bindings/antigravity/agents-install.py)?
5. CHANGELOG [1.11.0] and docs: every claim true of the diff?

Also run: `python3 -m unittest discover -s runtime/tests` in the checkout (it uses temp dirs only).

Rules: reproductions only under
<scratch>/review-1110
with HOME and PERMA_DIR pointed there. Never write to the real $HOME, ~/permanence, or any real repo.
Do not edit any file in <repo> except the output file. Do not read other folders under axis/runs/. Do not
spawn subagents. Stub launchctl on PATH if you run install.sh.

Write your full findings, verbatim, to: <repo>/axis/runs/2026-10-16-v1.11.0-skills-and-gates-review/02-review-output.md (any ANDON first; BLUF in 2-4
sentences; findings most severe first, each with file:line, the repro and its output, a suggested fix,
and one sentence headed "If not fixed:"; then a Verified/Unknown ledger). Report back in under 250 words.
