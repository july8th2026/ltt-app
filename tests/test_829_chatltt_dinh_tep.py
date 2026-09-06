"""
test_829 — đính tài liệu vào hội thoại: GIÁ HIỆN TRƯỚC, THU SAU. (H44 B1)

## Mệnh đề trung tâm

P06 §7 chốt: *"tải một tài liệu lên để hỏi **tốn credit** … giá phải nhỏ và
phải hiện **trước** khi bấm"*. Nên luồng là **hai bước**, và khoảng giữa hai
bước là thứ tệp này bảo vệ:

    1. `nhan()`   byte -> storage, BAO GIA   <- chua ai bi tru gi
    2. (khach doc gia va bam)
    3. `trich()`  giu credit -> promote -> gan

⛔ Gộp lại thành một bước thì khách bấm một nút và bị trừ tiền cho một giá họ
   chưa thấy. `test_TAI_LEN_khong_thu_mot_dong_nao` là phép kiểm giữ khoảng
   giữa ấy.

## Và B1 tồn tại vì một phép đo, không vì một mục trong danh sách

`grep -c LTT_CHATLTT_V3 app.env` → **0**. P06 xong 6/6 bước, 4.034 dòng, 101
phép kiểm — và **không một dòng nào chạm một người dùng nào**, vì chưa có đường
nào để khách đính một tệp. Đây là đường đó.
"""
from __future__ import annotations

import io

import pytest

CHU = "u-chu-829"
LA = "u-la-829"


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", "sqlite:///" + (tmp_path / "t.db").as_posix())
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine, get_session
    from platform_core.registry import load_app_tables
    load_app_tables()
    Base.metadata.create_all(get_engine())
    gen = get_session()
    s = next(gen)
    yield s
    try:
        next(gen)
    except StopIteration:
        pass
    dbmod.reset_engine()


def _users(db):
    from platform_core.models import User
    for uid in (CHU, LA):
        if db.get(User, uid) is None:
            db.add(User(id=uid, email=f"{uid}@x.test", password_hash="x"))
    db.flush()


def _conv(db, user_id=CHU):
    from apps.chatltt.tables import ChatlttConversation
    c = ChatlttConversation(user_id=user_id, title="t")
    db.add(c)
    db.flush()
    return c.id


VAN = ("Phan le duoi mot credit duoc cong don sang luot sau. " * 30).encode()


# ── 1. Giá hiện TRƯỚC, và bước 1 không thu gì ─────────────────────────────

def test_TAI_LEN_hien_gia_va_KHONG_thu_mot_dong_nao(db):
    """🔴 Mệnh đề trung tâm. Bước 1 phải để lại **đúng** một vé `ready` và
    **không** một bút toán credit nào."""
    from apps.chatltt.services import dinh_tep as DT
    from platform_core.models import CreditEntry, UploadSession

    _users(db)
    conv = _conv(db)
    kq = DT.nhan(db, user_id=CHU, conversation_id=conv, ten_tep="hop dong.txt",
                 content_type="text/plain", du_lieu=VAN)

    assert kq["bao_gia_credit"] >= 1, "khong hien gia thi khach bam mu"
    assert kq["gia_da_chot"] is False, (
        "gia dang la gia TAM — ket qua phai noi that dieu do")
    assert kq["so_byte"] == len(VAN)

    ve = db.get(UploadSession, kq["upload_id"])
    assert ve is not None and ve.status == "ready", (
        f"ve o trang thai {ve.status if ve else None!r} — buoc 1 KHONG duoc promote")
    assert db.query(CreditEntry).count() == 0, (
        "da co but toan credit o BUOC 1 — khach bi tru truoc khi thay gia")


def test_TAI_LEN_chua_gan_vao_hoi_thoai(db):
    """⭐ Chưa bấm đồng ý thì chưa có tệp nào trong hội thoại. Nếu có, giao diện
    sẽ hiện một tệp mà khách chưa đồng ý trả tiền để trích."""
    from apps.chatltt.services import dinh_tep as DT

    _users(db)
    conv = _conv(db)
    DT.nhan(db, user_id=CHU, conversation_id=conv, ten_tep="a.txt",
            content_type="text/plain", du_lieu=VAN)
    assert DT.danh_sach(db, user_id=CHU, conversation_id=conv) == []


