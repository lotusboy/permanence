# Pass 2 — Focused Verification (Adversarial) — Harness Binding Mechanism

Reviewer: fresh pass, no prior context, no access to Pass 1. Target: `git diff main...add-roadmap-and-adapter-designs` (33 files, ~2,700 insertions, 41 commits) in `/Users/lotusboy/workspaces/permanence`. Every claim below marked "verified" was actually executed against extracted or reproduced code in an isolated scratch directory — never touching the real `$HOME` install — before being written down; the exact repro commands are described inline so they can be re-run.

## CRITICAL — data loss possible with no backup path

**`runtime/lib/block-merge.sh:30-38`, the "no existing marker" branch, can silently destroy an existing standing-instruction file's real content, with zero backup, if the read of that file fails for any reason at write time.**

```
30	  else
31	    # No existing marker: this can only ever ADD content (prepend), never destroy any — no
32	    # backup needed, because nothing here can lose data.
...
38	    { cat "$src"; echo; cat "$dst" 2>/dev/null || true; } > "$dst.tmp" && mv "$dst.tmp" "$dst"
39	  fi
```

This branch runs for every first-ever merge into `CLAUDE.md` (`runtime/bindings/claude-code/wire:39`), `AGENTS.md` (`runtime/install.sh:56-63`, four call sites), `GEMINI.md` (`runtime/bindings/antigravity/wire:77`), and Devin's `AGENTS.md` (`runtime/bindings/devin/wire:89`) — i.e. every real user's first install, for every binding, the very moment it matters most.

The comment's safety claim ("nothing here can lose data") assumes `cat "$dst"` always succeeds when `$dst` exists with real content. It doesn't have to: `2>/dev/null || true` converts *any* read failure — a permission oddity, an ACL that allows write but not read, a transient I/O/NFS glitch, or a same-second race where a concurrent process is rewriting `$dst` between this function's own marker-peek (line 16) and this `cat` (line 38) — into "the file was empty." The subsequent `mv` then unconditionally overwrites `$dst` with just the new block, discarding the real prior content forever. There is no `cp "$dst" "$dst.bak"` anywhere in this branch, unlike the marker-found branch three lines above it (line 25), which does back up first.

**Verified live** (scratch dir, not the real repo):
```
$ echo "IMPORTANT USER CONTENT THAT MUST NOT BE LOST" > dst_test.md
$ chmod 000 dst_test.md   # simulate a read failure
$ { cat src_test.md; echo; cat dst_test.md 2>/dev/null || true; } > dst_test.md.tmp && mv dst_test.md.tmp dst_test.md
$ cat dst_test.md
src content
```
The original line is gone. No backup file was ever created for it.

**Fix**: back up unconditionally before this write too (`[ -f "$dst" ] && cp "$dst" "$dst.perma-bak"`, mirroring line 25), or fail closed like the mismatched-marker branch does when `cat "$dst"` returns non-zero instead of swallowing it with `|| true`.

---

## BLUF

The idempotent-merge helper this whole binding mechanism is built on has a real, verified data-loss gap in its "no existing marker" path (above), and its success/failure signalling is unreliable in three more independently-verified ways: it reports success when it silently did nothing (missing source file), all four JSON-hook-merge wire scripts crash uncaught on a validly-parsed-but-wrong-shaped config file instead of the "warn-and-skip" behaviour the design doc claims, and the three newer bindings' Skills-translation step lets one unreadable command file take down every other command's translation instead of isolating the failure per-file as its own `try/except` implies it does. `install.sh`'s discovery loop also cannot tell "harness not installed" apart from "this binding's `detect` script is broken," so a broken binding fails completely invisibly. None of these five are covered by the new CI matrix, which only tests the "wire returns 1" happy-failure path.

---

## Findings, most severe first

### 1. `_perma_block_merge` reports success when it did nothing — the standing-instruction file silently never gets written

