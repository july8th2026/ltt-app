"""Nexus N3.1 — agent tham chiếu, chạy thật qua HTTP.

Ba file trước (`test_223`–`test_228`) kiểm từng nửa một. File này kiểm **hai nửa
có gặp nhau không**: agent tự dựng chuỗi ký ở máy khách, server tự dựng lại ở
control plane, và nếu hai bên lệch **một dấu xuống dòng** thì mọi chữ ký hợp lệ
đều bị từ chối — một sự cố rất khó đọc từ phía khách, vì nó trông y hệt "sai
khoá".

Vì vậy ở đây dựng **một máy chủ HTTP thật** (uvicorn, cổng ngẫu nhiên) thay vì
gọi thẳng hàm. Một test gọi hàm sẽ dùng chung `canonical()` cho cả hai bên và
vì thế **không bao giờ** phát hiện được lớp lỗi đó.

Kiểm thêm thứ không nhìn thấy được từ phía server: khoá riêng nằm trên đĩa ở
dạng nào.
"""
from __future__ import annotations

import socket
import sys
import threading
import time

import pytest


def _cong_trong() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture()
def may_chu(tmp_path, monkeypatch):
    """Control plane thật trên một cổng ngẫu nhiên. Trả `(base_url, tmp)`."""
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'agent_e2e.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "agent-e2e-secret")
    monkeypatch.setenv("LTT_NEXUS", "1")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)

    from platform_core.public_api import limits
    limits.reset()

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    import uvicorn

    from server.app import create_app

    cong = _cong_trong()
    config = uvicorn.Config(create_app(), host="127.0.0.1", port=cong,
                            log_level="error")
    server = uvicorn.Server(config)
    luong = threading.Thread(target=server.run, daemon=True)
    luong.start()

    for _ in range(200):                       # tối đa ~10 giây
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


def _ma_ghep() -> str:
    from platform_core.db import get_session
    from platform_core.nexus import devices
    from platform_core.users import tao_nguoi_dung

    gen = get_session()
    db = next(gen)
    try:
        user = tao_nguoi_dung(db, email="e2e@example.com", password="x" * 24,
                              is_verified=True)
        db.flush()
        _row, ma = devices.tao_ma_ghep(db, user_id=user.id)
        db.commit()
        return ma
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def _agent(base_url: str, thu_muc):
    from nexus_agent.client import NexusClient
    from nexus_agent.keystore import Keystore

    return NexusClient(base_url, Keystore(thu_muc / "danh_tinh"))


# ── Hai nửa có gặp nhau không ────────────────────────────────────────────────

def test_ghep_roi_nhip_tim_QUA_HTTP_THAT(may_chu, monkeypatch):
    """Đây là phép thử mà một test gọi-thẳng-hàm không thay được.

    Agent ký ở phía nó, server kiểm ở phía kia, qua một socket thật. Lệch một
    dấu xuống dòng trong chuỗi ký là test này đỏ.
    """
    monkeypatch.setenv("LTT_NEXUS_AGENT_ALLOW_PLAINTEXT_KEY", "1")
    base_url, tmp = may_chu
    agent = _agent(base_url, tmp)

    device_id = agent.ghep(_ma_ghep(), ten_may="May E2E", platform=sys.platform)
    assert device_id

    tra_loi = agent.nhip_tim()
    assert tra_loi["ok"] is True
    assert tra_loi["revoked"] is False


def test_doi_ve_qua_HTTP_that(may_chu, monkeypatch):
    from platform_core.db import get_session
    from platform_core.nexus import devices, sessions

    monkeypatch.setenv("LTT_NEXUS_AGENT_ALLOW_PLAINTEXT_KEY", "1")
    base_url, tmp = may_chu
    agent = _agent(base_url, tmp)
    device_id = agent.ghep(_ma_ghep())

    gen = get_session()
    db = next(gen)
    try:
        row = db.get(devices.NexusDevice, device_id)
        _r, ve = sessions.cap_ve(db, user_id=row.user_id, device=row)
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    ket = agent.doi_ve(ve)
    assert ket["quyen"] == sessions.QUYEN_DIEU_KHIEN


