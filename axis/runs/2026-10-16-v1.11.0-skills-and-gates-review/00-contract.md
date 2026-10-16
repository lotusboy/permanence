# Axis Contract — v1.11.0 adversarial review

```
AXES:        Genba + Shoshin (read the real text and code fresh) · Chaos Engineering (break it) ·
             Poka-yoke (are the new gates real, and do they block only what they should)
TARGET:      branch v1.11.0 vs main (178bdf3), three commits: (1) a package of three skills and a
             skills-install block in runtime/bindings/claude-code/wire; (2) decision.sh / spend.sh
             gates, PM role and /perma-change rules, the human-expert agent and role; (3) five PM habits.
STRUCTURE:   any ANDON first; BLUF; findings most severe first with file:line, repro, fix, "If not fixed:"
EVIDENCE:    every code finding reproduced in a scratch HOME / scratch repo; every text finding quoted
ASSUMPTIONS: Verified/Unknown ledger
STOP:        Andon on: a user's own skill, agent or file lost or overwritten without a kept copy; a moved
             skill landing back inside ~/.claude/skills/ (it would load twice); a gate that refuses a
             call every existing user makes, or one that can be passed without the evidence it asks for;
             a contradiction between shipped instructions; a private or work name in the diff.
```

Single adversarial pass, one agent.
