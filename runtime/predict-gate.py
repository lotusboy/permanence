#!/usr/bin/env python3
"""The predicted-moves gate: compare a structured prediction with what a repo measured, and refuse
any move nobody predicted. A stop rule enforced by a machine, not by an agent choosing to stop.

Why (2026-10-10): an engineer committed past a stop rule. The gap register moved 9 -> 11, no move
had been predicted, the engineer judged the move fine and committed. The prediction was prose, and
nothing compared it with the measurement.

Standard library only. Usage (normally through predict-gate.sh):

  predict-gate.py check --prediction P --baseline B --measured M [--override REASON] [--task ID]
  predict-gate.py hook                     # run by the pre-commit hook, inside the repo
  predict-gate.py install-hook REPO

The three files:
  P  moves.prediction.json (or .yaml when PyYAML is installed). Written before the first edit.
       {"moves": [{"what": KEY, "from": X, "to": Y, "scope": TEXT}, ...],
        "mustNotMove": [KEY, ...], "tolerance": 0}
     A move says how its key moves by exactly one of: "to" (with "from" optional), "delta",
     "range" [lo, hi] (inclusive, the value after), or nothing ("moves, any value", for a hash).
     KEY may hold * and ? (fnmatch). "scope" is a label for the reader; it does not change matching.
     A key a move names is judged by that move even when a mustNotMove glob also matches it, so
     "mustNotMove": ["premium:*"] beside one predicted premium move means "no OTHER premium moves".
  B  moves.baseline.json  flat {KEY: value}, measured BEFORE the change.
  M  moves.measured.json  flat {KEY: value}, measured AFTER the change.

Exit: 0 pass (or failed and overridden, recorded); 1 the gate refused; 2 bad input.
"""

from __future__ import annotations

import fnmatch
import json
import os
import subprocess
import sys
from pathlib import Path

PREDICTION_NAMES = ("moves.prediction.json", "moves.prediction.yaml", "moves.prediction.yml")
BASELINE_NAME = "moves.baseline.json"
MEASURED_NAME = "moves.measured.json"
HOOK_MARKER = "# installed-by: permanence runtime/predict-gate.sh"
ABSENT = object()


class BadInput(Exception):
    pass


def load(path: Path, text: str | None = None):
    if text is None:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as e:
            raise BadInput(f"cannot read {path}: {e.strerror}")
    if path.suffix in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError:
            try:
                return json.loads(text)
            except ValueError:
                raise BadInput(f"{path} is YAML and PyYAML is not installed: write it as JSON")
        try:
            return yaml.safe_load(text)
        except yaml.YAMLError as e:
            raise BadInput(f"{path} is not valid YAML: {e}")
    try:
        return json.loads(text)
    except ValueError as e:
        raise BadInput(f"{path} is not valid JSON: {e}")


def flat(data, path: Path) -> dict:
    if not isinstance(data, dict):
        raise BadInput(f"{path} must be one JSON object of key -> value")
    for k, v in data.items():
        if isinstance(v, (dict, list)):
            raise BadInput(f"{path}: key {k!r} holds a {type(v).__name__}; values must be flat")
    return data


def check_prediction(p, path: Path) -> dict:
    if not isinstance(p, dict):
        raise BadInput(f"{path} must be one object with 'moves' and 'mustNotMove'")
    unknown = set(p) - {"moves", "mustNotMove", "tolerance", "about"}
    if unknown:
        raise BadInput(f"{path}: unknown field(s) {sorted(unknown)}")
    moves, mnm = p.get("moves") or [], p.get("mustNotMove") or []
    if not isinstance(moves, list) or not isinstance(mnm, list):
        raise BadInput(f"{path}: 'moves' and 'mustNotMove' must be lists")
    tol = p.get("tolerance", 0)
    if not isinstance(tol, (int, float)) or tol < 0:
        raise BadInput(f"{path}: 'tolerance' must be a number >= 0")
    for i, m in enumerate(moves):
        if not isinstance(m, dict) or not isinstance(m.get("what"), str):
            raise BadInput(f"{path}: move {i + 1} needs a 'what' key")
        extra = set(m) - {"what", "from", "to", "delta", "range", "scope"}
        if extra:
            raise BadInput(f"{path}: move {m['what']!r} has unknown field(s) {sorted(extra)}")
        kinds = [k for k in ("to", "delta", "range") if k in m]
        if len(kinds) > 1:
            raise BadInput(f"{path}: move {m['what']!r} gives {kinds}; give one of to/delta/range")
        if "from" in m and "to" not in m:
            raise BadInput(f"{path}: move {m['what']!r} gives 'from' without 'to'")
        r = m.get("range")
        if r is not None and not (isinstance(r, list) and len(r) == 2 and all(_num(x) for x in r)):
            raise BadInput(f"{path}: move {m['what']!r}: 'range' must be [low, high], numbers")
        if "delta" in m and not _num(m["delta"]):
            raise BadInput(f"{path}: move {m['what']!r}: 'delta' must be a number")
    for k in mnm:
        if not isinstance(k, str):
            raise BadInput(f"{path}: every mustNotMove entry must be a key")
        if any(m["what"] == k for m in moves):
            raise BadInput(f"{path}: {k!r} is both in mustNotMove and predicted to move")
    return {"moves": moves, "mustNotMove": mnm, "tolerance": tol}


