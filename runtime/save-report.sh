#!/usr/bin/env bash
# Save an agent's report VERBATIM. A subagent cannot write its own report file, so the PM pipes the
# report text in on stdin and this writes it unchanged below a short header (title, date, source
# agent id, "saved verbatim by the PM", body size and sha256). Refuses to overwrite an existing file
# unless --append (add a new section) or --force (replace). Works for any path the PM names.
#
#   pbpaste | save-report.sh docs/runs/2026-10-10-s2/report.md --title "S2 slice report" --source-agent a1b2c3
#   save-report.sh notes/review.md --append --source-agent r9 < /path/to/report.txt
#
# SAVE_REPORT_NOW=<text> fixes the header's date (tests, backfill).
set -euo pipefail
command -v python3 >/dev/null 2>&1 || { echo "$(basename "$0"): python3 not found on PATH — this tool needs it (standard library only)." >&2; exit 127; }
exec python3 "$(dirname "$0")/save-report.py" "$@"
