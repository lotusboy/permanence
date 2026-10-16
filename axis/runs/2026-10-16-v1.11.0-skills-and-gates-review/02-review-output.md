# v1.11.0 adversarial review — output

Reviewer: one agent, single adversarial pass, per 00-contract.md and 01-review-prompt.md.
Target: branch v1.11.0 against main (178bdf3). The brief named three commits (75c5863, db43c76, ce78090).
A fourth commit, 905ce4e ("the expert role runs on Fable by default"), landed on the branch at 18:21 while
this review was running. Its diff (2 lines: `model: opus` -> `fable` in agent-roles.json and
human-expert.md) is reviewed below. The scratch clone used for the wire runs is at ce78090; the wire does
not read either changed line.
Scratch: `$S` = <scratch>/review-1110.
Every repro ran with HOME and PERMA_DIR inside `$S`. Nothing in the repo was edited except this file.

---

## ANDON

The contract's STOP conditions are met three times. All three are text or gate problems. None of them
loses a user's file.

1. **A gate refuses a call that every existing user makes, and the shipped instructions still tell agents
   to make that call.**
   - `runtime/decision.sh:10-11` gives the example `decision.sh ask --category spend --question "Run the audit now?" ...`. It is now refused: `--read <file> is required`.
   - `runtime/spend.sh:9` and `runtime/README.md:19` give the example `spend.sh record --agent a1b2c3 --label "S2 answers r1" --tokens 131204 --kind answering-agent --task A508`. It is now refused: `give --why, --predicted, --predicted-tokens, --result, --outcome`.
   - (Findings H1 and H2.)
2. **The new gates can be passed without the evidence they ask for.**
   - `--read /etc/hosts --read-what .` passes.
   - `--read <a directory>` passes.
   - `--upstream " ."` passes.
   - `--stepped-back .` passes.
   - `--recheck --task NOPE-1` lets a fix proposal through without `--upstream`.
   - Repeating `--fix-round 1` never reaches the step-back gate.
   - Leaving `--task` out skips the architect gate.
   - (Finding H3.)
3. **Shipped instructions contradict each other.**
   - On the step-back threshold:
     - `pm.md:146-153` says that for any one signal, "dispatch nothing more and use the step-back skill".
     - `skills/step-back/SKILL.md:41-42` says "One signal: mention it in the next update. Two or more ... run the rest of this skill".
   - On logging defects, spend waves and engineer briefs (finding M3).
   - (Findings M2 and M3.)

No ANDON on skills install. A user's own skill was never lost in any repro, and every edited copy was kept.
One failure path does put a fresh nested copy at `~/.claude/skills/<name>/<name>/SKILL.md` (finding H4).
That copy is new; nothing that was moved lands there. Whether Claude Code loads a nested SKILL.md is Unknown.

## BLUF

The skills install is sound on its normal paths:
- It is idempotent.
- A user's own skill is left alone.
- Edited copies are kept outside `~/.claude/skills/`.

It has one unchecked `mv`. When that `mv` fails, the install reports success while it nests a copy and
leaves the old one in place.

The new decision.sh and spend.sh gates are the main problem:
- They refuse the examples that the tools' own headers and the runtime README still show.
- They refuse ordinary questions ("Should we ship X?", "fixed fee", "contract.pdf").
- They let meaningless values through. So they add friction without enforcing evidence.

pm.md now contradicts the step-back skill and itself in three places. CHANGELOG understates spend.sh's new
mandatory fields.

---

## Findings, most severe first

### H1. decision.sh `ask`: every existing call is refused, including the tool's own header example
- **Where:** `runtime/decision.py:284-288` (check_grounding, `--read` required). The example that is now refused is at `runtime/decision.sh:10-11`.
- **Repro** (`$S/gates.sh`, case 1):
  ```
  --- Run the audit now?
  decision: --read <file> is required: a source file you opened yourself (raw document, product data, code), not an agent's report
  ```
- **What this means:**
  - Many owner questions have no source file. Examples: "Run the audit now?"; pm.md's own "Park the current one, or finish it first?" (pm.md:115); the /perma-change "go or not" (perma-change.md step 3).
  - pm.md §8 says to record every question before sending it.
  - So the agent must either invent a `--read` or skip the record.
- **Fix:**
  1. Require `--read` only for categories or questions that assert a fact about a source. Or let `--evidence-kind inference` / a spend or scope category skip it.
  2. Update the header example in decision.sh to a call that passes.
  3. Add a test that runs the header example.
