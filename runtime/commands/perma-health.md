---
description: "Health watch for the current repo — run preflight, rewrite the repo's health register in its Permanence stream from the binding's signal, list the parts that are ready, then offer a refactor (a repo you own) or draft a proposal for the repo's approver (a repo another party owns). It never starts work. Trigger phrases: \"health check this repo\", \"what is ready to refactor\"."
harness: claude-code
---

# Permanence — Health

The health watch for *this* repo. It says where to look. It never starts work.

The watch is deterministic and costs no AI spend: it runs one command and reads one file. Every repo
fact — the register's name, the signal, who owns the repo, who approves — comes from the repo's
binding, `<stream>/repo/binding.json`. Never use a path, command, threshold or part name that the
binding and the register do not give you. A copied fact would bind every repo to the one it came from.

## How to run it

1. **Preflight.** From the repo root, run:

   ```
   python3 ~/permanence/runtime/team-preflight.py health --repo "$(git rev-parse --show-toplevel)"
   ```

   - It exits non-zero: show its output and stop. Change nothing. A missing binding means the team
     does not apply to this repo; say that plainly. Never guess a repo's commands.
   - It exits 0: carry on. A `note` line is not a failure. Keep a note that the generic signal
     script is not installed yet: step 3 needs it.

2. **Find the stream and read the binding.**
   - Run `~/permanence/runtime/resolve-stream.sh "$(pwd -P)"`. The stream folder is
     `~/permanence/<stream>/`.
   - Read `~/permanence/<stream>/repo/binding.json`. Keep `owned`, `approver`, `register` and
     `signal`.
   - The register's full path is `~/permanence/<stream>/repo/<register>`, with `~` expanded. This is
     the value of `{register}`. The value of `{root}` is the repo root from step 1. The value of
     `{date}` is today, as `YYYY-MM-DD`.

3. **Get the signal command.** `signal` takes one of three forms.
   - **A command** (a string with spaces and no `#`): use it as it stands.
   - **A pointer** (`file#key.id`): open `file` in the repo root. Find the item under the top-level
     `key` whose `id` is `id`. Its `command` is the signal command. A pointer that does not lead to
     exactly one command: stop and say so.
   - **Rules for the generic script** (an object with `script`): the command is
     `python3 ~/permanence/runtime/<script>.py`, called as that script's own usage line says, with
     the binding and `{register}`. If preflight noted that the script is not installed, or
     `~/permanence/runtime/<script>.py` does not exist, stop here and say "the generic signal script
     is not installed yet". Run nothing, write nothing, and skip steps 4 to 7. This is a clean stop,
     not an error.

   Fill `{root}`, `{register}` and `{date}`. If any `{…}` or `<…>` is left, stop and say which: the
   health watch has no value for it.

4. **Run the signal.** Run the filled command from the repo root, once. Show its printed output.
   - It exits non-zero: show the error and stop. Do not retry with other arguments.
   - It rewrites the register in the stream and nothing in the repo. The signal never overwrites a
     part's `decision`. Neither does this command.

5. **List the ready parts.** Read the register. List every part under `parts` whose `state` is
   `ready` or `ready-again`. For each, give one line:
   - the part id, its `signal`, its `fixCommits`, and its `topIds` if any;
   - for `ready-again`, also the earlier `decision`: its `date`, its `decision` and its
     `signalAtDecision`, because the signal has regrown since then.

   Say the count outright, and the `computed.asOf` and `computed.threshold` it was measured against.
   No ready part is a normal result: say "no part is ready" and skip step 6.

6. **Offer or propose, by ownership.** A ready part is an offer, never an order.
   - **`owned` is true.** Offer the owner one refactor per ready part, in one line each:
     `/perma-refactor <part>`, and that it starts only when the owner says so. If `/perma-refactor`
     is not installed, say so; the decision is still the owner's: restructure or accept. Do not start
     the refactor, write a decision, open a branch or brief an agent.
   - **`owned` is false.** Draft a proposal for the owner to take to the binding's `approver` — name
     the approver by that role, never by a person's name. For each ready part, the proposal states:
     the part id; the figures from step 5; what a refactor would do (restructure the part, behaviour
     unchanged, output only a pull request); and the approval it needs, a scope of exactly
     `{"part": "<part id>"}`. Show it in chat. When the owner says to keep it, add it to the stream's
     `WIP.md` as one row under a short proposal id: an approval later cites that id. Nothing is
     started. Nothing is written to the repo, its tracker or its branches.

7. **Commit the register.** In `~/permanence`, if the register changed, `git add` that one file by
   its path and commit it: `health(<stream>): register as of <computed.asOf>`. Never `git add -A`:
   other sessions may have writes in flight. Nothing changed: say so; make no empty commit. Never
   push.

## Guardrails

- **Watch only.** It reads, counts and writes the register. It never starts a refactor or a change,
  whatever the figures say, and even when the work looks small.
- **Facts from the binding.** Every repo path, command and owner rule comes from the binding or the
  register. If the binding lacks something this procedure needs, stop and say which field.
- **A repo another party owns is read-only.** The checkout is never written: no file, branch, hook,
  tracker item or commit. The only output is a proposal, which stays in the stream.
- **One-way flow.** The register lives in the stream. Never write a Permanence path or name into the
  repo's files.
- **Plain report.** Counts, not adjectives. State the result outright: how many parts are ready, and
  what the owner can decide.

If `~/permanence` is missing or this workspace has no stream, say so plainly rather than inventing content.
