"""Tail data/audit_log.jsonl realtime — for debugging OAuth flow.

Usage:
    .venv\\Scripts\\python.exe tools\\tail_audit.py
    .venv\\Scripts\\python.exe tools\\tail_audit.py --filter oauth_relay
    .venv\\Scripts\\python.exe tools\\tail_audit.py --since 5min
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT     = Path(__file__).resolve().parent.parent
LOG_FILE = ROOT / "data" / "audit_log.jsonl"


def _format(entry: dict) -> str:
    t   = entry.get("t", "?")
    mod = entry.get("mod", "?")
    evt = entry.get("evt", "?")
    rest = {k: v for k, v in entry.items() if k not in ("t", "mod", "evt")}
    extras = " ".join(f"{k}={v}" for k, v in rest.items())
    return f"[{t}] {mod:18} {evt:30} {extras}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Tail audit_log.jsonl")
    parser.add_argument("--filter", "-f", default="",
                        help="Only show entries where mod or evt contains this string")
    parser.add_argument("--since", default="",
                        help="Show past entries from N min/sec ago (e.g. '5min', '30sec')")
    parser.add_argument("--no-follow", action="store_true",
                        help="Print existing log then exit (don't tail)")
    args = parser.parse_args()

    if not LOG_FILE.exists():
        print(f"Log file not found: {LOG_FILE}")
        return 1

    # Parse --since
    cutoff = None
    if args.since:
        s = args.since.strip().lower()
        try:
            if s.endswith("min"):
                cutoff = datetime.now() - timedelta(minutes=int(s[:-3]))
            elif s.endswith("sec"):
                cutoff = datetime.now() - timedelta(seconds=int(s[:-3]))
            else:
                cutoff = datetime.now() - timedelta(minutes=int(s))
        except ValueError:
            print(f"Bad --since format: {args.since}")
            return 1

    flt = args.filter.lower()

    def _matches(entry: dict) -> bool:
        if cutoff:
            try:
                ts = datetime.fromisoformat(entry.get("t", ""))
                if ts < cutoff:
                    return False
            except ValueError:
                pass
        if flt:
            blob = (str(entry.get("mod", "")) + " " + str(entry.get("evt", ""))).lower()
            if flt not in blob:
                return False
        return True

    # Print existing
    with LOG_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line)
                if _matches(entry):
                    print(_format(entry))
            except json.JSONDecodeError:
                pass

    if args.no_follow:
        return 0

    # Tail
    print("─" * 70)
    print("Tailing... Ctrl+C to stop.")
    print("─" * 70)

    with LOG_FILE.open("r", encoding="utf-8") as f:
        f.seek(0, 2)  # EOF
        try:
            while True:
                line = f.readline()
                if not line:
                    time.sleep(0.5)
                    continue
                try:
                    entry = json.loads(line)
                    if _matches(entry):
                        print(_format(entry))
                except json.JSONDecodeError:
                    pass
        except KeyboardInterrupt:
            print("\nStopped.")
            return 0


if __name__ == "__main__":
    sys.exit(main())
