"""
Atomic file write helpers — prevent corruption on crash / power loss.

F2-01 fix: Several GUI paths write JSON/text to files using `open(path, "w")`
which leaves the file in a truncated state if the process dies mid-write.
This module provides atomic versions: write to a `.tmp` sibling, then
os.replace() (which is atomic on both Windows and POSIX).
"""
from __future__ import annotations

import json
import os
import tempfile
from typing import Any, Union


def atomic_write_text(
    path: Union[str, os.PathLike],
    content: str,
    encoding: str = "utf-8",
) -> None:
    """Atomically write text to *path*.

    Writes to ``{path}.tmp`` first, then ``os.replace`` to the target.
    Creates parent directory if missing. Caller is responsible for any
    locking against concurrent writers.

    Raises OSError on disk full / permission denied.
    """
    path = os.fspath(path)
    parent = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(parent, exist_ok=True)

    # Use NamedTemporaryFile so we get a unique name even under concurrency
    fd, tmp_path = tempfile.mkstemp(
        prefix=os.path.basename(path) + ".",
        suffix=".tmp",
        dir=parent,
        text=False,
    )
    try:
        with os.fdopen(fd, "w", encoding=encoding) as f:
            f.write(content)
            f.flush()
            try:
                os.fsync(f.fileno())   # ensure bytes hit disk before replace
            except OSError:
                pass   # fsync not supported on all FSes — best-effort
        os.replace(tmp_path, path)
    except Exception:
        # Clean up tmp file on failure
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise


def atomic_write_json(
    path: Union[str, os.PathLike],
    data: Any,
    *,
    ensure_ascii: bool = False,
    indent: int = 2,
) -> None:
    """Atomically serialise *data* as JSON to *path*.

    Convenience wrapper around atomic_write_text.
    """
    text = json.dumps(data, ensure_ascii=ensure_ascii, indent=indent)
    atomic_write_text(path, text)
