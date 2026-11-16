"""runtime/.role and the owner's own role file (v1.13.1). The install run warns when a role file of the
owner's own still names a tool that moved to bakehouse in v1.12.0; it never edits the file or fails.
session-start.sh and install.sh read runtime/.role through one function, and a path with a space loads.
Standard library only. A scratch Permanence and a scratch HOME; the real scripts run against them."""
import hashlib
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "runtime"
LIB = RUNTIME / "lib" / "role-file.sh"

STALE = """# My role
Record each choice with decision.sh ask.
Dispatch with `subagent_type: "role:engineer"`.
Your role: project manager.
Use bakehouse:step-back when a chain strains.
Before the gate, run step-back and decision.sh again.
"""


class RoleCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(os.path.realpath(self.tmp.name))
        self.perma = self.base / "permanence"
        (self.perma / "runtime" / "roles").mkdir(parents=True)
        self.home = self.base / "home"
        self.home.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def set_role(self, value):
        (self.perma / "runtime" / ".role").write_text(value)

    def check(self, **env):
        p = subprocess.run(["bash", "-c", f'. "{LIB}" && _perma_role_check'], capture_output=True, text=True,
                           env={"HOME": str(self.home), "PATH": os.environ["PATH"], "PERMA": str(self.perma), **env})
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stderr, "")
        return p.stdout

    def role_file(self, text, folder="roles of mine"):
        path = self.base / folder / "role.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def test_a_role_file_with_no_moved_names_is_silent(self):
        path = self.role_file("Keep the board up to date.\nUse bakehouse:pm for team work.\n")
        self.set_role(f"{path}\n")
        self.assertEqual(self.check(), "")

    def test_moved_names_are_reported_with_their_line_numbers(self):
        path = self.role_file(STALE)
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        self.set_role(f"{path}\n")
        out = self.check()
        self.assertIn("ATTENTION — decision.sh, line(s) 2, 6\n", out)
        self.assertIn("ATTENTION — a role:<name> dispatch, line(s) 3\n", out)
        self.assertIn("ATTENTION — step-back, line(s) 6\n", out)   # line 5 is bakehouse:step-back
        self.assertIn(f"your role file ({path}) still refers to tools that moved to bakehouse", out)
        self.assertIn("`bakehouse:pm` skill, or switch runtime/.role to pm", out)
        self.assertEqual(len(out.splitlines()), 4, out)              # three names and the one line of advice
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), before)   # never edited

    def test_prose_and_the_new_home_do_not_count(self):
        path = self.role_file("Your role: PM.\nrole: none\nCall bakehouse:dev-team.\n")
        self.set_role(f"{path}\n")
        self.assertEqual(self.check(), "")

    def test_innocent_words_do_not_count(self):
        # Each line once reported a moved name (review, 16 Nov): a name counts only as a whole word,
        # and `role:` only as the old dispatch, with a lowercase name right after the colon.
        lines = ["Never suspend.sh the job.", "Run the account-check before billing.",
                 "The YAML key `role:` sets the persona.", "Your role:PM", "role:\r", "myspend.sh-old"]
        path = self.role_file("\n".join(lines) + "\n")
        self.set_role(f"{path}\n")
        self.assertEqual(self.check(), "")

    def test_the_names_v1_12_0_deleted_are_found_in_their_sh_and_py_forms(self):
        lines = ['Use subagent_type: "refactor-engineer".', "python3 ~/permanence/runtime/decision.py ask",
                 "runtime/team-preflight.py first", "Ask the human-expert agent.", "(see `agent-roles.py`)",
                 "Then /perma-health."]
        path = self.role_file("\n".join(lines) + "\n")
        self.set_role(f"{path}\n")
        out = self.check()
        for i, name in enumerate(["refactor-engineer", "decision.py", "team-preflight", "human-expert",
                                  "agent-roles", "perma-health"], start=1):
            self.assertIn(f"ATTENTION — {name}, line(s) {i}\n", out)

    def test_at_most_ten_line_numbers_per_name(self):
        path = self.role_file("spend.sh\n" * 25)
        self.set_role(f"{path}\n")
        self.assertIn("ATTENTION — spend.sh, line(s) 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 and 15 more\n", self.check())

    def test_a_file_over_1_mb_is_not_read(self):
        path = self.role_file("decision.sh\n" + "x" * (1024 * 1024))
        self.set_role(f"{path}\n")
        out = self.check()
        self.assertIn("is over 1 MB, so it was not checked", out)
        self.assertNotIn("ATTENTION", out)

    def test_none_pm_and_no_file_are_silent(self):
        # The shipped role is never checked, even if it named a moved tool.
        (self.perma / "runtime" / "roles" / "pm.md").write_text("decision.sh\n")
        for value in ("none\n", "pm\n", "\n", "  \n"):
            with self.subTest(value=value):
                self.set_role(value)
                self.assertEqual(self.check(), "")
        (self.perma / "runtime" / ".role").unlink()
        self.assertEqual(self.check(), "")

    def test_a_missing_role_file_is_silent(self):
        self.set_role(f"{self.base / 'gone' / 'role.md'}\n")
        self.assertEqual(self.check(), "")

    def test_a_role_path_with_a_space_is_checked(self):
        path = self.role_file("Run spend.sh first.\n", folder="My Roles")
        self.set_role(f"  {path}  \r\n")   # spaces at the ends, and a Windows line end, are trimmed
        self.assertIn("ATTENTION — spend.sh, line(s) 1", self.check())

    def test_a_home_relative_path_and_the_env_override_resolve_as_session_start_does(self):
        path = self.home / "roles" / "role.md"
        path.parent.mkdir()
        path.write_text("Run /perma-change.\n")
        self.set_role("~/roles/role.md\n")
        self.assertIn("ATTENTION — perma-change, line(s) 1", self.check())
        self.assertEqual(self.check(PERMA_ROLE="none"), "")


