#!/usr/bin/env python3
"""Install Permanence's shipped agents as Antigravity custom agents. Called by this binding's wire.

    agents-install.py <runtime/agents folder> <~/.gemini/config/agents folder>

Each runtime/agents/<name>.md (a Claude Code agent file) becomes <dst>/<name>/agent.md, the form
Antigravity loads: YAML frontmatter, then the instructions under one H1. Verified against
Antigravity CLI 1.2.2 (design/project-team-on-other-harnesses.md).

  - tools: Claude Code tool names are mapped to Antigravity's. `send_message` is always added: it
    is how a subagent reports back.
  - model: Antigravity takes a tier, not a model name. fable and opus -> pro; sonnet and haiku -> flash.
  - The file ends with an installed-from marker. An agent folder of the owner's own with the same
    name (no marker naming it) is left exactly as it is and reported. An installed agent whose
    source is gone has its agent.md removed; the folder goes too only when nothing else is in it.

Exit 0, or 1 when an agent could not be written.
"""
import os
import re
import shutil
import sys

TOOLS = {
    "Read": ["view_file"],
    "Grep": ["grep_search"],
    "Glob": ["find_by_name", "list_dir"],
    "Bash": ["run_command"],
    "Edit": ["replace_file_content"],
    "Write": ["write_to_file"],
    "WebFetch": ["read_url_content"],
    "WebSearch": ["search_web"],
}
TIER = {"opus": "pro", "fable": "pro", "sonnet": "flash", "haiku": "flash"}
MARK = "installed-from: ~/permanence/runtime/agents/"


def parse(text):
    """(fields, body). Reads the few frontmatter keys an agent file uses; folded `>-` values too."""
    m = re.match(r"^﻿?---\s*\n(.*?)\n---\s*\n?", text, re.DOTALL)
    if not m:
        return {}, text
    fields, key = {}, None
    for line in m.group(1).split("\n"):
        km = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
        if km:
            key, val = km.group(1), km.group(2).strip()
            fields[key] = "" if val in (">-", ">", "|", "|-") else val.strip("'\"")
        elif key and line.startswith((" ", "\t")):
            fields[key] = (fields[key] + " " + line.strip()).strip()
    return fields, text[m.end():]


def translate(name, text):
    fields, body = parse(text)
    tools = []
    for t in [x.strip() for x in fields.get("tools", "").split(",") if x.strip()]:
        for mapped in TOOLS.get(t, []):
            if mapped not in tools:
                tools.append(mapped)
    out = ["---", f"name: {name}", "description: " + _quote(fields.get("description") or f"Permanence agent {name}.")]
    if tools:
        out.append("tools:")
        out += [f"    - {t}" for t in tools + ["send_message"]]
    out += ["subagent: true", f"model: {TIER.get(fields.get('model', ''), 'inherit')}", "---", "",
            "# Agent System Instructions", "", body.strip(), ""]
    return "\n".join(out)


def _quote(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def ours(path, name):
    try:
        last = open(path, encoding="utf-8", errors="replace").read().rstrip().split("\n")[-1]
    except OSError:
        return False
    return f"{MARK}{name}.md " in last


def main():
    src, dst = sys.argv[1], sys.argv[2]
    failed = False
    names = sorted(f[:-3] for f in os.listdir(src) if f.endswith(".md")) if os.path.isdir(src) else []
    for name in names:
        folder = os.path.join(dst, name)
        target = os.path.join(folder, "agent.md")
        if os.path.isdir(folder) and os.listdir(folder) and not ours(target, name):
            print(f"  agent: {name} — ATTENTION: you already have your own agent with this name; "
                  f"left as it is, Permanence's not installed")
            continue
        try:
            text = open(os.path.join(src, name + ".md"), encoding="utf-8").read()
            os.makedirs(folder, exist_ok=True)
            with open(target, "w", encoding="utf-8") as f:
                f.write(translate(name, text) + f"\n<!-- {MARK}{name}.md — edit the source in Permanence, "
                        f"then re-run ~/permanence/runtime/install.sh -->\n")
            print(f"  agent: {name}")
        except (OSError, ValueError) as e:
            print(f"  agent: {name} — FAILED to write ({e})")
            failed = True
    if os.path.isdir(dst):
        for entry in sorted(os.listdir(dst)):
            folder = os.path.join(dst, entry)
            target = os.path.join(folder, "agent.md")
            if entry in names or not os.path.isdir(folder) or not ours(target, entry):
                continue
            if os.listdir(folder) == ["agent.md"]:
                shutil.rmtree(folder)
                print(f"  agent: {entry} — removed (no longer in runtime/agents/)")
            else:
                os.remove(target)
                print(f"  agent: {entry} — agent.md removed (no longer in runtime/agents/); your other files kept")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
