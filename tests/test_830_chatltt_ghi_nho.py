"""
test_830 — kho ghi nhớ: QUYỀN và MÂU THUẪN trước, tiện ích sau. (H44 B4 bước 2)

## Vì sao tệp này chốt "mâu thuẫn" chứ không chỉ chốt CRUD

Một kho ghi nhớ **chỉ biết thêm** vẫn qua sạch mọi phép kiểm CRUD: thêm được,
đọc được, xoá được. Nó vẫn hỏng — chỉ là hỏng **im lặng và tăng dần**: *"khách
thích cà phê"* nằm mãi cạnh *"khách bỏ cà phê"*, và sản phẩm dở đi mà không có
ngày nào để ai đó đi sửa.

⇒ Phép kiểm quyết định của tệp này là `test_mau_thuan_giai_duoc_bang_thay`, và
  nó được viết sao cho **một bản chỉ-biết-thêm phải ĐỎ**: nó đếm số mẩu còn lại
  chứ không kiểm *"gọi `thay()` không ném"*.

## Đối chứng dương ở mọi phép kiểm quyền

Mỗi lần chốt *"người khác KHÔNG thấy"*, cùng dữ liệu ấy phải chứng minh
*"chủ thì CÓ thấy"*. Thiếu vế sau thì một hàm luôn trả rỗng cũng qua sạch —
Bẫy 24, và luật *"không đối chứng thì số 0 không phải phát hiện"*.

## Chữ ký hàm là một bất biến, và nó được đọc bằng `inspect`

`ghi_boi_model()` **không được** có tham số phạm vi/mục tiêu, và cũng không được
có `**kwargs` (một cửa hậu để thêm chúng sau). Kiểm bằng `inspect.signature`,
không bằng khớp chuỗi trong tài liệu — bài học *"đọc thứ đại diện thay vì đọc
thứ thật"*.
"""
from __future__ import annotations

import inspect

import pytest

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


# --------------------------------------------------------------- lược đồ

def test_khong_co_cot_vector_nao():
    """Không embedding — và đó là HỆ QUẢ của trần, không phải một thoả hiệp.

    Trần ký tự cho cả khối tiêm nghĩa là kho **được tiêm trọn vẹn**; không có gì
    để truy hồi. Ngày ai đó thêm một cột vector vào đây là ngày kiến trúc đổi,
    và nó phải là một quyết định chứ không phải một lần thêm cột.
    """
    from apps.chatltt.tables import ChatlttGhiNho
    ten = {c.name for c in ChatlttGhiNho.__table__.columns}
    assert not {t for t in ten if "vector" in t or "embed" in t}
    assert ten == {"id", "user_id", "pham_vi", "muc_tieu_id", "nguon",
                   "noi_dung", "bam", "meta", "created_at", "updated_at"}


def test_muc_tieu_id_KHONG_duoc_nullable():
    """🔴 `NULL` không bằng `NULL` ⇒ `UNIQUE` mất tác dụng ở phạm vi phổ biến nhất.

    Triệu chứng khi hỏng **không phải** một lỗi ràng buộc mà là kho tự nhân đôi —
    nên nó phải bị chặn ở đây, không ở một chú thích.
    """
    from apps.chatltt.tables import ChatlttGhiNho
    cot = ChatlttGhiNho.__table__.columns["muc_tieu_id"]
    assert cot.nullable is False


def test_noi_dung_co_tran_o_tang_csdl():
    """Trần ép ở CSDL, không chỉ ở service: mẩu này đi vào **mọi** lượt sau đó."""
    from apps.chatltt.tables import TRAN_KY_TU_MOT_BAN, ChatlttGhiNho
    assert ChatlttGhiNho.__table__.columns["noi_dung"].type.length == TRAN_KY_TU_MOT_BAN


def test_user_id_la_chuoi_36_khong_phai_so():
    """Bài học `apps/ltt_voice/tables.py:66-75`: khai số ⇒ mọi khách thành chủ 0."""
    from apps.chatltt.tables import ChatlttGhiNho
    assert ChatlttGhiNho.__table__.columns["user_id"].type.length == 36


# --------------------------------------------------- mâu thuẫn (phép quyết định)

