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


if __name__ == "__main__":
    unittest.main()
