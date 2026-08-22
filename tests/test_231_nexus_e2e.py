"""Nexus — vòng lặp sản phẩm thật, từ trình duyệt sang máy khách.

`test_223`–`test_230` kiểm từng mảnh. Chưa cái nào kiểm **cái mà khách thực sự
làm**: mở web, bấm "Ghép một máy mới", đọc mã trên màn hình, gõ mã đó vào phần
mềm trên máy tính của mình, rồi thấy máy hiện ra trong danh sách.

Chuỗi đó đi qua ba thứ được viết riêng rẽ, và chỗ chúng gặp nhau chưa từng được
chạy: mã hiện trên HTML ở dạng `ABCD-EFGH` (có gạch nối, để người ta đọc cho
nhau nghe), còn `doi_ma` chuẩn hoá lại trước khi băm. Hai bên đúng riêng thì
chưa có nghĩa là chúng khớp nhau.

Vì vậy ở đây dùng **một máy chủ HTTP thật**: phía web đi bằng cookie phiên thật
và CSRF thật, phía agent đi bằng chính `NexusClient` mà khách sẽ chạy.
"""
from __future__ import annotations

import re
import socket
import threading
import time

import pytest

PASSWORD = "mat-khau-test-e2e-rat-dai-0123456789"
EMAIL = "e2e-vongtron@example.com"


def _cong_trong() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture()
def he_thong(tmp_path, monkeypatch):
    """Control plane thật + một tài khoản đã xác thực. Trả `(base_url, tmp)`."""
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'e2e.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "e2e-secret-value")
    monkeypatch.setenv("LTT_NEXUS", "1")
    # Bảng điều khiển web-broker nằm sau cờ này từ Q101/A7 (mặc định TẮT —
    # `/nexus` nay là trang giới thiệu). Test dưới đo chính bề mặt đó nên
    # phải bật; cờ còn thì hành vi sau cờ vẫn phải đúng.
    monkeypatch.setenv("LTT_NEXUS_WEB_BROKER", "1")
    monkeypatch.setenv("LTT_NEXUS_AGENT_ALLOW_PLAINTEXT_KEY", "1")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)

    from platform_core.public_api import limits
    limits.reset()

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    from platform_core.db import get_session
    from platform_core.users import tao_nguoi_dung
    gen = get_session()
    db = next(gen)
    try:
        tao_nguoi_dung(db, email=EMAIL, password=PASSWORD, is_verified=True)
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    import uvicorn

    from server.app import create_app

    cong = _cong_trong()
    server = uvicorn.Server(uvicorn.Config(create_app(), host="127.0.0.1",
                                           port=cong, log_level="error"))
    luong = threading.Thread(target=server.run, daemon=True)
    luong.start()
    for _ in range(200):
        if getattr(server, "started", False):
            break
        time.sleep(0.05)
    else:
        pytest.fail("may chu thu khong khoi dong duoc")

    try:
        yield f"http://127.0.0.1:{cong}", tmp_path
    finally:
        server.should_exit = True
        luong.join(timeout=10)
        limits.reset()
        dbmod.reset_engine()


def _csrf(html: str) -> str:
    found = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
    assert found, "khong tim thay csrf_token"
    return found.group(1)


@pytest.fixture()
def trinh_duyet(he_thong):
    """Phiên web đã đăng nhập, bằng cookie thật."""
    import httpx

    base_url, _tmp = he_thong
    client = httpx.Client(base_url=base_url, follow_redirects=True, timeout=20)
    page = client.get("/login").text
    r = client.post("/login", data={"username": EMAIL, "password": PASSWORD,
                                    "csrf_token": _csrf(page)})
    assert r.status_code == 200, r.text[:300]
    try:
        yield client
    finally:
        client.close()


def _lay_ma(trinh_duyet) -> str:
    """Bấm 'Ghép một máy mới' và đọc mã trên màn hình, đúng như khách làm."""
    trang = trinh_duyet.get("/nexus").text
    r = trinh_duyet.post("/nexus/ma-ghep", data={"csrf_token": _csrf(trang)})
    assert r.status_code == 200, r.text[:300]

    ma = re.search(r"([23456789A-HJKMNP-Z]{4}-[23456789A-HJKMNP-Z]{4})", r.text)
    assert ma, "khong thay ma ghep tren trang"
    return ma.group(1)


# ── Vòng lặp sản phẩm ────────────────────────────────────────────────────────

def test_khach_ghep_may_va_thay_no_hien_ra(he_thong, trinh_duyet):
    """Chuỗi đầy đủ: web sinh mã → agent ghép bằng ĐÚNG chuỗi hiện trên màn
    hình → máy hiện trong danh sách.

    Mã hiện ra có gạch nối. Nếu agent hay server không nhận dạng đó thì khách gõ
    đúng thứ họ nhìn thấy mà vẫn bị từ chối — và không ai đoán ra vì sao.
    """
    from nexus_agent.client import NexusClient
    from nexus_agent.keystore import Keystore

    base_url, tmp = he_thong
    ma = _lay_ma(trinh_duyet)
    assert "-" in ma, "ma phai hien co gach noi cho de doc"

    agent = NexusClient(base_url, Keystore(tmp / "may_khach"))
    device_id = agent.ghep(ma, ten_may="May cua khach", platform="windows")
    assert device_id

    assert "May cua khach" in trinh_duyet.get("/nexus").text