- **If not fixed:** agents will satisfy `--read` with any file to hand, and the ledger's grounding field becomes noise.

### H2. spend.sh `record`: five new mandatory flags; the shipped examples are refused, and CHANGELOG does not say it is a breaking change
- **Where:**
  - `runtime/spend.py:221-225`.
  - The examples are at `runtime/spend.sh:9-11` and `runtime/README.md:19`.
  - The CHANGELOG [1.11.0] text says only "`spend.sh record` also tracks a tool's result".
- **Repro** (`$S/spend.sh`):
  ```
  --- --agent a1b2c3 --label S2 answers r1 --tokens 131204 --kind answering-agent --task A508
  spend: a first record states the tool's result, not only its cost: give --why, --predicted, --predicted-tokens, --result, --outcome
  ```
- **Empty values pass:**
  ```
  --- --agent e1 --label L --tokens 10 --why  --predicted  --predicted-tokens 1 --result  --outcome as-predicted
  recorded e1 (L): 10 tokens, harness, no wave open
  ```
- **Fix:**
  1. Update both examples.
  2. Say in CHANGELOG that a first record now requires the five flags.
  3. Refuse empty strings (`not (v or "").strip()`), as decision.py already does.
- **If not fixed:** every existing caller breaks on upgrade. The measured-spend ledger then loses rows, or fills with blank "why/result" values.

### H3. The gates pass without the evidence they ask for
- **Where:** `runtime/decision.py:290-327`, `runtime/spend.py:216-220`.
- **Repro** (`$S/gates.sh` cases 4-6, `$S/spend.sh`). Each line below was accepted with a ledger id, or recorded:
  ```
  --read src/02-review-output.md --read-what F1      -> d20261016-b1d9fc   (an agent's review record)
  --read /etc/hosts --read-what .                    -> d20261016-c18bba
  --read src (a directory) --read-what .             -> d20261016-812953
  "Apply the fix?" --upstream " ."                   -> d20261016-3070fa
  "Apply the fix?" --recheck --task NOPE-1           -> d20261016-a9e610   (no --upstream; task never existed)
  --fix-round 1, three times on T1                   -> accepted each time; the round count never rises
  "Apply the fix again?" --task T1 (no --fix-round)  -> d20261016-58261f   (round 4 in effect, no step-back asked)
  --fix-round 3 --rechecked . --stepped-back .       -> d20261016-82ff95
  --fix-round -4                                     -> d20261016-6edb3f
  spend: --kind architect, second run, no --task     -> recorded a3
  spend: --kind architect --task t9 (ledger has T9)  -> recorded a4
  spend: second architect --stepped-back " ."        -> recorded a2
  ```
- **The spend architect gate fires at record time.** spend.sh records the harness's token count after an agent finishes. So the refusal comes after the second architect has already run. It cannot prevent the run. It can only stop the cost being recorded.
- **Why the round gate fails:** the round number is self-declared. `rounds` is a set of distinct numbers, so repeating a number never raises it.
- **Fix:**
  1. Count fix rounds from the ledger: the number of asks per `--task` that propose a fix. Do not trust `--fix-round`.
  2. Require `--read` to be a regular file (`path.is_file()`).
  3. Require a minimum length or content for `--upstream`, `--rechecked` and `--stepped-back`, or make them point at a file or line that exists.
  4. Make `--recheck` require that the task already has a fix round in the ledger.
  5. Move the architect gate to dispatch time. The role hook in `runtime/agent-roles.py` sees every `role:architect` dispatch.
- **If not fixed:** the tools report that the step-back was "enforced" when it was not, and the owner trusts a gate that any hurried agent passes with ".".

### H4. Skills wire: an unchecked `mv` leads to a false "kept" message, a nested copy inside `~/.claude/skills/`, and exit 0
- **Where:** `runtime/bindings/claude-code/wire:120-129`.
- **The cause:**
  - If `mv "$dst" "$keep"` fails, the script still prints "your edits ... are kept".
  - `cp -R "${d%/}" "$dst"` then copies into the existing folder, which nests it.
- **Two triggers reproduced:**
  - Two edited reinstalls in the same second. The timestamp name collides: the first `mv` nests into the kept folder, the second `mv` fails.
  - `~/.claude/skills-perma-bak` exists as a file.