# ── 2. Bước 3: đồng ý ⇒ giữ credit, promote, gắn ──────────────────────────

def test_TRICH_giu_credit_promote_va_gan(db):
    from apps.chatltt.services import dinh_tep as DT
    from platform_core.models import UploadSession

    _users(db)
    from platform_core import credit
    credit.nap(db, CHU, 100, note="thu")
    conv = _conv(db)
    up = DT.nhan(db, user_id=CHU, conversation_id=conv, ten_tep="a.txt",
                 content_type="text/plain", du_lieu=VAN)["upload_id"]

    kq = DT.trich(db, user_id=CHU, conversation_id=conv, upload_id=up)

    assert kq["tep_id"] and kq["job_id"]
    assert kq["credit_da_giu"] >= 1
    ve = db.get(UploadSession, up)
    assert ve.status == "promoted", f"ve van o {ve.status!r} — cua credit chua dong"
    ds = DT.danh_sach(db, user_id=CHU, conversation_id=conv)
    assert len(ds) == 1 and ds[0]["ten_tep"] == "a.txt"


def test_job_mang_DU_tep_id_va_user_id(db):
    """🔴 Job được nộp **trước** khi có `tep_id` (vì `promote` đòi một job).
    Nếu quên nối hai đầu lại, worker nhận một job thiếu tham số và hỏng ở xa."""
    from apps.chatltt.services import dinh_tep as DT
    from platform_core import credit
    from platform_core.models import Job

    _users(db)
    credit.nap(db, CHU, 100, note="thu")
    conv = _conv(db)
    up = DT.nhan(db, user_id=CHU, conversation_id=conv, ten_tep="a.txt",
                 content_type="text/plain", du_lieu=VAN)["upload_id"]
    kq = DT.trich(db, user_id=CHU, conversation_id=conv, upload_id=up)

    job = db.get(Job, kq["job_id"])
    assert (job.params or {}).get("tep_id") == kq["tep_id"]
    assert (job.params or {}).get("user_id") == CHU


# ── 3. Sở hữu ─────────────────────────────────────────────────────────────

def test_nguoi_LA_khong_dinh_duoc_vao_hoi_thoai_cua_chu(db):
    from apps.chatltt.services import dinh_tep as DT

    _users(db)
    conv = _conv(db)
    with pytest.raises(DT.LoiDinhTep):
        DT.nhan(db, user_id=LA, conversation_id=conv, ten_tep="a.txt",
                content_type="text/plain", du_lieu=VAN)


def test_nguoi_LA_khong_TRICH_duoc_ve_cua_chu(db):
    """⛔ Chiều thứ hai: vé đúng, hội thoại đúng, **sai chủ**."""
    from apps.chatltt.services import dinh_tep as DT

    _users(db)
    conv = _conv(db)
    up = DT.nhan(db, user_id=CHU, conversation_id=conv, ten_tep="a.txt",
                 content_type="text/plain", du_lieu=VAN)["upload_id"]
    conv_la = _conv(db, user_id=LA)
    with pytest.raises(DT.LoiDinhTep):
        DT.trich(db, user_id=LA, conversation_id=conv_la, upload_id=up)


def test_nguoi_LA_khong_liet_ke_duoc(db):
    from apps.chatltt.services import dinh_tep as DT

    _users(db)
    conv = _conv(db)
    with pytest.raises(DT.LoiDinhTep):
        DT.danh_sach(db, user_id=LA, conversation_id=conv)


# ── 4. Từ chối sớm ────────────────────────────────────────────────────────

def test_dinh_dang_LA_bi_tu_choi_TRUOC_khi_ghi_byte(db):
    """⛔ Giao diện mời khách chọn thứ ta không đọc được là một lời hứa hỏng —
    đúng lỗi đang sống ở `chataistudio` với PDF."""
    from apps.chatltt.services import dinh_tep as DT
    from platform_core.models import UploadSession

    _users(db)
    conv = _conv(db)
    with pytest.raises(DT.LoiDinhTep):
        DT.nhan(db, user_id=CHU, conversation_id=conv, ten_tep="x.exe",
                content_type="application/x-msdownload", du_lieu=b"MZ")
    assert db.query(UploadSession).count() == 0, "da ghi ve cho mot kieu bi tu choi"


