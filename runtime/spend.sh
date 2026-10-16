#!/usr/bin/env bash
# Measured wave spend: record the token count the HARNESS reported for each finished agent
# (`subagent_tokens` in its completion notification, never the agent's own estimate), group agents
# into waves with a ceiling, and warn at 80% and 100% of that ceiling.
# The ledger is <stream>/spend/ledger.jsonl, append-only. The stream resolves from the current
# directory through _meta/REGISTRY.md (as decision.sh does), or is named with --stream.
#
#   spend.sh wave open s2-slice --ceiling 400000
#   spend.sh record --agent a1b2c3 --label "S2 answers r1" --tokens 131204 \
#       --why "answer the 40 open rows" --predicted "36 of 40 answered" --predicted-tokens 120000 \
#       --result "38 of 40 answered" --outcome better [--wave s2-slice]
#       [--kind agent|answering-agent|reviewer|architect] [--task A508] [--model M] [--note "..."]
#       [--source harness|self-reported|estimate] [--correct] [--no-ops]
#   A first record states the tool's result, not only its cost: --why, --predicted, --predicted-tokens,
#   --result and --outcome are required (since v1.11.0). --kind architect also needs --task, and a
#   second architect run on one task needs --stepped-back.
#   spend.sh status [--wave W] [--all] [--json]
#   spend.sh report [--since 2026-10-10] [--json]
#   spend.sh wave close [s2-slice]
#
# `record` run from inside an owned repo also writes that repo's ops ledger agent-run row (through
# ops-event.sh), so one command records both. --no-ops skips it; --stream and --correct never write it.
# BACKFILL ONLY: SPEND_TS=<iso> stamps the row with that time, marks it backfilled, and needs --note.
set -euo pipefail
command -v python3 >/dev/null 2>&1 || { echo "$(basename "$0"): python3 not found on PATH — this tool needs it (standard library only)." >&2; exit 127; }
exec python3 "$(dirname "$0")/spend.py" "$@"
