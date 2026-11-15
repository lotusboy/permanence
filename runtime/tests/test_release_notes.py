"""CHANGELOG.md's v1.12.0 migration notes reach every user the release changes for, team or not.
Standard library only; reads one file."""
import pathlib
import unittest

TEXT = (pathlib.Path(__file__).resolve().parents[2] / "CHANGELOG.md").read_text()
ENTRY = TEXT[TEXT.index("## [1.12.0]"):TEXT.index("## [1.11.0]")]
NOTES = ENTRY[ENTRY.index("**Migration notes.**"):]


class MigrationNotes(unittest.TestCase):
    def test_the_two_tools_v1_11_0_listed_as_core_extras_are_named_with_where_they_went(self):
        # docs/TOOLS.md in v1.11.0 listed both under "Core: optional extras", usable without the team.
        for tool in ("predict-gate.sh", "save-report.sh"):
            self.assertIn(f"`{tool}`", NOTES, tool)
        self.assertIn("install bakehouse", NOTES)


if __name__ == "__main__":
    unittest.main()
