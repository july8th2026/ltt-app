"""Nexus N2.4 — dòng thời gian mà CHỦ THIẾT BỊ đọc được.

Q93 ràng buộc 5 không nói "ghi lại hành động của admin" — nền tảng đã có
`nhat_ky_admin` làm việc đó. Nó nói hành động của admin phải để lại bản ghi
**chủ thiết bị đọc được**. Khác biệt ấy là toàn bộ nội dung của file này: một
nhật ký chỉ người làm hành động mới xem được không trả lời được câu hỏi duy nhất
quan trọng sau sự cố.

Test nặng nhất ở đây là `test_admin_thu_hoi_thi_CHU_MAY_THAY_DUOC`.
"""
from __future__ import annotations

import uuid

import pytest

def _khoa() -> str:
    """Mot khoa cong khai Ed25519 THAT.

    Truoc day cac test nay dung chuoi gia ("ltt_dev_" + "a"*64). Chuoi do luu
    xuong duoc nhung KHONG bao gio xac thuc duoc — nen test xanh trong khi mot
    thiet bi that se khong ket noi noi. Tu khi `doi_ma` kiem dang khoa o bien,
    test phai dung khoa that.
    """
    from platform_core.nexus import agent_auth

    _priv, pub = agent_auth.new_keypair_for_test()
    return pub



@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'nexus3.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine, get_session

    Base.metadata.create_all(get_engine())
    gen = get_session()
    session = next(gen)
    try:
        yield session
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
        dbmod.reset_engine()


def _user(db):
    from platform_core.users import tao_nguoi_dung

    user = tao_nguoi_dung(db, email=f"{uuid.uuid4().hex[:8]}@example.com",
                          password="x" * 24, is_verified=True)
    db.flush()
    return user


def _device(db, user):
    from platform_core.nexus import devices

    _row, ma = devices.tao_ma_ghep(db, user_id=user.id)
    return devices.doi_ma(db, code=ma,
                          public_key=_khoa(),
                          ip="198.51.100.9")


# ── Điều khoản 5: admin không đụng vào ai mà không để lại dấu ────────────────

def test_admin_thu_hoi_thi_CHU_MAY_THAY_DUOC(db):
    """Đây là lời hứa của Q93, và là chỗ dễ 'tiện tay' phá vỡ nhất.

    Nếu hành động của admin chỉ vào `nhat_ky_admin` thì khách không bao giờ biết
    — và "không có backdoor bí mật" trở thành một câu nói, không phải một tính
    chất kiểm được.
    """
    from platform_core.nexus import audit, devices

    user = _user(db)
    device = _device(db, user)
    devices.thu_hoi(db, device, by="admin:nhan-vien-1")

    dong = audit.dong_thoi_gian(db, user_id=user.id)
    thu_hoi = [d for d in dong if d["loai"] == audit.THU_HOI_THIET_BI]
    assert len(thu_hoi) == 1
    assert thu_hoi[0]["boi"] == "admin:nhan-vien-1"
    assert audit.do_admin_lam(thu_hoi[0]) is True

    chi_admin = audit.admin_da_lam_gi(db, user_id=user.id)
    assert [d["loai"] for d in chi_admin] == [audit.THU_HOI_THIET_BI]


def test_chu_tu_thu_hoi_thi_KHONG_bi_danh_dau_la_admin(db):
    """Nếu mọi thứ đều là 'admin' thì việc làm nổi bật mất hết ý nghĩa."""
    from platform_core.nexus import audit, devices

    user = _user(db)
    device = _device(db, user)
    devices.thu_hoi(db, device, by="owner")

    assert audit.admin_da_lam_gi(db, user_id=user.id) == []


def test_admin_cat_phien_thi_chu_may_cung_thay(db):
    from platform_core.nexus import audit, sessions

    user = _user(db)
    device = _device(db, user)
    _row, ve = sessions.cap_ve(db, user_id=user.id, device=device)
    phien = sessions.doi_ve(db, ticket=ve)
    sessions.thu_hoi_ve(db, phien, by="admin:nhan-vien-2")

    chi_admin = audit.admin_da_lam_gi(db, user_id=user.id)
    assert [d["loai"] for d in chi_admin] == [audit.THU_HOI_PHIEN]
    assert chi_admin[0]["boi"] == "admin:nhan-vien-2"


# ── Đầy đủ vòng đời ──────────────────────────────────────────────────────────

