"""Tests for .githooks/pre-push, the private-words guard. Standard library only.
Each test builds a scratch clone, a scratch 'public' remote and a scratch word list."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent.parent / ".githooks" / "pre-push"
GIT = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.public, self.backup, self.repo, self.home = t / "public.git", t / "backup.git", t / "repo", t / "home"
        self.words = t / "private-words.txt"
        self.env = dict(os.environ, HOME=str(self.home), PERMA_PRIVATE_WORDS=str(self.words), **GIT)
        for k in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "PERMA_PUSH_PRIVATE_OK"):
            self.env.pop(k, None)
        self.home.mkdir()
        for bare in (self.public, self.backup):
            self.git("init", "-q", "--bare", str(bare), cwd=t)
        self.git("init", "-q", "-b", "main", str(self.repo), cwd=t)
        (self.repo / ".githooks").mkdir()
        (self.repo / ".githooks" / "pre-push").write_text(HOOK.read_text())
        (self.repo / ".githooks" / "pre-push").chmod(0o755)
        (self.repo / "runtime").mkdir()
        (self.repo / "runtime" / ".update-source").write_text(f"{self.public}\n")
        self.git("config", "core.hooksPath", ".githooks")
        self.git("remote", "add", "origin", str(self.public))
        self.git("remote", "add", "backup", str(self.backup))
        self.words.write_text("# customers\nAcme Widgets\n\n\\bzq9\\b\n")
        self.commit("init", {"README.md": "hello\n"})
        self.assertEqual(self.push()[0], 0)

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args, cwd=None, check=True):
        return subprocess.run(["git", *args], cwd=str(cwd or self.repo), capture_output=True, text=True,
                              env=self.env, check=check)

    def commit(self, message, files):
        for path, text in files.items():
            p = self.repo / path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)
        self.git("add", "-A")
        self.git("commit", "-qm", message)

    def push(self, *args, remote="origin", ref="main", env=None):
        p = subprocess.run(["git", "push", "-q", *args, remote, ref], cwd=str(self.repo), capture_output=True,
                           text=True, env=dict(self.env, **(env or {})))
        return p.returncode, p.stdout + p.stderr

    def on_public(self, ref="main"):
        return self.git("--git-dir", str(self.public), "rev-parse", "--verify", "-q", ref, check=False).stdout.strip()

    def head(self):
        return self.git("rev-parse", "HEAD").stdout.strip()


class TestGuard(Fixture):
    def test_a_clean_push_goes_through(self):
        self.commit("add a thing", {"a.txt": "nothing private\n"})
        self.assertEqual(self.push()[0], 0)
        self.assertEqual(self.on_public(), self.head())

    def test_a_private_word_in_an_added_line_stops_the_push(self):
        before = self.on_public()
        self.commit("add notes", {"notes.md": "one\nwe met ACME widgets today\nthree\n"})
        code, out = self.push()
        self.assertEqual(code, 1)
        self.assertIn("STOPPED", out)
        self.assertIn("acme widgets today".lower(), out.lower())
        self.assertEqual(self.on_public(), before)

    def test_in_a_commit_message_a_file_name_and_a_branch_name(self):
        self.commit("for Acme Widgets", {"a.txt": "x\n"})
        self.assertIn("message:", self.push()[1])
        self.git("reset", "-q", "--hard", "HEAD~1")
        self.commit("add a file", {"docs/acme widgets.md": "x\n"})
        self.assertEqual(self.push()[0], 1)
        self.git("reset", "-q", "--hard", "HEAD~1")
        self.commit("fine", {"b.txt": "x\n"})
        self.git("branch", "zq9")
        code, out = self.push(ref="zq9")
        self.assertEqual(code, 1)
        self.assertIn("ref name: refs/heads/zq9", out)

    def test_a_pattern_is_a_regular_expression_and_matches_whole_words_when_told_to(self):
        self.commit("a", {"a.txt": "the code zq9x is not the word\n"})
        self.assertEqual(self.push()[0], 0)
        self.commit("b", {"b.txt": "but zq9 is\n"})
        self.assertEqual(self.push()[0], 1)

    def test_a_removed_line_does_not_stop_a_push(self):
        self.words.write_text("")
        self.commit("slipped in", {"a.txt": "Acme Widgets\nkeep\n"})
        self.assertEqual(self.push()[0], 0)
        self.words.write_text("Acme Widgets\n")
        self.commit("take the word out", {"a.txt": "keep\n"})
        self.assertEqual(self.push()[0], 0)

    def test_every_new_commit_is_read_not_only_the_last(self):
        self.commit("first", {"a.txt": "Acme Widgets\n"})
        self.commit("second", {"b.txt": "clean\n"})
        self.assertEqual(self.push()[0], 1)

    def test_a_new_branch_is_checked_from_where_it_leaves_the_remote(self):
        self.git("checkout", "-q", "-b", "feature")
        self.commit("on a branch", {"c.txt": "Acme Widgets\n"})
        self.assertEqual(self.push(ref="feature")[0], 1)
        self.assertEqual(self.on_public("feature"), "")

    def test_a_push_somewhere_else_is_not_looked_at(self):
        self.commit("private notes", {"notes.md": "Acme Widgets\n"})
        self.assertEqual(self.push(remote="backup")[0], 0)

    def test_no_list_or_an_empty_list_does_nothing(self):
        self.commit("x", {"a.txt": "Acme Widgets\n"})
        self.words.write_text("# only a comment\n\n")
        self.assertEqual(self.push()[0], 0)
        self.commit("y", {"b.txt": "Acme Widgets again\n"})
        self.words.unlink()
        self.assertEqual(self.push()[0], 0)

    def test_the_owner_can_push_once_on_purpose(self):
        self.commit("x", {"a.txt": "Acme Widgets\n"})
        code, out = self.push(env={"PERMA_PUSH_PRIVATE_OK": "1"})
        self.assertEqual(code, 0)
        self.assertIn("pushing anyway", out)
        self.assertEqual(self.on_public(), self.head())

    def test_the_same_repository_written_another_way_still_counts(self):
        (self.repo / "runtime" / ".update-source").write_text("https://Example.com/Owner/Repo.git\n")
        self.git("remote", "set-url", "origin", "git@example.com:owner/repo")
        self.commit("x", {"a.txt": "Acme Widgets\n"})
        p = subprocess.run([str(self.repo / ".githooks" / "pre-push"), "origin", "git@example.com:owner/repo"],
                           cwd=str(self.repo), capture_output=True, text=True, env=self.env,
                           input=f"refs/heads/main {self.head()} refs/heads/main {self.on_public()}\n")
        self.assertEqual(p.returncode, 1, p.stderr)

    def test_a_pattern_grep_cannot_read_stops_the_push_and_says_so(self):
        self.words.write_text("broken[\n")
        self.commit("x", {"a.txt": "clean\n"})
        code, out = self.push()
        self.assertEqual(code, 1)
        self.assertIn("holds a pattern grep cannot read", out)

    def test_deleting_a_remote_branch_is_allowed(self):
        self.git("branch", "old")
        self.assertEqual(self.push(ref="old")[0], 0)
        self.assertEqual(self.push("--delete", ref="old")[0], 0)


if __name__ == "__main__":
    unittest.main()