- **Repro** (`$S/blk.sh`, skills block cut out exactly as the unit test does):
  ```
  mv: rename .../hE2/.claude/skills/demo to .../hE2/.claude/skills-perma-bak/demo.20261016182202: Not a directory
    skill: demo — your edits to the installed copy are kept in ~/.claude/skills-perma-bak/demo.20261016182202
    skill: demo
  exit=0
  .../hE2/.claude/skills/demo/SKILL.md          <- still the user's edited copy ("body EDITED")
  .../hE2/.claude/skills/demo/demo/SKILL.md     <- new nested copy
  ```
- **Same-second variant** (`hD`, three edits in one second):
  - The third `mv` fails with "Directory not empty".
  - The result is `skills/demo/demo/SKILL.md`, and an earlier keep nested at `skills-perma-bak/demo.<ts>/demo/`.
- **What is not lost:** the user's edits survive in every case. The harm is:
  - a false message;
  - the new version not installed;
  - a nested SKILL.md under `~/.claude/skills/`. Whether Claude Code loads it is Unknown.
- **Fix:**
  1. `mv "$dst" "$keep" || { echo "  skill: $name — could not keep your copy; not replaced"; WIRE_FAILED=1; continue; }`.
  2. Apply the same to the unedited branch.
  3. Make `keep` unique: `mktemp -d "$SKILL_KEEP/$name.$(date +%Y%m%d%H%M%S).XXXX"`, then move into it.
- **If not fixed:** a rare failure produces a confident wrong message and a skill folder that is neither the old nor the new version.

### M1. Skills wire: an untouched installed copy is reported as "your edits" on every upgrade that changes the skill
- **Where:** `runtime/bindings/claude-code/wire:118-119`. The copy is compared with the current source, not the source it was installed from. The agents block, `wire:71`, does the same; that is older behaviour.
- **Repro** (`hF`): install, change the source upstream, re-run, with no user edit:
  ```
    skill: demo — your edits to the installed copy are kept in ~/.claude/skills-perma-bak/demo.20261016182156
  ```
- **Fix:** store a hash of the installed bytes in the marker, or in a sidecar outside the skill folder. Report "edited" only when the installed copy differs from that hash.
- **If not fixed:**
  - Every release that touches a skill tells every user they edited it.
  - `skills-perma-bak/` grows without limit.
  - Users learn to ignore the one message that matters.

### M2. pm.md contradicts the step-back skill on when to step back
- **Where:** `runtime/roles/pm.md:146-153` against `runtime/skills/step-back/SKILL.md:24-42`.
- **pm.md says:** "For any of them, dispatch nothing more and use the `step-back` skill."
- **The skill says:** "One signal: mention it in the next update. **Two or more, or any owner nudge: run the rest of this skill before the next dispatch.**"
- **The signal lists differ:**
  - pm.md has signals the skill's table lacks: "two rounds in which nothing moved", "a second serious review finding whose cause lies outside the code under review", "a second architect run in one chain".
  - The skill has signals pm.md lacks: Ceiling creep, Drift, Compensation pile.
  - Overrun is defined two ways: pm.md says "overrunning twice"; the skill says "≥ 1.5 × estimate, twice in a row".
  - decision.py enforces a third threshold again: fix round 3.
- **Fix:** keep one list and one threshold, in the skill. pm.md points to it and does not restate it.
- **If not fixed:** an agent obeying pm.md stops on one signal, and the same agent obeying the skill does not. The outcome depends on which file it read last.

### M3. pm.md's new habits contradict pm.md's own contract and §8
- **Log a defect.** `pm.md:118-120`: "A fault noticed in passing goes into the project's tracker at once ... never 'say if you want it logged'."
  - It conflicts with §1 `pm.md:20-21`: "A choice that changes cost, scope, anything other people will see, or a permanent record belongs to the owner."
  - A team tracker entry is both a permanent record and something other people will see.
- **Spend waves.** `pm.md:138-141`: "Before a chain of dependent work, open a spend wave."
  - It conflicts with §8 `pm.md:191-193`: "Each rule below applies where the owner uses that tool; none is required ... the PM does not start one unasked."
- **Engineer briefs.** `skills/step-back/SKILL.md:102-103`: "Brief every engineer and reviewer to run Seesaw and render the raw input before any fix."
  - It conflicts with `pm.md:56-60`: for /perma-change "the template wins; add nothing to it".
  - It also conflicts with `skills/live-prism/SKILL.md:11-12`: "Do not use it for a first, clean attempt that is working."
