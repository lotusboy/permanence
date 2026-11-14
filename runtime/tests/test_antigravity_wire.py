"""Tests for the Antigravity binding's wire: Permanence's own wiring stays, and the project team's
pieces an earlier version installed are removed (the team moved to the bakehouse plugin in v1.12.0).
Standard library only. Scratch HOME throughout; PERMA_DIR is this checkout, which wire only reads."""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WIRE = ROOT / "runtime" / "bindings" / "antigravity" / "wire"
MARK = "installed-from: ~/permanence/runtime/agents/"


class Wire(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        self.config = self.home / ".gemini" / "config"
        self.agents, self.skills = self.config / "agents", self.config / "skills"
        self.hooks = self.config / "hooks.json"
        self.home.mkdir()
        self.env = dict(os.environ, HOME=str(self.home), PERMA_DIR=str(ROOT))
        self.env.pop("PERMA_ATTENTION_FILE", None)

    def tearDown(self):
        self.tmp.cleanup()

    def wire(self):
        p = subprocess.run(["bash", str(WIRE)], capture_output=True, text=True, env=self.env)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        return p.stdout

    def agent(self, name, last_line, extra=False):
        (self.agents / name).mkdir(parents=True)
        (self.agents / name / "agent.md").write_text(f"---\nname: {name}\n---\n\nx\n{last_line}\n")
        if extra:
            (self.agents / name / "notes.txt").write_text("mine")

    def test_a_fresh_wire_installs_permanences_own_pieces_and_no_team(self):
        self.wire()
        data = json.loads(self.hooks.read_text())
        self.assertIn("PreInvocation", data["perma-pre-invocation"])
        self.assertIn("PreToolUse", data["perma-pre-tool-use"])
        self.assertNotIn("perma-agent-roles", data)
        self.assertIn("perma:begin", (self.home / ".gemini" / "GEMINI.md").read_text())
        self.assertTrue((self.skills / "perma-startup" / "SKILL.md").exists())
        for skill in self.skills.iterdir():
            self.assertNotIn("Running this on Antigravity", (skill / "SKILL.md").read_text(), skill.name)
        self.assertFalse(self.agents.exists())

    def test_an_upgrade_removes_only_the_team_pieces_an_earlier_version_installed(self):
        self.config.mkdir(parents=True)
        self.hooks.write_text(json.dumps({
            "perma-agent-roles": {"PreToolUse": [{"matcher": "invoke_subagent", "hooks": [
                {"type": "command", "command": "python3 /old/agent-roles-hook.py", "timeout": 10}]}]},
            "another-tool": {"PreToolUse": []}}))
        self.agent("gone", f"<!-- {MARK}gone.md — edit the source -->")
        self.agent("gone2", f"<!-- {MARK}gone2.md — edit the source -->", extra=True)
        self.agent("copy", f"<!-- {MARK}gone.md — edit the source -->")   # a copy under another name is the owner's
        self.agent("mine", "no marker")
        (self.skills / "perma-change").mkdir(parents=True)
        (self.skills / "perma-change" / "SKILL.md").write_text(
            "x\n<!-- installed-from: ~/permanence/runtime/commands/perma-change.md -->\n")
        out = self.wire()
        data = json.loads(self.hooks.read_text())
        self.assertNotIn("perma-agent-roles", data)
        self.assertIn("another-tool", data)
        self.assertIn("perma-agent-roles", json.loads(Path(str(self.hooks) + ".perma-bak").read_text()))
        self.assertIn("earlier agent-roles hook removed", out)
        self.assertFalse((self.agents / "gone").exists())
        self.assertEqual(sorted(p.name for p in (self.agents / "gone2").iterdir()), ["notes.txt"])
        self.assertTrue((self.agents / "copy" / "agent.md").exists())
        self.assertTrue((self.agents / "mine" / "agent.md").exists())
        self.assertFalse((self.skills / "perma-change").exists())

    def test_a_second_wire_changes_nothing(self):
        self.wire()
        before = self.hooks.read_text()
        self.assertIn("hooks already present", self.wire())
        self.assertEqual(self.hooks.read_text(), before)


if __name__ == "__main__":
    unittest.main()