def _num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def same(a, b, tol) -> bool:
    if _num(a) and _num(b):
        return abs(a - b) <= tol
    return a == b


def show(v) -> str:
    return "(absent)" if v is ABSENT else json.dumps(v)


def expected(m: dict) -> str:
    if "to" in m:
        return (f"{json.dumps(m['from'])} -> " if "from" in m else "-> ") + json.dumps(m["to"])
    if "delta" in m:
        return f"change of {m['delta']:+}"
    if "range" in m:
        return f"after in [{m['range'][0]}, {m['range'][1]}]"
    return "moves, any value"


def matches(m: dict, before, after, tol) -> str | None:
    """None when the move happened as predicted; else why not."""
    if "to" in m:
        if "from" in m and not same(before, m["from"], tol):
            return f"baseline was {show(before)}, the prediction said {json.dumps(m['from'])}"
        return None if same(after, m["to"], tol) else f"it reached {show(after)}"
    if "delta" in m:
        if not (_num(before) and _num(after)):
            return "a delta needs numbers before and after"
        return None if abs((after - before) - m["delta"]) <= tol else f"it changed by {after - before:+}"
    if "range" in m:
        lo, hi = m["range"]
        if not _num(after):
            return f"it reached {show(after)}, not a number"
        return None if lo - tol <= after <= hi + tol else f"it reached {show(after)}"
    return None


def compare(pred: dict, base: dict, meas: dict) -> dict:
    tol = pred["tolerance"]
    keys = sorted(set(base) | set(meas))
    moved = {
        k for k in keys
        if (k in base) != (k in meas) or not same(base.get(k), meas.get(k), tol)
    }
    out = {"keys": len(keys), "moved": len(moved), "hit": [], "missed": [], "wrong": [],
           "unpredicted": [], "breach": [], "unmeasured": []}
    covered = set()
    for m in pred["moves"]:
        hits = [k for k in keys if fnmatch.fnmatchcase(k, m["what"])]
        if not hits:
            out["missed"].append((m, m["what"], ABSENT, ABSENT, "no measured key matches it"))
            continue
        for k in hits:
            covered.add(k)
            before, after = base.get(k, ABSENT), meas.get(k, ABSENT)
            if k not in moved:
                out["missed"].append((m, k, before, after, "it did not move"))
                continue
            why = matches(m, before, after, tol)
            out["wrong" if why else "hit"].append((m, k, before, after, why))
    predicted = set(covered)  # a key a move names is judged by that move, not by a mustNotMove glob
    for pat in pred["mustNotMove"]:
        hits = [k for k in keys if fnmatch.fnmatchcase(k, pat)]
        if not hits:
            out["unmeasured"].append(pat)
        for k in hits:
            if k in predicted:
                continue
            covered.add(k)
            if k in moved:
                out["breach"].append((pat, k, base.get(k, ABSENT), meas.get(k, ABSENT)))
    out["unpredicted"] = [(k, base.get(k, ABSENT), meas.get(k, ABSENT)) for k in sorted(moved - covered)]
    out["failures"] = len(out["wrong"]) + len(out["unpredicted"]) + len(out["breach"]) + len(out["unmeasured"])
    return out


