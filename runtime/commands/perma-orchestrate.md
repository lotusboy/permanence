---
description: Generative orchestration pass over Permanence — detect cross-stream convergence, entangle, and propose emergent ideas into the _meta/emergent.md ledger. Divergent counterpart to /perma-consolidate; proposes only, never edits a stream.
---

# Permanence — Orchestrate (generative pass)

The divergent counterpart to `/perma-consolidate`: where consolidation finds similarity and settles it, this pass finds **independent streams converging on the same shape** and amplifies the connection toward an idea none of the sources held alone. This file is self-contained — run it as written. *(Advanced: only useful once you have several streams. Fuller design background — the discriminator's lens vocabulary, thresholds, independence test — is **not shipped in this starter** and isn't needed to run.)*

**Hard safety contract:** read-only over every stream. The ONLY file this pass writes is `~/permanence/_meta/emergent.md` (the ledger). Never edit, commit to, or branch any stream; never run during a `.perma-lock`. Manual/human-triggered only — never scheduled. Best run after a consolidation review has cleared the noise floor (un-deduped intra-stream repetition reads as false convergence; say so in the report if consolidation looks overdue).

## The pass

1. **Orient.** Read the ledger (`_meta/emergent.md`) — note `last-run`, existing candidates and their statuses. Read the git timeline since last-run: `git -C ~/permanence log --pretty=format:"%ad %s" --date=short --since=<last-run>`.
2. **Build per-stream digests of moves** per the discriminator §1: for every stream `~/permanence/runtime/list-streams.sh` lists (perma-meta first), reduce activity-since-last-run to move lines — `stream · date · lens-tag(s) · gist · source ref` — using the lens vocabulary (discriminator §2). Tag the *process* of each move, not its topic. A stream with no real moves gets none — don't pad (honest "doesn't fire" is signal).
3. **Detect convergence.** Group moves by lens; for each lens firing in ≥2 streams with substantive gists, run the independence checks (discriminator §4: citation scan, common-cause, temporal). Score each surviving shape by count of independent streams.
4. **Re-score the existing ledger.** For every open candidate: new supporting moves → strengthen (possibly nascent → ripening, or across the surface threshold); nothing new for ~6 passes/2 months → prune as coincidence (status `pruned`, dated, one-line why — close the loop, never silent-delete). Apply the owner's ratification verdicts from the conversation if he gives them.
5. **Update the ledger** (the one write). Each candidate entry carries: shape (one line), lens, contributing sources **quoted** with refs, independence notes (citation/common-cause flags), the emergent hypothesis as a dated provisional `[inference]`, strength (N independent streams), status (`nascent` / `ripening` / `surfaced` / `ratified → <stream>` / `pruned`), and history lines per pass. Bump `last-run`. New-lens needs become `lens-proposal` entries — never silently extend the vocabulary.
6. **Report by threshold.** Chat report: **surfaced candidates first** (≥3 independent streams — "an idea that wants to be born", with the hypothesis and what each stream contributed), then ripening (2, accumulating quietly — one line each), then prunes and lens-proposals. If nothing crossed threshold, say so plainly — a quiet pass is a healthy pass, not a failure. Never manufacture convergence to justify the run.
7. **Ratification is the owner's.** For surfaced candidates, ask the one plain question per candidate (discussion, not a menu — same style as the consolidation review): does this connection hold? Ratified → he decides which stream adopts it (that stream's session does the adopting write later; this pass still doesn't touch streams). Rejected → status `pruned` with his reason.

## Guardrails

- **Apophenia is the failure mode.** When in doubt a shape is lexical coincidence, log at sub-threshold rather than surface. If the owner rejects surfaced candidates repeatedly, the fix is the discriminator (raise threshold / tighten independence / sharpen gists) — propose that edit, don't just filter harder.
- **Voice:** the ledger is persisted — gentle, accurate register.
- **One-way flow:** stays entirely inside `~/permanence`.
- **No invention:** every contributing source is quoted and citable; a hypothesis must trace to its moves.
