"""Create or verify the deterministic LTTSTUDIOSAPP system dossier.

Usage:
    python tools/build_system_profile.py
    python tools/build_system_profile.py --check
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.system_profile import build_profile, profile_path  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a secret-safe full-source system dossier.")
    parser.add_argument("--check", action="store_true",
                        help="do not write; fail when the snapshot is stale")
    parser.add_argument("--output", type=Path,
                        help="optional destination; defaults to repository root")
    args = parser.parse_args(argv)
    destination = args.output.resolve() if args.output else profile_path()
    rendered = build_profile()
    if args.check:
        try:
            current = destination.read_text(encoding="utf-8")
        except OSError:
            current = ""
        if current != rendered:
            print(f"STALE: {destination}")
            print("Run: python tools/build_system_profile.py")
            return 1
        print(f"PASS: {destination} matches repository sources")
        return 0
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(rendered, encoding="utf-8", newline="\n")
    temporary.replace(destination)
    print(f"WROTE: {destination}")
    print(f"SIZE: {destination.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