- **"Investigate before asking" (pm.md:128-130) against "puts the big things on the table and waits" (pm.md:20).** These are consistent. The habit keeps "scope, cost, what others will see" for the owner.
- **Fix:**
  1. Make the defect habit "record it in the stream at once; put it in the team tracker on the owner's standing yes".
  2. Make the spend-wave habit conditional: "where the owner uses spend.sh".
  3. Make the step-back hard rule defer to a command's template.
- **If not fixed:** the PM must break one rule to keep another, and it will pick differently each time.

### M4. Guess-word and fix-word detection refuses ordinary text, and the label that clears it disables the whole check
- **Where:** `runtime/decision.py:43-47, 296-309`.
- **Repro** (`$S/gates.sh` cases 2-3, 5):
  ```
  "Should we ship the pricing change?"     -> the question uses 'should': an inference
  "Which naming pattern do we keep?"       -> the question uses 'pattern'
  "Is the likely-loss field required?"     -> the question uses 'likely'
  "Is cfg.should on?"                      -> the question uses 'should'   (code identifier with a dot)
  "Is the fixed fee applied per policy?"   -> the question proposes a fix: give --upstream
  "Bump the patch version?"                -> the question proposes a fix: give --upstream
  --read src/contract.pdf                  -> that is an agent's record, not the source
  --read src/report.csv                    -> that is an agent's record, not the source
  --read src/review/rates.csv              -> that is an agent's record, not the source
  ```
- **Bypasses:**
  - Wrapping the whole question in double quotes passed: `"\"It is probably fine; should we ship?\""` -> d20261016-81daee.
  - `guess: none. It is probably fine...` passed (d20261016-55cd0d), because one `guess:` anywhere switches the whole scan off.
- **Handled correctly:**
  - `should_retry` is not flagged.
  - Single-quoted `'should'` is not flagged.
  - Apostrophes ("It's", "isn't") do not break the quote stripping.
- **What this means:** "Should we ...?" is the normal form of a yes/no decision question. Agents will learn to prefix `guess:` by reflex, and that turns the check off.
- **Fix:**
  1. Drop "should" and "pattern" from GUESS_WORDS, or flag them only outside a leading interrogative.
  2. Drop "contract" and "report" from REPORT_NAMES, or match only the run-record names (`NN-*.md` under `axis/runs/`).
  3. Make `fixed` / `patch` not count as "proposes a fix".
  4. Make `guess:` exempt only the clause it labels.
- **If not fixed:** the check rejects good questions and accepts labelled ones blind, so it measures nothing.

### M5. The shipped expert role forces the top model on every dispatch, against dev-team's own model rule
- **Where:** `runtime/agent-roles.json:72-77` (`"model": "fable"`, commit 905ce4e) and `runtime/agents/human-expert.md:13`, against `runtime/skills/dev-team/SKILL.md:88`: "**The most expensive model** — only when the owner explicitly asks."
- **How the role table works:** the table is shipped to every install, and its `model` is "forced on every dispatch of the role" (agent-roles.json `_about`). `runtime/agent-roles.py:76` ranks `fable` above `opus`.
- **The commit messages disagree:** db43c76's message says "a shipped role 'expert' (model opus; a project may pin another)". The table now says fable.
- **Fix:** ship `opus`, as db43c76 described. Put the owner's fable choice in `_personal/agent-roles.json`. agent-roles.json's own `_about` says that is where owner-specific providers belong.
- **If not fixed:**
  - Every install runs the expert at the most expensive tier without having asked for it.
  - The playbook says not to do that.

### L1. Skills wire: the edit check skips nested SKILL.md files, so an edit to one is moved to OS temp
- **Where:** `wire:119` (`diff -rq -x SKILL.md` excludes that name at any depth) and `wire:126`.
- **Repro** (`hJ`): the user edited `demo/ref/SKILL.md`. The re-run printed only `skill: demo`, and the edit went to `$S/tmpdir/tmp.J8lK5p/demo/ref/SKILL.md`.
- **Scope:** no shipped skill has a subfolder today.
- **Fix:** compare the top SKILL.md separately, and diff the rest with `-x` limited to the top level (or compare file lists).
- **If not fixed:** the first skill shipped with a nested reference file can lose a user's edit to OS temp cleanup.

