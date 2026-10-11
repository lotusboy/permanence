"""Tests for runtime/team_roles.py and the agent-roles hook. Standard library only.

The hook under test is runtime/agent-roles.py. Each test runs it with a scratch PERMA_DIR and a scratch HOME, so the
installed agents are exactly the ones the test writes.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

RUNTIME = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RUNTIME))
import team_roles  # noqa: E402

HOOK = RUNTIME / "agent-roles.py"
SHIPPED = RUNTIME / "agent-roles.json"


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.home, self.perma = t / "home", t / "perma"
        self.repo, self.other = t / "repo", t / "other"
        for d in (self.home / ".claude" / "agents", self.perma / "runtime", self.perma / "_meta",
                  self.repo, self.other):
            d.mkdir(parents=True)
        (self.perma / "runtime" / "resolve-stream.sh").symlink_to(RUNTIME / "resolve-stream.sh")
        (self.perma / "runtime" / "agent-roles.json").write_text(SHIPPED.read_text())
        (self.perma / "_meta" / "REGISTRY.md").write_text(
            f"| workspace path | stream | notes |\n|---|---|---|\n| {self.repo} | team/repo | x |\n")
        self.install("refactor-engineer", "refactor-reviewer", "architect", "design-author", "absence-check",
                     "blast-radius")

    def tearDown(self):
        self.tmp.cleanup()

    def install(self, *names):
        for n in names:
            (self.home / ".claude" / "agents" / f"{n}.md").write_text(f"---\nname: {n}\n---\n")

    def uninstall(self, name):
        (self.home / ".claude" / "agents" / f"{name}.md").unlink()

    def binding(self, roles):
        d = self.perma / "team" / "repo" / "repo"
        d.mkdir(parents=True, exist_ok=True)
        (d / "binding.json").write_text(json.dumps({"owned": True, "roles": roles}))

    def personal(self, roles):
        (self.perma / "_personal").mkdir(exist_ok=True)
        (self.perma / "_personal" / "agent-roles.json").write_text(json.dumps({"roles": roles}))

    def dispatch(self, st, cwd=None, **extra):
        d = {"hook_event_name": "PreToolUse", "tool_name": "Agent", "cwd": str(cwd or self.repo),
             "tool_input": {"subagent_type": st, "description": "x", "prompt": "p"}}
        d.update(extra)
        p = subprocess.run(["python3", str(HOOK)], input=json.dumps(d), capture_output=True, text=True,
                           env=dict(os.environ, HOME=str(self.home), PERMA_DIR=str(self.perma)))
        self.assertEqual(p.stderr, "")
        if not p.stdout.strip():
            return None
        out = json.loads(p.stdout)["hookSpecificOutput"]
        return "DENY" if out["permissionDecision"] == "deny" else out["updatedInput"]

    def stop(self, **extra):
        t = self.repo / "t.jsonl"
        t.write_text("")
        d = {"hook_event_name": "SubagentStop", "agent_type": "refactor-reviewer",
             "agent_transcript_path": str(t), "cwd": str(self.repo)}
        d.update(extra)
        return subprocess.run(["python3", str(HOOK)], input=json.dumps(d), capture_output=True, text=True,
                              env=dict(os.environ, HOME=str(self.home), PERMA_DIR=str(self.perma))).stdout

    def resolver(self, body):
        r = self.perma / "runtime" / "resolve-stream.sh"
        r.unlink()
        if body is not None:
            r.write_text(body)
            r.chmod(0o755)
        return r

    def log(self):
        return (self.perma / "runtime" / "logs" / "agent-roles.log").read_text()


class TestGate(Fixture):
    """Move 2's gate (design §7), against the shipped table."""

    def test_engineer_resolves_to_shipped_default(self):
        self.assertEqual(self.dispatch("role:engineer")["subagent_type"], "refactor-engineer")
        self.assertEqual(self.dispatch("role:refactor:engineer")["subagent_type"], "refactor-engineer")

    def test_binding_override_wins_in_its_repo_only(self):
        self.binding({"engineer": "design-author"})
        self.assertEqual(self.dispatch("role:engineer")["subagent_type"], "design-author")
        self.assertEqual(self.dispatch("role:engineer", cwd=self.other)["subagent_type"], "refactor-engineer")

    def test_job_qualified_key_wins_over_plain(self):
        self.binding({"engineer": "architect", "change:engineer": "design-author"})
        self.assertEqual(self.dispatch("role:change:engineer")["subagent_type"], "design-author")
        self.assertEqual(self.dispatch("role:refactor:engineer")["subagent_type"], "architect")

    def test_uninstalled_override_is_skipped_and_logged(self):
        self.binding({"engineer": "no-such-agent"})
        self.assertEqual(self.dispatch("role:engineer")["subagent_type"], "refactor-engineer")
        self.assertIn("SKIP role:engineer: binding roles key 'engineer' names ['no-such-agent']", self.log())

    def test_reviewer_falls_back_to_general_purpose(self):
        self.uninstall("refactor-reviewer")
        self.assertEqual(self.dispatch("role:reviewer")["subagent_type"], "general-purpose")

    def test_code_review_without_personal_is_general_purpose(self):
        out = self.dispatch("role:code-review")
        self.assertEqual((out["subagent_type"], out["model"]), ("general-purpose", "sonnet"))

    def test_code_review_with_personal_uses_its_provider_and_rules(self):
        self.install("plugin-review")
        self.personal({"code-review": {"providers": ["plugin-review"], "model": "sonnet",
                                       "run_record": True, "prompt_append": "Run record (required): x"}})
        out = self.dispatch("role:code-review")
        self.assertEqual((out["subagent_type"], out["model"]), ("plugin-review", "sonnet"))
        self.assertIn("Run record (required): x", out["prompt"])
        self.assertEqual(self.dispatch("plugin-review")["model"], "sonnet")

    def test_unfilled_role_is_denied_and_logged(self):
        self.uninstall("architect")
        self.assertEqual(self.dispatch("role:architect"), "DENY")
        self.assertEqual(self.dispatch("role:tester"), "DENY")
        self.assertEqual(self.dispatch("role:no-such-role"), "DENY")
        self.assertIn("DENY Permanence agent-roles: role 'architect' is unresolved", self.log())


