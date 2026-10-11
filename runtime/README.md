# runtime/ — tools a session calls

Each tool's own header comment is its full reference. This page says what each one is for.

## spend.sh — measured wave spend

**Problem.** An agent's own report of its token use was off by up to 2x on 2026-10-10.
**The measured figure** is `subagent_tokens` in the harness's completion notification for that agent.
**What this does.** It records that figure per agent, groups agents into waves with a ceiling, and warns at 80% and stops at 100%.

- The ledger is `<stream>/spend/ledger.jsonl`. It is append-only.
- The stream resolves from the current directory through `_meta/REGISTRY.md`, or is named with `--stream`.
- A wrong row is never edited. `record --correct` appends a new row, and the latest row for an agent id counts.
- `record` run from inside an owned repo also writes that repo's ops ledger `agent-run` row through `ops-event.sh`. One command records both. `--no-ops` skips it.
- A row whose `--source` is not `harness` is shown as "not measured" in `status`.

```
spend.sh wave open s2-slice --ceiling 400000
spend.sh record --agent a1b2c3 --label "S2 answers r1" --tokens 131204 --kind answering-agent --task A508
spend.sh status                       # open waves: spent vs ceiling, per agent, warnings
spend.sh report --since 2026-10-10    # totals by day, wave, kind and source
spend.sh wave close s2-slice
```

## save-report.sh — save an agent's report verbatim

**Problem.** A subagent cannot write its own report file, so the PM re-typed reports, and re-typing introduces errors.
**What this does.** It reads the report on stdin and writes the bytes unchanged below a short header.
The header gives the title, the date, the source agent id, "saved verbatim by the PM", and the body's size and sha256.

- It refuses to overwrite an existing file. `--append` adds a new section; `--force` replaces the file.
- It creates missing parent folders and works for any path the PM names.

```
pbpaste | save-report.sh docs/runs/2026-10-10-s2/report.md --title "S2 slice report" --source-agent a1b2c3
```

Tests for both: `python3 -m unittest runtime/tests/test_spend_and_save_report.py`.

## ratify.sh — vocabulary ratification

**Problem.** A system holds a closed vocabulary: entries that map a pattern to a class (for example, the phrase "We will not cover …" maps to `exclude`). Entries get added during engineering without proof. Judging the list by eye puts the whole load on the owner.
**What this does.** For each entry it samples real matches from the project's own corpus. Two isolated blind readers judge each entry RIGHT, WRONG or MIXED. An entry is ratified only when both readers say RIGHT. The verdicts go to an append-only ledger. `check` then works as a gate.
The reading steps are in the two brief files `sample` writes (`brief-A.md`, `brief-B.md`): give each to one reader that has seen nothing else — a fresh agent, or a different model family. This tool is pure computation, standard library only, no AI.

**Verdicts.**
- `ratified`: every reader said RIGHT, or the owner approved a held entry (recorded as `ratifiedBy: owner`).
- `rejected`: every reader said WRONG or MIXED. It goes back for a fix and a new round. The owner cannot approve it with `--owner-approved`.
- `held`: the readers split, a reader gave no answer, or the entry matched nothing in the corpus.

**Interchange format.** A project writes two JSON files with its own small exporter. The tool never reads project code.

`entries.json` is an array. One object per vocabulary entry:

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | Stable id. It must not change when the pattern changes. |
| `pattern` | yes | The pattern text. |
| `patternKind` | yes | `regex`, `phrase` or `keyword`. |
| `class` | yes | The class the entry assigns. |
| `kind`, `source` | no | Engineering notes (what kind of rule, where it lives). Never shown to readers; not part of the hash. |

How each `patternKind` matches one corpus record:
- `regex`: Python `re.search`, as written. Put `(?i)` in the pattern for case-insensitive.
- `phrase`: case-insensitive. Any run of whitespace matches any run. Word edges are enforced, so `cover` does not match `coverage`. `…` or `...` means "any text here", within the same record.
- `keyword`: space-separated words. Every word must appear as a whole word, case-insensitive, in any order.

`corpus.json` is an array. One object per passage (a clause, a paragraph, a row):

| Field | Meaning |
|---|---|
| `docId` | The document the passage comes from. Sampling spreads across documents by this field. |
| `text` | The whole passage. Readers see it in full, never cut. |
| `pointer` | Where a reader finds it in the raw source: file, page, clause or cell. |

Optional `classes.json` is an object `{class: one-line meaning}`. Readers see it, so give it whenever classes are not self-explanatory.

**What an exporter must do.**
1. Read the vocabulary where the project keeps it (code, config, table). Write one `entries.json` row per entry, with a stable `id`.
2. Write the corpus at the same granularity the system classifies. If the system classifies clauses, one record is one clause.
3. Give every record a `pointer` a reader can open.
4. Write nothing else. The exporter makes no judgement.

A tiny example:

```
// entries.json
[{"id": "EXCL-01", "pattern": "We will not cover …", "patternKind": "phrase", "class": "exclude",
  "source": "rules/lead_ins.py:41"}]
// corpus.json
[{"docId": "wording-2024", "pointer": "wording-2024.pdf p.12, clause 4.2",
  "text": "We will not cover loss or damage caused by wear and tear."}]
```

**Commands.**

```
ratify.sh sample --entries entries.json --corpus corpus.json --per-entry 8 --seed 1 --out runs/2026-10-10-vocab --classes classes.json
#   -> runs/.../sample.json, readers-sample.md (what readers see), brief-A.md, brief-B.md
ratify.sh compare runs/.../reader-a.md runs/.../reader-b.md --out runs/2026-10-10-vocab
#   -> agreement.json, agreement.md; exit 1 if any entry is not ratified
ratify.sh record --stream my-org/my-project --agreement runs/.../agreement.json --owner-approved EXCL-07
#   -> <stream>/ratifications/ledger.jsonl, one row per entry
ratify.sh check --entries entries.json --stream my-org/my-project
#   exit 1 if any entry is unratified, rejected, held, or its pattern or class changed since its row
ratify.sh status                       # counts per stream
```

- Sampling is seeded per entry. The same seed and the same files give the same sample.
- Sampling is round-robin across documents, so one long document cannot fill an entry's sample.
- The pattern hash covers `pattern` and `patternKind`. A change to either, or to `class`, makes `check` report the entry as changed.
- The ledger is append-only. The latest row per entry id counts.
- `--stream` may be left out when the current directory is registered in `_meta/REGISTRY.md`.

Tests: `python3 -m unittest runtime/tests/test_ratify.py`.
