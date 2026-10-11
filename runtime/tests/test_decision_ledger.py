"""Tests for runtime/decision.sh. Standard library only:
python3 -m unittest discover -s runtime/tests"""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

RUNTIME = Path(__file__).resolve().parent.parent


class Ledger(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name).resolve()
        self.perma = t / "perma"
        (self.perma / "_meta").mkdir(parents=True)
        (self.perma / "runtime").mkdir()
        for s in ("resolve-stream.sh", "decision.sh", "decision.py", "decision-config.json"):
            (self.perma / "runtime" / s).symlink_to(RUNTIME / s)
        self.work = t / "work"
        self.work.mkdir()
        (self.perma / "a/proj").mkdir(parents=True)
        (self.perma / "_meta/REGISTRY.md").write_text(f"| path | stream | what |\n|---|---|---|\n| {self.work} | a/proj | t |\n")
        self.env = dict(os.environ, PERMA_DIR=str(self.perma), DECISION_NOW="2026-10-10T12:00:00+01:00")
        for k in ("DECISION_TS", "DECISION_BACKFILL"):
            self.env.pop(k, None)
        self.ledger = self.perma / "a/proj/decisions/ledger.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def run_(self, *args, env=None, ok=True):
        p = subprocess.run([str(self.perma / "runtime/decision.sh"), *args], cwd=self.work,
                           capture_output=True, text=True, env=dict(self.env, **(env or {})))
        if ok:
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        return p

    def ask(self, cat="spend", conf=0.9, ts="2026-10-10T10:00:00+01:00", **kw):
        args = ["ask", "--category", cat, "--question", kw.get("q", "Run it?"), "--option", "yes",
                "--option", "no", "--recommendation", "yes", "--confidence", str(conf),
                "--evidence-kind", "measured", "--evidence", "WIP.md"]
        args += kw.get("extra", [])
        return self.run_(*args, env={"DECISION_TS": ts}).stdout.strip()

    def rows(self):
        return [json.loads(l) for l in self.ledger.read_text().splitlines()]

    def score(self, *extra):
        return json.loads(self.run_("score", "--json", *extra).stdout)

    # --- record ---
    def test_ask_answer_outcome_append_to_the_streams_ledger(self):
        did = self.ask()
        self.run_("answer", did, "--choice", "yes")
        self.run_("outcome", did, "--verdict", "held", "--by", "the run finished")
        kinds = [(r["kind"], r["id"]) for r in self.rows()]
        self.assertEqual(kinds, [("ask", did), ("answer", did), ("outcome", did)])
        self.assertTrue(self.rows()[1]["agreed"])
        self.assertEqual(self.rows()[0]["stream"], "a/proj")

    def test_explicit_stream_works_outside_a_registered_directory(self):
        (self.perma / "b").mkdir()
        p = subprocess.run([str(self.perma / "runtime/decision.sh"), "ask", "--stream", "b", "--category", "scope",
                            "--question", "q", "--option", "x", "--option", "y", "--recommendation", "x",
                            "--confidence", "0.5", "--evidence-kind", "inference", "--evidence", "e"],
                           cwd=self.perma, capture_output=True, text=True, env=self.env)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertTrue((self.perma / "b/decisions/ledger.jsonl").exists())

    def test_validation_refuses_bad_input_and_writes_nothing(self):
        base = ["ask", "--category", "spend", "--question", "q", "--option", "a", "--option", "b",
                "--recommendation", "a", "--evidence-kind", "measured", "--evidence", "e"]
        for extra in (["--confidence", "1.5"], [], ["--confidence", "0.5", "--blind", "--autonomous"]):
            self.assertNotEqual(self.run_(*base, *extra, ok=False).returncode, 0, extra)
        bad_kind = [x if x != "measured" else "vibes" for x in base] + ["--confidence", "0.5"]
        self.assertNotEqual(self.run_(*bad_kind, ok=False).returncode, 0)
        self.assertFalse(self.ledger.exists())

    def test_disagreement_must_be_stated_and_past_lines_are_never_rewritten(self):
        did = self.ask()
        self.assertNotEqual(self.run_("answer", did, "--choice", "not now", ok=False).returncode, 0)
        before = self.ledger.read_text()
        self.run_("answer", did, "--choice", "not now", "--agreed", "no")
        self.assertTrue(self.ledger.read_text().startswith(before))
        self.assertFalse(self.rows()[-1]["agreed"])

    def test_blind_answer_may_leave_agreed_open(self):
        did = self.ask(extra=["--blind"])
        self.run_("answer", did, "--choice", "something else")
        self.assertIsNone(self.rows()[-1]["agreed"])
        self.assertEqual(self.score()["overall"]["scored"], 0)

    def test_autonomous_decisions_take_outcomes_not_answers(self):
        did = self.ask(extra=["--autonomous"])
        self.assertNotEqual(self.run_("answer", did, "--choice", "yes", ok=False).returncode, 0)
        self.run_("outcome", did, "--verdict", "reversed", "--by", "owner review")
        s = self.score()["overall"]
        self.assertEqual((s["autonomous"], s["asked"], s["reversed"]), (1, 0, 1))

    def test_backfill_relaxes_unknowable_fields_and_marks_the_line(self):
        env = {"DECISION_BACKFILL": "1", "DECISION_TS": "2026-10-09T08:00:00+01:00"}
        did = self.run_("ask", "--category", "spend", "--question", "q", env=env).stdout.strip()
        self.run_("answer", did, "--choice", "go", "--agreed", "yes", env=env)
        a, b = self.rows()
        self.assertTrue(a["backfilled"] and b["backfilled"])
        self.assertIsNone(a["confidence"])
        self.assertEqual(a["ts"], "2026-10-09T08:00:00+01:00")

    # --- score ---
    def test_agreement_brier_and_reversal_counting_against_agreement(self):
        a = self.ask(conf=0.9)
        b = self.ask(conf=0.6)
        c = self.ask(conf=0.8)
        self.run_("answer", a, "--choice", "yes")
        self.run_("answer", b, "--choice", "no", "--agreed", "no")
        self.run_("answer", c, "--choice", "yes")
        self.run_("outcome", c, "--verdict", "reversed", "--by", "re-measure")
        s = self.score()["categories"]["spend"]
        self.assertAlmostEqual(s["agreement"], 1 / 3, places=3)
        # (0.9-1)^2 + (0.6-0)^2 + (0.8-0)^2 = 0.01 + 0.36 + 0.64 = 1.01; / 3
        self.assertAlmostEqual(s["brier"], 0.337, places=3)
        self.assertEqual(s["reversed"], 1)
        band = {b["band"]: b for b in s["reliability"]}
        self.assertEqual(band["0.9-1.0"]["n"], 1)
        self.assertEqual(band["0.9-1.0"]["agreement"], 1.0)

    def test_recency_weighting_favours_recent_answers(self):
        old = self.ask(ts="2026-09-12T12:00:00+01:00")  # 28 days = two half-lives: weight 0.25
        new = self.ask(ts="2026-10-10T12:00:00+01:00")  # weight 1
        self.run_("answer", old, "--choice", "no", "--agreed", "no")
        self.run_("answer", new, "--choice", "yes")
        s = self.score()["overall"]
        self.assertEqual(s["agreement"], 0.5)
        self.assertAlmostEqual(s["agreementRecency"], 0.8, places=3)

    def make_autonomous(self, cat="placement", n=20):
        for _ in range(n):
            self.run_("answer", self.ask(cat=cat, conf=0.95), "--choice", "yes")

    def test_autonomy_needs_every_threshold(self):
        self.make_autonomous(n=19)
        s = self.score()["categories"]["placement"]
        self.assertEqual(s["autonomy"], "ask")
        self.assertIn("answered 19 < 20", s["autonomyReasons"][0])
        self.make_autonomous(n=1)
        self.assertEqual(self.score()["categories"]["placement"]["autonomy"], "autonomous")
        last = self.rows()[-1]["id"]
        self.run_("outcome", last, "--verdict", "reversed", "--by", "x")
        self.assertEqual(self.score()["categories"]["placement"]["autonomy"], "ask")

    def test_thresholds_are_configurable_per_stream(self):
        (self.perma / "a/proj/decisions").mkdir()
        (self.perma / "a/proj/decisions/config.json").write_text(json.dumps({"autonomy": {"minAnswered": 2}}))
        self.make_autonomous(n=2)
        s = self.score()["categories"]["placement"]
        self.assertEqual(s["autonomy"], "autonomous", s["autonomyReasons"])

    # --- sample ---
    def test_should_ask_always_asks_until_autonomous_then_samples_by_seed(self):
        self.assertEqual(self.run_("should-ask", "placement").stdout.strip(), "ask")
        self.make_autonomous()
        draws = {self.run_("should-ask", "placement", "--seed", str(i)).stdout.strip() for i in range(12)}
        self.assertEqual(draws, {"ask-blind", "decide-and-log"})
        again = [self.run_("should-ask", "placement", "--seed", "3").stdout.strip() for _ in range(3)]
        self.assertEqual(len(set(again)), 1)
        # random.Random(0).random() = 0.844 >= 0.2; random.Random(4).random() = 0.236; Random(2) = 0.956
        self.assertEqual(self.run_("should-ask", "placement", "--seed", "0").stdout.strip(), "decide-and-log")

    # --- review ---
    def test_review_lists_every_decision_newest_first_with_scores_on_top(self):
        a = self.ask(q="First | question", ts="2026-10-09T09:00:00+01:00")
        b = self.ask(q="Second question", ts="2026-10-10T09:00:00+01:00")
        self.run_("answer", a, "--choice", "yes", "--notes", "fine")
        self.run_("outcome", a, "--verdict", "refined", "--by", "later read")
        out = self.run_("review", "--md").stdout
        self.assertLess(out.index("Decision scores"), out.index("Every decision"))
        self.assertLess(out.index("Second question"), out.index("First \\| question"))
        self.assertIn("refined: later read", out)
        self.assertIn("(no answer yet)", out)
        self.assertIn(b, out)
        since = self.run_("review", "--since", "2026-10-10").stdout
        self.assertNotIn("First", since)

    # --- DECISIONS.md and QUESTIONS.md ---
    def test_decisions_md_is_regenerated_from_the_ledger_after_every_write(self):
        did = self.ask(q="Ship the page?")
        md = (self.perma / "a/proj/DECISIONS.md").read_text()
        self.assertIn(f"### `{did}` — Ship the page?", md)
        self.assertIn("no answer yet", md)
        self.run_("answer", did, "--choice", "yes")
        md = (self.perma / "a/proj/DECISIONS.md").read_text()
        self.assertIn("**Agreed with the recommendation:** yes", md)
        self.assertLess(md.index("## Scores"), md.index("## Every decision"))

    QS = ("# QUESTIONS\n\n## Q — Keep the old cache? (raised 2026-10-01) [OPEN]\nSome context.\n\n"
          "## Q — Rename the tool? (raised 2026-10-02) [OPEN]\nMore context.\n")

    def test_questions_md_round_trip_adds_only_pointer_lines(self):
        qp = self.perma / "a/proj/QUESTIONS.md"
        qp.write_text(self.QS)
        did = self.run_("ask", "--questions-ref", "old cache", "--category", "scope", "--option", "keep",
                        "--option", "drop", "--recommendation", "drop", "--confidence", "0.7",
                        "--evidence-kind", "source-read", "--evidence", "cache.py:12",
                        env={"DECISION_TS": "2026-10-10T09:00:00+01:00"}).stdout.strip()
        self.assertEqual(self.rows()[0]["question"], "Keep the old cache?")
        self.run_("answer", did, "--choice", "keep", "--agreed", "no",
                  env={"DECISION_TS": "2026-10-10T09:30:00+01:00"})
        lines = qp.read_text().split("\n")
        added = [l for l in lines if l not in self.QS.split("\n")]
        self.assertEqual(added, [
            f"Decision `{did}` in DECISIONS.md: asked 2026-10-10, recommended drop (confidence 0.7).",
            f"Decision `{did}` in DECISIONS.md: answered 2026-10-10: keep (differed from the recommendation)."])
        # pointers sit inside the referenced entry, and the rest of the file is unchanged
        self.assertEqual(lines.index("Some context.") + 1, lines.index(added[0]))
        stripped = "\n".join(l for l in lines if l not in added)
        self.assertEqual(stripped, self.QS)
        out = self.run_("review", "--md").stdout
        self.assertIn("Keep the old cache?", out.split("Every decision")[1])

    def test_questions_ref_must_match_exactly_one_entry(self):
        (self.perma / "a/proj/QUESTIONS.md").write_text(self.QS)
        base = ["ask", "--category", "scope", "--option", "a", "--option", "b", "--recommendation", "a",
                "--confidence", "0.5", "--evidence-kind", "inference", "--evidence", "e"]
        for ref in ("Q —", "no such entry"):
            self.assertNotEqual(self.run_(*base, "--questions-ref", ref, ok=False).returncode, 0, ref)
        self.assertEqual((self.perma / "a/proj/QUESTIONS.md").read_text(), self.QS)


if __name__ == "__main__":
    unittest.main()
