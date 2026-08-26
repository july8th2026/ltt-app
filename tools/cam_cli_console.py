"""Console entry point for the ZIP + BAT distribution.

The business logic remains in ``cam_cli.py``.  This file exists because the GUI
binary is built with the Windows GUI subsystem: a batch file cannot reliably
wait for it or receive stdout/exit codes.  The ZIP method needs a real console
program, not a windowed executable pretending to be one.
"""
from __future__ import annotations

import sys

import cam_cli


if __name__ == "__main__":
    sys.exit(cam_cli.main())
