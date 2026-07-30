"""
runtime_paths.py — runtime directory resolution, independent of CWD (P2).

Earlier builds resolved runtime paths as plain relative strings
("data/config.json", "logs/", ...), which only works when the process's
working directory happens to be the project root. That is fine for the
desktop shortcut, but a headless/service process (P1's worker_main.py, and
later a Windows Service) cannot rely on its CWD, and a VPS deployment
(ADR-009) must be able to point runtime data outside the release directory
entirely.

Resolution order per directory: explicit environment variable override,
else the existing desktop-relative default (computed from this file's
location, not the CWD, so it is correct regardless of where the process
was launched from).
"""
from __future__ import annotations

import os
from dataclasses import dataclass


def _project_root() -> str:
    # core/runtime_paths.py -> core/ -> project root
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@dataclass(frozen=True)
class RuntimePaths:
    data_dir:       str
    secrets_dir:    str
    logs_dir:       str
    temp_video_dir: str
    config_path:    str

    def ensure_dirs(self) -> None:
        """Create data/logs/temp_video dirs if missing. Never creates
        secrets_dir — that directory's existence/permissions are managed
        outside the application (deployment/ACL concern)."""
        for d in (self.data_dir, self.logs_dir, self.temp_video_dir):
            os.makedirs(d, exist_ok=True)


def resolve_runtime_paths(env: dict | None = None) -> RuntimePaths:
    """Resolve runtime directories from environment variables, falling back
    to the existing desktop-relative defaults.

    `env` is injectable (defaults to os.environ) so tests can verify
    precedence without mutating real process environment.
    """
    e = os.environ if env is None else env
    root = _project_root()

    data_dir    = (e.get("LTT_DATA_DIR")       or "").strip() or os.path.join(root, "data")
    secrets_dir = (e.get("LTT_SECRETS_DIR")    or "").strip() or os.path.join(root, "secrets")
    logs_dir    = (e.get("LTT_LOGS_DIR")       or "").strip() or os.path.join(root, "logs")
    temp_dir    = (e.get("LTT_TEMP_VIDEO_DIR") or "").strip() or os.path.join(root, "temp_videos")
    config_path = (e.get("LTT_CONFIG_PATH")    or "").strip() or os.path.join(data_dir, "config.json")

    return RuntimePaths(
        data_dir=data_dir, secrets_dir=secrets_dir, logs_dir=logs_dir,
        temp_video_dir=temp_dir, config_path=config_path,
    )
