# Pass 1 (Wide Net) — Harness Binding Mechanism review

Branch reviewed: `add-roadmap-and-adapter-designs` vs `main` (33 files, ~2,700 insertions, 41 commits).
Reviewed by reading every primary-target file in full at its current on-branch content (this
checkout was already on the branch), plus `git log`/`git diff main...add-roadmap-and-adapter-designs`
for history and per-file diffs, cross-checked against `design/*.md`, `SPEC.md`,
`docs/TOOL-SUPPORT.md`, `CHANGELOG.md`, `README.md`.

No CRITICAL (Andon-level) finding. I did not find a write that can destroy user data without a
backup path, a credential logged or mishandled, or an unconfirmed destructive operation. Every
config file this diff writes to (`hooks.json`, `config.json`, `settings.json`, `CLAUDE.md`,
`GEMINI.md`, `AGENTS.md`) goes through a backup-before-in-place-edit discipline, consistently
applied across all five bindings.

## BLUF

The mechanism itself — `install.sh`'s discovery loop, `block-merge.sh`'s splice-with-backup, and
the four new bindings' JSON hook-merges — is well-built, consistently idempotent, and doesn't
overwrite user config without a `.perma-bak` first. The real defects found are (1) three
user-facing docs (`README.md`, `design/harness-binding-mechanism.md`,
`docs/TOOL-SUPPORT.md`'s own capability table) that now contradict the shipped code and each
other about what's actually built — not a code bug, but exactly the kind of doc/code drift the
review was asked to catch — and (2) a real consistency gap: the three new bindings
(antigravity/devin/cursor) skip the `python3`-presence check and skill-overwrite-without-backup
protections that Claude Code's own binding has, so they've drifted slightly worse than the
reference implementation they were modeled on. None of this is data-loss-critical, but items 1–3
below should be fixed before merge since they're direct, cheap-to-verify factual errors.

---

## Findings, most severe first

### 1. `README.md:137` claims Antigravity "is designed... not yet built" — false, contradicted by the code and every other doc in this same diff

**Citation:** `README.md:137`

```
A full **Antigravity** binding is designed and largely live-verified, not yet built —
```

This is wrong. `runtime/bindings/antigravity/{detect,wire,pre-invocation-hook.sh,pre-tool-use-hook.sh}`
are all present and fully implemented on this branch (`runtime/bindings/antigravity/wire:1-142`
does the `hooks.json` merge, the `GEMINI.md` block, and the Skills translation). This directly
contradicts:
- `docs/TOOL-SUPPORT.md`'s own capability table (`docs/TOOL-SUPPORT.md:19`): `**Antigravity** | ✅ | ✅ | ✅ | ✅ | ✅ | Nothing`
- `SPEC.md`'s binding-contract section: "**Antigravity binding (all five answered).**... **Owner carries: nothing.**"
- `design/antigravity-binding.md:3`: "Status: **built and shipped, all five questions answered.**"
- `CHANGELOG.md`'s own [1.4.0] entry: "Antigravity is now the second binding (after Claude Code) with nothing left for the owner to carry by hand."

**Root cause, confirmed via `git log`:** `README.md` was last touched by commit `7e3c3f9`
(and `3f22c20` before it) — both land *before* `8c18e80` ("Build Antigravity's real binding...
Skills deferred") and long before `9330252` ("Close out Antigravity: Skills live-fire tested,
command layer shipped"). The README sentence was accurate when written and simply never got
updated in the 20+ commits since.

**Failure scenario:** a real user reads the README (the first thing anyone reads), concludes
Antigravity support doesn't exist yet, and either doesn't try it or goes looking for a binding
that's already shipped and working.

**Suggested fix:** update `README.md:137` to match `docs/TOOL-SUPPORT.md`'s table — list
Antigravity alongside Devin/Cursor in the "works with" sentence, drop the "designed... not yet
built" clause entirely.

---

### 2. `design/harness-binding-mechanism.md:120-121` claims Antigravity's "Skills/command layer is still deliberately unbuilt" — same stale-doc bug, different file

**Citation:** `design/harness-binding-mechanism.md:120-121`

```
test case — then Antigravity's binding (hooks.json + `GEMINI.md`; its Skills/command layer is
still deliberately unbuilt, see its own design doc). Each step verified against real GitHub
```

Same root cause as Finding 1: `git log --oneline -- design/harness-binding-mechanism.md` shows
the last commit to touch this file is `4884036` ("Add Cursor design doc"), which predates
`9330252` ("Close out Antigravity: Skills live-fire tested, command layer shipped"). The
referenced "its own design doc" (`design/antigravity-binding.md`) was correctly updated to
"Status: built and shipped, all five questions answered" (line 3) — this file was not.

**Failure scenario:** a maintainer reads this doc (explicitly positioned as "the one place [the
binding] mechanism is decided") to understand what Antigravity's binding does, and is told the
command layer doesn't exist — false, and directly contradicted by
`runtime/bindings/antigravity/wire:81-140`, which is the Skills-translation step.

**Suggested fix:** update the parenthetical to reflect that Skills shipped (`9330252`), or delete
the clause and let `design/antigravity-binding.md` be the single source of truth as the doc's own
§1 says it should be.

---

### 3. `docs/TOOL-SUPPORT.md:20` — the Cursor capability-table row has the interactive/headless claim backwards, contradicting the same file's own prose 60 lines later

**Citation:** `docs/TOOL-SUPPORT.md:20`

```
| **Cursor** | ✅ | ✅ | ✅ | ✅ | ✅ | Nothing in interactive use — the standing instruction (a `stop` hook) only reaches headless (`-p`) sessions with no coverage; see `design/cursor-binding.md` §3.3.1 |
```

Read literally, this says the `stop` hook "only reaches headless (`-p`) sessions" — i.e. it fires
in headless mode. That is the exact opposite of the truth. The real behavior, stated correctly
three other places in this same diff:

- `runtime/bindings/cursor/stop-hook.sh:1-2` (the code itself): "Live-fire confirmed 2026-09-14,
  interactive mode only... this hook never fires at all in headless (`-p`) mode"
- `docs/TOOL-SUPPORT.md:79-80` (same file, further down): "**Owner carries: nothing in interactive
  use.** Headless (`-p`) sessions are the one gap left — `stop` is confirmed to never fire there"
- `SPEC.md`'s Cursor entry: "Owner carries: standing-instruction coverage in headless (`-p`)
  sessions only... interactive use carries nothing."

So the table cell (line 20) and the prose it's supposed to summarize (lines 60-81 of the very same
file) say opposite things. This looks like a copy/paste or sentence-restructure error when the
capability table was authored, not a substantive redesign — everywhere else in the diff, the
"gap" is consistently described as headless-mode-only.

**Failure scenario:** the capability table is the first thing a reader of this doc sees (it's
positioned above the per-tool prose sections specifically as the quick-reference summary) — a
reader who only reads the table walks away believing the opposite of the real limitation, and
either wrongly assumes interactive use needs manual updates, or wrongly trusts headless sessions
to write back on their own.

**Suggested fix:** rewrite the cell to match line 79-80's wording, e.g. "Nothing in interactive
use — the standing instruction (a `stop` hook) never fires in headless (`-p`) sessions, which get
no coverage."

---

### 4. Skill/command files are overwritten with no backup, unlike every other file these wire scripts touch — a same-named pre-existing file is destroyed silently on collision

**Citations:**
- `runtime/bindings/claude-code/wire:27` — `if cp "$f" "$CMD_DST/$name"; then` (unconditional overwrite)
- `runtime/bindings/antigravity/wire:127`, `runtime/bindings/devin/wire:139`,
  `runtime/bindings/cursor/wire:111` — `with open(os.path.join(skill_dir, "SKILL.md"), "w") as f:`
  (unconditional overwrite, no existence check, no backup)

Every other config surface these wire scripts touch — `hooks.json`, `config.json`,
`settings.json`, and every `CLAUDE.md`/`GEMINI.md`/`AGENTS.md` standing-instruction splice — goes
through a `.perma-bak` copy before being overwritten (`block-merge.sh:25`, and the `shutil.copy(path, path + ".perma-bak")` line present in all three hooks-merge heredocs). The command-copy and
Skills-translation steps do not: `cp` and `open(..., "w")` both truncate/replace whatever was
already at that path with zero backup and zero collision check.

**Failure scenario:** if a user has their own, unrelated Cursor/Antigravity/Devin skill (or, for
Claude Code, their own command file) that happens to share a name with one of Permanence's own
(`perma-startup`, `perma-shutdown`, etc. — plausible if a user names a personal skill similarly,
or if a future Permanence command name collides with something they already had), re-running
`wire` silently destroys it with no backup and no warning. This is a narrower precondition than
the JSON-merge paths (requires an actual name collision), which is presumably why it wasn't
treated the same way, but it's the same class of risk the review was asked to check for
("does any `wire` script overwrite a user's existing config without backing it up first?").

**Suggested fix:** either back up an existing file before overwrite the same way the JSON merges
do, or at minimum detect and warn on a pre-existing, non-Permanence-authored file at that path
before overwriting (e.g. check for the `installed-from:` marker/managed-by comment before
clobbering).

---

### 5. Antigravity/Devin/Cursor's `wire` scripts don't check for `python3` before using it — a real regression from Claude Code's own binding, the one they were modeled on

**Citations:**
- `runtime/bindings/claude-code/wire:46` — `if command -v python3 >/dev/null 2>&1; then` ... (line 85) `else` prints a full manual-config snippet
- `runtime/bindings/antigravity/wire:21` and `:88`, `runtime/bindings/devin/wire:24` and `:100`,
  `runtime/bindings/cursor/wire:18` and `:71` — all six of these `if ! python3 - ... <<'PY'` calls
  have no preceding `command -v python3` check anywhere in any of the three files.

Claude Code's own `wire` explicitly detects a missing `python3` and, instead of just failing,
prints the exact JSON snippet the user needs to paste in by hand
(`runtime/bindings/claude-code/wire:85-94`). The three newer bindings skip this: on a machine
without `python3` on `PATH`, `python3 - ... <<'PY'` fails with a raw "command not found" from the
shell itself (not a friendly message), `WIRE_FAILED=1` is set, and the script's own
"FAILED to configure automatically — add the hooks by hand (**see message above**)" text
(`runtime/bindings/antigravity/wire:68`, `runtime/bindings/devin/wire:78`,
`runtime/bindings/cursor/wire:61`) references a helpful message that was never actually printed.
The same gap exists a second time in each file's Skills-translation step
(`antigravity/wire:88`, `devin/wire:100`, `cursor/wire:71`).

This is exactly the kind of "has one drifted and introduced a different (possibly worse)
approach" the review brief asked about — three of four non-Claude-Code bindings share one
(worse) pattern, diverging from the binding they structurally mirror in every other respect.

**Failure scenario:** a user on a machine with Antigravity/Devin/Cursor installed but no
`python3` (plausible — these are non-Python tools; `python3` isn't a hard dependency of any of
them) runs `install.sh`, sees "FAILED to configure automatically (see message above)" with no
actionable message above it, and has to reverse-engineer the JSON shape themselves from reading
the wire script's source, unlike a Claude Code user in the same situation.

**Suggested fix:** add the same `command -v python3` guard + manual-snippet fallback used in
`claude-code/wire:46-94` to the other three bindings' `wire` scripts (both call sites each).

---

### 6. Orphaned Skills/commands are never cleaned up — re-running `wire` doesn't converge to the current command set, only ever grows it

**Citations:** `runtime/bindings/antigravity/wire:113-135`, `runtime/bindings/devin/wire:125-147`,
`runtime/bindings/cursor/wire:96-119` (each iterates `os.listdir(cmd_src)` and writes/overwrites a
matching `skill_dir`, but never enumerates `skills_dst` to remove an entry with no matching
source file); `runtime/bindings/claude-code/wire:25-33` has the identical gap for
`$CMD_DST/*.md`.

If a command is ever renamed or removed from `runtime/commands/`, every machine that previously
ran `wire` keeps the old `SKILL.md`/command file forever — `wire` only ever adds/refreshes, never
deletes. This directly bears on the review's idempotency question: re-running `wire` on an
already-wired install does *not* converge to "matches what's currently in `runtime/commands/`" —
it converges to "superset of everything ever shipped, plus the current set." This is a
pre-existing pattern (already true of `claude-code/wire`'s commands loop before this diff), but
this diff triples the surface area by replicating the same gap into three new Skills directories
without addressing it.

**Failure scenario:** a future Permanence release renames or drops a command; existing installs
silently keep offering the stale one from `~/.claude/commands/`, `~/.gemini/config/skills/`,
`~/.config/devin/skills/`, and `~/.cursor/skills/` indefinitely, with no error and no mechanism
to detect the drift.

**Suggested fix (not urgent, but worth a tracked follow-up):** have each `wire` script diff
`skills_dst`/`CMD_DST` against the current `runtime/commands/*.md` list and remove entries with
no matching source, guarded to only ever delete files that carry the "managed by Permanence"
marker (so it never touches a user's own same-named content).

---

### 7. `_perma_block_merge`'s marker-mismatch check doesn't handle multiple begin/end pairs correctly — theoretical, not reachable via this diff's own usage

**Citation:** `runtime/lib/block-merge.sh:16-29`

```
16    if [ -f "$dst" ] && grep -q '<!-- perma:begin' "$dst" 2>/dev/null; then
17      begins=$(grep -c '<!-- perma:begin' "$dst")
18      ends=$(grep -c '<!-- perma:end -->' "$dst")
19      begin_line=$(grep -n '<!-- perma:begin' "$dst" | head -1 | cut -d: -f1)
20      end_line=$(grep -n '<!-- perma:end -->' "$dst" | head -1 | cut -d: -f1)
21      if [ "$begins" -ne "$ends" ] || [ -z "$end_line" ] || [ "$end_line" -le "$begin_line" ]; then
...
26      awk -v s="$src" '
27        /<!-- perma:begin/ {while ((getline line < s) > 0) print line; close(s); skip=1; next}
28        /<!-- perma:end -->/ {skip=0; next}
29        !skip {print}' "$dst" > "$dst.tmp" && mv "$dst.tmp" "$dst"
```

The validation at line 21 only compares *counts* (`begins -ne ends`) and the position of the
*first* begin/end pair. If a file somehow ends up with two well-formed, correctly-ordered
begin/end pairs (`begin1...end1...begin2...end2`), this check passes (`begins == ends == 2`,
`end_line`(first) > `begin_line`(first)) — but the `awk` splice at line 26-29 uses a single
boolean `skip` flag, not a counter, so it re-injects `$src`'s content at *every* begin marker it
encounters, doubling the injected block.

**Verified:** in this codebase's actual usage, every destination file (`CLAUDE.md`, `GEMINI.md`,
each global `AGENTS.md`) only ever receives one block from one source via `_perma_block_merge`,
so this path isn't reachable through any code in this diff — it would require a user (or a bug
elsewhere) to hand-corrupt the destination file into having two separate marker pairs first. Low
severity, flagged for completeness per the idempotency question in the review brief, not because
I found a live trigger for it.

**Suggested fix:** track nesting/count with a counter rather than a boolean, or add an explicit
check that only one begin/end pair exists at all (reject 2+ pairs the same way a mismatched count
is rejected today).

---

### 8. Minor: `_perma_block_merge` reports success even when it did nothing, if `$src` is missing

**Citation:** `runtime/lib/block-merge.sh:14` — `[ -f "$src" ] || return 0`

Every call site (`runtime/install.sh:58`, `runtime/bindings/claude-code/wire:39`,
`runtime/bindings/antigravity/wire:77`, `runtime/bindings/devin/wire:89`) prints a "block
refreshed" success message purely because the function returned 0 — which also happens on a
silent no-op when the source block file is missing from the repo (e.g. `runtime/claude-md-block.md`
deleted or a typo in the path). Would only trigger on repo corruption, not a real user path — low
severity, noted for completeness.

---

### 9. CI does not exercise the actual `wire` success path for Antigravity/Devin/Cursor — only their `detect`-absent path is tested

**Citation:** `.github/workflows/ci.yml:394-422` (three "Verify ... detect correctly reports
absent" steps) vs. `.github/workflows/ci.yml:374-392` (the one step that verifies actual wired
*content* — CLAUDE.md, settings.json — and it's Claude-Code-only).

This isn't a bug, and it's an understandable limitation (the CI runners don't have
`agy`/`devin`/`cursor-agent` installed, so `detect` correctly and only ever returns 1 there,
meaning `wire` never runs in CI for these three). But it means the JSON-merge idempotency,
backup-on-write, and Skills-translation logic in `antigravity/wire`, `devin/wire`, and
`cursor/wire` have zero automated regression coverage — their correctness rests entirely on the
one-time live-fire testing described in the design docs and commit messages, which (per the
review's own instruction) I can't verify from this repo and haven't treated as Verified. A future
change to any of these three `wire` scripts could silently break the JSON merge or the Skills
translation and CI would stay green.

**Suggested fix (optional):** the install-matrix job already fakes a scratch git checkout — it
could similarly fake a minimal `agy`/`devin`/`cursor-agent` shim on `PATH` (even a no-op script)
to get `detect` to pass and `wire` to actually run, then assert on the resulting `hooks.json`/
`config.json` content the same way the Claude Code step already does.

---

## Verified / Unknown ledger

**Verified (read the actual code/docs in this repo, or ran a command against it):**
- `runtime/lib/block-merge.sh` full content, backup-before-write and refuse-on-mismatch logic
- `runtime/install.sh` full content, including the bindings-discovery loop and `INSTALL_FAILED` tracking
- `runtime/bindings/{claude-code,antigravity,devin,cursor}/{detect,wire}` full content
- `runtime/bindings/antigravity/{pre-invocation-hook.sh,pre-tool-use-hook.sh}` full content
- `runtime/bindings/devin/{session-start-hook.sh,user-prompt-submit-hook.sh}` full content
- `runtime/bindings/cursor/{session-start-hook.sh,stop-hook.sh}` full content
- `.github/workflows/ci.yml` full content, all jobs
- All PY heredocs in the four `wire` scripts close on an unindented `PY` line (matches the CI
  lint job's extraction `awk` pattern — no blind spot there)
- `git log --oneline -- README.md`, `-- design/harness-binding-mechanism.md` — confirmed which
  commits last touched each file, and that later commits (`9330252`, `b86db90`, `1a43d4c`) shipped
  functionality those files still describe as unbuilt
- `runtime/session-load.sh` is unchanged by this diff (confirmed via `git diff main...branch --
  runtime/session-load.sh` returning empty) — the `/tmp/.perma-loaded-*` marker convention it uses
  predates this branch; `antigravity/pre-invocation-hook.sh` reuses the same pattern, not a new
  invention
- The design docs' claimed file paths (`~/.gemini/config/hooks.json`, `~/.config/devin/config.json`,
  `~/.cursor/hooks.json`, and their respective Skills directories) match exactly what the `wire`
  scripts actually write to — no drift found there
- `runtime/update.sh`'s diff (self-re-exec-on-self-update fix) — read in full; logic is sound and
  well-commented, not a primary target so not exhaustively adversarially tested
- CHANGELOG.md's [1.4.0] entry — read in full, cross-referenced against the commit history it summarizes

**Unknown (not verifiable from this repo alone, not claimed as Verified anywhere in this review):**
- Whether Antigravity/Devin/Cursor's hook JSON payload shapes (e.g. `conversationId`,
  `workspacePaths`, `loop_count`, `session_id`) actually match what those tools send on stdin in
  real use — the code and design docs claim this was live-fire tested outside this repo; I did not
  and could not re-verify that against a real running instance of any of these tools
- Whether the `.perma-bak` backup files these scripts create are ever cleaned up or grow
  unbounded across repeated installs — not addressed by any script I read, not flagged as a
  finding since it's a minor disk-space concern, not a data-safety one (the point of a backup is
  to persist, so this may be intentional)
