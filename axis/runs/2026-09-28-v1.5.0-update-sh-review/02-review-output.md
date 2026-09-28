# v1.5.0 review — `update.sh`, `nightly-consolidate.sh`, `install.sh`, `session-start.sh`

Axes applied: Genba + Shoshin (verify against real code, read fresh) · Chaos Engineering + Andon
(break it, stop loud on data loss) · Poka-yoke (are the claimed guards actually in place).
Diff reviewed: `git diff ecbc5b9 v1.5.0` (tag `v1.4.0` → `v1.5.0`).

All reproductions below were run in a scratch directory
(`/private/tmp/claude-501/-Users-lotusboy-workspaces-permanence/38b41717-830d-4b71-a750-0f85a6e0da16/scratchpad/update-sh-review/`),
against fake "template" and "install" git repos built for this review, using an unmodified copy
of the real `runtime/update.sh` / `runtime/nightly-consolidate.sh` under test. No file in
`/Users/lotusboy/workspaces/permanence` or `~/permanence` was written to.

---

## 🛑 CRITICAL — data-loss defect found, live-reproduced (Andon stop)

`update.sh` silently destroys an owner's local customisation to a machinery file whenever the
template deletes that file, or renames it away, in the same release — with no "needs review" flag,
no warning in the dry-run, and no mention in the commit message. Full details and two independent
live reproductions immediately below.

## BLUF

The three specific CHANGELOG claims for `update.sh` — never deletes owner-added files, renames
land instead of being dropped, and a solely-owner-customised file is kept without flagging "needs
review" every run — all independently reproduced true, exactly as stated. The release's broader
framing, "upgrades that never touch what is yours," does not hold: when the *template itself*
deletes or renames a file the owner had customised, that customisation is discarded unconditionally
and silently, because the deletion path (unlike every other bucket added in this release) never
checks whether the owner touched the file. A second, independent defect (an unscoped `chmod +x`
leaves the tree dirty after every apply) blocks the very "resolve a conflict, then re-run" workflow
this release is built around. `nightly-consolidate.sh`'s new awake-gate and `install.sh`'s new
HH:MM parsing both held up under adversarial testing; one `role_lines()` edge case in
`session-start.sh` did not.

## Findings

### 1. CRITICAL — `update.sh` silently deletes an owner's customisation to a file the template still ships under a new or unchanged path

`runtime/update.sh:99-119` sorts every path with git status `D` into two buckets:

```
99   CHANGED_FILES=()
100  DELETED_FILES=()
101  KEPT_FILES=()
102  while IFS=$'\t' read -r status path; do
103    [ -n "${path:-}" ] || continue
104    if [ "$status" = "D" ]; then
...
111      if [ "$CURRENT" != "unknown" ] && git -C "$PERMA" cat-file -e "$CURRENT:$path" 2>/dev/null; then
112        DELETED_FILES+=("$path")
113      else
114        KEPT_FILES+=("$path")
115      fi
```

This check only asks "did the template ship this path at my recorded version?" It never asks "did
*I* change this path since my recorded version?" — the question every other bucket in this same
release (CONFLICTS/YOURS at `update.sh:137-147`) does ask. `DELETED_FILES` is then applied
unconditionally at apply time:

```
209  # Deletions always apply, unconditionally — see the note where DELETED_FILES is built above.
210  if [ "${#DELETED_FILES[@]}" -gt 0 ]; then
211    git -C "$PERMA" rm -q -- "${DELETED_FILES[@]}" 2>/dev/null || true
212  fi
```

