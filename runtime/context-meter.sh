#!/usr/bin/env bash
# Permanence context meter (UserPromptSubmit hook) — says when this session's context is getting full.
# ---------------------------------------------------------------------------------
# Why: a session cannot see how full its context is, so "time to compact" was a guess. This hook
# reads the session's own transcript, finds the last main-thread assistant message, and adds up the
# input tokens it was sent (input + cache read + cache creation). That is how full the context was
# on the last turn. At or above the threshold it prints one line into context; below it, nothing.
#
# Its own script, not part of session-load.sh: session-load runs once per session and only in a
# registered workspace (it exits early otherwise). The meter must run on every prompt, in every
# workspace. Kept apart, each one stays simple and a fault in one cannot silence the other.
#
# Threshold: 60% by default. runtime/.context-warn (one line: a whole number 1-100, the percent)
# overrides it; "off" switches the meter off. Any other value is ignored and 60 is used.
#
# Window sizes: the table in the Python below, from Anthropic's docs (checked 2026-11-15):
#   https://platform.claude.com/docs/en/about-claude/models/overview (context window per model)
#   https://code.claude.com/docs/en/model-config (Extended context; Turn off 1M context)
# Opus 4.6 and Sonnet 4.6 run at 200k in Claude Code unless picked with [1m], and the transcript does
# not record the suffix, so for them the meter assumes 200k until the count passes 200k, then 1M.
# CLAUDE_CODE_DISABLE_1M_CONTEXT=1 means every model runs at 200k, as Claude Code itself does.
# A model not in the table prints nothing.
#
# Fail silent: no python3, no transcript, bad JSON, a missing field — all print nothing, exit 0.
# It must never block a prompt. It reads the transcript from its end, at most 8 MB.
PERMA="${PERMA_DIR:-$HOME/permanence}"
command -v python3 >/dev/null 2>&1 || exit 0
WARN="$(grep -v '^[[:space:]]*$' "$PERMA/runtime/.context-warn" 2>/dev/null | head -n1 | tr -d '[:space:]')"

# The program is passed with -c, so the hook's JSON stays on stdin for it to read.
METER=$(cat <<'PY'
import json, os, sys

CHUNK, LIMIT = 1 << 20, 8 << 20   # read backwards 1 MB at a time, 8 MB at most
M, K200 = 1000000, 200000
NATIVE_1M = ("claude-fable-", "claude-mythos-", "claude-opus-5", "claude-sonnet-5",
             "claude-haiku-5-5", "claude-opus-4-8", "claude-opus-4-7")
ONE_M_ONLY_WITH_SUFFIX = ("claude-opus-4-6", "claude-sonnet-4-6")
WINDOW_200K = ("claude-opus-4-5", "claude-opus-4-1", "claude-opus-4-2025", "claude-opus-4@",
               "claude-sonnet-4-5", "claude-sonnet-4-2025", "claude-sonnet-4@", "claude-haiku-4-5")


def window_for(model, used):
    m = model.lower()
    known = any(p in m for p in NATIVE_1M + ONE_M_ONLY_WITH_SUFFIX + WINDOW_200K)
    if not known:
        return None
    if os.environ.get("CLAUDE_CODE_DISABLE_1M_CONTEXT", "").lower() in ("1", "true"):
        return K200
    if "[1m]" in m or any(p in m for p in NATIVE_1M):
        return M
    if any(p in m for p in ONE_M_ONLY_WITH_SUFFIX):
        return M if used > K200 else K200
    return K200


def read_line(line):
    """'stop' at a compaction boundary (the last count is from before it); (model, used) for a
    main-thread assistant message with usage; None for anything else."""
    if b'"assistant"' not in line and b'"compact_boundary"' not in line:
        return None
    try:
        d = json.loads(line)
    except ValueError:
        return None
    if not isinstance(d, dict) or d.get("isSidechain"):
        return None
    if d.get("type") == "system" and d.get("subtype") == "compact_boundary":
        return "stop"
    msg = d.get("message")
    if d.get("type") != "assistant" or not isinstance(msg, dict):
        return None
    model, usage = msg.get("model"), msg.get("usage")
    if not isinstance(model, str) or model.startswith("<") or not isinstance(usage, dict):
        return None
    parts = [usage.get(k) or 0 for k in
             ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")]
    if not all(isinstance(p, int) for p in parts) or sum(parts) <= 0:
        return None
    return model, sum(parts)


def last_main_turn(path):
    with open(path, "rb") as f:
        f.seek(0, 2)
        pos, carry, done = f.tell(), b"", 0
        while pos > 0 and done < LIMIT:
            n = min(CHUNK, pos)
            pos -= n
            f.seek(pos)
            lines = (f.read(n) + carry).split(b"\n")
            done += n
            carry = lines.pop(0) if pos > 0 else b""   # may be cut; finished by the next chunk
            for line in reversed(lines):
                got = read_line(line)
                if got == "stop":
                    return None
                if got:
                    return got
    return None


def main():
    raw = sys.argv[1] if len(sys.argv) > 1 else ""
    if raw.lower() == "off":
        return
    threshold = int(raw) if raw in {str(n) for n in range(1, 101)} else 60   # "050" is not a value
    hook = json.load(sys.stdin)
    path = hook.get("transcript_path") if isinstance(hook, dict) else None
    if not isinstance(path, str) or not os.path.isfile(path):
        return
    found = last_main_turn(path)
    if not found:
        return
    model, used = found
    window = window_for(model, used)
    if not window or used * 100 < threshold * window:
        return
    label = "1M" if window == M else f"{window // 1000}k"
    print(f"[perma] context {used * 100 // window}% used ({used // 1000}k of {label}): at the next "
          "natural break, write back to the stream, then ask the owner to /compact.")


try:
    main()
except BaseException:
    pass
PY
)
python3 -c "$METER" "$WARN" 2>/dev/null
exit 0
