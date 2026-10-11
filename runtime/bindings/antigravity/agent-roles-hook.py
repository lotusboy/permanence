#!/usr/bin/env python3
"""Agent roles on Antigravity — a PreToolUse hook on `invoke_subagent`.

The Claude Code hook is runtime/agent-roles.py. This is the same job for Antigravity's subagent
tool, using the same rules (runtime/team_roles.py) and the same role tables. It reads the hook
input on stdin and prints one JSON object.

What it does to each entry of the call's `Subagents` list:

  - `TypeName: "role:<role>"` or `"role:<job>:<role>"` is resolved through the repo binding, the
    owner's own table and the shipped table, and replaced by the agent that fills the role. A role
    nothing fills is refused, with a reason the launching agent can read.
  - A role's `prompt_append` is added to the entry's `Prompt`, once.
  - A plain agent name that the SHIPPED table lists is touched only in a repository that has a
    binding. The owner's own table applies everywhere.

What it does NOT do, because Antigravity gives a hook no way to (docs/TOOL-SUPPORT.md):

  - force a model per dispatch. The model is set in each installed agent's own file instead.
  - cap what a role's agent spawns itself, or send an agent back for a missing run record: no
    hook input says which agent is the parent, or that a stopping conversation is a subagent.

It fails open: any error allows the call unchanged, and is logged to runtime/logs/agent-roles.log.
Antigravity treats a missing or empty decision as a refusal, so every path prints an explicit one.
"""
import json
import os
import sys
import time
from pathlib import Path

RUNTIME = Path(__file__).resolve().parent.parent.parent
PERMA = Path(os.environ.get("PERMA_DIR") or RUNTIME.parent)
LOG = PERMA / "runtime" / "logs" / "agent-roles.log"
MARKER = "[agent-roles]"
DEFAULT_REVIEWS = "axis/runs/"
# Antigravity has no agent called general-purpose. `self` starts a fresh conversation of the
# default agent, which is what a review that must not fall to the working session needs.
GENERAL = {"general-purpose": "self"}
ALLOW = {"decision": "allow"}


def log(msg):
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} antigravity {msg}\n")
    except OSError:
        pass


def reviews_folder(binding):
    v = binding.get("reviews", DEFAULT_REVIEWS) if isinstance(binding, dict) else DEFAULT_REVIEWS
    if not isinstance(v, str) or not v.strip() or os.path.isabs(v) or ".." in Path(v).parts:
        return DEFAULT_REVIEWS
    return v.rstrip("/") + "/"


def decide(d, team_roles):
    call = d.get("toolCall") or {}
    if call.get("name") != "invoke_subagent":
        return ALLOW
    subs = (call.get("args") or {}).get("Subagents")
    if not isinstance(subs, list):
        return ALLOW
    roots = d.get("workspacePaths") or []
    cwd = roots[0] if roots and isinstance(roots[0], str) else os.getcwd()
    os.environ["PERMA_HARNESS"] = "antigravity"
    have = team_roles.installed_agents(cwd)
    tabs = [team_roles.table_roles(team_roles.personal_table(PERMA)),
            team_roles.table_roles(team_roles.shipped_table(PERMA))]
    binding = None
    notes = []
    out = []
    for sub in subs:
        if not isinstance(sub, dict) or not isinstance(sub.get("TypeName"), str):
            out.append(sub)
            continue
        sub = dict(sub)
        st = sub["TypeName"]
        role_entry = None
        use = tabs
        if st.startswith("role:"):
            spec = st[5:]
            if binding is None:
                binding = team_roles.load_binding(PERMA, cwd, log)
            lvls = team_roles.levels(PERMA, binding)
            res = team_roles.resolve(spec, lvls, have)
            for where, key, provs in res["skipped"]:
                log(f"SKIP role:{spec}: {where} key '{key}' names {provs}, not installed")
            if not res["agent"]:
                what = "no installed agent fills it" if team_roles.known_role(spec, lvls) else "no level names it"
                reason = (f"Permanence agent-roles: role '{spec}' is unresolved ({what}). "
                          f"Do the work in this session instead, behind the same gates.")
                log(f"DENY {reason}")
                return {"decision": "deny", "reason": reason}
            st = res["agent"]
            sub["TypeName"] = GENERAL.get(st, st)
            notes.append(f"role:{spec} -> {sub['TypeName']}")
            role_entry = res["entry"]
        elif team_roles.role_of(st, tabs)[1]:
            if binding is None:
                binding = team_roles.load_binding(PERMA, cwd, log)
            if not binding:
                use = tabs[:1]
        _, r = team_roles.role_of(st, use)
        r = r or role_entry
        extra = (r or {}).get("prompt_append")
        if isinstance(extra, str) and extra and MARKER not in str(sub.get("Prompt") or ""):
            if "{reviews}" in extra:
                if binding is None:
                    binding = team_roles.load_binding(PERMA, cwd, log)
                extra = extra.replace("{reviews}", reviews_folder(binding))
            sub["Prompt"] = str(sub.get("Prompt") or "") + f"\n\n{MARKER}\n{extra}"
            notes.append(f"{st}: prompt_append added")
        out.append(sub)
    if not notes:
        return ALLOW
    log("REWRITE " + "; ".join(notes))
    return {"decision": "allow", "overwrite": {"Subagents": out}}


def main():
    try:
        d = json.loads(sys.stdin.read() or "{}")
        if not isinstance(d, dict):
            raise ValueError("hook input is not an object")
        sys.path.insert(0, str(RUNTIME))
        import team_roles
        result = decide(d, team_roles)
    except Exception as e:  # fail open, always with an explicit decision
        log(f"ERROR {e!r}")
        result = ALLOW
    print(json.dumps(result))


if __name__ == "__main__":
    main()
