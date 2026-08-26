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


# ── Bẫy mã hoá: công cụ chạy đúng khi gọi tay, vỡ khi bị hứng ────────────────

def test_nhan_buoc_in_duoc_khi_stdout_bi_HUNG_bang_cp1252():
    """26/08: `gate.py` đỏ ở bước `bo test (song song)` — **trước khi** bộ test
    chạy lấy một phép kiểm nào.

    ⭐ Vì sao đáng một phép kiểm riêng: lỗi này **chạy đúng khi gọi tay**. Console
       của người sửa là UTF-8, nên `python tools/test_nhanh.py` luôn xanh; nó chỉ
       vỡ khi stdout bị một trình khác hứng và Python rơi về `cp1252`. Tức nó vỡ
       ở đúng chỗ ít người nhìn nhất — trong gate, và sớm nhất là trong CI.
    """
    import importlib.util
    import io
    import pathlib
    import sys

    goc = pathlib.Path(__file__).resolve().parent.parent
    spec = importlib.util.spec_from_file_location(
        "tn_kiem", goc / "tools" / "test_nhanh.py")
    tn = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tn)  # type: ignore[union-attr]

    buf = io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict")
    that_out, that_err = sys.stdout, sys.stderr
    sys.stdout = sys.stderr = buf
    try:
        tn._ep_utf8()
        tn._chay([sys.executable, "-c", "pass"], "PHA 1 — song song, tiếng Việt")
    except UnicodeEncodeError as e:      # pragma: no cover - chinh la thu can chan
        sys.stdout, sys.stderr = that_out, that_err
        raise AssertionError(f"nhan buoc lam vo cp1252: {e}") from e
    finally:
        sys.stdout, sys.stderr = that_out, that_err


def test_MOI_dong_sinh_dau_ra_cua_test_nhanh_deu_la_ASCII():
    """Hai lớp, và lớp này là lớp không được phép vắng mặt.

    `_ep_utf8` dựa vào `reconfigure`, thứ chỉ có trên `io.TextIOWrapper` — dưới
    một trình hứng khác stdout có thể là thứ khác và phương thức đó biến mất
    **không báo gì**. Nên chính chuỗi in ra phải là ASCII.

    ⛔ BẢN ĐẦU CỦA PHÉP KIỂM NÀY CHỈ SOI HÀM `_chay`, VÀ ĐÃ BỎ LỌT BA CHỖ.
       Ngay lượt gate kế tiếp: nhãn `PHA 2 —` in ra thành `PHA 2 ?`, và khối tổng
       kết in ra `═══...` thay vì một đường kẻ.

    ⭐ Bài học là bài học của chính bánh cóc: **một phép kiểm bắt được nửa vấn đề
       nguy hiểm hơn không có phép kiểm nào**, vì nó mua về cảm giác đã xong. Nên
       phạm vi ở đây là CẢ TỆP, không phải một hàm.
    """
    import pathlib

    goc = pathlib.Path(__file__).resolve().parent.parent
    src = (goc / "tools" / "test_nhanh.py").read_text(encoding="utf-8")

    xau = []
    for so, dong in enumerate(src.splitlines(), 1):
        if dong.lstrip().startswith("#"):      # chu thich duoc phep co dau
            continue
        if "print(" not in dong and "_chay(" not in dong:
            continue
        if not dong.isascii():
            xau.append((so, dong.strip()))

    assert not xau, (
        "dong sinh dau ra co ky tu ngoai ASCII: "
        + "; ".join(f"dong {s}: {d}" for s, d in xau)
        + " -- duoi mot trinh hung dung cp1252, chung in ra rac hoac lam VO"
          " ca buoc truoc khi bo test kip chay.")
