"""
H5 — app thumbnail: handler + giá credit. Gọi Gemini được MOCK (không gọi API
thật, không tốn tiền). Khoá ba tính chất tiền/độ bền:
- thiếu topic hoặc thiếu GEMINI_API_KEY → NÉM (nền tảng hoàn credit);
- gọi Gemini thành công → lưu đúng số ảnh vào storage + trả image_keys;
- credit_cost = số ảnh × đơn giá (là hàm, theo tham số).
"""
from __future__ import annotations

import base64

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


def test_gemini_loi_thi_nem_va_che_khoa(storage, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "sieu-bi-mat-key-123")
    import httpx
    monkeypatch.setattr(httpx, "post",
                        lambda *a, **k: _FakeResp(403, {}, text="denied key=sieu-bi-mat-key-123"))
    from apps.thumbnail import jobs
    with pytest.raises(RuntimeError) as ei:
        jobs.handle({"topic": "abc", "owner_id": "u1"})
    assert "sieu-bi-mat-key-123" not in str(ei.value)   # khoá bị che
