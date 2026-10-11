# v1.6.0 adversarial review — output (PR #16, branch v1.6.0 vs origin/main ff58166)

All reproductions ran in a scratch clone of the branch with `HOME` and `PERMA_DIR` pointed at
`…/scratchpad/review-scratch/home` (`$S` below = `…/scratchpad/review-scratch`). Nothing in the
checkout, the real `$HOME`, or `the live install (~/permanence)` was written. `launchctl` was stubbed;
`install.sh` itself was not run (the wires were run directly). Python 3.12.2, git 2.52.0, macOS.

---

## CRITICAL (Andon: "a user's own file deleted without backup")

### C1. wire deletes a user's own agent, with no backup, if the file contains the marker text anywhere

- **Where:** `runtime/bindings/claude-code/wire:72-80` (the agents cleanup loop, new in this PR).
- **Problem:** The cleanup decides "this file is Permanence's" by `grep -q 'installed-from: ~/permanence/runtime/agents/'` anywhere in the file. It does not check that the marker names *this* file. It then runs `rm -f` with no backup.
- **Realistic trigger:** A user copies an installed agent to a new name to customise it (`cp architect.md my-architect.md`). The marker line at the bottom comes along. The next install or upgrade deletes the customised copy.
- **Who is hit:** Any Claude Code user, team or not. It runs on every `install.sh` / `update.sh`.
- **Repro (ran):**
  ```
  cp $HOME/.claude/agents/architect.md $HOME/.claude/agents/my-architect.md
  sed -i '' 's/^name: architect/name: my-architect/' $HOME/.claude/agents/my-architect.md
  echo "MY CUSTOM RULES - hours of work" >> $HOME/.claude/agents/my-architect.md
  bash $PERMA_DIR/runtime/bindings/claude-code/wire | grep -i my-architect
  find $HOME -name 'my-architect*'
  ```
  Output: `  agent: my-architect.md — removed (no longer in runtime/agents/)`; `find` prints nothing (no `.perma-bak`).
  A second variant also reproduced: a hand-written `other.md` whose body merely quotes the marker string was removed the same way.
- **Fix:** Match the marker against the file's own name (`installed-from: ~/permanence/runtime/agents/$bn `), anchored to the last line. Move the file to `$bn.perma-removed` instead of `rm -f`.
- **Note on ownership:** The commands cleanup (`wire:42-50`) and the skills cleanup in the antigravity/devin/cursor wires have the same substring test and pre-date this PR. Those wires `shutil.rmtree` the whole skill folder; I reproduced that a user's extra file inside a marked skill folder (`perma-change/my-notes.txt`) is removed with it. The agents loop is the new instance; the same fix belongs in all of them.

---

## BLUF

Yes, in three ways, none of which needs the team to be used. (1) Every install can delete a user's own agent file without backup (C1). (2) The eight agents use generic names (`architect`, `design-author`, …): a user's own same-named agent is replaced, and the always-on hook then forces models and, for `refactor-reviewer`, blocks the subagent's stop and tells it to write `axis/runs/` into whatever repo it is in — with no binding at all. That contradicts the CHANGELOG line "with no binding nothing about your install changes". (3) Smaller regressions: wire now fails on a machine without python3, and `repo-hooks.sh` writes into the wrong repo when `GIT_DIR` is set. The hook's "fail open" claim itself held under every malformed input I fed it, and it costs about 24 ms per Agent dispatch.

---

## Findings, most severe first

### H1. SubagentStop blocks `refactor-reviewer` and directs a write into a repo that has no binding (Andon-adjacent)

- **Where:** `runtime/agent-roles.py:158-184`; table entry `runtime/agent-roles.json:27-34` (`run_record: true`).
- **Problem:** `subagent_stop` keys only on `agent_type`. It never checks that a binding exists or that it says `owned: true`. With no binding, `load_binding` returns `{}`, `reviews` defaults to `axis/runs/`, and the hook returns `decision: block`.
- **Why a non-team user can reach it:** wire installs `refactor-reviewer` into `~/.claude/agents/` for everyone. Claude may select it from its description (a review of a restructure) with no team command involved.
- **Effect:** The agent is sent back once and told to create `axis/runs/<date>-…/contract.md` + `findings.md` at the repository root. That repository may belong to another party. docs/PROJECT-TEAM.md "Ownership" says a not-owned repo gets no writes without approval.
- **Repro (ran; `$S/proj` is a `git init` repo, not in REGISTRY):**
  ```
  printf '%s' '{"hook_event_name":"SubagentStop","cwd":"'$S/proj'","agent_type":"refactor-reviewer"}' | $PERMA_DIR/runtime/agent-roles.py
  ```
  Output: `{"decision": "block", "reason": "Permanence agent-roles: role 'reviewer' requires a run record. Before stopping, write axis/runs/<YYYY-MM-DD>-<subject>-<protocol>/ at the repository root with contract.md and findings.md, as your dispatch prompt describes."}`
  With `"stop_hook_active":true` it returns a `systemMessage` instead (does not loop; that guard holds).