def test_KIEU_NHAN_dung_bang_tap_TRICH_DUOC(db):
    """🔴 Hai danh sách ở hai tệp nói về cùng một thứ. Lệch nhau thì hoặc ta mời
    một định dạng không đọc được, hoặc từ chối một định dạng đọc được."""
    from apps.chatltt.services import dinh_tep as DT, trich_van_ban as T

    assert set(DT.KIEU_NHAN) == set(T.DUOC_NHAN)


def test_tep_QUA_LON_bi_tu_choi(db):
    from apps.chatltt.services import dinh_tep as DT

    _users(db)
    conv = _conv(db)
    with pytest.raises(DT.LoiDinhTep):
        DT.nhan(db, user_id=CHU, conversation_id=conv, ten_tep="a.txt",
                content_type="text/plain", du_lieu=b"x" * (DT.TRAN_BYTE + 1))


def test_tran_cao_hon_ca_THUONG_hai_bac_do_lon():
    """⭐ "Trần đặt DƯỚI nhu cầu bình thường biến thất bại thành MẶC ĐỊNH".
    Một hợp đồng PDF ~1–3 MB; trần phải bỏ xa mức ấy."""
    from apps.chatltt.services import dinh_tep as DT

    assert DT.TRAN_BYTE >= 10 * 1024 * 1024


# ── 5. Gỡ ─────────────────────────────────────────────────────────────────

def test_GO_xoa_ca_cac_DOAN_da_trich(db):
    """🔴 Xoá liên kết mà để lại `chatltt_doan` là để lại **chữ của khách**
    trong chỉ số tìm kiếm sau khi họ đã bấm gỡ. Giao diện nói "đã gỡ" trong khi
    model vẫn đọc được."""
    from apps.chatltt.services import chia_doan, dinh_tep as DT
    from apps.chatltt.tables import ChatlttDoan
    from platform_core import credit

    _users(db)
    credit.nap(db, CHU, 100, note="thu")
    conv = _conv(db)
    up = DT.nhan(db, user_id=CHU, conversation_id=conv, ten_tep="a.txt",
                 content_type="text/plain", du_lieu=VAN)["upload_id"]
    tep_id = DT.trich(db, user_id=CHU, conversation_id=conv, upload_id=up)["tep_id"]

    noi = "mot doan da trich"
    db.add(ChatlttDoan(user_id=CHU, conversation_id=conv, tep_id=tep_id,
                       thu_tu=0, trang=1, noi_dung=noi, so_ky_tu=len(noi),
                       bam=chia_doan.bam(noi)))
    db.flush()

    assert DT.go(db, user_id=CHU, tep_id=tep_id) is True
    assert db.query(ChatlttDoan).filter(ChatlttDoan.tep_id == tep_id).count() == 0


def test_nguoi_LA_khong_GO_duoc(db):
    from apps.chatltt.services import dinh_tep as DT
    from platform_core import credit

    _users(db)
    credit.nap(db, CHU, 100, note="thu")
    conv = _conv(db)
    up = DT.nhan(db, user_id=CHU, conversation_id=conv, ten_tep="a.txt",
                 content_type="text/plain", du_lieu=VAN)["upload_id"]
    tep_id = DT.trich(db, user_id=CHU, conversation_id=conv, upload_id=up)["tep_id"]

    assert DT.go(db, user_id=LA, tep_id=tep_id) is False
    assert len(DT.danh_sach(db, user_id=CHU, conversation_id=conv)) == 1


# ── 5b. Cửa chữ ký byte của NỀN TẢNG ──────────────────────────────────────
#
# 🔴 Thêm 06/09 sau một phép đột biến SỐNG SÓT. Tôi bổ sung `_signature_ok` cho
#    tài liệu (một thay đổi **nền tảng**, chạm mọi app) rồi gỡ phép kiểm magic
#    PDF ra — và **15/15 vẫn xanh**. Tức tôi vừa thêm một cửa bảo mật mà không
#    có gì canh nó.
#
# ⭐ Đây đúng lớp "một phép kiểm không thể đỏ", chỉ khác chiều: lần này không
#    phải phép kiểm sai, mà là **không có phép kiểm nào cả**.