def test_may_vua_ghep_hien_DANG_TAT_cho_toi_khi_co_nhip_tim(he_thong, trinh_duyet):
    """Ghép xong chưa phải là đang bật. Lẫn hai thứ thì danh sách nói máy online
    trong khi nó chưa từng kết nối lần nào."""
    from nexus_agent.client import NexusClient
    from nexus_agent.keystore import Keystore

    base_url, tmp = he_thong
    agent = NexusClient(base_url, Keystore(tmp / "may_khach"))
    agent.ghep(_lay_ma(trinh_duyet), ten_may="May B")

    trang = trinh_duyet.get("/nexus").text
    assert ("Đang tắt" in trang) or ("Offline" in trang)

    agent.nhip_tim()
    trang = trinh_duyet.get("/nexus").text
    assert ("Đang bật" in trang) or ("Online" in trang)


def test_khach_bam_THU_HOI_thi_agent_dung_han(he_thong, trinh_duyet):
    """Nút thu hồi phải có tác dụng trên máy khách, không chỉ trong CSDL."""
    from nexus_agent.client import NexusClient
    from nexus_agent.keystore import Keystore

    base_url, tmp = he_thong
    ks = Keystore(tmp / "may_khach")
    agent = NexusClient(base_url, ks)
    device_id = agent.ghep(_lay_ma(trinh_duyet), ten_may="May C")
    agent.nhip_tim()

    trang = trinh_duyet.get("/nexus").text
    r = trinh_duyet.post(f"/nexus/thu-hoi/{device_id}",
                         data={"csrf_token": _csrf(trang)})
    assert r.status_code == 200

    # Agent phat hien o nhip ke tiep va tu xoa danh tinh.
    assert agent.chay(so_nhip=3, ngu=lambda _s: None) == "revoked"
    assert ks.da_co_khoa() is False
    assert "May C" not in trinh_duyet.get("/nexus").text


def test_MOT_ma_chi_ghep_duoc_MOT_may(he_thong, trinh_duyet):
    """Mã nạn nhân đọc qua điện thoại (T1) phải chết ngay sau lần dùng đầu."""
    from nexus_agent.client import AgentError, NexusClient
    from nexus_agent.keystore import Keystore

    base_url, tmp = he_thong
    ma = _lay_ma(trinh_duyet)

    NexusClient(base_url, Keystore(tmp / "may1")).ghep(ma, ten_may="May 1")
    with pytest.raises(AgentError):
        NexusClient(base_url, Keystore(tmp / "may2")).ghep(ma, ten_may="May 2")


def test_nhat_ky_cua_khach_ghi_lai_viec_ghep(he_thong, trinh_duyet):
    """Sau sự cố, câu hỏi duy nhất quan trọng là 'chuyện gì đã xảy ra với máy
    tôi' — và nó phải trả lời được từ trang của khách."""
    from nexus_agent.client import NexusClient
    from nexus_agent.keystore import Keystore

    base_url, tmp = he_thong
    NexusClient(base_url, Keystore(tmp / "may_khach")).ghep(
        _lay_ma(trinh_duyet), ten_may="May D")

    nhat_ky = trinh_duyet.get("/nexus/nhat-ky").text
    assert ("Ghép máy" in nhat_ky) or ("Device paired" in nhat_ky)


def test_may_cua_nguoi_KHAC_khong_thu_hoi_duoc(he_thong, trinh_duyet):
    """Ràng buộc 9: thiết bị của người khác phải như không tồn tại."""
    import httpx

    from nexus_agent.client import NexusClient
    from nexus_agent.keystore import Keystore
    from platform_core.db import get_session
    from platform_core.users import tao_nguoi_dung

    base_url, tmp = he_thong
    device_id = NexusClient(base_url, Keystore(tmp / "may_khach")).ghep(
        _lay_ma(trinh_duyet), ten_may="May cua A")

    gen = get_session()
    db = next(gen)
    try:
        tao_nguoi_dung(db, email="ke-khac@example.com", password=PASSWORD,
                       is_verified=True)
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    khac = httpx.Client(base_url=base_url, follow_redirects=True, timeout=20)
    try:
        page = khac.get("/login").text
        khac.post("/login", data={"username": "ke-khac@example.com",
                                  "password": PASSWORD,
                                  "csrf_token": _csrf(page)})
        trang = khac.get("/nexus").text
        r = khac.post(f"/nexus/thu-hoi/{device_id}",
                      data={"csrf_token": _csrf(trang)}, follow_redirects=False)
        assert r.status_code == 404, f"thu hoi duoc may nguoi khac: {r.status_code}"
    finally:
        khac.close()

    assert "May cua A" in trinh_duyet.get("/nexus").text
