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

# ══════════════════════════════════════════════════════════════════════════════
#  Trang thai thu BA cua `--lf`: cache day id nhung khong id nao con song
# ══════════════════════════════════════════════════════════════════════════════

def _con_id_song(*a, **k):
    import importlib.util
    import sys
    goc = pathlib.Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("tn", goc / "tools" / "test_nhanh.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["tn"] = mod
    spec.loader.exec_module(mod)
    return mod._con_id_song(*a, **k)


def _canh_bao_lf(*a, **k):
    import importlib.util
    import sys
    goc = pathlib.Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("tn2", goc / "tools" / "test_nhanh.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["tn2"] = mod
    spec.loader.exec_module(mod)
    return mod._canh_bao_lf(*a, **k)


def test_id_MAT_HAM_va_MAT_TEP_deu_duoc_dem_la_chet():
    """🔴 `--lf` co ba trang thai, khong phai hai — va cai thu ba khong ai canh bao.

    `_da_do` da ke ba trang thai cua TEP cache (vang mat / doc duoc / doc hong).
    Nhung con mot truc khac: cache doc duoc, DAY id, va khong id nao con phan
    giai duoc. Luc do pytest thay "co failure da biet" nen `--lfnf=none` khong
    ap, roi khong id nao khop nen no khong deselect gi — mot luot **day du**
    chay duoi cai ten `--vong-lap`.

    ⭐ Do 05/09 tren `phien/asv-v4`: 20 id trong cache, **ca 20 deu chet**. Va
       chung chet mot cach lanh manh — pha 27 go nhung chot da het ly do ton
       tai. Tuc `--lf` tu xuong cap nhu he qua cua viec lam DUNG.
    """
    song, tong = _con_id_song({
        "tests/tep_khong_bao_gio_ton_tai_xyz.py::test_gi_do",
        "tests/test_309_toc_do_bo_test.py::test_ham_nay_da_bi_go_roi",
    })
    assert (song, tong) == (0, 2)


def test_MOT_id_song_thi_KHONG_bao_dong_du_co_nhieu_id_chet():
    """⚠️ Day la nua quan trong hon: mot canh bao luon bat la mot canh bao bi tat.

    Do bang thuc nghiem (phien LTTCHAT V3, 05/09): mot id chet nam canh mot id
    song thi `--lf` VAN thu hep binh thuong — id chet bi bo lang le, khong dau
    doc gi. Nen dieu kien canh bao phai la "khong con id nao song", KHONG phai
    "co id chet".
    """
    song, tong = _con_id_song({
        "tests/tep_khong_bao_gio_ton_tai_xyz.py::test_gi_do",
        "tests/test_309_toc_do_bo_test.py::test_MOT_id_song_thi_KHONG_bao_dong_du_co_nhieu_id_chet",
    })
    assert song == 1 and tong == 2


def test_id_o_TEP_KHONG_DOC_DUOC_duoc_dem_la_SONG():
    """⛔ Mot tep dang sua do (SyntaxError) khong duoc bien thanh 'da bi go'.

    Neu dem no la chet thi dung luc nguoi ta dang sua mot tep, canh bao se bao
    "khong con id nao song" va noi sai ve nguyen nhan. Nghi ngo thi nghieng ve
    IM LANG, vi canh bao nay chi de thong tin.
    """
    goc = pathlib.Path(__file__).resolve().parents[1]
    tam = goc / "tests" / "zz_thu_lf_syntax_loi.py"
    tam.write_text("def test_a(:" + chr(10) + "    pass" + chr(10),
                   encoding="utf-8")
    try:
        song, tong = _con_id_song({"tests/zz_thu_lf_syntax_loi.py::test_a"})
        assert (song, tong) == (1, 1)
    finally:
        tam.unlink(missing_ok=True)


def test_QUYET_DINH_canh_bao_chi_bat_khi_KHONG_con_id_nao_song():
    """🔑 Chot chinh PHAN QUYET, khong chi chot phep do ben duoi no.

    ⛔ Ba bai tren chot `_con_id_song` — mot dai luong. Neu chi co chung, mot
       ban sua doi `song == 0` thanh `song < tong` van xanh het, va canh bao se
       bat o moi luot co bat ky id chet nao — tuc bat gan nhu luon, tuc bi tat
       trong dau nguoi doc. Do dung la khe da cat toi ba lan trong mot phien:
       bai kiem do mot thu NAM CANH thu no tuyen bo.
    """
    chet = "tests/tep_khong_bao_gio_ton_tai_xyz.py::test_gi_do"
    song = ("tests/test_309_toc_do_bo_test.py::"
            "test_QUYET_DINH_canh_bao_chi_bat_khi_KHONG_con_id_nao_song")

    assert _canh_bao_lf(set()) == [], "cache rong da co nhanh rieng, dung noi hai lan"
    assert _canh_bao_lf({song}) == [], "con id song thi `--lf` van thu hep"
    assert _canh_bao_lf({song, chet}) == [], (
        "mot id chet canh mot id song KHONG lam `--lf` hong — do bang thuc nghiem")

    ra = _canh_bao_lf({chet})
    assert ra, "toan id chet ma khong canh bao gi"
    assert any("chay TOAN BO" in d for d in ra), (
        "canh bao phai noi ro HAU QUA, khong chi noi cache co van de")
    assert all(d.isascii() for d in ra), "moi dong dau ra cua test_nhanh phai ASCII"
