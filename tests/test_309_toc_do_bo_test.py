"""test_309 — bộ máy chạy test nhanh, và hai hàng rào giữ nó khỏi production.

Không mạng, không GPU.

## ⭐ VÌ SAO CÓ TỆP NÀY

Đo 2026-08-26: bộ test đầy đủ mất **2 giờ**. Đo tiếp thì thấy thời gian **không**
nằm ở logic test:

```
create_all 44 bảng, tệp SQLite mới :  2,8 giây   ← MỖI test
create_app()                       :  0,01 giây
reset_engine()                     :  0,00 giây
```

2,8 × 4.090 ≈ **hơn ba giờ chỉ để tạo bảng**. Toàn bộ nút cổ chai là `fsync`:
SQLite đồng bộ xuống đĩa sau mỗi câu lệnh DDL.

```
tệp thường                                   2,16s
tệp + synchronous=OFF, journal_mode=MEMORY   0,05s   (43 lần)
:memory:                                     0,03s
```

Tắt đồng bộ cho một CSDL **tạm** — thứ bị xoá ngay sau test — không đánh đổi gì.

## ⛔ NHƯNG NÓ TUYỆT ĐỐI KHÔNG ĐƯỢC CHẠM PRODUCTION

`synchronous=OFF` nghĩa là mất dữ liệu khi máy mất điện. Với một CSDL tạm thì vô
hại; với CSDL thật thì đó là mất tiền của khách.

Có **hai hàng rào độc lập**, và tệp này chốt cả hai — mất một rào thì rào kia
vẫn giữ:

  1. chỉ áp cho URL `sqlite` (production dùng PostgreSQL);
  2. ngay cả SQLite, `LTT_ENV=production` cũng không áp.
"""
from __future__ import annotations

import pathlib
import tempfile

import sqlalchemy as sa


def _url(ten: str) -> str:
    d = pathlib.Path(tempfile.mkdtemp())
    return f"sqlite:///{(d / ten).as_posix()}"


# ── Hàng rào 1: chỉ SQLite ────────────────────────────────────────────────────

def test_postgres_KHONG_bao_gio_bi_dat_pragma(monkeypatch):
    """Rào cứng nhất: nhánh này không chạy cho PostgreSQL, bất kể môi trường."""
    from platform_core.db import _nen_tang_toc_sqlite

    monkeypatch.setenv("LTT_ENV", "development")
    assert not _nen_tang_toc_sqlite("postgresql://u:p@h/db")
    assert not _nen_tang_toc_sqlite("postgres://u:p@h/db")


# ── Hàng rào 2: không phải production ─────────────────────────────────────────

def test_sqlite_o_PRODUCTION_cung_khong_duoc_dat_pragma(monkeypatch):
    """⛔ Rào thứ hai tồn tại cho đúng một tình huống: có ngày nào đó ai đó chạy
    SQLite ở production (một công cụ, một bản vá vội, một máy phụ).

    Khi ấy rào 1 im lặng cho qua, và chỉ rào này còn đứng.
    """
    from platform_core.db import _nen_tang_toc_sqlite

    monkeypatch.setenv("LTT_ENV", "production")
    assert not _nen_tang_toc_sqlite(_url("a.db"))
    monkeypatch.setenv("LTT_ENV", "PRODUCTION")      # hoa/thuong khong duoc lot
    assert not _nen_tang_toc_sqlite(_url("b.db"))
    monkeypatch.setenv("LTT_ENV", " production ")    # khoang trang cung khong
    assert not _nen_tang_toc_sqlite(_url("c.db"))


def test_sqlite_ngoai_production_thi_DUOC_tang_toc(monkeypatch):
    from platform_core.db import _nen_tang_toc_sqlite

    for moi_truong in ("development", "local-server-test", ""):
        monkeypatch.setenv("LTT_ENV", moi_truong)
        assert _nen_tang_toc_sqlite(_url("d.db")), moi_truong


# ── Pragma thật sự có tác dụng, không chỉ được gọi ───────────────────────────

def test_pragma_THAT_SU_duoc_dat_len_ket_noi(monkeypatch, tmp_path):
    """Chốt bằng cách HỎI LẠI CSDL, không bằng cách đọc mã.

    Một pragma gõ sai tên vẫn chạy êm và không đổi gì — SQLite bỏ qua lệnh nó
    không hiểu. Nên phép kiểm phải đọc lại giá trị.
    """
    import platform_core.db as dbmod

    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'p.db').as_posix()}")
    dbmod.reset_engine()
    try:
        with dbmod.get_engine().connect() as con:
            dong_bo = con.execute(sa.text("PRAGMA synchronous")).scalar()
            nhat_ky = con.execute(sa.text("PRAGMA journal_mode")).scalar()
        assert int(dong_bo) == 0, f"synchronous phai la OFF (0), dang la {dong_bo}"
        assert str(nhat_ky).lower() == "memory", nhat_ky
    finally:
        dbmod.reset_engine()


def test_pragma_KHONG_duoc_dat_khi_LTT_ENV_la_production(monkeypatch, tmp_path):
    """Cùng phép đo, nhưng ở production — giá trị phải là mặc định của SQLite."""
    import platform_core.db as dbmod

    monkeypatch.setenv("LTT_ENV", "production")
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'q.db').as_posix()}")
    dbmod.reset_engine()
    try:
        with dbmod.get_engine().connect() as con:
            dong_bo = con.execute(sa.text("PRAGMA synchronous")).scalar()
            nhat_ky = con.execute(sa.text("PRAGMA journal_mode")).scalar()
        assert int(dong_bo) != 0, "production ma synchronous bi tat"
        assert str(nhat_ky).lower() != "memory", "production ma nhat ky nam trong RAM"
    finally:
        dbmod.reset_engine()


# ── Bộ chạy nhanh phải tách đúng những tệp làm bẩn cây ───────────────────────

def test_bo_chay_nhanh_tach_dung_cac_tep_ghi_vao_cay_kho():
    """⛔ Ba tệp này ghi đè tệp THẬT trong kho rồi khôi phục.

    Chạy song song với phần còn lại thì một worker có thể đọc trúng lúc tệp đang
    bị sửa — đúng lớp lỗi đã làm hỏng hai lượt gate ngày 26/08.

    Danh sách được chốt ở đây để lần sau ai thêm một tệp cùng loại mà quên khai
    thì có một chỗ nhắc — chứ không phải để nó lặng lẽ chạy song song.
    """
    from tools.test_nhanh import TEP_NOI_TIEP

    assert TEP_NOI_TIEP == (
        "tests/test_209_versioning_status.py",
        "tests/test_210_sdk_ecosystem.py",
        "tests/test_306_banh_coc_bo_qua_va_dich.py",
    )
