"""runtime/list-streams.sh is the one list of streams (v1.13.3, finding F20): a folder is a stream exactly
when it has a PROJECT.md, at any depth; perma-meta is listed first and `_meta` never under its own name;
hidden folders are not searched; a registry row does not make a stream. perma-help, generate-contents
and the brief, list, consolidate and orchestrate commands all read it.
Standard library only. A scratch Permanence; the real scripts run against it through PERMA_DIR."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "runtime"


class OneList(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(os.path.realpath(self.tmp.name))
        self.perma = base / "permanence"
        self.home = base / "home"
        self.home.mkdir()
        for folder in ("_meta", "acme/shop", "acme/shop/archive", "solo", "with space/notes",
                       ".consolidation/snap", "acme/.hidden"):
            (self.perma / folder).mkdir(parents=True, exist_ok=True)
            (self.perma / folder / "PROJECT.md").write_text("# p\n")
        (self.perma / "notes-only" ).mkdir()          # a folder with notes but no PROJECT.md: not a stream
        (self.perma / "notes-only" / "LOG.md").write_text("# log\n")
        work = base / "work"
        for ws in ("shop", "old", "old2", "bad", "linked"):
            (work / ws).mkdir(parents=True)
        (base / "elsewhere" / "real").mkdir(parents=True)
        (base / "elsewhere" / "real" / "PROJECT.md").write_text("# p\n")
        os.symlink(base / "elsewhere" / "real", self.perma / "acme" / "linked")   # not followed
        (self.perma / "dirpm" / "PROJECT.md").mkdir(parents=True)                 # a folder, not a file
        (self.perma / "_meta" / "REGISTRY.md").write_text(
            "| workspace | stream | note |\n|---|---|---|\n"
            f"| {self.perma} | perma-meta | notes |\n"
            f"| {work}/shop/ | acme/shop/ | has a PROJECT.md; trailing slashes |\n"
            f"| {work}/old | registered/only | no PROJECT.md |\n"
            f"| {work}/old2 | registered/only | a second row for the same stream |\n"
            f"| {work}/linked | acme/linked | reached only through a symlink |\n"
            "| /Users/you/path/to/a-project | home/a-project | example row — replace with your own |\n"
            f"{work}/bad | not/a/row | no leading bar, so not a row |\n")
        os.symlink(RUNTIME, self.perma / "runtime")
        self.env = {"HOME": str(self.home), "PATH": os.environ["PATH"], "PERMA_DIR": str(self.perma)}

    def tearDown(self):
        self.tmp.cleanup()

    def run_list(self, *args):
        p = subprocess.run(["bash", str(RUNTIME / "list-streams.sh"), *args], capture_output=True, text=True,
                           env=self.env)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stderr, "")
        return p.stdout

    def test_the_list(self):
        self.assertEqual(self.run_list(), "perma-meta\t_meta\n"
                                          "acme/shop\tacme/shop\n"
                                          "acme/shop/archive\tacme/shop/archive\n"
                                          "solo\tsolo\n"
                                          "with space/notes\twith space/notes\n")

    def test_the_count_leaves_out_perma_meta(self):
        self.assertEqual(self.run_list("--count"), "4\n")

    def test_check_names_registry_rows_with_no_project_md_once(self):
        # Not the example row (its workspace is not on this machine); the symlinked stream is not in
        # the list, so --check names it too: the check and the list always agree.
        self.assertEqual(self.run_list("--check"), "acme/linked\nregistered/only\n")

    def test_the_shipped_registry_gives_no_warning(self):
        (self.perma / "_meta" / "REGISTRY.md").write_text((ROOT / "_meta" / "REGISTRY.md").read_text())
        self.assertEqual(self.run_list("--check"), "")

    def test_no_permanence_folder_prints_nothing(self):
        self.env["PERMA_DIR"] = str(self.home / "missing")
        for args in ((), ("--count",), ("--check",)):
            self.assertEqual(self.run_list(*args), "")

    def test_perma_help_counts_from_the_list_and_warns(self):
        p = subprocess.run(["bash", str(RUNTIME / "perma-help.sh")], capture_output=True, text=True, env=self.env)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("4 streams (plus perma-meta)", p.stdout)
        self.assertIn("registered/only is registered but has no PROJECT.md", p.stdout)
        self.assertIn("Check the stream name in _meta/REGISTRY.md, or add", p.stdout)
        self.assertEqual(p.stdout.count("is registered but has no PROJECT.md"), 2)

    def test_generate_contents_indexes_every_listed_stream_and_nothing_hidden(self):
        p = subprocess.run(["bash", str(RUNTIME / "generate-contents.sh"), "--quiet"], capture_output=True,
                           text=True, env=self.env)
        self.assertEqual(p.returncode, 0, p.stderr)
        for folder in ("_meta", "acme/shop", "acme/shop/archive", "solo", "with space/notes"):
            self.assertTrue((self.perma / folder / "CONTENTS.md").is_file(), folder)
        for folder in (".consolidation/snap", "acme/.hidden", "notes-only", "dirpm"):
            self.assertFalse((self.perma / folder / "CONTENTS.md").exists(), folder)


class CommandsReadTheOneList(unittest.TestCase):
    def test_the_nightly_consolidate_may_run_the_list(self):
        # It runs /perma-consolidate headless with a fixed allow-list; nobody is there to approve a prompt.
        text = (RUNTIME / "nightly-consolidate.sh").read_text()
        for spelling in ("$PERMA", "$HOME/permanence", "~/permanence"):
            self.assertIn(f'"Bash({spelling}/runtime/list-streams.sh:*)"', text)

    def test_each_command_that_needs_every_stream_runs_the_script(self):
        for name in ("perma-brief", "perma-list", "perma-consolidate", "perma-orchestrate"):
            text = (RUNTIME / "commands" / f"{name}.md").read_text()
            with self.subTest(command=name):
                self.assertIn("runtime/list-streams.sh", text)
                self.assertNotIn("<customer>/<project>", text)
                self.assertNotIn("directory containing a `PROJECT.md`", text)
                self.assertNotIn("PROJECT.md-bearing", text)


if __name__ == "__main__":
    unittest.main()
