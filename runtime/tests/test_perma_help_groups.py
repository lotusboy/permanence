"""perma-help.sh's programme-group folder line. Standard library only."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "perma-help.sh"
GROUPS = """# GROUPS

## Groups

| group | target repo | programme folder | task doc |
|---|---|---|---|
| `in-repo` | `/w/repo-a` | `docs/programme/` | `docs/programme/UPDATING.md` |
| `in-stream` | `/w/repo-b` | `/p/s/repo/programme/` | `/p/s/repo/programme/UPDATING.md` |
| `tilde` | `/w/repo-c` | `~/p/programme/` | `~/p/programme/UPDATING.md` |

## Membership

| group | workspace path | role | joined | left |
|---|---|---|---|---|
| `in-repo` | /w/repo-a | `a` | 2026-01-01 | |
"""


class GroupFolder(unittest.TestCase):
    def test_an_absolute_or_home_folder_is_shown_as_is_and_a_relative_one_under_the_target(self):
        with tempfile.TemporaryDirectory() as t:
            (Path(t) / "_meta").mkdir()
            (Path(t) / "_meta" / "GROUPS.md").write_text(GROUPS)
            env = dict(os.environ, PERMA_DIR=t, HOME=t)
            out = subprocess.run(["bash", str(SCRIPT)], capture_output=True, text=True, env=env).stdout
        folders = [l.split("folder:", 1)[1] for l in out.splitlines() if "folder:" in l]
        self.assertEqual(len(folders), 3, out)
        self.assertIn("/w/repo-a/docs/programme/", folders[0])
        self.assertIn("/p/s/repo/programme/", folders[1])
        self.assertNotIn("/w/repo-b", folders[1])
        self.assertIn(f"{t}/p/programme/", folders[2])


if __name__ == "__main__":
    unittest.main()
