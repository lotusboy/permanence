#!/usr/bin/env python3
"""Vocabulary ratification: prove each entry of a closed vocabulary against the project's own corpus.

A closed vocabulary maps a pattern (regex, phrase or keyword rule) to a class. This tool samples real
matches per entry, writes a brief for two isolated blind readers, compares their per-entry labels,
records verdicts in an append-only ledger, and checks a vocabulary against that ledger as a gate.
Pure computation, standard library only, no AI. Usage: see ratify.sh.
"""

import argparse
import hashlib
import json
import os
import random
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PERMA = Path(os.environ.get("PERMA_DIR") or Path.home() / "permanence")
HERE = Path(__file__).resolve().parent
TEMPLATE = HERE.parent / "templates/ratify-vocabulary-brief.md"
KINDS = ("regex", "phrase", "keyword")
LABELS = ("RIGHT", "WRONG", "MIXED")
ELLIPSIS = re.compile(r"\s*(?:…|\.\.\.)\s*")


def fail(msg, code=2):
    print(f"ratify: {msg}", file=sys.stderr)
    sys.exit(code)


def load_json(path, what):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError) as e:
        fail(f"cannot read {what} {path}: {e}")


def pattern_hash(entry):
    raw = json.dumps({"pattern": entry["pattern"], "patternKind": entry["patternKind"]}, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def load_entries(path):
    entries = load_json(path, "entries")
    if not isinstance(entries, list):
        fail(f"{path}: entries must be a JSON array")
    seen = set()
    for n, e in enumerate(entries):
        for k in ("id", "pattern", "patternKind", "class"):
            if not isinstance(e.get(k), str) or not e[k]:
                fail(f"{path}: entry {n} has no string '{k}'")
        if e["patternKind"] not in KINDS:
            fail(f"{path}: entry {e['id']} patternKind '{e['patternKind']}' is not one of {', '.join(KINDS)}")
        if e["id"] in seen:
            fail(f"{path}: entry id {e['id']} appears twice")
        seen.add(e["id"])
    return entries


def edge(s, end):
    ch = s[-1:] if end else s[:1]
    return (r"(?!\w)" if end else r"(?<!\w)") if re.match(r"\w", ch) else ""


def compile_entry(e):
    """One compiled regex per entry. A keyword rule compiles to one regex per word."""
    p, kind = e["pattern"], e["patternKind"]
    try:
        if kind == "regex":
            return [re.compile(p)]
        if kind == "phrase":
            parts = [x for x in ELLIPSIS.split(p.strip()) if x.strip()]
            if not parts:
                fail(f"entry {e['id']}: phrase has no words")
            body = ".*?".join(r"\s+".join(map(re.escape, x.split())) for x in parts)
            return [re.compile(edge(parts[0], False) + body + edge(parts[-1], True), re.I | re.S)]
        return [re.compile(r"(?<!\w)" + re.escape(w) + r"(?!\w)", re.I) for w in p.split()]
    except re.error as err:
        fail(f"entry {e['id']}: pattern does not compile: {err}")


def find(e, rx, text):
    """The matched text, or None. A keyword rule matches when every word is present, in any order."""
    if e["patternKind"] == "keyword":
        hits = [r.search(text) for r in rx]
        return " … ".join(h.group(0) for h in hits) if hits and all(hits) else None
    m = rx[0].search(text)
    return m.group(0) if m else None


def stratified(matches, k, rng):
    """Round-robin across documents in a seeded order, so one long document cannot fill the sample."""
    by_doc = {}
    for m in matches:
        by_doc.setdefault(m["docId"], []).append(m)
    docs = sorted(by_doc)
    rng.shuffle(docs)
    for d in docs:
        rng.shuffle(by_doc[d])
    out = []
    while len(out) < k and any(by_doc[d] for d in docs):
        for d in docs:
            if by_doc[d] and len(out) < k:
                out.append(by_doc[d].pop(0))
    return out


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def cmd_sample(a):
    entries = load_entries(a.entries)
    corpus = load_json(a.corpus, "corpus")
    if not isinstance(corpus, list):
        fail(f"{a.corpus}: corpus must be a JSON array")
    for n, c in enumerate(corpus):
        for k in ("docId", "text", "pointer"):
            if not isinstance(c.get(k), str):
                fail(f"{a.corpus}: record {n} has no string '{k}'")
    classes = load_json(a.classes, "classes") if a.classes else {}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    result, sampled, unmatched = [], 0, []
    for e in entries:
        rx = compile_entry(e)
        matches = [{"docId": c["docId"], "pointer": c["pointer"], "text": c["text"], "match": hit}
                   for c in corpus if (hit := find(e, rx, c["text"])) is not None]
        rng = random.Random(f"{a.seed}:{e['id']}")
        picks = stratified(matches, a.per_entry, rng)
        for n, s in enumerate(picks, 1):
            s["n"] = n
        result.append({"id": e["id"], "pattern": e["pattern"], "patternKind": e["patternKind"],
                       "class": e["class"], "patternHash": pattern_hash(e), "totalMatches": len(matches),
                       "docsMatched": len({m["docId"] for m in matches}), "samples": picks})
        sampled += len(picks)
        if not matches:
            unmatched.append(e["id"])
    doc = {"createdAt": now(), "seed": a.seed, "perEntry": a.per_entry,
           "entriesFile": str(Path(a.entries).resolve()), "entriesSha256": sha(a.entries),
           "corpusFile": str(Path(a.corpus).resolve()), "corpusSha256": sha(a.corpus),
           "corpusRecords": len(corpus), "classes": classes, "entries": result}
    (out / "sample.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    (out / "readers-sample.md").write_text(readers_sample(result, classes))
    template = Path(a.template) if a.template else TEMPLATE
    if not template.is_file():
        fail(f"brief template not found: {template} (pass --template)")
    judged = [r["id"] for r in result if r["samples"]]
    for letter in "ABCDEFGH"[:a.readers]:
        brief = (template.read_text().replace("{{READER}}", letter)
                 .replace("{{SAMPLE}}", str((out / "readers-sample.md").resolve()))
                 .replace("{{SOURCE}}", a.source or "the files named in each sample's pointer")
                 .replace("{{COUNT}}", str(len(judged)))
                 .replace("{{IDS}}", ", ".join(judged)))
        (out / f"brief-{letter}.md").write_text(brief)
    print(f"sampled {sampled} matches for {len(judged)} of {len(entries)} entries "
          f"(seed {a.seed}, up to {a.per_entry} each) -> {out}/sample.json")
    print("readers' briefs: " + ", ".join(f"{out}/brief-{x}.md" for x in "ABCDEFGH"[:a.readers]))
    if unmatched:
        print(f"{len(unmatched)} entries matched nothing in the corpus and cannot be judged "
              f"(they will be recorded as held): {', '.join(unmatched)}")
    return 0


def readers_sample(result, classes):
    """What the readers see: pattern, class and matches. Never the entry's kind, source or notes."""
    lines = ["# Entries to judge", ""]
    if classes:
        lines += ["## What each class means", ""] + [f"- **{k}**: {v}" for k, v in classes.items()] + [""]
    for r in result:
        if not r["samples"]:
            continue
        lines += [f"## {r['id']}", "", f"- Pattern ({r['patternKind']}): `{r['pattern']}`",
                  f"- Class it assigns: **{r['class']}**",
                  f"- Matches in the corpus: {r['totalMatches']} across {r['docsMatched']} documents; "
                  f"{len(r['samples'])} shown", ""]
        for s in r["samples"]:
            # The whole record, never a snippet: a cut-off passage is how a reader misjudges a match.
            lines += [f"### {r['id']} sample {s['n']} — {s['docId']}, {s['pointer']}", "",
                      f"Matched: \"{s['match']}\"", "", "> " + s["text"].replace("\n", "\n> "), ""]
    return "\n".join(lines) + "\n"


def last_json(path):
    blocks = re.findall(r"```json\s*\n(.*?)```", Path(path).read_text(), re.S)
    if not blocks:
        fail(f"{path}: no ```json block")
    try:
        data = json.loads(blocks[-1])
    except json.JSONDecodeError as e:
        fail(f"{path}: last ```json block does not parse: {e}")
    items = {}
    for i in data.get("items", []):
        label = str(i.get("label", "")).strip().upper()
        if label not in LABELS:
            fail(f"{path}: item {i.get('id')} label '{i.get('label')}' is not one of {', '.join(LABELS)}")
        items[str(i["id"])] = dict(i, label=label)
    return data.get("reader") or Path(path).stem, items


def verdict(labels):
    """Ratified only when every reader says RIGHT. Every reader saying not-RIGHT is rejected.
    A split, a missing answer, or no readers at all is held."""
    if not labels or None in labels:
        return "held"
    if all(x == "RIGHT" for x in labels):
        return "ratified"
    if all(x != "RIGHT" for x in labels):
        return "rejected"
    return "held"


def cmd_compare(a):
    if len(a.reports) < 2:
        fail("compare needs at least two reader reports")
    out = Path(a.out)
    sample_path = Path(a.sample) if a.sample else out / "sample.json"
    sample = load_json(sample_path, "sample")
    readers = [last_json(p) for p in a.reports]
    names = [n for n, _ in readers]
    if len(set(names)) != len(names):
        fail(f"two reports name the same reader: {names}")
    rows = []
    for e in sample["entries"]:
        answers = [items.get(e["id"]) for _, items in readers]
        labels = [x["label"] if x else None for x in answers] if e["samples"] else []
        v = verdict(labels)
        reason = ("no matches in the corpus" if not e["samples"] else
                  "a reader gave no answer" if None in labels else
                  "readers disagree" if v == "held" else "")
        rows.append({"id": e["id"], "pattern": e["pattern"], "patternKind": e["patternKind"],
                     "class": e["class"], "patternHash": e["patternHash"], "verdict": v, "reason": reason,
                     "readers": {n: x for n, x in zip(names, answers)}})
    known = {e["id"] for e in sample["entries"]}
    stray = sorted({i for _, items in readers for i in items} - known)
    doc = {"createdAt": now(), "sample": str(sample_path.resolve()),
           "reports": [str(Path(p).resolve()) for p in a.reports], "readers": names, "entries": rows,
           "unknownIds": stray}
    out.mkdir(parents=True, exist_ok=True)
    (out / "agreement.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    (out / "agreement.md").write_text(agreement_md(doc))
    counts = {v: sum(r["verdict"] == v for r in rows) for v in ("ratified", "rejected", "held")}
    print(f"{len(rows)} entries: {counts['ratified']} ratified, {counts['rejected']} rejected, "
          f"{counts['held']} held -> {out}/agreement.json, {out}/agreement.md")
    if stray:
        print(f"ignored ids not in the sample: {', '.join(stray)}")
    return 0 if counts["ratified"] == len(rows) else 1


def agreement_md(doc):
    names = doc["readers"]
    lines = ["# Vocabulary agreement table", "", f"Sample: `{doc['sample']}`", "Reports: " +
             ", ".join(f"`{p}`" for p in doc["reports"]), "",
             "Ratified only when every reader says RIGHT. Rejected when every reader says WRONG or MIXED. "
             "Held when the readers split, a reader gave no answer, or the entry matched nothing.", "",
             "| Id | Class | " + " | ".join(names) + " | Verdict |", "|---|---|" + "---|" * len(names) + "---|"]
    for r in doc["entries"]:
        cells = [(r["readers"][n] or {}).get("label", "—") for n in names]
        lines.append(f"| {r['id']} | {r['class']} | " + " | ".join(cells) + f" | {r['verdict']} |")
    lines += [""]
    for v in ("rejected", "held"):
        rs = [r for r in doc["entries"] if r["verdict"] == v]
        if not rs:
            continue
        lines += [f"## {v.capitalize()} — evidence from every reader", ""]
        for r in rs:
            lines.append(f"- **{r['id']}** `{r['pattern']}` -> {r['class']}" + (f" ({r['reason']})" if r["reason"] else ""))
            for n in names:
                x = r["readers"][n]
                if x:
                    lines.append(f"  - {n}: {x['label']} — \"{x.get('quote', '')}\" ({x.get('where', '')}). "
                                 f"{x.get('recommendation', '')}")
        lines.append("")
    return "\n".join(lines)


def resolve_stream(explicit):
    if explicit:
        return explicit
    p = subprocess.run([str(PERMA / "runtime/resolve-stream.sh"), os.getcwd()], capture_output=True, text=True,
                       env=dict(os.environ, PERMA_DIR=str(PERMA)))
    s = p.stdout.strip()
    if not s:
        fail(f"no stream is registered for {os.getcwd()} in _meta/REGISTRY.md; pass --stream")
    return s


def ledger_path(stream):
    return PERMA / stream / "ratifications" / "ledger.jsonl"


def latest(stream):
    path = ledger_path(stream)
    rows = {}
    if path.is_file():
        for line in path.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                rows[r["id"]] = r
    return rows


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def cmd_record(a):
    stream = resolve_stream(a.stream)
    agreement = load_json(a.agreement, "agreement")
    owner = {x.strip() for x in (a.owner_approved or "").split(",") if x.strip()}
    by_id = {r["id"]: r for r in agreement["entries"]}
    for i in sorted(owner):
        if i not in by_id:
            fail(f"--owner-approved {i}: not in {a.agreement}")
        if by_id[i]["verdict"] != "held":
            fail(f"--owner-approved {i}: its verdict is {by_id[i]['verdict']}; the owner approves held entries "
                 "only. A rejected entry goes back for a fix and a new round.")
    path = ledger_path(stream)
    path.parent.mkdir(parents=True, exist_ok=True)
    evidence = str(Path(a.agreement).resolve())
    counts = {}
    with path.open("a") as f:
        for r in agreement["entries"]:
            approved = r["id"] in owner
            v = "ratified" if approved else r["verdict"]
            row = {"ts": now(), "date": now()[:10], "id": r["id"], "patternHash": r["patternHash"],
                   "patternKind": r["patternKind"], "pattern": r["pattern"], "class": r["class"], "verdict": v,
                   "ratifiedBy": "owner" if approved else ("readers" if v == "ratified" else None),
                   "readers": {n: (x or {}).get("label") for n, x in r["readers"].items()},
                   "reason": r.get("reason") or None, "evidence": evidence, "reports": agreement["reports"]}
            if approved:
                row["note"] = a.note or "owner approved a held entry"
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            counts[v] = counts.get(v, 0) + 1
    print(f"recorded {len(agreement['entries'])} rows in {path}: " +
          ", ".join(f"{k} {v}" for k, v in sorted(counts.items())) +
          (f" ({len(owner)} ratified by the owner)" if owner else ""))
    return 0


def cmd_check(a):
    stream = resolve_stream(a.stream)
    entries = load_entries(a.entries)
    led = latest(stream)
    problems = []
    for e in entries:
        r = led.get(e["id"])
        if r is None:
            state = "unratified"
        elif r["patternHash"] != pattern_hash(e) or r["class"] != e["class"]:
            what = [w for w, bad in (("pattern", r["patternHash"] != pattern_hash(e)),
                                     ("class", r["class"] != e["class"])) if bad]
            state = f"changed ({' and '.join(what)} since {r['verdict']} on {r['date']})"
        elif r["verdict"] != "ratified":
            state = r["verdict"]
        else:
            continue
        problems.append({"id": e["id"], "state": state, "pattern": e["pattern"], "class": e["class"]})
    if a.json:
        print(json.dumps({"stream": stream, "entries": len(entries), "problems": problems}, indent=2))
    else:
        for p in problems:
            print(f"{p['id']}: {p['state']} — `{p['pattern']}` -> {p['class']}")
        print(f"{len(entries) - len(problems)} of {len(entries)} entries ratified and unchanged in {stream}.")
    return 1 if problems else 0


def cmd_status(a):
    streams = [a.stream] if a.stream else sorted(
        str(p.parent.parent.relative_to(PERMA)) for p in PERMA.glob("**/ratifications/ledger.jsonl"))
    if not streams:
        print("no ratification ledgers found")
    for s in streams:
        rows = latest(s).values()
        counts = {v: sum(r["verdict"] == v for r in rows) for v in ("ratified", "rejected", "held")}
        owner = sum(r.get("ratifiedBy") == "owner" for r in rows)
        print(f"{s}: {len(rows)} entries — ratified {counts['ratified']} (by owner {owner}), "
              f"rejected {counts['rejected']}, held {counts['held']}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="ratify.sh", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sample")
    s.add_argument("--entries", required=True)
    s.add_argument("--corpus", required=True)
    s.add_argument("--per-entry", type=int, default=8)
    s.add_argument("--seed", type=int, required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--classes", help="JSON object: class -> one-line meaning, shown to the readers")
    s.add_argument("--source", help="where the raw source lives, for the readers' brief")
    s.add_argument("--readers", type=int, default=2)
    s.add_argument("--template")
    c = sub.add_parser("compare")
    c.add_argument("reports", nargs="+")
    c.add_argument("--out", required=True)
    c.add_argument("--sample", help="default <out>/sample.json")
    r = sub.add_parser("record")
    r.add_argument("--stream")
    r.add_argument("--agreement", required=True)
    r.add_argument("--owner-approved", help="comma-separated ids of HELD entries the owner approved")
    r.add_argument("--note")
    k = sub.add_parser("check")
    k.add_argument("--entries", required=True)
    k.add_argument("--stream")
    k.add_argument("--json", action="store_true")
    t = sub.add_parser("status")
    t.add_argument("--stream")
    a = ap.parse_args(argv)
    if a.cmd == "sample" and (a.per_entry < 1 or not 2 <= a.readers <= 8):
        fail("--per-entry must be at least 1 and --readers between 2 and 8")
    return {"sample": cmd_sample, "compare": cmd_compare, "record": cmd_record,
            "check": cmd_check, "status": cmd_status}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
