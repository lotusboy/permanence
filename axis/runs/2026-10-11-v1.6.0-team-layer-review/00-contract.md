# Axis Contract — v1.6.0 adversarial review (PR #16)

```
AXES:        Genba + Shoshin (read the real code fresh; trust no note) · Chaos Engineering + Andon
             (break it; stop loud on data loss or a blocked session) · Poka-yoke (are the guards real)
TARGET:      PR #16, branch v1.6.0 vs main (ff58166). Primary: what every existing install runs —
             runtime/bindings/claude-code/wire (agents copy/cleanup, three new hooks merged into
             settings.json, repo-hooks call), runtime/agent-roles.py + team_roles.py (a PreToolUse
             hook on EVERY Agent dispatch, a SubagentStop hook, a SessionStart check),
             runtime/session-start.sh, runtime/repo-hooks.sh (writes into other git repos),
             the harness-marker skip in the antigravity/devin/cursor wires. Secondary: the new
             tools (decision, spend, save-report, predict-gate, ratify, ops-event, ops-gap).
STRUCTURE:   BLUF, then findings most severe first: file:line, exact repro, suggested fix
EVIDENCE:    every finding live-reproduced in a scratch HOME / scratch repo before it is written
ASSUMPTIONS: Verified/Unknown ledger. The package was built on another machine against one repo.
STOP:        Andon on: an existing install's settings.json or agents damaged; a user's own file
             overwritten or deleted without backup; a hook that can block or break a session for a
             user who never opted in to the team; a write into a repo the owner does not own.
```

Single adversarial pass, one agent: this release is mostly new files nothing depends on, so the
risk to existing users sits in the changed files and the always-on hook, which is the scope.
