#!/usr/bin/env python3
"""Measured spend: the token count the harness reported for each agent, grouped into waves with a
ceiling. Pure computation; no AI. Called through runtime/spend.sh.

Why it exists: an agent's own report of its token use was off by up to 2x (2026-10-10). The figure
the harness puts in the completion notification (`subagent_tokens`) is the measured one, so that is
the figure recorded here, and `source` says when a row is anything less.

Ledger: <stream>/spend/ledger.jsonl, append-only, a sibling of decisions/ledger.jsonl. It is a
stream ledger, not the repo ops ledger, because a wave can run from any stream, owned repo or not.
Event kinds:
  wave-open   wave, ceiling
  wave-close  wave
  agent       agent, label, tokens, wave, kind, source, task, model, note, corrects,
              why, predicted, predictedTokens, result, outcome
Every first record of an agent states why that tool was chosen, what was predicted (result and
tokens), what happened and the outcome (owner, 2026-09-27 and 2026-10-14: track tool use in results,
not only stats). A run that went worse or failed, or whose tokens are off the prediction by more than
half, gets a stub entry in <stream>/TOOLS.md for the lesson to be written.
A wrong agent row is never edited: `record --correct` appends a new row for the same agent id, and
the latest row for an agent id is the one that counts.
"""
import argparse
import datetime
import json
import os
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

PERMA = Path(os.environ.get("PERMA_DIR") or Path.home() / "permanence")
LEDGER = "spend/ledger.jsonl"
KINDS = ("agent", "answering-agent", "reviewer", "architect")
SOURCES = ("harness", "self-reported", "estimate")
OUTCOMES = ("as-predicted", "better", "worse", "failed")
TOOLS = "TOOLS.md"
WARN, STOP = 0.8, 1.0


def fail(msg):
    sys.exit(f"spend: {msg}")


def stamp():
    return os.environ.get("SPEND_TS") or datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def resolve_stream(explicit):
    if explicit:
        stream = explicit.strip("/")
    else:
        out = subprocess.run([str(PERMA / "runtime" / "resolve-stream.sh"), os.getcwd()],
                             capture_output=True, text=True, env=dict(os.environ, PERMA_DIR=str(PERMA)))
        stream = out.stdout.strip()
        if not stream:
            fail(f"no stream is registered for {os.getcwd()} in _meta/REGISTRY.md; pass --stream")
    if ".." in Path(stream).parts or os.path.isabs(stream):
        fail(f"stream {stream} is not a folder inside {PERMA}")
    if not (PERMA / stream).is_dir():
        fail(f"stream {stream} has no folder in {PERMA}")
    return stream


def read_events(stream):
    p = PERMA / stream / LEDGER
    if not p.exists():
        return []
    rows = []
    for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                print(f"spend: {stream}/{LEDGER} line {n} is not JSON; skipped", file=sys.stderr)
    return rows


