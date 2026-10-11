"""Role resolution for the project team: the one implementation of the rules in docs/PROJECT-TEAM.md, "Roles".

Used by team-preflight.py (check 5) and the agent-roles hook. Standard library only.

A dispatch names `<job>:<role>` or `<role>`. Resolution checks three levels in order: the repo
binding's `roles`, the owner's `_personal/agent-roles.json`, the shipped `runtime/agent-roles.json`.
At each level the key `<job>:<role>` is tried first, then `<role>`. A level matches when it names an
agent installed for the working directory; a level that names only agents not installed is skipped,
and the skip is reported. The first match wins. When nothing matches, a review role resolves to the
built-in `general-purpose`; any other role is left to the session.
"""
import json
import os
import signal
import subprocess
from pathlib import Path

BUILT_IN = {"general-purpose", "Explore", "Plan", "claude-code-guide", "statusline-setup", "claude", "fork"}
REVIEW_ROLES = {"reviewer", "code-review"}
REVIEW_FALLBACK = "general-purpose"
RESOLVE_TIMEOUT = 2  # seconds; the hook's whole budget is 10


def frontmatter_name(path):
    try:
        lines = open(path).read().split("\n")
    except OSError:
        return None
    if not lines or lines[0].strip() != "---":
        return path.stem
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line.startswith("name:"):
            return line.split(":", 1)[1].strip().strip("'\"")
    return path.stem


def enabled_plugins(cwd):
    enabled = {}
    for p in (Path.home() / ".claude" / "settings.json", Path(cwd) / ".claude" / "settings.json",
              Path(cwd) / ".claude" / "settings.local.json"):
        try:
            enabled.update(json.load(open(p)).get("enabledPlugins", {}))
        except (OSError, ValueError):
            pass
    return [k for k, v in enabled.items() if v]


def installed_agents(cwd):
    """Every agent name this session could dispatch: built-ins, user, project, enabled plugins."""
    names = set(BUILT_IN)
    for d in (Path.home() / ".claude" / "agents", Path(cwd) / ".claude" / "agents"):
        for f in d.glob("*.md"):
            n = frontmatter_name(f)
            if n:
                names.add(n)
    try:
        installs = json.load(open(Path.home() / ".claude" / "plugins" / "installed_plugins.json"))["plugins"]
    except (OSError, ValueError, KeyError):
        installs = {}
    for key in enabled_plugins(cwd):
        entries = installs.get(key, [])
        # a project-scope install for this folder wins over the user-scope one
        pick = next((e for e in entries if e.get("scope") == "project"
                     and str(cwd).startswith(e.get("projectPath", "\0"))), None)
        pick = pick or next((e for e in entries if e.get("scope") == "user"), None)
        if not pick:
            continue
        plugin = key.split("@")[0]
        for f in Path(pick["installPath"], "agents").glob("*.md"):
            n = frontmatter_name(f)
            if n:
                names.add(f"{plugin}:{n}")
    return names


def table_roles(path):
    try:
        roles = json.loads(Path(path).read_text()).get("roles")
    except (OSError, ValueError, AttributeError):
        return {}
    return roles if isinstance(roles, dict) else {}


def providers(entry):
    """A binding entry is an agent name, a list of names, or the table form {"providers": [...]}
    (which may also set a model); a table entry is {"providers": [...]}.
    Anything else names no agent (a string `providers` is not read character by character)."""
    if isinstance(entry, dict):
        entry = entry.get("providers")
    elif isinstance(entry, str):
        return [entry]
    return [p for p in entry if isinstance(p, str)] if isinstance(entry, list) else []