def test_mot_vong_doi_day_du_hien_ra_du_su_kien(db):
    from platform_core.nexus import audit, sessions

    user = _user(db)
    device = _device(db, user)
    _row, ve = sessions.cap_ve(db, user_id=user.id, device=device)
    phien = sessions.doi_ve(db, ticket=ve)
    sessions.ket_thuc(db, phien)

    loai = {d["loai"] for d in audit.dong_thoi_gian(db, user_id=user.id)}
    assert loai == {audit.GHEP, audit.CAP_VE, audit.BAT_DAU_PHIEN,
                    audit.KET_THUC_PHIEN}


def test_ghep_may_ghi_lai_IP(db):
    """'Máy đó ghép từ đâu' là câu hỏi đầu tiên khi nghi bị lừa ghép (T1)."""
    from platform_core.nexus import audit

    user = _user(db)
    _device(db, user)

    ghep = [d for d in audit.dong_thoi_gian(db, user_id=user.id)
            if d["loai"] == audit.GHEP]
    assert len(ghep) == 1
    assert "198.51.100.9" in ghep[0]["chi_tiet"]


def test_moi_nhat_truoc(db):
    from platform_core.nexus import audit, sessions

    user = _user(db)
    device = _device(db, user)
    _row, ve = sessions.cap_ve(db, user_id=user.id, device=device)
    sessions.doi_ve(db, ticket=ve)

    dong = audit.dong_thoi_gian(db, user_id=user.id)
    thoi_diem = [d["luc"] for d in dong]
    assert thoi_diem == sorted(thoi_diem, reverse=True)


def test_thu_hoi_phien_KHONG_de_ra_hai_dong_ket_thuc(db):
    """`thu_hoi_ve` cũng đóng phiên. Nếu đếm cả hai thì dòng thời gian nói phiên
    kết thúc hai lần."""
    from platform_core.nexus import audit, sessions

    user = _user(db)
    device = _device(db, user)
    _row, ve = sessions.cap_ve(db, user_id=user.id, device=device)
    phien = sessions.doi_ve(db, ticket=ve)
    sessions.thu_hoi_ve(db, phien, by="owner")

    dong = audit.dong_thoi_gian(db, user_id=user.id)
    ket = [d for d in dong if d["loai"] in (audit.KET_THUC_PHIEN,
                                            audit.THU_HOI_PHIEN)]
    assert [d["loai"] for d in ket] == [audit.THU_HOI_PHIEN]


# ── Owner-scoped ─────────────────────────────────────────────────────────────

def test_khong_lay_duoc_dong_thoi_gian_cua_nguoi_khac(db):
    from platform_core.nexus import audit, sessions

    a, b = _user(db), _user(db)
    da = _device(db, a)
    _row, ve = sessions.cap_ve(db, user_id=a.id, device=da)
    sessions.doi_ve(db, ticket=ve)

    assert audit.dong_thoi_gian(db, user_id=b.id) == []
    # Biet id may cua nguoi khac cung khong lay duoc gi.
    assert audit.dong_thoi_gian(db, user_id=b.id, device_id=da.id) == []


def test_loc_theo_mot_thiet_bi(db):
    from platform_core.nexus import audit

    user = _user(db)
    d1, d2 = _device(db, user), _device(db, user)

    chi_d1 = audit.dong_thoi_gian(db, user_id=user.id, device_id=d1.id)
    assert {d["device_id"] for d in chi_d1} == {d1.id}
    assert len(audit.dong_thoi_gian(db, user_id=user.id)) > len(chi_d1)
    assert d2.id not in {d["device_id"] for d in chi_d1}


def test_user_id_rong_khong_tra_ve_gi(db):
    from platform_core.nexus import audit

    user = _user(db)
    _device(db, user)
    assert audit.dong_thoi_gian(db, user_id="") == []
    assert audit.admin_da_lam_gi(db, user_id="") == []


# ── Không có nguồn chân lý thứ hai ───────────────────────────────────────────

def test_khong_co_bang_su_kien_rieng():
    """Thêm một bảng sự kiện sẽ tạo nguồn chân lý thứ hai: sẽ có ngày một phiên
    tồn tại mà không có dòng nhật ký (hoặc ngược lại), và lúc đối chiếu thì
    không biết tin cái nào."""
    from platform_core.db import Base

    ten_bang = set(Base.metadata.tables)
    assert "nexus_audit_events" not in ten_bang
    assert {"nexus_devices", "nexus_enrollments", "nexus_sessions"} <= ten_bang
