# Axis Contract — v1.9.0 adversarial review

```
AXES:        Genba + Shoshin (read the changed text fresh, as the agent that will obey it) ·
             Chaos Engineering (find the input or the reading that makes an instruction misfire) ·
             Poka-yoke (does each new rule still hold when followed literally)
TARGET:      branch v1.9.0-shortcuts vs main: runtime/roles/pm.md, runtime/commands/perma-health.md,
             runtime/agents/design-reviewer.md, runtime/agents/refactor-reviewer.md, CHANGELOG.md [1.9.0],
             and the two doc table rows. Instruction text only; no code changed.
STRUCTURE:   BLUF, then findings most severe first: file:line, the exact case, a suggested fix
EVIDENCE:    every finding either reproduced (a command run in a scratch repo) or quoted from the text
ASSUMPTIONS: Verified/Unknown ledger
STOP:        Andon on: an instruction that can make an agent write to a repo it does not own;
             one that contradicts another shipped instruction; a rule that weakens a safety limit;
             a change to a file every session loads; Ponytail text copied rather than reworded.
```

Single adversarial pass, one agent. The release changes instructions, not code, so the risk is in
how an agent reads them.
