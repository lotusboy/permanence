"""runtime/context-meter.sh, the UserPromptSubmit hook that says when the context is getting full: it reads
the last main-thread assistant message of a real-shaped transcript, sizes it against the model's window,
and prints one line at or above the threshold. Every failure prints nothing and exits 0.
Standard library only. Scratch folders; PERMA_DIR is a scratch folder holding only runtime/.context-warn."""
import json
import os
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
METER = ROOT / "runtime" / "context-meter.sh"


def assistant(model, used, sidechain=False, text="ok"):
    # The shape Claude Code writes: usage split across plain, cache-read and cache-creation input.
    third = used // 3
    return {"parentUuid": "p", "isSidechain": sidechain, "type": "assistant", "uuid": "u",
            "sessionId": "s", "message": {"model": model, "role": "assistant", "type": "message",
            "content": [{"type": "text", "text": text}],
            "usage": {"input_tokens": used - 2 * third, "cache_read_input_tokens": third,
                      "cache_creation_input_tokens": third, "output_tokens": 50}}}


def user(text="next", sidechain=False):
    return {"parentUuid": "p", "isSidechain": sidechain, "type": "user", "uuid": "u",
            "message": {"role": "user", "content": text}}


class Meter(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.perma = self.dir / "perma"
        (self.perma / "runtime").mkdir(parents=True)
        self.transcript = self.dir / "session.jsonl"
        self.env = {k: v for k, v in os.environ.items() if k != "CLAUDE_CODE_DISABLE_1M_CONTEXT"}
        self.env.update(HOME=str(self.dir / "home"), PERMA_DIR=str(self.perma))

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, *entries):
        with open(self.transcript, "w") as f:
            for e in entries:
                f.write((e if isinstance(e, str) else json.dumps(e)) + "\n")

    def run_meter(self, stdin=None, env=None):
        if stdin is None:
            stdin = json.dumps({"session_id": "s", "transcript_path": str(self.transcript),
                                "cwd": "/x", "hook_event_name": "UserPromptSubmit", "prompt": "hi"})
        p = subprocess.run(["bash", str(METER)], input=stdin, capture_output=True, text=True,
                           env=env or self.env)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stderr, "")
        return p.stdout

    def warn(self, value):
        (self.perma / "runtime" / ".context-warn").write_text(value)

    def test_the_line_it_prints(self):
        self.write(user(), assistant("claude-opus-5-5", 640000), user())
        self.assertEqual(self.run_meter(),
                         "[perma] context 64% used (640k of 1M): at the next natural break, write back "
                         "to the stream, then ask the owner to /compact.\n")

    def test_the_main_thread_counts_not_a_sidechain_after_it(self):
        self.write(assistant("claude-opus-5-5", 700000), assistant("claude-haiku-4-5", 20000, sidechain=True),
                   user(sidechain=True))
        self.assertIn("context 70% used (700k of 1M)", self.run_meter())
        self.write(assistant("claude-opus-5-5", 100000), assistant("claude-opus-5-5", 900000, sidechain=True))
        self.assertEqual(self.run_meter(), "")

    def test_a_synthetic_message_is_skipped(self):
        self.write(assistant("claude-sonnet-5-5", 650000), assistant("<synthetic>", 0))
        self.assertIn("65% used", self.run_meter())

    def test_each_model_is_sized_by_its_window(self):
        cases = [  # (model, tokens used, expected text or "" for silence)
            ("claude-fable-5-2", 610000, "61% used (610k of 1M)"),
            ("claude-opus-5-5", 610000, "61% used (610k of 1M)"),
            ("claude-sonnet-5-5", 610000, "61% used (610k of 1M)"),
            ("claude-haiku-5-5", 610000, "61% used (610k of 1M)"),
            ("claude-opus-4-8", 610000, "61% used (610k of 1M)"),
            ("us.anthropic.claude-opus-4-7", 610000, "61% used (610k of 1M)"),
            ("claude-haiku-5-5", 150000, ""),                                  # 15% of 1M
            ("claude-haiku-4-5-20251001", 150000, "75% used (150k of 200k)"),
            ("claude-sonnet-4-5@20250929", 150000, "75% used (150k of 200k)"),
            ("claude-opus-4-6", 150000, "75% used (150k of 200k)"),            # 200k unless [1m]
            ("claude-opus-4-6", 300000, ""),                                   # past 200k: it is [1m]
            ("claude-sonnet-4-6", 700000, "70% used (700k of 1M)"),
            ("claude-opus-4-6[1m]", 150000, ""),
        ]
        for model, used, want in cases:
            with self.subTest(model=model, used=used):
                self.write(assistant(model, used))
                got = self.run_meter()
                if want:
                    self.assertIn(want, got)
                else:
                    self.assertEqual(got, "")

    def test_one_m_context_switched_off_means_200k(self):
        self.write(assistant("claude-opus-5-5", 150000))
        self.assertEqual(self.run_meter(), "")
        self.assertIn("75% used (150k of 200k)",
                      self.run_meter(env=dict(self.env, CLAUDE_CODE_DISABLE_1M_CONTEXT="1")))

    def test_the_threshold_edge(self):
        self.write(assistant("claude-opus-5-5", 599999))
        self.assertEqual(self.run_meter(), "")
        self.write(assistant("claude-opus-5-5", 600000))
        self.assertIn("60% used (600k of 1M)", self.run_meter())

    def test_the_override_file(self):
        self.write(assistant("claude-opus-5-5", 500000))
        self.assertEqual(self.run_meter(), "")
        self.warn("50\n")
        self.assertIn("50% used", self.run_meter())
        self.warn("\n  51  \n")
        self.assertEqual(self.run_meter(), "")
        self.write(assistant("claude-opus-5-5", 990000))
        self.warn("off\n")
        self.assertEqual(self.run_meter(), "")
        for bad in ("abc", "0", "101", "-5", "6O", "050"):   # ignored: the default 60 applies
            with self.subTest(bad=bad):
                self.warn(bad)
                self.write(assistant("claude-opus-5-5", 590000))
                self.assertEqual(self.run_meter(), "")
                self.write(assistant("claude-opus-5-5", 610000))
                self.assertIn("61% used", self.run_meter())

    def test_an_unknown_model_prints_nothing(self):
        for model in ("my-gateway-model", "claude-haiku-9-9", "gpt-x"):
            with self.subTest(model=model):
                self.write(assistant(model, 990000))
                self.assertEqual(self.run_meter(), "")

    def test_after_a_compaction_the_old_count_is_not_used(self):
        boundary = {"type": "system", "subtype": "compact_boundary", "isSidechain": False,
                    "content": "Conversation compacted", "compactMetadata": {"trigger": "manual"}}
        self.write(assistant("claude-opus-5-5", 900000), boundary, user())
        self.assertEqual(self.run_meter(), "")
        self.write(assistant("claude-opus-5-5", 900000), boundary, assistant("claude-opus-5-5", 650000))
        self.assertIn("65% used", self.run_meter())

    def test_every_failure_is_silent(self):
        self.write(assistant("claude-opus-5-5", 900000))
        for stdin in ("", "not json", "[]", json.dumps({"session_id": "s"}),
                      json.dumps({"transcript_path": str(self.dir / "missing.jsonl")}),
                      json.dumps({"transcript_path": 42}), json.dumps({"transcript_path": str(self.dir)})):
            with self.subTest(stdin=stdin):
                self.assertEqual(self.run_meter(stdin=stdin), "")
        for garbled in (["{not json", "\x00\x01", ""],
                        [json.dumps({"type": "assistant", "isSidechain": False, "message": "x"})],
                        [json.dumps({"type": "assistant", "message": {"model": "claude-opus-5-5",
                                                                      "usage": {"input_tokens": "lots"}}})],
                        [json.dumps({"type": "assistant", "message": {"model": "claude-opus-5-5"}})]):
            with self.subTest(garbled=garbled):
                self.write(*garbled)
                self.assertEqual(self.run_meter(), "")
        self.transcript.write_bytes(b"\xff\xfe" * 1000)
        self.assertEqual(self.run_meter(), "")

    def test_garbled_lines_after_the_last_turn_do_not_hide_it(self):
        self.write(assistant("claude-opus-5-5", 650000), "{cut off mid-wri")
        self.assertIn("65% used", self.run_meter())

    def test_without_python3_it_prints_nothing(self):
        bin_dir = self.dir / "bin"
        bin_dir.mkdir()
        for tool in ("bash", "cat", "grep", "head", "tr"):
            os.symlink(shutil.which(tool), bin_dir / tool)
        self.write(assistant("claude-opus-5-5", 900000))
        self.assertEqual(self.run_meter(env=dict(self.env, PATH=str(bin_dir))), "")

    def test_a_turn_longer_than_one_read_chunk_is_still_found(self):
        self.write(assistant("claude-opus-5-5", 700000, text="x" * (3 << 20)), user())
        self.assertIn("70% used", self.run_meter())

    def test_a_20_mb_transcript_is_read_from_its_end_quickly(self):
        filler = json.dumps(user("y" * 4000))
        with open(self.transcript, "w") as f:
            f.write(json.dumps(assistant("claude-opus-5-5", 950000)) + "\n")   # far back: not reached
            for _ in range((20 << 20) // len(filler)):
                f.write(filler + "\n")
            f.write(json.dumps(assistant("claude-opus-5-5", 620000)) + "\n")
            f.write(json.dumps(assistant("claude-opus-5-5", 999000, sidechain=True)) + "\n")
            f.write(filler + "\n")
        self.assertGreater(self.transcript.stat().st_size, 20 << 20)
        start = time.monotonic()
        out = self.run_meter()
        took = time.monotonic() - start
        self.assertIn("62% used", out)
        self.assertLess(took, 2.0, f"took {took:.3f}s")
        # The bound: a last turn further back than 8 MB from the end is not searched for.
        with open(self.transcript, "w") as f:
            f.write(json.dumps(assistant("claude-opus-5-5", 950000)) + "\n")
            for _ in range((20 << 20) // len(filler)):
                f.write(filler + "\n")
        start = time.monotonic()
        self.assertEqual(self.run_meter(), "")
        took = time.monotonic() - start
        self.assertLess(took, 2.0, f"took {took:.3f}s")
        if os.environ.get("PERMA_TEST_TIMING"):
            print(f"\n  context-meter on a {self.transcript.stat().st_size >> 20} MB transcript, "
                  f"nothing in the last 8 MB: {took * 1000:.0f} ms")


if __name__ == "__main__":
    unittest.main()
