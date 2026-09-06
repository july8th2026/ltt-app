"""
test_828 — mở `noi_bo.tim_tai_lieu` cho model. Bước CUỐI của P06. (H44 P06 b6)

## Mệnh đề trung tâm: PHẠM VI không được là thứ model đặt

Tool này tìm trong tài liệu của **hội thoại hiện tại**. Hội thoại nào là một
**ranh giới quyền**, nên nó phải đến từ **người gọi**, không từ đối số.

⛔ Nếu `conversation_id` là một tham số trong schema, model đọc được id hội
   thoại khác **từ chính lịch sử trò chuyện** và tool thành đường đọc chéo. Một
   tham số do model kiểm soát không thể là ranh giới phạm vi.

⇒ `boi_canh` do `bo_chay_tool` đặt, không đi qua schema. Thiếu nó thì handler
  **ném** — fail-closed, không im lặng tìm toàn tài khoản.

## Và đây là bước duy nhất đổi hành vi người dùng thấy

Năm bước trước của P06 không mở một cửa nào. §4 của kế hoạch: *"Không bước nào
mở cho model gọi cho tới bước cuối"*. Tệp này là chỗ lời hứa ấy được thu lại.
"""
from __future__ import annotations

import pytest

CHU = "u-chu-828"
LA = "u-la-828"


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


def _tai_lieu(db, *, conv, user_id=CHU, ten="hop dong.pdf", chu="credit token"):
    from apps.chatltt.services import chia_doan
    from apps.chatltt.tables import ChatlttDoan, ChatlttTep

    tep = ChatlttTep(user_id=user_id, conversation_id=conv, upload_id="up1",
                     ten_tep=ten, content_type="application/pdf")
    db.add(tep)
    db.flush()
    noi = f"Dieu khoan noi ve {chu} va cac muc lien quan."
    db.add(ChatlttDoan(user_id=user_id, conversation_id=conv, tep_id=tep.id,
                       thu_tu=0, trang=3, noi_dung=noi, so_ky_tu=len(noi),
                       bam=chia_doan.bam(noi)))
    db.flush()
    return tep


# ── 1. Bốn cửa ────────────────────────────────────────────────────────────

def test_tool_DA_duoc_mo_o_cong_THU_TU():
    from apps.chatltt.services import chieu_tool, tool_noi_bo

    assert tool_noi_bo.TEN_TIM_TAI_LIEU in chieu_tool.CHO_MODEL_GOI


def test_tool_KHONG_o_cong_thu_BA_va_do_la_chu_dich():
    """⭐ Cổng ba là thứ ChatLTT **mời người dùng bấm**; cổng bốn là thứ **model
    tự gọi**. Tìm trong tài liệu của chính mình không phải một nút để bấm —
    cùng chỗ đứng với `noi_bo.tinh`."""
    from apps.chatltt.services import chinh_sach, tool_noi_bo

    assert tool_noi_bo.TEN_TIM_TAI_LIEU not in chinh_sach.CONG_CU_CHO_PHEP
    assert "noi_bo.tinh" not in chinh_sach.CONG_CU_CHO_PHEP


def test_lop_chinh_sach_la_READ_ONLY_nen_KHONG_can_duyet():
    """🔴 Trích đã thu tiền một lần. Tìm trong đoạn đã trích là một truy vấn
    CSDL trên dữ liệu của chính người hỏi — bắt duyệt lần nữa là tính tiền hai
    lần cho một việc."""
    from apps.chatltt.services import chieu_tool, tool_noi_bo

    assert chieu_tool.lop_chinh_sach(tool_noi_bo.TEN_TIM_TAI_LIEU) == "READ_ONLY"
    assert not chieu_tool.can_duyet(tool_noi_bo.TEN_TIM_TAI_LIEU)


def test_khoi_gui_model_KHONG_co_tham_so_conversation_id():
    """🔴 Mệnh đề trung tâm, đo ở đúng chỗ nó quyết định: **hợp đồng gửi model**.

    Nếu `conversation_id` xuất hiện trong `parameters`, model đặt được nó — và
    mọi lớp phòng thủ bên dưới trở thành lớp phòng thủ chống lại một thứ ta tự
    mời vào.
    """
    from apps.chatltt.services import tool_noi_bo

    khoi = [k for k in tool_noi_bo.KHOI
            if k["function"]["name"] == tool_noi_bo.TEN_TIM_TAI_LIEU]
    assert khoi, "tool chua duoc chieu cho model"
    thuoc = khoi[0]["function"]["parameters"]["properties"]
    for cam in ("conversation_id", "conv_id", "user_id", "hoi_thoai"):
        assert cam not in thuoc, (
            f"{cam!r} nam trong hop dong gui model — model dat duoc pham vi")


