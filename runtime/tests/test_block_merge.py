"""runtime/lib/block-merge.sh keeps the Permanence block when the block file's path holds a backslash
(v1.13.1). awk read backslashes in a `-v` value as escapes, so on Windows (D:\\a\\_temp\\...) the second
install run wrote an empty block and dropped both markers. A folder name with backslashes stands in
for the Windows path here. Standard library only; a scratch folder."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

LIB = Path(__file__).resolve().parents[2] / "runtime" / "lib" / "block-merge.sh"


class BackslashPath(unittest.TestCase):
    def test_a_refresh_keeps_the_block_when_its_path_has_backslashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(os.path.realpath(tmp)) / "D:\\a\\_temp"
            folder.mkdir()
            src = folder / "block.md"
            src.write_text("<!-- perma:begin -->\nthe block\n<!-- perma:end -->\n")
            dst = Path(tmp) / "CLAUDE.md"
            dst.write_text("my own text\n")
            for _ in range(2):   # the first run adds the block, the second refreshes it in place
                p = subprocess.run(["bash", "-c", f'. "{LIB}" && _perma_block_merge "$1" "$2"', "_", str(dst), str(src)],
                                   capture_output=True, text=True)
                self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
                self.assertEqual(p.stderr, "")
            self.assertEqual(dst.read_text(), "<!-- perma:begin -->\nthe block\n<!-- perma:end -->\n\nmy own text\n")


if __name__ == "__main__":
    unittest.main()
