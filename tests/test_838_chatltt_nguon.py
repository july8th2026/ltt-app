"""
test_838 — nguồn nghiên cứu: KHAI loại, không SUY loại. (H44 B6 bước 1)

## Bánh cóc chính của tệp này chốt một thứ KHÔNG được viết

`gpt_researcher/retrievers/base.py` (đọc 07/09) kể lại issue #1846/#1892: hàm
gom nguồn của họ đoán *"đây là nội dung thật hay chỉ là đoạn xem trước"* bằng
`len(raw_content) > 100`. Đoán sai ⇒ URL không bao giờ được đọc ⇒ **báo cáo
không có trích dẫn kiểm được**.

⭐ Cùng hình dạng với lỗ H44 vừa vá ở P09 bước 1: `tom_tat == ""` đứng thay cho
   *"đang chạy"*. Một hình dạng dữ liệu thay cho một trạng thái.

⇒ Phép kiểm ở đây đọc **AST của `services/nguon.py`** và cấm mọi `len(...)` so
  với một hằng số. Nó chốt sự **vắng mặt**, nên nó đi kèm một đối chứng dương:
  bộ dò phải chứng minh nó tìm thấy `len(` khi có.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]
TEP = GOC / "apps" / "chatltt" / "services" / "nguon.py"
CHU = "u-chu-that"
NGUOI_KHAC = "u-nguoi-khac"


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


def _hoi_thoai(db, user_id: str) -> str:
    from apps.chatltt.tables import ChatlttConversation
    c = ChatlttConversation(user_id=user_id, title="t")
    db.add(c)
    db.flush()
    return c.id


def _doan(db, *, user_id: str, conv_id: str, chu: str, trang: int = 1):
    from apps.chatltt.tables import ChatlttDoan, ChatlttTep
    t = ChatlttTep(user_id=user_id, conversation_id=conv_id,
                   upload_id="up_" + chu[:6], ten_tep="tai-lieu.pdf",
                   content_type="application/pdf", kich_thuoc=10)
    db.add(t)
    db.flush()
    d = ChatlttDoan(user_id=user_id, conversation_id=conv_id, tep_id=t.id,
                    thu_tu=0, trang=trang, noi_dung=chu, so_ky_tu=len(chu))
    db.add(d)
    db.flush()
    return d


# ── 1. Bánh cóc: không SUY loại từ độ dài ──────────────────────────────────

def _cac_len_so_voi_hang_so() -> list:
    """Mọi `len(...) <op> <hằng số>` trong `nguon.py`."""
    cay = ast.parse(TEP.read_bytes().decode("utf-8"))
    ra = []
    for n in ast.walk(cay):
        if not isinstance(n, ast.Compare):
            continue
        ve = [n.left, *n.comparators]
        co_len = any(isinstance(x, ast.Call) and isinstance(x.func, ast.Name)
                     and x.func.id == "len" for x in ve)
        co_hang = any(isinstance(x, ast.Constant) for x in ve)
        if co_len and co_hang:
            ra.append(ast.unparse(n))
    return ra


def test_KHONG_suy_loai_tu_do_dai():
    """🔴 PHÉP KIỂM QUYẾT ĐỊNH — chốt một thứ không được viết."""
    assert _cac_len_so_voi_hang_so() == []


def test_doi_chung_bo_do_TIM_DUOC_khi_co_that(tmp_path):
    """⛔ Không có dòng này thì phép kiểm trên xanh cả khi bộ dò hỏng.

    Cùng luật *"không đối chứng thì số 0 không phải phát hiện"*: một hàm luôn
    trả danh sách rỗng qua sạch mọi phép kiểm chốt sự vắng mặt.
    """
    gia = tmp_path / "gia.py"
    gia.write_text("def f(x):\n    if len(x) > 100:\n        return 1\n    return 0\n",
                   encoding="utf-8")
    cay = ast.parse(gia.read_text(encoding="utf-8"))
    thay = [n for n in ast.walk(cay) if isinstance(n, ast.Compare)
            and any(isinstance(x, ast.Call) and getattr(x.func, "id", "") == "len"
                    for x in [n.left, *n.comparators])]
    assert len(thay) == 1


def test_Nguon_KHONG_co_truong_xem_truoc():
    """Chính sự tồn tại của một trường vừa-có-thể-là-xem-trước-vừa-có-thể-là-nội-dung
    đã sinh ra #1846. Ở đây một `Nguon` **luôn** mang chữ thật."""
    from apps.chatltt.services.nguon import Nguon

    ten = set(Nguon.__dataclass_fields__)
    assert ten == {"loai", "chu", "trich_dan", "diem"}
    for cam in ("snippet", "xem_truoc", "raw_content", "preview", "body"):
        assert cam not in ten