def stream_of(perma, path, log=None):
    """The stream registered for path in _meta/REGISTRY.md, or None (perma-meta counts as none).

    A resolver that is missing, not executable, slow or broken gives None, so the binding level is
    skipped and the other levels still resolve; the reason goes to log when one is given."""
    try:
        p = subprocess.Popen([str(Path(perma) / "runtime" / "resolve-stream.sh"), str(path)],
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
                             start_new_session=True)
        try:
            out, _ = p.communicate(timeout=RESOLVE_TIMEOUT)
        except subprocess.TimeoutExpired:
            # kill the whole group: a child left holding the pipe would block the read
            os.killpg(p.pid, signal.SIGKILL)
            p.communicate()
            raise
    except (OSError, subprocess.SubprocessError, ValueError) as e:
        if log:
            log(f"SKIP binding level: cannot resolve the stream for {path} ({e!r})")
        return None
    stream = out.strip()
    return None if not stream or stream == "perma-meta" else stream


def binding_path(perma, path, log=None):
    stream = stream_of(perma, path, log)
    return (Path(perma) / stream / "repo" / "binding.json") if stream else None, stream


def load_binding(perma, path, log=None):
    """The binding for the repo at path, or {} when there is none or it does not parse."""
    bpath, _ = binding_path(perma, path, log)
    try:
        b = json.loads(bpath.read_text()) if bpath else {}
    except (OSError, ValueError):
        return {}
    return b if isinstance(b, dict) else {}


def shipped_table(perma):
    """The shipped table. Before the move-2 swap the new one waits beside the live one as
    agent-roles.next.json; preflight reads it so it agrees with the hook after the swap."""
    nxt = Path(perma) / "runtime" / "agent-roles.next.json"
    return nxt if nxt.is_file() else Path(perma) / "runtime" / "agent-roles.json"


def personal_table(perma):
    return Path(perma) / "_personal" / "agent-roles.json"


def levels(perma, binding):
    """The three resolution levels, in order, as (label, table)."""
    roles = binding.get("roles") if isinstance(binding, dict) else None
    shipped = shipped_table(perma)
    return [("binding roles", roles if isinstance(roles, dict) else {}),
            ("_personal/agent-roles.json", table_roles(personal_table(perma))),
            (f"runtime/{shipped.name}", table_roles(shipped))]


def resolve(spec, lvls, have):
    """Resolve `<job>:<role>` or `<role>`.

    Returns {agent, where, key, skipped, fallback, entry}: agent is None when the session does it;
    skipped lists (where, key, providers) for each level passed over; fallback is None,
    "general-purpose" or "session". entry is the dispatched role's own table entry (first in
    level order, job-qualified key first), whatever level matched: a resolved agent that no table
    lists as a provider takes that entry's model, and nothing else from it."""
    job, _, role = spec.rpartition(":")
    keys = [f"{job}:{role}", role] if job else [role]
    res = {"agent": None, "where": None, "key": None, "skipped": [], "fallback": None,
           "entry": next((t[k] for _, t in lvls for k in keys if isinstance(t.get(k), dict)), None)}
    for where, table in lvls:
        for key in keys:
            if key not in table:
                continue
            provs = providers(table[key])
            pick = next((p for p in provs if p in have), None)
            if pick:
                res.update(agent=pick, where=where, key=key)
                return res
            if provs:
                res["skipped"].append((where, key, provs))
    if role in REVIEW_ROLES:
        res.update(agent=REVIEW_FALLBACK, fallback=REVIEW_FALLBACK)
    else:
        res["fallback"] = "session"
    return res


def known_role(spec, lvls):
    job, _, role = spec.rpartition(":")
    keys = [f"{job}:{role}", role] if job else [role]
    return any(k in table for _, table in lvls for k in keys)


def role_of(agent_type, tables):
    """(role name, entry) of the first table entry listing agent_type as a provider."""
    if not agent_type:
        return None, None
    for table in tables:
        for name, r in table.items():
            if not isinstance(r, dict):
                continue
            for p in providers(r):
                # a plugin agent may be reported with or without its plugin prefix
                if agent_type == p or p.split(":")[-1] == agent_type:
                    return name, r
    return None, None
