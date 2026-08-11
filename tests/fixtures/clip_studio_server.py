"""Isolated H32 Clip Studio browser fixture with streamed direct upload.

The fixture uses the real app routes, DB, credit ledger and worker contract.  Its
same-origin upload ticket emulates R2's browser-to-object-storage PUT without
touching production or loading a 500 MB request into web-process memory.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import secrets

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


ROOT = Path(os.environ["CLIP_STUDIO_FIXTURE_ROOT"]).resolve()
ROOT.mkdir(parents=True, exist_ok=True)
ORIGIN = os.environ.get("CLIP_STUDIO_FIXTURE_ORIGIN", "http://127.0.0.1:8143")
os.environ["LTT_DATABASE_URL"] = f"sqlite:///{(ROOT / 'browser.db').as_posix()}"
os.environ["LTT_DATA_DIR"] = str(ROOT / "data")
os.environ["LTT_ENV"] = "development"
os.environ["LTT_SESSION_SECRET"] = "clip-studio-browser-fixture"

config = ROOT / "config.json"
config.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1}),
                  encoding="utf-8")

import platform_core.db as dbmod  # noqa: E402
import platform_core.models  # noqa: E402,F401
from platform_core.credit import cap_tay  # noqa: E402
from platform_core.storage import (LocalStorage, UploadTarget,  # noqa: E402
                                   set_storage)
from platform_core.users import tao_nguoi_dung  # noqa: E402
from platform_core.models import User  # noqa: E402


class StreamedFixtureStorage(LocalStorage):
    """Local backend whose PUT ticket behaves like an object-store presign."""

    def __init__(self, root: str):
        super().__init__(root)
        self.uploads: dict[str, tuple[str, str]] = {}

    def put_url(self, key: str, ttl_s: int = 900,
                content_type: str = "application/octet-stream") -> UploadTarget:
        token = secrets.token_urlsafe(24)
        self.uploads[token] = (key, content_type)
        return UploadTarget(url=f"{ORIGIN}/__fixture_upload/{token}", key=key,
                            headers={"Content-Type": content_type})


fixture_storage = StreamedFixtureStorage(str(ROOT / "data" / "files"))
set_storage(fixture_storage)
dbmod.Base.metadata.create_all(dbmod.get_engine())
gen = dbmod.get_session(); db = next(gen)
try:
    user = db.query(User).filter_by(email="clip-browser@example.com").one_or_none()
    if user is None:
        user = tao_nguoi_dung(db, email="clip-browser@example.com",
                              password="Browser-pass-123", is_verified=True)
        db.flush(); cap_tay(db, user.id, 1000, by="fixture", note="browser H32.4")
    db.commit()
finally:
    try: next(gen)
    except StopIteration: pass

from server.app import create_app  # noqa: E402

app = create_app(env={
    "LTT_ENV": "development", "LTT_CONFIG_PATH": str(config),
    "LTT_SESSION_SECRET": os.environ["LTT_SESSION_SECRET"],
    "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
})


@app.put("/__fixture_upload/{token}")
async def fixture_upload(token: str, request: Request):
    ticket = fixture_storage.uploads.pop(token, None)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Upload ticket invalid or used.")
    key, _content_type = ticket
    target = fixture_storage._path(key)  # fixture-only use of protected helper
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + f".part{os.getpid()}")
    size = 0
    try:
        with temporary.open("wb") as output:
            async for chunk in request.stream():
                size += len(chunk)
                if size > 1024 * 1024 * 1024:
                    raise HTTPException(status_code=413, detail="Fixture upload exceeds 1 GiB.")
                output.write(chunk)
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink(missing_ok=True)
    return JSONResponse({"ok": True, "size": size})
