"""runtime/stale-loops.sh (v1.15.0) brings old open loops back: open questions and board rows more than N
days old, or past their by: date, and LOG paragraphs holding a marker phrase. /perma-brief prints its
section; /perma-startup prints its one line for one stream. Read-only.
Standard library only. A scratch Permanence in its own git repo, with commits at fixed dates; "today" is
set with PERMA_TODAY."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "runtime"
OLD, YOUNG, TODAY = "2026-06-01T12:00:00", "2026-06-25T12:00:00", "2026-06-30"  # 29 and 5 days old


class StaleLoops(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(os.path.realpath(self.tmp.name))
        self.perma = base / "permanence"
        (self.perma / "_meta").mkdir(parents=True)
        (self.perma / "_meta" / "PROJECT.md").write_text("# meta\n")
        (self.perma / "runtime").mkdir()  # holds only the owner's setting; the scripts run from the repo
        self.home = base / "home"
        self.home.mkdir()
        self.env = {"HOME": str(self.home), "PATH": os.environ["PATH"], "PERMA_DIR": str(self.perma),
                    "PERMA_TODAY": TODAY}
        self.git("init", "-q")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "ci@example.com")
        self.git("config", "commit.gpgsign", "false")
        self.git("config", "core.hooksPath", "/dev/null")

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args, date=None):
        env = dict(self.env)
        if date:
            env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
        subprocess.run(["git", "-C", str(self.perma), *args], check=True, capture_output=True, env=env)

    def write(self, rel, text):
        path = self.perma / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def commit(self, date):
        self.git("add", "-A", ".", ":!runtime")
        self.git("commit", "-q", "--allow-empty", "-m", "c", date=date)

    def stream(self, name, **files):
        self.write(f"{name}/PROJECT.md", "# p\n")
        for fname, text in files.items():
            self.write(f"{name}/{fname}.md", text)

    def run_it(self, *args):
        p = subprocess.run(["bash", str(RUNTIME / "stale-loops.sh"), *args], capture_output=True, text=True,
                           env=self.env)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stderr, "")
        return p.stdout

    def items(self, out):
        return [ln for ln in out.splitlines() if ln.startswith("- ")]

    # --- age -----------------------------------------------------------------------------------

    def test_an_old_open_question_is_listed_and_a_young_one_is_not(self):
        table = "# QUESTIONS\n\n| # | Question | Where |\n|---|---|---|\n| Q1 | Who signs off the audit? | owner |\n"
        self.stream("acme/shop", QUESTIONS=table)
        self.commit(OLD)
        self.write("acme/shop/QUESTIONS.md", table + "| Q2 | Which supplier next? | owner |\n")
        self.commit(YOUNG)
        out = self.run_it()
        self.assertEqual(self.items(out), ["- acme/shop · QUESTIONS.md:5 · Q1 Who signs off the audit? · 29 days old"])
        self.assertIn("Stale loops: 1 in 1 stream (open items more than 14 days old", out)

    def test_oldest_first(self):
        self.stream("acme/shop", QUESTIONS="## Open\n\n- First question\n")
        self.commit(OLD)
        self.write("acme/shop/QUESTIONS.md", "## Open\n\n- First question\n- Second question\n")
        self.commit("2026-06-10T12:00:00")
        self.assertEqual([i.split(" · ")[2] for i in self.items(self.run_it())],
                         ["First question", "Second question"])

    def test_a_row_moved_inside_its_file_keeps_its_age(self):
        row = "- Decide the export format for the quarterly figures\n"
        self.stream("acme/shop", WIP="## Now\n\n" + row + "\n## Blocked\n\n## Parked\n\n")
        self.commit(OLD)
        self.write("acme/shop/WIP.md", "## Now\n\n## Blocked\n\n## Parked\n\n" + row)
        self.commit(YOUNG)
        self.assertEqual(self.items(self.run_it()),
                         ["- acme/shop · WIP.md:7 · Decide the export format for the quarterly figures · 29 days old"])

    def test_uncommitted_lines_count_as_new(self):
        self.stream("acme/shop", QUESTIONS="## Open\n\n")
        self.commit(OLD)
        self.write("acme/shop/QUESTIONS.md", "## Open\n\n- Not committed yet\n")
        self.assertIn("Stale loops: none", self.run_it())

    # --- the three files -----------------------------------------------------------------------

    def test_three_question_shapes(self):
        self.stream("acme/shop", QUESTIONS=(
            "# QUESTIONS\n\n> Open questions.\n\n## Open\n\n- **A bullet question** (2026-05-01)\n  wrapped on\n\n"
            "| # | Question | Where |\n|---|---|---|\n| Q7 | A table question | owner |\n\n"
            "## Q — A heading question (raised 2026-05-02)\n\nIts body.\n"))
        self.commit(OLD)
        self.assertEqual([i.split(" · ")[1:3] for i in self.items(self.run_it())],
                         [["QUESTIONS.md:7", "A bullet question (2026-05-01)"],
                          ["QUESTIONS.md:12", "Q7 A table question"],
                          ["QUESTIONS.md:14", "Q — A heading question (raised 2026-05-02)"]])

    def test_closed_items_are_left_out(self):
        self.stream("acme/shop", QUESTIONS=(
            "## Open\n\n- Closed bullet [CLOSED 2026-06-02: done]\n\n"
            "| # | Question | Where |\n|---|---|---|\n| Q3 | Closed row | [CLOSED 2026-06-02: yes] |\n\n"
            "## Q — A closed heading [CLOSED 2026-06-02: no]\n\n"
            "## Answered / closed\n\n- Answered long ago\n\n| Q9 | Also answered | x |\n"),
            LOG="## 2026-05-01 — a day\n\nThe report is not yet read. [CLOSED 2026-06-03: read]\n")
        self.commit(OLD)
        self.assertIn("Stale loops: none", self.run_it())

    def test_the_template_placeholder_row_is_left_out(self):
        self.stream("acme/shop", QUESTIONS=(ROOT / "templates" / "QUESTIONS.template.md").read_text(),
                    LOG=(ROOT / "templates" / "LOG.template.md").read_text())
        self.commit(OLD)
        self.assertIn("Stale loops: none", self.run_it())

    def test_board_reads_only_now_blocked_and_parked(self):
        self.stream("acme/shop", WIP=(
            "# WIP\n\n## Now\n\n- Now row\n  with a second line\n\n## Blocked\n\n- Nothing.\n- Blocked row\n\n"
            "## Parked\n\n- Parked row (reason: waiting for the spring)\n\n## Done today\n\n- Done row\n\n"
            "## Watch\n\n- Watch row\n"))
        self.commit(OLD)
        self.assertEqual([i.split(" · ")[1:3] for i in self.items(self.run_it())],
                         [["WIP.md:5", "Now row"], ["WIP.md:11", "Blocked row"],
                          ["WIP.md:15", "Parked row (reason: waiting for the spring)"]])

    def test_log_marker_phrases(self):
        self.stream("acme/shop", LOG=(
            "# LOG\n\n> Append-only. The phrase to confirm here is before any entry.\n\n"
            "## 2026-06-25 — young\n\nStill to confirm, but young.\n\n"
            "## 2026-06-01 — old\n\nThe assessment is attached; not yet\nread here.\n\n"
            "- The figure is still unconfirmed.\n- Probably overtaken by the new plan.\n\n"
            "Nobody holds it: no owner.\n\nThe date is for Owner to confirm.\n\n"
            "```\nan example: not yet read\n```\n\n"
            "### a sub-heading keeps the date\n\nThis one is still unconfirmed too.\n"))
        self.commit(YOUNG)
        out = self.run_it()  # lines 11, 14, 15, 17, 19, 27; not 3 (before any entry), 7 (young), 22 (fenced)
        self.assertIn("Stale loops: 6 in 1 stream", out)
        self.assertEqual([i.split(" · ")[1] for i in self.items(out)], ["LOG.md:11", "LOG.md:14", "LOG.md:15"])
        self.assertIn("Not shown: 3 (acme/shop 3).", out)
        self.assertIn("“The assessment is attached; not yet read here.” · 29 days old", out)
        self.assertIn("“The figure is still unconfirmed.”", out)

    # --- by: dates -----------------------------------------------------------------------------

    def test_by_dates(self):
        self.stream("acme/shop", QUESTIONS="## Open\n\n- Old, but by: 2026-07-15\n- Old, owner: the owner, no date\n")
        self.commit(OLD)
        self.write("acme/shop/QUESTIONS.md", "## Open\n\n- Old, but by: 2026-07-15\n- Old, owner: the owner, no date\n"
                                              "- Young, owner: the owner, by: 2026-06-20\n")
        self.commit(YOUNG)
        self.assertEqual([i.split(" · ")[2:] for i in self.items(self.run_it())],
                         [["Old, owner: the owner, no date", "29 days old"],
                          ["Young, owner: the owner, by: 2026-06-20", "10 days past its by: date 2026-06-20"]])

    def test_a_later_by_date_wins(self):
        self.stream("acme/shop", WIP="## Parked\n\n- Parked on purpose: by: 2026-06-10, then by: 2026-08-01\n")
        self.commit(OLD)
        self.assertIn("Stale loops: none", self.run_it())

    # --- the cap, the streams, the setting --------------------------------------------------------

    def test_the_cap(self):
        for s in ("a/one", "b/two", "c/three", "d/four"):
            self.stream(s, QUESTIONS="## Open\n\n" + "".join(f"- {s} question {n}\n" for n in range(4)))
        self.commit(OLD)
        out = self.run_it()
        shown = [i.split(" · ")[0][2:] for i in self.items(out)]
        self.assertEqual(len(shown), 10)
        self.assertEqual({s: shown.count(s) for s in set(shown)}, {"a/one": 3, "b/two": 3, "c/three": 3, "d/four": 1})
        self.assertIn("Stale loops: 16 in 4 streams", out)
        self.assertIn("Not shown: 6 (a/one 1, b/two 1, c/three 1, d/four 3).", out)
        self.assertIn("close it ([CLOSED YYYY-MM-DD: answer]); give it an owner and a date "
                      "(owner: X, by: YYYY-MM-DD); or park it on purpose (by: a review date, and the reason).", out)

    def test_a_stream_with_no_questions_board_or_log(self):
        self.stream("acme/bare")
        self.commit(OLD)
        self.assertEqual(self.run_it(), "Stale loops: none (open items more than 14 days old, or past their by: date).\n")

    def test_perma_meta_is_left_out(self):
        self.write("_meta/WIP.md", "## Now\n\n- A meta row\n")
        self.write("LOG.md", "## 2026-05-01 — x\n\nNot yet read.\n")
        self.commit(OLD)
        self.assertIn("Stale loops: none", self.run_it())

    def test_the_setting(self):
        self.stream("acme/shop", QUESTIONS="## Open\n\n- A question\n")
        self.commit(OLD)
        setting = self.perma / "runtime" / ".stale-loops"
        for value, listed in (("40\n", False), ("  7 \n", True), ("junk\n", True), ("\n\n20\n", True),
                              ("0\n", True)):
            setting.write_text(value)
            self.assertEqual(bool(self.items(self.run_it())), listed, value)
        setting.write_text("40\n")
        self.assertIn("more than 40 days old", self.run_it())
        setting.write_text("OFF\n")
        self.assertEqual(self.run_it(), "")
        self.assertEqual(self.run_it("acme/shop"), "")

    def test_one_stream(self):
        self.stream("acme/shop", QUESTIONS="## Open\n\n- Older one\n")
        self.stream("acme/quiet")
        self.commit(OLD)
        self.write("acme/shop/QUESTIONS.md", "## Open\n\n- Older one\n- Newer one\n")
        self.commit("2026-06-10T12:00:00")
        self.assertEqual(self.run_it("acme/shop/"),
                         "Stale loops in this stream: 2. The oldest: QUESTIONS.md:3 · Older one · 29 days old. "
                         "/perma-brief shows up to 3 per stream.\n")
        self.assertEqual(self.run_it("acme/quiet"), "")
        self.assertEqual(self.run_it("no/such"), "")

    def test_no_permanence(self):
        self.env["PERMA_DIR"] = str(self.perma / "missing")
        self.assertEqual(self.run_it(), "")

    # --- the review's findings (design 2026-11-24, 02) --------------------------------------------

    def test_an_amended_row_takes_the_amend_date(self):  # P2-1: committer time, never too old
        self.stream("acme/shop", WIP="## Now\n\n- First row\n")
        self.commit(OLD)
        self.write("acme/shop/WIP.md", "## Now\n\n- First row\n- Added three weeks later by an amend\n")
        self.git("add", "-A", ".", ":!runtime")
        env = dict(self.env, GIT_COMMITTER_DATE="2026-06-28T12:00:00")
        subprocess.run(["git", "-C", str(self.perma), "commit", "-q", "--amend", "--no-edit"], check=True,
                       capture_output=True, env=env)
        self.assertIn("Stale loops: none", self.run_it())

    def test_a_closed_sub_item_leaves_its_parent_open(self):  # P2-2
        self.stream("acme/shop", QUESTIONS=(
            "## Open\n\n- Parent question still open\n  - a sub-part [CLOSED 2026-06-02: done]\n\n"
            "### Q10 — A heading question\n\nOne sub-part is [CLOSED 2026-06-02: yes]; the rest is open.\n"))
        self.commit(OLD)
        self.assertEqual([i.split(" · ")[1] for i in self.items(self.run_it())], ["QUESTIONS.md:3", "QUESTIONS.md:6"])

    def test_only_a_heading_that_starts_closed_or_answered_closes_its_section(self):  # P2-3
        self.stream("acme/shop", QUESTIONS=(
            "# QUESTIONS — closed-loop pump\n\n## Unanswered\n\n- One\n\n## Not yet answered\n\n- Two\n\n"
            "## Answered\n\n- Three\n\n## Closed (2026)\n\n- Four\n"))
        self.commit(OLD)
        self.assertEqual([i.split(" · ")[2] for i in self.items(self.run_it())], ["One", "Two"])

    def test_numbered_lists_are_items(self):  # P2-4
        self.stream("acme/shop", WIP="## Parked\n\n- A bullet row\n1. A numbered row\n2) Another one\n")
        self.commit(OLD)
        self.assertEqual([i.split(" · ")[2] for i in self.items(self.run_it())],
                         ["A bullet row", "A numbered row", "Another one"])

    def test_a_log_line_with_a_past_by_date_and_no_phrase(self):  # P2-5
        self.stream("acme/shop", LOG="## 2026-06-25 — x\n\n- Draft due by: 2026-06-10\n\n- Later, by: 2026-07-10\n")
        self.commit(YOUNG)
        self.assertEqual([i.split(" · ")[1:] for i in self.items(self.run_it())],
                         [["LOG.md:3", "“Draft due by: 2026-06-10”", "20 days past its by: date 2026-06-10"]])

    def test_a_failure_says_so(self):  # P2-7
        self.stream("acme/shop", QUESTIONS="## Open\n\n- A question\n")
        self.commit(OLD)
        (self.perma / "runtime" / ".stale-loops").write_bytes(b"\xff14\n")
        self.assertIn("Stale loops: 1 in 1 stream", self.run_it())  # unreadable setting: the default
        (self.perma / "runtime" / ".stale-loops").write_bytes("\ufeffoff\n".encode())
        self.assertEqual(self.run_it(), "")                          # P3-12: a BOM does not hide "off"
        (self.perma / "runtime" / ".stale-loops").unlink()
        tools = self.perma.parent / "tools"   # python3 and git on PATH, but no bash for the stream list
        tools.mkdir()
        for tool in ("python3", "git", "dirname"):
            found = subprocess.run(["bash", "-c", f"command -v {tool}"], capture_output=True, text=True).stdout.strip()
            (tools / tool).symlink_to(found)
        bash = subprocess.run(["bash", "-c", "command -v bash"], capture_output=True, text=True).stdout.strip()
        p = subprocess.run([bash, str(RUNTIME / "stale-loops.sh")], capture_output=True, text=True,
                           env=dict(self.env, PATH=str(tools)))
        self.assertEqual((p.returncode, p.stdout), (0, "Stale loops: not checked (the check failed: FileNotFoundError).\n"))

    def test_closed_looking_rows_comments_tables_and_code_spans(self):  # P3-1, P3-3, P3-4, P3-5
        self.stream("acme/shop", WIP=(
            "## Now\n\n<!-- - A commented row\n- Another -->\n- [x] A done task\n- [ ] An open task\n"
            "- ~~A struck row~~\n- A row with a table\n  | inner | table |\n"
            "- A row that only quotes `by: 2099-01-01`\n"))
        self.commit(OLD)
        self.assertEqual([i.split(" · ")[2] for i in self.items(self.run_it())[:3]] + [len(self.items(self.run_it()))],
                         ["[ ] An open task", "A row with a table", "A row that only quotes by: 2099-01-01", 3])

    def test_month_grouped_log_and_labels(self):  # P3-7, P3-8
        self.stream("acme/shop", LOG=(
            "## June 2026\n\n### 2026-06-04 — a day\n\nThe figure is still unconfirmed.\n\n"
            "### 2026-06-05\n\nThe phrase 'still unconfirmed' was used.\n"))
        self.commit(YOUNG)
        out = self.run_it()
        self.assertIn("LOG.md:5 · “The figure is still unconfirmed.” · 26 days old", out)
        self.assertIn("LOG.md:9 · “The phrase 'still unconfirmed' was used.” · 25 days old", out)

    # --- the PR review's findings (design 2026-11-24, 04) -----------------------------------------

    def test_finished_work_and_bare_adjectives_are_not_loops(self):  # P2-3, owner's narrow rule
        self.stream("acme/shop", LOG=(
            "## 2026-06-01 — old\n\nRe-ran the suite to confirm nothing moved.\n\nRe-ran to confirm. Done.\n\n"
            "- Diffed every file to confirm only two changed.\n\nThe tag is unconfirmed in the data model.\n\n"
            "- Ran it twice. Checked to confirm.\n\n- **Decision (Owner to confirm direction)**: ship it\n"))
        self.commit(OLD)
        self.assertEqual([i.split(" · ")[1] for i in self.items(self.run_it())], ["LOG.md:13"])

    def test_a_sub_heading_inside_a_closed_section_stays_closed(self):  # P2-1
        self.stream("acme/shop", QUESTIONS=(
            "# Questions\n\n## Open\n\n- open one\n\n## Closed\n\n### September\n\n- answered thing\n"
            "- another\n\n## Later\n\n- reopened section\n"))
        self.commit(OLD)
        self.assertEqual([i.split(" · ")[2] for i in self.items(self.run_it())], ["open one", "reopened section"])

    def test_a_sub_heading_inside_a_board_section_stays_inside(self):  # P2-2
        self.stream("acme/shop", WIP=(
            "# WIP\n\n## Now\n\n### Project A\n\n- row under A\n\n## Parked\n\n- parked row\n\n"
            "## Done today\n\n### Morning\n\n- done row\n"))
        self.commit(OLD)
        self.assertEqual([i.split(" · ")[2] for i in self.items(self.run_it())], ["row under A", "parked row"])

    def test_a_board_row_is_as_old_as_its_newest_line(self):  # P2-4, owner's ruling
        rows = "## Now\n\n- A row worked on every day\n  - started\n"
        self.stream("acme/shop", WIP=rows, QUESTIONS="## Open\n\n- A question\n  - started\n")
        self.commit(OLD)
        self.write("acme/shop/WIP.md", rows + "  - and updated yesterday\n")
        self.write("acme/shop/QUESTIONS.md", "## Open\n\n- A question\n  - started\n  - and edited\n")
        self.commit("2026-06-29T12:00:00")
        self.assertEqual([i.split(" · ")[1:] for i in self.items(self.run_it())],
                         [["QUESTIONS.md:3", "A question", "29 days old"]])

    def test_a_struck_heading_question_is_closed(self):  # P3-1
        self.stream("acme/shop", QUESTIONS="## Q — ~~Old question?~~ ANSWERED 2026-05-27\n\n## Q — Still open?\n")
        self.commit(OLD)
        self.assertEqual([i.split(" · ")[2] for i in self.items(self.run_it())], ["Q — Still open?"])

    def test_fences_follow_the_meters_rule(self):  # P3-2
        self.stream("acme/shop", QUESTIONS=(
            "## Open\n\n```bash``` is how\n- not hidden\n\n````\n- in code\n```\n- still in code\n````\n"
            "- after the fence\n\n~~~\n- tilde code\n```\n~~~\n- after the tilde fence\n"))
        self.commit(OLD)
        out = self.run_it()  # exactly three: the code lines inside both fences are not items
        self.assertEqual([i.split(" · ")[2] for i in self.items(out)],
                         ["not hidden", "after the fence", "after the tilde fence"])
        self.assertIn("Stale loops: 3 in 1 stream", out)

    def test_a_sub_items_by_date_does_not_decide_the_parent(self):  # P3-3
        self.stream("acme/shop", QUESTIONS="## Open\n\n- Parent, young\n  - a part, by: 2026-06-10\n")
        self.commit(YOUNG)
        self.assertIn("Stale loops: none", self.run_it())

    # --- the commands ---------------------------------------------------------------------------

    def test_perma_help_reads_the_setting_the_same_way(self):
        help_sh = RUNTIME / "perma-help.sh"
        setting = self.perma / "runtime" / ".stale-loops"
        for value, shown in ((None, "more than 14 days old"), ("30\n", "more than 30 days old"),
                             ("0\n", "more than 14 days old"), ("99999\n", "more than 14 days old"),
                             ("junk\n", "more than 14 days old"), ("Off\n", "switched off in runtime/.stale-loops")):
            if value is not None:
                setting.write_text(value)
            out = subprocess.run(["bash", str(help_sh)], capture_output=True, text=True, env=self.env).stdout
            line = next((ln for ln in out.splitlines() if "stale loops in /perma-brief" in ln), "")
            self.assertIn(shown, line, value)


    def test_the_brief_and_startup_run_it(self):
        brief = (RUNTIME / "commands" / "perma-brief.md").read_text()
        self.assertIn("~/permanence/runtime/stale-loops.sh", brief)
        self.assertIn("**Stale loops**", brief)
        startup = (RUNTIME / "commands" / "perma-startup.md").read_text()
        self.assertIn('~/permanence/runtime/stale-loops.sh "<stream>"', startup)


if __name__ == "__main__":
    unittest.main()
