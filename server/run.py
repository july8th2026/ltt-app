"""
Uvicorn entrypoint (P3).

Always binds to loopback (127.0.0.1) by default — per AGENTS.md, "Public
ports are 80/443 through the reverse proxy. Application ports bind to
127.0.0.1." The reverse proxy (Caddy, ADR-007) is the only intended
public-facing surface; this process is never meant to be reachable
directly in production.
"""
from __future__ import annotations

import os

import uvicorn

from server.app import create_app
from platform_core.observability import configure_logging

configure_logging(component="server")
app = create_app()

if __name__ == "__main__":
    host = os.environ.get("LTT_SERVER_HOST", "127.0.0.1")
    port = int(os.environ.get("LTT_SERVER_PORT", "8100"))
    uvicorn.run(app, host=host, port=port)