# ── 2. Fail-closed khi thiếu phạm vi ──────────────────────────────────────

def test_THIEU_boi_canh_thi_NEM_chu_khong_tim_toan_tai_khoan(db):
    """🔴 Một tool mất phạm vi mà vẫn trả kết quả là một rò rỉ trông như một
    tính năng."""
    from apps.chatltt.services import thi_hanh, tool_noi_bo

    _tai_lieu(db, conv="c1")
    kq = thi_hanh.thi_hanh(db, user_id=CHU, ten=tool_noi_bo.TEN_TIM_TAI_LIEU,
                           doi_so={"cau_hoi": "credit"})
    assert kq.ok is False
    assert kq.ma_loi == thi_hanh.LOI_HANDLER
    assert "pham vi" in kq.thong_diep


def test_CO_boi_canh_thi_chay_va_kem_TRICH_DAN(db):
    """⭐ Đối chứng dương. Không có nó thì một handler luôn ném cũng qua sạch."""
    from apps.chatltt.services import thi_hanh, tool_noi_bo

    tep = _tai_lieu(db, conv="c1")
    kq = thi_hanh.thi_hanh(db, user_id=CHU, ten=tool_noi_bo.TEN_TIM_TAI_LIEU,
                           doi_so={"cau_hoi": "credit token"},
                           boi_canh={"conversation_id": "c1"})
    assert kq.ok is True, kq.thong_diep
    assert kq.noi_dung["so_khop"] >= 1
    td = kq.noi_dung["doan"][0]["trich_dan"]
    assert td["tep_id"] == tep.id and td["trang"] == 3
    assert td["ten_tep"] == "hop dong.pdf"


def test_boi_canh_tro_hoi_thoai_KHAC_thi_khong_thay_gi(db):
    """⛔ Phạm vi phải **thật sự** giới hạn, không chỉ được truyền vào."""
    from apps.chatltt.services import thi_hanh, tool_noi_bo

    _tai_lieu(db, conv="c1")
    kq = thi_hanh.thi_hanh(db, user_id=CHU, ten=tool_noi_bo.TEN_TIM_TAI_LIEU,
                           doi_so={"cau_hoi": "credit"},
                           boi_canh={"conversation_id": "c2"})
    assert kq.ok is True
    assert kq.noi_dung["so_khop"] == 0
    assert kq.noi_dung["co_tai_lieu"] is False


def test_model_dat_conversation_id_trong_DOI_SO_thi_VO_HIEU(db):
    """🔴 Ca tấn công trực tiếp: model **cố** đặt phạm vi.

    Kể cả khi nó gửi `conversation_id` trong đối số, phạm vi vẫn phải là cái
    người gọi đặt. Nếu phép kiểm này đỏ, nghĩa là đối số đã đè được bối cảnh.
    """
    from apps.chatltt.services import thi_hanh, tool_noi_bo

    _tai_lieu(db, conv="c-rieng-tu", chu="bi mat luong")
    kq = thi_hanh.thi_hanh(
        db, user_id=CHU, ten=tool_noi_bo.TEN_TIM_TAI_LIEU,
        doi_so={"cau_hoi": "bi mat luong", "conversation_id": "c-rieng-tu"},
        boi_canh={"conversation_id": "c-cong-viec"})
    # Doi so la o schema => bi chan tu tang kiem doi so; du di duoc toi handler
    # thi pham vi van la `c-cong-viec`. Ca hai duong deu KHONG duoc lo du lieu.
    if kq.ok:
        assert kq.noi_dung["so_khop"] == 0, "doi so cua model da de duoc pham vi"


