#!/usr/bin/env bash
# stale-loops.sh — open loops nobody has come back to (v1.15.0).
# ---------------------------------------------------------------------------------
# Why: Permanence writes loose ends down accurately, but nothing brought an old one back. The brief and
# the morning orientation show current state and next actions, so a loop with no next action never
# appeared in either, and sat until an outside question happened to hit it. /perma-brief prints this
# script's output as its "Stale loops" section; /perma-startup prints its one-line form for one stream.
#
# What is an open loop (every stream except perma-meta):
#   - QUESTIONS.md: a table row, a top-level bullet, or a heading that is itself a question ("## Q — ...",
#     "### Q12: ..."). Items under a heading that says "closed" or "answered" are not open. Nor is an item
#     holding "[CLOSED", or the template's placeholder row.
#   - WIP.md: a top-level bullet in a section whose heading starts with Now, Blocked or Parked. A row that
#     says only "Nothing." or "None." is skipped. Other sections (Done today, a handover, ...) are not read.
#   - LOG.md: a paragraph or bullet, under a dated "## YYYY-MM-DD" heading, that holds one of the phrases
#     "not yet read", "to confirm", "unconfirmed", "probably overtaken" or "no owner" (any letter case, also
#     across a line break). A paragraph holding "[CLOSED" is not open: closing one of these is the one
#     edit allowed to an old LOG entry (SPEC.md invariant 2).
#   Lines inside a fenced code block are never read.
#
# When is a loop stale:
#   - An item that holds "by: YYYY-MM-DD" is stale once that date has passed, whatever its age (the latest
#     by: date in the item counts). A future by: date means it is not stale.
#   - Otherwise it is stale when it is more than N days old. N is 14, or the whole number (1-3650) on the
#     first line of runtime/.stale-loops; "off" there silences this script. Any other value: 14.
#   - Age: for a LOG paragraph, its entry's date. For a question or a board row, `git blame -w -M`: the
#     date the oldest of the item's lines was committed (one blame per file; a row moved inside its file
#     keeps its age). How it fails, always towards a shorter list, never a wrong one: an item whose every
#     line was rewritten looks new; uncommitted lines are 0 days old; an install with short git history
#     caps every age at its first commit; a file git cannot blame gives no ages (a by: date still counts).
#   "owner: X" is for the reader only. An item with an owner but no by: date is judged by its age.
#
# Output, oldest first (the number of days old, or the days past its by: date):
#   stale-loops.sh           the brief's section: at most 10 items and at most 3 from one stream, then a
#                            count of the rest per stream, then the owner's three choices. With nothing
#                            stale, one line saying so.
#   stale-loops.sh <stream>  one line for that stream: its count and its oldest item. Nothing when it has
#                            none, or when the name is not a stream.
# Read-only; changes no file. Prints nothing, and exits 0, when ~/permanence or python3 is missing.
# PERMA_TODAY=YYYY-MM-DD sets "today" (for tests).

PERMA="${PERMA_DIR:-$HOME/permanence}"
[ -d "$PERMA" ] || exit 0
command -v python3 >/dev/null 2>&1 || exit 0
HERE="$(cd "$(dirname "$0")" && pwd)"

python3 - "$PERMA" "$HERE/list-streams.sh" "${1:-}" <<'PY' 2>/dev/null
import datetime as dt
import os
import re
import subprocess
import sys

PERMA, LISTER, ONLY = sys.argv[1], sys.argv[2], sys.argv[3].strip().rstrip("/")
SHOW_TOTAL, SHOW_PER_STREAM = 10, 3

HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
BULLET = re.compile(r"^[-*+]\s+\S")
FENCE = re.compile(r"^\s*(```|~~~)")
Q_HEADING = re.compile(r"^Q\d*\s*[—–:-]|^Q\d+\b")
CLOSED_SECTION = re.compile(r"closed|answered", re.I)
WIP_SECTION = re.compile(r"^(now|blocked|parked)\b", re.I)
NOTHING_ROW = re.compile(r"^(nothing|none)\b[^.]{0,30}\.?$", re.I)
TABLE_SEP = re.compile(r"^\|?\s*:?-{3,}")
PLACEHOLDER = re.compile(r"^<[^>]*>$")
PHRASES = re.compile(r"\b(not\s+yet\s+read|to\s+confirm|unconfirmed|probably\s+overtaken|no\s+owner)\b", re.I)
BY = re.compile(r"\bby:\s*(\d{4}-\d{2}-\d{2})", re.I)
LOG_DATE = re.compile(r"^(\d{4}-\d{2}-\d{2})\b")


def setting():
    try:
        with open(os.path.join(PERMA, "runtime", ".stale-loops"), encoding="utf-8") as f:
            first = next((ln for ln in f if ln.strip()), "")
    except OSError:
        return 14
    v = "".join(first.split()).lower()
    if v == "off":
        return None
    if re.fullmatch(r"[0-9]{1,4}", v) and 1 <= int(v) <= 3650:
        return int(v)
    return 14


