You are doing an adversarial code review using the Axis Engineering method. You have no context
beyond this prompt; that is intentional. Read the contract first: <checkout>/axis/runs/2026-10-11-v1.6.0-team-layer-review/00-contract.md

Repo checkout (a git worktree, branch v1.6.0): <checkout>
Diff under review: `git -C <checkout> diff origin/main...v1.6.0`. Reference for intended behaviour:
docs/PROJECT-TEAM.md and the [1.6.0] entry in CHANGELOG.md, both in that checkout — treat them as
claims to test, not facts.

The question that matters most: **can this release hurt someone who upgrades and never uses the
team?** Such a user gets, on every install: three new hooks merged into ~/.claude/settings.json;
agent-roles.py running before every Agent dispatch and at every subagent stop and session start;
eight agent files copied into ~/.claude/agents/; repo-hooks.sh run by wire. Attack that surface:

- wire: settings.json merge with existing hooks of the same events, wrong-shaped values, a second
  run (idempotent? duplicates?), python3 absent; agents copy when the user has a same-named agent of
  their own (backup? marker logic?), cleanup deleting something it should not; behaviour when
  runtime/agents/ is empty or missing.
- agent-roles.py: feed it the hook stdin shapes it expects AND malformed/empty/huge/non-JSON stdin,
  an Agent call with no subagent_type, a plain built-in agent, an unknown role, a missing or
  malformed agent-roles.json, a malformed _personal/agent-roles.json, an unregistered cwd, no
  ~/permanence. It claims to "fail open": prove or break that for each hook mode. Can it ever deny
  or rewrite a dispatch for a user with no binding and no role: prefix? What does it cost per call?
- repo-hooks.sh: can it ever write a hook into a repo whose binding does not say owned:true, or
  overwrite a user's existing post-commit hook, or act when core.hooksPath is set?
- session-start.sh: the new CLAUDE_PROJECT_DIR fallback and the no-WIP.md line.
- The antigravity/devin/cursor wires: the new `harness:` frontmatter skip, including the cleanup of a
  previously installed copy — can it remove a user's own skill?
- Then, with the time left, the new tools: append-only really append-only? concurrent writers?
  a stream that cannot be resolved? paths with spaces?

Rules: do every reproduction in a scratch directory with HOME and PERMA_DIR pointed at scratch.
Never write to the real $HOME, to the live install (~/permanence), or to any real repo. Stub
`launchctl` on PATH if you run install.sh. Do not edit any file in the checkout. Do not read other
folders under axis/runs/. Do not spawn subagents.

Write your full findings, verbatim, to: <checkout>/axis/runs/2026-10-11-v1.6.0-team-layer-review/02-review-output.md
Shape: any CRITICAL first (above the BLUF); BLUF in 2-4 sentences answering the question above;
findings most severe first, each with file:line, the exact repro you ran and its output, and a
suggested fix; then a Verified/Unknown ledger. If a claimed guard holds under attack, say so in
the ledger — that is a result too. Report back in under 250 words.
