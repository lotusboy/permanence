# Predicted-moves gate

> Optional. Moved here from `README.md` in v1.7.1; the text is unchanged.

**The problem.** A stop rule written in prose is enforced only when an agent chooses to stop. On
2026-10-10 an engineer's change moved a gap count from 9 to 11. No move had been predicted. The
engineer judged the move fine and committed. Nothing compared the prediction with the measurement.

**What the gate does.** It compares a structured prediction with two flat measurements, taken
before and after the change. It exits non-zero on any move nobody predicted. It is generic: it knows
no repo. Each key is a name the repo's own measurement scripts emit.

**The three files**, kept together in one run folder:

| File | Written | Holds |
|---|---|---|
| `moves.prediction.json` | before the first edit | the predicted moves |
| `moves.baseline.json` | measured before the change | flat `{key: value}` |
| `moves.measured.json` | measured after the change | flat `{key: value}` |

The prediction file is JSON. A `.yaml` file works too, when PyYAML is installed. Example:

```json
{
  "about": "A496: the caveat drop rule",
  "moves": [
    {"what": "gaps:unfaithful-logic", "from": 9, "to": 11, "scope": "product-a"},
    {"what": "rules:fired:product-a", "delta": 2},
    {"what": "gaps:capture", "range": [360, 375]},
    {"what": "definition:file-hash:product-a"}
  ],
  "mustNotMove": ["premium:*"],
  "tolerance": 0.005
}
```

Rules for the prediction:

1. A move gives exactly one of: `to` (with `from` optional), `delta`, `range` [low, high] for the
   value after, or nothing. Nothing means "moves, any value". Use it for a hash.
2. `what` and `mustNotMove` entries may use `*` and `?`.
3. A key a move names is judged by that move, even when a `mustNotMove` glob also matches it. So
   `"mustNotMove": ["premium:*"]` beside one predicted premium move means "no other premium moves".
4. `scope` is a label for the reader. It does not change matching.
5. `tolerance` is an absolute numeric tolerance. The default is 0.

**Run it.**

```bash
~/permanence/runtime/predict-gate.sh check --prediction moves.prediction.json --measured moves.measured.json
# --baseline defaults to moves.baseline.json beside the measured file
```

It reports six sections:

1. Predicted, and it happened.
2. Predicted, and it did not happen. This is reported. It does not stop the commit.
3. Predicted to move, and it moved to a different value. This stops the commit.
4. Moved, and nobody predicted it. This stops the commit.
5. A `mustNotMove` key moved. This stops the commit.
6. A `mustNotMove` entry matched no measured key, so it is unproven. This stops the commit.

A key that appears or disappears counts as a move. Exit codes: 0 pass, 1 refused, 2 bad input.

**The owner's exception.** `--override "<reason>" [--task <id>]` turns a refusal into a pass. The
gate writes one `gate-refused` line, outcome `done`, to the repository's ops ledger through
`ops-event.sh`. The line carries the reason and the refused keys. If the line cannot be written, the
override is refused. An override is never silent. An override on a passing check records nothing.

**Before every commit.** `predict-gate.sh install-hook <repo>` writes a pre-commit hook into that
repository's local `.git/hooks`, which git never commits. Nothing installs it for you.

1. The hook acts only when a commit stages a `moves.measured.json`. A commit with only the
   prediction (the "before the first edit" commit) passes through.
2. It checks each folder that holds a staged `moves.measured.json`. It reads all three files from
   the index, so it checks what is being committed, not the working tree.
3. A staged measurement with no prediction or no baseline beside it is refused.
4. The owner's exception: `PREDICT_GATE_OVERRIDE="<reason>" PREDICT_GATE_TASK=<id> git commit ...`.
   The override is recorded as above.
5. The installer leaves a pre-commit hook it did not write alone. It also skips a repository that
   sets `core.hooksPath`. In both cases it prints the one line to add to the existing hook.
6. To remove the gate, delete `.git/hooks/pre-commit`.