def test_mau_thuan_giai_duoc_bang_thay(db):
    """🔴 PHÉP KIỂM QUYẾT ĐỊNH — một bản chỉ-biết-thêm phải ĐỎ ở đây.

    Nó đếm **số mẩu còn lại**, không kiểm *"`thay()` chạy không ném"*. Kho chỉ
    biết thêm sẽ có 2 mẩu mâu thuẫn và trượt dòng `== 1`.
    """
    from apps.chatltt.services import ghi_nho as g
    mau, tt = g.them(db, user_id=CHU, pham_vi=g.NGUOI_DUNG,
                     noi_dung="Khach thich ca phe")
    assert tt == "them"

    g.thay(db, user_id=CHU, ghi_nho_id=mau.id, noi_dung="Khach da bo ca phe")

    con = g.liet_ke(db, user_id=CHU, pham_vi=g.NGUOI_DUNG)
    assert len(con) == 1
    assert con[0].noi_dung == "Khach da bo ca phe"


def test_them_lai_cung_noi_dung_tra_bo_qua(db):
    """Trùng là chuyện BÌNH THƯỜNG, không phải sự cố — hành vi `skipped` của OWUI."""
    from apps.chatltt.services import ghi_nho as g
    a, tt1 = g.them(db, user_id=CHU, pham_vi=g.NGUOI_DUNG, noi_dung="Ten la Thang")
    b, tt2 = g.them(db, user_id=CHU, pham_vi=g.NGUOI_DUNG, noi_dung="Ten la Thang")
    assert (tt1, tt2) == ("them", "bo_qua")
    assert a.id == b.id
    assert len(g.liet_ke(db, user_id=CHU)) == 1


def test_bam_bo_qua_hoa_thuong_va_khoang_trang_thua(db):
    """*"Cà Phê"* và *"  cà   phê "* là **một** mẩu — nếu không thì chống trùng
    chỉ chặn được bản sao chép-dán y nguyên, tức gần như không chặn gì."""
    from apps.chatltt.services import ghi_nho as g
    g.them(db, user_id=CHU, pham_vi=g.NGUOI_DUNG, noi_dung="Thich Ca Phe")
    _, tt = g.them(db, user_id=CHU, pham_vi=g.NGUOI_DUNG,
                   noi_dung="  thich   ca phe ")
    assert tt == "bo_qua"


# ------------------------------------------------------------------ quyền

def test_pham_vi_hoi_thoai_khong_ro_sang_hoi_thoai_khac(db):
    """Mẩu ghi ở hội thoại A không được xuất hiện ở hội thoại B.

    ⭐ Kèm **đối chứng dương**: chính mẩu ấy PHẢI xuất hiện ở A. Thiếu vế đó thì
       một `khoi_ngu_canh()` luôn trả rỗng cũng qua.
    """
    from apps.chatltt.services import ghi_nho as g
    a = _hoi_thoai(db, CHU)
    b = _hoi_thoai(db, CHU)
    g.them(db, user_id=CHU, pham_vi=g.HOI_THOAI, muc_tieu_id=a,
           noi_dung="Dang noi ve hop dong so 7")

    assert "hop dong so 7" in g.khoi_ngu_canh(db, user_id=CHU, conv_id=a)
    assert "hop dong so 7" not in g.khoi_ngu_canh(db, user_id=CHU, conv_id=b)


def test_nguoi_khac_khong_thay_va_chu_thi_thay(db):
    from apps.chatltt.services import ghi_nho as g
    g.them(db, user_id=CHU, pham_vi=g.NGUOI_DUNG, noi_dung="Bi mat cua chu")
    assert len(g.liet_ke(db, user_id=CHU)) == 1          # doi chung duong
    assert g.liet_ke(db, user_id=NGUOI_KHAC) == []


def test_ghi_vao_hoi_thoai_nguoi_khac_bi_chan(db):
    """Cửa quyền ở **tầng service**, không ở route — route có thể quên."""
    from apps.chatltt.services import ghi_nho as g
    cua_ho = _hoi_thoai(db, NGUOI_KHAC)
    with pytest.raises(g.KhongDuocPhep):
        g.them(db, user_id=CHU, pham_vi=g.HOI_THOAI, muc_tieu_id=cua_ho,
               noi_dung="chen vao hoi thoai nguoi khac")


