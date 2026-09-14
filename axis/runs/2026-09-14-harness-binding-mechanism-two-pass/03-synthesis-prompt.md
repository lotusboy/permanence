# Merge instructions

Apply `two-pass-strategy.md`'s Merge Contract exactly:

- **Dedupe key:** `(artifact, symptom, root-cause-class)`. Two findings about the same artifact
  with the same root cause merge into one.
- **Severity:** `max(pass1_severity, pass2_severity)`.
- **Conflicts:** if Pass 2 contradicts Pass 1, prefer Pass 2 if it has stronger evidence (more
  file:line citations, verbatim snippets, live reproduction). Pass 2 reads fresh without anchoring
  on Pass 1.
- **Unique findings:** included as-is, with source attribution (Pass 1 / Pass 2 / both).

Performed by the orchestrating session directly (not a third subagent), since both raw outputs
were already being read in full to check the run's own health before reporting back to the user —
spinning up a separate merge agent would have meant re-reading both outputs a second time for no
additional isolation benefit (the merge step doesn't need to be blind to anything; only Pass 2
needed isolation from Pass 1). Per the Merge Contract's own stated risk ("the third agent
synthesising two reviews may fabricate connections... or invent severity escalations"), the same
risk applies to a first-party synthesis too — mitigated the same way: every merged finding below
traces to a specific citation in one or both raw outputs, and no finding's severity was raised
without a citation from the higher-severity pass justifying it.

## Real disagreement found and resolved

Pass 1's Finding 7 hypothesized that two **cleanly-separated, well-formed** `perma:begin`/`end`
pairs would cause `block-merge.sh`'s `awk` splice to duplicate the injected block, but explicitly
labeled this "theoretical... not because I found a live trigger." Pass 2's Finding 10 **directly
tested that exact scenario** (two clean, separated pairs) and found it works correctly — no bug —
but then found a *different*, narrower case (overlapping/improperly-nested pairs) that does
reproduce duplication.

Per the merge contract, Pass 2's live reproduction is stronger evidence than Pass 1's theoretical
reasoning about the same code path. **Pass 1's Finding 7 is retracted; Pass 2's Finding 10 replaces
it** as the accurate version of this finding. Noted explicitly in the synthesis below rather than
silently dropped, since Pass 1's underlying instinct (the marker-mismatch guard doesn't handle
every malformed case) was directionally right even though its specific repro claim was wrong.
