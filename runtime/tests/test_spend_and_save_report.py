"""Tests for runtime/spend.sh and runtime/save-report.sh. Standard library only:
python3 -m unittest discover -s runtime/tests"""
import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

RUNTIME = Path(__file__).resolve().parent.parent
GIT = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}


class Spend(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name).resolve()
        self.perma = t / "perma"
        (self.perma / "_meta").mkdir(parents=True)
        (self.perma / "runtime").mkdir()
        for s in ("resolve-stream.sh", "spend.sh", "spend.py", "ops-event.sh"):
            (self.perma / "runtime" / s).symlink_to(RUNTIME / s)
        self.work = t / "work"
        subprocess.run(["git", "init", "-q", str(self.work)], check=True)
        subprocess.run(["git", "-C", str(self.work), "commit", "-q", "--allow-empty", "-m", "first"],
                       check=True, env=dict(os.environ, **GIT))
        (self.perma / "a/proj/repo").mkdir(parents=True)
        (self.perma / "a/proj/repo/binding.json").write_text(json.dumps({"owned": True}))
        (self.perma / "_meta/REGISTRY.md").write_text(f"| path | stream | what |\n|---|---|---|\n| {self.work} | a/proj | t |\n")
        self.env = dict(os.environ, PERMA_DIR=str(self.perma), **GIT)
        for k in ("SPEND_TS", "OPS_REPO", "OPS_TS"):
            self.env.pop(k, None)
        self.ledger = self.perma / "a/proj/spend/ledger.jsonl"
        self.ops = self.perma / "a/proj/repo/ops/events.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def run_(self, *args, env=None, ok=True, cwd=None):
        p = subprocess.run([str(self.perma / "runtime/spend.sh"), *args], cwd=cwd or self.work,
                           capture_output=True, text=True, env=dict(self.env, **(env or {})))
        if ok:
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        return p

    RESULT = ["--why", "a build agent for engine work", "--predicted", "the gate passes",
              "--predicted-tokens", "10000", "--result", "the gate passed", "--outcome", "as-predicted"]

    def rec(self, agent, tokens, *extra, **kw):
        res = [] if "--correct" in extra or "--outcome" in extra else self.RESULT
        return self.run_("record", "--agent", agent, "--label", f"job {agent}", "--tokens", str(tokens),
                         *res, *extra, **kw)

    def test_a_first_record_states_the_tools_result_not_only_its_cost(self):
        p = self.run_("record", "--agent", "x1", "--label", "j", "--tokens", "100", ok=False)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("--outcome", p.stderr)
        self.assertFalse(self.ledger.exists())
        self.rec("x1", 10000)
        row = json.loads(self.ledger.read_text().splitlines()[-1])
        self.assertEqual((row["outcome"], row["predictedTokens"], row["why"]),
                         ("as-predicted", 10000, "a build agent for engine work"))
        self.rec("x1", 12000, "--correct")

    def test_a_second_architect_run_for_a_task_needs_a_step_back(self):
        self.rec("ar1", 10000, "--kind", "architect", "--task", "A9")
        p = self.rec("ar2", 10000, "--kind", "architect", "--task", "A9", ok=False)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("--stepped-back", p.stderr)
        self.rec("ar2", 10000, "--kind", "architect", "--task", "A9", "--stepped-back", "looked upstream first")
        self.rec("ar3", 10000, "--kind", "architect", "--task", "A10")

    def test_review_2026_10_16_the_spend_gates_need_real_values(self):
        # the example in runtime/README.md and spend.sh's header passes as written
        self.run_("record", "--agent", "a1b2c3", "--label", "S2 answers r1", "--tokens", "131204",
                  "--kind", "answering-agent", "--task", "A508", "--why", "answer the 40 open rows",
                  "--predicted", "36 of 40 answered", "--predicted-tokens", "120000",
                  "--result", "38 of 40 answered", "--outcome", "better")
        # empty values are refused
        p = self.run_("record", "--agent", "e1", "--label", "L", "--tokens", "10", "--why", " ", "--predicted", "",
                      "--predicted-tokens", "1", "--result", "", "--outcome", "as-predicted", ok=False)
        self.assertIn("--why", p.stderr)
        # an architect run names its task; a second one on the same task, whatever its case, needs a real step-back
        self.assertIn("--task", self.rec("ar0", 10, "--kind", "architect", ok=False).stderr)
        self.rec("ar1", 10, "--kind", "architect", "--task", "T9")
        self.assertNotEqual(self.rec("ar2", 10, "--kind", "architect", "--task", "t9", ok=False).returncode, 0)
        self.assertNotEqual(self.rec("ar2", 10, "--kind", "architect", "--task", "T9", "--stepped-back", " .",
                                     ok=False).returncode, 0)

    def test_a_worse_or_far_off_run_gets_a_lesson_stub_in_tools_md(self):
        tools = self.perma / "a/proj/TOOLS.md"
        tools.write_text("# TOOLS\n")
        self.rec("x2", 10500)
        self.assertEqual(tools.read_text(), "# TOOLS\n")
        self.rec("x3", 10000, "--why", "w", "--predicted", "8 of 15 right", "--predicted-tokens", "10000",
                 "--result", "2 of 15 right", "--outcome", "worse")
        self.rec("x4", 30000, "--why", "w", "--predicted", "p", "--predicted-tokens", "10000",
                 "--result", "r", "--outcome", "as-predicted")
        text = tools.read_text()
        self.assertIn("x3", text)
        self.assertIn("2 of 15 right", text)
        self.assertIn("x4", text)
        self.assertEqual(text.count("**Lesson:** TODO"), 2)

    def status(self, *extra):
        return json.loads(self.run_("status", "--json", *extra).stdout)["waves"]

    def test_record_goes_to_the_open_wave_and_status_sums_it(self):
        self.run_("wave", "open", "w1", "--ceiling", "100,000")
        self.rec("a1", 30000)
        self.rec("a2", "20_000", "--kind", "reviewer")
        (w,) = self.status()
        self.assertEqual((w["wave"], w["spent"], w["ceiling"], w["level"]), ("w1", 50000, 100000, "ok"))
        self.assertEqual([r["agent"] for r in w["agents"]], ["a1", "a2"])
        self.assertEqual(w["agents"][1]["kind"], "reviewer")

    def test_warns_at_80_and_stops_at_100_percent(self):
        self.run_("wave", "open", "w1", "--ceiling", "1000")
        self.assertNotIn("WARNING", self.rec("a1", 790).stderr)
        p = self.rec("a2", 10)
        self.assertIn("WARNING", p.stderr)
        self.assertEqual(self.status()[0]["level"], "warn")
        p = self.rec("a3", 200)
        self.assertIn("STOP", p.stderr)
        self.assertEqual(self.status()[0]["level"], "over")
        self.assertIn("STOP", self.run_("status").stdout)

    def test_duplicate_agent_is_refused_and_correct_replaces_without_editing(self):
        self.run_("wave", "open", "w1", "--ceiling", "1000")
        self.rec("a1", 100)
        self.assertNotEqual(self.rec("a1", 200, ok=False).returncode, 0)
        self.rec("a1", 250, "--correct", "--note", "harness figure, not the self-report")
        self.assertEqual(self.status()[0]["spent"], 250)
        self.assertEqual(len([l for l in self.ledger.read_text().splitlines() if '"agent"' in l]), 2)
        self.assertNotEqual(self.rec("zz", 5, "--correct", ok=False).returncode, 0)

    def test_bad_input_writes_nothing(self):
        self.run_("wave", "open", "w1", "--ceiling", "1000")
        before = self.ledger.read_text()
        for tok in ("0", "-5", "410k", "1.5"):
            self.assertNotEqual(self.rec("a1", tok, ok=False).returncode, 0, tok)
        self.assertNotEqual(self.rec("a1", 5, "--wave", "nope", ok=False).returncode, 0)
        self.assertNotEqual(self.rec("a1", 5, "--kind", "intern", ok=False).returncode, 0)
        self.assertNotEqual(self.run_("wave", "open", "w1", "--ceiling", "5", ok=False).returncode, 0)
        self.assertNotEqual(self.run_("wave", "open", "w2", ok=False).returncode, 0)
        self.assertEqual(self.ledger.read_text(), before)

    def test_two_open_waves_need_an_explicit_wave(self):
        self.run_("wave", "open", "w1", "--ceiling", "1000")
        self.run_("wave", "open", "w2", "--ceiling", "1000")
        self.assertNotEqual(self.rec("a1", 5, ok=False).returncode, 0)
        self.rec("a1", 5, "--wave", "w2")
        self.assertNotEqual(self.run_("wave", "close", ok=False).returncode, 0)
        self.run_("wave", "close", "w1")
        self.run_("wave", "close")
        self.assertEqual(self.status(), [])
        self.assertEqual([w["wave"] for w in self.status("--all")], ["w1", "w2"])
        self.assertNotEqual(self.run_("wave", "close", "w1", ok=False).returncode, 0)

    def test_record_with_no_wave_open_is_kept_unwaved(self):
        self.rec("a1", 7)
        (row,) = [json.loads(l) for l in self.ledger.read_text().splitlines()]
        self.assertIsNone(row["wave"])
        rep = json.loads(self.run_("report", "--json").stdout)
        self.assertEqual(rep["wave"], {"(no wave)": 7})

    def test_report_totals_by_day_wave_kind_and_source_with_since(self):
        self.run_("wave", "open", "w1", "--ceiling", "1000")
        self.rec("old", 100, "--note", "backfilled from the 9 Oct notification", env={"SPEND_TS": "2026-10-09T10:00:00+01:00"})
        self.rec("a1", 30, "--kind", "architect", "--task", "R1")
        self.rec("a2", 5, "--source", "self-reported")
        rep = json.loads(self.run_("report", "--json").stdout)
        self.assertEqual(rep["total"], 135)
        self.assertEqual(rep["day"]["2026-10-09"], 100)
        self.assertEqual(rep["kind"], {"agent": 105, "architect": 30})
        self.assertEqual(rep["source"], {"harness": 130, "self-reported": 5})
        self.assertEqual(json.loads(self.run_("report", "--json", "--since", "2026-10-10").stdout)["total"], 35)
        self.assertIn("not measured", self.run_("status").stdout)

    def test_backfill_needs_a_note(self):
        p = self.rec("a1", 5, env={"SPEND_TS": "2026-10-09T10:00:00+01:00"}, ok=False)
        self.assertNotEqual(p.returncode, 0)
        self.assertFalse(self.ledger.exists())

    def test_record_also_writes_the_ops_ledger_once(self):
        self.rec("a1", 1234, "--task", "A508")
        (row,) = [json.loads(l) for l in self.ops.read_text().splitlines()]
        self.assertEqual((row["kind"], row["task"], row["tokens"], row["outcome"]), ("agent-run", "A508", 1234, "done"))
        self.assertIn("agent=a1", row["note"])
        self.rec("a2", 9, "--no-ops")
        self.rec("a3", 9, "--source", "estimate")
        rows = [json.loads(l) for l in self.ops.read_text().splitlines()]
        self.assertEqual(len(rows), 2)
        self.assertIsNone(rows[1]["tokens"])

    def test_unowned_stream_and_explicit_stream_skip_the_ops_ledger(self):
        (self.perma / "b").mkdir()
        p = self.rec("a1", 5, "--stream", "b", cwd=self.perma)
        self.assertTrue((self.perma / "b/spend/ledger.jsonl").exists())
        self.assertNotIn("ops ledger", p.stdout)
        (self.perma / "a/proj/repo/binding.json").write_text(json.dumps({"owned": False}))
        self.assertIn("not written", self.rec("a2", 5).stdout)
        self.assertFalse(self.ops.exists())

    def test_unregistered_directory_without_stream_fails(self):
        p = self.run_("status", cwd=self.perma, ok=False)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("--stream", p.stderr)