`runtime/lib/block-merge.sh:14`:
```
14	  [ -f "$src" ] || return 0
```
If the block-source template file is missing (a stale/partial checkout, a case-sensitivity mismatch, or — concretely, given this very PR's own `update.sh` history of adding new tracked paths that older installs' `PATHS` array didn't cover yet — a `*-block.md` file that a future release adds but an older `update.sh` never fetched), the function returns `0` having done **nothing at all** — no write, no backup, no warning.

Every caller treats that `0` as "the merge happened":
- `runtime/bindings/claude-code/wire:39-41`: `if _perma_block_merge "$CMD_MD" "$BLOCK_SRC"; then echo "  CLAUDE.md: Permanence block refreshed"; fi`
- `runtime/install.sh:56-58` (`merge_agents_block`, used at lines 60-63 for four separate `AGENTS.md` paths)
- `runtime/bindings/antigravity/wire:77-79` (`GEMINI.md`)
- `runtime/bindings/devin/wire:89-91` (Devin's `AGENTS.md`)

So the install prints "CLAUDE.md: Permanence block refreshed" (or the equivalent) even though the file was never touched and the standing instruction was never installed.

**Verified live**:
```
$ source runtime/lib/block-merge.sh
$ _perma_block_merge "dst2.md" "nonexistent-src.md" && echo "REPORTED SUCCESS"
REPORTED SUCCESS
$ ls dst2.md
ls: dst2.md: No such file or directory
```

This is not a cosmetic bug. `SPEC.md:61-65` names the standing-instruction capability explicitly as *"the capability whose absence is silent... nothing raises an error, and the failure surfaces only as an empty LOG.md weeks later. **Verify this one first, not last.**"* This exact code path is the one place the mechanism could actually verify that and doesn't — it converts a real failure into a false "refreshed" message, which is precisely the failure mode SPEC.md warns about.

**Fix**: have `_perma_block_merge` return a distinct non-zero (or print its own warning) when `$src` is missing, and have callers not print "refreshed" on that path.

### 2. All four JSON-merge wire scripts crash uncaught on a validly-parsed but wrong-shaped config file, instead of the claimed graceful "checks presence before writing" behaviour

`design/claude-code-binding.md:40-43` explicitly claims the settings.json merge is *"a Python3 heredoc that checks presence before writing (idempotent), backs up the file before any change."* The `try/except` around `json.load` only catches genuinely-invalid JSON (line 52-57 pattern, repeated in all four wire scripts). It does **not** protect against a file that parses fine but has one of Permanence's own keys already occupied by the wrong *type* — e.g. `"hooks": {"SessionStart": "not-a-list"}` (plausible if some other tool, or a hand-edit, ever set it that way).

`runtime/bindings/claude-code/wire:63`:
```
63	ss = data.setdefault("hooks", {}).setdefault("SessionStart", [])
```
`setdefault` only supplies a default when the key is *absent* — if `"SessionStart"` already exists as a string, `ss` becomes that string, and the later `ss.append(...)` (line 66/73) throws `AttributeError: 'str' object has no attribute 'append'`.

**Verified live** (exact repro of this code path against a crafted `settings.json`):
```
$ cat settings.json
{"hooks": {"SessionStart": "not-a-list"}}
$ python3 - settings.json /tmp/fakeperma <<'PY'
[... claude-code/wire's exact settings.json-merge logic ...]
PY
Traceback (most recent call last):
  File "<stdin>", line 19, in <module>
AttributeError: 'str' object has no attribute 'append'
```
The exception happens *before* the `if changed:` write block, so it fails safe (no corruption) — but it exits via an unhandled traceback, not the clean "present but unparseable — NOT touched" message the same script gives for actually-invalid JSON three lines earlier (line 56). The outer `if ! python3 -...; then WIRE_FAILED=1; fi` (lines 81-84) does catch the non-zero exit and mark the wire failed, so this doesn't lie about success — but it violates the explicit "checks presence" claim and gives the user a raw traceback instead of a diagnosis.

The identical `setdefault`/`.get(...) or default` pattern, and identical vulnerability, exists in:
- `runtime/bindings/claude-code/wire:60-62` (`additionalDirectories`, same class: a pre-existing non-list value there breaks `ad.append`)
- `runtime/bindings/antigravity/wire:38-43` (`pi = data.get("perma-pre-invocation") or {}` then `pi.get("PreInvocation")` — breaks if that key is a truthy non-dict) and `:45-57` (`perma-pre-tool-use`)
- `runtime/bindings/devin/wire:43-54` (`SessionStart`) and `:56-67` (`UserPromptSubmit`)
- `runtime/bindings/cursor/wire:38-43` (`sessionStart`) and `:45-50` (`stop`)

Antigravity, Devin, and Cursor namespace their own keys (`perma-pre-invocation`, etc.) specifically so *other tools'* entries are never touched (a real, good mistake-proofing decision, confirmed by reading the comments) — but that namespacing doesn't protect against the file being malformed under Permanence's *own* key from a previous partial/failed run, or hand-editing.

**Fix**: wrap the shape-assumption in a `try/except (AttributeError, TypeError)` that falls back to the same "present but unparseable" warn-and-skip message already used for JSON-parse failures, in all seven vulnerable spots.

### 3. Skills-translation: one bad command file kills every other command's translation, in three bindings

`runtime/bindings/antigravity/wire:114-132`, `runtime/bindings/devin/wire:126-144`, `runtime/bindings/cursor/wire:97-116` all contain the identical loop (cursor's version shown, line numbers per-file differ slightly):
```
97	for fname in sorted(os.listdir(cmd_src)):
98	    if not fname.endswith(".md"):
99	        continue
100	    name = fname[:-3]
101	    src_path = os.path.join(cmd_src, fname)
102	    content = open(src_path).read()          # <-- NOT inside the try/except below
103	    description = extract_description(content)
104	
105	    skill_dir = os.path.join(skills_dst, name)
106	    try:
107	        os.makedirs(skill_dir, exist_ok=True)
...
116	        failed.append(name)
```
The `try/except` (lines 106-116 in cursor's copy) visually reads as per-file fault isolation — a failure writing *this* skill is caught and logged, and the loop moves on to the next file. But `content = open(src_path).read()` sits **outside** that block. Any read failure on any single command file (invalid UTF-8, a permission bit, a mid-loop deletion) raises an uncaught exception that aborts the entire `for` loop immediately — every command file not yet processed (alphabetically after the bad one) never gets attempted, regardless of how well-formed it is.

**Verified live**: 3 files in a scratch `cmds/` dir — `bad.md` (contains invalid UTF-8 bytes), `good.md`, `zzz-good2.md`. Sorted order processes `bad.md` first:
```
$ python3 [exact skills-translation loop from cursor/wire] cmds skills_out
Traceback (most recent call last):
  ...
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff in position 25: invalid start byte
$ ls skills_out/
(empty — good.md and zzz-good2.md were never even attempted)
```
Zero of two genuinely-fine commands were translated. This does correctly propagate as a wire failure (`sys.exit(1)` path → `WIRE_FAILED=1`), so it isn't silent — but the blast radius is every Skill for that harness, not the one bad file, and it affects three bindings simultaneously from one shared bug (this loop is triplicated verbatim across antigravity/devin/cursor, not factored into a shared helper the way `block-merge.sh` was — the exact "duplicating this function was the risk" pattern `block-merge.sh`'s own header comment warns against, reintroduced here).

**Fix**: move `content = open(src_path).read()` inside the existing `try:` block (one-line fix, ×3 files).

### 4. `install.sh`'s discovery loop can't tell "harness not installed" from "this binding is broken," and never says so

`runtime/install.sh:74-88`:
```
74	for b in "$PERMA/runtime/bindings/"*/; do
75	  [ -d "$b" ] || continue
76	  name="$(basename "$b")"
77	  [ -x "$b/detect" ] || continue
78	  if "$b/detect" >/dev/null 2>&1; then
```
Two adversarial cases the prompt asked about, both real:

- **`detect` missing or not executable** (line 77): silently `continue`s — no output line at all for that binding, not even "no wire script yet." Step 1 (line 21) does `chmod +x ... "$PERMA/runtime/bindings/"*/detect ...` first, which covers the common case, but that chmod's own errors are suppressed (`2>/dev/null`) and unchecked — if it fails for any one binding (e.g. a read-only mount, a third-party binding added without following the convention), that binding vanishes from the entire install with zero trace, and `INSTALL_FAILED` is never set.
- **`detect` exits with an unexpected/crashed code** (line 78): `if "$b/detect" ...; then` treats *any* non-zero exit identically to the intentional "not applicable, exit 1" signal. A `detect` script that crashes for the wrong reason (a typo, a missing intermediate command, permission denied on something it checks) is indistinguishable from "this tool genuinely isn't installed" — the bug in `detect` itself can never surface as an install failure, only as a binding that mysteriously never gets wired.

The CI `install-matrix` job (`.github/workflows/ci.yml:450-462`) only tests the case where `wire` itself is swapped for a script that `exit 1`s *after* `detect` already succeeded — it never exercises a missing/non-executable/crashing `detect`, so this gap has no test coverage.

**Fix**: distinguish "no `detect`/not executable" (log it, don't just `continue` silently) from "`detect` said no" (exit 1, the documented contract) — e.g. treat any `detect` exit code other than 0 or 1 as itself a reportable failure.

### 5. Process-compliance is inconsistent across bindings: `claude-code/wire`'s own header comment admits it doesn't meet the design doc's stated bar

`design/harness-binding-mechanism.md:77-78` states the `wire` contract in the doc every binding is supposed to implement: *"Exit 0 on success, including a no-op 'already wired'; non-zero on a real failure, which `install.sh` surfaces rather than swallowing."*

`runtime/bindings/claude-code/wire:8-12` (its own header):
```
8	# Exit code: only the settings.json merge failing is treated as a real wire failure (the one
9	# genuine hard-failure path install.sh already tracked before this migration). A command-copy
10	# failure is reported but historically wasn't fatal to the overall install either — preserved
11	# as-is rather than tightening behavior nobody asked for.
```
And indeed, the commands-copy loop (`runtime/bindings/claude-code/wire:24-33`) never sets `WIRE_FAILED` on a `cp` failure — only echoes "$name — FAILED to copy" per file and moves on. Compare this to the *analogous* step in the other three bindings — Skills translation (finding #3 above) — which **does** set `WIRE_FAILED=1` on any per-file failure. Same shape of step (copy/translate N files from `runtime/commands/`), two different failure-propagation policies, by the newer bindings' own author's design intent (per comment) rather than an oversight — but it means "verify it, don't assume consistency" (as this pass was asked to do) surfaces a real inconsistency: a partial command-copy failure in Claude Code's own binding — arguably the harness every install depends on most — is the one case in the whole mechanism that's explicitly, deliberately swallowed, contradicting the shared design doc's own stated contract for what `wire` must do.

### 6. Mismatched `perma:begin`/`perma:end` marker WARN never reaches any wire script's exit code — "wired" can mean "the standing instruction was left completely untouched"

`runtime/lib/block-merge.sh:21-23` correctly refuses to touch a file with a mismatched marker count and returns `1`. But every call site swallows that return value without checking it:
```
39	if _perma_block_merge "$CMD_MD" "$BLOCK_SRC"; then
40	  echo "  CLAUDE.md: Permanence block refreshed"
41	fi
```
(`runtime/bindings/claude-code/wire:39-41`; identical pattern at `runtime/install.sh:56-58`, `runtime/bindings/antigravity/wire:77-79`, `runtime/bindings/devin/wire:89-91`.) There is no `else` branch anywhere. `claude-code/wire`'s own header (`:11-12`) calls this "a deliberate soft warning, never a wire failure" — so this is intentional, not an oversight — but the practical effect is: a user whose `CLAUDE.md` has a stray/duplicated `perma:begin` marker gets a WARN printed to the terminal, and then `install.sh` still prints `binding: claude-code wired`, with `INSTALL_FAILED` staying `0`. Given finding's SPEC.md citation above (§3, question 3 — "the capability whose absence is silent... verify this one first"), a soft warning that doesn't affect the overall "done." vs "done, WITH FAILURES" summary line is exactly the kind of signal that's easy to miss scrolling past a long install log.

**Fix (if the soft-warning behavior stays intentional)**: at minimum have `install.sh`'s closing summary separately track and surface "N standing-instruction files need manual attention," rather than folding successfully into the same "wired" line as everything else.

### 7. Malformed YAML frontmatter in a `runtime/commands/*.md` file silently produces a garbage Skill description, not a rejection

`extract_description()` (identical in `runtime/bindings/antigravity/wire:93-111`, `runtime/bindings/devin/wire:105-123`, `runtime/bindings/cursor/wire:76-94`) uses a regex, not a YAML parser, to find the closing `---` of frontmatter:
```
94	    m = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
```
If a command file's frontmatter is missing its closing `---` (a real, plausible authoring mistake — the exact "malformed YAML frontmatter" case this pass was asked to check), `m` is `None`, and the code falls through to its plain-text fallback (lines 105-110 in cursor's copy), which just returns the first non-blank, non-`#` line of the file. Since the file *starts* with `---\n`, that first line **is** the literal delimiter `---` itself.

**Verified live**:
```python
>>> extract_description("---\nname: broken-cmd\ndescription: This command has broken frontmatter\n\nSome body text here.\n")
'---'
```
The resulting `~/.gemini/config/skills/<name>/SKILL.md` (or the Devin/Cursor equivalent) ships with `description: "---"` — silently breaking that command's description-matched invocation for that harness, with no warning printed anywhere in the wire script's output.

### 8. Antigravity's once-per-conversation dedup marker is a non-atomic check-then-act — a real double-delivery race under concurrent `PreInvocation` firing

`runtime/bindings/antigravity/pre-invocation-hook.sh:24-31`:
```
24	if [ "$CONV_ID" != "noconv" ]; then
25	  MARKER="/tmp/.perma-loaded-agy-$(printf '%s' "$CONV_ID" | tr -c 'A-Za-z0-9' _)"
26	  if [ -f "$MARKER" ]; then
27	    echo '{}'
28	    exit 0
29	  fi
30	  touch "$MARKER"
31	fi
```
The script's own header (lines 8-10) states `PreInvocation` "fires more than once per turn (invocationNum 0, 1, ... within a single exchange, live-confirmed)" — precisely the "what if this runs twice" scenario this pass was asked to probe. `[ -f "$MARKER" ]` then `touch "$MARKER"` is a classic TOCTOU: if two invocations for the same `conversationId` are dispatched close enough together (the header doesn't rule out concurrency, only documents multiple sequential-looking firings), both can observe the marker absent before either creates it, and both proceed to inject the orientation message — a double-delivered `injectSteps` payload into the same turn. Low-severity in isolation (redundant context, not corruption), but it is a real, unaddressed race exactly where the header comment already flags repeated firing as a known behavior to guard against.

**Fix**: use an atomic marker primitive (`mkdir "$MARKER" 2>/dev/null` or `set -C; > "$MARKER"`, both atomic create-if-absent) instead of test-then-touch.

### 9. No `python3` availability guard in any of the seven runtime hook-translator scripts, unlike the install-time wire scripts

Every wire script that runs at install time checks `command -v python3` before depending on it (e.g. `runtime/bindings/claude-code/wire:46`, with a documented manual-entry fallback at lines 85-94 if it's absent). None of the hook scripts that run on every session/turn do the same, despite depending on `python3` multiple times each: `runtime/bindings/antigravity/pre-invocation-hook.sh:16-21,38-44,57-60`; `runtime/bindings/antigravity/pre-tool-use-hook.sh` (no python3, fine); `runtime/bindings/devin/session-start-hook.sh:10,20-23`; `runtime/bindings/devin/user-prompt-submit-hook.sh:11-16,20,30-33`; `runtime/bindings/cursor/session-start-hook.sh:13-19,22,32-35`; `runtime/bindings/cursor/stop-hook.sh:16-21,29-35,46-56`.

Most of these degrade gracefully via the `[ -n "$X" ] || X="fallback"` pattern already in place for the *earlier* python3 calls in each script (confirmed correct on inspection) — but each script's *final* step, which builds the actual JSON response object Antigravity/Devin/Cursor reads back, has no equivalent fallback (e.g. `antigravity/pre-invocation-hook.sh:57-60`, `cursor/stop-hook.sh:46-56`). If `python3` is present at install time (so `wire` succeeds) but later becomes unavailable on that machine (uninstalled, a PATH change, a sandboxed/ephemeral execution environment the hook runs in that differs from the interactive shell), that final step silently produces empty stdout instead of `{}`. Given `pre-tool-use-hook.sh`'s own header states *"a bare `{}` (or any malformed response) fails closed and blocks the tool call"* for that specific hook, an *empty* (not even `{}`) response from a sibling hook script in the same binding is an untested, unspecified condition.

### 10. Guard coverage for malformed markers is incomplete: overlapping (improperly nested) `perma:begin` pairs pass the mismatch check and produce duplicated content

`runtime/lib/block-merge.sh:17-23` only checks that the *count* of begins equals the count of ends, and that the *first* end comes after the *first* begin. It does not verify the markers are non-overlapping. Cleanly-separated multiple pairs work correctly (verified — two independent begin/end blocks with content between them were each correctly, independently refreshed, with the middle content preserved). But an overlapping/improperly-nested case slips through:

**Verified live** — `dst4.md` containing `begin1, begin2, old inner, end1, end2` (begins=2, ends=2, first end after first begin → passes the check):
```
$ _perma_block_merge dst4.md src4.md; echo "exit: $?"
exit: 0
$ cat dst4.md
<!-- perma:begin -->
NEW CONTENT
<!-- perma:end -->
<!-- perma:begin -->
NEW CONTENT
<!-- perma:end -->
```
The content is duplicated rather than flagged, because the `awk` splice (lines 26-29) triggers its inject-and-skip action on *every* line matching the begin pattern, not just the first. This does go through the branch that creates a `.perma-bak` first (line 25), so it's recoverable, unlike Finding CRITICAL above — but it's a real gap in what the guard actually catches relative to what its own comment (`block-merge.sh:2-6`, "the safety net... must not drift") implies it catches. Low real-world likelihood (requires the file to already be in a malformed overlapping state), but genuine and reproducible.

### 11. No locking anywhere in the merge mechanism — mostly self-healing, but the CRITICAL finding above is a second way in

None of `block-merge.sh`, `install.sh`, or any `wire` script takes a lock before reading-then-writing its target file. For the JSON-hook merges (settings.json, hooks.json, config.json) this is low-risk in practice: two concurrent runs both compute the identical idempotent addition, so the final content converges regardless of which write wins the race, even without a lock. For `block-merge.sh`'s no-marker branch specifically, though, a concurrent process modifying `$dst` in the window between this function's marker-peek (`block-merge.sh:16`) and its later `cat "$dst"` (`block-merge.sh:38`) is a second, independent way to trigger the exact same silent-data-loss path as the CRITICAL finding above — not just a hypothetical read-permission edge case, but a genuine "two installs run at once" scenario the prompt asked to check for.

### 12. Minor: single-generation backups

Every `.perma-bak` (`block-merge.sh:25`, and every `*.perma-bak` written by the four JSON-merge wire scripts) is overwritten on each real change. Only the immediately-prior state is ever recoverable, not a history — fine for the common case, but worth knowing before relying on it to undo something from two installs ago.

---

## Verified / Unknown ledger

**Verified (executed against extracted or reproduced code, in an isolated scratch dir):**
- `block-merge.sh` no-marker branch discards existing content with no backup when the read fails (CRITICAL).
- `_perma_block_merge` returns 0 and prints nothing when `$src` is missing, while every caller reports "refreshed" (Finding 1).
- `claude-code/wire`'s settings.json merge throws an uncaught `AttributeError` on a validly-parsed-but-wrong-shaped `hooks.SessionStart` value (Finding 2), traced identically into `antigravity/wire`, `devin/wire`, `cursor/wire`.
- The triplicated Skills-translation loop in `antigravity/wire`/`devin/wire`/`cursor/wire` aborts entirely on one unreadable command file, translating zero of the remaining valid files (Finding 3).
- Malformed frontmatter (missing closing `---`) produces the literal description `"---"` (Finding 7).
- Two cleanly-separated `perma:begin`/`perma:end` pairs are each correctly, independently refreshed with the content between them preserved (checked while investigating Finding 10 — this is *not* a bug, noted for completeness since it was a live hypothesis before testing disproved it).
- Two overlapping/improperly-nested `perma:begin` pairs pass the mismatch check and produce duplicated content, recoverable via the `.perma-bak` that branch does create (Finding 10).
- All hook-translator scripts (`pre-invocation-hook.sh`, `session-start-hook.sh`, `user-prompt-submit-hook.sh`, `stop-hook.sh`) correctly wrap their `json.load(sys.stdin)` calls in `try/except` and fall back to `{}` — confirmed by code inspection across all instances — so malformed/non-JSON stdin is handled gracefully everywhere it's parsed. Credit where due.
- All hook-translator scripts check `[ -d "$PERMA" ]` before doing anything else — confirmed present in every one.
- `install.sh`'s `INSTALL_FAILED` tracking genuinely does gate the final "done." vs "done, WITH FAILURES" line, and CI (`ci.yml:450-462`) does verify this for the one case it tests (an already-detected binding whose `wire` exits 1).

**Unknown / not independently verified (reasoned from code reading only, not executed):**
- Whether Antigravity's real `PreInvocation` event can actually fire concurrently for one `conversationId` (Finding 8) — the header comment only confirms multiple *sequential-looking* firings (`invocationNum 0, 1, ...`), not true concurrency; I could not launch real Antigravity to confirm.
- Whether a hook script producing empty stdout (Finding 9's failure mode) is actually treated as "fails closed" by Antigravity/Devin/Cursor the way `pre-tool-use-hook.sh`'s header states for its own specific case — not live-tested against any of the three real tools.
- Whether `chmod +x` (`install.sh:21`) can realistically fail in a way that leaves a `detect` script non-executable on a real user machine (vs. only a contrived read-only-mount scenario) — plausible but not reproduced.
- Design-doc and `docs/TOOL-SUPPORT.md` prose claims not directly exercised by the code paths above were spot-checked for internal consistency only, not fully cross-verified line-by-line against every binding's design doc (the prompt scoped these as secondary/spot-check).

---

## What a purely structural/completeness review would likely miss

These are specifically the findings that only surface by actually running the code against crafted adversarial input, not by reading it for organization/SOLID/completeness:

1. **The CRITICAL finding** — the code *reads* as safe ("no backup needed, because nothing here can lose data" is stated as a design rationale, and structurally the branch does look like a harmless prepend). Only forcing the `cat` to fail (via `chmod 000` in the repro) reveals that the safety argument has an unstated assumption baked into it. A structural review would see "prepend, not overwrite" and move on.
2. **`_perma_block_merge` reporting success on a no-op** (Finding 1) is invisible from reading the success path alone — the function's contract (verified vs. unverified success) only breaks under a missing-file precondition a structural pass has no particular reason to manufacture.
3. **The JSON-shape crash** (Finding 2) requires constructing a file that is valid JSON but wrong-shaped under an existing key — a completeness review checking "is there a try/except around the JSON parse" would see one and mark it handled, without noticing the exception surface extends past the parse into every subsequent `.setdefault()`/`.get()` chain.
4. **The Skills-translation blast radius** (Finding 3) looks, on a structural read, like exactly the fault-isolation pattern you'd want — a `try/except` per file inside a loop. Only actually feeding it a file that fails to `.read()` (not just fails to `.write()`) exposes that the isolation boundary is drawn one line too late.
5. **The garbage-description fallback** (Finding 7) requires actually feeding the parser malformed frontmatter; reading the regex alone, it looks like a reasonable lightweight frontmatter extractor with a sensible plain-text fallback.
6. **The overlapping-marker duplication** (Finding 10) required constructing a specific malformed pre-existing state and running the real `awk` script against it — the mismatch-detection code reads as sufficient (counts match, ordering checked) until tested against a case its own logic doesn't consider.