class TestRules(Fixture):
    def test_direct_dispatch_keeps_role_rules(self):
        self.assertEqual(self.dispatch("refactor-engineer")["model"], "opus")
        self.assertIsNone(self.dispatch("general-purpose"))

    def test_nested_ceiling(self):
        out = self.dispatch("general-purpose", agent_type="refactor-reviewer",
                            tool_input={"subagent_type": "general-purpose", "model": "opus", "prompt": "p"})
        self.assertEqual(out["model"], "sonnet")

    def test_run_record_reads_reviews_from_binding(self):
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        d = self.perma / "team" / "repo" / "repo"
        d.mkdir(parents=True)
        (d / "binding.json").write_text(json.dumps({"owned": True, "reviews": "records/"}))
        t = self.repo / "t.jsonl"
        t.write_text("")
        stop = {"hook_event_name": "SubagentStop", "agent_type": "refactor-reviewer",
                "agent_transcript_path": str(t), "cwd": str(self.repo)}
        run = lambda: subprocess.run(["python3", str(HOOK)], input=json.dumps(stop), capture_output=True,
                                     text=True, env=dict(os.environ, HOME=str(self.home),
                                                         PERMA_DIR=str(self.perma))).stdout
        self.assertIn("write records/<YYYY-MM-DD>", run())
        (self.repo / "records" / "2026-10-05-x-review").mkdir(parents=True)
        (self.repo / "records" / "2026-10-05-x-review" / "02-pass-output.md").write_text("x")
        self.assertEqual(run(), "")


