# v1.9.0 adversarial review — pass output

Reviewed: `git diff main...v1.9.0-shortcuts` (head 03513a1), 8 files, instruction text only.
Reproductions: scratch repos under `.../scratchpad/review-190/` (git 2.52.0, global git config
disabled). Build script: `review-190/scripts/build.sh`. Nothing was written to the repo except this file.

## ANDON

The contract names five stop conditions. Three are met by the letter. I give my own read of how
much each matters, because "met by the letter" and "dangerous" are not the same thing.

| Id | Stop condition met | My read of the weight |
|---|---|---|
| A1 | Contradicts another shipped instruction: the PM's two "word for word" brief rules against the fixed engineer brief templates and against `refactor-engineer` ("Verbatim ... No logic edits") | Real. Fix before merge. |
| A2 | Ponytail text copied rather than reworded: one heading, the marker template, one tag and two phrases are identical; the six-item list is a line-by-line light paraphrase | Real at phrase level. The CHANGELOG sentence "Nothing of Ponytail is installed or copied" is not true as written. Whether it matters legally is the owner's call; I am not a lawyer. |
| A3 | Contradicts another shipped instruction: step 8 hard-codes a command, and the same file says never to use a command the binding does not give | Met by the letter. Low practical weight. A two-line wording fix. |

Not met: no instruction can make an agent write to a repo it does not own (step 8 is read-only, verified).
No safety limit is weakened in text. No file every session loads was changed.

## BLUF

The health step's grep works as described for the plain cases, but it is not the "deterministic, no AI
spend" watch the file promises: in a repo with keyboard-shortcut config it returns thousands of
non-marker lines, and the agent must judge each one. The larger problem is in `pm.md`: the two new
brief rules are not in the brief templates that `/perma-change` and `/perma-refactor` actually send,
and when they are added to a refactor brief they tell a move-verbatim engineer to ask "does it need to
exist" and "is it already in this codebase". The reviewer changes fit their contracts with two small
ambiguities. The owner's constraints (nothing every session loads, no hook, generic `pm.md`) all hold.

## Findings, most severe first

### A1 (ANDON by criterion; P1) — The two brief rules contradict the engineer's own contract and the shipped brief templates

