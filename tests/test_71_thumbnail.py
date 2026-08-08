"""
H5 — app thumbnail: handler + giá credit. Gọi Gemini được MOCK (không gọi API
thật, không tốn tiền). Khoá ba tính chất tiền/độ bền:
- thiếu topic hoặc thiếu GEMINI_API_KEY → NÉM (nền tảng hoàn credit);
- gọi Gemini thành công → lưu đúng số ảnh vào storage + trả image_keys;
- credit_cost = số ảnh × đơn giá (là hàm, theo tham số).
"""
from __future__ import annotations

import base64
import io

import pytest


class _FakeResp:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


def _payload_one_image():
    b64 = base64.b64encode(b"\x89PNG-fake-bytes").decode("ascii")
    return {"candidates": [{"content": {"parts": [{"inlineData": {"data": b64}}]}}]}


@pytest.fixture()
def storage(tmp_path):
    from platform_core.storage import LocalStorage, set_storage
    st = LocalStorage(str(tmp_path / "store"))
    set_storage(st)
    try:
        yield st
    finally:
        set_storage(None)


def test_cost_theo_so_anh():
    from apps.thumbnail.manifest import MANIFEST
    assert MANIFEST.credit_cost({"count": 1}) == 5
    assert MANIFEST.credit_cost({"count": 3}) == 15
    assert MANIFEST.credit_cost({"count": 99}) == 20   # chặn trên 4 ảnh
    assert MANIFEST.credit_cost({}) == 5


def _valid_png(size=(320, 180), color=(180, 30, 25)):
    from PIL import Image
    out = io.BytesIO(); Image.new("RGB", size, color).save(out, format="PNG")
    return out.getvalue()


def test_reference_brand_va_score_ky_thuat_la_du_lieu_that():
    from apps.thumbnail.features import (brand_directive, clean_brand,
                                         technical_score, validate_reference)
    data = _valid_png()
    assert validate_reference(data, "image/png") == ("image/png", (320, 180))
    with pytest.raises(ValueError, match="MIME"):
        validate_reference(data, "image/jpeg")
    brand = clean_brand({"name": " LTT ", "primary_color": "#aa1122",
                         "secondary_color": "khong-hop-le", "font": "Barlow"})
    assert brand["primary_color"] == "#AA1122" and brand["secondary_color"] == "#111111"
    assert "brand=LTT" in brand_directive(brand)
    score = technical_score(data)
    assert score["method"] == "technical-v1" and score["width"] == 320
    assert 0 <= score["score"] <= 100


