"""runtime/roles/pm.md, Permanence's half of the PM role: rules every session needs, team or not.

The spending rules stay in Permanence (owner ruling 2026-11-14 16:50): without bakehouse no other file
carries them. SPEC.md's Roles paragraph says so too.
Standard library only; reads files.
"""
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
PM = (ROOT / "runtime" / "roles" / "pm.md").read_text()
SPEC = (ROOT / "SPEC.md").read_text()


class SpendingRules(unittest.TestCase):
    def test_the_cost_is_said_and_a_yes_given_before_spending_on_agents(self):
        self.assertIn("**Before spending on agents, say what it will cost and get a yes:**", PM)
        self.assertIn("**One agent** for a bounded task: say so and go", PM)

    def test_a_fan_out_waits_for_its_own_yes(self):
        self.assertIn("**More than one agent, or any fan-out:**", PM)
        self.assertIn("A yes to the work is not a yes to the fan-out.", PM)

    def test_a_failed_fan_out_is_never_retried_automatically(self):
        self.assertIn("**Never retry a failed fan-out automatically.**", PM)

    def test_the_scope_is_counted_before_spending(self):
        self.assertIn("**Count the scope before spending.**", PM)

    def test_spec_says_the_pm_asks_before_spending_on_agents(self):
        self.assertIn("asks before spending on agents", SPEC)


class BoardFromBakehouse(unittest.TestCase):
    def test_a_missing_bakehouse_command_means_no_team(self):
        self.assertIn("exit 127", PM)

    def test_only_closes_not_already_on_the_board_are_added(self):
        self.assertIn("whose work order is not already named on the board", PM)

    def test_the_since_time_is_the_boards_last_commit_and_nothing_else(self):
        self.assertIn("git -C ~/permanence log -1 --format=%cI --", PM)
        self.assertNotIn("A board never committed", PM)


if __name__ == "__main__":
    unittest.main()
