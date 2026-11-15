"""A session's launch folder is its identity. A session launched in a project that cd's into its own
notes folder under ~/permanence (which matches the perma-meta row) keeps its project's stream, in
session-start.sh and in the two event listeners. A session launched in a perma-meta folder stays
perma-meta wherever it goes. The fallback for an unregistered cwd still works.
Standard library only. A scratch Permanence; the real scripts run against it through PERMA_DIR."""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "runtime"


class LaunchFolder(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(os.path.realpath(self.tmp.name))
        self.perma = base / "permanence"
        self.notes = self.perma / "work" / "bakehouse"   # the stream's own folder
        self.notes.mkdir(parents=True)
        (self.perma / "_meta").mkdir()
        (self.perma / "runtime").mkdir()
        os.symlink(RUNTIME / "resolve-stream.sh", self.perma / "runtime" / "resolve-stream.sh")
        self.project = base / "workspaces" / "bakehouse"
        self.project.mkdir(parents=True)
        self.elsewhere = base / "scratch"
        self.elsewhere.mkdir()
        (self.perma / "_meta" / "REGISTRY.md").write_text(
            "| workspace | stream | note |\n|---|---|---|\n"
            f"| {self.perma} | perma-meta | the notes themselves |\n"
            f"| {self.project} | work/bakehouse | a project |\n")
        self.env = {"HOME": str(base / "home"), "PATH": os.environ["PATH"], "PERMA_DIR": str(self.perma)}

    def tearDown(self):
        self.tmp.cleanup()

    def start(self, cwd, project=None):
        env = dict(self.env, **({"CLAUDE_PROJECT_DIR": str(project)} if project else {}))
        p = subprocess.run(["bash", str(RUNTIME / "session-start.sh")], input=json.dumps({"cwd": str(cwd)}),
                           capture_output=True, text=True, env=env, cwd=cwd)
        self.assertEqual(p.returncode, 0, p.stderr)
        return p.stdout

    def test_a_project_session_in_its_notes_folder_keeps_its_stream(self):
        out = self.start(self.notes, project=self.project)
        self.assertIn("Registered stream for this workspace: work/bakehouse", out)
        self.assertIn(f"The working folder ({self.notes}) is a perma-meta folder; resolved from the project "
                      f"folder ({self.project}) instead.", out)
        self.assertNotIn("Perma-meta context", out)

    def test_a_session_launched_in_permanence_stays_perma_meta(self):
        for cwd in (self.perma, self.notes):
            with self.subTest(cwd=cwd):
                out = self.start(cwd, project=self.perma)
                self.assertIn("Perma-meta context", out)
                self.assertNotIn("work/bakehouse", out)

    def test_the_unregistered_cwd_fallback_still_works(self):
        out = self.start(self.elsewhere, project=self.project)
        self.assertIn("Registered stream for this workspace: work/bakehouse", out)
        self.assertIn("is not registered; resolved from the project folder", out)

    def test_without_a_project_folder_nothing_changes(self):
        self.assertIn("Perma-meta context", self.start(self.notes))
        self.assertIn("Registered stream for this workspace: work/bakehouse", self.start(self.project))
        self.assertIn("is NOT registered", self.start(self.elsewhere))

    def test_an_unregistered_project_folder_leaves_perma_meta(self):
        self.assertIn("Perma-meta context", self.start(self.notes, project=self.elsewhere))

    def test_a_symlinked_project_folder_is_resolved_to_its_physical_path(self):
        # A home folder reached through a symlink: the registry holds the physical path.
        link = self.project.parent.parent / "linked-home"
        os.symlink(self.project.parent.parent, link)
        linked_project = link / "workspaces" / "bakehouse"
        out = self.start(self.notes, project=linked_project)
        self.assertIn("Registered stream for this workspace: work/bakehouse", out)
        self.assertIn(f"resolved from the project folder ({linked_project}) instead.", out)
        self.assertIn("Registered stream for this workspace: work/bakehouse",
                      self.start(self.elsewhere, project=linked_project))
        outbox = self.perma / "_meta" / "events.jsonl"
        outbox.write_text(json.dumps({"id": "1", "ts": "t", "source": "home/other",
                                      "target": "work/bakehouse", "message": "hello"}) + "\n")
        for script in ("events-listen.sh", "stop-listen.sh"):
            with self.subTest(script=script):
                for f in (self.perma / "_meta" / ".events-seen").glob("*"):
                    f.unlink()
                self.assertIn("hello", self.listen(script, project=linked_project))

    def listen(self, script, project=None):
        env = dict(self.env, CLAUDE_CWD=str(self.notes), **({"CLAUDE_PROJECT_DIR": str(project)} if project else {}))
        p = subprocess.run(["bash", str(RUNTIME / script)], input=json.dumps({"cwd": str(self.notes)}),
                           capture_output=True, text=True, env=env, cwd=self.notes)
        self.assertEqual(p.returncode, 0, p.stderr)
        return p.stdout

    def test_the_event_listeners_deliver_to_the_launch_folders_stream(self):
        outbox = self.perma / "_meta" / "events.jsonl"
        event = {"id": "1", "ts": "t", "source": "home/other", "target": "work/bakehouse", "message": "hello"}
        for script in ("events-listen.sh", "stop-listen.sh"):
            with self.subTest(script=script):
                outbox.write_text(json.dumps(event) + "\n")
                seen = self.perma / "_meta" / ".events-seen"
                for f in seen.glob("*") if seen.exists() else []:
                    f.unlink()
                self.assertEqual(self.listen(script), "")                   # no project folder: perma-meta
                self.assertIn("hello", self.listen(script, project=self.project))
                self.assertEqual(self.listen(script, project=self.perma), "")


if __name__ == "__main__":
    unittest.main()
