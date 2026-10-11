"""Tests for runtime/ops-event.sh, ops-gap.sh and repo-hooks.sh. Standard library only:
python3 -m unittest discover -s runtime/tests"""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

RUNTIME = Path(__file__).resolve().parent.parent
GIT = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name).resolve()
        self.perma = t / "perma"
        (self.perma / "_meta").mkdir(parents=True)
        (self.perma / "runtime").mkdir()
        for s in ("resolve-stream.sh", "ops-event.sh", "ops-gap.sh", "repo-hooks.sh"):
            (self.perma / "runtime" / s).symlink_to(RUNTIME / s)
        self.owned, self.other = t / "owned", t / "other"
        rows = []
        for repo, stream, owned in ((self.owned, "a/owned", True), (self.other, "a/other", False)):
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            self.commit(repo, "first")
            (self.perma / stream / "repo").mkdir(parents=True)
            (self.perma / stream / "repo" / "binding.json").write_text(json.dumps({"owned": owned}))
            rows.append(f"| {repo} | {stream} | test |")
        (self.perma / "_meta" / "REGISTRY.md").write_text("| path | stream | what |\n|---|---|---|\n" + "\n".join(rows) + "\n")
        self.env = dict(os.environ, PERMA_DIR=str(self.perma), **GIT)
        self.env.pop("OPS_REPO", None)
        self.ledger = self.perma / "a/owned/repo/ops/events.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def commit(self, repo, msg):
        subprocess.run(["git", "-C", str(repo), "commit", "-q", "--allow-empty", "-m", msg],
                       check=True, env=dict(os.environ, **GIT), capture_output=True)

    def run_in(self, cwd, script, *args, env=None):
        p = subprocess.run([str(self.perma / "runtime" / script), *args], cwd=cwd, capture_output=True,
                           text=True, env=env or self.env)
        return p.returncode, p.stdout + p.stderr


