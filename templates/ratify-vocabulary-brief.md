# Vocabulary blind-reader brief — reader {{READER}}

You are reader **{{READER}}**, an independent reader. Another reader may be given the same entries.
You must not look for, read or ask about anyone else's answers.

## The task

A system holds a closed vocabulary. Each entry maps a pattern to a class. For example, the phrase
"We will not cover …" maps to the class `exclude`. Every passage the pattern matches is given that
class.

For each of the {{COUNT}} entries below, read every sample match and answer one question:

> Is this class right for the passages this pattern matches?

## The entries and their matches

`{{SAMPLE}}`

Each entry shows its pattern, the class it assigns, how many passages it matches in the whole corpus,
and a seeded sample of those passages. Each sample gives its document and its place in the source.

Entries: {{IDS}}

## The source

{{SOURCE}}

Where a sample is unclear on its own, open the source at its pointer and read the passage in place.

## Answer vocabulary

Exactly one label per entry:

- **RIGHT**: the class is right for every sample.
- **WRONG**: the class is wrong for every sample, or for most of them.
- **MIXED**: the class is right for some samples and wrong for others. The pattern is too broad, or
  it catches two kinds of passage.

## Do not read

- Any other reader's report or output.
- The PM's notes, plans or messages about these entries.
- The code or configuration that holds the vocabulary, and any note on why an entry was added.

If you open one of these by accident, say so in your report.

## How to read

1. **Read each sample in full.** Judge the passage, not only the matched words.
2. **Quote verbatim.** For a WRONG or MIXED entry, quote the sample that shows the class is wrong,
   with its sample number and pointer.
3. **Mark fact and inference.** Begin each sentence of reasoning with FACT (it is in the quote) or
   INFERENCE (your reading of the quote).
4. **One label and one recommendation per entry.** For WRONG or MIXED, the recommendation says the
   fix: narrow the pattern, change the class, or split the entry.
5. **Confidence.** A number from 0 to 1 for each entry.

Do not edit files, commit, or start other agents.

## Report shape

For each entry:

```
### <id>
Samples right: <n of m>. Samples wrong: <sample numbers>
Quote: "<verbatim>" — sample <n>, <pointer>
FACT: …
INFERENCE: …
Label: <RIGHT | WRONG | MIXED>   Confidence: <0-1>
Recommendation: <one sentence>
```

End the report with exactly one JSON block, and nothing after it:

```json
{"reader": "{{READER}}", "items": [
  {"id": "<entry id>", "label": "<RIGHT | WRONG | MIXED>", "confidence": 0.9,
   "wrongSamples": [3, 5], "quote": "<verbatim, short>", "where": "<sample n, pointer>",
   "recommendation": "<one sentence>"}
]}
```