def test_PDF_doi_ten_tu_EXE_bi_chan_o_TANG_NEN_TANG():
    """🔴 Đây là cái lợi bảo mật thật của việc kiểm magic.

    Một tệp `.exe` đổi tên thành `.pdf` phải bị chặn **trước** khi chạm bộ trích
    — không phải vì bộ trích yếu, mà vì một tệp không đọc được thì không nên đi
    xa tới đó.
    """
    from platform_core.upload_sessions import _signature_ok

    assert _signature_ok("application/pdf", b"%PDF-1.7\n...") is True
    assert _signature_ok("application/pdf", b"MZ\x90\x00") is False
    assert _signature_ok("application/pdf", b"day khong phai PDF") is False


def test_chu_thuan_chan_theo_TINH_CHAT_chu_khong_theo_tien_to():
    """⛔ Chữ thuần **không có magic**, nên điều kiện phải là một *tính chất*:
    không byte NUL, và giải được UTF-8. Một tệp nhị phân gần như luôn có NUL
    trong 512 byte đầu; một tệp chữ thì không bao giờ."""
    from platform_core.upload_sessions import _signature_ok

    for ct in ("text/plain", "text/markdown", "text/csv", "application/json"):
        assert _signature_ok(ct, "xin chào Việt Nam".encode("utf-8")) is True
        assert _signature_ok(ct, b"co byte NUL\x00o giua") is False
        assert _signature_ok(ct, b"") is False


def test_chu_cat_giua_KY_TU_NHIEU_BYTE_van_duoc_nhan():
    """⭐ `confirm()` chỉ đọc 512 byte đầu, nên nó **sẽ** cắt giữa một ký tự
    tiếng Việt. Từ chối vì lý do đó là từ chối đúng những tệp ta nhắm tới."""
    from platform_core.upload_sessions import _signature_ok

    tho = ("Tiếng Việt có dấu " * 40).encode("utf-8")[:512]
    assert tho.decode("utf-8", errors="ignore") != tho.decode("utf-8", errors="replace") \
        or True     # chi de noi ro: doan nay CO THE cat giua ky tu
    assert _signature_ok("text/plain", tho) is True


def test_kieu_KHONG_khai_van_bi_TU_CHOI():
    """⭐ Đối chứng bắt buộc: bản vá của tôi không được biến hàm thành "đồng ý
    mọi thứ". Một kiểu không khai vẫn phải là `False`."""
    from platform_core.upload_sessions import _signature_ok

    assert _signature_ok("application/x-msdownload", b"MZ\x90\x00") is False
    assert _signature_ok("application/zip", b"PK\x03\x04") is False


# ── 6. Bề mặt HTTP ────────────────────────────────────────────────────────

def test_BON_route_da_gan_va_dung_phuong_thuc():
    from apps.chatltt.routes import router

    co = {(tuple(sorted(r.methods)), r.path) for r in router.routes
          if "tep" in getattr(r, "path", "")}
    assert (("POST",), "/api/hoi-thoai/{conv_id}/tep") in co
    assert (("POST",), "/api/hoi-thoai/{conv_id}/tep/{upload_id}/trich") in co
    assert (("GET",), "/api/hoi-thoai/{conv_id}/tep") in co
    assert (("DELETE",), "/api/tep/{tep_id}") in co


def test_CO_TEP_mac_dinh_TAT(monkeypatch):
    """🔴 Kế hoạch tổng ghi *"Làn B — mỗi nhóm một cờ"*, và tôi bỏ sót nó suốt
    cả P06 lẫn B1/B2.

    Hậu quả nếu deploy nguyên trạng: bật **ngay** một tính năng **tính tiền**, ở
    một giá còn tạm (`gia_trich.CHU_DU_AN_DA_CHOT` = False). Đúng thứ danh mục
    điều kiện bật cờ sinh ra để chặn — và nó lọt vì tôi đọc danh mục ấy **sau**
    khi viết route thay vì trước.
    """
    from apps.chatltt.services import co_v3

    monkeypatch.delenv(co_v3.CO_TEP, raising=False)
    assert co_v3.tep_bat() is False
    assert co_v3.trang_thai()["tep"] is False


