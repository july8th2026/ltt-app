"""Fixture browser cô lập cho H26.9 Tạo ảnh AI; không gọi provider thật."""
from __future__ import annotations

import io
import json
import os
from pathlib import Path


ROOT = Path(os.environ["IMAGE_STUDIO_FIXTURE_ROOT"]).resolve()
ROOT.mkdir(parents=True, exist_ok=True)
os.environ["LTT_DATABASE_URL"] = f"sqlite:///{(ROOT / 'browser.db').as_posix()}"
os.environ["LTT_DATA_DIR"] = str(ROOT / "data")
os.environ["LTT_ENV"] = "development"
os.environ["LTT_SESSION_SECRET"] = "image-studio-browser-fixture"

config = ROOT / "config.json"
config.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1}),
                  encoding="utf-8")

import platform_core.db as dbmod  # noqa: E402
import platform_core.models  # noqa: E402,F401
from platform_core.credit import cap_tay  # noqa: E402
from platform_core.models import JOB_DONE, JOB_ERROR, Job, User  # noqa: E402
from platform_core.storage import get_storage  # noqa: E402
from platform_core.users import tao_nguoi_dung  # noqa: E402

dbmod.Base.metadata.create_all(dbmod.get_engine())
gen = dbmod.get_session(); db = next(gen)
try:
    user = db.query(User).filter_by(email="image-browser@example.com").one_or_none()
    if user is None:
        user = tao_nguoi_dung(db, email="image-browser@example.com",
                              password="Browser-pass-123", is_verified=True)
        db.flush(); cap_tay(db, user.id, 500, by="fixture", note="browser H26.9")

    from PIL import Image
    storage = get_storage()

    def put_png(key: str, color: tuple[int, int, int], size=(640, 360)) -> None:
        out = io.BytesIO(); Image.new("RGB", size, color).save(out, format="PNG")
        out.seek(0); storage.put(key, out, content_type="image/png")

    if not db.query(Job).filter_by(user_id=user.id, app_slug="taoanh").first():
        general_key = f"taoanh/{user.id}/fixture-general/0.png"
        thumb_key = f"thumbnail/{user.id}/fixture-thumb/0.png"
        put_png(general_key, (32, 115, 190))
        put_png(thumb_key, (205, 45, 55))
        db.add_all([
            Job(user_id=user.id, app_slug="taoanh", job_type="taoanh.generate",
                status=JOB_DONE, progress=100,
                params={"prompt": "Thành phố tương lai", "model": "gemini-2.5-flash-image",
                        "aspect_ratio": "16:9", "count": 1, "edit_mode": "generate"},
                result={"image_keys": [general_key], "count": 1}),
            Job(user_id=user.id, app_slug="taoanh", job_type="taoanh.generate",
                status=JOB_ERROR, progress=18, error="Fixture: provider tạm gián đoạn",
                params={"prompt": "Ảnh lỗi để kiểm tra trạng thái", "aspect_ratio": "1:1",
                        "count": 1}),
            Job(user_id=user.id, app_slug="thumbnail", job_type="thumbnail.generate",
                status=JOB_DONE, progress=100,
                params={"topic": "Ra mắt sản phẩm", "title": "BỨT PHÁ 2026",
                        "aspect_ratio": "16:9", "count": 1,
                        "text_style": "bold_impact"},
                result={"image_keys": [thumb_key], "count": 1,
                        "scores": [{"score": 82, "width": 640, "height": 360,
                                    "method": "technical-v1"}]}),
            Job(user_id=user.id, app_slug="thumbnail", job_type="thumbnail.generate",
                status=JOB_ERROR, progress=25, error="Fixture: không tạo được output",
                params={"topic": "Thumbnail lỗi", "aspect_ratio": "16:9", "count": 1}),
        ])
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