The code comment at `update.sh:91-98` defends this as a deliberate choice ("if the template
removed it, it's removed on upgrade, customized or not... still visible either way, in the
'Changed machinery files' diff"). In practice the "Changed machinery files" line for a deleted
path is a bare `D  runtime/foo.sh` — visually identical whether the owner touched that file or
never opened it. Nothing distinguishes "template deletion of a file you never touched" from
"template deletion (or rename-away) of a file you spent time customising."

**Two live reproductions**

**(a) Template deletes a file the owner customised in place.**
Fixture: template ships `runtime/deleteme.sh` at `v1.0.0`; owner edits it locally to
`DM1_owner_customized_important_data` and commits; template deletes it at `v2.0.0`.

```
$ echo "DM1_owner_customized_important_data" > runtime/deleteme.sh && git commit -am "owner: customise deleteme.sh"
$ PERMA_DIR=$INSTALL bash runtime/update.sh --apply
...
✅ Machinery updated to v2.0.0 and committed; your streams are untouched. Start a fresh session so the new hooks load.
$ cat runtime/deleteme.sh
cat: runtime/deleteme.sh: No such file or directory
```

No mention of `deleteme.sh` anywhere in the dry-run's KEPT/YOURS/CONFLICTS sections. No "needs
review." The owner's edit is gone from the working tree; the commit message says only "your
streams are untouched" — true of streams, false of this customised machinery file.

**(b) Template renames a file the owner customised (without renaming it themselves).**
Fixture: template ships `runtime/rename_src.sh` at `v1.0.0`; owner edits it locally to
`RN1_owner_important_customization`; template renames it to `runtime/renamed_dst.sh` (with new
content `RN2`) at `v2.0.0` — the exact "renames instead of dropping them" scenario the CHANGELOG
claims to have fixed.

```
$ echo "RN1_owner_important_customization" > runtime/rename_src.sh && git commit -am "owner: customise rename_src.sh"
$ PERMA_DIR=$INSTALL bash runtime/update.sh --apply
...
✅ Machinery updated to v2.0.0 and committed; your streams are untouched.
$ cat runtime/rename_src.sh
cat: runtime/rename_src.sh: No such file or directory
$ cat runtime/renamed_dst.sh
RN2
```

The owner's customisation to the pre-rename file is discarded outright and silently replaced by
the template's own content under the new name. This is worse than "the rename never landed" (the
pre-v1.5.0 bug this release fixes) — it's "the rename landed and overwrote your edit with the
template's, with no flag."

Both cases are recoverable from the install's own git history (`git show HEAD~1:runtime/deleteme.sh`)
since the deletion goes through a real commit — this is not unrecoverable content loss — but it is
exactly the class of thing the Andon stop condition names: `update.sh` "silently deleting ... content
it claims to protect," with no distinguishing signal in the dry-run output and no `--apply`
confirmation step.

**Fix suggestion:** before adding a path to `DELETED_FILES`, run the same customisation check
already used for `CONFLICTS`/`YOURS` (`git diff --quiet "$CURRENT" HEAD -- "$path"`). If the owner
customised a path the template deleted or renamed away, route it into `CONFLICTS` (flagged, not
applied) rather than `DELETED_FILES` (applied unconditionally) — the multi-file-flat-list tradeoff
the in-code comment worries about already exists for ordinary conflicts and is treated as
acceptable there.

---

### 2. HIGH — every `--apply` leaves the working tree dirty via an unscoped `chmod +x`, blocking the very next `--apply`

`update.sh:233` and `update.sh:249`:

```
233  chmod +x "$PERMA/runtime/"*.sh "$PERMA/.githooks/"* 2>/dev/null
...
249  chmod +x "$PERMA/runtime/"*.sh "$PERMA/.githooks/"* 2>/dev/null
```

