#!/usr/bin/env bash
# Append ONE team-operations event to the ops ledger of the repository you are in. The ledger is the
# owner's working file, so it lives in that repository's stream, never in the repository:
#   <stream>/repo/ops/events.jsonl   (rules beside it in OPERATIONS.md)
# The stream is found from the repository root through _meta/REGISTRY.md, as session start does.
# THE canonical writer: a hand-typed line in a different shape is a silent gap in any report built
# from the ledger. Fields are positional; anything you do not know is left empty, never guessed.
#
# Usage (from inside the repository, or set OPS_REPO to its path):
#   ops-event.sh <kind> <task> <purpose> [model] [effort] [count] [tokens] [duration_s] [outcome] [note]
#
# BACKFILL ONLY — two env overrides, for an event written after the fact:
#   OPS_TS=2026-09-12T23:01:14+01:00 OPS_COMMIT=5308be8 ops-event.sh ...
# Always pair with `backfilled ...` in `note`, naming where the figure came from: the ledger is
# append-only and a reader must be able to tell a measurement taken at the time from one recovered
# later.
#     kind      agent-run | fan-out | loop | handshake | gate-refused | diagnosis | decision-asked |
#               decision-answered | status-run | session-start | session-end | note
#     task      the tracker id of the work, or "-"
#     purpose   one short phrase
#     model     the model id, or -
#     effort    high | medium | low | -
#     count     fan-out width / loop iterations / items offered, or -
#     tokens    subagent tokens as the harness reported them, or -
#     duration_s  seconds, or -
#     outcome   done | refused | partial | stopped | pending | -
#     note      free text, kept short
set -euo pipefail
command -v python3 >/dev/null 2>&1 || { echo "$(basename "$0"): python3 not found on PATH — this tool needs it (standard library only)." >&2; exit 127; }
PERMA="${PERMA_DIR:-$HOME/permanence}"
REPO="$(git -C "${OPS_REPO:-$PWD}" rev-parse --show-toplevel 2>/dev/null)" \
  || { echo "ops-event: ${OPS_REPO:-$PWD} is not inside a git repository" >&2; exit 1; }
STREAM="$("$PERMA/runtime/resolve-stream.sh" "$REPO")"
[ -n "$STREAM" ] || { echo "ops-event: no stream is registered for $REPO in _meta/REGISTRY.md" >&2; exit 1; }
[ -d "$PERMA/$STREAM/repo" ] || { echo "ops-event: stream $STREAM has no repo/ folder: this repository keeps no ledger" >&2; exit 1; }
# Only the owner's own repositories keep a ledger: another party's commits are not the owner's to log.
python3 -c 'import json,sys; sys.exit(0 if json.load(open(sys.argv[1])).get("owned") is True else 1)' \
  "$PERMA/$STREAM/repo/binding.json" 2>/dev/null \
  || { echo "ops-event: $STREAM/repo/binding.json does not say \"owned\": true: this repository keeps no ledger" >&2; exit 1; }
OUT="$PERMA/$STREAM/repo/ops/events.jsonl"
mkdir -p "$(dirname "$OUT")"
KIND="${1:?kind}"; TASK="${2:?task}"; PURPOSE="${3:?purpose}"
MODEL="${4:--}"; EFFORT="${5:--}"; COUNT="${6:--}"; TOKENS="${7:--}"; DUR="${8:--}"; OUTCOME="${9:--}"; NOTE="${10:-}"
python3 - "$OUT" "$REPO" "$KIND" "$TASK" "$PURPOSE" "$MODEL" "$EFFORT" "$COUNT" "$TOKENS" "$DUR" "$OUTCOME" "$NOTE" <<'PY'
import json, sys, datetime, subprocess, os
out, repo, kind, task, purpose, model, effort, count, tokens, dur, outcome, note = sys.argv[1:]
def num(v):
    try: return int(v)
    except ValueError: return None if v in ("-", "") else v
ev = {"ts": os.environ.get("OPS_TS") or datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
      "role": "engine", "kind": kind,
      "task": None if task == "-" else task, "purpose": purpose, "model": None if model == "-" else model,
      "effort": None if effort == "-" else effort, "count": num(count), "tokens": num(tokens), "durationS": num(dur),
      "outcome": None if outcome == "-" else outcome, "note": note or None,
      "commit": os.environ.get("OPS_COMMIT")
      or subprocess.run(["git", "-C", repo, "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
      or None}
with open(out, "a", encoding="utf-8") as f: f.write(json.dumps(ev, ensure_ascii=False) + "\n")
print(json.dumps(ev, ensure_ascii=False))
PY