def report(r: dict, files: dict) -> str:
    lines = ["Predicted-moves gate", f"  prediction: {files['prediction']}",
             f"  baseline:   {files['baseline']}", f"  measured:   {files['measured']}",
             f"Keys measured: {r['keys']}. Keys that moved: {r['moved']}.", ""]

    def section(title, rows, stops):
        lines.append(f"{title}: {len(rows)}." + (" Each one stops the commit." if stops and rows else ""))
        lines.extend(f"  - {row}" for row in rows)
        lines.append("")

    def scope(m):
        return f" [scope: {m['scope']}]" if m.get("scope") else ""

    section("1. Predicted, and it happened",
            [f"{k}: {show(b)} -> {show(a)}. Predicted: {expected(m)}.{scope(m)}"
             for m, k, b, a, _ in r["hit"]], False)
    section("2. Predicted, and it did not happen (reported; does not stop)",
            [f"{k}: {show(b)} -> {show(a)}. Predicted: {expected(m)}. Not met: {why}.{scope(m)}"
             for m, k, b, a, why in r["missed"]], False)
    section("3. Predicted to move, and it moved to a different value",
            [f"{k}: {show(b)} -> {show(a)}. Predicted: {expected(m)}. Not met: {why}.{scope(m)}"
             for m, k, b, a, why in r["wrong"]], True)
    section("4. Moved, and nobody predicted it",
            [f"{k}: {show(b)} -> {show(a)}." for k, b, a in r["unpredicted"]], True)
    section("5. Must not move, and it moved",
            [f"{k}: {show(b)} -> {show(a)} (rule: {pat})." for pat, k, b, a in r["breach"]], True)
    section("6. Must not move, and it was not measured, so it is unproven",
            [f"{pat}: no key in the baseline or the measured file matches it." for pat in r["unmeasured"]], True)
    if r["failures"]:
        lines.append(f"Result: REFUSED. {r['failures']} line(s) in sections 3 to 6. "
                     "An unpredicted move goes to the owner. Do not edit the prediction, a test or an "
                     "output to make this pass; a new prediction needs the owner's go.")
    else:
        lines.append("Result: PASS. Every move was predicted, and nothing in mustNotMove moved.")
    return "\n".join(lines)


def record_override(reason: str, task: str, repo: Path, r: dict) -> str | None:
    """Write the override to the ops ledger. Returns an error text when it could not be written."""
    perma = Path(os.environ.get("PERMA_DIR") or Path.home() / "permanence")
    note = (f"predicted-moves gate overridden: {reason} | refused lines: wrong {len(r['wrong'])}, "
            f"unpredicted {len(r['unpredicted'])}, mustNotMove moved {len(r['breach'])}, "
            f"unmeasured {len(r['unmeasured'])}; first: "
            + "; ".join(k for k, _, _ in r["unpredicted"][:3]))
    env = dict(os.environ, OPS_REPO=str(repo))
    try:
        p = subprocess.run([str(perma / "runtime" / "ops-event.sh"), "gate-refused", task or "-",
                            "predicted-moves gate overridden", "-", "-", str(r["failures"]), "-", "-",
                            "done", note], capture_output=True, text=True, env=env)
    except OSError as e:
        return f"cannot run ops-event.sh: {e.strerror}"
    return None if p.returncode == 0 else (p.stderr.strip() or f"ops-event.sh exit {p.returncode}")


def run_check(pred_path: Path, base_path: Path, meas_path: Path, override: str, task: str,
              texts: dict | None = None, repo: Path | None = None) -> int:
    texts = texts or {}
    pred = check_prediction(load(pred_path, texts.get("prediction")), pred_path)
    base = flat(load(base_path, texts.get("baseline")), base_path)
    meas = flat(load(meas_path, texts.get("measured")), meas_path)
    r = compare(pred, base, meas)
    print(report(r, {"prediction": pred_path, "baseline": base_path, "measured": meas_path}))
    if not r["failures"]:
        if override:
            print("The override was not needed and was not recorded.")
        return 0
    if not override:
        return 1
    repo = repo or Path(subprocess.run(["git", "-C", str(pred_path.parent), "rev-parse", "--show-toplevel"],
                                       capture_output=True, text=True).stdout.strip() or pred_path.parent)
    err = record_override(override, task, repo, r)
    if err:
        print(f"\nOVERRIDE REFUSED: it could not be recorded in the ops ledger ({err}). "
              "An override is never silent, so the gate stays refused.")
        return 1
    print(f"\nOVERRIDDEN by the owner, recorded in the ops ledger: {override}")
    return 0


def git(repo, *args, check=True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=check)


