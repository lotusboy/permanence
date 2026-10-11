#!/usr/bin/env bash
# The decision ledger: record every question put to the owner, score how often the agent's
# recommendation is the owner's choice, and say when a category has earned autonomy.
# The ledger is <stream>/decisions/ledger.jsonl, append-only, and is the source of truth for the
# scores. <stream>/DECISIONS.md is its readable view, regenerated after every write. The stream
# resolves from the current directory through _meta/REGISTRY.md (as ops-event.sh does), or is
# named with --stream. --questions-ref "<text>" ties a decision to an existing QUESTIONS.md entry:
# ask and answer each add one pointer line under that entry and change nothing else in the file.
#
#   decision.sh ask --category spend --question "Run the audit now?" --option yes --option no \
#       --recommendation yes --confidence 0.8 --evidence-kind measured --evidence "estimate in WIP.md"
#   decision.sh answer <id> --choice yes            # agreed is worked out when the choice matches
#   decision.sh outcome <id> --verdict held|reversed|refined --by "what showed it"
#   decision.sh score [--stream S] [--category C] [--since DATE] [--all-streams] [--json]
#   decision.sh should-ask <category> [--seed N]    # ask | ask-blind | decide-and-log
#   decision.sh review [--stream S] [--since DATE] [--md] [--all-streams]
#   decision.sh render [--stream S] [--all-streams]  # regenerate DECISIONS.md
#
# BACKFILL ONLY: DECISION_BACKFILL=1 DECISION_TS=<iso> marks the line backfilled and relaxes the
# required fields (confidence, evidence, options) that cannot be recovered after the fact.
# Defaults: runtime/decision-config.json; per stream: <stream>/decisions/config.json.
set -euo pipefail
command -v python3 >/dev/null 2>&1 || { echo "$(basename "$0"): python3 not found on PATH — this tool needs it (standard library only)." >&2; exit 127; }
exec python3 "$(dirname "$0")/decision.py" "$@"
