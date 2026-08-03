"""H15.S9.1 Image Studio UI: owner history, metadata and real-output compare."""
from __future__ import annotations

import io
import re


def test_image_studio_history_owner_scoped(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path/'image-ui.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-image-ui")
    monkeypatch.setenv("LTT_ADMIN_USERNAME", "admin")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from platform_core.models import JOB_DONE, Job
    from platform_core.storage import LocalStorage, set_storage
    from platform_core.users import tao_nguoi_dung
    storage = LocalStorage(str(tmp_path / "store")); set_storage(storage)
    gen = dbmod.get_session(); db = next(gen)
    try:
        owner = tao_nguoi_dung(db, email="image-owner@test.com",
                               password="matkhau-tot-12", is_verified=True)
        other = tao_nguoi_dung(db, email="image-other@test.com",
                               password="matkhau-tot-12", is_verified=True)
        db.flush()
        owner_key = f"taoanh/{owner.id}/j1/0.png"
        other_key = f"taoanh/{other.id}/j2/0.png"
        db.add_all([
            Job(user_id=owner.id, app_slug="taoanh", job_type="taoanh.generate",
                status=JOB_DONE, progress=100,
                params={"prompt": "OWNER_PROMPT", "aspect_ratio": "16:9", "count": 1},
                result={"image_keys": [owner_key]}),
            Job(user_id=other.id, app_slug="taoanh", job_type="taoanh.generate",
                status=JOB_DONE, progress=100,
                params={"prompt": "OTHER_PROMPT", "aspect_ratio": "1:1", "count": 1},
                result={"image_keys": [other_key]}),
        ]); db.commit()
        storage.put(owner_key, io.BytesIO(b"owner"), content_type="image/png")
    finally:
        try: next(gen)
        except StopIteration: pass

    from fastapi.testclient import TestClient
    from server.app import create_app
    client = TestClient(create_app(), base_url="https://testserver", follow_redirects=False)
    try:
        login = client.get("/login")
        token = re.search(r'name="csrf_token" value="([^"]+)"', login.text).group(1)
        client.post("/login", data={"username": "image-owner@test.com",
                                    "password": "matkhau-tot-12", "csrf_token": token})
        page = client.get("/taoanh")
        assert page.status_code == 200
        assert "Image Studio" in page.text and "OWNER_PROMPT" in page.text
        assert "OTHER_PROMPT" not in page.text
        assert "im-pick" in page.text and "16:9 · 1 ảnh" in page.text
    finally:
        client.close(); set_storage(None); dbmod.reset_engine()


def test_image_template_has_no_inline_layout_and_safe_compare_dom():
    from pathlib import Path
    src = (Path(__file__).parents[1] / "apps" / "taoanh" / "templates" / "image.html").read_text("utf-8")
    assert src.count('style="') == 1 and 'style="width:{{j.progress}}%"' in src
    assert "textContent" in src and "innerHTML" not in src
    assert "aria-pressed" in src and "role=\"progressbar\"" in src