- **Fix:** In `subagent_stop`, return `None` unless a binding was found for `cwd` and it says `owned: true` (or carries an explicit `reviews`). Same gate for the `{reviews}` prompt text.

### H2. The hook rewrites dispatches for a user with no binding and no `role:` prefix

- **Where:** `runtime/agent-roles.py:113-137`; `runtime/team_roles.py:192-204` (`role_of` matches by bare agent name).
- **Problem:** Any dispatch whose `subagent_type` equals a shipped provider name gets the table's model forced. Any agent spawned *by* `refactor-reviewer` or `design-reviewer` is capped to sonnet. Neither path looks at a binding. The match is by name only, so a project-level `.claude/agents/architect.md` of the user's own is treated the same.
- **Effect:** A user who asked for haiku gets opus (cost). Every rewrite also returns `permissionDecision: "allow"`, which I could not test in a live Claude Code (see Unknown).
- **Repro (ran):**
  ```
  printf '%s' '{"hook_event_name":"PreToolUse","tool_input":{"subagent_type":"architect","prompt":"x","model":"haiku","description":"d"}}' | agent-roles.py
  → {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow", "updatedInput": {"subagent_type": "architect", "prompt": "x", "model": "opus", "description": "d"}}}
  printf '%s' '{"hook_event_name":"PreToolUse","cwd":"'$S/proj'","agent_type":"design-reviewer","tool_input":{"subagent_type":"general-purpose","prompt":"x","description":"d"}}' | agent-roles.py
  → … "updatedInput": {"subagent_type": "general-purpose", "prompt": "x", "description": "d", "model": "sonnet"}
  ```
- **Deny:** A deny is only reachable with a `role:` prefix (`role:nonsense`, `role:tester` → `permissionDecision: deny`). No deny was reachable without the prefix. That part of the claim holds.
- **Fix:** Either correct the CHANGELOG/README claim, or apply by-name enforcement only when the cwd resolves to a stream with a binding. Omit `permissionDecision` from rewrites (send `updatedInput` only) unless auto-approval is intended.

### H3. A user's own same-named agent is replaced; the backup is a single slot

- **Where:** `runtime/bindings/claude-code/wire:58-71`.
- **Problem:** The eight shipped names are generic. A user with their own `~/.claude/agents/architect.md` loses it as the live agent on upgrade. The install line printed is just `  agent: architect.md` — it does not say a user file was replaced or where the backup is.
- **Repro (ran):** user file `architect.md` ("MY OWN architect v1", model haiku) → after wire, `architect.md` is Permanence's (6326 bytes) and `architect.md.perma-bak` holds v1. If the user puts their own file back (v2) and wire runs again, `.perma-bak` now holds v2; v1 is gone. Edits made directly to an installed (marked) copy are overwritten with no backup at all.
- **Fix:** Namespace the shipped agents (`perma-architect`, …) so no collision is possible. Failing that: skip (do not replace) an unmarked same-named file and print a FAILED/attention line; never overwrite an existing `.perma-bak`.

### M1. `repo-hooks.sh` writes the hook into the wrong repository when `GIT_DIR` is set in the environment

- **Where:** `runtime/repo-hooks.sh:50-58` (`git -C "$repo" …` honours an inherited `GIT_DIR`).
- **Repro (ran):** registry has `$S/repos/owned` (binding `owned:true`); `$S/repos/victim` is unregistered.
  ```
  GIT_DIR=$S/repos/victim/.git bash $PERMA_DIR/runtime/repo-hooks.sh
  ```
  Output says `…/repos/owned — post-commit written`. Actual: `victim/.git/hooks/post-commit` exists; `owned/.git/hooks/` has no hook.