class OpsEvent(Fixture):
    def test_writes_to_the_streams_ledger_and_stamps_the_repos_head(self):
        sub = self.owned / "deep"
        sub.mkdir()
        rc, out = self.run_in(sub, "ops-event.sh", "decision", "T1", "pick a path", "-", "-", "-", "-", "-", "done", "why")
        self.assertEqual(rc, 0, out)
        (row,) = [json.loads(l) for l in self.ledger.read_text().splitlines()]
        head = subprocess.run(["git", "-C", str(self.owned), "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True).stdout.strip()
        self.assertEqual((row["kind"], row["task"], row["outcome"], row["note"], row["commit"]),
                         ("decision", "T1", "done", "why", head))
        self.assertFalse((self.owned / "docs").exists())

    def test_appends_and_never_rewrites(self):
        self.run_in(self.owned, "ops-event.sh", "note", "-", "one")
        self.run_in(self.owned, "ops-event.sh", "note", "-", "two")
        self.assertEqual([json.loads(l)["purpose"] for l in self.ledger.read_text().splitlines()], ["one", "two"])

    def test_refuses_an_unregistered_repository(self):
        stray = Path(self.tmp.name) / "stray"
        subprocess.run(["git", "init", "-q", str(stray)], check=True)
        rc, out = self.run_in(stray, "ops-event.sh", "note", "-", "x")
        self.assertEqual(rc, 1)
        self.assertIn("no stream is registered", out)


    def test_ops_repo_names_the_repository_when_run_from_outside_it(self):
        """M9: OPS_REPO, not the working directory, picks the repository."""
        rc, out = self.run_in(Path(self.tmp.name), "ops-event.sh", "note", "-", "x",
                              env=dict(self.env, OPS_REPO=str(self.owned)))
        self.assertEqual(rc, 0, out)
        self.assertEqual(len(self.ledger.read_text().splitlines()), 1)

    def test_refuses_a_stream_with_no_repo_folder(self):
        """M10: a registered stream with no repo/ folder keeps no ledger."""
        import shutil
        shutil.rmtree(self.perma / "a/owned/repo")
        rc, out = self.run_in(self.owned, "ops-event.sh", "note", "-", "x")
        self.assertEqual(rc, 1)
        self.assertIn("has no repo/ folder", out)
        self.assertFalse(self.ledger.exists())

    def test_refuses_a_repository_the_owner_does_not_own(self):
        """Another party's repository (owned: false) never gets a ledger, even with a repo/ folder."""
        rc, out = self.run_in(self.other, "ops-event.sh", "note", "-", "x")
        self.assertEqual(rc, 1)
        self.assertIn('does not say "owned": true', out)
        self.assertFalse((self.perma / "a/other/repo/ops").exists())


class OpsGap(Fixture):
    def test_reads_the_streams_ledger(self):
        self.run_in(self.owned, "ops-event.sh", "note", "-", "x", env=dict(self.env, OPS_TS="2000-01-01T00:00:00+00:00"))
        rc, out = self.run_in(self.owned, "ops-gap.sh", "1")
        self.assertEqual(rc, 0, out)
        self.assertIn("ops ledger is 1 commit(s) behind — last event 2000-01-01", out)

    def test_quiet_line_under_the_threshold(self):
        self.run_in(self.owned, "ops-event.sh", "note", "-", "x")
        rc, out = self.run_in(self.owned, "ops-gap.sh")
        self.assertEqual(rc, 0, out)
        self.assertRegex(out, r"^ops ledger: [01] commit\(s\) behind \(last event ")


class RepoHooks(Fixture):
    def hook(self, repo):
        return repo / ".git" / "hooks" / "post-commit"

    def test_writes_the_hook_only_into_an_owned_repository_and_it_reports_after_a_commit(self):
        rc, out = self.run_in(self.owned, "repo-hooks.sh")
        self.assertEqual(rc, 0, out)
        self.assertTrue(os.access(self.hook(self.owned), os.X_OK))
        self.assertFalse(self.hook(self.other).exists())
        self.run_in(self.owned, "ops-event.sh", "note", "-", "x", env=dict(self.env, OPS_TS="2000-01-01T00:00:00+00:00"))
        p = subprocess.run(["git", "-C", str(self.owned), "commit", "--allow-empty", "-m", "second"],
                           capture_output=True, text=True, env=self.env)
        self.assertIn("ops ledger: 2 commit(s) behind", p.stdout + p.stderr)

    def test_never_overwrites_a_hook_it_did_not_write(self):
        self.hook(self.owned).write_text("#!/bin/sh\necho mine\n")
        rc, out = self.run_in(self.owned, "repo-hooks.sh")
        self.assertEqual(rc, 0, out)
        self.assertIn("left alone", out)
        self.assertEqual(self.hook(self.owned).read_text(), "#!/bin/sh\necho mine\n")

    def test_rewrites_its_own_hook(self):
        self.run_in(self.owned, "repo-hooks.sh")
        rc, out = self.run_in(self.owned, "repo-hooks.sh")
        self.assertEqual(rc, 0, out)
        self.assertIn("post-commit written", out)

    def test_skips_a_repository_that_sets_core_hooks_path(self):
        subprocess.run(["git", "-C", str(self.owned), "config", "core.hooksPath", "elsewhere"], check=True)
        rc, out = self.run_in(self.owned, "repo-hooks.sh")
        self.assertEqual(rc, 0, out)
        self.assertIn("core.hooksPath", out)
        self.assertFalse(self.hook(self.owned).exists())

    def test_an_argument_limits_the_run_to_that_repository(self):
        rc, out = self.run_in(self.owned, "repo-hooks.sh", str(self.other))
        self.assertEqual(rc, 0, out)
        self.assertFalse(self.hook(self.owned).exists())

    def test_an_owned_repository_passed_as_argument_gets_the_hook(self):
        """M7: the argument filter keeps a qualifying repository."""
        rc, out = self.run_in(self.owned, "repo-hooks.sh", str(self.owned))
        self.assertEqual(rc, 0, out)
        self.assertTrue(os.access(self.hook(self.owned), os.X_OK))
        self.assertFalse(self.hook(self.other).exists())

    def test_an_argument_not_registered_as_owned_is_reported(self):
        stray = Path(self.tmp.name) / "stray"
        subprocess.run(["git", "init", "-q", str(stray)], check=True)
        for path in (stray, self.other):
            rc, out = self.run_in(self.owned, "repo-hooks.sh", str(path))
            self.assertEqual(rc, 0, out)
            self.assertIn(f"{path} — not registered to a stream whose binding says owned: true", out)

    def test_never_writes_through_a_symlink(self):
        """Its own hook reached through a link is replaced by a plain file; the link's target is untouched."""
        target = Path(self.tmp.name) / "elsewhere-hook"
        target.write_text("#!/bin/sh\n# installed-by: permanence runtime/repo-hooks.sh\nexit 0\n")
        before = target.read_text()
        self.hook(self.owned).symlink_to(target)
        rc, out = self.run_in(self.owned, "repo-hooks.sh")
        self.assertEqual(rc, 0, out)
        self.assertFalse(self.hook(self.owned).is_symlink())
        self.assertIn("ops-gap.sh", self.hook(self.owned).read_text())
        self.assertEqual(target.read_text(), before)

    def test_the_hook_is_harmless_when_permanence_is_absent(self):
        """M12: with the runtime gone, a commit still succeeds and the hook prints nothing."""
        self.run_in(self.owned, "repo-hooks.sh")
        (self.perma / "runtime" / "ops-gap.sh").unlink()
        p = subprocess.run(["git", "-C", str(self.owned), "commit", "--allow-empty", "-m", "third"],
                           capture_output=True, text=True, env=self.env)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertNotIn("ops ledger", p.stdout + p.stderr)
        self.assertEqual(p.stderr, "")


if __name__ == "__main__":
    unittest.main()