class SaveReport(unittest.TestCase):
    BODY = ("# Report\n\nTabs\tkept,  double  spaces, trailing space \n"
            "CRLF line\r\nunicode: £8,913.13 — “quotes” ✓\n\n\n```\n  code\n```\nno final newline").encode("utf-8")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name).resolve()
        self.env = dict(os.environ, SAVE_REPORT_NOW="2026-10-10 14:00 +01:00")

    def tearDown(self):
        self.tmp.cleanup()

    def save(self, dest, *args, body=None, ok=True):
        p = subprocess.run([str(RUNTIME / "save-report.sh"), str(dest), *args], input=self.BODY if body is None else body,
                           capture_output=True, env=self.env)
        if ok:
            self.assertEqual(p.returncode, 0, (p.stdout + p.stderr).decode())
        return p

    def split(self, data):
        head, sep, body = data.partition(b"\n---\n\n")
        self.assertTrue(sep)
        return head.decode(), body

    def test_body_is_byte_identical_and_header_names_title_date_and_agent(self):
        dest = self.dir / "deep/new/report.md"
        self.save(dest, "--title", "S2 slice", "--source-agent", "a1b2c3")
        head, body = self.split(dest.read_bytes())
        self.assertEqual(body, self.BODY)
        self.assertTrue(head.startswith("# S2 slice\n"))
        for want in ("2026-10-10 14:00 +01:00", "a1b2c3", "Saved verbatim by the PM",
                     hashlib.sha256(self.BODY).hexdigest()[:16], f"{len(self.BODY)} bytes"):
            self.assertIn(want, head)

    def test_title_defaults_to_the_file_name(self):
        dest = self.dir / "review-notes.md"
        self.save(dest)
        self.assertTrue(dest.read_text().startswith("# review-notes\n"))

    def test_refuses_to_overwrite_without_a_flag(self):
        dest = self.dir / "r.md"
        self.save(dest)
        first = dest.read_bytes()
        p = self.save(dest, body=b"other", ok=False)
        self.assertNotEqual(p.returncode, 0)
        self.assertEqual(dest.read_bytes(), first)
        self.save(dest, "--force", body=b"second report\n")
        self.assertEqual(self.split(dest.read_bytes())[1], b"second report\n")

    def test_append_adds_a_section_and_keeps_both_bodies_verbatim(self):
        dest = self.dir / "r.md"
        self.save(dest, "--source-agent", "one")
        first = dest.read_bytes()
        self.save(dest, "--append", "--source-agent", "two", body=b"second\n")
        data = dest.read_bytes()
        self.assertTrue(data.startswith(first))
        self.assertIn(self.BODY, data)
        self.assertTrue(data.endswith(b"\n---\n\nsecond\n"))
        self.assertIn(b"from agent two", data)

    def test_append_and_force_together_are_refused(self):
        self.assertNotEqual(self.save(self.dir / "r.md", "--append", "--force", ok=False).returncode, 0)

    def test_empty_input_and_directory_destination_are_refused(self):
        self.assertNotEqual(self.save(self.dir / "r.md", body=b"  \n", ok=False).returncode, 0)
        self.assertFalse((self.dir / "r.md").exists())
        self.assertNotEqual(self.save(self.dir, ok=False).returncode, 0)


if __name__ == "__main__":
    unittest.main()