class TestReview(Fixture):
    """Findings of the adversarial review of 31fe3fe + a907219."""

    def assert_resolves(self):
        self.assertEqual(self.dispatch("role:code-review")["subagent_type"], "general-purpose")
        self.assertEqual(self.dispatch("role:absence-check")["subagent_type"], "absence-check")

    def test_p1_missing_resolver_skips_binding_level(self):
        self.resolver(None)
        self.assert_resolves()
        self.assertIn("SKIP binding level: cannot resolve the stream", self.log())

    def test_p1_non_executable_resolver(self):
        self.resolver("#!/bin/bash\necho team/repo\n").chmod(0o644)
        self.assert_resolves()

    def test_p1_slow_resolver_times_out(self):
        self.resolver("#!/bin/bash\nsleep 7\necho team/repo\n")
        t0 = time.time()
        self.assert_resolves()
        self.assertLess(time.time() - t0, 9)
        self.assertIn("TimeoutExpired", self.log())

    def test_m14_personal_level_before_shipped(self):
        self.personal({"absence-check": {"providers": ["design-author"]}})
        self.assertEqual(self.dispatch("role:absence-check")["subagent_type"], "design-author")

    def test_m15_personal_rules_before_shipped_rules(self):
        self.personal({"code-review": {"providers": ["refactor-engineer"], "model": "haiku"}})
        self.assertEqual(self.dispatch("refactor-engineer")["model"], "haiku")

    def test_m17_deny_reason_names_the_cause(self):
        self.uninstall("architect")
        self.dispatch("role:architect")
        self.dispatch("role:no-such-role")
        log = self.log()
        self.assertIn("role 'architect' is unresolved (no installed agent fills it)", log)
        self.assertIn("role 'no-such-role' is unresolved (no level names it)", log)

    def test_m16_perma_meta_has_no_binding(self):
        (self.perma / "_meta" / "REGISTRY.md").write_text(
            f"| workspace path | stream | notes |\n|---|---|---|\n| {self.repo} | perma-meta | x |\n")
        d = self.perma / "perma-meta" / "repo"
        d.mkdir(parents=True)
        (d / "binding.json").write_text(json.dumps({"owned": True, "roles": {"engineer": "design-author"}}))
        self.assertEqual(self.dispatch("role:engineer")["subagent_type"], "refactor-engineer")

    def test_m22_prompt_append_added_once(self):
        self.personal({"code-review": {"providers": ["design-author"], "prompt_append": "EXTRA"}})
        out = self.dispatch("design-author", tool_input={"subagent_type": "design-author",
                                                          "prompt": "p\n\n[perma:agent-roles]\nEXTRA"})
        self.assertIsNone(out)
        self.assertEqual(self.dispatch("design-author")["prompt"].count("EXTRA"), 1)

    def test_m24_second_stop_is_let_through(self):
        self.assertIn('"decision": "block"', self.stop())
        out = self.stop(stop_hook_active=True)
        self.assertNotIn("block", out)
        self.assertIn("systemMessage", out)

    def test_m25_model_approved_keeps_the_model(self):
        out = self.dispatch("blast-radius", tool_input={"subagent_type": "blast-radius", "model": "opus",
                                                         "description": "x [model-approved]", "prompt": "p"})
        self.assertIsNone(out)
        self.assertEqual(self.dispatch("blast-radius")["model"], "sonnet")

    def test_p2_4_prompt_names_the_bindings_review_folder(self):
        self.personal({"code-review": {"providers": ["design-author"],
                                       "prompt_append": "create {reviews}<date>-x/"}})
        self.assertIn("create axis/runs/<date>-x/", self.dispatch("design-author")["prompt"])
        d = self.perma / "team" / "repo" / "repo"
        d.mkdir(parents=True)
        (d / "binding.json").write_text(json.dumps({"owned": True, "reviews": "records"}))
        self.assertIn("create records/<date>-x/", self.dispatch("design-author")["prompt"])

    def test_p3_2_binding_provider_in_no_table_takes_the_roles_model(self):
        self.install("other-agent")
        self.binding({"engineer": "other-agent"})
        out = self.dispatch("role:refactor:engineer")
        self.assertEqual((out["subagent_type"], out["model"]), ("other-agent", "opus"))
        self.assertNotIn("[perma:agent-roles]", out["prompt"])

    def test_binding_table_form_entry_sets_the_model(self):
        self.install("other-agent")
        self.binding({"change:engineer": {"providers": ["other-agent"], "model": "sonnet"}})
        out = self.dispatch("role:change:engineer")
        self.assertEqual((out["subagent_type"], out["model"]), ("other-agent", "sonnet"))
        self.assertEqual(self.dispatch("role:refactor:engineer")["model"], "opus")
        self.assertEqual(self.dispatch("role:change:engineer", cwd=self.other)["subagent_type"],
                         "refactor-engineer")

    def test_p3_3_string_providers_name_no_agent(self):
        self.install("a")
        self.personal({"absence-check": {"providers": "abc"}})
        self.assertEqual(self.dispatch("role:absence-check")["subagent_type"], "absence-check")
        self.assertEqual(team_roles.providers({"providers": "abc"}), [])

    def test_p3_3_bad_reviews_skip_the_run_record_check(self):
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        d = self.perma / "team" / "repo" / "repo"
        d.mkdir(parents=True)
        for bad in (["x"], "/tmp", "../up"):
            (d / "binding.json").write_text(json.dumps({"owned": True, "reviews": bad}))
            self.assertEqual(self.stop(), "", bad)
        log = self.log()
        self.assertIn("is not a path", log)
        self.assertEqual(log.count("is outside the repository"), 2)


class TestResolve(unittest.TestCase):
    def test_levels_in_order(self):
        lv = [("binding roles", {"reviewer": "b"}), ("personal", {"reviewer": {"providers": ["p"]}}),
              ("shipped", {"reviewer": {"providers": ["s"]}})]
        self.assertEqual(team_roles.resolve("reviewer", lv, {"b", "p", "s"})["agent"], "b")
        self.assertEqual(team_roles.resolve("reviewer", lv, {"p", "s"})["where"], "personal")
        r = team_roles.resolve("refactor:reviewer", lv, {"s"})
        self.assertEqual((r["agent"], r["key"], len(r["skipped"])), ("s", "reviewer", 2))

    def test_fallbacks(self):
        self.assertEqual(team_roles.resolve("x:reviewer", [], set())["agent"], "general-purpose")
        self.assertEqual(team_roles.resolve("code-review", [], set())["fallback"], "general-purpose")
        r = team_roles.resolve("refactor:engineer", [], set())
        self.assertEqual((r["agent"], r["fallback"]), (None, "session"))


if __name__ == "__main__":
    unittest.main()