### L2. Skills wire and its test write into the real per-user temp dir on every run
- **Where:** `wire:126` (`mv "$dst" "$(mktemp -d)/"`) and `runtime/tests/test_claude_code_skills.py:48-50`.
- **Why it escapes:** macOS `mktemp -d` with no template ignores a `TMPDIR` passed on the command line and uses the per-user temp dir.
- **Evidence:**
  - Each wire run left one `tmp.*` folder per skill in `<os-temp>` (3 per run).
  - Each unit-test run left a `demo` folder there. Folders from earlier runs by other sessions are present at 18:06, 18:08, 18:10 and 18:17.
  - The test docstring says it "never touches the real ~/.claude". That is true, but the test does write outside its temp dir.
- **Reviewer note:** my own first run left five such folders: tmp.x0IEmxeDMQ, tmp.GgQ0Nb9AXV, tmp.IDMKJIlgSZ, tmp.YQxn4cfQbO, tmp.PABZLyn9g2. A cleanup `rm` was refused by the permission classifier, so they remain. Later runs stubbed `mktemp` on PATH into `$S/tmpdir`.
- **Fix:** move the unedited copy to `"$SKILL_KEEP/.trash"` and remove it, or simply `rm -rf` it, since an unedited copy is by definition reproducible. The test should also set a temp root it owns.
- **If not fixed:** temp folders keep piling up with full skill copies, and the test is not hermetic.

### L3. Shipped "generic" skills carry the source project's domain and history
- **Where:** `skills/step-back/SKILL.md:17` ("no premium or rule moved"), `:55-56` ("raw → pre-processor → extracted → AI pass → assembler → rater → page"), `:35` ("per-product correction"), `:39` ("270 hand corrections on one product"), and `:69` ("work-order commits (`A<n>: …`)"); `skills/live-prism/SKILL.md:33` (`qlmanage`, macOS only).
- `pm.md:199`: "put to **him** as fact". The rest of pm.md uses "they" for the owner (pm.md:8).
- **No names:** no person's or employer's name appears. A grep for names and domain terms over the `+` lines found only the items above.
- **Against the CHANGELOG:** CHANGELOG says the items "were written generic before release".
- **Fix:** replace the pipeline and premium wording with neutral terms. Use "the owner". Mark `qlmanage` as a macOS example.
- **If not fixed:** other installs read one insurance pipeline as the general method.

### L4. pm.md cites a binding field that does not exist
- **Where:** `pm.md:216`: "The repo names its kinds: the binding's `census` pointer."
- **Evidence:** `grep -rln census runtime docs` finds only pm.md and one test string. Nothing in docs/PROJECT-TEAM.md's binding description, preflight or any job reads a `census` key.
- **Fix:** document the key in PROJECT-TEAM.md's binding section, or drop the sentence.
- **If not fixed:** an agent goes looking for a field no binding has, then asks the owner every time.

### L5. The dev-team frontmatter check snippet is broken
- **Where:** `skills/dev-team/SKILL.md:145`.
- **Evidence:**
  - The regex `r'^---.n(.*?).n---'` has lost its backslashes. It fails to match human-expert.md, step-back and live-prism. Measured: `snippet-regex match: False` for all three; the correct `\n` regex matches all four.
  - It also needs PyYAML, which is not in the standard library and is not installed on this machine (`ModuleNotFoundError: No module named 'yaml'`).
- **Fix:** restore `\n`, and give a stdlib-only check.
- **If not fixed:** "prove it parses" reports a valid file as broken.

### L6. Smaller doc inaccuracies
- **docs/TOOLS.md, new text:** "installed into `~/.claude/skills/` (Claude Code only, **like the agents**)".
  - This is false. The Antigravity wire installs the agents too (docs/PROJECT-TEAM.md: "The shipped agents, translated ...").
  - Verified: `agents-install.py` wrote `human-expert/agent.md` with `model: pro`.
- **CHANGELOG:** "makes `/perma-refactor`'s existing reference to the step-back skill resolve **for every install**".
  - The same entry says Antigravity does not get the skills, so it is true for Claude Code installs only.