- **When it happens:** install/update run from inside a git hook, `git rebase --exec`, or some `!` aliases. Not from a normal shell.
- **Limits that held:** even then it does not overwrite an unmarked hook.
- **Fix:** `unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE` at the top of the script.

### M2. wire now exits 1 on a machine without python3 (it exited 0 on main)

- **Where:** `runtime/bindings/claude-code/wire:161` + `runtime/repo-hooks.sh:17` (`exit 127`).
- **Repro (ran, PATH with no python3):** v1.6.0 wire `rc=1`, prints `repo-hooks.sh: python3 not found on PATH…`; origin/main wire `rc=0`. `install.sh:103-107` turns that into `binding: claude-code — FAILED to wire` and "done, WITH FAILURES".
- **Also:** the hand-merge text at `wire:149-156` does not list the three new hooks (harmless: they need python3 anyway).
- **Fix:** in wire, call repo-hooks only inside the `command -v python3` branch, or have repo-hooks exit 0 with a "skipped" line.

### M3. Concurrent `decision.sh ask --questions-ref` corrupts the owner's QUESTIONS.md

- **Where:** `runtime/decision.py:136-147` (read → modify → `write_text`, no lock, not atomic).
- **Repro (ran):** QUESTIONS.md with 40 `## Q` entries; 40 parallel `decision.py ask --questions-ref numberNN …`.
  Result: 36 asks in the ledger, 34 pointer lines, **42** headings (entries 39 and 40 duplicated at the tail). Errors seen: `matches 0 QUESTIONS.md entries`, `matches 2 QUESTIONS.md entries`, `…is no longer in the file`. A 12-way run did not reproduce it.
- **Who:** team users only, with two or more writers on one stream.
- **Fix:** `fcntl.flock` on a lock file around read-modify-write, and write via temp file + `os.replace`. Same for `render()` at `decision.py:456`.
- **Related, same function:** a CRLF QUESTIONS.md is rewritten with LF throughout (ran; `od -c` shows `\n` only). The docstring says "Every other byte is left as it was". Open with `newline=""`.

### L1. `--check-new` nags every session if a shipped agent file is removed
`agent-roles.py:200-207`. Ran: move `architect.md` away → every session start prints `[perma] Agent role 'architect': provider 'architect' is not installed — re-run ~/permanence/runtime/install.sh. Tell the owner…`. A non-team user who deletes agents they do not want gets this in every session's context. Fix: only when the cwd has a binding.

### L2. One non-UTF-8 agent file disables `--check-new` and all `role:` resolution
`team_roles.py:24-28` catches `OSError` only. Ran: `~/.claude/agents/latin.md` containing byte `\xe9` → log `ERROR check-new: UnicodeDecodeError(…)`; a `role:reviewer` dispatch passes through unrewritten (so Claude Code receives the literal type `role:reviewer`). Under `LC_ALL=POSIX PYTHONUTF8=0 PYTHONCOERCECLOCALE=0` the shipped agents themselves fail (em dash) and the whole file body is dumped into the log each time. Fix: `open(path, encoding="utf-8", errors="replace")`.

### L3. `repo-hooks.sh` prints a Python traceback when REGISTRY.md is missing
`repo-hooks.sh:26`. Ran: `FileNotFoundError` traceback on stderr, `rc=0`. Fix: `[ -f "$PERMA/_meta/REGISTRY.md" ] || exit 0`.

### L4. A registered sub-folder gets the hook written into the enclosing repository
Ran: registry row `…/mono/sub` with `owned:true` → hook written to `mono/.git/hooks/post-commit`. The owner asserted ownership of the sub-folder, not the monorepo. Fix: require `git rev-parse --show-toplevel` to equal the registered path.

### L5. `--stream` accepts `..`
`spend.py:42-53`, `decision.py:57-68`. Ran: `spend.sh wave open esc --ceiling 5 --stream ../../outside` → wrote `$S/outside/spend/ledger.jsonl`, outside PERMA. Owner-typed input, so low. Fix: reject a stream whose resolved path is not under PERMA.

### L6. `harness:` frontmatter parser is strict in ways that fail open to "install everywhere"
`runtime/bindings/{antigravity,devin,cursor}/wire` `only_for`. Ran: `harness: claude-code # note`, an indented key, `Harness:`, or a BOM → `None` → the command is translated on every harness. `harness: "claude-code"` keeps the quotes. The three shipped files parse correctly.

