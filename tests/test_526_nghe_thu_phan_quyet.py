r"""D006 — NGHE THỬ VĂN BẢN CỦA KHÁCH: VẪN PHÁT khi lệch làn, chỉ NÓI RA.

## Vì sao cửa này KHÔNG chặn, trong khi `/tao` (cửa trả credit) thì chặn

`lan_ngon_ngu.quyet_dinh` là MỘT thẩm quyền cho cả hai cửa (Task 3). Cái khác
nhau là NGƯỜI GỌI dùng phán quyết đó để làm gì:

    /tao              (features.giai_giong)   ném LoiGiongNoi -> 0 job, 0 credit
    /nghe-thu-van-ban (route này)              vẫn sinh, chỉ kèm `phan_quyet`

Nghe thử không giữ credit — không có gì để bảo vệ bằng cách chặn. Và chặn ở
đây còn phản tác dụng: cửa này TỒN TẠI để khách tự NGHE thấy giọng đọc lệch
làn ra sao trước khi trả tiền một lượt thật ở `/tao`. Chặn nó là xoá đúng
lượt thử mà D006 muốn giữ.
"""
from __future__ import annotations

import re

import pytest

UID_KHAC = "00000000-0000-0000-0000-000000000000"


@pytest.fixture()
def khach(tmp_path, monkeypatch):
    """Một khách đã đăng nhập, trên SQLite tạm. Không cần credit — cửa này
    miễn phí. Chép khuôn từ `test_500`/`test_357`."""
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'nghe-thu-pq.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-nghe-thu-pq")
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
        u = tao_nguoi_dung(db, email="nghe-thu-pq@test.com",
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
    r = client.post("/login", data={"username": "nghe-thu-pq@test.com",
                                    "password": "matkhau-tot-12",
                                    "csrf_token": m.group(1)})
    assert r.status_code in (200, 302, 303)
    try:
        yield client, uid
    finally:
        client.close()
        dbmod.reset_engine()


def _csrf(client) -> str:
    m = re.search(r'name="csrf_token" value="([^"]+)"',
                  client.get("/ltt-voice").text)
    assert m
    return m.group(1)


def test_nghe_thu_lech_lan_VAN_PHAT_va_NOI_RA(khach, monkeypatch):
    """🔴 MỆNH ĐỀ TRUNG TÂM. Preset `Adam` là giọng mẫu làn `vi`; văn bản là
    một câu tiếng Anh chắc chắn — `doan_ngon_ngu` đọc ra `"en"`. `quyet_dinh`
    phải CHẶN (`cho_phep=False`) NHƯNG lượt sinh vẫn chạy (status 200, kèm
    `phan_quyet` với một câu đã dịch sẵn cho khách)."""
    client, uid = khach
    from apps.ltt_voice import nghe_thu_cua_toi
    # Đọc tên hàm sinh THẬT trước khi mock — `nghe_thu_cua_toi.sinh`, ranh
    # giới mỏng quanh `features.goi_cong` (xem docstring của chính nó).
    monkeypatch.setattr(nghe_thu_cua_toi, "sinh",
                        lambda *a, **k: b"RIFF....WAVE")
    r = client.post("/ltt-voice/nghe-thu-van-ban",
                    data={"text": "The quick brown fox jumps over the lazy "
                                 "dog that we know.",
                          "preset": "Adam", "csrf_token": _csrf(client)})
    assert r.status_code == 200, r.text
    js = r.json()
    assert js["ok"] is True, "sinh van phai chay du lech lan (D006)"
    pq = js["phan_quyet"]
    assert pq["cho_phep"] is False
    assert pq["ma_loi"] == "voice_language_mismatch"
    assert pq["cau"], "phai co cau da dich san cho khach khi cho_phep=False"


def test_nghe_thu_dung_lan_thi_KHONG_co_canh_bao(khach, monkeypatch):
    """Đối chứng: cùng đường, văn bản khớp làn giọng — `phan_quyet.cho_phep`
    phải `True` và `cau` phải rỗng (không doạ khách vô cớ)."""
    client, uid = khach
    from apps.ltt_voice import nghe_thu_cua_toi
    monkeypatch.setattr(nghe_thu_cua_toi, "sinh",
                        lambda *a, **k: b"RIFF....WAVE")
    r = client.post("/ltt-voice/nghe-thu-van-ban",
                    data={"text": "Xin chào các bạn, hôm nay trời đẹp quá.",
                          "preset": "Adam", "csrf_token": _csrf(client)})
    assert r.status_code == 200, r.text
    pq = r.json()["phan_quyet"]
    assert pq["cho_phep"] is True
    assert pq["ma_loi"] == ""
    assert pq["cau"] == ""


def test_cua_nghe_thu_HOI_tham_quyen():
    """Chốt bằng AST: `nghe_thu_van_ban` phải THẬT SỰ gọi `quyet_dinh`, không
    chỉ nhắc tên nó trong một chú thích."""
    import ast
    import inspect

    from apps.ltt_voice.routes import _p_nghe_thu
    src = inspect.getsource(_p_nghe_thu.nghe_thu_van_ban)
    goi = {getattr(n.func, "attr", "") or getattr(n.func, "id", "")
           for n in ast.walk(ast.parse(src.lstrip())) if isinstance(n, ast.Call)}
    assert "quyet_dinh" in goi