class SessionStartRole(unittest.TestCase):
    """session-start.sh loads the role file the check reads, including a path with a space."""

    def test_a_role_path_with_a_space_loads(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(os.path.realpath(tmp))
            perma = base / "permanence"
            (perma / "_meta").mkdir(parents=True)
            (perma / "runtime").mkdir()
            os.symlink(RUNTIME / "resolve-stream.sh", perma / "runtime" / "resolve-stream.sh")
            os.symlink(RUNTIME / "lib", perma / "runtime" / "lib")
            (perma / "_meta" / "REGISTRY.md").write_text(
                f"| workspace | stream | note |\n|---|---|---|\n| {perma} | perma-meta | notes |\n")
            role = base / "My Roles" / "role.md"
            role.parent.mkdir()
            role.write_text("# my role\n")
            (perma / "runtime" / ".role").write_text(f"{role}\n")
            p = subprocess.run(["bash", str(RUNTIME / "session-start.sh")], input='{"cwd": "%s"}' % perma,
                               capture_output=True, text=True, cwd=perma,
                               env={"HOME": str(base / "home"), "PATH": os.environ["PATH"], "PERMA_DIR": str(perma)})
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertIn(f"[perma] ROLE: read {role} now", p.stdout)


class SessionStartMissingLib(unittest.TestCase):
    """If runtime/lib/role-file.sh is gone (a hand deletion), session start says so; the role is not lost silently."""

    def run_start(self, role):
        with tempfile.TemporaryDirectory() as tmp:
            perma = Path(os.path.realpath(tmp)) / "permanence"
            (perma / "_meta").mkdir(parents=True)
            (perma / "runtime").mkdir()
            os.symlink(RUNTIME / "resolve-stream.sh", perma / "runtime" / "resolve-stream.sh")
            (perma / "_meta" / "REGISTRY.md").write_text(
                f"| workspace | stream | note |\n|---|---|---|\n| {perma} | perma-meta | notes |\n")
            (perma / "runtime" / ".role").write_text(role)
            p = subprocess.run(["bash", str(RUNTIME / "session-start.sh")], input='{"cwd": "%s"}' % perma,
                               capture_output=True, text=True, cwd=perma,
                               env={"HOME": tmp, "PATH": os.environ["PATH"], "PERMA_DIR": str(perma)})
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertEqual(p.stderr, "")
            return p.stdout

    def test_a_chosen_role_is_reported_as_not_loaded(self):
        out = self.run_start("pm\n")
        self.assertIn("runtime/lib/role-file.sh is missing, so the role in runtime/.role was not loaded", out)
        self.assertNotIn("ROLE: read", out)

    def test_no_role_says_nothing(self):
        self.assertNotIn("role-file.sh is missing", self.run_start("none\n"))


class InstallRun(unittest.TestCase):
    """The real install.sh, in a scratch copy of this checkout, prints the warning and still finishes."""

    def test_install_warns_and_does_not_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(os.path.realpath(tmp))
            perma, home, stubs = base / "permanence", base / "home", base / "bin"
            files = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-co", "--exclude-standard"],
                                   capture_output=True, text=True, check=True).stdout.split("\n")
            for rel in filter(None, files):
                src = ROOT / rel
                if src.is_file() and "__pycache__" not in rel:
                    (perma / rel).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, perma / rel)
            git = ["git", "-C", str(perma), "-c", "user.email=ci@example.com", "-c", "user.name=CI"]
            subprocess.run(["git", "init", "-q", str(perma)], check=True)
            subprocess.run(git + ["add", "-A"], check=True)
            subprocess.run(git + ["commit", "-qm", "scratch"], check=True)
            home.mkdir()
            stubs.mkdir()
            for tool in ("launchctl", "crontab", "schtasks"):   # no real scheduler is touched
                (stubs / tool).write_text("#!/bin/sh\nexit 0\n")
                (stubs / tool).chmod(0o755)
            role = base / "My Roles" / "role.md"
            role.parent.mkdir()
            role.write_text(STALE)
            before = hashlib.sha256(role.read_bytes()).hexdigest()
            (perma / "runtime" / ".role").write_text(f"{role}\n")
            p = subprocess.run(["bash", str(perma / "runtime" / "install.sh")], capture_output=True, text=True,
                               env={"HOME": str(home), "PERMA_DIR": str(perma),
                                    "PATH": f"{stubs}{os.pathsep}{os.environ['PATH']}"})
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertIn("role file: ATTENTION — decision.sh, line(s) 2, 6", p.stdout)
            self.assertIn("still refers to tools that moved to bakehouse", p.stdout)
            self.assertEqual(p.stdout.rstrip().splitlines()[-1], "done.")
            self.assertEqual(hashlib.sha256(role.read_bytes()).hexdigest(), before)


if __name__ == "__main__":
    unittest.main()
