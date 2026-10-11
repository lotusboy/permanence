"""Tests for runtime/ratify.sh. Standard library only: python3 -m unittest runtime/tests/test_ratify.py"""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

RUNTIME = Path(__file__).resolve().parent.parent

ENTRIES = [
    {"id": "X1", "pattern": "We will not cover …", "patternKind": "phrase", "class": "exclude"},
    {"id": "X2", "pattern": r"(?i)\bexcess of £\d+", "patternKind": "regex", "class": "deductible"},
    {"id": "X3", "pattern": "flood damage", "patternKind": "keyword", "class": "peril"},
    {"id": "X4", "pattern": "never appears anywhere", "patternKind": "phrase", "class": "exclude"},
]


def corpus(n_docs=5, per_doc=6):
    rows = []
    for d in range(n_docs):
        for k in range(per_doc):
            rows.append({"docId": f"doc{d}", "pointer": f"doc{d}.pdf p.{k + 1}",
                         "text": f"Clause {k}. We will NOT  cover loss caused by wear (doc {d}). "
                                 f"An excess of £{100 + k} applies. Damage caused by flood is insured."})
    rows.append({"docId": "docZ", "pointer": "z.pdf p.1", "text": "We will not coverage."})
    return rows


def report(reader, labels):
    items = [{"id": i, "label": lab, "quote": f"q-{i}", "where": "s1", "recommendation": "r"}
             for i, lab in labels.items()]
    return f"# Reader {reader}\n\nprose\n\n```json\n" + json.dumps({"reader": reader, "items": items}) + "\n```\n"


