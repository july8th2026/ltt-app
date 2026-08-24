"""H39/G3b — vé console và cầu WebSocket.

Vé console là **quyền xem màn hình máy của khách**. Nên test ở đây không kiểm
"hàm chạy được không" mà kiểm bốn cách nó có thể bị lạm dụng:

1. dùng lại một vé đã tiêu (URL rò ra lịch sử trình duyệt, ảnh chụp màn hình);
2. đổi `instance_id` trên URL để nhìn máy người khác;
3. dùng vé của người khác;
4. dùng một vé cũ sau khi máy đã đổi chủ hoặc đã bị xoá.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from apps.vps.services import console
from apps.vps.tables import VpsConsoleVe, VpsInstance


@pytest.fixture()
def db():
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401

    e = create_engine("sqlite://")
    dbmod.Base.metadata.create_all(e, tables=[
        t for t in dbmod.Base.metadata.sorted_tables
        if t.name in ("vps_console_ve", "vps_instance")])
    s = sessionmaker(bind=e)()
    try:
        yield s
    finally:
        s.close()


def _may(db, user_id="u1", trang_thai="dang_chay", vmid=200):
    m = VpsInstance(user_id=user_id, plan_id="vps-nho", os_id="win10",
                    gateway_id="gw1", trang_thai=trang_thai, vmid=vmid)
    db.add(m)
    db.commit()
    return m


# ── 1. Cấp và tiêu ──────────────────────────────────────────────────────────

def test_ve_dung_duoc_dung_MOT_lan(db):
    m = _may(db)
    ve = console.cap_ve(db, m, "u1", cong=5901, pve_ve="PVEVNC:abc")
    may, cong, pve_ve = console.tieu_ve(db, ve, m.id, "u1")
    assert (may.id, cong, pve_ve) == (m.id, 5901, "PVEVNC:abc")
    with pytest.raises(console.VeKhongHopLeError):
        console.tieu_ve(db, ve, m.id, "u1")


def test_ve_proxmox_bi_XOA_khoi_CSDL_ngay_khi_tieu(db):
    """Vé của Proxmox là một chứng chỉ thật. Nó không có lý do gì nằm lại trong
    CSDL sau khi đã dùng — và nó sống nhiều nhất `HAN_VE_GIAY` giây."""
    m = _may(db)
    ve = console.cap_ve(db, m, "u1", cong=5901, pve_ve="PVEVNC:bi-mat")
    console.tieu_ve(db, ve, m.id, "u1")
    con = db.query(VpsConsoleVe).all()
    assert not any("bi-mat" in (x.pve_ve or "") for x in con)


def test_CSDL_khong_luu_ve_tho_ma_luu_bam(db):
    """Ai đọc được CSDL — bản sao lưu, một truy vấn lỡ tay — thì đọc được vé,
    và vé là quyền xem màn hình máy của khách."""
    m = _may(db)
    ve = console.cap_ve(db, m, "u1")
    luu = db.query(VpsConsoleVe).one()
    assert luu.id != ve
    assert len(luu.id) == 64 and ve not in luu.id


def test_ve_het_han_thi_khong_tieu_duoc(db):
    m = _may(db)
    ve = console.cap_ve(db, m, "u1")
    cu = db.query(VpsConsoleVe).one()
    cu.created_at = datetime.now(timezone.utc) - timedelta(
        seconds=console.HAN_VE_GIAY + 5)
    db.commit()
    with pytest.raises(console.VeKhongHopLeError):
        console.tieu_ve(db, ve, m.id, "u1")


# ── 2. Bốn cách lạm dụng ────────────────────────────────────────────────────

def test_doi_instance_id_tren_URL_thi_ve_vo_hieu(db):
    """Vé buộc vào (khách, máy). Đổi id trên URL không nhìn được máy khác."""
    m1, m2 = _may(db), _may(db, vmid=201)
    ve = console.cap_ve(db, m1, "u1")
    with pytest.raises(console.VeKhongHopLeError):
        console.tieu_ve(db, ve, m2.id, "u1")


def test_ve_cua_nguoi_khac_thi_vo_hieu(db):
    m = _may(db, user_id="u1")
    ve = console.cap_ve(db, m, "u1")
    with pytest.raises(console.VeKhongHopLeError):
        console.tieu_ve(db, ve, m.id, "u2")


def test_may_doi_chu_giua_luc_ve_con_song_thi_van_chan(db):
    """Lớp 3: vé đúng nhưng trạng thái đã đổi trong lúc vé còn sống."""
    m = _may(db, user_id="u1")
    ve = console.cap_ve(db, m, "u1")
    m.user_id = "u2"
    db.commit()
    with pytest.raises(console.VeKhongHopLeError):
        console.tieu_ve(db, ve, m.id, "u1")


def test_may_da_xoa_thi_khong_mo_console_duoc(db):
    m = _may(db)
    ve = console.cap_ve(db, m, "u1")
    m.trang_thai = "da_xoa"
    db.commit()
    with pytest.raises(console.VeKhongHopLeError):
        console.tieu_ve(db, ve, m.id, "u1")


def test_may_chua_co_vmid_thi_khong_mo_console_duoc(db):
    m = _may(db, vmid=None)
    ve = console.cap_ve(db, m, "u1")
    with pytest.raises(console.VeKhongHopLeError):
        console.tieu_ve(db, ve, m.id, "u1")


def test_ve_bia_ra_thi_vo_hieu(db):
    m = _may(db)
    console.cap_ve(db, m, "u1")
    for xau in ("", "khong-phai-ve", "x" * 64):
        with pytest.raises(console.VeKhongHopLeError):
            console.tieu_ve(db, xau, m.id, "u1")


# ── 3. Bảng vé không được phình mãi ─────────────────────────────────────────

def test_ve_cu_bi_don_bot(db):
    """Bảng vé chỉ để bắc cầu, không phải để lưu lịch sử."""
    m = _may(db)
    for _ in range(console.GIU_TOI_DA_MOI_MAY + 6):
        console.cap_ve(db, m, "u1")
        time.sleep(0.001)          # để `created_at` khác nhau, sắp xếp mới ổn định
    assert db.query(VpsConsoleVe).count() <= console.GIU_TOI_DA_MOI_MAY + 1


# ── 4. Ghép URL của Proxmox ─────────────────────────────────────────────────

class _CauHinh:
    base_url = "https://192.168.2.168:8006"
    node = "pve"


def test_ghep_dung_URL_websocket_cua_proxmox():
    """Ghép sai thì lỗi hiện ra dưới dạng 'console trắng', không dưới dạng một
    thông báo nào — nên nó phải có test riêng."""
    u = console.dia_chi_websocket_proxmox(
        _CauHinh(), 200, {"port": "5900", "ticket": "PVEVNC:abc/def+gh=="})
    assert u.startswith("wss://192.168.2.168:8006/api2/json/nodes/pve/qemu/200/"
                        "vncwebsocket?port=5900&vncticket=")
    assert "/" not in u.split("vncticket=")[1], "ticket phai duoc ma hoa URL"
    assert "+" not in u.split("vncticket=")[1]


def test_thieu_port_hoac_ticket_thi_NEM_chu_khong_ghep_bua():
    for thieu in ({"ticket": "x"}, {"port": 5900}, {}):
        with pytest.raises(console.VeKhongHopLeError):
            console.dia_chi_websocket_proxmox(_CauHinh(), 200, thieu)
