#!/usr/bin/env python3
"""Agent roles — enforce the role tables on every agent dispatch.

Three entry points, all wired by bindings/claude-code/wire:

  PreToolUse (matcher Agent)  stdin = hook JSON
      - subagent_type 'role:<job>:<role>' or 'role:<role>' is resolved by team_roles (design
        docs/PROJECT-TEAM.md, "Roles"): the repo binding's roles, then _personal/agent-roles.json,
        then runtime/agent-roles.json. A review role nothing fills goes to general-purpose; any
        other unfilled role is denied, and the session does the work itself.
      - a dispatch of a role's provider gets the role's model and prompt_append.
      - an agent spawned BY a role's provider is held to that role's nested_model.
  SubagentStop                stdin = hook JSON
      - a role with run_record: the agent is sent back once if it wrote no record folder under the
        binding's `reviews` (default axis/runs/).
  --check-new                 (SessionStart) print agents installed since the last check, once.

Measured behaviour this relies on (2026-09-30, in a live session): PreToolUse fires for Agent calls
made inside subagents and carries agent_id/agent_type of the caller; updatedInput rewrites prompt
and model; SubagentStop {"decision":"block"} makes the agent continue, with stop_hook_active on
re-entry.

Fail-open by design: any error here lets the dispatch through unchanged, so a broken table can
never stop work. Every change it makes is logged to runtime/logs/agent-roles.log.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

PERMA = Path(os.environ.get("PERMA_DIR", Path.home() / "permanence"))
SEEN = PERMA / "runtime" / ".agent-roles-seen"
LOG = PERMA / "runtime" / "logs" / "agent-roles.log"
MARKER = "[perma:agent-roles]"
APPROVED = "[model-approved]"
DEFAULT_REVIEWS = "axis/runs/"


def log(msg):
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG, "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")
    except OSError:
        pass


try:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import team_roles
except Exception as e:  # fail open: without the module every dispatch passes unchanged
    log(f"ERROR import team_roles: {e!r}")
    team_roles = None


def tables():
    """Role entries in lookup order: the owner's overrides, then the shipped table."""
    return [team_roles.table_roles(team_roles.personal_table(PERMA)),
            team_roles.table_roles(team_roles.shipped_table(PERMA))]


def reviews_folder(binding):
    """(folder, None) for the binding's `reviews`, or (None, reason) when it is not a safe path."""
    v = binding.get("reviews", DEFAULT_REVIEWS)
    if not isinstance(v, str) or not v.strip():
        return None, f"reviews {v!r} is not a path"
    if os.path.isabs(v) or ".." in Path(v).parts:
        return None, f"reviews {v!r} is outside the repository"
    return v.rstrip("/") + "/", None


def is_above(model, ceiling):
    """True when model (None = inherit, which may be opus) is above the ceiling."""
    order = {"haiku": 0, "sonnet": 1, "opus": 2, "fable": 3}
    m = next((k for k in order if model and k in model), None)
    c = next((k for k in order if k in ceiling), None)
    if c is None:
        return False
    return m is None or order[m] > order[c]


def pre_tool_use(d):
    ti = dict(d.get("tool_input") or {})
    tabs = tables()
    st = ti.get("subagent_type") or "general-purpose"
    cwd = d.get("cwd") or os.getcwd()
    notes = []
    role_entry = None
    binding = None

    if st.startswith("role:"):
        spec = st[5:]
        binding = team_roles.load_binding(PERMA, cwd, log)
        lvls = team_roles.levels(PERMA, binding)
        res = team_roles.resolve(spec, lvls, team_roles.installed_agents(cwd))
        for where, key, provs in res["skipped"]:
            log(f"SKIP role:{spec}: {where} key '{key}' names {provs}, not installed")
        if not res["agent"]:
            what = "no installed agent fills it" if team_roles.known_role(spec, lvls) else "no level names it"
            reason = (f"Permanence agent-roles: role '{spec}' is unresolved ({what}). "
                      f"Do the work in this session instead, behind the same gates.")
            log(f"DENY {reason}")
            return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                           "permissionDecision": "deny",
                                           "permissionDecisionReason": reason}}
        ti["subagent_type"] = st = res["agent"]
        src = "fallback, no level matched" if res["fallback"] else f"{res['where']} key '{res['key']}'"
        notes.append(f"role:{spec} -> {st} ({src})")
        role_entry = res["entry"]

    rname, r = team_roles.role_of(st, tabs)
    if not r and role_entry:
        # an agent no table lists takes only the dispatched role's model
        r = {"model": role_entry.get("model")}
    if r:
        want = r.get("model")
        if want and ti.get("model") != want and APPROVED not in (ti.get("description") or ""):
            notes.append(f"model {ti.get('model')} -> {want}")
            ti["model"] = want
        extra = r.get("prompt_append")
        if isinstance(extra, str) and extra and MARKER not in (ti.get("prompt") or ""):
            if "{reviews}" in extra:
                if binding is None:
                    binding = team_roles.load_binding(PERMA, cwd, log)
                extra = extra.replace("{reviews}", reviews_folder(binding)[0] or DEFAULT_REVIEWS)
            ti["prompt"] = (ti.get("prompt") or "") + f"\n\n{MARKER}\n{extra}"
            notes.append("prompt_append added")

    parent = d.get("agent_type")
    if parent:
        pname, pr = team_roles.role_of(parent, tabs)
        cap = (pr or {}).get("nested_model")
        if cap and is_above(ti.get("model"), cap):
            notes.append(f"nested spawn by {parent}: model {ti.get('model')} -> {cap}")
            ti["model"] = cap

    if not notes:
        return None
    log(f"REWRITE {st} ({ti.get('description', '')}): " + "; ".join(notes))
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                   "permissionDecision": "allow",
                                   "updatedInput": ti}}


