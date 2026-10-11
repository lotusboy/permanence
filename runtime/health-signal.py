#!/usr/bin/env python3
"""Health signal per part of a repository, over a rolling window. Deterministic, no AI.

    python3 ~/permanence/runtime/health-signal.py --binding <binding.json> --register <register.json>
        [--repo .] [--as-of YYYY-MM-DD] [--window-days N] [--threshold X] [--regrowth X]
        [--top N] [--no-write]

Standard library only. It reads the repository with read-only git commands at one ref, so it never
needs the checkout to be on any branch and never changes the repository. It writes one file: the
register, which lives in the owner's stream (docs/PROJECT-TEAM.md).

THE RULES come from the binding's `signal` object:

    "signal": {
      "script": "health-signal",
      "ref": "HEAD",                              the commit or ref that is measured
      "fix": "(?i)^fix\\b",                        a commit whose subject matches is a FIX
      "codeRoots": ["src/", "scripts/"],          only lines under these count as code
      "part": "^src/([^/]+)/",                    a file's part id is group 1 ...
      "parts": [                                  ... or a list, first match wins:
        {"kind": "module", "match": "^src/pkg/(.+\\.py)$"},
        {"kind": "config", "match": "^conf/([^/]+)/", "id": "config/{1}"}
      ],
      "extensions": [".py"],                      optional: only these files belong to a part
      "reviewFinding": "\\bP1\\b"                  optional: what marks a finding worth counting
    }

THE THREE INPUTS

1. Fix pressure (decides the state). A fix commit's changed code lines are shared out over the
   parts they fall in; a part's SIGNAL is the sum of its shares over the window's fix commits. Each
   fix counts once in total, so a 5-line change beside a 200-line fix adds 0.02, not 1. A share
   under `passingShare` is also counted as `inPassing`.
2. Size (reported only). Per part: files, lines, and the longest file, at the ref.
3. Review findings (reported only). In each review folder whose name starts with a date inside the
   window, every paragraph that matches `reviewFinding` and names a part's file path adds one to
   that part. This is a text match, not a reading: treat it as a pointer to go and look.

THE STATE. A part at or over the threshold with no decision is `ready`; under it, `settled`. A
decision (`restructure`, `redesign` or `accept`) is written by a person under the part's
`decision` key and is NEVER overwritten: the script only fills `signalAtDecision` when it is
missing. A decided part shows `reshaped` or `kept`, and is raised again (`ready-again`) only when
its signal reaches `signalAtDecision` x `regrowth`. The window, threshold and regrowth live in the
register's own `settings` block, which the script also never overwrites.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

DEFAULT_SETTINGS = {
    "windowDays": 30,
    "threshold": 8.0,
    "regrowth": 1.5,
    "passingShare": 0.1,
    "idPattern": r"\b[A-Z]+-?\d{2,}\b",
    "top": 10,
}
DECISIONS = ("restructure", "redesign", "accept")
DEFAULT_FIX = r"(?i)^fix\b"
DEFAULT_FINDING = r"\bP1\b"
DATED = re.compile(r"^(\d{4}-\d{2}-\d{2})")


def fail(msg):
    sys.exit(f"health-signal: {msg}")


def git(repo, *args):
    p = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if p.returncode:
        fail(f"git {' '.join(args[:3])} failed in {repo}: {p.stderr.strip().splitlines()[-1:] or ''}")
    return p.stdout


# ---------- the rules ----------

def load_rules(binding_path):
    try:
        binding = json.loads(Path(binding_path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        fail(f"cannot read the binding {binding_path}: {e}")
    sig = binding.get("signal")
    if not isinstance(sig, dict) or sig.get("script") != "health-signal":
        fail('the binding\'s "signal" is not rules for this script (it needs an object with '
             '"script": "health-signal"; see this script\'s header)')
    roots = sig.get("codeRoots")
    if not isinstance(roots, list) or not roots or not all(isinstance(r, str) and r for r in roots):
        fail("signal.codeRoots must be a list of one or more folders")
    rules = []
    listed = sig.get("parts")
    if listed is not None and not isinstance(listed, list):
        fail("signal.parts must be a list")
    for r in listed or []:
        if not isinstance(r, dict) or not isinstance(r.get("match"), str):
            fail(f"signal.parts entry needs a \"match\" pattern, got {r!r}")
        rules.append((r.get("kind") or "part", compile_re("signal.parts.match", r["match"]), r.get("id")))
    if isinstance(sig.get("part"), str):
        rules.append(("part", compile_re("signal.part", sig["part"]), None))
    if not rules:
        fail('the binding gives no part rule: add signal.part (one pattern) or signal.parts (a list)')
    for kind, rx, _ in rules:
        if rx.groups < 1:
            fail(f"part pattern {rx.pattern!r} needs one group: the part id")
    ext = sig.get("extensions")
    reviews = binding.get("reviews", "axis/runs/")
    return {
        "ref": sig.get("ref") or "HEAD",
        "fix": compile_re("signal.fix", sig.get("fix") or DEFAULT_FIX),
        "roots": tuple(r if r.endswith("/") else r + "/" for r in roots),
        "rules": rules,
        "ext": tuple(ext) if isinstance(ext, list) and ext else None,
        "finding": compile_re("signal.reviewFinding", sig.get("reviewFinding") or DEFAULT_FINDING),
        "reviews": reviews.rstrip("/") + "/" if isinstance(reviews, str) and reviews.strip() else None,
    }


def compile_re(name, pattern):
    try:
        return re.compile(pattern)
    except (re.error, TypeError) as e:
        fail(f"{name} does not compile: {e}")


def part_of(path, rules):
    """(part id, kind) for a file path, or (None, None). The first rule that matches decides."""
    if rules["ext"] and not path.endswith(rules["ext"]):
        return None, None
    for kind, rx, template in rules["rules"]:
        m = rx.search(path)
        if m:
            if template:
                pid = template
                for i, g in enumerate(m.groups(), 1):
                    pid = pid.replace("{%d}" % i, g or "")
                return pid, kind
            return m.group(1), kind
    return None, None


# ---------- input 1: fix pressure ----------

def tracked_files(repo, ref):
    return [p for p in git(repo, "-c", "core.quotepath=off", "ls-tree", "-r", "--name-only", ref).splitlines() if p]


def fix_commits(repo, rules, since, until):
    out = git(repo, "-c", "core.quotepath=off", "log", rules["ref"], "--no-merges", "--no-renames", "--numstat",
              f"--since={since.isoformat()}T00:00:00", f"--until={until.isoformat()}T23:59:59",
              "--pretty=format:@@%h\t%s")
    commits, cur = [], None
    for line in out.splitlines():
        if line.startswith("@@"):
            sha, _, subject = line[2:].partition("\t")
            cur = {"sha": sha, "subject": subject, "files": {}}
            commits.append(cur)
        elif line.strip() and cur is not None:
            added, deleted, path = line.split("\t", 2)
            if added != "-":  # "-" marks a binary file: it has no lines
                cur["files"][path] = int(added) + int(deleted)
    return [c for c in commits if rules["fix"].search(c["subject"])]


def measure(commits, parts, rules, settings, own_ids):
    id_re = compile_re("settings.idPattern", settings["idPattern"])
    stats = defaultdict(lambda: {"fixCommits": 0, "linesChanged": 0, "signal": 0.0, "inPassing": 0, "ids": Counter()})
    by_id = defaultdict(lambda: {"fixCommits": 0, "parts": Counter()})
    for c in commits:
        ids = sorted(set(id_re.findall(c["subject"])))
        code = sum(n for p, n in c["files"].items() if p.startswith(rules["roots"]))
        per_part = Counter()
        for path, n in c["files"].items():
            pid, _ = part_of(path, rules)
            if pid in parts and n:
                per_part[pid] += n
        if not code:  # a part outside every code root cannot be given a share of nothing
            per_part = Counter()
        for pid, n in per_part.items():
            # a decided part's own restructure is the reshaping itself, not more signal on it
            if own_ids.get(pid) in ids:
                continue
            share = n / code
            s = stats[pid]
            s["fixCommits"] += 1
            s["linesChanged"] += n
            s["signal"] += share
            s["inPassing"] += share < settings["passingShare"]
            s["ids"].update(ids)
        for i in ids:
            by_id[i]["fixCommits"] += 1
            by_id[i]["parts"].update({p: n / code for p, n in per_part.items()})
    return stats, by_id


# ---------- input 2: size ----------

def sizes(repo, rules, files):
    """{part: {"files", "lines", "longestFile": {"path", "lines"}}} at the ref. Binary files count
    as files with no lines."""
    # git grep exits 1 when nothing matches (an empty code root), which is not an error here
    out = subprocess.run(["git", "-C", str(repo), "-c", "core.quotepath=off", "grep", "-c", "-I", "-e", "",
                          rules["ref"], "--", *rules["roots"]], capture_output=True, text=True).stdout
    lines = {}
    prefix = rules["ref"] + ":"
    for row in out.splitlines():
        body = row[len(prefix):] if row.startswith(prefix) else row
        path, _, n = body.rpartition(":")
        if n.isdigit():
            lines[path] = int(n)
    size = {}
    for path in files:
        pid, _ = part_of(path, rules)
        if not pid:
            continue
        s = size.setdefault(pid, {"files": 0, "lines": 0, "longestFile": None})
        n = lines.get(path, 0)
        s["files"] += 1
        s["lines"] += n
        if s["longestFile"] is None or n > s["longestFile"]["lines"]:
            s["longestFile"] = {"path": path, "lines": n}
    return size


# ---------- input 3: review findings ----------

def review_findings(repo, rules, files, since, until):
    """({part: count}, folders read). Reads the checkout's review folders: review records are files
    people and agents write as they work, and the newest are often not committed yet."""
    if not rules["reviews"]:
        return {}, 0
    root = Path(repo) / rules["reviews"]
    if not root.is_dir():
        return {}, 0
    paths = {}
    for f in files:
        pid, _ = part_of(f, rules)
        if pid:
            paths[f] = pid
    counts, folders = Counter(), 0
    for d in sorted(root.iterdir()):
        m = DATED.match(d.name)
        if not m or not d.is_dir():
            continue
        try:
            day = date.fromisoformat(m.group(1))
        except ValueError:
            continue
        if not since <= day <= until:
            continue
        folders += 1
        for md in sorted(d.rglob("*.md")):
            try:
                text = md.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for para in re.split(r"\n\s*\n", text):
                if rules["finding"].search(para):
                    for pid in {pid for f, pid in paths.items() if f in para}:
                        counts[pid] += 1
    return dict(counts), folders


# ---------- the register ----------

def read_register(path):
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return {}
    try:
        old = json.loads(text)
    except ValueError:
        fail(f"the register {path} is not JSON. This script reads and writes a JSON register. If it is an "
             f"older YAML register, convert it once (keeping `settings` and every `decision`) and point "
             f"the binding's `register` at the new file.")
    if not isinstance(old, dict):
        fail(f"the register {path} is not a JSON object")
    return old


def state_of(signal, decision, settings):
    if decision:
        if signal >= decision["signalAtDecision"] * settings["regrowth"]:
            return "ready-again"
        return "kept" if decision["decision"] == "accept" else "reshaped"
    return "ready" if signal >= settings["threshold"] else "settled"


def check_decision(pid, d):
    if not isinstance(d, dict) or d.get("decision") not in DECISIONS or not d.get("date"):
        fail(f"parts.{pid}.decision needs a date and one of {' | '.join(DECISIONS)}, got {d!r}")
    if "signalAtDecision" in d and not isinstance(d["signalAtDecision"], (int, float)):
        fail(f"parts.{pid}.decision.signalAtDecision must be a number, got {d['signalAtDecision']!r}")


def build(repo, rules, register_path, as_of, overrides):
    old = read_register(register_path)
    settings = {**DEFAULT_SETTINGS, **(old.get("settings") or {})}
    run = {**settings, **{k: v for k, v in overrides.items() if v is not None}}
    since = as_of - timedelta(days=run["windowDays"])
    files = tracked_files(repo, rules["ref"])
    parts = {}
    for path in files:
        pid, kind = part_of(path, rules)
        if pid:
            parts.setdefault(pid, kind)
    commits = fix_commits(repo, rules, since, as_of)
    old_parts = old.get("parts") or {}
    own_ids = {pid: d["backlogId"] for pid, v in old_parts.items()
               if isinstance(v, dict) and isinstance(d := v.get("decision"), dict) and d.get("backlogId")}
    stats, by_id = measure(commits, parts, rules, run, own_ids)
    size = sizes(repo, rules, files)
    found, folders = review_findings(repo, rules, files, since, as_of)

    out_parts = {}
    decided = {p for p, v in old_parts.items() if isinstance(v, dict) and v.get("decision")}
    for pid in sorted(set(parts) | decided):
        s = stats.get(pid)
        signal = round(s["signal"], 1) if s else 0.0
        decision = (old_parts.get(pid) or {}).get("decision")
        if decision:
            check_decision(pid, decision)
            decision.setdefault("signalAtDecision", signal)
        entry = {"kind": parts.get(pid, (old_parts.get(pid) or {}).get("kind"))}
        if pid not in parts:
            entry["present"] = False
        entry.update({
            "signal": signal,
            "fixCommits": s["fixCommits"] if s else 0,
            "inPassing": s["inPassing"] if s else 0,
            "linesChanged": s["linesChanged"] if s else 0,
            "topIds": [i for i, _ in s["ids"].most_common(3)] if s else [],
            "state": state_of(signal, decision, run),
            "decision": decision,
            "size": size.get(pid),
            "reviewFindings": found.get(pid, 0),
        })
        out_parts[pid] = entry

    ids = {i: {"fixCommits": v["fixCommits"], "topParts": [p for p, _ in v["parts"].most_common(3)]}
           for i, v in sorted(by_id.items(), key=lambda kv: (-kv[1]["fixCommits"], kv[0]))}
    return {
        "_about": "Generated by Permanence runtime/health-signal.py, except `settings` and each part's "
                  "`decision`, which a person owns and the script never overwrites.",
        "settings": settings,
        "computed": {
            "asOf": as_of.isoformat(),
            "windowDays": run["windowDays"],
            "threshold": run["threshold"],
            "regrowth": run["regrowth"],
            "fixCommits": len(commits),
            "head": git(repo, "rev-parse", "--short", rules["ref"]).strip(),
            "ref": rules["ref"],
            "reviewFolders": folders,
        },
        "parts": out_parts,
        "ids": ids,
    }


def render(reg, top):
    c = reg["computed"]
    ranked = sorted(reg["parts"].items(), key=lambda kv: (-kv[1]["signal"], kv[0]))
    ready = [p for p, v in ranked if v["state"] in ("ready", "ready-again")]
    lines = [
        f"Health, {c['windowDays']} days to {c['asOf']} at `{c['head']}`: {c['fixCommits']} fix commits; "
        f"threshold {c['threshold']}; {len(ready)} part(s) ready.",
        "",
        "| part | fix commits | in passing | signal | lines | review findings | top ids | state | decision |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for pid, v in ranked[:top]:
        d = v["decision"]
        dec = f"{d['decision']} {d['date']} ({d.get('backlogId') or 'no id'})" if d else "none"
        size = v.get("size") or {}
        lines.append(f"| `{pid}` | {v['fixCommits']} | {v['inPassing']} | {v['signal']:.1f} | "
                     f"{size.get('lines', '-')} | {v.get('reviewFindings', 0)} | "
                     f"{', '.join(v['topIds']) or '-'} | {v['state']} | {dec} |")
    repeated = [(i, v) for i, v in reg["ids"].items() if v["fixCommits"] >= 3]
    if repeated:
        lines += ["", "Ids with 3 or more fix commits: "
                  + "; ".join(f"{i} {v['fixCommits']} ({', '.join(v['topParts'])})" for i, v in repeated)]
    if ready:
        lines += ["", "Ready (needs the owner: restructure, redesign or accept): "
                  + ", ".join(f"`{p}` {reg['parts'][p]['signal']:.1f}" for p in ready)]
    return "\n".join(lines)


def write_whole(path, text):
    """Replace the register in one step, so a reader never sees half of it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--binding", required=True, help="the repo's binding.json, in the owner's stream")
    ap.add_argument("--register", required=True,
                    help="the register file; a relative path is taken beside the binding")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    ap.add_argument("--window-days", type=int)
    ap.add_argument("--threshold", type=float)
    ap.add_argument("--regrowth", type=float)
    ap.add_argument("--top", type=int)
    ap.add_argument("--no-write", action="store_true", help="print the block; leave the register as it is")
    a = ap.parse_args(argv)
    rules = load_rules(a.binding)
    repo = Path(a.repo)
    register = Path(a.register)
    if not register.is_absolute():
        register = Path(a.binding).resolve().parent / register
    overrides = {"windowDays": a.window_days, "threshold": a.threshold, "regrowth": a.regrowth}
    reg = build(repo, rules, register, a.as_of, overrides)
    if not a.no_write:
        write_whole(register, json.dumps(reg, indent=2, ensure_ascii=False) + "\n")
    print(render(reg, a.top or reg["settings"]["top"]))
    return reg


if __name__ == "__main__":
    main()
