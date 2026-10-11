"""Tests for runtime/team-preflight.py. Standard library only: python3 -m unittest discover runtime/tests"""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "team-preflight.py"
RECIPE = """steps:
  - id: build
    command: true
  - id: signal
    command: >-
      true --flag
gates:
  - id: tests
    command: true
  - id: review
    command: a careful read of the diff by a second agent
other: 1
"""


def run(*args, env=None):
    p = subprocess.run(["python3", str(SCRIPT), *args], capture_output=True, text=True, env=env)
    return p.returncode, p.stdout + p.stderr


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.repo = t / "repo"
        (self.repo / "docs").mkdir(parents=True)
        (self.repo / "reviews").mkdir()
        (self.repo / "docs" / "TRACKER.md").write_text("x\n")
        (self.repo / "recipe.yaml").write_text(RECIPE)
        (self.repo / "recipe.json").write_text(json.dumps({"gates": [{"id": "tests", "command": "true"}]}))
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.stream = t / "stream" / "repo"
        self.stream.mkdir(parents=True)
        self.binding = self.stream / "binding.json"
        # scratch install: results never depend on this machine's agents, plugins or tables
        (t / "home").mkdir()
        (t / "perma" / "runtime").mkdir(parents=True)
        self.env = dict(os.environ, HOME=str(t / "home"), PERMA_DIR=str(t / "perma"))

    def tearDown(self):
        self.tmp.cleanup()

    def owned(self, **over):
        b = {"owned": True, "register": "shape.yaml", "signal": "recipe.yaml#steps.signal",
             "tracker": {"file": "docs/TRACKER.md", "id": "^T[0-9]+$"},
             "measure": {"commands": ["echo {register} {part}"]},
             "gates": {"byteIdentical": "recipe.yaml#gates",
                       "predictedMoves": {"gates": "recipe.json#gates.tests", "prediction": "p.md"}},
             "reviews": "reviews/", "reviewName": "{date}-{id}-step{n}-review",
             "branches": {"refactor": "r/{id}-{n}-{name}", "change": "f/{id}-{name}"}}
        b.update(over)
        self.binding.write_text(json.dumps(b))

    def other(self):
        self.binding.write_text(json.dumps({"owned": False, "approver": "the repository's PM",
                                            "register": "h.json", "signal": "recipe.yaml#steps.build"}))

    def pre(self, *job):
        return run(*job, "--repo", str(self.repo), "--binding", str(self.binding), env=self.env)


