"""Tests for the Antigravity binding's project-team pieces: the role hook and the agent installer.
Standard library only. Scratch HOME and PERMA_DIR throughout."""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

RUNTIME = Path(__file__).resolve().parent.parent
BINDING = RUNTIME / "bindings" / "antigravity"
HOOK = BINDING / "agent-roles-hook.py"
INSTALL = BINDING / "agents-install.py"


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.home, self.perma, self.repo, self.other = t / "home", t / "perma", t / "repo", t / "other"
        self.agents = self.home / ".gemini" / "config" / "agents"
        for d in (self.agents, self.perma / "runtime", self.perma / "_meta", self.repo, self.other):
            d.mkdir(parents=True)
        (self.perma / "runtime" / "resolve-stream.sh").symlink_to(RUNTIME / "resolve-stream.sh")
        (self.perma / "runtime" / "agent-roles.json").write_text((RUNTIME / "agent-roles.json").read_text())
        (self.perma / "_meta" / "REGISTRY.md").write_text(
            f"| workspace path | stream | notes |\n|---|---|---|\n| {self.repo} | team/repo | x |\n")
        self.env = dict(os.environ, HOME=str(self.home), PERMA_DIR=str(self.perma))
        self.env.pop("PERMA_HARNESS", None)
        self.install("refactor-engineer", "refactor-reviewer", "count-check")

    def tearDown(self):
        self.tmp.cleanup()

    def install(self, *names):
        for n in names:
            (self.agents / n).mkdir(exist_ok=True)
            (self.agents / n / "agent.md").write_text(f"---\nname: {n}\n---\n\n# Agent System Instructions\n\nx\n")

    def binding(self, **fields):
        d = self.perma / "team" / "repo" / "repo"
        d.mkdir(parents=True, exist_ok=True)
        (d / "binding.json").write_text(json.dumps({"owned": True, **fields}))

    def hook(self, *type_names, cwd=None, raw=None, prompt="p"):
        d = {"toolCall": {"name": "invoke_subagent", "args": {"Subagents": [
            {"TypeName": t, "Role": "r", "Prompt": prompt, "Model": "inherit"} for t in type_names]}},
            "workspacePaths": [str(cwd or self.repo)], "conversationId": "c", "stepIdx": 1}
        p = subprocess.run(["python3", str(HOOK)], input=raw if raw is not None else json.dumps(d),
                           capture_output=True, text=True, env=self.env)
        self.assertEqual(p.stderr, "")
        return json.loads(p.stdout)


class TestHook(Fixture):
    def test_role_is_replaced_by_the_agent_that_fills_it(self):
        out = self.hook("role:refactor:engineer", "role:count-check", cwd=self.other)
        self.assertEqual(out["decision"], "allow")
        self.assertEqual([s["TypeName"] for s in out["overwrite"]["Subagents"]], ["refactor-engineer", "count-check"])
        self.assertEqual(out["overwrite"]["Subagents"][0]["Prompt"], "p")

    def test_the_whole_list_is_returned_because_overwrite_is_shallow(self):
        out = self.hook("research", "role:count-check")
        self.assertEqual([s["TypeName"] for s in out["overwrite"]["Subagents"]], ["research", "count-check"])

    def test_binding_override_wins(self):
        self.binding(roles={"engineer": "count-check"})
        self.assertEqual(self.hook("role:engineer")["overwrite"]["Subagents"][0]["TypeName"], "count-check")

    def test_review_role_falls_back_to_a_fresh_default_agent(self):
        (self.agents / "refactor-reviewer" / "agent.md").unlink()
        (self.agents / "refactor-reviewer").rmdir()
        self.assertEqual(self.hook("role:reviewer")["overwrite"]["Subagents"][0]["TypeName"], "self")

    def test_unfilled_role_is_refused_with_a_reason(self):
        out = self.hook("role:tester")
        self.assertEqual(out["decision"], "deny")
        self.assertIn("role 'tester' is unresolved", out["reason"])
        self.assertNotIn("overwrite", out)

    def test_plain_names_are_untouched_without_a_binding(self):
        self.assertEqual(self.hook("refactor-reviewer", "research", cwd=self.other), {"decision": "allow"})

    def test_prompt_append_names_the_bindings_review_folder_once(self):
        self.binding(reviews="docs/reviews")
        (self.perma / "_personal").mkdir()
        (self.perma / "_personal" / "agent-roles.json").write_text(json.dumps({"roles": {"reviewer": {
            "providers": ["refactor-reviewer"], "prompt_append": "Write the record under {reviews}."}}}))
        out = self.hook("role:reviewer")["overwrite"]["Subagents"][0]
        self.assertIn("[agent-roles]\nWrite the record under docs/reviews/.", out["Prompt"])
        again = self.hook("role:reviewer", prompt=out["Prompt"])["overwrite"]["Subagents"][0]
        self.assertEqual(again["Prompt"].count("[agent-roles]"), 1)

    def test_it_always_prints_an_explicit_allow_on_bad_input(self):
        for raw in ("", "not json", "[]", "null", '{"toolCall": null}',
                    '{"toolCall": {"name": "invoke_subagent", "args": {"Subagents": "x"}}}',
                    '{"toolCall": {"name": "invoke_subagent", "args": {"Subagents": [1, {"TypeName": 7}]}}}',
                    '{"toolCall": {"name": "run_command", "args": {}}}'):
            self.assertEqual(self.hook(raw=raw), {"decision": "allow"}, raw)

    def test_it_allows_when_the_shared_rules_cannot_be_loaded(self):
        (self.perma / "runtime" / "agent-roles.json").write_text("{not json")
        self.assertEqual(self.hook("research"), {"decision": "allow"})


