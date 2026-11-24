---
description: Daily morning brief — current state across all active Permanence project streams
---

# Permanence — Daily Brief

Produce my morning briefing from Permanence at `~/permanence`. This is the first thing I read each day, so optimise for fast orientation: what's live, what's next, what needs me.

## How to build it

1. **Timeline first.** Run `git -C ~/permanence log --pretty=format:"%ad  %s" --date=short -20`. This is the canonical chronology of what's moved across all streams — read it before anything else so the per-stream reads land in context, and so a stream whose `PROJECT.md` is stale doesn't fool you about recency.
2. **Discover the active streams:** run `~/permanence/runtime/list-streams.sh`. Each line is a stream name, a tab, and its folder under `~/permanence/`. Brief every stream it lists except `perma-meta`. Don't assume the set — new streams appear automatically.
3. **For each stream**, read:
   - `PROJECT.md` (the "Current phase" / headline blocks), noting its `Last updated YYYY-MM-DD` header
   - The **tail** of `LOG.md` (most recent entries only — don't re-read history), noting its most recent date header
   - `QUESTIONS.md` if present — pull only the still-**open** questions (not ones marked `[CLOSED ...]`)
4. **Staleness flag.** If a stream's most recent `LOG.md` entry is dated AFTER its `PROJECT.md`'s `Last updated` header, the project file is behind the log — flag this explicitly in the brief (a one-liner like *"⚠️ home/kitchen/PROJECT.md last updated 2026-06-02 but LOG has a 2026-06-10 entry — headline may be stale"*). This catches the failure mode where a milestone hits the LOG but PROJECT.md hasn't been bumped.
5. **Dates.** Resolve every relative date against **today's actual date**. Call out anything dated within the next ~5 days, and flag anything already overdue.
6. **Consolidation surface.** Check `~/permanence/.consolidation/` for `REPORT-*.md` files sitting at its top level (reviewed ones live under `done/`) — each is an **unreviewed consolidation report** waiting for `/perma-consolidate-review`. Without this step the nightly "dreams" land silently and rot.

   **An empty `.consolidation/` does NOT mean "caught up" — it is ambiguous**, and you must resolve it before saying anything reassuring. It means either *nothing needed doing* or *nothing ran*. Always read the tail of `~/permanence/runtime/logs/nightly-consolidate.log` to tell them apart:
   - most recent line is `run complete` → genuinely caught up, say so;
   - `ERROR` / `SKIPPED` / no line for last night → **the nightly did not produce a report**; report that plainly, with the reason from the log. A run that exits 0 but writes no report is logged as an `ERROR` by design, precisely so this case cannot read as healthy.
   - log missing entirely → the nightly has never run; say that rather than implying all is well.
7. **Stale loops.** Run `~/permanence/runtime/stale-loops.sh`. It lists open loops nobody has come back to: open questions and board rows (Now, Blocked, Parked) more than 14 days old, or past their `by:` date, and LOG lines saying "not yet read", "to confirm", "unconfirmed", "probably overtaken" or "no owner". At most 10, and at most 3 from one stream, oldest first. It can take a few seconds on a long history. Print its output as it is, under **Stale loops**. It prints nothing when the owner has switched it off in `runtime/.stale-loops`; then omit the section. Do not answer the choices yourself, and change no file: the owner chooses for each item, in the session that follows.

## Output shape

Keep it tight — a screen or so, scannable, no preamble.

- **One line per stream**: name → current phase → the single most imminent thing.
- **This week / Next week**: group dated items by the **actual calendar week** they fall in — "this week" = the Mon–Sun block containing today; anything in the following Mon–Sun block goes under a separate **Next week** line; further out gets an explicit dated "Later" line. Never file a following-week item under "This week" (the failure this section was added to fix). Include not just external milestones but what *you're actually doing* on the near days — prep days, focus blocks — soonest first. Flag overdue items. Anchor every this/next-week judgement to today's real date.
- **Needs me**: open questions or decisions actually waiting on me — not the full backlog. Omit the section if there's nothing.
- **Recently moved**: 2–3 bullets on what changed most recently (from the git timeline + LOG tails).
- **Staleness**: any `PROJECT.md` files behind their stream's LOG (per step 4). Omit if everything's fresh.
- **Stale loops**: the output of step 7, word for word (one line when nothing is stale). Omit only when it printed nothing.
- **Consolidation**: unreviewed reports (name + date, suggest `/perma-consolidate-review`) and any failed/skipped nightly run (per step 6). Omit if none and the last run was clean.

## Voice

These are working notes — internal phrasing can be blunt. Render anything that reads coarse, bleak, or dramatic into a gentle, accurate register. Same meaning, safer key. This is a briefing for me, not a team-facing artefact, so stay direct and honest — just kind in tone.

If `~/permanence` is missing or has no project streams, say so plainly rather than inventing content.