def test_quen_KHONG_lo_id_co_ton_tai_hay_khong(db):
    """Không phân biệt *"không có"* với *"không phải của bạn"*.

    Một API phân biệt hai ca đó cho phép dò id của người khác — cùng lý do
    `kho_tep.mot()` trả `None` chứ không ném.
    """
    from apps.chatltt.services import ghi_nho as g
    cua_ho, _ = g.them(db, user_id=NGUOI_KHAC, pham_vi=g.NGUOI_DUNG,
                       noi_dung="cua nguoi khac")
    assert g.quen(db, user_id=CHU, ghi_nho_id=cua_ho.id) is False
    assert g.quen(db, user_id=CHU, ghi_nho_id="gn_khong_ton_tai") is False
    assert g.quen(db, user_id=NGUOI_KHAC, ghi_nho_id=cua_ho.id) is True  # doi chung


def test_model_khong_sua_duoc_mau_do_nguoi_ghi(db):
    from apps.chatltt.services import ghi_nho as g
    mau, _ = g.them(db, user_id=CHU, pham_vi=g.NGUOI_DUNG,
                    noi_dung="Nguoi dung tu ghi", nguon=g.NGUOI)
    with pytest.raises(g.KhongDuocPhep):
        g.thay(db, user_id=CHU, ghi_nho_id=mau.id, noi_dung="model sua trom",
               boi=g.MODEL)


def test_nguoi_sua_duoc_mau_do_model_ghi(db):
    """Chiều ngược lại PHẢI mở — đó chính là lời hứa *"bạn sửa được"* của B4."""
    from apps.chatltt.services import ghi_nho as g
    cv = _hoi_thoai(db, CHU)
    mau, _ = g.ghi_boi_model(db, user_id=CHU, conv_id=cv, noi_dung="Model doan sai")
    g.thay(db, user_id=CHU, ghi_nho_id=mau.id, noi_dung="Nguoi dung sua lai")
    assert g.liet_ke(db, user_id=CHU)[0].noi_dung == "Nguoi dung sua lai"


# ------------------------------------------- model: dia chi vs do ben (D3)

def test_chu_ky_ghi_boi_model_khong_co_dia_chi():
    """⛔ Không `pham_vi`, không `muc_tieu_id`, và không `**kwargs`.

    `**kwargs` là một cửa hậu: nó cho phép thêm lại đúng những tham số này về
    sau mà chữ ký vẫn trông sạch.
    """
    from apps.chatltt.services import ghi_nho as g
    tham_so = inspect.signature(g.ghi_boi_model).parameters
    assert "pham_vi" not in tham_so
    assert "muc_tieu_id" not in tham_so
    assert not [p for p in tham_so.values()
                if p.kind is inspect.Parameter.VAR_KEYWORD]


def test_model_xin_lau_dai_ma_khong_duoc_phep_thi_ghi_HEP(db):
    """Hạ trần thì **nói ra** qua `pham_vi` của hàng trả về, không im lặng."""
    from apps.chatltt.services import ghi_nho as g
    cv = _hoi_thoai(db, CHU)
    mau, _ = g.ghi_boi_model(db, user_id=CHU, conv_id=cv, noi_dung="nho lau di",
                             lau_dai=True, cho_phep_lau_dai=False)
    assert mau.pham_vi == g.HOI_THOAI
    assert mau.muc_tieu_id == cv


def test_model_xin_lau_dai_va_duoc_phep_thi_ghi_RONG(db):
    from apps.chatltt.services import ghi_nho as g
    cv = _hoi_thoai(db, CHU)
    mau, _ = g.ghi_boi_model(db, user_id=CHU, conv_id=cv, noi_dung="nho lau di",
                             lau_dai=True, cho_phep_lau_dai=True)
    assert (mau.pham_vi, mau.muc_tieu_id) == (g.NGUOI_DUNG, "")


def test_mau_model_ghi_luon_khai_nguon_model(db):
    from apps.chatltt.services import ghi_nho as g
    cv = _hoi_thoai(db, CHU)
    mau, _ = g.ghi_boi_model(db, user_id=CHU, conv_id=cv, noi_dung="abc")
    assert mau.nguon == g.MODEL