def append(stream, event):
    p = PERMA / stream / LEDGER
    p.parent.mkdir(exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def tokens_arg(v):
    s = v.replace(",", "").replace("_", "")
    if not s.isdigit() or int(s) <= 0:
        raise argparse.ArgumentTypeError(f"'{v}' is not a whole number of tokens above 0")
    return int(s)


# ---------- state ----------

def waves(events):
    """name -> {ceiling, opened, closed} in the order they were opened."""
    out = {}
    for e in events:
        if e["event"] == "wave-open":
            out[e["wave"]] = {"ceiling": e["ceiling"], "opened": e["ts"], "closed": None}
        elif e["event"] == "wave-close" and e["wave"] in out:
            out[e["wave"]]["closed"] = e["ts"]
    return out


def open_waves(events):
    return [n for n, w in waves(events).items() if w["closed"] is None]


def agents(events):
    """The latest row per agent id: a correction replaces the row it corrects."""
    latest = {}
    for e in events:
        if e["event"] == "agent":
            latest[e["agent"]] = e
    return list(latest.values())


def wave_summary(events, name):
    w = waves(events)[name]
    rows = [a for a in agents(events) if a.get("wave") == name]
    spent = sum(a["tokens"] for a in rows)
    frac = spent / w["ceiling"]
    level = "over" if frac >= STOP else "warn" if frac >= WARN else "ok"
    return {"wave": name, "ceiling": w["ceiling"], "spent": spent, "fraction": round(frac, 4), "level": level,
            "open": w["closed"] is None, "opened": w["opened"], "closed": w["closed"],
            "agents": [{k: a.get(k) for k in ("agent", "label", "kind", "tokens", "source", "ts")} for a in rows]}


def flag(s):
    pct = f"{s['fraction'] * 100:.0f}%"
    if s["level"] == "over":
        return f"STOP: wave {s['wave']} has spent {s['spent']:,} of its {s['ceiling']:,} ceiling ({pct})."
    if s["level"] == "warn":
        return f"WARNING: wave {s['wave']} has spent {s['spent']:,} of its {s['ceiling']:,} ceiling ({pct}); 80% reached."
    return None


def bar(frac, width=20):
    filled = min(width, int(frac * width))
    return "[" + "#" * filled + "." * (width - filled) + "]"


# ---------- commands ----------

def cmd_wave(a):
    stream = resolve_stream(a.stream)
    ev = read_events(stream)
    known = waves(ev)
    if a.action == "open":
        if not a.name:
            fail("wave open needs a name")
        if a.ceiling is None:
            fail("wave open needs --ceiling <tokens>")
        if a.name in known:
            fail(f"wave {a.name} already exists in {stream} (opened {known[a.name]['opened']}); pick a new name")
        append(stream, {"ts": stamp(), "event": "wave-open", "wave": a.name, "ceiling": a.ceiling})
        print(f"wave {a.name} open in {stream}: ceiling {a.ceiling:,} tokens")
        return
    name = a.name
    if not name:
        live = open_waves(ev)
        if len(live) != 1:
            fail(f"{len(live)} waves are open in {stream}; name the one to close")
        name = live[0]
    if name not in known:
        fail(f"no wave {name} in {stream}")
    if known[name]["closed"]:
        fail(f"wave {name} was already closed at {known[name]['closed']}")
    append(stream, {"ts": stamp(), "event": "wave-close", "wave": name})
    s = wave_summary(read_events(stream), name)
    print(f"wave {name} closed in {stream}: spent {s['spent']:,} of {s['ceiling']:,} "
          f"({s['fraction'] * 100:.0f}%) across {len(s['agents'])} agents")


def mirror_to_ops(stream, a):
    """One write for the PM: an agent-run row in the repo ops ledger, when this cwd keeps one."""
    binding = PERMA / stream / "repo" / "binding.json"
    try:
        owned = json.loads(binding.read_text()).get("owned") is True
    except (OSError, json.JSONDecodeError):
        owned = False
    if not owned:
        return "ops ledger: not written (this stream keeps no ops ledger)"
    note = f"spend.sh: agent={a.agent} kind={a.kind} source={a.source}" + (f" wave={a.wave}" if a.wave else "")
    if a.note:
        note += f"; {a.note}"
    tokens = str(a.tokens) if a.source == "harness" else "-"
    p = subprocess.run([str(PERMA / "runtime" / "ops-event.sh"), "agent-run", a.task or "-", a.label,
                        a.model or "-", "-", "-", tokens, "-", "done", note],
                       capture_output=True, text=True, env=dict(os.environ, PERMA_DIR=str(PERMA)))
    if p.returncode != 0:
        return f"ops ledger: NOT written ({p.stderr.strip()}); the spend row stands"
    return "ops ledger: agent-run row written"


def cmd_record(a):
    stream = resolve_stream(a.stream)
    ev = read_events(stream)
    if os.environ.get("SPEND_TS") and not a.note:
        fail("a backfilled row (SPEND_TS set) needs --note naming where the figure came from")
    known = waves(ev)
    if a.wave:
        if a.wave not in known:
            fail(f"no wave {a.wave} in {stream}; open it first: spend.sh wave open {a.wave} --ceiling <n>")
    else:
        live = open_waves(ev)
        if len(live) > 1:
            fail(f"{len(live)} waves are open in {stream} ({', '.join(live)}); pass --wave")
        a.wave = live[0] if live else None
    seen = {r["agent"] for r in agents(ev)}
    if a.agent in seen and not a.correct:
        fail(f"agent {a.agent} is already recorded in {stream}; pass --correct to replace its row")
    if a.correct and a.agent not in seen:
        fail(f"--correct given but agent {a.agent} has no row in {stream} to correct")
    if a.kind == "architect" and a.task and not a.correct:
        earlier = [r for r in agents(ev) if r.get("kind") == "architect" and r.get("task") == a.task]
        if earlier and not (a.stepped_back or "").strip():
            fail(f"a second architect run for {a.task} ({len(earlier)} before): give --stepped-back, the"
                 " step-back done before dispatching it (owner, 2026-10-15)")
    if not a.correct and not os.environ.get("SPEND_TS"):
        missing = [f for f in ("why", "predicted", "predicted_tokens", "result", "outcome") if getattr(a, f) is None]
        if missing:
            fail("a first record states the tool's result, not only its cost: give "
                 + ", ".join("--" + m.replace("_", "-") for m in missing))
    row = {"ts": stamp(), "event": "agent", "agent": a.agent, "label": a.label, "tokens": a.tokens,
           "wave": a.wave, "kind": a.kind, "source": a.source, "task": a.task, "model": a.model,
           "note": a.note, "corrects": bool(a.correct), "backfilled": bool(os.environ.get("SPEND_TS")),
           "why": a.why, "predicted": a.predicted, "predictedTokens": a.predicted_tokens,
           "result": a.result, "outcome": a.outcome, "steppedBack": getattr(a, "stepped_back", None)}
    append(stream, row)
    if needs_lesson(a):
        print(stub_lesson(stream, a))
    print(f"recorded {a.agent} ({a.label}): {a.tokens:,} tokens, {a.source}"
          + (f", wave {a.wave}" if a.wave else ", no wave open"))
    if a.wave:
        s = wave_summary(read_events(stream), a.wave)
        print(f"wave {a.wave}: {bar(s['fraction'])} {s['spent']:,} / {s['ceiling']:,} ({s['fraction'] * 100:.0f}%)")
        msg = flag(s)
        if msg:
            print(msg, file=sys.stderr)
    if not a.no_ops and not a.correct and not a.stream:
        print(mirror_to_ops(stream, a))


def needs_lesson(a):
    if a.outcome is None:
        return False
    off = a.predicted_tokens and abs(a.tokens - a.predicted_tokens) > a.predicted_tokens / 2
    return a.outcome in ("worse", "failed") or bool(off)


def stub_lesson(stream, a):
    path = PERMA / stream / TOOLS
    if not path.exists():
        return f"TOOLS.md: {stream} has none; no lesson stub written"
    entry = (f"\n### {stamp()[:10]} — {a.task or '-'} — {a.label} ({a.kind}, {a.agent})\n"
             f"- **Why this tool:** {a.why}\n"
             f"- **Predicted:** {a.predicted}; {a.predicted_tokens:,} tokens.\n"
             f"- **Actual:** {a.result}; {a.tokens:,} tokens ({a.source}); outcome {a.outcome}.\n"
             f"- **Lesson:** TODO — what to do differently with this tool, or the tool this shows we need.\n")
    with path.open("a", encoding="utf-8") as f:
        f.write(entry)
    return f"TOOLS.md: lesson stub added for {a.agent} ({a.outcome}); write the lesson before the next dispatch"


def cmd_status(a):
    stream = resolve_stream(a.stream)
    ev = read_events(stream)
    names = list(waves(ev)) if a.all else open_waves(ev)
    if a.wave:
        if a.wave not in waves(ev):
            fail(f"no wave {a.wave} in {stream}")
        names = [a.wave]
    out = [wave_summary(ev, n) for n in names]
    if a.json:
        print(json.dumps({"stream": stream, "waves": out}, indent=2, ensure_ascii=False))
        return
    if not out:
        print(f"{stream}: no {'' if a.all else 'open '}waves. Open one: spend.sh wave open <name> --ceiling <tokens>")
        return
    for s in out:
        state = "open" if s["open"] else f"closed {s['closed']}"
        print(f"wave {s['wave']} ({state}) {bar(s['fraction'])} {s['spent']:,} / {s['ceiling']:,} "
              f"({s['fraction'] * 100:.0f}%), {s['ceiling'] - s['spent']:,} left")
        for r in s["agents"]:
            mark = "" if r["source"] == "harness" else f"  [{r['source']}, not measured]"
            print(f"  {r['tokens']:>10,}  {r['kind']:<15} {r['agent']}  {r['label']}{mark}")
        msg = flag(s)
        if msg:
            print("  " + msg)


def cmd_report(a):
    stream = resolve_stream(a.stream)
    rows = [r for r in agents(read_events(stream)) if not a.since or r["ts"][:10] >= a.since]
    by = {"day": defaultdict(int), "wave": defaultdict(int), "kind": defaultdict(int), "source": defaultdict(int)}
    for r in rows:
        by["day"][r["ts"][:10]] += r["tokens"]
        by["wave"][r.get("wave") or "(no wave)"] += r["tokens"]
        by["kind"][r["kind"]] += r["tokens"]
        by["source"][r["source"]] += r["tokens"]
    total = sum(r["tokens"] for r in rows)
    if a.json:
        print(json.dumps({"stream": stream, "since": a.since, "agents": len(rows), "total": total,
                          **{k: dict(sorted(v.items())) for k, v in by.items()}}, indent=2, ensure_ascii=False))
        return
    print(f"{stream}: {total:,} tokens across {len(rows)} agents" + (f" since {a.since}" if a.since else ""))
    for k in ("day", "wave", "kind", "source"):
        print(f"by {k}:")
        for name, n in sorted(by[k].items()):
            print(f"  {n:>12,}  {name}")


def main():
    p = argparse.ArgumentParser(prog="spend.sh", description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("record", help="record one finished agent's measured token count")
    r.add_argument("--agent", required=True, help="the agent id from the completion notification")
    r.add_argument("--label", required=True, help="a short name for what it did")
    r.add_argument("--tokens", required=True, type=tokens_arg, help="subagent_tokens from the notification")
    r.add_argument("--wave", help="default: the one open wave, if exactly one is open")
    r.add_argument("--kind", choices=KINDS, default="agent")
    r.add_argument("--source", choices=SOURCES, default="harness",
                   help="harness = the notification's figure (default); anything else is flagged as not measured")
    r.add_argument("--task", help="tracker id the agent served")
    r.add_argument("--model")
    r.add_argument("--note")
    r.add_argument("--why", help="why this tool was chosen over the alternatives")
    r.add_argument("--predicted", help="the result predicted before the run")
    r.add_argument("--predicted-tokens", type=tokens_arg, help="the tokens predicted before the run")
    r.add_argument("--result", help="what actually happened, measured")
    r.add_argument("--outcome", choices=OUTCOMES)
    r.add_argument("--stepped-back", help="a second architect run for --task: the step-back done first")
    r.add_argument("--correct", action="store_true", help="replace this agent's earlier row (appends; never edits)")
    r.add_argument("--no-ops", action="store_true", help="do not also write the repo ops ledger's agent-run row")
    r.add_argument("--stream")
    r.set_defaults(fn=cmd_record)

    w = sub.add_parser("wave", help="open or close a wave")
    w.add_argument("action", choices=("open", "close"))
    w.add_argument("name", nargs="?")
    w.add_argument("--ceiling", type=tokens_arg)
    w.add_argument("--stream")
    w.set_defaults(fn=cmd_wave)

    s = sub.add_parser("status", help="spent vs ceiling per wave, per agent, with 80%%/100%% warnings")
    s.add_argument("--wave")
    s.add_argument("--all", action="store_true", help="closed waves too")
    s.add_argument("--json", action="store_true")
    s.add_argument("--stream")
    s.set_defaults(fn=cmd_status)

    t = sub.add_parser("report", help="totals by day, wave, kind and source")
    t.add_argument("--since", help="YYYY-MM-DD, inclusive")
    t.add_argument("--json", action="store_true")
    t.add_argument("--stream")
    t.set_defaults(fn=cmd_report)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
