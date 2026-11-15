<!-- perma:begin (managed by ~/permanence/runtime/install.sh — edit ~/permanence/runtime/devin-agents-md-block.md, not here) -->
## Permanence protocol (standing instruction)
This session's project context loads automatically at the start of each session and on your first message — no manual step needed. The one thing those hooks can't do for you: whenever something material shifts during the session (a decision, a scope change, a meeting, anything that moves the picture), update the active stream's files without being asked — see `~/permanence/SPEC.md` for the full contract. Never reference Permanence's paths or contents in any file committed to a project repository (one-way flow).

### In every session

**Drift count (a tiredness proxy).** You cannot feel your own error rate rise, so count it. Each session, from zero, count three kinds of event: a scratch-script error (a one-off measurement reported, or nearly reported, wrong); a self-contradiction (a later check of the same thing gives a different number); a re-derivation error (a fact established earlier in the session rebuilt from memory, wrongly). At 3, say so in one line and switch method: use tested code paths, and cross-check each new number before reporting it. At 5, recommend stopping. Report it as a rate, not a crisis. It tends to rise with novel one-off scripts, long runs of "keep going", and very long contexts.
<!-- perma:end -->