# ── 2. Khai loại ───────────────────────────────────────────────────────────

def test_loai_la_bi_TU_CHOI_ngay_luc_dung():
    from apps.chatltt.services.nguon import LoaiNguonLa, Nguon

    with pytest.raises(LoaiNguonLa):
        Nguon(loai="web", chu="x")


def test_loai_web_CHUA_duoc_khai():
    """⚠️ Khai sẵn một loại chưa có cài đặt là mời người ta viết mã cho nó, rồi
    mã ấy nằm chết — và một nhánh chết trông y hệt một nhánh chưa chạy bao giờ."""
    from apps.chatltt.services.nguon import BO_THU, LOAI_NGUON

    assert LOAI_NGUON == ("doan_tai_lieu",)
    assert set(BO_THU) == {"doan_tai_lieu"}


def test_bo_thu_la_bi_NEM_chu_khong_tra_rong(db):
    """⛔ Trả rỗng cho một loại lạ biến một lỗi cấu hình thành *"không tìm thấy
    gì"* — và báo cáo sẽ nói *"không có tài liệu nào"* trong khi sự thật là ta
    gọi sai tên một bộ thu."""
    from apps.chatltt.services import nguon as N

    with pytest.raises(N.LoaiNguonLa):
        N.thu_nguon(db, user_id=CHU, boi_canh={"conversation_id": "c1"},
                    cau_hoi="x", so_toi_da=3, loai="tavily")


# ── 3. Bộ thu tài liệu ─────────────────────────────────────────────────────

def test_thu_duoc_doan_va_MOI_nguon_deu_co_trich_dan(db):
    from apps.chatltt.services import nguon as N

    cv = _hoi_thoai(db, CHU)
    _doan(db, user_id=CHU, conv_id=cv, chu="dieu khoan thanh toan la 30 ngay")
    ra = N.thu_nguon(db, user_id=CHU, boi_canh={"conversation_id": cv},
                     cau_hoi="thanh toan", so_toi_da=5)
    assert ra, "khong thu duoc nguon nao"
    # ⭐ Quet MOI phan tu, khong kiem phan tu dau — mot ham quen gan nguon cho
    #    doan thu ba van qua duoc phep kiem chi nhin doan dau (`test_827`).
    for n in ra:
        assert n.loai == "doan_tai_lieu"
        assert n.chu.strip()
        assert n.trich_dan.get("doan_id")
        assert n.trich_dan.get("tep_id")


def test_MAT_pham_vi_thi_KHONG_thu_gi(db):
    """Fail-closed: thiếu `conversation_id` thì không thu **toàn tài khoản**.

    Một bộ thu mất phạm vi mà vẫn trả kết quả là một rò rỉ trông như một tính
    năng — cùng luật `tool_noi_bo._h_tim_tai_lieu`.
    """
    from apps.chatltt.services import nguon as N

    cv = _hoi_thoai(db, CHU)
    _doan(db, user_id=CHU, conv_id=cv, chu="bi mat cua chu")
    assert N.thu_nguon(db, user_id=CHU, boi_canh={}, cau_hoi="bi mat",
                       so_toi_da=5) == []


def test_khong_thu_duoc_tai_lieu_cua_NGUOI_KHAC(db):
    from apps.chatltt.services import nguon as N

    cv_chu = _hoi_thoai(db, CHU)
    _doan(db, user_id=CHU, conv_id=cv_chu, chu="tai lieu rieng cua chu")
    ra = N.thu_nguon(db, user_id=NGUOI_KHAC,
                     boi_canh={"conversation_id": cv_chu},
                     cau_hoi="tai lieu", so_toi_da=5)
    assert ra == []
    # doi chung duong: chinh chu thi thay
    assert N.thu_nguon(db, user_id=CHU, boi_canh={"conversation_id": cv_chu},
                       cau_hoi="tai lieu", so_toi_da=5)


def test_kho_RONG_tra_rong_chu_khong_bia(db):
    """Không có nguồn nào thì **không** dựng nguồn giả. §4 mục 4 của kế hoạch."""
    from apps.chatltt.services import nguon as N

    cv = _hoi_thoai(db, CHU)
    assert N.thu_nguon(db, user_id=CHU, boi_canh={"conversation_id": cv},
                       cau_hoi="bat ky", so_toi_da=5) == []
