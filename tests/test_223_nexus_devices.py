"""Nexus N2.1 — ghép máy, thu hồi, hiện diện.

Mọi app trước đây cùng một hình dạng: khách bấm nút, job chạy trên máy LTT, trả
file về. Nexus khác về **loại**: sản phẩm chạy đúng nghĩa là có người đang gõ
phím trên máy tính của người khác. Một lỗi uỷ quyền ở đây không làm mất một job
— nó giao cả cái máy.

Vì vậy test ở đây chốt những thứ **không được đúng do may mắn**:

* khoá riêng không bao giờ có mặt trong CSDL (Q93 ràng buộc 1);
* thiết bị của người khác trả về như không tồn tại (ràng buộc 9);
* mọi lý do từ chối mã ghép nói **cùng một câu** — mã sai, hết hạn và đã dùng
  phải không phân biệt được từ ngoài;
* thu hồi phải ghi **ai thu hồi** (ràng buộc 5).
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
                       f"sqlite:///{(tmp_path / 'nexus.db').as_posix()}")
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


def _user(db, email: str = ""):
    from platform_core.users import tao_nguoi_dung

    user = tao_nguoi_dung(db, email=email or f"{uuid.uuid4().hex[:8]}@example.com",
                          password="x" * 24, is_verified=True)
    db.flush()
    return user


KHOA = _khoa()


# ── Cờ fail-closed ───────────────────────────────────────────────────────────

def test_nexus_mac_dinh_TAT(monkeypatch):
    """Q93: một bề mặt cho phép điều khiển máy người khác mà mặc định mở thì
    sai lầm đầu tiên là sai lầm cuối cùng."""
    from platform_core import nexus

    monkeypatch.delenv(nexus.FLAG_ENV, raising=False)
    assert nexus.enabled() is False
    monkeypatch.setenv(nexus.FLAG_ENV, "")
    assert nexus.enabled() is False
    monkeypatch.setenv(nexus.FLAG_ENV, "co le")     # gia tri la -> TAT
    assert nexus.enabled() is False
    monkeypatch.setenv(nexus.FLAG_ENV, "1")
    assert nexus.enabled() is True


# ── Ghép máy ─────────────────────────────────────────────────────────────────

def test_ghep_may_bang_ma_hop_le(db):
    from platform_core.nexus import devices

    user = _user(db)
    _row, ma = devices.tao_ma_ghep(db, user_id=user.id)
    device = devices.doi_ma(db, code=ma, public_key=KHOA,
                            display_name="May ban lam viec")

    assert device.user_id == user.id
    assert device.public_key == KHOA
    assert device.revoked_at is None


def test_khoa_RIENG_khong_bao_gio_nam_trong_CSDL(db):
    """Ràng buộc 1. Chốt bằng cấu trúc: bảng không có cột nào để chứa nó.

    Nếu ai đó thêm một cột `private_key` hay `secret` vào bảng thiết bị thì test
    này đỏ — và đó đúng là lúc cần đỏ, chứ không phải sau khi CSDL bị đọc trộm.
    """
    from platform_core.nexus.tables import NexusDevice

    ten_cot = {c.name for c in NexusDevice.__table__.columns}
    cam = {"private_key", "secret", "password", "token", "khoa_rieng"}
    assert not (ten_cot & cam), f"bang thiet bi khong duoc chua bi mat: {ten_cot & cam}"
    assert "public_key" in ten_cot


def test_ma_da_dung_thi_chet_han(db):
    from platform_core.nexus import devices

    user = _user(db)
    _row, ma = devices.tao_ma_ghep(db, user_id=user.id)
    devices.doi_ma(db, code=ma, public_key=KHOA)

    with pytest.raises(devices.NexusError):
        devices.doi_ma(db, code=ma, public_key=_khoa())


def test_ma_het_han_thi_khong_dung_duoc(db):
    from platform_core.nexus import devices

    user = _user(db)
    row, ma = devices.tao_ma_ghep(db, user_id=user.id)
    sau = row.expires_at + timedelta(seconds=1)

    with pytest.raises(devices.NexusError):
        devices.doi_ma(db, code=ma, public_key=KHOA, now=sau)


def test_moi_ly_do_tu_choi_noi_CUNG_MOT_CAU(db):
    """Mã sai, mã hết hạn, mã đã dùng — không phân biệt được từ ngoài.

    Nếu ba lý do cho ba thông điệp khác nhau thì việc dò mã biết được mình đang
    tới gần: "mã này có thật nhưng hết hạn" là một nửa câu trả lời.
    """
    from platform_core.nexus import devices

    user = _user(db)
    row, ma = devices.tao_ma_ghep(db, user_id=user.id)
    _row2, ma2 = devices.tao_ma_ghep(db, user_id=user.id)
    devices.doi_ma(db, code=ma2, public_key=_khoa())

    loi = []
    for kwargs in (
        {"code": "ZZZZZZZZ", "public_key": KHOA},                      # sai
        {"code": ma, "public_key": KHOA,
         "now": row.expires_at + timedelta(seconds=1)},                # het han
        {"code": ma2, "public_key": KHOA},                             # da dung
    ):
        with pytest.raises(devices.NexusError) as exc:
            devices.doi_ma(db, **kwargs)
        loi.append(str(exc.value))

    assert len(set(loi)) == 1, f"ba ly do lo ra ba thong diep khac nhau: {loi}"


def test_cai_lai_cung_mot_may_khong_de_ra_dong_thu_hai(db):
    """Hai dòng cùng khoá công khai làm 'thu hồi máy này' thành câu không trả
    lời được."""
    from platform_core.nexus import devices

    user = _user(db)
    _r1, ma1 = devices.tao_ma_ghep(db, user_id=user.id)
    d1 = devices.doi_ma(db, code=ma1, public_key=KHOA, display_name="cu")

    _r2, ma2 = devices.tao_ma_ghep(db, user_id=user.id)
    d2 = devices.doi_ma(db, code=ma2, public_key=KHOA, display_name="moi")

    assert d1.id == d2.id
    assert d2.display_name == "moi"
    assert len(devices.danh_sach(db, user_id=user.id)) == 1


def test_khoa_cua_may_nguoi_KHAC_thi_tu_choi(db):
    """Cùng khoá công khai nhưng khác chủ = không được cướp thiết bị."""
    from platform_core.nexus import devices

    a, b = _user(db), _user(db)
    _r1, ma1 = devices.tao_ma_ghep(db, user_id=a.id)
    devices.doi_ma(db, code=ma1, public_key=KHOA)

    _r2, ma2 = devices.tao_ma_ghep(db, user_id=b.id)
    with pytest.raises(devices.NexusError):
        devices.doi_ma(db, code=ma2, public_key=KHOA)


def test_ma_ghep_khong_luu_dang_thuong(db):
    from platform_core.nexus import devices

    user = _user(db)
    row, ma = devices.tao_ma_ghep(db, user_id=user.id)
    assert row.code_digest != devices.normalize_code(ma)
    assert ma not in row.code_digest


def test_ma_nhan_moi_kieu_go(db):
    """Mã được đọc miệng và gõ tay: gạch nối, khoảng trắng, chữ thường đều nhận."""
    from platform_core.nexus import devices

    user = _user(db)
    _row, ma = devices.tao_ma_ghep(db, user_id=user.id)
    lam_ban = devices.format_code(ma).lower().replace("-", " - ")

    device = devices.doi_ma(db, code=lam_ban, public_key=KHOA)
    assert device.user_id == user.id


def test_bang_chu_cai_bo_ky_tu_de_nham():
    from platform_core.nexus import devices

    for ch in "01OIL":
        assert ch not in devices.ALPHABET, f"{ch} de nham khi doc mieng"


# ── Quyền sở hữu ─────────────────────────────────────────────────────────────

def test_thiet_bi_cua_nguoi_khac_nhu_khong_ton_tai(db):
    """Ràng buộc 9: trả None (nơi gọi biến thành 404), không bao giờ 403.

    403 biến mỗi `device_id` thành một máy tra cứu: rải id, thu id nào trả 403,
    và đã lập được bản đồ thiết bị của người khác.
    """
    from platform_core.nexus import devices

    a, b = _user(db), _user(db)
    _row, ma = devices.tao_ma_ghep(db, user_id=a.id)
    device = devices.doi_ma(db, code=ma, public_key=KHOA)

    assert devices.cua_chu(db, user_id=a.id, device_id=device.id) is not None
    assert devices.cua_chu(db, user_id=b.id, device_id=device.id) is None
    # Id khong ton tai va id cua nguoi khac cho ra CUNG mot ket qua.
    assert devices.cua_chu(db, user_id=b.id, device_id=str(uuid.uuid4())) is None


# ── Thu hồi ──────────────────────────────────────────────────────────────────

def test_thu_hoi_phai_ghi_ai_thu_hoi(db):
    """Ràng buộc 5: một hàm cho phép thu hồi ẩn danh là hàm xoá mất câu trả lời
    'ai đã gỡ máy của tôi'."""
    from platform_core.nexus import devices

    user = _user(db)
    _row, ma = devices.tao_ma_ghep(db, user_id=user.id)
    device = devices.doi_ma(db, code=ma, public_key=KHOA)

    with pytest.raises(devices.NexusError):
        devices.thu_hoi(db, device, by="")

    assert devices.thu_hoi(db, device, by="admin:u-1") is True
    assert device.revoked_by == "admin:u-1"
    assert device.revoked_at is not None
    # Thu hoi lan hai khong ghi de nguoi thu hoi dau tien.
    assert devices.thu_hoi(db, device, by="owner") is False
    assert device.revoked_by == "admin:u-1"


def test_thu_hoi_khong_xoa_dong(db):
    """Sau sự cố, câu hỏi duy nhất quan trọng là 'máy nào từng được tin'."""
    from platform_core.nexus import devices

    user = _user(db)
    _row, ma = devices.tao_ma_ghep(db, user_id=user.id)
    device = devices.doi_ma(db, code=ma, public_key=KHOA)
    devices.thu_hoi(db, device, by="owner")

    assert devices.danh_sach(db, user_id=user.id) == []
    assert len(devices.danh_sach(db, user_id=user.id, gom_da_thu_hoi=True)) == 1


# ── Hiện diện ────────────────────────────────────────────────────────────────

def test_nhip_tim_va_online(db):
    from platform_core.nexus import devices

    user = _user(db)
    _row, ma = devices.tao_ma_ghep(db, user_id=user.id)
    device = devices.doi_ma(db, code=ma, public_key=KHOA)

    assert devices.dang_online(device) is False        # chua bao gio ket noi
    assert devices.nhip_tim(db, device) is True
    assert devices.dang_online(device) is True

    xa = datetime.now(timezone.utc) + timedelta(seconds=devices.OFFLINE_AFTER_S + 1)
    assert devices.dang_online(device, now=xa) is False


def test_thiet_bi_da_thu_hoi_khong_ghi_nhip_tim(db):
    """Trả False để agent biết mà dừng hẳn, thay vì gõ cửa mãi."""
    from platform_core.nexus import devices

    user = _user(db)
    _row, ma = devices.tao_ma_ghep(db, user_id=user.id)
    device = devices.doi_ma(db, code=ma, public_key=KHOA)
    devices.thu_hoi(db, device, by="owner")

    assert devices.nhip_tim(db, device) is False
    assert devices.dang_online(device) is False


# ── Đồ thị migration ─────────────────────────────────────────────────────────
#
# Hai test dưới đây không thuộc Nexus, nhưng chúng sinh ra từ Nexus: migration
# đầu tiên của N2.1 dùng `a1b2c3d4e5f6` — một id TRÔNG hợp lý mà đã bị
# `20260801_1600_chat_ai_studio.py` dùng rồi. Alembic báo "Cycle is detected"
# và **mọi** lệnh migration chết, kể cả `current`.
#
# Không test nào bắt được, vì test dựng schema bằng `Base.metadata.create_all()`
# chứ không chạy alembic. Nói cách khác: bộ test có thể xanh trong khi CSDL
# không nâng cấp nổi — và chỗ phát hiện ra sẽ là giữa một lần deploy.

def _revision_ids() -> dict:
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent / "alembic" / "versions"
    found: dict = {}
    pattern = re.compile(r"^revision(?::\s*str)?\s*=\s*['\"]([^'\"]+)['\"]", re.M)
    for path in sorted(root.glob("*.py")):
        for match in pattern.finditer(path.read_text(encoding="utf-8")):
            found.setdefault(match.group(1), []).append(path.name)
    return found


def test_khong_co_hai_migration_trung_revision_id():
    trung = {rid: files for rid, files in _revision_ids().items() if len(files) > 1}
    assert trung == {}, f"revision id bi dung lai: {trung}"


def test_do_thi_migration_chi_co_MOT_head():
    """Hai head nghĩa là hai nhánh schema song song: `upgrade head` sẽ không
    biết đi đâu, và hai máy chủ có thể chạy hai lược đồ khác nhau."""
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent / "alembic" / "versions"
    # RHS co the la mot chuoi, None, hoac mot tuple nhieu chuoi (revision MERGE
    # noi hai head, vd `down_revision = ("a", "b")`).
    down = re.compile(r"^down_revision(?::[^=]+)?\s*=\s*(.+)$", re.M)
    id_re = re.compile(r"['\"]([^'\"]+)['\"]")
    tat_ca = set(_revision_ids())
    da_bi_tro_toi = set()
    for path in root.glob("*.py"):
        for match in down.finditer(path.read_text(encoding="utf-8")):
            for m2 in id_re.finditer(match.group(1)):
                da_bi_tro_toi.add(m2.group(1))

    heads = tat_ca - da_bi_tro_toi
    assert len(heads) == 1, f"phai co dung mot head, dang co: {sorted(heads)}"


def test_khoa_cong_khai_SAI_DANG_bi_tu_choi_ngay_luc_ghep(db):
    """Kiểm ở biên, không kiểm lúc dùng.

    Một khoá sai dạng lưu xuống được nghĩa là thiết bị đó **không bao giờ** xác
    thực được — và lỗi sẽ hiện ra muộn, dưới dạng "máy không kết nối được", một
    triệu chứng không dẫn về nguyên nhân này. Chính các test ở file này từng dùng
    khoá giả `"ltt_dev_" + "a"*64` và vẫn xanh, nên đây là lớp lỗi có thật.
    """
    from platform_core.nexus import devices

    user = _user(db)
    for xau in ("", "khong-co-tien-to", "ltt_dev_", "ltt_dev_" + "a" * 64,
                "ltt_dev_khong-phai-base64!!!"):
        _row, ma = devices.tao_ma_ghep(db, user_id=user.id)
        with pytest.raises(devices.NexusError):
            devices.doi_ma(db, code=ma, public_key=xau)
