"""Tests for runtime/predict-gate.sh. Standard library only:
python3 -m unittest discover -s runtime/tests"""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

RUNTIME = Path(__file__).resolve().parent.parent
GATE = RUNTIME / "predict-gate.sh"
GIT = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}

BASE = {"premium:clean-risk": 1840.40, "premium:referral-risk": 8913.13, "gaps:unfaithful-logic": 9,
        "rules:fired": 120, "definition:file-hash": "aaa", "gaps:capture": 370}


class Check(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def run_gate(self, prediction, measured, baseline=BASE, *extra, env=None):
        (self.d / "moves.prediction.json").write_text(json.dumps(prediction))
        (self.d / "moves.baseline.json").write_text(json.dumps(baseline))
        (self.d / "moves.measured.json").write_text(json.dumps(measured))
        return subprocess.run([str(GATE), "check", "--prediction", str(self.d / "moves.prediction.json"),
                               "--measured", str(self.d / "moves.measured.json"), *extra],
                              capture_output=True, text=True, env=env)

    def after(self, **changes):
        return {**BASE, **{k.replace("__", ":").replace("_", "-"): v for k, v in changes.items()}}

    def test_predicted_and_happened_passes(self):
        p = self.run_gate({"moves": [{"what": "gaps:unfaithful-logic", "from": 9, "to": 11, "scope": "product-a"}],
                           "mustNotMove": ["premium:*"]}, self.after(gaps__unfaithful_logic=11))
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertIn("1. Predicted, and it happened: 1.", p.stdout)
        self.assertIn("gaps:unfaithful-logic: 9 -> 11. Predicted: 9 -> 11. [scope: product-a]", p.stdout)
        self.assertIn("Result: PASS", p.stdout)

    def test_the_2026_10_10_case_unpredicted_move_refuses(self):
        p = self.run_gate({"moves": [], "mustNotMove": ["premium:*"]}, self.after(gaps__unfaithful_logic=11))
        self.assertEqual(p.returncode, 1)
        self.assertIn("4. Moved, and nobody predicted it: 1. Each one stops the commit.", p.stdout)
        self.assertIn("gaps:unfaithful-logic: 9 -> 11.", p.stdout)
        self.assertIn("Result: REFUSED", p.stdout)

    def test_predicted_but_did_not_happen_is_reported_not_refused(self):
        p = self.run_gate({"moves": [{"what": "rules:fired", "delta": 2}, {"what": "rules:nope", "to": 1}]}, BASE)
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertIn("2. Predicted, and it did not happen (reported; does not stop): 2.", p.stdout)
        self.assertIn("rules:fired: 120 -> 120. Predicted: change of +2. Not met: it did not move.", p.stdout)
        self.assertIn("Not met: no measured key matches it.", p.stdout)

    def test_moved_to_a_different_value_refuses(self):
        p = self.run_gate({"moves": [{"what": "rules:fired", "delta": 2}]}, self.after(rules__fired=125))
        self.assertEqual(p.returncode, 1)
        self.assertIn("rules:fired: 120 -> 125. Predicted: change of +2. Not met: it changed by +5.", p.stdout)

    def test_wrong_from_refuses(self):
        p = self.run_gate({"moves": [{"what": "gaps:unfaithful-logic", "from": 8, "to": 11}]},
                          self.after(gaps__unfaithful_logic=11))
        self.assertEqual(p.returncode, 1)
        self.assertIn("baseline was 9, the prediction said 8", p.stdout)

    def test_range_and_any_value(self):
        pred = {"moves": [{"what": "gaps:capture", "range": [360, 375]}, {"what": "definition:file-hash"}]}
        ok = self.run_gate(pred, self.after(gaps__capture=365, definition__file_hash="bbb"))
        self.assertEqual(ok.returncode, 0, ok.stdout)
        bad = self.run_gate(pred, self.after(gaps__capture=380, definition__file_hash="bbb"))
        self.assertEqual(bad.returncode, 1)
        self.assertIn("gaps:capture: 370 -> 380. Predicted: after in [360, 375]. Not met: it reached 380.", bad.stdout)

    def test_must_not_move_breach_refuses(self):
        p = self.run_gate({"moves": [], "mustNotMove": ["premium:clean-risk"]}, self.after(premium__clean_risk=1900.0))
        self.assertEqual(p.returncode, 1)
        self.assertIn("5. Must not move, and it moved: 1.", p.stdout)
        self.assertNotIn("4. Moved, and nobody predicted it: 1", p.stdout)

    def test_must_not_move_not_measured_refuses(self):
        p = self.run_gate({"mustNotMove": ["quotes:*"]}, BASE)
        self.assertEqual(p.returncode, 1)
        self.assertIn("6. Must not move, and it was not measured, so it is unproven: 1.", p.stdout)

    def test_a_named_move_beats_a_must_not_move_glob(self):
        p = self.run_gate({"moves": [{"what": "premium:clean-risk", "to": 1900.0}], "mustNotMove": ["premium:*"]},
                          self.after(premium__clean_risk=1900.0))
        self.assertEqual(p.returncode, 0, p.stdout)
        p = self.run_gate({"moves": [{"what": "premium:clean-risk", "to": 1900.0}], "mustNotMove": ["premium:*"]},
                          self.after(premium__clean_risk=1900.0, premium__referral_risk=1.0))
        self.assertEqual(p.returncode, 1)
        self.assertIn("premium:referral-risk: 8913.13 -> 1.0 (rule: premium:*).", p.stdout)

    def test_tolerance(self):
        pred = {"moves": [], "tolerance": 0.005}
        self.assertEqual(self.run_gate(pred, self.after(premium__clean_risk=1840.404)).returncode, 0)
        self.assertEqual(self.run_gate(pred, self.after(premium__clean_risk=1840.41)).returncode, 1)

    def test_key_appearing_or_disappearing_is_a_move(self):
        gone = {k: v for k, v in BASE.items() if k != "rules:fired"}
        p = self.run_gate({}, {**gone, "rules:new": 1})
        self.assertEqual(p.returncode, 1)
        self.assertIn("rules:fired: 120 -> (absent).", p.stdout)
        self.assertIn("rules:new: (absent) -> 1.", p.stdout)

    def test_bad_input_exits_2(self):
        cases = [
            ({"moves": [{"what": "x", "to": 1, "delta": 1}]}, BASE),
            ({"moves": [{"what": "x", "from": 1}]}, BASE),
            ({"moves": [{"what": "x"}], "mustNotMove": ["x"]}, BASE),
            ({"moves": [], "extra": 1}, BASE),
            ({}, {"nested": {"a": 1}}),
        ]
        for pred, meas in cases:
            p = self.run_gate(pred, meas)
            self.assertEqual(p.returncode, 2, (pred, p.stdout, p.stderr))
            self.assertIn("bad input", p.stderr)

    def test_yaml_named_prediction_written_as_json_reads_without_pyyaml(self):
        (self.d / "moves.prediction.yaml").write_text(json.dumps({"moves": [{"what": "rules:fired", "to": 121}]}))
        (self.d / "moves.baseline.json").write_text(json.dumps(BASE))
        (self.d / "moves.measured.json").write_text(json.dumps(self.after(rules__fired=121)))
        p = subprocess.run([str(GATE), "check", "--prediction", str(self.d / "moves.prediction.yaml"),
                            "--measured", str(self.d / "moves.measured.json")], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_override_without_ledger_stays_refused(self):
        env = dict(os.environ, PERMA_DIR=str(self.d / "no-perma"))
        p = self.run_gate({}, self.after(rules__fired=121), BASE, "--override", "owner said so", env=env)
        self.assertEqual(p.returncode, 1)
        self.assertIn("OVERRIDE REFUSED", p.stdout)


class Ledger(unittest.TestCase):
    """An owned repo registered to a stream, so ops-event.sh can write; the hook end to end."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name).resolve()
        self.perma = t / "perma"
        (self.perma / "_meta").mkdir(parents=True)
        (self.perma / "runtime").mkdir()
        for s in ("resolve-stream.sh", "ops-event.sh", "predict-gate.sh", "predict-gate.py"):
            (self.perma / "runtime" / s).symlink_to(RUNTIME / s)
        self.repo = t / "repo"
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.env = dict(os.environ, PERMA_DIR=str(self.perma), **GIT)
        self.env.pop("PREDICT_GATE_OVERRIDE", None)
        self.git("commit", "-q", "--allow-empty", "-m", "first")
        (self.perma / "a/s/repo").mkdir(parents=True)
        (self.perma / "a/s/repo/binding.json").write_text(json.dumps({"owned": True}))
        (self.perma / "_meta/REGISTRY.md").write_text(f"| path | stream | what |\n|---|---|---|\n| {self.repo} | a/s | t |\n")
        self.ledger = self.perma / "a/s/repo/ops/events.jsonl"
        self.run_dir = self.repo / "runs" / "x"
        self.run_dir.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args, env=None, check=True):
        return subprocess.run(["git", "-C", str(self.repo), *args], capture_output=True, text=True,
                              env=env or self.env, check=check)

    def write(self, prediction, measured, baseline=BASE):
        for name, data in (("moves.prediction.json", prediction), ("moves.baseline.json", baseline),
                           ("moves.measured.json", measured)):
            (self.run_dir / name).write_text(json.dumps(data))

    def gate(self, *args, env=None):
        return subprocess.run([str(self.perma / "runtime/predict-gate.sh"), *args], capture_output=True,
                              text=True, env=env or self.env)

    def test_override_is_recorded_in_the_ops_ledger(self):
        self.write({}, {**BASE, "rules:fired": 121})
        p = self.gate("check", "--prediction", str(self.run_dir / "moves.prediction.json"),
                      "--measured", str(self.run_dir / "moves.measured.json"),
                      "--override", "owner go 13:49: the +1 is the A496 fix", "--task", "A496")
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertIn("OVERRIDDEN by the owner", p.stdout)
        ev = json.loads(self.ledger.read_text().splitlines()[-1])
        self.assertEqual((ev["kind"], ev["task"], ev["outcome"], ev["count"]), ("gate-refused", "A496", "done", 1))
        self.assertIn("owner go 13:49", ev["note"])
        self.assertIn("rules:fired", ev["note"])

    def test_override_not_needed_is_not_recorded(self):
        self.write({}, BASE)
        p = self.gate("check", "--prediction", str(self.run_dir / "moves.prediction.json"),
                      "--measured", str(self.run_dir / "moves.measured.json"), "--override", "x")
        self.assertEqual(p.returncode, 0)
        self.assertFalse(self.ledger.exists())

    def test_install_hook_and_commit(self):
        self.assertEqual(self.gate("install-hook", str(self.repo)).returncode, 0)
        hook = self.repo / ".git/hooks/pre-commit"
        self.assertIn("installed-by: permanence runtime/predict-gate.sh", hook.read_text())
        # 1. unpredicted move: refused
        self.write({"moves": []}, {**BASE, "gaps:unfaithful-logic": 11})
        self.git("add", "-A")
        p = self.git("commit", "-m", "x", check=False)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("4. Moved, and nobody predicted it: 1.", p.stdout + p.stderr)
        # 2. the owner's override: committed, and recorded
        env = dict(self.env, PREDICT_GATE_OVERRIDE="owner accepted 9 -> 11", PREDICT_GATE_TASK="A496")
        p = self.git("commit", "-m", "x", env=env, check=False)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("owner accepted 9 -> 11", self.ledger.read_text())
        # 3. predicted: committed without override
        self.write({"moves": [{"what": "gaps:unfaithful-logic", "from": 11, "to": 12}]},
                   {**BASE, "gaps:unfaithful-logic": 12}, {**BASE, "gaps:unfaithful-logic": 11})
        self.git("add", "-A")
        p = self.git("commit", "-m", "y", check=False)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        # 4. the staged copy is what is checked, not the working tree
        self.write({"moves": []}, {**BASE, "gaps:unfaithful-logic": 13}, {**BASE, "gaps:unfaithful-logic": 12})
        self.git("add", "-A")
        self.write({"moves": [{"what": "gaps:unfaithful-logic"}]}, {**BASE, "gaps:unfaithful-logic": 13},
                   {**BASE, "gaps:unfaithful-logic": 12})
        self.assertNotEqual(self.git("commit", "-m", "z", check=False).returncode, 0)

    def test_hook_ignores_commits_without_a_measured_file(self):
        self.gate("install-hook", str(self.repo))
        (self.run_dir / "moves.prediction.json").write_text(json.dumps({"moves": []}))
        (self.run_dir / "measured.json").write_text(json.dumps({"some": {"nested": 1}}))
        self.git("add", "-A")
        self.assertEqual(self.git("commit", "-m", "prediction first", check=False).returncode, 0)

    def test_hook_refuses_measured_without_prediction_or_baseline(self):
        self.gate("install-hook", str(self.repo))
        (self.run_dir / "moves.measured.json").write_text(json.dumps(BASE))
        self.git("add", "-A")
        p = self.git("commit", "-m", "x", check=False)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("moves.prediction.json, moves.baseline.json is not in the index", p.stdout + p.stderr)

    def test_install_hook_leaves_a_foreign_hook_alone(self):
        hook = self.repo / ".git/hooks/pre-commit"
        hook.write_text("#!/bin/sh\necho mine\n")
        p = self.gate("install-hook", str(self.repo))
        self.assertEqual(p.returncode, 1)
        self.assertIn("was not written by Permanence", p.stdout)
        self.assertEqual(hook.read_text(), "#!/bin/sh\necho mine\n")

    def test_install_hook_skips_hooks_path(self):
        self.git("config", "core.hooksPath", ".githooks")
        p = self.gate("install-hook", str(self.repo))
        self.assertEqual(p.returncode, 1)
        self.assertIn("core.hooksPath", p.stdout)
        self.assertFalse((self.repo / ".git/hooks/pre-commit").exists())


if __name__ == "__main__":
    unittest.main()
