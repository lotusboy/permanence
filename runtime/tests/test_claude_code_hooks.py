"""The Claude Code binding's wire and the v1.13.0 hooks: the context meter (UserPromptSubmit) and the
pre-compact hook (PreCompact) are added on a fresh install and on an upgrade from v1.12.0, once each,
with a backup; a user's own hooks are left exactly as they are, and another PreCompact hook is named.
The CLAUDE.md block carries the drift and compact rules.
Standard library only. Scratch HOME; PERMA_DIR is this checkout, which wire only reads."""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WIRE = ROOT / "runtime" / "bindings" / "claude-code" / "wire"


def hook(command):
    return {"type": "command", "command": command, "timeout": 10}


class Hooks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        self.claude = self.home / ".claude"
        self.claude.mkdir(parents=True)
        self.settings = self.claude / "settings.json"
        self.env = dict(os.environ, HOME=str(self.home), PERMA_DIR=str(ROOT))
        self.env.pop("PERMA_ATTENTION_FILE", None)
        self.meter = f"{ROOT}/runtime/context-meter.sh"
        self.pc = f"{ROOT}/runtime/pre-compact.sh"

    def tearDown(self):
        self.tmp.cleanup()

    def wire(self):
        p = subprocess.run(["bash", str(WIRE)], capture_output=True, text=True, env=self.env)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        return p.stdout

    def hooks(self, event, path=None):
        data = json.loads((path or self.settings).read_text())
        return [h["command"] for e in data["hooks"].get(event, []) for h in e["hooks"]]

    def test_a_fresh_install_wires_both_once_and_a_rerun_changes_nothing(self):
        self.wire()
        self.assertEqual(self.hooks("UserPromptSubmit"), [f"{ROOT}/runtime/session-load.sh", self.meter])
        self.assertEqual(self.hooks("PreCompact"), [self.pc])
        before = self.settings.read_text()
        out = self.wire()
        self.assertIn("hook + permission already present", out)
        self.assertEqual(self.settings.read_text(), before)
        self.assertNotIn("another PreCompact hook", out)

    def test_an_upgrade_from_v1_12_0_adds_both_after_a_backup(self):
        v112 = {"permissions": {"additionalDirectories": [str(ROOT)]}, "hooks": {
            "SessionStart": [{"hooks": [hook(f"{ROOT}/runtime/session-start.sh")]}],
            "UserPromptSubmit": [{"hooks": [hook(f"{ROOT}/runtime/session-load.sh")]},
                                 {"hooks": [hook("/mine/paste-check.sh")]}]}}
        self.settings.write_text(json.dumps(v112, indent=2))
        out = self.wire()
        self.assertIn("context-meter + pre-compact hooks", out)
        self.assertEqual(self.hooks("UserPromptSubmit"),
                         [f"{ROOT}/runtime/session-load.sh", "/mine/paste-check.sh", self.meter])
        self.assertEqual(self.hooks("PreCompact"), [self.pc])
        self.assertEqual(json.loads((self.claude / "settings.json.perma-bak").read_text()), v112)

    def test_a_users_own_precompact_hook_is_left_alone_and_named(self):
        own = {"hooks": [dict(hook("/mine/precompact-snapshot.sh"), statusMessage="Logging")]}
        self.settings.write_text(json.dumps({"hooks": {"PreCompact": [own]}}))
        out = self.wire()
        data = json.loads(self.settings.read_text())
        self.assertEqual(data["hooks"]["PreCompact"][0], own)
        self.assertEqual(self.hooks("PreCompact"), ["/mine/precompact-snapshot.sh", self.pc])
        self.assertIn("ATTENTION: another PreCompact hook is also wired, and both run: "
                      "/mine/precompact-snapshot.sh", out)
        self.assertIn("another PreCompact hook", self.wire())   # said again on every run
        self.assertEqual(self.hooks("PreCompact"), ["/mine/precompact-snapshot.sh", self.pc])

    def test_the_claude_md_block_carries_the_two_rules(self):
        self.wire()
        md = (self.claude / "CLAUDE.md").read_text()
        self.assertIn("**Drift count (a tiredness proxy).**", md)
        self.assertIn("At 3, say so in one line and switch method", md)
        self.assertIn("At 5, recommend stopping.", md)
        self.assertIn("**Compact routine.**", md)
        self.assertIn("Only the owner can type `/compact`.", md)

    def test_the_other_blocks_get_the_drift_rule_only(self):
        for name in ("agents-md-block.md", "gemini-md-block.md", "devin-agents-md-block.md"):
            with self.subTest(block=name):
                text = (ROOT / "runtime" / name).read_text()
                self.assertIn("**Drift count (a tiredness proxy).**", text)
                self.assertNotIn("/compact", text)


if __name__ == "__main__":
    unittest.main()