def repo_root(cwd):
    try:
        out = subprocess.run(["git", "-C", cwd, "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, timeout=2)
        if out.returncode == 0:
            return Path(out.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        pass
    return Path(cwd)


def subagent_stop(d):
    rname, r = team_roles.role_of(d.get("agent_type"), tables())
    if not r or not r.get("run_record"):
        return None
    try:
        st = os.stat(d["agent_transcript_path"])
        started = getattr(st, "st_birthtime", st.st_mtime)
    except (KeyError, OSError):
        started = time.time() - 3600
    cwd = d.get("cwd") or os.getcwd()
    folder, why = reviews_folder(team_roles.load_binding(PERMA, cwd, log))
    if not folder:
        log(f"RUN-RECORD check skipped for {d.get('agent_type')}: binding {why}")
        return None
    runs = repo_root(cwd) / folder
    fresh = [p for p in runs.glob("*/*") if p.is_file() and p.stat().st_mtime >= started - 5] if runs.is_dir() else []
    if fresh:
        log(f"RUN-RECORD ok for {d.get('agent_type')}: {fresh[0].parent.name}")
        return None
    if not d.get("stop_hook_active"):
        log(f"RUN-RECORD missing for {d.get('agent_type')} — sent back")
        return {"decision": "block",
                "reason": f"Permanence agent-roles: role '{rname}' requires a run record. Before stopping, "
                          f"write {folder}<YYYY-MM-DD>-<subject>-<protocol>/ at the repository root with "
                          f"contract.md and findings.md, as your dispatch prompt describes."}
    log(f"RUN-RECORD still missing for {d.get('agent_type')} — let it stop, told the user")
    return {"systemMessage": f"Permanence agent-roles: {d.get('agent_type')} stopped without writing a record under {folder}."}


def check_new(cwd):
    have = team_roles.installed_agents(cwd)
    entries = [(rn, r) for t in tables() for rn, r in t.items() if isinstance(r, dict)]
    known = {p for _, r in entries for p in team_roles.providers(r)}
    try:
        seen = set(SEEN.read_text().split())
        first = False
    except OSError:
        seen, first = set(), True
    # A provider that has gone missing while its plugin is still installed is almost always a rename
    # upstream. Said every session until the table is fixed. A plugin that is not installed at all is
    # the normal case for someone without it, so that stays silent.
    plugins = {n.split(":")[0] for n in have if ":" in n}
    gone = [(rn, p) for rn, r in entries for p in team_roles.providers(r)
            if p not in have and (":" not in p or p.split(":")[0] in plugins)]
    for rn, p in gone:
        print(f"[perma] Agent role '{rn}': provider '{p}' is not installed"
              + (f", but the {p.split(':')[0]} plugin is — it was probably renamed or removed. "
                 if ":" in p else " — re-run ~/permanence/runtime/install.sh. ")
              + "Tell the owner, and offer to update the role table that names it "
                "(runtime/agent-roles.json or _personal/agent-roles.json).")
    new = sorted(have - seen - known - team_roles.BUILT_IN)
    if new and not first:
        print("[perma] New agent(s) installed since the last check: " + ", ".join(new) + ". "
              "If one does the same job as a Permanence role (runtime/agent-roles.json), tell the owner and "
              "offer to add it to that role's providers. PM: record this in WIP.md — it is shown only once.")
    SEEN.write_text("\n".join(sorted(seen | have)) + "\n")


def main():
    if team_roles is None:
        return
    if "--check-new" in sys.argv:
        try:
            check_new(os.getcwd())
        except Exception as e:  # never break session start
            log(f"ERROR check-new: {e!r}")
        return
    try:
        d = json.load(sys.stdin)
        ev = d.get("hook_event_name")
        out = pre_tool_use(d) if ev == "PreToolUse" else subagent_stop(d) if ev == "SubagentStop" else None
    except Exception as e:  # fail open
        log(f"ERROR: {e!r}")
        out = None
    if out:
        print(json.dumps(out))


if __name__ == "__main__":
    main()
