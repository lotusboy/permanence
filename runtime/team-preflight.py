#!/usr/bin/env python3
"""Team preflight: check a repository's binding before a team job or the health watch starts.

The checks are listed in docs/PROJECT-TEAM.md, "Preflight". Standard library only. Reads files and runs
read-only git commands; it never writes to the repository or the stream.

Usage:
  team-preflight.py refactor <part>      [--repo DIR] [--binding FILE]
  team-preflight.py change <work-order>  [--repo DIR] [--binding FILE]
  team-preflight.py health               [--repo DIR] [--binding FILE]
  team-preflight.py startup              [--repo DIR] [--binding FILE]

--repo defaults to the working directory. --binding replaces the stream's binding.json (for a
scratch copy); approvals.json is then read from the same folder.

Checks, in order: 1 binding exists; 2 it parses, has the fields its `owned` value requires, and
uses only the closed placeholder list; 3 every path field exists in the checkout; 4 every pointer
finds its key (prose gates are listed, not failed), and a generic-script signal is valid (a
missing script is a note, except for `refactor`, which runs the signal); 5 every
role the job dispatches resolves; 6 for a job when owned is false, an unconsumed approval of this
exact scope exists. `startup` runs checks 1-4 and exits 0 when the stream has no binding.

Prints one line per failure. Exits 1 on any failure, 0 otherwise.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import team_roles  # noqa: E402

PERMA = Path(os.environ.get("PERMA_DIR", Path.home() / "permanence"))
PLACEHOLDERS = {"root", "register", "id", "n", "date", "part", "name"}
REGEX_FIELDS = {("tracker", "id"), ("signal", "fix"), ("signal", "part")}
PATH_FIELDS = (("tracker", "file"), ("measure", "layerRules"), ("reviews",), ("leaveAlone",))
POINTER = re.compile(r"^([^\s#]+)#([^\s#]+)$")
JOB_ROLES = {"refactor": ["architect", "engineer", "reviewer"], "change": ["engineer", "reviewer"]}
GIT_ENV = dict(os.environ, GIT_OPTIONAL_LOCKS="0")


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, env=GIT_ENV)


def get(d, path):
    for k in path:
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d


def strings(node, path=()):
    """Every string value with its field path, skipping _about."""
    if isinstance(node, str):
        yield path, node
    elif isinstance(node, dict):
        for k, v in node.items():
            if k != "_about":
                yield from strings(v, path + (k,))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from strings(v, path + (i,))


def label(path):
    return ".".join(str(p) for p in path)


def find_binding(repo):
    path, stream = team_roles.binding_path(PERMA, repo)
    if not path:
        return None, f"no stream is registered for {repo} in _meta/REGISTRY.md"
    return path, f"stream {stream} has no repo/binding.json: the team does not apply to this repository"


def check_fields(b):
    fails = []
    if not isinstance(b.get("owned"), bool):
        return ["check 2: field 'owned' is missing or not true/false"]
    need = [("register",), ("signal",)]
    if b["owned"]:
        need += [("tracker", "file"), ("tracker", "id"), ("measure", "commands"),
                 ("gates", "byteIdentical"), ("gates", "predictedMoves", "gates"),
                 ("gates", "predictedMoves", "prediction"), ("branches", "refactor"),
                 ("branches", "change")]
    else:
        need += [("approver",)]
    fails += [f"check 2: required field '{label(p)}' is missing" for p in need if get(b, p) is None]
    for path, s in strings(b):
        if tuple(p for p in path if isinstance(p, str)) in REGEX_FIELDS:
            continue
        if re.search(r"<[^<>]*>", s):
            fails.append(f"check 2: field '{label(path)}' uses a '<...>' placeholder; the binding allows only '{{...}}' from the closed list")
        for ph in re.findall(r"\{([^{}]*)\}", s):
            if ph not in PLACEHOLDERS:
                fails.append(f"check 2: field '{label(path)}' uses placeholder '{{{ph}}}', which is not in the closed list")
    return fails


def check_paths(b, repo):
    fails = []
    root = repo.resolve()
    for path in PATH_FIELDS:
        val = get(b, path)
        for v in val if isinstance(val, list) else [] if val is None else [val]:
            if not isinstance(v, str) or not v.strip():
                fails.append(f"check 3: path field '{label(path)}' = {json.dumps(v)} is not a path")
                continue
            target = (repo / v.split("{", 1)[0]).resolve()
            if target != root and root not in target.parents:
                fails.append(f"check 3: path field '{label(path)}' = '{v}' is outside {repo}")
            elif not target.exists():
                fails.append(f"check 3: path field '{label(path)}' = '{v}' does not exist in {repo}")
    return fails


def yaml_block(lines, key):
    """Lines under a top-level `key:` line, up to the next top-level key; None if absent."""
    for i, line in enumerate(lines):
        if re.match(rf"^{re.escape(key)}:(\s|$)", line):
            end = next((j for j in range(i + 1, len(lines)) if re.match(r"^[^\s#-][^:]*:", lines[j])), len(lines))
            return lines[i + 1:end]
    return None


def yaml_items(block):
    """{id: command's first word or None} for each `- id:` item in a YAML block, read as text."""
    items, cur, want_next = {}, None, False
    for line in block:
        m = re.match(r"^\s*-\s+id:\s*['\"]?([^'\"\s#]+)", line)
        if m:
            cur, want_next = m.group(1), False
            items[cur] = None
            continue
        if cur is None or not line.strip() or line.strip().startswith("#"):
            continue
        if want_next:
            items[cur], want_next = line.split()[0], False
            continue
        m = re.match(r"^\s+command:\s*(.*)$", line)
        if m:
            val = m.group(1).strip().strip("'\"")
            if val in ("", ">", ">-", "|", "|-"):
                want_next = True
            else:
                items[cur] = val.split()[0]
    return items


def runnable(word, repo):
    if not word:
        return False
    word = word.replace("{root}/", "")
    return bool(shutil.which(word)) or (repo / word).is_file() or (repo / ".venv" / "bin" / word).is_file()


def resolve_pointer(ptr, repo):
    """(error or None, {gate id: first word}) for a `file#key` or `file#key.id` pointer."""
    fname, ref = POINTER.match(ptr).groups()
    key, _, item = ref.partition(".")
    target = repo / fname
    if not target.is_file():
        return f"file '{fname}' does not exist", {}
    if target.suffix == ".json":
        try:
            data = json.loads(target.read_text())
        except ValueError as e:
            return f"file '{fname}' is not valid JSON ({e})", {}
        if not isinstance(data, dict) or key not in data:
            return f"key '{key}' not found in {fname}", {}
        node = data[key]
        rows = node if isinstance(node, list) else []
        cmds = {r["id"]: (str(r.get("command", "")).split() or [None])[0]
                for r in rows if isinstance(r, dict) and "id" in r}
    elif target.suffix in (".yaml", ".yml"):
        block = yaml_block(target.read_text().split("\n"), key)
        if block is None:
            return f"no top-level '{key}:' line in {fname}", {}
        cmds = yaml_items(block)
    else:
        return f"file '{fname}' is neither JSON nor YAML", {}
    if item:
        if item not in cmds:
            return f"no item 'id: {item}' under '{key}' in {fname}", {}
        cmds = {item: cmds[item]}
    return None, cmds


def check_pointers(b, repo, job):
    fails, notes = [], []
    entries = [(p, s) for p, s in strings(b)
               if p and p[0] in ("signal", "measure", "gates") and POINTER.match(s)]
    for path, s in entries:
        err, cmds = resolve_pointer(s, repo)
        if err:
            fails.append(f"check 4: pointer '{label(path)}' = '{s}': {err}")
        elif path[0] == "gates":
            prose = [g for g, w in cmds.items() if not runnable(w, repo)]
            if prose:
                notes.append(f"check 4: '{label(path)}' has prose gates, run by the reviewer: {', '.join(prose)}")
    sig = b.get("signal")
    if isinstance(sig, dict):
        f, n = check_signal_rules(sig, repo, job)
        fails += f
        notes += n
    return fails, notes


def check_signal_rules(sig, repo, job):
    """(fails, notes). A missing script fails only `refactor`, the one job that runs the signal;
    the health watch stops at its signal step instead, and `change` never runs it."""
    fails, notes = [], []
    script = sig.get("script")
    if not script:
        fails.append("check 4: signal.script is missing")
    elif not (PERMA / "runtime" / f"{script}.py").is_file():
        msg = f"check 4: the generic signal script is not installed yet ({script}.py in {PERMA / 'runtime'})"
        (fails if job == "refactor" else notes).append(
            msg + ("; the refactor job refreshes the register with it" if job == "refactor" else ""))
    for k in ("fix", "part"):
        if k in sig:
            try:
                re.compile(sig[k])
            except (re.error, TypeError) as e:
                fails.append(f"check 4: signal.{k} does not compile ({e})")
    ref = sig.get("ref")
    if not ref or git(repo, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}").returncode:
        return fails + [f"check 4: signal.ref '{ref}' does not resolve in {repo}"], notes
    for root in sig.get("codeRoots") or []:
        if git(repo, "cat-file", "-e", f"{ref}:{root.rstrip('/')}").returncode:
            fails.append(f"check 4: signal.codeRoots '{root}' does not exist at {ref}")
    if not sig.get("codeRoots"):
        fails.append("check 4: signal.codeRoots is missing or empty")
    return fails, notes


def check_roles(b, job, repo):
    """Resolve each role the job dispatches by §5.1 (team_roles.resolve)."""
    have = team_roles.installed_agents(str(repo))
    lvls = team_roles.levels(PERMA, b)
    notes = []
    for role in JOB_ROLES.get(job, []):
        res = team_roles.resolve(f"{job}:{role}", lvls, have)
        for where, key, provs in res["skipped"]:
            notes.append(f"check 5: role {job}:{role}: {where} key '{key}' names {provs}, not installed; skipped")
        if res["fallback"] == "session":
            found = "the session does it"
        elif res["fallback"]:
            found = f"{res['agent']} (review roles never fall to the session)"
        else:
            found = f"{res['agent']} (from {res['where']}, key '{res['key']}')"
        notes.append(f"check 5: role {job}:{role} -> {found}")
    return notes


def check_approval(b, job, arg, approvals):
    want = {"refactor": {"part": arg}, "change": {"workOrder": arg}}[job]
    try:
        records = json.loads(approvals.read_text())
    except OSError:
        return [f"check 6: owned is false and {approvals} does not exist: no approval for {job} {arg}"]
    except ValueError as e:
        return [f"check 6: {approvals} is not valid JSON ({e})"]
    match = [r for r in records if isinstance(r, dict) and r.get("scope") == want] if isinstance(records, list) else []
    if any(not r.get("consumed") for r in match):
        return []
    if match:
        return [f"check 6: the approval for scope {json.dumps(want)} is consumed ({match[0]['consumed']}); a consumed approval never starts a job again"]
    return [f"check 6: owned is false and {approvals.name} holds no approval with scope {json.dumps(want)}"]


def main(argv):
    args, opts = [], {}
    it = iter(argv)
    for a in it:
        if a in ("--repo", "--binding"):
            opts[a] = next(it, None)
        else:
            args.append(a)
    job = args[0] if args else None
    if job not in ("refactor", "change", "health", "startup") or (job in JOB_ROLES and len(args) != 2) \
            or (job not in JOB_ROLES and len(args) != 1) or None in opts.values():
        print(__doc__.split("\n\n")[2], file=sys.stderr)
        return 2
    arg = args[1] if len(args) == 2 else None
    cwd = Path(opts.get("--repo") or os.getcwd()).resolve()
    top = git(cwd, "rev-parse", "--show-toplevel")
    repo = Path(top.stdout.strip()) if top.returncode == 0 else cwd

    if opts.get("--binding"):
        bpath, missing = Path(opts["--binding"]).resolve(), f"binding file {opts['--binding']} does not exist"
    else:
        bpath, missing = find_binding(repo)
    if bpath is None or not bpath.is_file():
        if job == "startup":
            print(f"preflight: {missing}")
            return 0
        print(f"FAIL check 1: {missing}")
        return 1

    try:
        b = json.loads(bpath.read_text())
    except ValueError as e:
        print(f"FAIL check 2: {bpath} does not parse as JSON ({e})")
        return 1
    if not isinstance(b, dict):
        print(f"FAIL check 2: {bpath} is not a JSON object")
        return 1

    fails = check_fields(b)
    notes = []
    if isinstance(b.get("owned"), bool):
        fails += check_paths(b, repo)
        f4, notes = check_pointers(b, repo, job)
        fails += f4
    if job in JOB_ROLES:
        notes += check_roles(b, job, repo)
        if b.get("owned") is False:
            fails += check_approval(b, job, arg, bpath.parent / "approvals.json")

    for n in notes:
        print(f"note {n}")
    for f in fails:
        print(f"FAIL {f}")
    print(f"preflight {job}{' ' + arg if arg else ''} on {repo}: "
          f"{'ok' if not fails else f'{len(fails)} failure(s)'} (binding {bpath})")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
