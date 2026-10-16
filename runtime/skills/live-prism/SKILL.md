---
name: live-prism
description: >-
  Run Axis Prism on a LIVE item that is resisting: stop refining one approach and refract the
  actual input through at least three lenses until its real shape shows. Use this skill whenever a
  fix needs a second guard or exception, a heuristic keeps growing special cases, a reader or parser
  misreads a document, data "cannot" be got out of a file, the same failure repeats after a fix, a
  review keeps finding false positives, or an estimate keeps growing — and whenever the user says
  "how hard can it be", "have you looked at it", "poke it", "twist it", "keep pulling", "what does
  the raw file look like" or "screenshot it". Also use it before designing any fix to how a
  document, spreadsheet, PDF, form or data feed is read. Do not use it for a first, clean attempt
  that is working.
---

# Live Prism — refract the item that is resisting

Prism normally models a system from raw material at the start. Live Prism is the same move made
mid-fix, on the one item that will not yield. The rule: **when a fix needs its second guard, stop
writing rules and look at the input from more sides.** Repeated failure at one layer is evidence
that the answer is in what that layer is given (Seesaw).

Prism and Seesaw are protocols from the axis-engineering methodology, a separate and optional public
companion (https://github.com/lotusboy/axis-engineering). This skill carries everything it needs to run
on its own; install axis-engineering for the full protocols.

## The loop

1. **Name the item and the symptom** in one line: which file, sheet, page, record or call, and
   what comes out wrong.
2. **Refract it through at least three lenses.** Pick the ones that fit; write down what each
   showed, even "nothing":
   - **What a person sees.** Render it. An xlsx sheet: copy the workbook, delete every other sheet
     with openpyxl, render it (on macOS: `qlmanage -t -s 2200 -o <dir> <file>`), then read the PNG. A PDF page:
     render the page. A web page: screenshot it.
   - **What the author declared.** Styles (bold, fills, borders, merged cells), Excel tables and
     named ranges, data-validation source ranges, number formats, comments and margin notes,
     headings, document properties.
   - **What the machine uses.** Formulas and the ranges they read, lookups, code paths, API
     fields actually consumed.
   - **What the reader is given.** The exact bytes the failing layer receives (a CSV export, a
     truncated string, a flattened table) — compared side by side with the raw item.
   - **What breaks it.** Odd inputs, an empty or huge value, the item reversed or shifted, two
     copies compared, the item with one part removed.
   - **What a second source says.** Another version of the file, another document stating the
     same thing, a built system that already consumes it.
3. **Lay the findings next to each other.** Where two lenses agree on a boundary or a value, that
   is evidence. Where the reader disagrees with all of them, the reader was given too little.
4. **Decide the fix from the strongest evidence**, preferring what the author declared over what
   has to be inferred. Keep inference only as the fallback for inputs that declare nothing.
5. **Measure it on every case it touches** before switching anything, and say which lens each
   rule rests on.

## Hard rules

- Never add a third guard to a heuristic without having run this loop.
- Never declare, label or classify a misread away; a misread is fixed at the source.
- Report what each lens showed, in plain sentences, before proposing the fix.
- When delegating, put "run Live Prism on the input first: at least three lenses, findings
  listed" into the engineer's brief.