### L7. A non-string `model` in a table is passed straight into `updatedInput`
Ran: `"model": 7` → `"updatedInput": {…, "model": 7}`. The hook does not crash, but the Agent call would then be invalid, which is not "fail open". Owner-authored tables only. Fix: ignore a non-string model.

### L8. session-start: the WIP line is not "once", and session-load does not share the fallback
`session-start.sh:99-103`: with a role set and no WIP.md, the "Offer the owner ONCE" line prints on every session start (ran twice, printed twice), including for perma-meta (`_meta/WIP.md`). `session-load.sh:39` and `agent-roles.py` still resolve from `cwd` only, so after a compaction SessionStart resolves the stream via `CLAUDE_PROJECT_DIR` and the other two do not. Role users only.

---

## Verified / Unknown ledger

**Verified — guard held under attack**

- settings.json merge: existing `PreToolUse` (matcher Bash) and `SessionStart` entries preserved; three new entries added; second run byte-identical (`diff` clean, "already present"); backup written. No duplicates.
- settings.json wrong shapes: read from code — list/str/None under `hooks`/an event → caught, "NOT touched", exit 1. Not re-run live (unchanged logic from main).
- `runtime/agents/` empty or missing: the copy loop skips (`[ -f ] || continue`). Marked agents are then removed, which is the stated design.
- Fail open, PreToolUse: empty stdin, non-JSON, JSON list, `null`, `{}`, `tool_input` null/string, integer `subagent_type`, integer `description`, 50 MB prompt → rc 0, no stdout, one log line each.
- Fail open, SubagentStop: no `agent_type`, list `agent_type`, integer `cwd`, built-in agent → rc 0, no stdout.
- Fail open, `--check-new`: missing/empty/malformed tables → rc 0, silent. First run silent; a new agent is named once only.
- Missing or malformed `runtime/agent-roles.json` (`{not json`, `[]`, `{"roles":[1]}`, empty, absent): by-name dispatch and stop pass untouched; `role:reviewer` falls back to general-purpose.
- Malformed `_personal/agent-roles.json`: ignored, shipped table still applies.
- `team_roles.py` absent: every mode passes untouched. No `~/permanence` (PERMA_DIR nonexistent): passes untouched.
- Plain built-in agent, no `subagent_type`, unregistered cwd: no output, no rewrite, no deny.
- Cost: 20 plain dispatches 0.48 s (≈24 ms each); 20 `role:` dispatches 0.93 s (≈46 ms each).
- repo-hooks: `owned:false`, no binding, `owned:"true"` (string), list/unparseable binding → no hook. Existing unmarked post-commit → left alone. Symlinked post-commit → left alone, target untouched. `core.hooksPath` set → skipped. Path with spaces → fine. Second run idempotent. The hook never fails a commit (rc 0 with and without a ledger).
- Harness skip: an unmarked user skill named `perma-health` survived on all three wires; marked copies were removed; all three `harness: claude-code` commands skipped.
- session-start: `CLAUDE_PROJECT_DIR` unset, unregistered, or with spaces all behave; no role → no WIP line.
- Tools: paths with spaces work in ops-event, ops-gap, spend, save-report, repo-hooks. Unresolvable stream → one plain line, rc 1, nothing written. save-report refuses to overwrite without `--force`. 3×40 parallel same-agent `spend record` → exactly 1 row each. No unparseable ledger lines after any concurrent run. Test suite: 140 pass in the scratch clone.
- `.agent-roles-seen` and `runtime/logs/` are gitignored; `git status` in PERMA stayed clean of them.

**Unknown — not testable here**

- Whether a live Claude Code delivers `role:<x>` to PreToolUse before validating `subagent_type`, and whether `agent_type` in PreToolUse is the caller (the docstring's 2026-09-30 measurement). Not re-measured.
- What `permissionDecision: "allow"` on a rewrite does to a user's own Agent permission/ask rules.
- Older Claude Code versions where the tool is named `Task`: the `Agent` matcher would never fire (a silent no-op, not harm).
- git older than 2.31: `rev-parse --path-format=absolute` is not understood there; `repo-hooks.sh:58` behaviour not tested.
- Linux and Windows/Git-Bash: nothing here ran off macOS.
- `install.sh` and `update.sh` end to end; ratify, predict-gate and team-preflight beyond the shipped tests.
- spend's check-then-append has no lock; it did not race in 120 attempts, which does not prove it cannot.
