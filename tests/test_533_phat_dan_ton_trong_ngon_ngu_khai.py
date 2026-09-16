"""
W4' (16/09/2026) — cửa `/phat-dan` ("Nghe ngay") phải đưa NGÔN NGỮ ĐÃ KHAI tới
cổng làn, và chặn TRƯỚC khi giữ credit.

🔴 Lỗ đo được: `_p_phat_dan.py` gọi `features.chuan_hoa` KHÔNG có `ngon_ngu`, nên
   khách khai "Tiếng Anh" ở Studio + giọng mẫu tiếng Việt vẫn đi tiếp — cổng chỉ
   còn đoán từ văn bản (có dấu ⇒ "vi" ⇒ khớp giọng). `/tao` đã chặn đúng ca này.

⭐ Phép đo phân biệt được hai bản: bản cũ đi qua cổng rồi đâm vào `giu_cho` với
   tài khoản 0 credit ⇒ 402; bản sửa dừng ở cổng ⇒ 400 `voice_language_mismatch`.
"""
from __future__ import annotations

import pathlib
import re

import pytest

JS = pathlib.Path(__file__).resolve().parents[1] / "server" / "static" / "voice.js"


@pytest.fixture()
def khach(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'voice-533.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-voice-533")
    monkeypatch.setenv("LTT_VOICE_STREAM", "1")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import apps.ltt_voice.tables  # noqa: F401
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    from platform_core.storage import LocalStorage, set_storage
    from platform_core.users import tao_nguoi_dung
    set_storage(LocalStorage(str(tmp_path / "store")))
    gen = dbmod.get_session()
    db = next(gen)
    try:
        tao_nguoi_dung(db, email="pd-533@test.com", password="matkhau-tot-12",
                       is_verified=True)
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    from fastapi.testclient import TestClient

    from server.app import create_app
    client = TestClient(create_app(), base_url="https://testserver",
                        follow_redirects=False)
    m = re.search(r'name="csrf_token" value="([^"]+)"', client.get("/login").text)
    assert m
    client.post("/login", data={"username": "pd-533@test.com",
                                "password": "matkhau-tot-12",
                                "csrf_token": m.group(1)})
    trang = client.get("/ltt-voice").text
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', trang).group(1)
    try:
        yield client, csrf
    finally:
        client.close()
        set_storage(None)
        dbmod.reset_engine()


def test_khai_EN_voi_giong_mau_VIET_bi_chan_truoc_credit(khach):
    client, csrf = khach
    r = client.post("/ltt-voice/phat-dan", data={
        "csrf_token": csrf, "text": "Xin chào, đây là bài kiểm tra.",
        "preset": "Ngọc Huyền", "ngon_ngu": "en"})
    assert r.status_code == 400, (r.status_code, r.text[:300])
    d = r.json()
    assert d["ok"] is False
    assert d["ma_loi"] == "voice_language_mismatch"


def test_khong_khai_thi_van_di_tiep_toi_cong_credit(khach):
    """Đối chứng trong cùng fixture: bỏ `ngon_ngu` (auto) thì cổng làn cho qua —
    lượt dừng ở bước credit (tài khoản 0 credit), không phải ở cổng làn."""
    client, csrf = khach
    r = client.post("/ltt-voice/phat-dan", data={
        "csrf_token": csrf, "text": "Xin chào, đây là bài kiểm tra.",
        "preset": "Ngọc Huyền"})
    assert r.status_code != 400 or r.json().get("ma_loi") != "voice_language_mismatch"


def test_js_nghe_ngay_gui_ngon_ngu_va_noi_ro_toc_do():
    js = JS.read_text(encoding="utf-8")
    i = js.index("function ganPhatDan")
    than = js[i:i + 6000]
    assert 'fd.append("ngon_ngu"' in than
    assert 'getAttribute("data-nhan-toc-do")' in than