def test_reference_duoc_gui_inline_va_brand_vao_prompt(storage, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    ref = _valid_png((128, 128))
    storage.put("thumbnail/u1/refs/r1", io.BytesIO(ref), content_type="image/png")
    captured = {}
    import httpx

    def fake_post(*_args, **kwargs):
        captured.update(kwargs["json"])
        return _FakeResp(200, _payload_one_image())

    monkeypatch.setattr(httpx, "post", fake_post)
    from apps.thumbnail import jobs
    out = jobs.handle({"topic": "x", "owner_id": "u1",
                       "reference_key": "thumbnail/u1/refs/r1",
                       "reference_mime": "image/png",
                       "brand": {"name": "LTT", "font": "Barlow"}}, _Ctx("job-ref"))
    parts = captured["contents"][0]["parts"]
    assert any("inlineData" in part for part in parts)
    assert "brand=LTT" in out["prompt"]
    assert out["scores"][0]["method"] == "unavailable"  # payload mock không phải PNG thật


def test_thieu_topic_thi_nem(storage, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    from apps.thumbnail import jobs
    with pytest.raises(ValueError):
        jobs.handle({"topic": "  "})


def test_thieu_khoa_thi_nem(storage, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    from apps.thumbnail import jobs
    with pytest.raises(RuntimeError):
        jobs.handle({"topic": "abc", "owner_id": "u1"})


def test_tao_anh_thanh_cong_luu_storage(storage, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    import httpx
    monkeypatch.setattr(httpx, "post",
                        lambda *a, **k: _FakeResp(200, _payload_one_image()))

    from apps.thumbnail import jobs

    class Ctx:
        job_id = "job123"
        def progress(self, *a, **k): pass

    out = jobs.handle({"topic": "dau tu", "title": "GIAU", "count": 2,
                       "aspect_ratio": "16:9", "owner_id": "u1"}, Ctx())
    assert out["count"] == 2
    assert len(out["image_keys"]) == 2
    for k in out["image_keys"]:
        assert k.startswith("thumbnail/u1/job123/")
        assert storage.exists(k)                     # ảnh đã lưu thật


class _Ctx:
    def __init__(self, job_id): self.job_id = job_id
    def progress(self, *a, **k): pass


def test_loi_mot_anh_khong_hong_ca_job(storage, monkeypatch):
    """W1.1: một ảnh lỗi KHÔNG làm hỏng cả job — tạo được bao nhiêu tính tiền
    bấy nhiêu (credit_cost theo số ảnh THÀNH CÔNG)."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    import httpx
    calls = {"n": 0}

    def fake_post(*a, **k):
        calls["n"] += 1
        if calls["n"] == 2:                       # ảnh thứ 2 lỗi
            return _FakeResp(500, {}, text="server error")
        return _FakeResp(200, _payload_one_image())

    monkeypatch.setattr(httpx, "post", fake_post)
    from apps.thumbnail import jobs
    out = jobs.handle({"topic": "x", "count": 3, "owner_id": "u1"}, _Ctx("jobP"))
    assert out["count"] == 2                       # 2 thành công, 1 lỗi
    assert out["credit_cost"] == 2 * 5             # chỉ tính tiền 2 ảnh
    assert len(out["image_keys"]) == 2


def test_resume_khong_goi_lai_anh_da_co(storage, monkeypatch):
    """W1.1: ảnh đã lưu (worker crash rồi job bị reclaim) được DÙNG LẠI, không
    gọi Gemini lần nữa → không trả tiền API hai lần."""
    import io
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    storage.put("thumbnail/u1/jobR/0.png", io.BytesIO(b"old"),
                content_type="image/png")          # ảnh 0 đã có sẵn
    import httpx
    calls = {"n": 0}

    def fake_post(*a, **k):
        calls["n"] += 1
        return _FakeResp(200, _payload_one_image())

    monkeypatch.setattr(httpx, "post", fake_post)
    from apps.thumbnail import jobs
    out = jobs.handle({"topic": "x", "count": 2, "owner_id": "u1"}, _Ctx("jobR"))
    assert out["count"] == 2
    assert calls["n"] == 1                          # chỉ gọi Gemini cho ảnh CHƯA có
    assert out["credit_cost"] == 2 * 5


def test_khong_tao_duoc_anh_nao_thi_nem(storage, monkeypatch):
    """W1.1: KHÔNG tạo được ảnh nào → ném để nền tảng hoàn toàn bộ credit + retry."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    import httpx
    monkeypatch.setattr(httpx, "post",
                        lambda *a, **k: _FakeResp(500, {}, text="down"))
    from apps.thumbnail import jobs
    with pytest.raises(RuntimeError):
        jobs.handle({"topic": "x", "count": 2, "owner_id": "u1"}, _Ctx("jobF"))


def test_handle_dung_key_tu_engine(tmp_path, monkeypatch):
    """H8.6: thumbnail lấy key từ bộ máy APIKEYS (không còn env) + đánh dấu
    thành công lên key."""
    import io as _io  # noqa: F401
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'e.db').as_posix()}")
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEY", "mat-khoa-engine-1")
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from platform_core.storage import LocalStorage, set_storage
    set_storage(LocalStorage(str(tmp_path / "st")))
    from platform_core import api_keys
    from platform_core.models import APIKEY_CAT_IMAGE
    gen = dbmod.get_session(); db = next(gen)
    try:
        api_keys.tao_key(db, provider="gemini", credential="AIzaENGINEKEY9999",
                         categories=[APIKEY_CAT_IMAGE]); db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass

    import httpx
    monkeypatch.setattr(httpx, "post",
                        lambda *a, **k: _FakeResp(200, _payload_one_image()))
    from apps.thumbnail import jobs
    try:
        out = jobs.handle({"topic": "x", "count": 1, "owner_id": "u1"}, _Ctx("jE"))
        assert out["count"] == 1
        from sqlalchemy import select
        from platform_core.models import ApiKey
        gen = dbmod.get_session(); db = next(gen)
        try:
            k = db.execute(select(ApiKey)).scalars().first()
            assert k.total_requests >= 1 and k.total_success >= 1
        finally:
            try: next(gen)
            except StopIteration: pass
    finally:
        set_storage(None); dbmod.reset_engine()


def test_image_route_chan_cross_user(tmp_path, monkeypatch):
    """W2.6: gõ thẳng URL ảnh của người khác → 404 (kiểm sở hữu ở tầng HTTP),
    ảnh của chính mình → 200."""
    import io as _io
    import re as _re

    import platform_core.db as dbmod
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'img.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-img")
    monkeypatch.setenv("LTT_ADMIN_USERNAME", "admin")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    from platform_core.storage import LocalStorage, set_storage
    st = LocalStorage(str(tmp_path / "store")); set_storage(st)
    from platform_core.models import JOB_DONE, Job
    from platform_core.users import tao_nguoi_dung
    gen = dbmod.get_session(); db = next(gen)
    try:
        a = tao_nguoi_dung(db, email="a@img.com", password="matkhau-tot-12", is_verified=True)
        b = tao_nguoi_dung(db, email="b@img.com", password="matkhau-tot-12", is_verified=True)
        db.flush()
        seeded = Job(user_id=a.id, app_slug="thumbnail", job_type="thumbnail.generate",
                     status=JOB_DONE, progress=100,
                     params={"topic": "NOI_DUNG_CUA_A", "title": "TIEU_DE_CUA_A",
                             "aspect_ratio": "16:9", "count": 1,
                             "text_style": "bold_impact"},
                     result={"image_keys": [f"thumbnail/{a.id}/job2/0.png"]})
        db.add(seeded); db.commit(); a_id, b_id, seeded_id = a.id, b.id, seeded.id
    finally:
        try: next(gen)
        except StopIteration: pass

    st.put(f"thumbnail/{b_id}/job1/0.png", _io.BytesIO(b"PNGB"), content_type="image/png")
    st.put(f"thumbnail/{a_id}/job2/0.png", _io.BytesIO(b"PNGA"), content_type="image/png")

    from fastapi.testclient import TestClient
    from server.app import create_app
    c = TestClient(create_app(), base_url="https://testserver", follow_redirects=False)
    try:
        tok = _re.search(r'name="csrf_token" value="([^"]+)"', c.get("/login").text).group(1)
        c.post("/login", data={"username": "a@img.com",
                               "password": "matkhau-tot-12", "csrf_token": tok})
        # A đọc ảnh của B → 404
        r = c.get(f"/thumbnail/image/thumbnail/{b_id}/job1/0.png")
        assert r.status_code == 404
        # A đọc ảnh của CHÍNH MÌNH → 200
        r2 = c.get(f"/thumbnail/image/thumbnail/{a_id}/job2/0.png")
        assert r2.status_code == 200
        studio = c.get("/thumbnail")
        assert studio.status_code == 308
        assert studio.headers["location"] == "/taoanh/thumbnail"
        shell = c.get(studio.headers["location"])
        assert shell.status_code == 200
        assert "Tạo ảnh AI" in shell.text and "Thumbnail YouTube" in shell.text
        fragment = c.get("/thumbnail/studio-fragment")
        assert fragment.status_code == 200 and "TIEU_DE_CUA_A" in fragment.text
        assert "th-compare-pick" in fragment.text and "NOI_DUNG_CUA_A" not in fragment.text
        remix = c.get(f"/thumbnail/remix/{seeded_id}/0")
        assert remix.status_code == 308
        assert remix.headers["location"].startswith("/taoanh/thumbnail?")
        remix_fragment = c.get(
            f"/thumbnail/studio-fragment?remix_job_id={seeded_id}&image_index=0")
        assert (remix_fragment.status_code == 200 and
                "Đang remix từ output đã chọn" in remix_fragment.text)
        assert "NOI_DUNG_CUA_A" in remix_fragment.text and "TIEU_DE_CUA_A" in remix_fragment.text
        remix_csrf = _re.search(
            r'name="csrf_token" value="([^"]+)"', remix_fragment.text).group(1)
        import platform_core.job_submit as job_submit
        from platform_core.credit import ThieuCreditError
        monkeypatch.setattr(job_submit, "submit_with_credit",
                            lambda *_a, **_k: (_ for _ in ()).throw(ThieuCreditError("thiếu")))
        failed = c.post("/thumbnail/queue", data={
            "csrf_token": remix_csrf, "topic": "remix", "count": "1",
            "saved_reference_key": f"thumbnail/{a_id}/job2/0.png"})
        assert failed.status_code == 400
        assert st.exists(f"thumbnail/{a_id}/job2/0.png")  # lỗi submit không xóa output gốc
        c.cookies.clear()
        tok_b = _re.search(r'name="csrf_token" value="([^"]+)"', c.get("/login").text).group(1)
        c.post("/login", data={"username": "b@img.com",
                               "password": "matkhau-tot-12", "csrf_token": tok_b})
        assert c.get(f"/thumbnail/remix/{seeded_id}/0").status_code == 404
    finally:
        set_storage(None); dbmod.reset_engine()


def test_gemini_loi_thi_nem_va_che_khoa(storage, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "sieu-bi-mat-key-123")
    import httpx
    monkeypatch.setattr(httpx, "post",
                        lambda *a, **k: _FakeResp(403, {}, text="denied key=sieu-bi-mat-key-123"))
    from apps.thumbnail import jobs
    with pytest.raises(RuntimeError) as ei:
        jobs.handle({"topic": "abc", "owner_id": "u1"})
    assert "sieu-bi-mat-key-123" not in str(ei.value)   # khoá bị che