def test_CO_TEP_KHONG_dung_chung_voi_co_vong_lap_tool(monkeypatch):
    """⛔ Bật cờ tool **không** được kéo theo cờ tệp. Đính một tài liệu tốn tiền
    ngay cả khi vòng lặp tool tắt — một cờ gác hai thứ khác nhau là một cờ không
    ai bật được đúng."""
    from apps.chatltt.services import co_v3

    monkeypatch.setenv(co_v3.CO_TOOLS, "1")
    monkeypatch.delenv(co_v3.CO_TEP, raising=False)
    assert co_v3.tool_bat() is True
    assert co_v3.tep_bat() is False


def test_cong_co_dat_TRUOC_require_login():
    """🔴 `Depends` chạy **theo thứ tự khai báo**, và `require_login` chuyển
    hướng 303 về `/login`.

    ⇒ Đặt cổng cờ **sau** nó thì một route "đã đóng" vẫn trả 303 cho khách chưa
      đăng nhập — tức nó **vẫn nói rằng đường này tồn tại**. Ca này đã xảy ra
      thật ở kho này, nên phép kiểm chốt **thứ tự trong mã**, không chốt hành vi
      của một request (hành vi ấy chỉ lộ ra với đúng một loại khách).
    """
    import pathlib
    import re

    ma = (pathlib.Path(__file__).resolve().parents[1] / "apps" / "chatltt"
          / "routes" / "_p_tep.py").read_text(encoding="utf-8")
    dong = [d for d in ma.splitlines() if "Depends(" in d]
    assert dong, "khong tim thay route nao"
    for d in dong:
        i_co = d.find("Depends(cong_tep)")
        i_login = d.find("Depends(require_login)")
        assert i_co >= 0, f"route thieu cong co: {d.strip()[:70]}"
        assert i_co < i_login, (
            f"cong co dat SAU require_login: {d.strip()[:70]}")
    assert len(re.findall(r"Depends\(cong_tep\)", ma)) == 4, (
        "phai du BON route deu co cong")


def test_cong_co_tra_404_chu_khong_403(monkeypatch):
    """⛔ 404 chứ không 403: một tính năng chưa mở thì không nên tự khai rằng nó
    tồn tại và đang bị cấm."""
    from fastapi import HTTPException

    from apps.chatltt.routes._chung import cong_tep
    from apps.chatltt.services import co_v3

    monkeypatch.delenv(co_v3.CO_TEP, raising=False)
    with pytest.raises(HTTPException) as e:
        cong_tep()
    assert e.value.status_code == 404

    monkeypatch.setenv(co_v3.CO_TEP, "1")
    assert cong_tep() is None


def test_route_KHONG_chua_nghiep_vu():
    """⛔ `routes/` chỉ lo HTTP (`AGENTS.md` §8.1). Một quy tắc rơi vào route là
    một quy tắc không ai test được nếu không dựng một request.

    ⭐ Đọc **AST**, không đọc chuỗi. Bản đầu của phép kiểm này quét cả tệp và đỏ
       vì chính **docstring** — chỗ tôi *giải thích* rằng `upload_sessions.sweep()`
       dọn hộ. Đó đúng bẫy đã ghi: *một bộ dò quét văn bản trừng phạt việc giải
       thích*, và cách chữa là hỏi cấu trúc chứ không hỏi ký tự.
    """
    import ast
    import pathlib

    cay = ast.parse((pathlib.Path(__file__).resolve().parents[1] / "apps"
                     / "chatltt" / "routes" / "_p_tep.py"
                     ).read_text(encoding="utf-8"))
    ten = {n.id for n in ast.walk(cay) if isinstance(n, ast.Name)}
    ten |= {n.attr for n in ast.walk(cay) if isinstance(n, ast.Attribute)}
    ten |= {a.name for n in ast.walk(cay) if isinstance(n, ast.Import)
            for a in n.names}
    ten |= {n.module or "" for n in ast.walk(cay) if isinstance(n, ast.ImportFrom)}

    for cam in ("upload_sessions", "get_storage", "bao_gia", "nop_job",
                "promote", "stage_bytes"):
        assert cam not in ten, f"nghiep vu {cam!r} nam trong route, khong o service"