class TestOwned(Fixture):
    def test_valid_binding_passes_and_lists_prose_gate(self):
        self.owned()
        code, out = self.pre("health")
        self.assertEqual(code, 0, out)
        self.assertIn("prose gates, run by the reviewer: review", out)
        self.assertNotIn("tests", out.split("prose gates")[1].split("\n")[0])

    def test_job_reports_roles(self):
        self.owned()
        code, out = self.pre("refactor", "engine")
        self.assertEqual(code, 0, out)
        self.assertIn("role refactor:reviewer -> ", out)

    def test_binding_role_override_wins(self):
        self.owned(roles={"refactor:engineer": "general-purpose"})
        code, out = self.pre("refactor", "engine")
        self.assertIn("role refactor:engineer -> general-purpose (from binding roles", out)

    def test_uninstalled_override_is_skipped_and_logged(self):
        self.owned(roles={"engineer": "no-such-agent"})
        code, out = self.pre("change", "T1")
        self.assertEqual(code, 0, out)
        self.assertIn("names ['no-such-agent'], not installed; skipped", out)

    def test_renamed_path_fails_and_names_it(self):
        self.owned(tracker={"file": "docs/TRACKER-renamed.md", "id": "^T[0-9]+$"})
        code, out = self.pre("health")
        self.assertEqual(code, 1)
        self.assertIn("path field 'tracker.file' = 'docs/TRACKER-renamed.md' does not exist", out)

    def test_placeholder_path_checks_prefix(self):
        self.owned(leaveAlone=["docs/{id}.md"])
        self.assertEqual(self.pre("health")[0], 0)
        self.owned(leaveAlone=["gone/{id}.md"])
        self.assertIn("'leaveAlone' = 'gone/{id}.md' does not exist", self.pre("health")[1])

    def test_broken_yaml_pointer_fails_and_names_it(self):
        self.owned(signal="recipe.yaml#steps.renamed-step")
        code, out = self.pre("health")
        self.assertEqual(code, 1)
        self.assertIn("pointer 'signal' = 'recipe.yaml#steps.renamed-step': no item 'id: renamed-step' under 'steps'", out)

    def test_yaml_item_under_another_key_does_not_count(self):
        self.owned(signal="recipe.yaml#gates.build")
        self.assertIn("no item 'id: build' under 'gates'", self.pre("health")[1])

    def test_missing_top_level_key_and_json_pointer(self):
        self.owned(gates={"byteIdentical": "recipe.yaml#nokey",
                          "predictedMoves": {"gates": "recipe.json#gates.nope", "prediction": "p.md"}})
        code, out = self.pre("health")
        self.assertEqual(code, 1)
        self.assertIn("no top-level 'nokey:' line in recipe.yaml", out)
        self.assertIn("no item 'id: nope' under 'gates' in recipe.json", out)

    def test_measure_command_pointer_is_checked(self):
        self.owned(measure={"commands": ["missing.yaml#steps"]})
        self.assertIn("pointer 'measure.commands.0' = 'missing.yaml#steps': file 'missing.yaml' does not exist",
                      self.pre("health")[1])

    def test_required_field_missing(self):
        self.owned(branches={"refactor": "r/{id}"})
        code, out = self.pre("health")
        self.assertEqual(code, 1)
        self.assertIn("required field 'branches.change' is missing", out)

    def test_unknown_placeholder_fails_regex_fields_exempt(self):
        self.owned(reviewName="{date}-{ticket}", tracker={"file": "docs/TRACKER.md", "id": "^T[0-9]{2}$"})
        code, out = self.pre("health")
        self.assertEqual(code, 1)
        self.assertIn("'reviewName' uses placeholder '{ticket}'", out)
        self.assertNotIn("tracker.id", out)

    def test_unparsable_binding(self):
        self.binding.write_text("{not json")
        code, out = self.pre("health")
        self.assertEqual(code, 1)
        self.assertIn("check 2", out)

    def test_missing_binding(self):
        none = str(self.stream / "none.json")
        code, out = run("health", "--repo", str(self.repo), "--binding", none, env=self.env)
        self.assertEqual(code, 1)
        self.assertIn("FAIL check 1", out)
        self.assertEqual(run("startup", "--repo", str(self.repo), "--binding", none, env=self.env)[0], 0)

    def test_empty_outside_and_non_string_paths_fail(self):
        for bad, msg in (("", "= \"\" is not a path"), ("../x", "'reviews' = '../x' is outside"),
                         ("/etc", "'reviews' = '/etc' is outside")):
            self.owned(reviews=bad)
            code, out = self.pre("health")
            self.assertEqual(code, 1, bad)
            self.assertIn(msg, out)
        self.owned(leaveAlone=[{"x": 1}])
        code, out = self.pre("health")
        self.assertEqual(code, 1)
        self.assertIn("FAIL check 3: path field 'leaveAlone' = {\"x\": 1} is not a path", out)
        self.assertNotIn("Traceback", out)

    def test_angle_placeholder_in_binding_fails(self):
        self.owned(measure={"commands": ["echo <touched files>"]})
        code, out = self.pre("health")
        self.assertEqual(code, 1)
        self.assertIn("'measure.commands.0' uses a '<...>' placeholder", out)

    def test_role_check_reads_the_next_table_before_the_swap(self):
        rt = Path(self.env["PERMA_DIR"]) / "runtime"
        (rt / "agent-roles.json").write_text(json.dumps({"roles": {"refactor-engineer": {"providers": ["Plan"]}}}))
        (rt / "agent-roles.next.json").write_text(json.dumps({"roles": {"engineer": {"providers": ["Explore"]}}}))
        self.owned()
        self.assertIn("role refactor:engineer -> Explore (from runtime/agent-roles.next.json", self.pre("refactor", "engine")[1])
        (rt / "agent-roles.next.json").unlink()
        self.assertIn("role refactor:engineer -> the session does it", self.pre("refactor", "engine")[1])

    def test_job_needs_its_argument(self):
        self.owned()
        self.assertEqual(self.pre("refactor")[0], 2)


