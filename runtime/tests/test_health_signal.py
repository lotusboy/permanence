"""Tests for runtime/health-signal.py. Standard library only. Each test builds a scratch git repository."""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "health-signal.py"
ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
           GIT_COMMITTER_EMAIL="t@t")
for k in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
    ENV.pop(k, None)


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.repo, self.stream = t / "repo", t / "stream"
        self.repo.mkdir()
        self.stream.mkdir()
        self.git("init", "-q")
        self.binding = self.stream / "binding.json"
        self.register = self.stream / "health.json"
        self.rules(part="^src/([^/]+)/")

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args, date="2026-06-10T12:00:00"):
        env = dict(ENV, GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
        subprocess.run(["git", "-C", str(self.repo), *args], check=True, capture_output=True, env=env)

    def commit(self, subject, files, date="2026-06-10T12:00:00"):
        """files: {path: number of lines to write}. Each commit rewrites the file with new lines."""
        for path, n in files.items():
            p = self.repo / path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("".join(f"{subject} {i}\n" for i in range(n)))
        self.git("add", "-A", date=date)
        self.git("commit", "-qm", subject, date=date)

    def rules(self, reviews="reviews/", **signal):
        sig = {"script": "health-signal", "ref": "HEAD", "codeRoots": ["src/"], **signal}
        self.binding.write_text(json.dumps({"owned": True, "register": "health.json", "signal": sig,
                                            "reviews": reviews}))

    def run_signal(self, *args, as_of="2026-06-15"):
        p = subprocess.run(["python3", str(SCRIPT), "--binding", str(self.binding), "--register", "health.json",
                            "--repo", str(self.repo), "--as-of", as_of, *args],
                           capture_output=True, text=True, env=ENV)
        return p.returncode, p.stdout + p.stderr

    def reg(self):
        return json.loads(self.register.read_text())


class TestFixPressure(Fixture):
    def test_a_fix_is_shared_out_by_changed_lines(self):
        self.commit("init", {"src/a/x.py": 1, "src/b/y.py": 1})
        self.commit("fix: one", {"src/a/x.py": 30, "src/b/y.py": 10})
        self.commit("feat: not a fix", {"src/a/x.py": 50})
        code, out = self.run_signal()
        self.assertEqual(code, 0, out)
        p = self.reg()["parts"]
        # the fix replaced 1 line with 30 in a (31 changed) and 1 with 10 in b (11 changed)
        self.assertEqual((p["a"]["linesChanged"], p["b"]["linesChanged"]), (31, 11))
        self.assertEqual((p["a"]["signal"], p["b"]["signal"]), (0.7, 0.3))
        self.assertEqual((p["a"]["fixCommits"], self.reg()["computed"]["fixCommits"]), (1, 1))

    def test_lines_outside_the_code_roots_do_not_dilute(self):
        self.commit("init", {"src/a/x.py": 1, "docs/readme.md": 1})
        self.commit("fix: one", {"src/a/x.py": 10, "docs/readme.md": 500})
        self.run_signal()
        self.assertEqual(self.reg()["parts"]["a"]["signal"], 1.0)

    def test_window_and_fix_pattern(self):
        self.commit("init", {"src/a/x.py": 1}, date="2026-01-01T12:00:00")
        self.commit("fix: old", {"src/a/x.py": 5}, date="2026-02-01T12:00:00")
        self.commit("PRJ-12 fix thing", {"src/a/x.py": 9})
        self.run_signal()
        self.assertEqual(self.reg()["computed"]["fixCommits"], 0)
        self.rules(part="^src/([^/]+)/", fix=r"^PRJ-\d+ fix")
        self.run_signal()
        r = self.reg()
        self.assertEqual((r["computed"]["fixCommits"], r["parts"]["a"]["topIds"]), (1, ["PRJ-12"]))

    def test_part_list_first_match_wins_and_id_template(self):
        self.rules(parts=[{"kind": "contract", "match": r"^src/pkg/(schemas/.+\.json)$"},
                          {"kind": "module", "match": r"^src/pkg/(.+\.py)$"},
                          {"kind": "config", "match": r"^conf/([^/]+)/", "id": "config/{1}"}],
                   codeRoots=["src/", "conf/"])
        self.commit("init", {"src/pkg/schemas/s.json": 2, "src/pkg/m/n.py": 2, "conf/acme/a.yaml": 2,
                             "src/pkg/notes.txt": 2})
        self.run_signal()
        p = self.reg()["parts"]
        self.assertEqual({k: v["kind"] for k, v in p.items()},
                         {"schemas/s.json": "contract", "m/n.py": "module", "config/acme": "config"})

    def test_extensions_limit_what_belongs_to_a_part(self):
        self.rules(part="^src/([^/]+)/", extensions=[".cls"])
        self.commit("init", {"src/a/x.cls": 3, "src/b/readme.md": 3})
        self.run_signal()
        self.assertEqual(list(self.reg()["parts"]), ["a"])

    def test_it_measures_the_ref_not_the_checkout(self):
        self.commit("init", {"src/a/x.py": 1})
        self.git("branch", "pinned")
        self.commit("fix: later", {"src/a/x.py": 9, "src/new/z.py": 4})
        self.rules(part="^src/([^/]+)/", ref="pinned")
        self.run_signal()
        r = self.reg()
        self.assertEqual((list(r["parts"]), r["computed"]["fixCommits"]), (["a"], 0))


class TestStateAndDecision(Fixture):
    def setUp(self):
        super().setUp()
        self.commit("init", {"src/a/x.py": 1, "src/b/y.py": 1})
        for i in range(3):
            self.commit(f"fix: a{i}", {"src/a/x.py": 5 + i})

    def test_ready_at_the_threshold(self):
        self.run_signal("--threshold", "3")
        p = self.reg()["parts"]
        self.assertEqual((p["a"]["state"], p["b"]["state"]), ("ready", "settled"))
        self.assertIn("1 part(s) ready", self.run_signal("--threshold", "3", "--no-write")[1])

    def test_decision_and_settings_are_never_overwritten(self):
        d = {"date": "2026-06-01", "decision": "restructure", "reason": "r", "backlogId": "T77"}
        self.register.write_text(json.dumps({"settings": {"threshold": 3.0, "mine": "kept"},
                                             "parts": {"a": {"decision": d}}}))
        self.run_signal()
        r = self.reg()
        self.assertEqual(r["settings"]["threshold"], 3.0)
        self.assertEqual(r["settings"]["mine"], "kept")
        self.assertEqual(r["parts"]["a"]["decision"], dict(d, signalAtDecision=3.0))
        self.assertEqual(r["parts"]["a"]["state"], "reshaped")
        self.commit("fix: more", {"src/a/x.py": 20})
        self.commit("fix: more again", {"src/a/x.py": 21})
        self.run_signal()
        r = self.reg()
        self.assertEqual(r["parts"]["a"]["decision"]["signalAtDecision"], 3.0)
        self.assertEqual((r["parts"]["a"]["signal"], r["parts"]["a"]["state"]), (5.0, "ready-again"))

    def test_a_decided_parts_own_work_is_not_counted_against_it(self):
        d = {"date": "2026-06-01", "decision": "accept", "backlogId": "T77", "signalAtDecision": 3.0}
        self.register.write_text(json.dumps({"parts": {"a": {"decision": d}}}))
        self.commit("fix(T77): the restructure itself", {"src/a/x.py": 40})
        self.run_signal()
        a = self.reg()["parts"]["a"]
        self.assertEqual((a["signal"], a["state"]), (3.0, "kept"))

    def test_a_decided_part_that_is_gone_is_kept_and_marked(self):
        d = {"date": "2026-06-01", "decision": "accept"}
        self.register.write_text(json.dumps({"parts": {"gone": {"kind": "part", "decision": d}}}))
        self.run_signal()
        self.assertIs(self.reg()["parts"]["gone"]["present"], False)

    def test_no_write_leaves_the_register_alone(self):
        self.assertEqual(self.run_signal("--no-write")[0], 0)
        self.assertFalse(self.register.exists())


class TestSizeAndReviews(Fixture):
    def test_size_per_part(self):
        self.commit("init", {"src/a/x.py": 7, "src/a/long.py": 40, "src/b/y.py": 2})
        self.run_signal()
        a = self.reg()["parts"]["a"]["size"]
        self.assertEqual(a, {"files": 2, "lines": 47, "longestFile": {"path": "src/a/long.py", "lines": 40}})

    def test_review_findings_in_the_window_that_name_a_file(self):
        self.commit("init", {"src/a/x.py": 1, "src/b/y.py": 1})
        for folder, text in (
            ("2026-06-12-thing", "### P1 wrong order\nIn src/a/x.py the order breaks.\n\nP2 small, src/b/y.py\n"),
            ("2026-06-13-other", "P1: also src/a/x.py and src/b/y.py\n"),
            ("2026-01-01-old", "P1 src/b/y.py long ago\n"),
            ("notes", "P1 src/b/y.py undated\n"),
        ):
            (self.repo / "reviews" / folder).mkdir(parents=True)
            (self.repo / "reviews" / folder / "findings.md").write_text(text)
        self.run_signal()
        r = self.reg()
        self.assertEqual((r["parts"]["a"]["reviewFindings"], r["parts"]["b"]["reviewFindings"]), (2, 1))
        self.assertEqual(r["computed"]["reviewFolders"], 2)
        self.assertEqual(r["parts"]["a"]["state"], "settled")  # reported only: never moves the state


class TestRefusals(Fixture):
    def test_binding_without_rules(self):
        self.binding.write_text(json.dumps({"signal": "make health"}))
        code, out = self.run_signal()
        self.assertEqual(code, 1)
        self.assertIn('not rules for this script', out)

    def test_no_part_rule_and_bad_pattern(self):
        self.rules()
        self.assertIn("gives no part rule", self.run_signal()[1])
        self.rules(part="^src/[^/]+/")
        self.assertIn("needs one group", self.run_signal()[1])
        self.rules(part="(")
        self.assertIn("signal.part does not compile", self.run_signal()[1])

    def test_a_register_that_is_not_json_is_not_overwritten(self):
        self.commit("init", {"src/a/x.py": 1})
        self.register.write_text("settings: {threshold: 8.0}\nparts:\n  a:\n    decision: null\n")
        code, out = self.run_signal()
        self.assertEqual(code, 1)
        self.assertIn("is not JSON", out)
        self.assertTrue(self.register.read_text().startswith("settings:"))

    def test_bad_decision_stops_before_writing(self):
        self.commit("init", {"src/a/x.py": 1})
        self.register.write_text(json.dumps({"parts": {"a": {"decision": {"decision": "maybe"}}}}))
        before = self.register.read_text()
        code, out = self.run_signal()
        self.assertEqual(code, 1)
        self.assertIn("parts.a.decision needs a date", out)
        self.assertEqual(self.register.read_text(), before)

    def test_the_repository_is_left_unchanged(self):
        self.commit("init", {"src/a/x.py": 1})
        self.run_signal()
        st = subprocess.run(["git", "-C", str(self.repo), "status", "--porcelain"], capture_output=True, text=True, env=ENV)
        self.assertEqual(st.stdout, "")


if __name__ == "__main__":
    unittest.main()