- **docs/TOOLS.md:88:** the "writes" column for spend.sh omits `<stream>/TOOLS.md`. spend.py:253-264 now appends lesson stubs there. CHANGELOG's "nothing in any stream changes shape" leaves out this new stream write.
- **docs/PROJECT-TEAM.md and agents-install.py docstring:** the tier mapping is stated as "opus is pro; sonnet and haiku are flash". `fable` (now the expert's model) is mapped in code (`TIER`) but not in either text.
- **pm.md's own examples:** "Never illustrate with invented data" (pm.md:124) sits in a file whose own examples are invented: `pm.md:80` (the 50 MB shortcut) and `pm.md:113` ("N2 — close the design gaps"). These are low risk, but the rule as worded catches them.
- **If not fixed:** readers trust docs that are wrong in small ways.

---

## Checked and holding

- **Unit tests:** `python3 -m unittest discover -s runtime/tests` -> `Ran 206 tests in 42.825s  OK`.
- **Wire run twice:** the installed trees are identical (`diff -r` clean, "IDENTICAL"), and exit is 0 both times.
- **A user's own same-named skill (no marker):** `ATTENTION ... left as it is`, and the content is unchanged ("my own").
- **A user's skill whose last line carries the marker for its own name:** it is treated as ours. It is not lost: it is kept in `skills-perma-bak/dev-team.<ts>/` or `skills-perma-removed/mine.<ts>/`.
- **An edited copy re-installed twice:**
  - The first keep was `step-back.20261016182133`.
  - The second run kept nothing, which is correct: there was no edit.
  - The earlier keep was not overwritten.
  - (The same-second collision is H4.)
- **Extra user files inside an installed skill:** detected as an edit and kept.
- **A shipped skill removed from runtime/skills/, including a name with a space ("my skill"):** retired to `skills-perma-removed/my skill.<ts>/`. Nothing left in `skills/`.
- **`~/.claude/skills` as a symlink:** installs through the link. Kept copies go to the sibling `skills-perma-bak`.
- **A dangling symlink at a skill name:** `FAILED to copy`. The link is untouched and nothing is written to its target.
- **Moved copies:** nothing the block moves lands inside `~/.claude/skills/` on any path tried. The exception is the fresh nested copy in H4.
- **Old ledgers:** a decision ledger written by main's decision.py scores, reviews, renders and answers should-ask under v1.11.0. A spend ledger written by main's spend.py reads under status and report, and it counts toward the architect gate.
- **The expert role:**
  - `team_roles.resolve('expert')` gives `human-expert`.
  - When `human-expert` is not installed, it falls back to `session`.
  - `change:expert` gives `human-expert`.
  - Preflight checks only the job roles (`JOB_ROLES`). `expert` is not one, so there is nothing more to check.
  - The Antigravity translation gives `model: pro`, and the tools are mapped.
- **CHANGELOG claims that are true:**
  - the marker;
  - same-named skill left alone;
  - edited copy kept outside `skills/`;
  - "a ledger already written is read as before";
  - the hand-copied human-expert.md note;
  - nine agents.

## Verified / Unknown ledger

| Claim | Status | How |
|---|---|---|
| Header examples of decision.sh and spend.sh, and the runtime/README example, are refused | Verified | ran them, outputs quoted |
| Gates accept ".", a directory, /etc/hosts, a nonexistent task with --recheck, repeated round 1 | Verified | gates.sh, spend.sh, ledger ids |
| Failed `mv` leads to a false "kept" message, a nested `skills/demo/demo/SKILL.md` and exit 0 | Verified | blk.sh, hD and hE2 |
| Claude Code loads a nested `~/.claude/skills/x/x/SKILL.md` as a second skill | **Unknown** | not tested in a live Claude Code session |
| An untouched copy is reported as "edited" after an upstream change | Verified | hF |
| A nested SKILL.md edit goes to OS temp | Verified | hJ |
| mktemp ignores a command-line TMPDIR on macOS, and the test leaks to /var/folders | Verified | `TMPDIR=$S/tmpdir mktemp -d` printed a /var/folders path; leftover dirs listed |
| pm.md and step-back contradict on one signal against two | Verified | quoted lines |
| fable is the most expensive tier | Inference | from agent-roles.py:76 ordering and dev-team wording; price not checked |
| No person's or employer's name in the diff | Verified (bounded) | grep of the `+` lines for names and domain terms; a name outside that word list would not be caught |
| Old ledgers read and score | Verified | main's decision.py and spend.py wrote them; v1.11.0 read them |
| The Antigravity wire end to end (beyond agents-install.py) | Unknown | only agents-install.py was run |
| install.sh end to end | Unknown | not run; the wire was run directly with HOME and PERMA_DIR in scratch |