class TestApproval(Fixture):
    """Move 1 gate: owned false - no record fails, unconsumed same scope passes, consumed fails."""

    def approvals(self, records):
        (self.stream / "approvals.json").write_text(json.dumps(records))

    def rec(self, scope, consumed=""):
        return {"proposal": "P1", "approver": "the repository's PM", "date": "2026-10-05",
                "scope": scope, "consumed": consumed}

    def test_no_approvals_file_fails(self):
        self.other()
        code, out = self.pre("refactor", "engine")
        self.assertEqual(code, 1)
        self.assertIn("check 6", out)

    def test_no_matching_record_fails(self):
        self.other()
        self.approvals([self.rec({"part": "other"}), self.rec({"workOrder": "engine"})])
        code, out = self.pre("refactor", "engine")
        self.assertEqual(code, 1)
        self.assertIn('holds no approval with scope {"part": "engine"}', out)

    def test_unconsumed_matching_record_passes(self):
        self.other()
        self.approvals([self.rec({"part": "engine"})])
        self.assertEqual(self.pre("refactor", "engine")[0], 0)
        self.approvals([self.rec({"workOrder": "T-1"})])
        self.assertEqual(self.pre("change", "T-1")[0], 0)

    def test_superset_scope_does_not_match(self):
        self.other()
        self.approvals([self.rec({"part": "engine", "workOrder": "T-1"})])
        self.assertEqual(self.pre("refactor", "engine")[0], 1)
        self.assertEqual(self.pre("change", "T-1")[0], 1)

    def test_consumed_record_fails(self):
        self.other()
        self.approvals([self.rec({"part": "engine"}, consumed="https://example.invalid/pr/1")])
        code, out = self.pre("refactor", "engine")
        self.assertEqual(code, 1)
        self.assertIn("is consumed", out)

    def test_health_skips_approval(self):
        self.other()
        self.assertEqual(self.pre("health")[0], 0)

    def test_owned_false_needs_approver(self):
        self.binding.write_text(json.dumps({"owned": False, "register": "h.json", "signal": "true"}))
        self.assertIn("required field 'approver' is missing", self.pre("health")[1])


class TestSignalRules(Fixture):
    def test_generic_script_rules(self):
        (self.repo / "src").mkdir()
        (self.repo / "src" / "a.py").write_text("x\n")
        g = ["git", "-C", str(self.repo), "-c", "user.name=t", "-c", "user.email=t@t"]
        subprocess.run(g + ["add", "-A"], check=True)
        subprocess.run(g + ["commit", "-qm", "init"], check=True)
        perma = Path(self.tmp.name) / "perma"
        (perma / "runtime").mkdir(parents=True, exist_ok=True)
        env = dict(self.env, PERMA_DIR=str(perma))
        sig = {"script": "health-signal", "ref": "HEAD", "fix": "^fix", "codeRoots": ["src/"]}
        self.binding.write_text(json.dumps({"owned": False, "approver": "PM", "register": "h.json", "signal": sig}))
        args = ("health", "--repo", str(self.repo), "--binding", str(self.binding))
        for job in ("health", "startup"):
            code, out = run(job, *args[1:], env=env)
            self.assertEqual(code, 0, out)
            self.assertIn("note check 4: the generic signal script is not installed yet", out)
        (self.stream / "approvals.json").write_text(json.dumps(
            [{"scope": {"part": "src"}, "consumed": ""}, {"scope": {"workOrder": "T-1"}, "consumed": ""}]))
        code, out = run("change", "T-1", *args[1:], env=env)
        self.assertEqual(code, 0, out)
        self.assertIn("note check 4: the generic signal script is not installed yet", out)
        code, out = run("refactor", "src", *args[1:], env=env)
        self.assertEqual(code, 1)
        self.assertIn("FAIL check 4: the generic signal script is not installed yet", out)
        (perma / "runtime" / "health-signal.py").write_text("")
        code, out = run(*args, env=env)
        self.assertEqual(code, 0)
        self.assertNotIn("not installed", out)
        self.assertEqual(run("refactor", "src", *args[1:], env=env)[0], 0)
        sig.update(ref="nope", fix="(")
        self.binding.write_text(json.dumps({"owned": False, "approver": "PM", "register": "h.json", "signal": sig}))
        out = run(*args, env=env)[1]
        self.assertIn("signal.fix does not compile", out)
        self.assertIn("signal.ref 'nope' does not resolve", out)
        sig.update(ref="HEAD", fix="^fix", codeRoots=["src/", "lib/"])
        self.binding.write_text(json.dumps({"owned": False, "approver": "PM", "register": "h.json", "signal": sig}))
        self.assertIn("signal.codeRoots 'lib/' does not exist at HEAD", run(*args, env=env)[1])


if __name__ == "__main__":
    unittest.main()