class TestInstall(Fixture):
    def setUp(self):
        super().setUp()
        self.src = Path(self.tmp.name) / "src"
        self.src.mkdir()
        (self.src / "checker.md").write_text(
            "---\nname: checker\ndescription: >-\n  Checks one thing,\n  \"twice\".\ntools: Read, Grep, Bash\n"
            "model: sonnet\n---\n\nYou check one thing.\n")

    def run_install(self):
        p = subprocess.run(["python3", str(INSTALL), str(self.src), str(self.agents)],
                           capture_output=True, text=True, env=self.env)
        return p.returncode, p.stdout + p.stderr

    def test_translation(self):
        self.assertEqual(self.run_install()[0], 0)
        text = (self.agents / "checker" / "agent.md").read_text()
        self.assertIn('description: "Checks one thing, \\"twice\\"."', text)
        self.assertIn("tools:\n    - view_file\n    - grep_search\n    - run_command\n    - send_message\n", text)
        self.assertIn("subagent: true\nmodel: flash\n---\n\n# Agent System Instructions\n\nYou check one thing.\n", text)
        self.assertIn("installed-from: ~/permanence/runtime/agents/checker.md ", text.rstrip().split("\n")[-1])

    def test_an_owners_own_agent_is_left_alone(self):
        (self.agents / "checker").mkdir()
        (self.agents / "checker" / "agent.md").write_text("mine\n")
        code, out = self.run_install()
        self.assertEqual(code, 0)
        self.assertIn("ATTENTION", out)
        self.assertEqual((self.agents / "checker" / "agent.md").read_text(), "mine\n")

    def test_cleanup_removes_only_its_own_orphans_and_keeps_added_files(self):
        self.run_install()
        for name, extra in (("gone", False), ("gone2", True)):
            (self.agents / name).mkdir()
            (self.agents / name / "agent.md").write_text(
                (self.agents / "checker" / "agent.md").read_text().replace("agents/checker.md", f"agents/{name}.md"))
            if extra:
                (self.agents / name / "notes.txt").write_text("mine")
        (self.agents / "copy").mkdir()   # a copy of an installed agent under another name is the owner's
        (self.agents / "copy" / "agent.md").write_text((self.agents / "checker" / "agent.md").read_text())
        self.run_install()
        self.assertFalse((self.agents / "gone").exists())
        self.assertEqual(sorted(p.name for p in (self.agents / "gone2").iterdir()), ["notes.txt"])
        self.assertTrue((self.agents / "copy" / "agent.md").exists())
        self.assertTrue((self.agents / "refactor-engineer" / "agent.md").exists())  # never marked: the owner's


if __name__ == "__main__":
    unittest.main()
