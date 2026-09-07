# Consolidation Report — 2026-06-28-0530

> **Illustrative.** Run against `example/` (fictional) to show the shape of a real `/perma-consolidate` report — the format is exactly what a run against your own streams produces. Nothing here is applied automatically; this is what `/perma-consolidate-review` would walk you through next, one item at a time.

## Mechanical edits (ready to apply, recommended)

**Mechanical 1 — `example/home/bathroom/PROJECT.md`: current phase is behind the LOG**

The LOG has moved past what `PROJECT.md` still says.

- Source, `LOG.md` 2026-06-08: "Replaced the DIY silicone bead with a proper job... Snagging effectively done — the room is finished."
- Current `PROJECT.md`, "Current phase": `**DONE (2026-05-30).** Painted terracotta; chuffed with it. Snagging only.`

Proposed edit:

```diff
- **DONE (2026-05-30).** Painted terracotta; chuffed with it. Snagging only.
+ **DONE (2026-06-08).** Painted terracotta; snagging complete — basin seal redone properly. Room finished.
```

Also drop the "Open" line about the cracked basin seal once you confirm it — the LOG only confirms the seal, not the woodwork touch-up, so that half stays open pending your check.

## Needs a verdict

**Verdict 1 — `example/home/kitchen/PEOPLE.md`: Jamie's inference is 18 days old with nothing closing it**

- Inference (2026-06-10, provisional): "likely a genuine supplier issue rather than over-booking... revisit if the 24th also moves."
- The 24 Jun fit date it was hinging on has now passed; `LOG.md`'s most recent entry is still 2026-06-10 — nothing in the stream says whether the date held.
- Your call: **confirm** (the 24th went ahead), **revise** (a different reason came up), **wrong** (it slipped again — the "one slip" read becomes a pattern worth naming, still as behaviour, not character), or **prune** (moot now, e.g. the worktop's in regardless).

## Proposed moves

**Move 1 — `example/home/kitchen/QUESTIONS.md`: Q1's own deadline has passed**

- Q1 ("Which handles? — must be decided before Jamie drills, fit day 24 Jun") is still open; the date it's gated on has come and gone with no LOG entry either way.
- Either the handles got decided (close it with the answer) or the fit slipped again (update the question's own deadline so it doesn't quietly go stale). Flagging the mismatch, not guessing which.

---

**Summary:** 1 mechanical edit ready to apply as-is, 1 inference needing your call, 1 question whose own deadline needs revisiting. Nothing here has changed anything — that's what `/perma-consolidate-review` is for.