def test_ma_sai_thi_KHONG_giu_lai_khoa_vua_sinh(may_chu, monkeypatch):
    """Giữ một khoá mà server không biết chỉ gây nhầm lẫn ở lần chạy sau."""
    from nexus_agent.client import AgentError

    monkeypatch.setenv("LTT_NEXUS_AGENT_ALLOW_PLAINTEXT_KEY", "1")
    base_url, tmp = may_chu
    agent = _agent(base_url, tmp)

    with pytest.raises(AgentError):
        agent.ghep("ZZZZZZZZ")
    assert agent.ks.da_co_khoa() is False


# ── Thu hồi: nút của khách phải có tác dụng thật ─────────────────────────────

def test_bi_thu_hoi_thi_agent_DUNG_HAN_va_xoa_danh_tinh(may_chu, monkeypatch):
    """Một agent tiếp tục gõ cửa sau khi bị thu hồi biến nút 'Thu hồi' của
    khách thành nút trang trí."""
    from platform_core.db import get_session
    from platform_core.nexus import devices

    monkeypatch.setenv("LTT_NEXUS_AGENT_ALLOW_PLAINTEXT_KEY", "1")
    base_url, tmp = may_chu
    agent = _agent(base_url, tmp)
    device_id = agent.ghep(_ma_ghep())

    gen = get_session()
    db = next(gen)
    try:
        devices.thu_hoi(db, db.get(devices.NexusDevice, device_id), by="owner")
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    # `ngu` gia: mot vong lap chi kiem duoc bang cach cho 60 giay la mot vong
    # lap khong ai kiem.
    ly_do = agent.chay(so_nhip=5, ngu=lambda _s: None)
    assert ly_do == "revoked"
    assert agent.ks.da_co_khoa() is False


def test_khong_ket_noi_duoc_thi_LUI_DAN_chu_khong_dung(monkeypatch, tmp_path):
    """Mất mạng là chuyện thường trên máy khách. Dừng hẳn vì một lần timeout
    nghĩa là máy biến mất khỏi danh sách cho tới khi có người đăng nhập vào."""
    from nexus_agent.client import NexusClient
    from nexus_agent.keystore import Keystore

    monkeypatch.setenv("LTT_NEXUS_AGENT_ALLOW_PLAINTEXT_KEY", "1")
    ks = Keystore(tmp_path / "dt")
    ks.sinh_khoa()
    ks.luu_device_id("khong-ton-tai")

    agent = NexusClient(f"http://127.0.0.1:{_cong_trong()}", ks)   # khong ai nghe
    cho = []
    ly_do = agent.chay(so_nhip=3, ngu=cho.append)

    assert ly_do == "het so nhip"
    assert cho == sorted(cho), "thoi gian cho phai TANG dan"
    assert cho[-1] > cho[0], "khong thay lui dan"
    assert ks.da_co_khoa() is True, "loi mang KHONG duoc xoa danh tinh"


# ── Khoá riêng nằm trên đĩa ở dạng nào ───────────────────────────────────────

def test_sinh_khoa_KHONG_tra_ve_khoa_rieng(monkeypatch, tmp_path):
    """Một giá trị đã trả về là một giá trị có thể bị log."""
    from nexus_agent.keystore import Keystore

    monkeypatch.setenv("LTT_NEXUS_AGENT_ALLOW_PLAINTEXT_KEY", "1")
    ks = Keystore(tmp_path / "dt")
    tra_ve = ks.sinh_khoa()

    assert tra_ve.startswith("ltt_dev_")
    assert tra_ve == ks.doc_public()
    # Khoa rieng doc duoc, nhung phai di lay chu khong duoc dua tan tay.
    assert len(ks.doc_khoa()) == 32


@pytest.mark.skipif(not sys.platform.startswith("win"),
                    reason="DPAPI chi co tren Windows")
