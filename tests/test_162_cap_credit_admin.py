"""
F-01 · P0 — cấp credit cho người dùng không tồn tại phải bị CHẶN.

Audit LTT-AQA 2026-08-07 (control-plane/quan-tri-user).

Trước bản vá: `/admin/grant-credit` nhận UUID gõ tay, `cap_tay()` gọi thẳng
`_ghi()` không kiểm gì, và `credit_entries` **không có khoá ngoại**. Gõ nhầm một
ký tự là credit rơi vào hư không, trong khi màn hình admin báo đầy tự tin:

    Đã cấp +500 credit cho 3f2a…. Số dư mới: 500.

Không lỗi nào ở đâu cả. Cách duy nhất phát hiện là tự đi truy vấn CSDL. Đó là lý
do finding này là P0 và chặn cả G3 (Money/Credit) lẫn G4 (Honest UI).

Test chạy trên SQLite nên **không** phủ được khoá ngoại (migration cố ý bỏ qua
SQLite, xem `20260807_1000_credit_fk_user.py`). Nó phủ tầng nghiệp vụ — tầng cho
thông báo lỗi tử tế và là thứ người dùng chạm vào.
"""
from __future__ import annotations

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'c.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEY", "test-material-cho-secretbox-123")
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session(); s = next(gen)
    try:
        yield s
    finally:
        s.close(); dbmod.reset_engine()


@pytest.fixture()
def nguoi_that(db):
    from platform_core.users import tao_nguoi_dung
    u = tao_nguoi_dung(db, email="that@x.com", password="matkhau-tot", is_verified=True)
    db.commit()
    return u


# ── F-01: chặn cấp cho người không tồn tại ───────────────────────────────────
def test_cap_credit_cho_user_khong_ton_tai_bi_TU_CHOI(db, nguoi_that):
    from platform_core import credit
    with pytest.raises(credit.NguoiDungKhongTonTai):
        credit.cap_tay(db, "khong-co-uuid-nay", 500, by="admin")


def test_bi_tu_choi_thi_KHONG_ghi_but_toan_nao(db, nguoi_that):
    """Từ chối mà vẫn ghi sổ thì còn tệ hơn — sổ credit là bằng chứng đối soát."""
    from platform_core import credit
    from platform_core.models import CreditEntry
    truoc = db.query(CreditEntry).count()
    with pytest.raises(credit.NguoiDungKhongTonTai):
        credit.cap_tay(db, "3f2a-go-nham", 500, by="admin")
    db.rollback()
    assert db.query(CreditEntry).count() == truoc


@pytest.mark.parametrize("xau", ["", "   ", None])
def test_user_id_rong_cung_bi_tu_choi(db, nguoi_that, xau):
    from platform_core import credit
    with pytest.raises(credit.NguoiDungKhongTonTai):
        credit.cap_tay(db, xau, 100, by="admin")


def test_cap_cho_nguoi_that_van_chay(db, nguoi_that):
    from platform_core import credit
    credit.cap_tay(db, nguoi_that.id, 500, by="admin", note="onboarding")
    db.commit()
    assert credit.so_du(db, nguoi_that.id) == 500


def test_thu_hoi_bang_so_am_van_chay(db, nguoi_that):
    from platform_core import credit
    credit.cap_tay(db, nguoi_that.id, 500, by="admin")
    credit.cap_tay(db, nguoi_that.id, -200, by="admin", note="thu hoi")
    db.commit()
    assert credit.so_du(db, nguoi_that.id) == 300


def test_so_0_van_bi_tu_choi_nhu_cu(db, nguoi_that):
    from platform_core import credit
    with pytest.raises(ValueError):
        credit.cap_tay(db, nguoi_that.id, 0, by="admin")


def test_ghi_ro_ai_cap(db, nguoi_that):
    """Nhật ký: bút toán phải nói ai cấp — đây là dấu vết duy nhất cho tiền."""
    from platform_core import credit
    from platform_core.models import CreditEntry
    credit.cap_tay(db, nguoi_that.id, 100, by="admin@x.com", note="bồi thường")
    db.commit()
    e = db.query(CreditEntry).order_by(CreditEntry.id.desc()).first()
    assert "admin@x.com" in e.note and "bồi thường" in e.note


# ── F-02: tìm theo email ─────────────────────────────────────────────────────
def test_tim_theo_email(db, nguoi_that):
    from platform_core import credit
    assert credit.tim_theo_email(db, "that@x.com").id == nguoi_that.id


def test_tim_theo_email_khong_phan_biet_hoa_thuong_va_khoang_trang(db, nguoi_that):
    """Admin gõ tay nên phải chịu được ' That@X.com '."""
    from platform_core import credit
    for xau in ("THAT@X.COM", "  that@x.com  ", "That@X.com"):
        assert credit.tim_theo_email(db, xau) is not None, xau


@pytest.mark.parametrize("xau", ["khong-co@x.com", "", "   ", None])
def test_tim_theo_email_khong_thay_tra_None(db, nguoi_that, xau):
    from platform_core import credit
    assert credit.tim_theo_email(db, xau) is None


# ── Bánh cóc: khoá ngoại phải có trong model ─────────────────────────────────
def test_model_co_khoa_ngoai_tren_credit_entries():
    """Luới an toàn cuối. Không có nó thì mọi đường ghi MỚI đều hở lại."""
    from platform_core.models import CreditEntry
    fks = list(CreditEntry.__table__.c.user_id.foreign_keys)
    assert fks, "credit_entries.user_id mat khoa ngoai — F-01 se quay lai"
    assert fks[0].column.table.name == "users"
    assert fks[0].ondelete == "RESTRICT", (
        "phai la RESTRICT: so credit la bang chung doi soat tien, "
        "xoa nguoi dung ma mat so cua ho thi khong doi soat duoc nua")