Where: `runtime/roles/pm.md:50-71`, against `runtime/agents/refactor-engineer.md:43-44`,
`runtime/commands/perma-refactor.md` (engineer brief, "Move code verbatim. Stop on any output change")
and `runtime/commands/perma-change.md` ("Keep each brief short: the agent's own definition already
holds the method" and "A filled brief has no `{…}` and no `[…]` left").

The case, in three parts.

1. The rules are not where engineers are briefed. `pm.md:50` says "A brief to an engineer also carries
   two rules, word for word". The only shipped engineer briefs are the two fixed templates in
   `perma-refactor.md` and `perma-change.md`. Neither template contains the rules. `git grep -n shortcut`
   over `runtime/commands/perma-refactor.md` and `perma-change.md` returns nothing. A PM that fills the
   template as written sends no shortcut rule. Then no engineer ever writes a marker, and health step 8
   always reports "no shortcut markers". A PM that obeys `pm.md` instead appends about 20 lines to a
   template that says "keep each brief short". The text does not say which instruction wins.
2. In a refactor, the list contradicts the engineer. `agent-roles.json` fills the `engineer` role with
   `refactor-engineer` for both jobs. Its contract is "Verbatim: same names, same order, same comments.
   No logic edits." The new list tells it, in order: "1. Does it need to exist at all? 2. Is it already
   in this codebase?" An engineer obeying literally deletes a function it judges unneeded, or replaces a
   moved function with a call to a similar existing helper. The byte-identical gate passes when today's
   outputs do not exercise the difference. The stated limits ("never drop ... anything the owner asked
   for") do not name "the brief's own method" or "verbatim moves". The `refactor-reviewer` samples 10
   moved units, so it may catch this, or may not.
3. The list items are questions, not options. "Take the first that fully does the job" cannot be applied
   to "Does it need to exist at all?". The text gives no action for a "no" (do nothing? report it?) and
   no action for a "yes". The source gives an action on every line; the rewording removed them. The
   source also says to reuse "the way the surrounding code does" and to "keep the structure the codebase
   already has: its layers, interfaces and conventions". That limit was dropped. So item 2 can couple
   to an unrelated module, and in `/perma-change` it can pull a fix out of the "Owning layer" the brief
   names ("a fix in another layer is an andon").

Also: the marker rule adds a comment at a moved line. That breaks "same comments" in a verbatim move.
And "Smallest does not mean cut corners" sits one paragraph above "When the engineer takes a shortcut
on purpose". The text never says what a permitted shortcut is, as distinct from a cut corner.

Suggested fix (about 30 minutes):
- In `pm.md`, add one sentence after the limits: "These rules apply to new or changed code. In a
  byte-identical refactor step the engineer's own contract wins: move verbatim, delete nothing, reuse
  nothing, add no marker."
- Give each list item its action: "1. Does it need to exist at all? If not, build nothing and say so in
  the report." "2. Is it already in this codebase, in a layer this code may depend on? Use it."
- Add one line to the `/perma-change` engineer brief template that carries the rules (or a pointer),
  or say in `pm.md` that a command's brief template wins and name where the rules go. This is a
  decision for the owner: I do not know which of the two was intended.

If not fixed: the first `/perma-refactor` run under the PM role either ships no shortcut rule at all, so the health list stays empty for good, or it hands a move-verbatim engineer an instruction to delete and reuse, on the next refactor step that contains dead-looking or duplicated code.

### A2 (ANDON by criterion; P1) — Some Ponytail text is identical, and the CHANGELOG says none is

Where: `runtime/roles/pm.md:53-71`, `runtime/commands/perma-health.md:85,94`, `CHANGELOG.md:21-23,27,35-38`.

Compared against the three source files (fetched read-only into scratch, not installed):

| This branch | Ponytail | Same? |
|---|---|---|
| `*The smallest complete change.*` (`pm.md:53`, and the CHANGELOG title) | `## The smallest complete change` | Identical heading |
| `shortcut: <the limit>, <when to upgrade>` (`pm.md:68`, `perma-health.md:85`, `CHANGELOG.md:27`) | `shortcut: <the limit>, <when to upgrade>` | Identical |
| `no-trigger` (`perma-health.md:94`) | `no-trigger` tag | Identical |
| "error handling that prevents data loss" (`pm.md:62-63`, `CHANGELOG.md:37`) | "error handling that prevents data loss" | Identical, 6 words |
| "one line a reader gets at a glance" (`CHANGELOG.md:36`) | "one line a reader gets at a glance" | Identical, 8 words |
| "Otherwise: the least code that works." | "Otherwise: the minimum code that works." | One word changed |
| Items 1 to 5 of the list | Items 1 to 5 | Same six items, same order, each turned into a full question |
| "Never drop validation where data crosses a trust boundary ... anything security depends on, or anything the owner asked for" | "Never cut: validation at trust boundaries, ... security, ... anything the user asked for" | Close paraphrase |
| "If not fixed:" and its guidance | "If we skip it:" | Reworded. Clean. |
| Health step 8 prose | ponytail-debt Scan and Output | Reworded. Clean, apart from the two identical tokens above. |

The marker format and the tag are an interface. Keeping them identical is defensible, and useful if the
owner ever wants the two tools to read each other's markers. But then the CHANGELOG sentence "each
reworded for this project. Nothing of Ponytail is installed or copied; these are its ideas, not its
files" is not accurate.

Suggested fix (about 10 minutes): change the CHANGELOG sentence to say what is true: "The marker format
`shortcut: <the limit>, <when to upgrade>`, the `no-trigger` tag and the six-step order are Ponytail's,
kept so the two stay compatible; the rest is reworded." Reword the heading and the two identical
phrases if the owner wants a clean "nothing copied" claim. Whether the six-item list needs the MIT
copyright notice beside it is a question for the owner; I did not read the repo's LICENSE file (the
brief limited me to three files), so I do not know the copyright holder's name.

If not fixed: the release notes publish a "nothing copied" claim that anyone can disprove in two minutes by placing `pm.md` beside the Ponytail skill file, as soon as v1.9.0 is public.

### A3 (ANDON by criterion; P2) — Step 8 breaks the file's own "facts from the binding" rule and its "no AI spend" claim

Where: `runtime/commands/perma-health.md:10-13`, `:107-108`, against `:84-101`.

Quoted: line 10, "The watch is deterministic and costs no AI spend: it runs one command and reads one
file." Line 12, "Never use a path, command, threshold or part name that the binding and the register
do not give you." Line 107, "Every repo path, command and owner rule comes from the binding or the
register."

Step 8 runs `git grep -nI 'shortcut:'`. That command and that marker word come from the instruction
file, not from the binding. Step 8 also asks the agent to judge each line (marker or not, where the
limit ends, whether a condition exists). That is not deterministic, and it costs AI spend in proportion
to the number of hits.

Suggested fix (about 5 minutes): add "except step 8, which uses one fixed command" to line 12 and to
the guardrail, and change line 10 to say steps 1 to 7 are deterministic.

If not fixed: an agent that obeys the guardrail strictly can refuse step 8 or stop to ask which binding field holds the command, the first time it runs the command with care.

### F4 (P1) — In a repo that has keyboard shortcuts, step 8 returns noise, and the text does not exclude it

Where: `runtime/commands/perma-health.md:88`, `:96-97`.

Reproduced (scratch repo `b`):

```
$ git grep -nI 'shortcut:'
dist/app.min.js:1:var a=1;var a=1;...            <- one output line of 320,048 bytes
docs/README.md:1:Mark a shortcut with `shortcut: <the limit>, <when to upgrade>`.
node_modules/x/i.js:1:// shortcut: tracked node_modules, upgrade y
src/app.py:1:data = open(p).read()  # shortcut: holds the whole file in memory, upgrade when files pass 50 MB
src/app.py:2:rows = scan(all)  # shortcut: linear scan
src/app.py:3:n = f(x)  # shortcut: O(n^2), fine under 1,000 rows, upgrade when rows pass 10,000
src/app.py:4:m = g(x)  # shortcut: reads everything, no pagination
src/app.py:8:msg = "press the shortcut: Ctrl+K to search"
src/app.py:9:url = "https://example.com/docs/keyboard-shortcut:list"
src/app.py:10:z = 1  # shortcut: modified in worktree only, upgrade r
src/keymap.yaml:3:    shortcut: ctrl+s
src/keymap.yaml:5:    shortcut: ctrl+o
src/staged.py:1:# shortcut: staged-not-committed, upgrade q
vendor/lib/v.js:1:// shortcut: vendored lib marker, upgrade never
rc=0
```

Scratch repo `many` (40 keymap files, one real marker): 4,001 output lines, 128,534 bytes.

What the instruction tells the agent, case by case:

| Case | Told what to do? |
|---|---|
| No markers (exit 1, no output) | Yes. Correct. Also correct in a repo with no commits (exit 1). |
| Marker with a condition | Yes. |
| Marker with no condition (`linear scan`) | Yes: `no-trigger`. |
| Limit that contains a comma (`O(n^2), fine under 1,000 rows, upgrade when ...`) | No. The agent must guess where the limit ends. |
| No condition, but a comma (`reads everything, no pagination`) | No. A literal split at the first comma reads "no pagination" as the condition, so the `no-trigger` flag is missed. |
| Documentation line | Yes: left out. |
| String literal (`"press the shortcut: Ctrl+K"`), URL (`keyboard-shortcut:list`), YAML key (`shortcut: ctrl+s`) | No. The only exclusion is "a line that only talks about the marker (documentation, a test of this rule)". These lines do not talk about the marker. A literal agent lists `shortcut: ctrl+s` as a marker with limit "ctrl+s" and `no-trigger`. |
| Minified tracked file | No. One hit is one 320 KB line, read in full. |
| Tracked `vendor/` or `node_modules/` | No. Listed as the repo's own markers. See F5. |
| Thousands of hits | No cap, no "count first". The whole output goes to the agent. |
| Non-git folder | Not in step 8. Exit is 128, `fatal: not a git repository`. Step 1 stops first (`git rev-parse` fails), so this is covered in practice. |
| Exit code above 1 | No. Only exit 1 is described. |
| Binary file | Yes, by `-I`. Verified: with `-I` exit 1, without it "Binary file src/blob.bin matches". |

The source tool avoids most of this. It anchors the pattern on a comment leader
(`'(#|//|/[*]) ?(shortcut|ponytail):'`) and says "Skip hits that are not a deferral, like a note about a
keyboard shortcut". Run in scratch repo `b`, the anchored pattern drops the README, the string, the
URL and both YAML lines. This branch dropped the anchor and the sentence.

Suggested fix (about 20 minutes): say "A marker is a comment. A line where `shortcut:` is not inside a
comment is not a marker: leave it out." Add "If the limit holds a comma, the upgrade condition is the
last clause; if no clause says when to upgrade, it is `no-trigger`." Add a cap: "More than 200 lines:
run `git grep -cI 'shortcut:'`, give the per-file counts, and say the list was not read." Add "Any
other exit code: show the error." Anchoring the pattern on a comment leader is the stronger fix, but
the leader set depends on the language, so I am not confident which set fits the owner's repos.

If not fixed: the first health run in a repo with a keymap or UI-shortcut config spends a large read on non-markers and reports a marker count the owner cannot trust.

### F5 (P2) — Two statements about `git grep` are not true in every repo, and "every marker" is an overclaim

Where: `runtime/commands/perma-health.md:91-92`; `CHANGELOG.md:27-28`; `docs/PROJECT-TEAM.md:23`; `docs/TOOLS.md:29`.

Quoted: "`git grep` reads tracked files only, so `.git`, installed dependencies and build output are
already left out."

- "Tracked files only" is true. "So installed dependencies and build output are left out" is true only
  when those are untracked. Reproduced: tracked `node_modules/x/i.js`, `vendor/lib/v.js` and
  `dist/app.min.js` all appear (output in F4). Vendored and committed build files are common.
- "Lists every marker" (CHANGELOG, both doc rows) is not true. Reproduced misses:
  - an untracked new file: `src/new_untracked.py` holds a marker and is not listed. This is exactly
    the state of work an engineer has just done and not yet added;
  - `# Shortcut:`, `# SHORTCUT:` and `# shortcut :` (lines 5 to 7 of `src/app.py`) are not listed.
    The match is case-sensitive and needs the colon directly after the word;
  - a submodule: `git grep -nI 'shortcut:' -- sub` exits 1; with `--recurse-submodules` it finds
    `sub/s.py:1`.
- It reads the working tree of the checked-out branch. Markers on other branches are not seen. A
  staged or modified tracked file is seen (verified). That is reasonable, but the text does not say it.
- "From the repo root" matters and is stated: from `docs/` the same command lists only `README.md`.

Suggested fix (about 10 minutes): reword to "`git grep` reads tracked files in the checked-out tree. It
leaves out `.git` and anything untracked. A dependency or build folder that is tracked is still
searched: leave those hits out and say so. It does not see untracked files, submodules, or a marker
written with a capital letter." Change "every" to "the" in the CHANGELOG and the two doc rows, or add
`-i`.

If not fixed: an owner reads "no shortcut markers" as "none exist" while a marker sits in a new untracked file or a submodule, on any run made before the engineer's work is committed.

### F6 (P2) — The word-for-word rule puts a Permanence command name into briefs that reach the repo

Where: `runtime/roles/pm.md:70` ("`/perma-health` lists every marker"), against `pm.md:137` ("Never write
Permanence content or paths into a project repo"), `perma-health.md:111-112` ("Never write a Permanence
path or name into the repo's files"), `SPEC.md:118` ("a repository never names Permanence"), and
`perma-change.md` ("Briefs reach committed review records").

The rule must be carried "word for word", and its last sentence names `/perma-health`. The review record
is committed on the step's branch in the repo (`perma-refactor.md`, step 9, last bullet). The engineer
brief templates today contain no Permanence name (checked: no match for `perma` inside either file's
brief blocks).

Suggested fix (about 5 minutes): end the word-for-word text at "write the condition." Move the
`/perma-health` sentence outside the part that is carried into the brief.

If not fixed: the first reviewer that quotes its brief in `contract.md` commits a Permanence command name into a project repo, which invariant 1 forbids, and in another party's repo that lands in their pull request.

### F7 (P2) — Step 8 runs after some stops and not after others

Where: `runtime/commands/perma-health.md:41`, `:44-47`, `:49-50`, `:53`, `:101`.

Step 3's "script not installed" stop now says "stop here ... skip steps 4 to 7 (step 8 still runs)".
"Stop here" and "step 8 still runs" sit in one sentence. Three other stops say only "stop": a pointer
that leads to no command (`:41`), a placeholder left unfilled (`:49`), and a signal that exits non-zero
(`:53`). Step 8 says it "does not need the register", so by its own reasoning it could run after all
four. The text gives one answer for one stop and none for the other three.

Holds: step 1's stop (no binding) correctly ends everything, and "skip step 6" in step 5 leaves 7 and 8
running, which is right.

Related, in another file: `perma-refactor.md:151` says "Refresh the register exactly as `/perma-health`
steps 3 and 4 do". Step 3 now contains "(step 8 still runs)". An agent following step 3 "exactly" from
inside a refactor could run the marker list in the middle of that job. Harmless, but not intended.

Suggested fix (about 5 minutes): in step 3 write "skip to step 8" instead of "stop here ... (step 8
still runs)". Add to step 8: "It also runs after any stop in steps 3 or 4. It does not run after a
stop in step 1."

If not fixed: the marker list appears on some failed health runs and not on others, and the owner cannot tell a missing list from an empty one.

### F8 (P3) — refactor-reviewer: "every finding ... in the report" against "each ANDON/P0/P1 in two or three lines"

Where: `runtime/agents/refactor-reviewer.md:60-64`.

The report lists only ANDON, P0 and P1. The new sentence says "Every finding, in `findings.md` and in
the report, ends with one sentence headed 'If not fixed:'". A literal reader can take this as "put
every finding, P2 and P3 too, in the report". Also "two or three lines" now has a fourth line.
(`P0` is not in the severity table at `:49-54`. That was already so on `main`; I flag it and leave it.)

Fit with readers: `perma-refactor.md` step 9 and `perma-change.md` fix rounds send the findings to an
engineer and write `disposition.md`. Neither parses the findings. `agent-roles.py:189-198` checks only
that a fresh file exists in the record folder. So nothing breaks mechanically. One soft effect: step 9
says "Fix every ANDON, P0 and P1 ... Skip only the cosmetic". A finding that carries "If not fixed: I
cannot say what happens" and "it is a reason to doubt the finding" gives the PM a reason to skip a P1
that step 9 says must be fixed. The reviewer text does not say that severity still decides.

Suggested fix (about 5 minutes): "Every finding in `findings.md`, and each one listed in the report,
ends with ...". Add: "The sentence does not change the severity."

If not fixed: reports from different reviewer runs differ in which findings they list, and a P1 with a "cannot say" sentence may be skipped in a fix round, the first time one occurs.

### F9 (P3) — design-reviewer: the new column against "in the format of the previous runs"

Where: `runtime/agents/design-reviewer.md:56-59`, `:68-69`.

The table gains a fifth column. Line 68 still says to write `02-pass-output.md` "in the format of the
previous runs", and previous runs have four columns. The new instruction is the more specific one, so
most agents will add the column, but the two lines pull in opposite directions. The column holds a full
sentence beside a quoted-text column, so the table gets wide. The severity table (`:46-51`) is
untouched and consistent.

Suggested fix (about 2 minutes): add to line 68 "plus the 'if not fixed' column".

If not fixed: some design reviews after this release copy the old four-column format and leave the sentence out, with no error to show it.

### F10 (P3) — CHANGELOG: "opt-in files" is loose for the two agents

Where: `CHANGELOG.md:40-41`.

"All three live in opt-in files: the PM role, the team's health command and two of its agents."
`runtime/bindings/claude-code/wire:60-79` installs every file in `runtime/agents/` for every Claude Code
install. The agent bodies load only when the agent is dispatched, and their frontmatter (the part every
session lists) is unchanged. So "nothing every session loads has changed" is true. But the agents are
not opt-in by a switch: any session that dispatches `design-reviewer` gets the new column.

Suggested fix (about 2 minutes): "the PM role (opt-in), the health command, and the bodies of two
agents, which load only when the agent is dispatched".

If not fixed: an owner who uses `design-reviewer` outside the team sees a changed report shape that the release notes said was opt-in, on their next review.

## Verified / Unknown ledger

Verified (held under attack):

- Step 8 writes nothing. `git grep` is a read. It is safe in a repo another party owns. The guardrail
  "A repo another party owns is read-only" holds.
- "Exit code 1 with no output means none" is true (scratch `a`: rc=1; empty repo `a0`: rc=1).
- `-I` skips binary files (scratch `b`: rc=1 with `-I`, "Binary file ... matches" without).
- "`git grep` reads tracked files only" is true as a bare statement (untracked `new_untracked.py` not listed).
- Non-git folder: exit 128, and step 1 stops before step 8 is reached.
- Step numbering: every outside reference still points at the right step. `perma-change.md:141` and
  `perma-refactor.md:98` cite step 6; `perma-refactor.md:151` cites steps 3 and 4; `team-preflight.py:226`
  cites "its signal step". Steps 1 to 7 were not renumbered. `runtime/bindings/antigravity/team-note.md`
  cites no step number. `docs/` cites none.
- Step 5's "skip step 6" still works with step 8 present.
- `pm.md` is generic: no person's name and no project name in the diff or in the whole file.
- The limits paragraph does cover "does it need to exist" being used to skip owner-asked work ("or
  anything the owner asked for"), and covers partial work ("its callers, its tests, its fixtures").
- `agent-roles.py` run-record check reads no finding text; the new sentence cannot fail it.
- Severity tables in both reviewers are untouched.
- Owner constraints: the diff touches 8 files only. `runtime/claude-md-block.md`,
  `runtime/agents-md-block.md`, `runtime/session-start.sh`, `runtime/install.sh`, `SPEC.md` and every
  `.json`, `.sh` and `.py` file are untouched. No hook or settings file is added or changed. The
  frontmatter of `perma-health.md` and of both agents is unchanged, so no session-wide listing changed.
- Credit: the link resolves to the public repo `DietrichGebert/ponytail`; GitHub reports its licence as
  MIT. (I read the repo's metadata record for this, one call beyond the three files.)
- CHANGELOG claims that are true of the diff: the `no-trigger` flag; "the step only reads; it changes no
  part's state"; one sentence added to each finding in both reviewers; the six items and the limits as
  listed; no hook added; no migration notes needed.
- Both doc rows match the step, apart from the word "every" (F5).

Unknown:

- Whether the six-item list is close enough to the source to need the MIT notice. Not my call.
- The copyright holder's name in Ponytail's LICENSE. Not read; the brief limited me to three files.
- Which was intended in A1: the rules added to the command brief templates, or the templates winning.
- How a real agent resolves "stop here ... (step 8 still runs)". Read, not run: I ran no agent.
- How often `refactor-reviewer`'s 10-unit sample would catch a "reuse" substitution from A1. Read, not run.
- Behaviour on Antigravity. Read, not run. The team note changes nothing that step 8 depends on.
- The test suite was not run. I could not confirm it leaves the real `$HOME` alone.
- `refactor-reviewer.md:16` ("the engineer who will be paged when it silently breaks") resembles the
  opening line of the Ponytail review skill. It is on `main` already and outside this diff. Flagged, not assessed.
