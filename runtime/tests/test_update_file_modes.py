"""update.sh --apply gives each file it delivers the executable bit the release itself gives it (v1.13.1).
Before, a name pattern made a sourced library under runtime/lib/ executable in the owner's repo, and
every later release that changed it was held back as "customized locally".
Standard library only. A scratch template and a scratch install, both copies of this checkout."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), "-c", "user.email=ci@example.com", "-c", "user.name=CI",
                           *args], capture_output=True, text=True, check=True).stdout


class UpgradeFileModes(unittest.TestCase):
    def test_modes_match_the_release_after_apply_and_a_later_change_is_delivered(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(os.path.realpath(tmp))
            src, inst, home, stubs = base / "src", base / "install", base / "home", base / "bin"
            files = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-co", "--exclude-standard"],
                                   capture_output=True, text=True, check=True).stdout.split("\n")
            for rel in filter(None, files):
                f = ROOT / rel
                if f.is_file() and "__pycache__" not in rel:
                    (src / rel).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(f, src / rel)
            subprocess.run(["git", "init", "-q", "-b", "main", str(src)], check=True)
            (src / "_meta" / "VERSION").write_text("v97.0.0")
            git(src, "add", "-A")
            git(src, "commit", "-qm", "v97.0.0")
            git(src, "tag", "v97.0.0")
            # The next release adds a sourced library (100644) and a script (100755) to runtime/.
            (src / "runtime" / "lib" / "added-lib.sh").write_text("# sourced\n")
            os.chmod(src / "runtime" / "lib" / "added-lib.sh", 0o644)
            (src / "runtime" / "added-tool.sh").write_text("#!/bin/bash\n")
            os.chmod(src / "runtime" / "added-tool.sh", 0o755)
            (src / "_meta" / "VERSION").write_text("v97.0.1")
            git(src, "add", "-A")
            git(src, "commit", "-qm", "v97.0.1")
            git(src, "tag", "v97.0.1")

            subprocess.run(["git", "-c", "advice.detachedHead=false", "clone", "-q", "--branch", "v97.0.0", str(src), str(inst)], check=True)
            git(inst, "checkout", "-q", "-B", "main")
            git(inst, "config", "user.email", "ci@example.com")   # as CI does: update.sh commits the upgrade
            git(inst, "config", "user.name", "CI")
            home.mkdir()
            stubs.mkdir()
            for tool in ("launchctl", "crontab", "schtasks"):   # no real scheduler is touched
                (stubs / tool).write_text("#!/bin/sh\nexit 0\n")
                (stubs / tool).chmod(0o755)
            env = {"HOME": str(home), "PERMA_DIR": str(inst), "PERMA_UPDATE_SOURCE": str(src),
                   "PATH": f"{stubs}{os.pathsep}{os.environ['PATH']}"}

            def apply():
                p = subprocess.run(["bash", str(inst / "runtime" / "update.sh"), "--apply"],
                                   capture_output=True, text=True, env=env)
                self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
                return p.stdout

            apply()
            modes = {line.split("\t")[1]: line.split()[0] for line in
                     git(inst, "ls-files", "-s", "runtime/lib/added-lib.sh", "runtime/added-tool.sh").splitlines()}
            self.assertEqual(modes, {"runtime/lib/added-lib.sh": "100644", "runtime/added-tool.sh": "100755"})
            self.assertEqual(git(inst, "diff", "HEAD", "v97.0.1", "--", "runtime"), "")

            # A later release that changes the library is delivered, not held back as customized.
            (src / "runtime" / "lib" / "added-lib.sh").write_text("# sourced, changed\n")
            (src / "_meta" / "VERSION").write_text("v97.0.2")
            git(src, "commit", "-qam", "v97.0.2")
            git(src, "tag", "v97.0.2")
            out = apply()
            self.assertNotIn("customized locally", out)
            self.assertEqual((inst / "runtime" / "lib" / "added-lib.sh").read_text(), "# sourced, changed\n")
            self.assertEqual((inst / "_meta" / "VERSION").read_text().strip(), "v97.0.2")


class UpgradeFromRealReleases(unittest.TestCase):
    """The real v1.13.0 and v1.13.1 trees, upgraded to this checkout, all the way to the end (v1.13.2).
    v1.13.0's update.sh runs the first pass and still marks runtime/lib/*.sh executable; this
    checkout's update.sh must not hold those files back for it."""

    def setUp(self):
        for tag in ("v1.13.0", "v1.13.1"):
            if subprocess.run(["git", "-C", str(ROOT), "rev-parse", "-q", "--verify", f"refs/tags/{tag}"],
                              capture_output=True).returncode != 0:
                if os.environ.get("CI"):
                    self.fail(f"tag {tag} is missing: CI must fetch tags (fetch-depth: 0)")
                self.skipTest(f"tag {tag} is not in this clone")
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(os.path.realpath(self.tmp.name))
        self.src, self.inst = self.base / "src", self.base / "install"
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.src)], check=True)

    def tearDown(self):
        self.tmp.cleanup()

    def release(self, version, tag=None):
        """Make the template's next release: the tree of <tag>, or of this checkout when tag is None."""
        for child in self.src.iterdir():
            if child.name != ".git":
                shutil.rmtree(child) if child.is_dir() else child.unlink()
        if tag:
            archive = subprocess.run(["git", "-C", str(ROOT), "archive", tag], capture_output=True, check=True).stdout
            subprocess.run(["tar", "-x", "-C", str(self.src)], input=archive, check=True)
        else:
            files = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-co", "--exclude-standard"],
                                   capture_output=True, text=True, check=True).stdout.split("\n")
            for rel in filter(None, files):
                f = ROOT / rel
                if f.is_file() and "__pycache__" not in rel:
                    (self.src / rel).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(f, self.src / rel)
        (self.src / "_meta" / "VERSION").write_text(version)
        git(self.src, "add", "-A")
        git(self.src, "commit", "-qm", version)
        git(self.src, "tag", version)

    def install_at(self, version):
        subprocess.run(["git", "-c", "advice.detachedHead=false", "clone", "-q", "--branch", version,
                        str(self.src), str(self.inst)], check=True)
        git(self.inst, "checkout", "-q", "-B", "main")
        git(self.inst, "config", "user.email", "ci@example.com")
        git(self.inst, "config", "user.name", "CI")
        home, stubs = self.base / "home", self.base / "bin"
        home.mkdir()
        stubs.mkdir()
        for tool in ("launchctl", "crontab", "schtasks"):   # no real scheduler is touched
            (stubs / tool).write_text("#!/bin/sh\nexit 0\n")
            (stubs / tool).chmod(0o755)
        self.env = {"HOME": str(home), "PERMA_DIR": str(self.inst), "PERMA_UPDATE_SOURCE": str(self.src),
                    "PATH": f"{stubs}{os.pathsep}{os.environ['PATH']}"}

    def apply(self):
        p = subprocess.run(["bash", str(self.inst / "runtime" / "update.sh"), "--apply"],
                           capture_output=True, text=True, env=self.env)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        return p.stdout

    def assert_finished_at(self, version, out):
        self.assertNotIn("left for review", out)
        self.assertEqual((self.inst / "_meta" / "VERSION").read_text().strip(), version)
        self.assertEqual(git(self.inst, "diff", "HEAD", version, "--", "runtime", ".githooks"), "")

    def test_an_install_on_v1_13_0_upgrades_to_this_release_in_one_apply(self):
        self.release("v97.0.0", "v1.13.0")
        self.install_at("v97.0.0")
        self.release("v97.0.1")
        self.assert_finished_at("v97.0.1", self.apply())

    def test_the_changelog_rescue_for_an_install_left_stuck_by_v1_13_1(self):
        # Such an install still records v1.13.0 and runs v1.13.1's update.sh, so this release cannot
        # rescue it by itself. The CHANGELOG's commands do, and the next upgrade then finishes.
        self.release("v97.0.0", "v1.13.0")
        self.install_at("v97.0.0")
        self.release("v97.0.1", "v1.13.1")
        stuck = self.apply()
        self.assertIn("left for review", stuck)            # the v1.13.1 defect, reproduced
        self.assertEqual(git(self.inst, "diff", "HEAD", "v97.0.1", "--", "runtime", ".githooks").count("old mode"), 2)
        for f in ("block-merge.sh", "role-file.sh"):
            os.chmod(self.inst / "runtime" / "lib" / f, 0o644)
        (self.inst / "_meta" / "VERSION").write_text("v97.0.1")
        (self.inst / "_meta" / "REGISTRY.md").write_text("an owner's staged edit\n")   # must stay out
        git(self.inst, "add", "_meta/REGISTRY.md")
        rescued = ["runtime/lib/block-merge.sh", "runtime/lib/role-file.sh", "_meta/VERSION"]
        git(self.inst, "add", *rescued)
        git(self.inst, "commit", "-qm", "runtime/lib modes back to the template's; version v1.13.1", "--", *rescued)
        self.assertEqual(sorted(git(self.inst, "show", "--name-only", "--format=", "HEAD").split()), sorted(rescued))
        git(self.inst, "reset", "-q", "--hard")   # the owner's edit is theirs; drop it before the upgrade
        self.release("v97.0.2")
        self.assert_finished_at("v97.0.2", self.apply())


if __name__ == "__main__":
    unittest.main()