def today():
    try:
        return dt.date.fromisoformat(os.environ.get("PERMA_TODAY", ""))
    except ValueError:
        return dt.date.today()


def iso(s):
    try:
        return dt.date.fromisoformat(s)
    except ValueError:
        return None


def read_lines(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return [ln.rstrip("\r\n").rstrip("\r") for ln in f]
    except OSError:
        return None


def blame(rel):
    """{line number: date} for a file under PERMA, from the commit that wrote each line."""
    try:
        out = subprocess.run(["git", "-C", PERMA, "blame", "-w", "-M", "--line-porcelain", "--", rel],
                             capture_output=True, encoding="utf-8", errors="replace", timeout=60).stdout
    except Exception:
        return {}
    dates, line_no, when = {}, None, None
    for ln in out.splitlines():
        m = re.match(r"^[0-9a-f]{40,64} \d+ (\d+)", ln)
        if m:
            line_no = int(m.group(1))
        elif ln.startswith("author-time "):
            when = dt.date.fromtimestamp(int(ln.split()[1]))
        elif ln.startswith("\t") and line_no is not None and when is not None:
            dates[line_no] = when
    return dates


def short(text, words=10, chars=70):
    t = re.sub(r"(\*\*|__|`)", "", text)
    t = " ".join(t.split())
    w = t.split(" ")
    s = " ".join(w[:words])
    if len(s) > chars:
        s = s[:chars].rstrip()
    return s + ("…" if s != t else "")


def unfenced(lines):
    """(line number, text) for each line outside a fenced code block."""
    fence = None
    for i, ln in enumerate(lines, 1):
        m = FENCE.match(ln)
        if m:
            fence = None if fence == m.group(1) else (fence or m.group(1))
            continue
        if fence is None:
            yield i, ln


def blocks(lines):
    """Headings, top-level bullets with their continuation lines, table rows, and paragraphs, in order.
    Each is (kind, heading level or None, [(line number, text), ...])."""
    out, cur = [], None
    gap = False
    for i, ln in unfenced(lines):
        h = HEADING.match(ln)
        if h:
            cur = None
            out.append(("heading", len(h.group(1)), [(i, h.group(2))]))
            continue
        if not ln.strip():
            gap = True
            continue
        if ln.lstrip().startswith("|"):
            cur = None
            out.append(("row", None, [(i, ln.strip())]))
            continue
        if BULLET.match(ln):
            cur = ("bullet", None, [(i, ln)])
            out.append(cur)
        elif cur is not None and (not gap or ln[:1].isspace()):
            cur[2].append((i, ln))
        else:
            cur = ("para", None, [(i, ln)])
            out.append(cur)
        gap = False
    return out


def row_item(rows, k):
    """The label of table row k, or None when it is a header, a separator or the template placeholder."""
    text = rows[k][2][0][1]
    if TABLE_SEP.match(text):
        return None
    nxt = rows[k + 1][2][0][1] if k + 1 < len(rows) and rows[k + 1][0] == "row" else ""
    if TABLE_SEP.match(nxt):
        return None  # the header row
    cells = [c.strip() for c in text.strip().strip("|").split("|")]
    if all(not c or PLACEHOLDER.match(c) for c in cells[1:]) or "<question>" in text:
        return None
    if cells and re.fullmatch(r"Q\d+[a-z]?", cells[0], re.I):
        rest = next((c for c in cells[1:] if c), "")
        return cells[0] + " " + short(rest, 9)
    return short(next((c for c in cells if c), ""))


def question_items(lines):
    items, bl = [], blocks(lines)
    closed, section_level = False, 0
    q_open = None  # the open heading question collecting its body, or None
    for k, (kind, level, body) in enumerate(bl):
        if kind == "heading":
            text = body[0][1]
            if Q_HEADING.match(text):
                q_open = None
                if closed and level > section_level:
                    continue
                q_open = {"label": short(text), "lines": [body[0]]}
                items.append(q_open)
            else:
                q_open = None
                closed, section_level = bool(CLOSED_SECTION.search(text)), level
            continue
        if q_open is not None:
            q_open["lines"].extend(body)
            continue
        if closed:
            continue
        if kind == "bullet":
            items.append({"label": short(body[0][1].lstrip("-*+ ")), "lines": body})
        elif kind == "row":
            label = row_item(bl, k)
            if label:
                items.append({"label": label, "lines": body})
    return items


def board_items(lines):
    items, inside = [], False
    for kind, level, body in blocks(lines):
        if kind == "heading":
            inside = bool(WIP_SECTION.match(body[0][1]))
        elif inside and kind == "bullet":
            first = " ".join(t for _, t in body).lstrip("-*+ ").strip().strip("*_ ")
            if NOTHING_ROW.match(" ".join(first.split())):
                continue
            items.append({"label": short(body[0][1].lstrip("-*+ ")), "lines": body})
    return items


def log_items(lines):
    items, when = [], None
    for kind, level, body in blocks(lines):
        if kind == "heading":
            if level <= 2:  # a dated "## YYYY-MM-DD" opens an entry; any other top heading ends it
                m = LOG_DATE.match(body[0][1]) if level == 2 else None
                when = iso(m.group(1)) if m else None
            continue
        if when is None or kind == "row":
            continue
        starts, pos = [], 0
        for n, t in body:
            starts.append((pos, n))
            pos += len(t) + 1
        joined = " ".join(t for _, t in body)
        m = PHRASES.search(joined)
        if not m:
            continue
        at = next(n for p, n in reversed(starts) if p <= m.start())
        before, after = joined[:m.start()].split(), joined[m.start():].split()
        if before[:1] in (["-"], ["*"], ["+"]):
            before = before[1:]
        label = (("\u2026" if len(before) > 5 else "") + " ".join(before[-5:] + after[:8])
                 + ("\u2026" if len(after) > 8 else ""))
        items.append({"label": "\u201c" + re.sub(r"(\*\*|__|`)", "", label) + "\u201d", "line": at,
                      "lines": body, "date": when})
    return items


def stale_in(name, folder, days, now):
    found = []
    for fname, reader in (("QUESTIONS.md", question_items), ("WIP.md", board_items), ("LOG.md", log_items)):
        rel = os.path.join(folder, fname)
        lines = read_lines(os.path.join(PERMA, rel))
        if not lines:
            continue
        items = reader(lines)
        dates = None
        for it in items:
            text = "\n".join(t for _, t in it["lines"])
            if "[closed" in text.lower():
                continue
            bys = [d for d in (iso(s) for s in BY.findall(text)) if d]
            if bys:
                by = max(bys)
                if by >= now:
                    continue
                measure, how = (now - by).days, "past its by: date " + by.isoformat()
            else:
                when = it.get("date")
                if when is None:
                    if dates is None:
                        dates = blame(rel)
                    known = [dates[n] for n, _ in it["lines"] if n in dates]
                    when = min(known) if known else None
                if when is None:
                    continue
                age = (now - when).days
                if age <= days:
                    continue
                measure, how = age, None
            line = it.get("line", it["lines"][0][0])
            days_txt = "%d day%s" % (measure, "" if measure == 1 else "s")
            found.append({"stream": name, "where": "%s:%d" % (fname, line), "label": it["label"],
                          "measure": measure, "age": days_txt + (" " + how if how else " old"),
                          "key": (-measure, name, fname, line)})
    return found


def main():
    days = setting()
    if days is None:
        return
    now = today()
    try:
        listing = subprocess.run(["bash", LISTER], capture_output=True, encoding="utf-8", errors="replace",
                                 timeout=60).stdout
    except Exception:
        return
    streams = [ln.split("\t", 1) for ln in listing.splitlines() if "\t" in ln]
    streams = [(n, f) for n, f in streams if n != "perma-meta"]
    if ONLY:
        streams = [(n, f) for n, f in streams if n == ONLY]
        if not streams:
            return
    stale = []
    for name, folder in streams:
        stale.extend(stale_in(name, folder, days, now))
    stale.sort(key=lambda s: s["key"])
    if ONLY:
        if stale:
            s = stale[0]
            print("Stale loops in this stream: %d. The oldest: %s · %s · %s. /perma-brief lists them."
                  % (len(stale), s["where"], s["label"], s["age"]))
        return
    rule = "open items more than %d days old, or past their by: date" % days
    if not stale:
        print("Stale loops: none (%s)." % rule)
        return
    shown, per = [], {}
    for s in stale:
        if len(shown) < SHOW_TOTAL and per.get(s["stream"], 0) < SHOW_PER_STREAM:
            shown.append(s)
            per[s["stream"]] = per.get(s["stream"], 0) + 1
    n_streams = len({s["stream"] for s in stale})
    print("Stale loops: %d in %d stream%s (%s). The oldest:"
          % (len(stale), n_streams, "" if n_streams == 1 else "s", rule))
    for s in shown:
        print("- %s · %s · %s · %s" % (s["stream"], s["where"], s["label"], s["age"]))
    rest = {}
    for s in stale:
        if s not in shown:
            rest[s["stream"]] = rest.get(s["stream"], 0) + 1
    if rest:
        print("Not shown: %d (%s)." % (sum(rest.values()),
                                        ", ".join("%s %d" % (n, c) for n, c in sorted(rest.items()))))
    print("For each, choose one: close it ([CLOSED YYYY-MM-DD: answer]); give it an owner and a date "
          "(owner: X, by: YYYY-MM-DD); or park it on purpose (by: a review date, and the reason).")


main()
PY
exit 0
