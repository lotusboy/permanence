"""The Claude Code binding's wire on an install upgrading from a version that shipped the project team
(it moved to the bakehouse plugin in v1.12.0): the team's hooks, agents and skills an earlier version
installed are removed after a backup, and nothing of the owner's is touched.
Standard library only. Scratch HOME; PERMA_DIR is this checkout, which wire only reads."""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WIRE = ROOT / "runtime" / "bindings" / "claude-code" / "wire"


class Upgrade(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        self.claude = self.home / ".claude"
        self.claude.mkdir(parents=True)
        self.settings = self.claude / "settings.json"
        self.env = dict(os.environ, HOME=str(self.home), PERMA_DIR=str(ROOT))
        self.env.pop("PERMA_ATTENTION_FILE", None)
        self.roles = f"{ROOT}/runtime/agent-roles.py"

    def tearDown(self):
        self.tmp.cleanup()

    def wire(self):
        p = subprocess.run(["bash", str(WIRE)], capture_output=True, text=True, env=self.env)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        return p.stdout

    @staticmethod
    def commands(data):
        return [(ev, h["command"]) for ev, lst in data["hooks"].items() for e in lst for h in e["hooks"]]

    def test_the_team_hooks_go_and_every_other_hook_stays(self):
        hook = lambda c: {"type": "command", "command": c, "timeout": 10}
        self.settings.write_text(json.dumps({"hooks": {
            "SessionStart": [{"hooks": [hook(f"{ROOT}/runtime/session-start.sh")]},
                             {"hooks": [hook(f"{self.roles} --check-new"), hook("/mine/also-here.sh")]}],
            "PreToolUse": [{"matcher": "Agent", "hooks": [hook(self.roles)]},
                           {"matcher": "Bash", "hooks": [hook("/mine/bash-guard.sh")]}],
            "SubagentStop": [{"hooks": [hook(self.roles)]}]}}))
        out = self.wire()
        got = self.commands(json.loads(self.settings.read_text()))
        self.assertFalse([c for c in got if "agent-roles" in c[1]], got)
        self.assertIn(("SessionStart", "/mine/also-here.sh"), got)
        self.assertIn(("PreToolUse", "/mine/bash-guard.sh"), got)
        self.assertIn(("SessionStart", f"{ROOT}/runtime/session-start.sh"), got)
        self.assertIn(("UserPromptSubmit", f"{ROOT}/runtime/session-load.sh"), got)
        self.assertNotIn("SubagentStop", json.loads(self.settings.read_text())["hooks"])
        backup = self.commands(json.loads((self.claude / "settings.json.perma-bak").read_text()))
        self.assertIn(("SubagentStop", self.roles), backup)
        self.assertIn("earlier team hooks removed", out)

    def test_an_edited_team_hook_that_still_calls_permanences_script_goes_too(self):
        hook = lambda c: {"type": "command", "command": c, "timeout": 10}
        self.settings.write_text(json.dumps({"hooks": {
            "SubagentStop": [{"hooks": [hook(f"python3 {self.roles}")]}],
            "SessionStart": [{"hooks": [hook(f"/usr/bin/env python3 {self.roles} --check-new")]}],
            "PreToolUse": [{"matcher": "Agent", "hooks": [hook("python3 /elsewhere/runtime/agent-roles.py")]}]}}))
        out = self.wire()
        got = self.commands(json.loads(self.settings.read_text()))
        self.assertFalse([c for c in got if self.roles in c[1]], got)
        self.assertIn(("PreToolUse", "python3 /elsewhere/runtime/agent-roles.py"), got)
        self.assertIn(f"removed the earlier team hook SubagentStop: python3 {self.roles}", out)
        self.assertIn(f"removed the earlier team hook SessionStart: /usr/bin/env python3 {self.roles} --check-new", out)
        backup = self.commands(json.loads((self.claude / "settings.json.perma-bak").read_text()))
        self.assertIn(("SubagentStop", f"python3 {self.roles}"), backup)

    def test_a_fresh_install_wires_no_team_hook(self):
        out = self.wire()
        self.assertNotIn("earlier team hooks removed", out)
        self.assertFalse((self.claude / "agents").exists())   # Permanence ships no agents or skills
        self.assertFalse((self.claude / "skills").exists())
        got = self.commands(json.loads(self.settings.read_text()))
        self.assertFalse([c for c in got if "agent-roles" in c[1]], got)
        self.assertIn("hook + permission already present", self.wire())

    def test_earlier_team_agents_and_skills_are_moved_aside_and_the_owners_are_kept(self):
        agents, skills = self.claude / "agents", self.claude / "skills"
        agents.mkdir()
        (agents / "count-check.md").write_text(
            "x\n<!-- installed-from: ~/permanence/runtime/agents/count-check.md @ abc123 — edit -->\n")
        (agents / "my-agent.md").write_text("mine\n")
        (skills / "step-back").mkdir(parents=True)
        (skills / "step-back" / "SKILL.md").write_text(
            "x\n<!-- installed-from: ~/permanence/runtime/skills/step-back @ abc123 — edit -->\n")
        (skills / "my-skill").mkdir()
        (skills / "my-skill" / "SKILL.md").write_text("mine\n")
        (self.claude / "commands").mkdir()
        (self.claude / "commands" / "perma-change.md").write_text(
            "x\n<!-- installed-from: ~/permanence/runtime/commands/perma-change.md @ abc123 — edit -->\n")
        self.wire()
        self.assertFalse((agents / "count-check.md").exists())
        self.assertTrue((agents / "count-check.md.perma-removed").exists())
        self.assertEqual((agents / "my-agent.md").read_text(), "mine\n")
        self.assertFalse((skills / "step-back").exists())
        self.assertEqual(len(list((self.claude / "skills-perma-removed").iterdir())), 1)
        self.assertEqual((skills / "my-skill" / "SKILL.md").read_text(), "mine\n")
        self.assertFalse((self.claude / "commands" / "perma-change.md").exists())
        self.assertTrue((self.claude / "commands" / "perma-change.md.perma-removed").exists())
        for never in ("perma-refactor.md", "perma-health.md"):
            self.assertFalse((self.claude / "commands" / never).exists())


if __name__ == "__main__":
    unittest.main()
