#!/usr/bin/env bash
# The predicted-moves gate. A stop rule enforced by a machine: compares a structured prediction
# (moves.prediction.json) with a repo's flat before/after measurements (moves.baseline.json,
# moves.measured.json) and exits non-zero on any move nobody predicted.
#
#   predict-gate.sh check --prediction P --measured M [--baseline B] [--override "<reason>"] [--task ID]
#   predict-gate.sh install-hook <repo>     # pre-commit hook in that repo; never run automatically
#   predict-gate.sh hook                    # what the hook runs
#
# Format, outcomes and exit codes: runtime/predict-gate.py docstring and README "Predicted-moves gate".
set -euo pipefail
command -v python3 >/dev/null 2>&1 || { echo "$(basename "$0"): python3 not found on PATH — this tool needs it (standard library only)." >&2; exit 127; }
exec python3 "$(dirname "$0")/predict-gate.py" "$@"
