"""test_536 — nút "Nghe thử câu đầu (miễn phí)" nối cửa `/nghe-thu-van-ban` (U-13).

🔴 16/09/2026: cửa có từ 08/09 (DV-015) mà KHÔNG nút nào trên giao diện gọi tới —
`grep` 0 khớp trong `*.js`/`*.html`. Phép kiểm này đỏ nếu nút hoặc lời gọi biến mất.
"""
from __future__ import annotations

import pathlib
import re

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]
JS = GOC / "server" / "static" / "voice.js"


@pytest.fixture()
def khach(tmp_path, monkeypatch):
    """Một khách đã đăng nhập, trên SQLite tạm. Không cần credit — cửa này
    miễn phí. Chép khuôn từ `test_500`/`test_357`."""
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'nut-nghe-cau.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-nut-nghe-cau")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import apps.ltt_voice.tables  # noqa: F401
    import platform_core.models  # noqa: F401

    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from platform_core.users import tao_nguoi_dung

    gen = dbmod.get_session()
    db = next(gen)
    try:
        u = tao_nguoi_dung(db, email="nut-nghe-cau@test.com",
                           password="matkhau-tot-12", is_verified=True)
        db.commit()
        uid = str(u.id)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    from fastapi.testclient import TestClient

    from server.app import create_app
    client = TestClient(create_app(), base_url="https://testserver",
                        follow_redirects=False)
    login = client.get("/login")
    m = re.search(r'name="csrf_token" value="([^"]+)"', login.text)
    assert m
    r = client.post("/login", data={"username": "nut-nghe-cau@test.com",
                                    "password": "matkhau-tot-12",
                                    "csrf_token": m.group(1)})
    assert r.status_code in (200, 302, 303)
    try:
        yield client, uid
    finally:
        client.close()
        dbmod.reset_engine()


def test_studio_co_nut_va_tran_lay_tu_nghe_thu_cua_toi(khach):
    from apps.ltt_voice import nghe_thu_cua_toi as NT
    client, _uid = khach
    r = client.get("/ltt-voice")
    assert r.status_code == 200
    assert 'id="lv-nut-nghe-cau"' in r.text
    assert f'data-tran="{NT.TRAN_KY_TU}"' in r.text
    assert 'id="lv-nghe-cau-bao"' in r.text and 'role="status"' in r.text


def test_voice_js_goi_dung_cua_voi_preset_va_csrf():
    js = JS.read_text(encoding="utf-8")
    assert "ganNgheCau(form, oText, duong);" in js
    khoi = js[js.index("function ganNgheCau"):js.index("function ganPhatDan")]
    assert '"/nghe-thu-van-ban"' in khoi
    assert 'fd.append("preset", g.slice(2))' in khoi
    assert 'fd.append("csrf_token"' in khoi
    # chỉ giọng mẫu: cửa không nhận voice_id
    assert 'g.indexOf("m:") !== 0' in khoi and "voice_id" not in khoi
    # hiện câu lỗi đã dịch của máy chủ, không tự viết câu
    assert "noi(d.loi)" in khoi
    # CSP production `media-src 'self' blob:` chan `data:` (E2E 17/09): phai phat qua blob:
    assert "URL.createObjectURL(new Blob(" in khoi
    assert '"data:audio' not in khoi


def test_csp_that_khong_cho_data_media():
    """Doi chung: neu mot ngay CSP cho `data:` thi test tren van dung, nhung ly do da doi."""
    src = (GOC / "server" / "app.py").read_text(encoding="utf-8")
    dong = [l for l in src.splitlines() if "media-src" in l and "blob:" in l]
    assert dong and "data:" not in dong[0]
