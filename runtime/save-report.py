#!/usr/bin/env python3
"""Save an agent's report verbatim. Called through runtime/save-report.sh.

A subagent cannot write its own report file, so the PM saves it. Re-typing a report introduces
errors; this reads the report from stdin and writes the bytes unchanged below a short header.
The body is never decoded, re-wrapped or re-encoded: what came in on stdin is what lands on disk.
"""
import argparse
import datetime
import hashlib
import os
import sys
import tempfile
from pathlib import Path

RULE = b"\n---\n\n"


def fail(msg):
    sys.exit(f"save-report: {msg}")


def header(title, source, when, digest, size):
    by = f" from agent {source}" if source else ""
    return (f"# {title}\n\n"
            f"> Saved verbatim by the PM on {when}{by}.\n"
            f"> Everything below the line is the agent's report, byte for byte: {size} bytes, sha256 {digest[:16]}.\n"
            ).encode("utf-8") + RULE


def main():
    p = argparse.ArgumentParser(prog="save-report.sh", description=__doc__.split("\n\n")[0])
    p.add_argument("dest", help="the file to write, in any repo")
    p.add_argument("--title", help="default: the file name without its extension")
    p.add_argument("--source-agent", help="the agent id from the completion notification")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--append", action="store_true", help="add this report as a new section at the end of an existing file")
    g.add_argument("--force", action="store_true", help="replace an existing file")
    a = p.parse_args()

    if sys.stdin.isatty():
        fail("pipe the report in on stdin, e.g. pbpaste | save-report.sh <dest>")
    body = sys.stdin.buffer.read()
    if not body.strip():
        fail("stdin was empty; nothing written")
    dest = Path(a.dest).expanduser().absolute()
    if dest.is_dir():
        fail(f"{dest} is a directory; name the file")
    exists = dest.exists()
    if exists and not (a.append or a.force):
        fail(f"{dest} already exists; pass --append to add a section or --force to replace it")

    when = (os.environ.get("SAVE_REPORT_NOW")
            or datetime.datetime.now().astimezone().isoformat(sep=" ", timespec="minutes"))
    digest = hashlib.sha256(body).hexdigest()
    block = header(a.title or dest.stem, a.source_agent, when, digest, len(body)) + body

    dest.parent.mkdir(parents=True, exist_ok=True)
    if exists and a.append:
        prev = dest.read_bytes()
        sep = b"" if prev.endswith(b"\n\n") else b"\n" if prev.endswith(b"\n") else b"\n\n"
        with dest.open("ab") as f:
            f.write(sep + block)
        action = "appended to"
    else:
        fd, tmp = tempfile.mkstemp(dir=dest.parent, prefix=f".{dest.name}.")
        with os.fdopen(fd, "wb") as f:
            f.write(block)
        os.replace(tmp, dest)
        action = "replaced" if exists else "wrote"
    print(f"save-report: {action} {dest} ({len(body)} body bytes, sha256 {digest[:16]})")


if __name__ == "__main__":
    main()