def test_nguoi_KHAC_khong_doc_duoc_du_dung_conversation_id(db):
    """⛔ Hai chiều: đúng hội thoại nhưng sai chủ."""
    from apps.chatltt.services import thi_hanh, tool_noi_bo

    _tai_lieu(db, conv="c1")
    kq = thi_hanh.thi_hanh(db, user_id=LA, ten=tool_noi_bo.TEN_TIM_TAI_LIEU,
                           doi_so={"cau_hoi": "credit"},
                           boi_canh={"conversation_id": "c1"})
    assert kq.ok is True
    assert kq.noi_dung["so_khop"] == 0


def test_cau_hoi_RONG_bi_tu_choi(db):
    from apps.chatltt.services import thi_hanh, tool_noi_bo

    _tai_lieu(db, conv="c1")
    kq = thi_hanh.thi_hanh(db, user_id=CHU, ten=tool_noi_bo.TEN_TIM_TAI_LIEU,
                           doi_so={"cau_hoi": "   "},
                           boi_canh={"conversation_id": "c1"})
    assert kq.ok is False


# ── 3. Bối cảnh thật sự đi từ `bo_chay_tool` xuống ────────────────────────

def test_bo_chay_tool_TRUYEN_conv_id_xuong_handler(db):
    """🔴 Nối cả đường, không chỉ hai đầu.

    Bốn cửa đúng và handler đúng vẫn vô nghĩa nếu `bo_chay_tool` quên truyền
    `conv_id` — khi ấy mọi lời gọi thật đều rơi vào nhánh fail-closed, và tool
    "đã mở" nhưng không bao giờ trả được gì.
    """
    from apps.chatltt.services import bo_chay_tool, dieu_phoi as DP, tool_noi_bo

    _tai_lieu(db, conv="c1")
    khoi = list(tool_noi_bo.KHOI)
    chay = bo_chay_tool.tao(db, user_id=CHU, run_id="r1", khoi_tools=khoi,
                            conv_id="c1")
    kq = chay(tool_noi_bo.TEN_TIM_TAI_LIEU, {"cau_hoi": "credit token"},
              DP.NgoCanhGoi(thu_tu=0, goi_id="g1"))
    assert kq.ok is True, kq.thong_diep
    assert kq.noi_dung["so_khop"] >= 1


def test_MOI_handler_da_dang_ky_deu_nhan_du_BON_tham_so():
    """🔴 Bánh cóc cho chính lần đổi hợp đồng này (06/09).

    `dang_ky` nay đòi `(db, user_id, doi_so, boi_canh)`. Một handler còn ba tham
    số sẽ ném `TypeError` — nhưng `thi_hanh` **bắt rộng có chủ ý** (một handler
    ném là dữ liệu cho model đọc, không phải sự cố), nên nó thành một `KetQua`
    lỗi bình thường.

    ⛔ Tức chế độ hỏng của một hợp đồng lệch là **im**: tool "có tồn tại", model
       gọi được, và mỗi lần gọi trả về một lỗi khó hiểu. Đó là lý do phải chốt
       chữ ký ở đây chứ không đợi một phép kiểm hành vi nào đó tình cờ chạm tới.
    """
    import inspect

    from apps.chatltt.services import thi_hanh

    thi_hanh._nap_noi_bo()
    assert thi_hanh._SO_HANDLER, "so handler rong — phep kiem nay khong do gi"
    for ten, ham in thi_hanh._SO_HANDLER.items():
        sig = inspect.signature(ham)
        n = len([p for p in sig.parameters.values()
                 if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)])
        assert n >= 4, f"handler {ten!r} chi nhan {n} tham so, hop dong doi 4"


def test_bo_chay_tool_KHONG_co_conv_id_thi_fail_closed(db):
    """⭐ Đối chứng: thiếu `conv_id` thì hỏng **ồn**, không im lặng tìm rộng."""
    from apps.chatltt.services import bo_chay_tool, dieu_phoi as DP, tool_noi_bo

    _tai_lieu(db, conv="c1")
    chay = bo_chay_tool.tao(db, user_id=CHU, run_id="r1",
                            khoi_tools=list(tool_noi_bo.KHOI))
    kq = chay(tool_noi_bo.TEN_TIM_TAI_LIEU, {"cau_hoi": "credit"},
              DP.NgoCanhGoi(thu_tu=0, goi_id="g1"))
    assert kq.ok is False
    assert "pham vi" in kq.thong_diep