class Ratify(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.t = Path(self.tmp.name).resolve()
        self.perma = self.t / "perma"
        (self.perma / "_meta").mkdir(parents=True)
        (self.perma / "runtime").mkdir()
        (self.perma / "runtime/resolve-stream.sh").symlink_to(RUNTIME / "resolve-stream.sh")
        (self.perma / "_meta/REGISTRY.md").write_text("| path | stream | what |\n|---|---|---|\n")
        self.env = dict(os.environ, PERMA_DIR=str(self.perma))
        self.entries = self.t / "entries.json"
        self.corpus = self.t / "corpus.json"
        self.entries.write_text(json.dumps(ENTRIES))
        self.corpus.write_text(json.dumps(corpus()))
        self.run_dir = self.t / "run"

    def tearDown(self):
        self.tmp.cleanup()

    def ratify(self, *args, code=0):
        p = subprocess.run([str(RUNTIME / "ratify.sh"), *map(str, args)], capture_output=True, text=True,
                           env=self.env, cwd=self.t)
        self.assertEqual(p.returncode, code, p.stdout + p.stderr)
        return p

    def sample(self, out=None, seed=7, per=4):
        out = out or self.run_dir
        self.ratify("sample", "--entries", self.entries, "--corpus", self.corpus, "--per-entry", per,
                    "--seed", seed, "--out", out)
        return json.loads((out / "sample.json").read_text())

    def by_id(self, s):
        return {e["id"]: e for e in s["entries"]}

    # --- matching per patternKind -------------------------------------------------------------
    def test_phrase_is_case_and_space_insensitive_with_ellipsis_and_word_edges(self):
        e = self.by_id(self.sample())["X1"]
        self.assertEqual(e["totalMatches"], 30)  # "coverage" in docZ does not match "cover"
        self.assertNotIn("docZ", {s["docId"] for s in e["samples"]})

    def test_regex_and_keyword(self):
        s = self.by_id(self.sample())
        self.assertEqual(s["X2"]["totalMatches"], 30)
        self.assertRegex(s["X2"]["samples"][0]["match"], r"excess of £10\d")
        self.assertEqual(s["X3"]["totalMatches"], 30)  # both words present, any order
        self.assertEqual(s["X4"]["totalMatches"], 0)

    def test_keyword_needs_every_word(self):
        self.entries.write_text(json.dumps([{"id": "K", "pattern": "flood volcano", "patternKind": "keyword",
                                             "class": "peril"}]))
        self.assertEqual(self.sample()["entries"][0]["totalMatches"], 0)

    def test_bad_inputs_exit_2(self):
        self.entries.write_text(json.dumps([{"id": "B", "pattern": "(", "patternKind": "regex", "class": "c"}]))
        self.ratify("sample", "--entries", self.entries, "--corpus", self.corpus, "--seed", 1, "--out",
                    self.run_dir, code=2)
        self.entries.write_text(json.dumps([{"id": "B", "pattern": "x", "patternKind": "glob", "class": "c"}]))
        self.ratify("sample", "--entries", self.entries, "--corpus", self.corpus, "--seed", 1, "--out",
                    self.run_dir, code=2)

    # --- sampling ------------------------------------------------------------------------------
    def test_sampling_is_deterministic_and_stratified(self):
        a = self.sample(self.t / "r1", seed=7)
        b = self.sample(self.t / "r2", seed=7)
        c = self.sample(self.t / "r3", seed=8)
        picks = lambda s: [(x["docId"], x["pointer"]) for e in s["entries"] for x in e["samples"]]
        self.assertEqual(picks(a), picks(b))
        self.assertNotEqual(picks(a), picks(c))
        x1 = self.by_id(a)["X1"]["samples"]
        self.assertEqual(len(x1), 4)
        self.assertEqual(len({s["docId"] for s in x1}), 4)  # 4 picks from 5 docs: never two from one doc

    def test_sample_writes_full_text_and_briefs_without_engineering_notes(self):
        self.entries.write_text(json.dumps([dict(ENTRIES[0], kind="exclusion-lead", source="added in A123")]))
        self.sample()
        md = (self.run_dir / "readers-sample.md").read_text()
        self.assertIn("Damage caused by flood is insured.", md)  # whole record, not a snippet
        self.assertNotIn("A123", md)
        self.assertNotIn("exclusion-lead", md)
        brief = (self.run_dir / "brief-B.md").read_text()
        self.assertIn("reader **B**", brief)
        self.assertNotIn("{{", brief)

    # --- compare -------------------------------------------------------------------------------
    def compare(self, a, b):
        (self.run_dir / "reader-a.md").write_text(report("A", a))
        (self.run_dir / "reader-b.md").write_text(report("B", b))
        return self.ratify("compare", self.run_dir / "reader-a.md", self.run_dir / "reader-b.md",
                           "--out", self.run_dir, code=1)

    def test_compare_verdicts(self):
        self.sample()
        self.compare({"X1": "RIGHT", "X2": "right", "X3": "WRONG"}, {"X1": "RIGHT", "X2": "MIXED", "X3": "MIXED"})
        ag = {r["id"]: r for r in json.loads((self.run_dir / "agreement.json").read_text())["entries"]}
        self.assertEqual(ag["X1"]["verdict"], "ratified")
        self.assertEqual(ag["X2"]["verdict"], "held")
        self.assertEqual(ag["X3"]["verdict"], "rejected")
        self.assertEqual(ag["X4"]["verdict"], "held")
        self.assertEqual(ag["X4"]["reason"], "no matches in the corpus")
        md = (self.run_dir / "agreement.md").read_text()
        self.assertIn('q-X3', md)

    def test_compare_missing_answer_is_held_and_all_ratified_exits_0(self):
        self.entries.write_text(json.dumps(ENTRIES[:2]))
        self.sample()
        self.compare({"X1": "RIGHT", "X2": "RIGHT"}, {"X1": "RIGHT"})
        ag = {r["id"]: r for r in json.loads((self.run_dir / "agreement.json").read_text())["entries"]}
        self.assertEqual(ag["X2"]["verdict"], "held")
        (self.run_dir / "reader-b.md").write_text(report("B", {"X1": "RIGHT", "X2": "RIGHT"}))
        self.ratify("compare", self.run_dir / "reader-a.md", self.run_dir / "reader-b.md", "--out", self.run_dir)

    def test_compare_rejects_bad_label_and_missing_json(self):
        self.sample()
        (self.run_dir / "reader-a.md").write_text(report("A", {"X1": "MAYBE"}))
        (self.run_dir / "reader-b.md").write_text("no json here")
        self.ratify("compare", self.run_dir / "reader-a.md", self.run_dir / "reader-b.md", "--out",
                    self.run_dir, code=2)

    # --- record + check ------------------------------------------------------------------------
    def recorded(self, *owner):
        self.sample()
        self.compare({"X1": "RIGHT", "X2": "RIGHT", "X3": "WRONG"}, {"X1": "RIGHT", "X2": "MIXED", "X3": "WRONG"})
        args = ["record", "--stream", "a/proj", "--agreement", self.run_dir / "agreement.json"]
        if owner:
            args += ["--owner-approved", ",".join(owner)]
        self.ratify(*args)
        return [json.loads(x) for x in (self.perma / "a/proj/ratifications/ledger.jsonl").read_text().splitlines()]

    def test_record_rows(self):
        rows = {r["id"]: r for r in self.recorded()}
        self.assertEqual(rows["X1"]["verdict"], "ratified")
        self.assertEqual(rows["X1"]["ratifiedBy"], "readers")
        self.assertEqual(rows["X1"]["readers"], {"A": "RIGHT", "B": "RIGHT"})
        self.assertEqual(rows["X2"]["verdict"], "held")
        self.assertEqual(rows["X3"]["verdict"], "rejected")
        self.assertTrue(rows["X1"]["evidence"].endswith("agreement.json"))
        self.assertEqual(len(rows["X1"]["patternHash"]), 16)

    def test_owner_may_approve_held_only(self):
        rows = {r["id"]: r for r in self.recorded("X2")}
        self.assertEqual(rows["X2"]["verdict"], "ratified")
        self.assertEqual(rows["X2"]["ratifiedBy"], "owner")
        self.ratify("record", "--stream", "a/proj", "--agreement", self.run_dir / "agreement.json",
                    "--owner-approved", "X3", code=2)

    def test_check_exit_codes_and_hash_invalidation(self):
        self.recorded("X2")
        p = self.ratify("check", "--entries", self.entries, "--stream", "a/proj", code=1)
        self.assertIn("X3: rejected", p.stdout)
        self.assertIn("X4: held", p.stdout)
        good = self.t / "good.json"
        good.write_text(json.dumps(ENTRIES[:2]))
        self.ratify("check", "--entries", good, "--stream", "a/proj")
        good.write_text(json.dumps([dict(ENTRIES[0], pattern="We shall not cover …"), ENTRIES[1]]))
        p = self.ratify("check", "--entries", good, "--stream", "a/proj", code=1)
        self.assertIn("X1: changed (pattern since ratified", p.stdout)
        good.write_text(json.dumps([dict(ENTRIES[0], **{"class": "condition"}), ENTRIES[1]]))
        p = self.ratify("check", "--entries", good, "--stream", "a/proj", code=1)
        self.assertIn("X1: changed (class since ratified", p.stdout)
        good.write_text(json.dumps([dict(ENTRIES[0], kind="new note"), ENTRIES[1]]))
        self.ratify("check", "--entries", good, "--stream", "a/proj")  # kind/source are not judged
        good.write_text(json.dumps(ENTRIES[:2] + [{"id": "NEW", "pattern": "x", "patternKind": "phrase",
                                                   "class": "c"}]))
        p = self.ratify("check", "--entries", good, "--stream", "a/proj", "--json", code=1)
        self.assertEqual(json.loads(p.stdout)["problems"][0]["state"], "unratified")

    def test_latest_row_wins_and_status(self):
        self.recorded()
        self.ratify("record", "--stream", "a/proj", "--agreement", self.run_dir / "agreement.json",
                    "--owner-approved", "X2")
        p = self.ratify("status")
        self.assertIn("a/proj: 4 entries — ratified 2 (by owner 1), rejected 1, held 1", p.stdout)

    def test_stream_resolves_from_registry(self):
        (self.perma / "_meta/REGISTRY.md").write_text(f"| path | stream | what |\n|---|---|---|\n| {self.t} | a/proj | t |\n")
        self.recorded()
        p = self.ratify("check", "--entries", self.entries, code=1)
        self.assertIn("in a/proj", p.stdout)


if __name__ == "__main__":
    unittest.main()
