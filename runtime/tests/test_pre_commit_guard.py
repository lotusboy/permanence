"""The people-rule pre-commit hook (.githooks/pre-commit), run in scratch git repositories.

AC-01: a commit adding 4,000+ Markdown lines finishes the hook in under 2 seconds.
AC-02: on the same staged diff, the hook flags the same files, lines and patterns as the per-line loop
it replaced (v1.11.0), which is kept below as the reference, reading the hook's own pattern list.
AC-03: the top-level README.md and the hook's own folder stay exempt; a stream's README.md does not.
Standard library only. The fixture phrases are about things, not people.
"""
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parents[2] / ".githooks" / "pre-commit"

# The v1.11.0 loop, verbatim apart from its comments, fed the hook's own patterns=( ... ) block.
REFERENCE_LOOP = r'''
file=""
flagged=0
while IFS= read -r line; do
  case "$line" in
    '+++ b/'*) file="${line#+++ b/}" ;;
    '+++ "b/'*) file="${line#+++ \"b/}"; file="${file%\"}" ;;
    '+++ '*) file="" ;;
    '+'*)
      [ -z "$file" ] && continue
      case "$file" in
        README.md|.githooks/*) continue ;;
      esac
      content="${line#+}"
      for p in "${patterns[@]}"; do
        if printf '%s' "$content" | grep -qiE "$p"; then
          if [ "$flagged" -eq 0 ]; then
            printf '\n⚠️  Permanence people-rule guard — staged phrasing to review:\n\n' >&2
          fi
          printf '  %s\n    %s\n    ↳ matched: %s\n\n' "$file" "$content" "$p" >&2
          flagged=1
          break
        fi
      done
      ;;
  esac
done < <(git diff --cached --unified=0 --no-color -- '*.md')
[ "$flagged" -eq 1 ] && exit 1
exit 0
'''

FLAGGED = [
    "This old laptop is too old to run the new build.",
    "The parser is a real clown about dates.",
    "A personality flaw in the config loader.",
    "The cache is never going to change on its own.",
    "The module, which is just a toy, is such a liar about sizes.",
    "Its personality flaw: the board is too old to boot.",   # two patterns: the first in the list is named
]
PLAIN = [
    "A race condition in the retry loop.",
    "Public Liability cover renews in May.",
    "The service is idempotent by nature.",
    "Line with a 100% sign and a \\backslash and `code`.",
    "",
]


def patterns_block():
    text = HOOK.read_text()
    start = text.index("patterns=(")
    end = text.index("\n)\n", start) + 3
    return text[start:end]


class Guard(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "repo"
        self.repo.mkdir()
        self.env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", HOME=self.tmp.name,
                        GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="ci@example.com")
        self.git("init", "-q")
        (self.repo / "start.md").write_text("start\n")
        self.git("add", "-A")
        self.git("-c", "user.name=t", "-c", "user.email=ci@example.com", "commit", "-q", "-m", "start")
        self.reference = Path(self.tmp.name) / "reference.sh"
        self.reference.write_text("#!/usr/bin/env bash\nset -uo pipefail\n" + patterns_block() + REFERENCE_LOOP)

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        subprocess.run(["git", *args], cwd=self.repo, env=self.env, check=True, capture_output=True)

    def stage(self, files):
        for name, lines in files.items():
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("\n".join(lines) + "\n")
        self.git("add", "-A")

    def run_script(self, script):
        p = subprocess.run(["bash", str(script)], cwd=self.repo, env=self.env, capture_output=True, text=True)
        return p.returncode, p.stderr

    def test_ac01_a_4000_line_markdown_commit_takes_under_two_seconds(self):
        cycle = FLAGGED + PLAIN
        lines = [cycle[i % len(cycle)] + f" ({i})" for i in range(4200)]
        self.stage({"notes/a.md": lines[:2100], "notes/b.md": lines[2100:]})
        started = time.monotonic()
        code, err = self.run_script(HOOK)
        took = time.monotonic() - started
        self.assertEqual(code, 1)
        self.assertEqual(err.count("↳ matched:"), sum(1 for i in range(4200) if i % len(cycle) < len(FLAGGED)))
        self.assertLess(took, 2.0, f"the hook took {took:.2f} s")

    def test_ac02_same_files_lines_and_patterns_as_the_per_line_loop(self):
        mixed = [x for pair in zip(FLAGGED, PLAIN) for x in pair] * 4
        self.stage({"a/notes.md": mixed, "b/more notes.md": PLAIN + FLAGGED, "café.md": FLAGGED[:2],
                    "code.py": FLAGGED, "c/clean.md": PLAIN})
        new = self.run_script(HOOK)
        old = self.run_script(self.reference)
        self.assertEqual(new[0], 1)
        self.assertEqual(old[0], 1)
        report = lambda err: err[:err.index("This phrasing may cross")]
        self.assertEqual(report(new[1]), old[1])
        self.assertEqual(new[1].count("↳ matched:"), 4 * len(PLAIN) + len(FLAGGED) + 2)
        self.assertNotIn("code.py", new[1])

    def test_ac02_a_clean_diff_passes_both(self):
        self.stage({"a/notes.md": PLAIN})
        self.assertEqual(self.run_script(HOOK), (0, ""))
        self.assertEqual(self.run_script(self.reference), (0, ""))

    def test_sort_keys_are_spelled_with_a_space(self):
        # `-k 1,1`, not the joined form: a joined key reads as a short code word, and an owner's
        # private-word list (.githooks/pre-push) may hold one, which stopped the push of this file.
        self.assertNotRegex(HOOK.read_text(), r"-k[0-9]")

    def test_ac03_top_level_readme_and_the_hook_folder_are_exempt_a_stream_readme_is_not(self):
        self.stage({"README.md": FLAGGED, ".githooks/notes.md": FLAGGED, "s/p/README.md": FLAGGED[:1]})
        code, err = self.run_script(HOOK)
        self.assertEqual(code, 1)
        self.assertEqual(err.count("↳ matched:"), 1)
        self.assertIn("  s/p/README.md\n", err)


if __name__ == "__main__":
    unittest.main()
