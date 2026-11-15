"""runtime/pre-compact.sh, the PreCompact hook: one log line per compaction in ~/.claude/compaction-log.txt,
and the summary instructions on stdout (the shipped default, or runtime/.compact-instructions when it has
text, cut to under 10,000 characters). Plain bash: it must work with no jq and no python3 on PATH.
Standard library only. Scratch HOME; PERMA_DIR is a scratch folder."""
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / "runtime" / "pre-compact.sh"
TOOLS = ("bash", "cat", "sed", "head", "tr", "date")   # everything the hook calls, and nothing else


class PreCompact(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.home = self.dir / "home"
        (self.home / ".claude").mkdir(parents=True)
        self.perma = self.dir / "perma"
        (self.perma / "runtime").mkdir(parents=True)
        self.work = self.dir / "work"
        self.work.mkdir()
        # A PATH holding only the tools the hook needs: no jq, no python3.
        self.bin = self.dir / "bin"
        self.bin.mkdir()
        for tool in TOOLS:
            os.symlink(shutil.which(tool), self.bin / tool)
        self.env = {"HOME": str(self.home), "PERMA_DIR": str(self.perma), "PATH": str(self.bin)}
        self.log = self.home / ".claude" / "compaction-log.txt"

    def tearDown(self):
        self.tmp.cleanup()

    def run_hook(self, stdin=None):
        if stdin is None:
            stdin = json.dumps({"session_id": "abc-123", "transcript_path": "/t.jsonl", "cwd": str(self.work),
                                "hook_event_name": "PreCompact", "trigger": "manual",
                                "custom_instructions": None})
        p = subprocess.run([str(self.bin / "bash"), str(HOOK)], input=stdin, capture_output=True,
                           text=True, env=self.env, cwd=self.work)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stderr, "")
        return p.stdout

    def test_no_jq_or_python3_on_the_path(self):
        for absent in ("jq", "python3"):
            self.assertFalse((self.bin / absent).exists())

    def test_the_default_instructions_and_the_log_line(self):
        out = self.run_hook()
        self.assertTrue(out.startswith("Keep: the task in progress and its step status;"), out)
        self.assertIn("not yet written to the\nstream files", out)
        self.assertIn("Work from the stream files, not this summary.", out)
        line = self.log.read_text()
        self.assertRegex(line, r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ  trigger=manual  session=abc-123  cwd=.+\n$")
        self.assertTrue(line.rstrip("\n").endswith(os.path.realpath(self.work)), line)
        self.run_hook(json.dumps({"session_id": "def", "trigger": "auto", "custom_instructions": "a \"trigger\": x"}))
        lines = self.log.read_text().splitlines()
        self.assertEqual(len(lines), 2)
        self.assertIn("trigger=auto  session=def", lines[1])

    def test_the_override_file_is_printed_instead(self):
        (self.perma / "runtime" / ".compact-instructions").write_text("Keep only the open decisions.\n")
        self.assertEqual(self.run_hook(), "Keep only the open decisions.\n")
        (self.perma / "runtime" / ".compact-instructions").write_text("  \n\n")   # no text: the default
        self.assertTrue(self.run_hook().startswith("Keep: the task in progress"))

    def test_a_long_override_is_cut_under_the_docs_limit(self):
        (self.perma / "runtime" / ".compact-instructions").write_text("word " * 5000)
        out = self.run_hook()
        self.assertLess(len(out), 10000)
        self.assertTrue(out.startswith("word word"))

    def test_bad_input_and_no_claude_folder_still_exit_0(self):
        shutil.rmtree(self.home / ".claude")
        for stdin in ("", "not json", "{}"):
            with self.subTest(stdin=stdin):
                self.assertTrue(self.run_hook(stdin).startswith("Keep:"))
        (self.home / ".claude").mkdir()
        self.run_hook("garbage")
        self.assertIn("trigger=unknown  session=unknown", self.log.read_text())

    def test_odd_characters_never_reach_the_log(self):
        self.run_hook(json.dumps({"session_id": "a b;$(x)\\n", "trigger": "auto"}))
        self.assertTrue(re.search(r"session=abxn  cwd=", self.log.read_text()), self.log.read_text())


if __name__ == "__main__":
    unittest.main()