# ------------------------------------------------------------------ trần

def test_tran_pham_vi_NOI_RA_chu_khong_am_tham_vut_mau_cu(db):
    """🔴 Đầy thì ném `KhoDay`, và **mẩu cũ còn nguyên**.

    Một kho tự quên là một kho nói dối: người dùng thấy mình đã dạy máy một
    điều, và điều đó biến mất mà không ai báo.
    """
    from apps.chatltt.services import ghi_nho as g
    dai = "x" * 500
    for i in range(4):                       # 4 x 500 = 2000 = dung tran
        g.them(db, user_id=CHU, pham_vi=g.NGUOI_DUNG, noi_dung=dai[:-1] + str(i))
    truoc = len(g.liet_ke(db, user_id=CHU))
    with pytest.raises(g.KhoDay):
        g.them(db, user_id=CHU, pham_vi=g.NGUOI_DUNG, noi_dung="mot mau nua")
    assert len(g.liet_ke(db, user_id=CHU)) == truoc == 4


def test_mau_dai_qua_tran_mot_ban_bi_chan(db):
    from apps.chatltt.services import ghi_nho as g
    from apps.chatltt.tables import TRAN_KY_TU_MOT_BAN
    with pytest.raises(g.ThamSoSai):
        g.them(db, user_id=CHU, pham_vi=g.NGUOI_DUNG,
               noi_dung="y" * (TRAN_KY_TU_MOT_BAN + 1))


# ----------------------------------------------------------- khối ngữ cảnh

def test_khoi_rong_la_CHUOI_RONG_chu_khong_phai_khoi_trong(db):
    """⛔ Một khối *"(chua co ghi nho)"* vẫn tốn token mỗi lượt **và** dạy model
    rằng nó có một kho để viện dẫn — rồi nó viện dẫn một kho trống."""
    from apps.chatltt.services import ghi_nho as g
    assert g.khoi_ngu_canh(db, user_id=CHU, conv_id=_hoi_thoai(db, CHU)) == ""


def test_khoi_xep_rong_truoc_hep_sau(db):
    """Mẩu hẹp hơn đứng gần câu hỏi hơn."""
    from apps.chatltt.services import ghi_nho as g
    cv = _hoi_thoai(db, CHU)
    g.them(db, user_id=CHU, pham_vi=g.HOI_THOAI, muc_tieu_id=cv, noi_dung="HEP")
    g.them(db, user_id=CHU, pham_vi=g.NGUOI_DUNG, noi_dung="RONG")
    khoi = g.khoi_ngu_canh(db, user_id=CHU, conv_id=cv)
    assert khoi.index("RONG") < khoi.index("HEP")


# ------------------------------------------------------------ tham số sai

def test_pham_vi_nguoi_dung_khong_duoc_co_muc_tieu(db):
    """Một id thừa làm mẩu *"áp cho mọi hội thoại"* im lặng thành mẩu chỉ áp
    cho một hội thoại — hỏng theo hướng người dùng không nhìn thấy."""
    from apps.chatltt.services import ghi_nho as g
    with pytest.raises(g.ThamSoSai):
        g.them(db, user_id=CHU, pham_vi=g.NGUOI_DUNG, muc_tieu_id="cv_abc",
               noi_dung="x")


def test_pham_vi_hoi_thoai_phai_co_muc_tieu(db):
    from apps.chatltt.services import ghi_nho as g
    with pytest.raises(g.ThamSoSai):
        g.them(db, user_id=CHU, pham_vi=g.HOI_THOAI, noi_dung="x")


def test_pham_vi_va_nguon_la_bi_tu_choi(db):
    from apps.chatltt.services import ghi_nho as g
    with pytest.raises(g.ThamSoSai):
        g.them(db, user_id=CHU, pham_vi="toan_cau", noi_dung="x")
    with pytest.raises(g.ThamSoSai):
        g.them(db, user_id=CHU, pham_vi=g.NGUOI_DUNG, noi_dung="x", nguon="admin")


def test_noi_dung_rong_bi_tu_choi(db):
    from apps.chatltt.services import ghi_nho as g
    with pytest.raises(g.ThamSoSai):
        g.them(db, user_id=CHU, pham_vi=g.NGUOI_DUNG, noi_dung="   ")
