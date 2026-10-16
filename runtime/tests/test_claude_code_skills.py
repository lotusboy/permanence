"""The skills block of runtime/bindings/claude-code/wire, run against a fake HOME and PERMA.

Only that block is run (cut out of the wire between its own heading comment and the next one), so the
test never touches the real ~/.claude or wires anything else.
"""
import os
import pathlib
import subprocess
import tempfile
import unittest

WIRE = pathlib.Path(__file__).resolve().parents[1] / "bindings" / "claude-code" / "wire"
START = "# Skills: the method skills"
END = "# CLAUDE.md: manage ONLY"
MARK = "installed-from: ~/permanence/runtime/skills/"


def skills_block():
    lines = WIRE.read_text().splitlines(keepends=True)
    out, on = [], False
    for line in lines:
        if line.startswith(START):
            on = True
        elif line.startswith(END):
            break
        if on:
            out.append(line)
    assert out, "skills block not found in the wire"
    return "".join(out)


class SkillsInstall(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = pathlib.Path(self.tmp.name)
        self.perma, self.home = root / "perma", root / "home"
        self.src = self.perma / "runtime" / "skills"
        self.dst = self.home / ".claude" / "skills"
        (self.src / "demo").mkdir(parents=True)
        (self.src / "demo" / "SKILL.md").write_text("---\nname: demo\n---\nbody\n")
        (self.src / "demo" / "notes.md").write_text("extra\n")
        self.block = root / "block.sh"
        self.block.write_text(skills_block())

    def tearDown(self):
        self.tmp.cleanup()

    def run_block(self):
        env = dict(os.environ, HOME=str(self.home), PERMA=str(self.perma), SHA="abc123", WIRE_FAILED="0")
        return subprocess.run(["bash", str(self.block)], env=env, capture_output=True, text=True, check=True).stdout

    def test_a_skill_is_installed_whole_with_the_marker(self):
        self.run_block()
        self.assertEqual((self.dst / "demo" / "notes.md").read_text(), "extra\n")
        self.assertIn(MARK + "demo @ abc123", (self.dst / "demo" / "SKILL.md").read_text().splitlines()[-1])

    def test_a_reinstall_with_no_edits_keeps_no_backup(self):
        self.run_block()
        self.run_block()
        self.assertFalse((self.home / ".claude" / "skills-perma-bak").exists()
                         and any((self.home / ".claude" / "skills-perma-bak").iterdir()))

    def test_an_edited_installed_copy_is_kept_outside_the_skills_folder(self):
        self.run_block()
        with open(self.dst / "demo" / "notes.md", "a") as f:
            f.write("user tweak\n")
        out = self.run_block()
        self.assertIn("your edits to the installed copy are kept", out)
        kept = list((self.home / ".claude" / "skills-perma-bak").iterdir())
        self.assertEqual(len(kept), 1)
        self.assertIn("user tweak", (kept[0] / "notes.md").read_text())
        self.assertNotIn("user tweak", (self.dst / "demo" / "notes.md").read_text())
        self.assertEqual(sorted(p.name for p in self.dst.iterdir()), ["demo"])

    def test_an_owners_own_same_named_skill_is_left_alone(self):
        (self.dst / "demo").mkdir(parents=True)
        (self.dst / "demo" / "SKILL.md").write_text("users own\n")
        out = self.run_block()
        self.assertIn("ATTENTION", out)
        self.assertEqual((self.dst / "demo" / "SKILL.md").read_text(), "users own\n")

    def test_a_skill_removed_from_the_source_is_retired_outside_the_skills_folder(self):
        self.run_block()
        (self.src / "demo" / "SKILL.md").rename(self.perma / "gone.md")
        out = self.run_block()
        self.assertIn("no longer in runtime/skills/", out)
        self.assertFalse((self.dst / "demo").exists())
        self.assertEqual(len(list((self.home / ".claude" / "skills-perma-removed").iterdir())), 1)


if __name__ == "__main__":
    unittest.main()