def test_tren_WINDOWS_khoa_tren_dia_KHONG_phai_ban_tho(tmp_path):
    """Chép file không được bằng nhân bản máy (Q93 ràng buộc 1, T3).

    Nếu file trên đĩa **là** 32 byte khoá thô thì mọi lời hứa về 'khoá không rời
    máy' chỉ còn là một câu trong tài liệu.
    """
    from nexus_agent.keystore import Keystore

    ks = Keystore(tmp_path / "dt")
    ks.sinh_khoa()
    tren_dia = ks.key_path.read_bytes()
    that = ks.doc_khoa()

    assert len(that) == 32
    assert tren_dia != that, "khoa dang nam tho tren dia"
    assert that not in tren_dia, "khoa tho nam LOT BEN TRONG file"
    assert len(tren_dia) > 32, "DPAPI phai lam file dai them"


@pytest.mark.skipif(sys.platform.startswith("win"),
                    reason="chi kiem duong du phong cua may khong phai Windows")
def test_ngoai_WINDOWS_duong_plaintext_mac_dinh_DONG(tmp_path, monkeypatch):
    from nexus_agent.keystore import Keystore, KeystoreError

    monkeypatch.delenv("LTT_NEXUS_AGENT_ALLOW_PLAINTEXT_KEY", raising=False)
    with pytest.raises(KeystoreError):
        Keystore(tmp_path / "dt").sinh_khoa()


def test_xoa_danh_tinh_xoa_CA_BA_file(monkeypatch, tmp_path):
    """Giữ `device_id` mà mất khoá thì agent gõ cửa mãi bằng một danh tính nó
    không chứng minh được."""
    from nexus_agent.keystore import Keystore

    monkeypatch.setenv("LTT_NEXUS_AGENT_ALLOW_PLAINTEXT_KEY", "1")
    ks = Keystore(tmp_path / "dt")
    ks.sinh_khoa()
    ks.luu_device_id("abc")

    ks.xoa()
    assert not ks.key_path.exists()
    assert not ks.public_path.exists()
    assert not ks.device_id_path.exists()


# ── Ranh giới AGPL ───────────────────────────────────────────────────────────

def test_agent_KHONG_import_gi_tu_engine():
    """Q93 ràng buộc 4 và `03_OSS_LICENSE.md` §5: tiến trình A không được chứa,
    import hay link mã AGPL.

    Kiểm **câu lệnh import**, không kiểm việc nhắc tên: docstring của package
    nhắc RustDesk chính là để giải thích ranh giới này, và một test cấm nhắc tên
    sẽ phạt đúng phần tài liệu làm ranh giới ấy dễ hiểu.

    Ranh giới này bị phá bằng một dòng `import` 'cho tiện', nên đó là thứ được
    canh.
    """
    import ast
    from pathlib import Path

    CAM = ("rustdesk", "hbbs", "hbbr", "libvnc", "sunshine", "moonlight")
    goc = Path(__file__).resolve().parent.parent / "nexus_agent"
    vi_pham = []

    for path in goc.rglob("*.py"):
        cay = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(cay):
            ten = []
            if isinstance(node, ast.Import):
                ten = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                ten = [node.module or ""]
            for muc in ten:
                if any(c in muc.lower() for c in CAM):
                    vi_pham.append(f"{path.name}: import {muc}")

    assert vi_pham == [], f"agent import mã của engine: {vi_pham}"


def test_agent_khong_dung_ham_co_chu_test_trong_ten():
    """Đường chạy thật không được gọi một hàm tên là `*_for_test`.

    Cái tên đó nói dối người đọc sau này về chỗ nó được dùng — và ở đây nó là
    hàm **ký mọi request của mọi máy khách**, tức là chỗ ít được phép hiểu nhầm
    nhất.
    """
    from pathlib import Path

    goc = Path(__file__).resolve().parent.parent / "nexus_agent"
    xau = [f"{p.name}" for p in goc.rglob("*.py")
           if "_for_test" in p.read_text(encoding="utf-8")]
    assert xau == [], f"duong chay that goi ham *_for_test: {xau}"