This glob matches **every** `.sh` file directly under `runtime/`, regardless of whether it was
touched by this run — including files just reported as KEPT ("not deleted") or YOURS ("left
exactly as they are"). Setting the executable bit is a real, git-tracked change
(`100644` → `100755`), and nothing in this run commits it.

**Reproduction** (continuing the v1.0.0→v2.0.0 fixture from the CRITICAL section's sibling scratch
run, which had a clean CONFLICT on `bothchange.sh` still outstanding):

```
$ PERMA_DIR=$INSTALL bash runtime/update.sh --apply
✅ 3 non-conflicting file(s) updated and committed; recorded version stays v1.0.0 until the 1 flagged file(s) below are resolved.
$ git status --short
 M runtime/bothchange.sh
 M runtime/onlyowner.sh
 M "runtime/owner added file.sh"
 M runtime/owner_added.sh
 M runtime/renamed_by_owner_dst.sh
 M runtime/untouched.sh
$ git diff
diff --git a/runtime/bothchange.sh b/runtime/bothchange.sh
old mode 100644
new mode 100755
... (same for the other 5 files)
$ PERMA_DIR=$INSTALL bash runtime/update.sh --apply
Your Permanence has uncommitted changes — commit or stash them first, then re-run --apply (so the machinery update lands cleanly).
```

Nothing about the owner's *content* changed — this is the file-mode-only diff. But the second
`--apply` (exactly the "script runs twice" / "resolve the flagged conflict, then re-run" workflow
this release is designed around, per its own CHANGELOG: "resolve them with `/perma-upgrade`, then
re-run to finish and advance the version") is now blocked by the tool's own side effect, on files
it had just finished telling the owner would be "left exactly as they are." The owner has to
notice and manually `git checkout -- <mode-only files>` or commit a no-op mode change before they
can ever advance past the outstanding conflict.

This line is unchanged since `v1.4.0` (`git show ecbc5b9:runtime/update.sh` has the identical
`chmod +x "$PERMA/runtime/"*.sh` at both call sites) — it is not new code from this diff. It is,
however, newly consequential: v1.5.0 is the release that introduces a workflow where `--apply` is
expected to be re-run after a conflict is resolved, and that is precisely the case this blocks.

**Fix suggestion:** scope the `chmod +x` to `APPLY_FILES` (and, for the self-update branch, the
files actually checked out) rather than every `.sh` file in `runtime/`, or `git add` the resulting
mode changes as part of the same commit this run already makes.

---

### 3. MEDIUM — `role_lines()` resolves a bare/relative `.role` path against the session's cwd, not `$PERMA`

`runtime/session-start.sh:67-77`:

```
67  role_lines() {  # role_lines <dir-whose-WIP.md-to-mention>
68    local role file
69    role="${PERMA_ROLE:-$(grep -v '^[[:space:]]*$' "$PERMA/runtime/.role" 2>/dev/null | head -n1 | tr -d '[:space:]')}"
...
72    case "$role" in
73      ""|none) return 0 ;;
74      pm)      file="$PERMA/runtime/roles/pm.md" ;;
75      "~/"*)   file="$HOME/${role#\~/}" ;;
76      *)       file="$role" ;;
77    esac
```

The fallback branch (`*) file="$role"`) is meant for "a path to the owner's own role file" per the
comment at `session-start.sh:63`. For an absolute path this is fine. For a bare relative value
(e.g. an owner writes `echo roles/custom.md > .role`, a natural thing to type by analogy with the
shipped `pm` value), `file="$role"` is resolved by the shell relative to whatever directory the
script happens to be running in — which, for the real SessionStart hook, is the *project
workspace* the session opened in, essentially never `$PERMA` or `$PERMA/runtime`.

**Reproduction** (extracted the function verbatim from the file and called it with two different
working directories):

```
$ echo 'roles/custom.md' > $PERMA/runtime/.role
$ echo 'CUSTOM RELATIVE ROLE' > $PERMA/runtime/roles/custom.md
$ (cd $PERMA/runtime && role_lines "$PERMA/stream1")
[perma] ROLE: read roles/custom.md now and follow it for the whole session ...
$ (cd /some/other/project && role_lines "$PERMA/stream1")
[perma] runtime/.role names a role file that does not exist (roles/custom.md) — no role applied. Tell the owner once.
```

Same `.role` file, same `$PERMA`, different result depending purely on the session's cwd. In real
use — a session opened in a registered stream's own project repo — this will essentially always
resolve to "does not exist," silently disabling the role every session, with only a one-line print
easy to lose among normal session-start output. There is no install-time validation of `.role`'s
value the way `install.sh` validates `.consolidate-time` (see the clean result below) — a
malformed/ambiguous `.role` value is only ever discovered at session-start time, repeatedly, quietly.

**Fix suggestion:** document (and/or enforce) that the fallback branch requires an absolute path,
or resolve a bare relative value against `$PERMA` explicitly (`file="$PERMA/$role"`) rather than
the process cwd.

The rest of the documented `.role` test matrix reproduced clean — see the Verified ledger below.

---

### 4. MEDIUM — the new `caffeinate` wrap wires a new failure mode into a pre-existing, misleading generic error message

`runtime/nightly-consolidate.sh:161` (new in v1.5.0) wraps the whole `claude` invocation:

```
161  caffeinate -i "$CLAUDE_BIN" -p "/perma-consolidate" \
```

Any nonzero exit from this line — including `caffeinate` itself being unavailable — falls through
to the pre-existing generic handler at `nightly-consolidate.sh:178-181`:

```
178  if [ $RC -ne 0 ]; then
179    note "ERROR: run failed (exit $RC)"
180    alert "Nightly consolidate FAILED (exit $RC) on $(date '+%Y-%m-%d'). NOT an API-key fallback — most likely the subscription token expired; re-run 'claude setup-token'. Log: runtime/logs/nightly-consolidate.log."
```

**Reproduction** (real machine, real `/usr/sbin/ioreg`, so the awake gate passes instantly; only
`caffeinate` replaced with a nonexistent command name to force an exec failure):

```
$ PATH=.../bin:/usr/bin:/bin:/usr/sbin CLAUDE_CODE_OAUTH_TOKEN=fake bash nightly-nocaffeinate.sh
$ echo $?
127
$ cat runtime/logs/nightly-consolidate.log
2026-09-28 15:35:09 run start
.../nightly-nocaffeinate.sh: line 161: caffeinate-DOES-NOT-EXIST: command not found
2026-09-28 15:35:09 ERROR: run failed (exit 127)
```

The failure is loud (nonzero exit, logged, `alert()` fired) — not silent — so the core "does a gate
failure silently skip forever" question is answered "no" for this case. But the `alert()` text sent
to the owner's next session says "most likely the subscription token expired; re-run 'claude
setup-token'" regardless of cause. Before v1.5.0 that heuristic covered a narrower set of real
causes (auth failures dominate an unwrapped `claude` invocation's nonzero exits). Now the exact
same generic message also fires for "`caffeinate` isn't on PATH" or any other `caffeinate`-side
failure, sending the owner to re-authenticate when the actual fix is unrelated. This is real,
verified-live misdirection, not a hypothetical.

**Fix suggestion:** distinguish the `caffeinate` exec failure (e.g. `command -v caffeinate` check
before use, with its own log/alert line) from `claude`'s own nonzero exit.

---

### 5. LOW — awake-gate failure visibility depends on the (opt-in, off-by-default) events system

`nightly-consolidate.sh:111-119` fails loud in the sense of `exit 1` + a `note()` log line + a
best-effort `alert()`. Reproduced directly (real machine, `ioreg` path pointed at a nonexistent
binary to simulate "not at that absolute path," deadline shrunk from 180min→0 purely for test
turnaround, nothing else changed):

```
$ PERMA_DIR=$FAKE CLAUDE_CODE_OAUTH_TOKEN=fake bash nightly-broken-ioreg.sh
$ echo $?
1
$ cat runtime/logs/nightly-consolidate.log
2026-09-28 15:34:17 ERROR: the awake gate could not read idle time (/usr/sbin/ioreg returned nothing) for 0m — the probe is broken, not the machine idle. No run started.
```

This is correctly not a silent infinite skip — it does stop and it does log — but `alert()`
(`nightly-consolidate.sh:36-39`) is a no-op unless the owner has separately opted in to the events
hooks (`install.sh:120-131` describes this as OPT-IN, not wired by default). On a fresh/default
install, "loud" in practice means a line in a log file nobody is prompted to read; the owner would
see the nightly job simply never produce a report, night after night, with no session-start signal
pointing at why. This is consistent with how every other failure path in this same file already
behaves (missing `claude` binary, missing token, stale lock all use the same `note`+`alert`
pattern) — not a regression specific to the new gate, but worth naming since the review prompt asks
the question directly and the honest answer is "loud only if events are already wired up."

---

### 6. LOW — an owner-initiated rename gets folded into "YOURS ... left exactly as they are," which is not quite true

Fixture: owner renames-and-edits a template file themselves (`git mv rename_by_owner.sh
renamed_by_owner_dst.sh` + edit); template does not touch the original path.

```
🛡  2 file(s) you customised that the template did not change — left exactly as they are:
  runtime/onlyowner.sh
  runtime/rename_by_owner.sh
```

`runtime/rename_by_owner.sh` is reported as "left exactly as they are," but that path does not
exist in the working tree at all — the owner renamed it away. Nothing is resurrected and nothing
is lost (the content survives under the new name, confirmed: `renamed_by_owner_dst.sh` still reads
`OWR1_owner_edit` after apply), so this is cosmetic, not a safety defect — but the message is
inaccurate for this case and could confuse an owner reading the dry-run output line-by-line trying
to account for every file. `update.sh:127-166`.

---

### 7. Observational (LOW, pre-existing, out of this diff) — a completely missing `_meta/VERSION` leaks a raw bash diagnostic

`update.sh:40`: `CURRENT=$(tr -d '[:space:]' < "$PERMA/_meta/VERSION" 2>/dev/null || echo "")`.
When `_meta/VERSION` is entirely absent (not just empty), bash resolves the `<` redirection before
the trailing `2>/dev/null` takes effect, so the "No such file or directory" diagnostic prints
straight to the terminal/log instead of being suppressed:

```
$ PERMA_DIR=$INSTALL bash runtime/update.sh
runtime/update.sh: line 40: .../install4/_meta/VERSION: No such file or directory
fetching from .../template4 (main) ...
installed: unknown  →  latest: v2.0.0
```

Functionally harmless — `CURRENT` still correctly falls back to `"unknown"`, and the script
correctly refuses to apply anything blind ("no recorded version — treating all N changed file(s)
as needing review"), confirmed by re-running with `--apply`: nothing applied, owner's local edit to
`onlyowner.sh` survived untouched. This line predates v1.5.0 (`git show ecbc5b9:runtime/update.sh`
has the identical construct) and is out of scope for this PR's diff, but it's exactly the "what if
this file is missing" chaos case the review asks for, so it's recorded here rather than silently
dropped.

---

## Verified/Unknown ledger

Claims are quoted or paraphrased from `CHANGELOG.md`'s `[1.5.0]` section and the review prompt's
own instructions. "Verified" means independently reproduced in this pass, live, against the real
scripts, in the scratch fixtures described above (all under
`.../scratchpad/update-sh-review/`). "Unknown" means not independently reproduced here.

| # | Claim | Status | Basis |
|---|---|---|---|
| 1 | `update.sh` "never deletes files the owner added" | **Verified** | Owner-added files (plain, spaced, dash-prefixed-dir, and a renamed-to file) all survived `--apply` in every fixture; correctly bucketed as KEPT. |
| 2 | `update.sh` "applies renames instead of dropping them" | **Verified, with a caveat** | The new path is created and the old path removed (confirmed via `--no-renames` producing D+A, both handled). **But** when the pre-rename path carried an owner customisation, that customisation is destroyed, not carried forward or flagged — see CRITICAL finding above. The literal claim (rename lands, doesn't silently vanish) holds; the implied safety (nothing of yours is lost in the process) does not. |
| 3 | `update.sh`: "a file only the owner customised is kept and no longer flagged 'needs review' on every run" | **Verified** | `onlyowner.sh` (template unchanged, owner edited) landed in the new YOURS bucket, was left byte-for-byte untouched by `--apply`, and did not appear in CONFLICTS. |
| 4 | `update.sh`: both-sides-changed file is flagged as a conflict and left untouched by `--apply` | **Verified** | `bothchange.sh` appeared only in CONFLICTS; `--apply` left the owner's edit (`BC1_owner_edit`) in place, did not overwrite with the template's `BC2`. |
| 5 | `update.sh`: template-only change is applied | **Verified** | `templateonly.sh` → `TO2` after `--apply`. |
| 6 | `update.sh`: template-added file is applied | **Verified** | `newfile.sh` (`NF1`) appeared after `--apply`. |
| 7 | `update.sh`: real template deletion (owner never touched the file) is applied | **Verified** | `deleteme.sh` (untouched by owner) removed cleanly. |
| 8 | `update.sh`: template deletion **of a file the owner customised** is safe | **NOT verified — falsified.** | See CRITICAL finding: silently deleted, no flag. |
| 9 | `update.sh`: template rename **of a file the owner customised (without renaming it themselves)** is safe | **NOT verified — falsified.** | See CRITICAL finding: owner's edit destroyed, replaced by template content under the new name, no flag. |
| 10 | `update.sh`: idempotent / safe to run twice | **NOT verified — falsified for `--apply`.** | Second consecutive `--apply` (the release's own designed "resolve conflict, re-run" workflow) is blocked by a self-inflicted dirty working tree (unscoped `chmod +x`). See HIGH finding. Dry-run alone is safe to repeat. |
| 11 | `nightly-consolidate.sh`: awake gate — unreadable `ioreg` output is treated as "do not start," never "start anyway" | **Verified** | Simulated missing `ioreg` at the expected absolute path; `IDLE` fell through to the `999999` sentinel every iteration; script never proceeded to run `claude`. |
| 12 | `nightly-consolidate.sh`: a broken gate fails loudly rather than silently skipping forever | **Verified, with a caveat** | It does `exit 1` with a distinct log line and a best-effort `alert()`. On a default install (events not opted in, per `install.sh:120-131`), the only durable trace is that log file — see LOW finding. |
| 13 | `nightly-consolidate.sh`: `caffeinate -i` wraps the run | **Verified (present)**; failure-mode messaging **NOT verified as accurate** | The wrap is real (`nightly-consolidate.sh:161`). A `caffeinate` exec failure was reproduced (RC 127, loud, logged) but routes through a pre-existing generic "token probably expired" message that is actively wrong for this cause. See MEDIUM finding. |
| 14 | `install.sh`: HH:MM parsing — missing value falls back to 05:30 | **Verified** | No file and an empty file both produced `05:30`, `INSTALL_FAILED=0`, reported via the standard summary line. |
| 15 | `install.sh`: HH:MM parsing — malformed (`abc`), out-of-range (`24:00`, `25:99`, `18:00:00`) are rejected and fallback is reported, not silent | **Verified** | Each produced a `FAILED:` line, `INSTALL_FAILED=1`, and `05:30` in the final summary. |
| 16 | `install.sh`: HH:MM parsing — single-digit hour (`7:30`) | **Verified (rejected by design)** | Requires zero-padded `HH:MM`; `7:30` is correctly treated as malformed and reported, not silently accepted or silently defaulted. |
| 17 | `install.sh`: HH:MM parsing — padded whitespace, leading blank lines | **Verified (accepted correctly)** | `"  18:45  \n"` → `18:45`; blank lines before a valid line are skipped via `grep -v '^[[:space:]]*$'` + `head -n1`. |
| 18 | `session-start.sh` `role_lines()`: `.role` missing / `none` / `pm` / absolute path / `~/` path / padded whitespace / path to a missing file / `PERMA_ROLE` override | **Verified, all 8 cases** | Each behaved exactly as documented; extracted the real function body verbatim and drove it with all 8 inputs plus a `WIP.md`-present case. |
| 19 | `session-start.sh` `role_lines()`: any other path form (the fallback `*)` case) | **NOT verified — a real gap found**, not previously documented as tested | Bare relative values resolve against the session's cwd, not `$PERMA`. See MEDIUM finding. |
| 20 | The ShellCheck SC2088 fix (commit `a2b4ab3`) was an isolated false positive, no defect nearby | **Verified** | The `"~/"*` branch and the whole surrounding `case` block behave correctly for every input tried, including the exact padded-whitespace and tilde-path cases most likely to interact with that suppression. |
| 21 | Edit(...) vs Write(...) permission-rule claim in `nightly-consolidate.sh`'s comments (`nightly-consolidate.sh:146-150`) | **Unknown** | Requires a live headless `claude` invocation against real permission gating to verify; out of scope for a shell-only scratch repro and not on the review prompt's explicit target list for this file. Not contradicted by anything found, just not independently exercised here. |
| 22 | Multi-release upgrade (owner installed several versions behind, template touched a path differently across intermediate releases) | **Not separately reproduced** | The mechanism is tag-based (`CURRENT`..`TARGET` diff only, no per-intermediate-release logic), so the single-hop fixtures above exercise the same code path a multi-hop upgrade would; reasoned as equivalent rather than independently built as a 3-tag chain, given time budget. |
