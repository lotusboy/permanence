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
# not record the suffix. The meter looks for the model's ID in ANTHROPIC_MODEL, ANTHROPIC_DEFAULT_OPUS_MODEL,
# ANTHROPIC_DEFAULT_SONNET_MODEL, then `model` in the settings files (local, shared project, user): the
# first that names it decides, with or without [1m]. If none does, a count above 200k means 1M, and at or
# below it the line says "of 200k, or 1M if you chose [1m]".
# CLAUDE_CODE_DISABLE_1M_CONTEXT=1 means every model runs at 200k, as Claude Code itself does.
# A model not in the table prints nothing, and so does a count above the window.
#
# Auto-compact window: Claude Code compacts at it, so the meter measures against the smaller of the model
# window and that window (https://code.claude.com/docs/en/model-config, "Set the auto-compact window";
# https://code.claude.com/docs/en/settings, "Settings precedence"; settings-reference, "modelSettings").
# Order: CLAUDE_CODE_AUTO_COMPACT_WINDOW when it is a usable size, then the settings files in precedence
# order (.claude/settings.local.json at the project's git root, then .claude/settings.json in the project
# folder, then the user file), each file's modelSettings.<model>.autoCompactWindow before its top-level
# autoCompactWindow. "auto", or a value it cannot read, means the model window. Not seen by a hook:
# --autocompact and managed settings.
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


def settings_files(cwd):
    """The settings files a hook can read, highest precedence first: project local, shared project, user."""
    base = os.environ.get("CLAUDE_PROJECT_DIR") or cwd or ""
    root, d = None, base
    while d and d != os.path.dirname(d):
        if os.path.exists(os.path.join(d, ".git")):
            root = d
            break
        d = os.path.dirname(d)
    files = [os.path.join(root, ".claude", "settings.local.json")] if root else []
    if base:
        files += [os.path.join(base, ".claude", "settings.local.json"), os.path.join(base, ".claude", "settings.json")]
    user = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
    files.append(os.path.join(user, "settings.json"))
    out = []
    for f in dict.fromkeys(files):
        try:
            if not os.path.isfile(f):  # never open a FIFO or device: it could hang the hook
                continue
            with open(f) as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                out.append(data)
        except (OSError, ValueError):
            pass
    return out


def tokens(value, env=False):
    """A window size in tokens: 100k-1M, clamped as Claude Code clamps it; None when unusable.
    The variable takes a plain count or a k/M suffix; a settings value is a number."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        try:
            n = int(value)
        except (ValueError, OverflowError):  # NaN, Infinity, 1e400
            return None
    elif env and isinstance(value, str):
        v = value.strip().lower()
        mult = 1000 if v.endswith("k") else M if v.endswith("m") else 1
        try:
            n = int(float(v[:-1] if mult > 1 else v) * mult)
        except (ValueError, OverflowError):
            return None
    else:
        return None
    return min(max(n, 100000), M) if n > 0 else None


def auto_compact(model, files):
    raw = os.environ.get("CLAUDE_CODE_AUTO_COMPACT_WINDOW")
    if raw:
        n = tokens(raw, env=True)
        if n:
            return n
    m = model.lower().replace("[1m]", "")
    for data in files:
        per = data.get("modelSettings")
        keys = [k for k in per if isinstance(k, str) and k.lower() in m] if isinstance(per, dict) else []
        entry = per[max(keys, key=len)] if keys else None
        for value in ((entry or {}).get("autoCompactWindow") if isinstance(entry, dict) else None,
                      data.get("autoCompactWindow")):
            if value == "auto":
                return None
            if value is not None:
                return tokens(value)
    return None


def chose_1m(base, files):
    """True or False when a configured model names this model, with or without [1m]; None if none does."""
    names = [os.environ.get(v) for v in ("ANTHROPIC_MODEL", "ANTHROPIC_DEFAULT_OPUS_MODEL",
                                         "ANTHROPIC_DEFAULT_SONNET_MODEL")]
    names += [d.get("model") for d in files]
    for name in names:
        if isinstance(name, str) and base in name.lower():
            return "[1m]" in name.lower()
    return None


def window_for(model, used, files):
    """(window in tokens, label) or None when the window is not known."""
    m = model.lower()
    if os.environ.get("CLAUDE_CODE_DISABLE_1M_CONTEXT", "").lower() in ("1", "true"):
        if any(p in m for p in NATIVE_1M + ONE_M_ONLY_WITH_SUFFIX + WINDOW_200K):
            return K200, "200k"
        return None
    if "[1m]" in m or any(p in m for p in NATIVE_1M):
        return M, "1M"
    base = next((p for p in ONE_M_ONLY_WITH_SUFFIX if p in m), None)
    if base:
        one_m = chose_1m(base, files)
        if one_m is None:
            return (M, "1M") if used > K200 else (K200, "200k, or 1M if you chose [1m]")
        return (M, "1M") if one_m else (K200, "200k")
    if any(p in m for p in WINDOW_200K):
        return K200, "200k"
    return None


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
    files = settings_files(hook.get("cwd") if isinstance(hook.get("cwd"), str) else "")
    sized = window_for(model, used, files)
    if not sized:
        return
    window, label = sized
    acw = auto_compact(model, files)
    if acw and acw < window:
        window, label = acw, f"{acw // 1000}k, the auto-compact window"
    if used > window or used * 100 < threshold * window:
        return
    print(f"[perma] context {used * 100 // window}% used ({used // 1000}k of {label}): at the next "
          "natural break, write back to the stream, if this workspace has one, then ask the owner to /compact.")


try:
    main()
except BaseException:
    pass
PY
)
python3 -c "$METER" "$WARN" 2>/dev/null
exit 0
