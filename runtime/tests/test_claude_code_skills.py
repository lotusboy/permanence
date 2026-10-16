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
        # TMPDIR points inside the test folder; the block must not need it (review 2026-10-16, L2).
        env = dict(os.environ, HOME=str(self.home), PERMA=str(self.perma), SHA="abc123", WIRE_FAILED="0",
                   TMPDIR=str(pathlib.Path(self.tmp.name) / "no-such-tmp"))
        return subprocess.run(["bash", str(self.block)], env=env, capture_output=True, text=True, check=True).stdout

    def kept(self):
        """Kept copies: each in a folder of its own under skills-perma-bak (the .installed prints are not copies)."""
        bak = self.home / ".claude" / "skills-perma-bak"
        return sorted(p for p in bak.iterdir() if p.name != ".installed") if bak.exists() else []

    def test_a_skill_is_installed_whole_with_the_marker(self):
        self.run_block()
        self.assertEqual((self.dst / "demo" / "notes.md").read_text(), "extra\n")
        self.assertIn(MARK + "demo @ abc123", (self.dst / "demo" / "SKILL.md").read_text().splitlines()[-1])

    def test_a_reinstall_with_no_edits_keeps_no_backup(self):
        self.run_block()
        self.run_block()
        self.assertEqual(self.kept(), [])

    def test_an_edited_installed_copy_is_kept_outside_the_skills_folder(self):
        self.run_block()
        with open(self.dst / "demo" / "notes.md", "a") as f:
            f.write("user tweak\n")
        out = self.run_block()
        self.assertIn("your edits to the installed copy are kept", out)
        kept = self.kept()
        self.assertEqual(len(kept), 1)
        self.assertIn("user tweak", (kept[0] / "demo" / "notes.md").read_text())
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


    def test_an_untouched_copy_is_not_called_edited_when_the_source_changes(self):
        self.run_block()
        (self.src / "demo" / "SKILL.md").write_text("---\nname: demo\n---\nbody, revised upstream\n")
        out = self.run_block()
        self.assertNotIn("your edits", out)
        self.assertEqual(self.kept(), [])
        self.assertIn("revised upstream", (self.dst / "demo" / "SKILL.md").read_text())

    def test_an_edit_to_a_nested_skill_file_is_kept(self):
        (self.src / "demo" / "ref").mkdir()
        (self.src / "demo" / "ref" / "SKILL.md").write_text("nested\n")
        self.run_block()
        with open(self.dst / "demo" / "ref" / "SKILL.md", "a") as f:
            f.write("user tweak\n")
        self.assertIn("your edits", self.run_block())
        self.assertIn("user tweak", (self.kept()[0] / "demo" / "ref" / "SKILL.md").read_text())

    def test_two_edited_reinstalls_in_one_second_both_keep_their_copy(self):
        self.run_block()
        for n in (1, 2):
            with open(self.dst / "demo" / "notes.md", "a") as f:
                f.write(f"edit {n}\n")
            self.run_block()
        self.assertEqual(len(self.kept()), 2)
        self.assertFalse((self.dst / "demo" / "demo").exists())
        self.assertFalse(any(self.dst.rglob("demo/*/SKILL.md")), "a nested copy inside the skills folder")

    def test_when_the_edited_copy_cannot_be_set_aside_nothing_is_replaced(self):
        self.run_block()
        with open(self.dst / "demo" / "notes.md", "a") as f:
            f.write("user tweak\n")
        bak = self.home / ".claude" / "skills-perma-bak"
        for p in sorted(bak.rglob("*"), reverse=True):
            p.unlink() if p.is_file() else p.rmdir()
        bak.rmdir()
        bak.write_text("a file where the folder should be\n")
        out = self.run_block()
        self.assertIn("FAILED to set aside", out)
        self.assertNotIn("are kept", out)
        self.assertIn("user tweak", (self.dst / "demo" / "notes.md").read_text())
        self.assertFalse((self.dst / "demo" / "demo").exists())


if __name__ == "__main__":
    unittest.main()
