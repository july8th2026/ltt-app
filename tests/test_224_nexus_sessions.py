"""Nexus N2.2/N2.3 — vé phiên, dọn dẹp, và chỗ uỷ quyền được quyết.

`devices.py` trả lời "máy này của ai". Module vé trả lời "ai được vào máy này" —
và câu thứ hai mới là chỗ một lỗi biến thành việc người lạ điều khiển máy khách.

Thứ được chốt kỹ nhất ở đây là **ràng buộc nằm trong chữ ký hàm**: `cap_ve` tự
so chủ sở hữu, không có tham số nào bỏ qua được phép so đó và không có cờ
`force`. Cách sai — một hàm nhận `device_id` rồi dặn nhau "nhớ kiểm chủ trước
khi gọi" — sẽ có ngày quên, và ngày quên đó không ai thấy.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

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
                       f"sqlite:///{(tmp_path / 'nexus2.db').as_posix()}")
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


def _device(db, user, khoa: str = ""):
    from platform_core.nexus import devices

    _row, ma = devices.tao_ma_ghep(db, user_id=user.id)
    return devices.doi_ma(db, code=ma,
                          public_key=khoa or (_khoa()))


# ── Uỷ quyền: ràng buộc nằm trong chữ ký ─────────────────────────────────────

def test_chu_may_cap_duoc_ve(db):
    from platform_core.nexus import sessions

    user = _user(db)
    device = _device(db, user)
    row, ve = sessions.cap_ve(db, user_id=user.id, device=device)

    assert row.device_id == device.id
    assert row.user_id == user.id
    assert len(ve) >= 16
    assert row.ticket_digest != ve


def test_KHONG_cap_duoc_ve_cho_may_nguoi_khac(db):
    """Q93 ràng buộc 5. Đây là điều khoản dễ bị 'tiện tay' phá vỡ nhất."""
    from platform_core.nexus import devices, sessions

    chu, ke_khac = _user(db), _user(db)
    device = _device(db, chu)

    with pytest.raises(devices.NexusError):
        sessions.cap_ve(db, user_id=ke_khac.id, device=device)


def test_ham_cap_ve_khong_co_duong_bo_qua_kiem_chu(db):
    """Chốt bằng CHỮ KÝ, không bằng hành vi.

    Nếu ai đó thêm `force=` hay đổi tham số `device` thành `device_id` thì việc
    kiểm chủ sở hữu không còn nằm trong hàm nữa — và test hành vi ở trên vẫn có
    thể xanh trong khi cửa đã mở.
    """
    import inspect

    from platform_core.nexus import sessions

    sig = inspect.signature(sessions.cap_ve)
    assert "device" in sig.parameters, "phai nhan doi tuong thiet bi"
    assert "device_id" not in sig.parameters, (
        "nhan id nghia la noi goi phai tu kiem chu — do la cho se quen")
    for cam in ("force", "bo_qua", "skip_owner_check", "as_admin"):
        assert cam not in sig.parameters, f"khong duoc co duong bo qua: {cam}"

    src = inspect.getsource(sessions.cap_ve)
    assert "device.user_id != xin" in src, "phep so chu so huu phai nam trong ham"


def test_may_da_thu_hoi_thi_khong_cap_ve(db):
    from platform_core.nexus import devices, sessions

    user = _user(db)
    device = _device(db, user)
    devices.thu_hoi(db, device, by="owner")

    with pytest.raises(devices.NexusError):
        sessions.cap_ve(db, user_id=user.id, device=device)


def test_quyen_la_thi_tu_choi(db):
    from platform_core.nexus import devices, sessions

    user = _user(db)
    device = _device(db, user)
    with pytest.raises(devices.NexusError):
        sessions.cap_ve(db, user_id=user.id, device=device, quyen="toan_quyen")


# ── Vé dùng một lần ──────────────────────────────────────────────────────────

def test_ve_dung_mot_lan(db):
    from platform_core.nexus import devices, sessions

    user = _user(db)
    device = _device(db, user)
    _row, ve = sessions.cap_ve(db, user_id=user.id, device=device)

    phien = sessions.doi_ve(db, ticket=ve)
    assert phien.consumed_at is not None

    with pytest.raises(devices.NexusError):
        sessions.doi_ve(db, ticket=ve)


def test_ve_het_han_thi_khong_doi_duoc(db):
    from platform_core.nexus import devices, sessions

    user = _user(db)
    device = _device(db, user)
    row, ve = sessions.cap_ve(db, user_id=user.id, device=device)

    with pytest.raises(devices.NexusError):
        sessions.doi_ve(db, ticket=ve, now=row.expires_at + timedelta(seconds=1))


def test_thu_hoi_may_GIUA_luc_cap_ve_va_luc_dung(db):
    """Đây là lúc việc thu hồi phải có tác dụng, chứ không phải lúc nào khác.

    Vé đã cấp hợp lệ; chủ máy bấm thu hồi; vé phải chết. Nếu `doi_ve` tin trạng
    thái lúc cấp thay vì kiểm lại, nút thu hồi trở thành nút trang trí.
    """
    from platform_core.nexus import devices, sessions

    user = _user(db)
    device = _device(db, user)
    _row, ve = sessions.cap_ve(db, user_id=user.id, device=device)
    devices.thu_hoi(db, device, by="owner")

    with pytest.raises(devices.NexusError):
        sessions.doi_ve(db, ticket=ve)


def test_moi_ly_do_tu_choi_ve_noi_cung_mot_cau(db):
    from platform_core.nexus import devices, sessions

    user = _user(db)
    device = _device(db, user)
    row, ve = sessions.cap_ve(db, user_id=user.id, device=device)
    _r2, ve2 = sessions.cap_ve(db, user_id=user.id, device=device)
    sessions.doi_ve(db, ticket=ve2)

    loi = []
    for kwargs in ({"ticket": "z" * 40},
                   {"ticket": ve, "now": row.expires_at + timedelta(seconds=1)},
                   {"ticket": ve2}):
        with pytest.raises(devices.NexusError) as exc:
            sessions.doi_ve(db, **kwargs)
        loi.append(str(exc.value))

    assert len(set(loi)) == 1, f"lo ra ba thong diep khac nhau: {loi}"


def test_ma_ghep_va_ve_bam_KHAC_khong_gian(db):
    """Nếu hai loại bí mật băm cùng cách, một digest lấy ở bảng này đem thử được
    ở bảng kia."""
    from platform_core.nexus import devices, sessions

    chung = "ABCD2345"
    assert devices.digest_code(chung) != sessions.digest_ticket(chung)


# ── Bản ghi kiểm toán ────────────────────────────────────────────────────────

def test_ket_thuc_ghi_them_chu_khong_sua_qua_khu(db):
    from platform_core.nexus import sessions

    user = _user(db)
    device = _device(db, user)
    _row, ve = sessions.cap_ve(db, user_id=user.id, device=device,
                               controller_ip="203.0.113.7")
    phien = sessions.doi_ve(db, ticket=ve)
    cap_luc, ip = phien.issued_at, phien.controller_ip

    assert sessions.ket_thuc(db, phien) is True
    assert phien.ended_at is not None
    assert phien.end_reason == sessions.KET_THUC_BINH_THUONG
    # Phan qua khu giu nguyen.
    assert phien.issued_at == cap_luc and phien.controller_ip == ip
    # Dong lan hai khong ghi de ly do lan dau.
    assert sessions.ket_thuc(db, phien, ly_do=sessions.KET_THUC_THU_HOI) is False
    assert phien.end_reason == sessions.KET_THUC_BINH_THUONG


def test_thu_hoi_ve_cat_phien_dang_chay_va_ghi_ai_lam(db):
    from platform_core.nexus import devices, sessions

    user = _user(db)
    device = _device(db, user)
    _row, ve = sessions.cap_ve(db, user_id=user.id, device=device)
    phien = sessions.doi_ve(db, ticket=ve)

    with pytest.raises(devices.NexusError):
        sessions.thu_hoi_ve(db, phien, by="")

    assert sessions.thu_hoi_ve(db, phien, by="owner") is True
    assert phien.revoked_by == "owner"
    assert phien.end_reason == sessions.KET_THUC_THU_HOI
    assert phien.dang_chay() is False


def test_dang_mo_thay_phien_dang_chay(db):
    """Dùng để hiện chỉ báo 'đang có người điều khiển' (ràng buộc 7)."""
    from platform_core.nexus import sessions

    user = _user(db)
    device = _device(db, user)
    assert sessions.dang_mo(db, device_id=device.id) == []

    _row, ve = sessions.cap_ve(db, user_id=user.id, device=device)
    phien = sessions.doi_ve(db, ticket=ve)
    assert [s.id for s in sessions.dang_mo(db, device_id=device.id)] == [phien.id]

    sessions.ket_thuc(db, phien)
    assert sessions.dang_mo(db, device_id=device.id) == []


def test_ve_chua_dung_KHONG_phai_phien_dang_chay(db):
    """Cấp vé không phải là mở phiên. Nếu lẫn hai thứ, chỉ báo sẽ sáng lên khi
    chưa có ai vào máy — và người dùng sẽ học cách bỏ qua nó."""
    from platform_core.nexus import sessions

    user = _user(db)
    device = _device(db, user)
    sessions.cap_ve(db, user_id=user.id, device=device)
    assert sessions.dang_mo(db, device_id=device.id) == []


def test_lich_su_la_be_mat_cua_KHACH(db):
    from platform_core.nexus import sessions

    a, b = _user(db), _user(db)
    da = _device(db, a)
    _row, ve = sessions.cap_ve(db, user_id=a.id, device=da)
    sessions.doi_ve(db, ticket=ve)

    assert len(sessions.lich_su(db, user_id=a.id)) == 1
    assert sessions.lich_su(db, user_id=b.id) == []


# ── Dọn dẹp (N2.2) ───────────────────────────────────────────────────────────

def test_don_ma_giu_ban_da_dung_lau_hon_ban_khong_ai_dung(db):
    """Mã đã dùng là một mẩu kiểm toán; mã hết hạn không ai dùng thì không."""
    from platform_core.nexus import devices

    user = _user(db)
    now = datetime.now(timezone.utc)

    # Da dung 40 ngay truoc: van phai con (nguong 365).
    r1, ma1 = devices.tao_ma_ghep(db, user_id=user.id, now=now - timedelta(days=40))
    devices.doi_ma(db, code=ma1, public_key=_khoa(),
                   now=now - timedelta(days=40))
    # Het han 40 ngay truoc, khong ai dung: phai bi xoa (nguong 30).
    devices.tao_ma_ghep(db, user_id=user.id, now=now - timedelta(days=40))

    assert devices.don_ma_het_han(db, now=now) == 1
    assert db.get(type(r1), r1.id) is not None


def test_don_ma_khong_cham_ma_con_song(db):
    from platform_core.nexus import devices

    user = _user(db)
    row, _ma = devices.tao_ma_ghep(db, user_id=user.id)
    assert devices.don_ma_het_han(db) == 0
    assert db.get(type(row), row.id) is not None


def test_don_nexus_KHONG_chay_khi_co_tat(db, monkeypatch):
    """Cờ tắt = không chạm gì cả, không phải 'thử rồi bỏ qua lỗi'.

    Khi Nexus tắt, bảng của nó có thể còn chưa được migrate; truy vấn một bảng
    chưa tồn tại mỗi lượt bảo trì sẽ làm log ngập.
    """
    from platform_core import job_runner, nexus

    monkeypatch.delenv(nexus.FLAG_ENV, raising=False)
    assert job_runner._don_nexus(db) == 0


def test_don_nexus_nam_trong_vong_BAO_TRI_chu_khong_trong_vong_job():
    """Số tiến trình worker mặc định bằng số GPU: một việc nền đặt sai chỗ sẽ
    chạy ở mọi tiến trình. Đó là nguyên nhân gốc của cả ba lỗi P0 của H36."""
    import inspect

    from platform_core import job_runner

    assert "_don_nexus(db)" in inspect.getsource(job_runner._quet_canh_bao)
    assert "_quet_canh_bao()" in inspect.getsource(job_runner._mot_luot_bao_tri)