def run_hook() -> int:
    """Inside a repo, at pre-commit: check every folder whose moves.measured.json is staged."""
    repo = Path(git(".", "rev-parse", "--show-toplevel").stdout.strip())
    staged = git(repo, "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z").stdout.split("\0")
    folders = sorted({str(Path(f).parent) for f in staged if Path(f).name == MEASURED_NAME})
    if not folders:
        return 0
    override = os.environ.get("PREDICT_GATE_OVERRIDE", "")
    task = os.environ.get("PREDICT_GATE_TASK", "-")
    worst = 0
    for folder in folders:
        d = Path(folder)

        def staged_text(name):
            p = git(repo, "show", f":{(d / name).as_posix()}", check=False)
            return p.stdout if p.returncode == 0 else None

        pred_name = next((n for n in PREDICTION_NAMES if staged_text(n) is not None), None)
        missing = [n for n, t in (("moves.prediction.json", pred_name),
                                  (BASELINE_NAME, staged_text(BASELINE_NAME))) if t is None]
        print(f"\n== {folder}")
        if missing:
            print(f"Predicted-moves gate: REFUSED. {folder}/{MEASURED_NAME} is staged, and "
                  f"{', '.join(missing)} is not in the index beside it. A measurement with no "
                  "prediction or no baseline cannot be checked.")
            worst = 1
            continue
        texts = {"prediction": staged_text(pred_name), "baseline": staged_text(BASELINE_NAME),
                 "measured": staged_text(MEASURED_NAME)}
        try:
            rc = run_check(repo / d / pred_name, repo / d / BASELINE_NAME, repo / d / MEASURED_NAME,
                           override, task, texts, repo)
        except BadInput as e:
            print(f"Predicted-moves gate: bad input: {e}")
            rc = 1
        worst = max(worst, rc)
    if worst:
        print("\nCommit stopped by the predicted-moves gate. Owner-approved exception only: "
              'PREDICT_GATE_OVERRIDE="<reason>" [PREDICT_GATE_TASK=<id>] git commit ...')
    return worst


def install_hook(repo_arg: str, gate: Path) -> int:
    p = git(repo_arg, "rev-parse", "--show-toplevel", check=False)
    if p.returncode != 0:
        print(f"install-hook: {repo_arg} is not a git repository")
        return 2
    repo = Path(p.stdout.strip())
    hp = git(repo, "config", "--get", "core.hooksPath", check=False).stdout.strip()
    if hp:
        print(f"install-hook: {repo} sets core.hooksPath ({hp}), so git ignores .git/hooks. Not "
              f"installed. Add this line to {hp}/pre-commit instead:\n  \"{gate}\" hook || exit 1")
        return 1
    hook = Path(git(repo, "rev-parse", "--path-format=absolute", "--git-path", "hooks").stdout.strip()) / "pre-commit"
    if (hook.exists() or hook.is_symlink()) and HOOK_MARKER not in hook.read_text(errors="replace"):
        print(f"install-hook: {hook} exists and was not written by Permanence. Left alone. Add this "
              f"line to it instead:\n  \"{gate}\" hook || exit 1")
        return 1
    hook.parent.mkdir(parents=True, exist_ok=True)
    if hook.is_symlink():
        hook.unlink()
    hook.write_text(
        "#!/bin/sh\n"
        f"{HOOK_MARKER}\n"
        "# Refuses a commit whose staged moves.measured.json shows a move its moves.prediction.json\n"
        "# did not predict. Owner-approved exception: PREDICT_GATE_OVERRIDE=\"<reason>\" git commit ...\n"
        "# (recorded in the ops ledger). Delete this file to remove the gate.\n"
        f"exec \"{gate}\" hook\n")
    hook.chmod(0o755)
    print(f"install-hook: {hook} written")
    return 0


def main(argv) -> int:
    gate = Path(__file__).resolve().with_name("predict-gate.sh")
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0 if argv else 2
    cmd, rest = argv[0], argv[1:]
    try:
        if cmd == "check":
            import argparse
            ap = argparse.ArgumentParser(prog="predict-gate.sh check")
            ap.add_argument("--prediction", required=True, type=Path)
            ap.add_argument("--measured", required=True, type=Path)
            ap.add_argument("--baseline", type=Path,
                            help=f"default: {BASELINE_NAME} beside the measured file")
            ap.add_argument("--override", default="", help="owner-approved reason; recorded in the ops ledger")
            ap.add_argument("--task", default="-", help="tracker id for the ops ledger line")
            a = ap.parse_args(rest)
            if "--override" in rest and not a.override.strip():
                raise BadInput("--override needs a reason")
            return run_check(a.prediction, a.baseline or a.measured.with_name(BASELINE_NAME),
                             a.measured, a.override.strip(), a.task)
        if cmd == "hook":
            return run_hook()
        if cmd == "install-hook" and len(rest) == 1:
            return install_hook(rest[0], gate)
    except BadInput as e:
        print(f"predict-gate: bad input: {e}", file=sys.stderr)
        return 2
    print("usage: predict-gate.sh check --prediction P --measured M [--baseline B] [--override R] [--task ID]\n"
          "       predict-gate.sh install-hook <repo>\n"
          "       predict-gate.sh hook", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
