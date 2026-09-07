"""
test_827 — trích dẫn: chữ và NGUỒN không tách rời nhau được. (H44 P06 bước 5)

## Mệnh đề trung tâm, và vì sao nó là chuyện HÌNH DẠNG chứ không phải quy ước

P06 §4 giải thích bước 5 bằng một câu: không có trích dẫn thì truy hồi là *"một
cái máy nói linh tinh có tự tin"*. Nhưng một quy ước *"nhớ kèm nguồn"* sẽ bị
quên, và nó bị quên **im lặng** — câu trả lời vẫn trôi chảy, chỉ là không ai
kiểm được nó lấy từ đâu.

⇒ Nên thứ chặn phải là **hình dạng dữ liệu**: không có đường nào lấy được chữ
  mà không cầm theo nguồn. Tệp này chốt đúng điều đó, và chốt trên **mọi** phần
  tử — vì một hàm quên gắn nguồn cho đoạn thứ ba vẫn qua được phép kiểm chỉ
  nhìn đoạn đầu.
"""
from __future__ import annotations

import pytest

CHU = "u-chu-827"
LA = "u-la-827"


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


def _canh(db, *, so_doan=6, ten_tep="bao cao quy bon.pdf", conv="c1"):
    """Một tệp đã gắn + `so_doan` đoạn, mỗi đoạn một trang khác nhau."""
    from apps.chatltt.services import chia_doan
    from apps.chatltt.tables import ChatlttDoan, ChatlttTep

    tep = ChatlttTep(user_id=CHU, conversation_id=conv, upload_id="up1",
                     ten_tep=ten_tep, content_type="application/pdf")
    db.add(tep)
    db.flush()
    for i in range(so_doan):
        noi = f"Doan so {i} noi ve credit va token va doanh thu quy bon."
        db.add(ChatlttDoan(user_id=CHU, conversation_id=conv, tep_id=tep.id,
                           thu_tu=i, trang=i + 1, noi_dung=noi,
                           so_ky_tu=len(noi), bam=chia_doan.bam(noi)))
    db.flush()
    return tep


# ── 1. Chữ và nguồn dính liền ─────────────────────────────────────────────

def test_MOI_doan_tra_ve_deu_mang_trich_dan_day_du(db):
    """🔴 Mệnh đề trung tâm. Quét **mọi** phần tử, không chỉ phần tử đầu."""
    from apps.chatltt.services import tim_doan

    tep = _canh(db)
    ra = tim_doan.cho_tool(db, user_id=CHU, conversation_id="c1",
                           cau_hoi="credit token", so_doan=5)

    assert ra["so_khop"] >= 3, "canh nay phai khop nhieu doan moi co nghia"
    for d in ra["doan"]:
        td = d["trich_dan"]
        assert d["noi_dung"], "co trich dan ma khong co chu"
        assert td["tep_id"] == tep.id
        assert td["doan_id"], "thieu doan_id — khong tro nguoc ve duoc"
        assert td["ten_tep"] == "bao cao quy bon.pdf", (
            "thieu ten tep — trich dan dung ma nguoi dung khong doc duoc")
        assert isinstance(td["trang"], int)


def test_KHONG_co_duong_nao_lay_duoc_chu_TRAN(db):
    """⛔ Đối chứng cấu trúc: nếu có một khoá nào trả về danh sách chuỗi, thì
    quy ước "nhớ kèm nguồn" đã quay lại — và nó sẽ bị quên."""
    from apps.chatltt.services import tim_doan

    _canh(db)
    ra = tim_doan.cho_tool(db, user_id=CHU, conversation_id="c1",
                           cau_hoi="credit")
    for khoa, gia_tri in ra.items():
        if isinstance(gia_tri, list):
            assert all(isinstance(x, dict) and "trich_dan" in x for x in gia_tri), (
                f"khoa {khoa!r} tra ve chu tran, khong kem nguon")


def test_trang_dung_bang_trang_that_cua_doan(db):
    """⭐ Trích dẫn **đúng** mới có giá trị. Một trích dẫn trỏ nhầm trang tệ hơn
    không trích dẫn: nó mời người ta đi kiểm rồi làm họ mất niềm tin vào cả
    những trích dẫn đúng."""
    from apps.chatltt.services import tim_doan
    from apps.chatltt.tables import ChatlttDoan

    _canh(db)
    ra = tim_doan.cho_tool(db, user_id=CHU, conversation_id="c1",
                           cau_hoi="credit", so_doan=5)
    for d in ra["doan"]:
        that = db.get(ChatlttDoan, d["trich_dan"]["doan_id"])
        assert that is not None
        assert d["trich_dan"]["trang"] == that.trang
        assert d["noi_dung"] == that.noi_dung


# ── 2. Phân biệt "không có tài liệu" với "câu hỏi quá hẹp" ────────────────

def test_KHONG_co_tai_lieu_nao_khac_voi_CAU_HOI_QUA_HEP(db):
    """🔴 Đây đúng cái bẫy đã dính khi viết `test_821`.

    `plainto_tsquery` nối các từ bằng **AND**, nên **một** từ vắng mặt làm cả
    câu trượt — **giống hệt** triệu chứng "chưa đính tài liệu nào". Hai nguyên
    nhân, một triệu chứng; gộp chúng thì giao diện sẽ nói *"bạn chưa có tài
    liệu"* với một người vừa tải lên ba tệp.
    """
    from apps.chatltt.services import tim_doan

    # (a) chua co tai lieu nao
    trong = tim_doan.cho_tool(db, user_id=CHU, conversation_id="c-trong",
                              cau_hoi="credit")
    assert trong["so_khop"] == 0
    assert trong["co_tai_lieu"] is False

    # (b) CO tai lieu, nhung cau hoi chua mot tu khong ton tai
    _canh(db)
    hep = tim_doan.cho_tool(db, user_id=CHU, conversation_id="c1",
                            cau_hoi="credit va ca heo bay")
    assert hep["so_khop"] == 0
    assert hep["co_tai_lieu"] is True, (
        "gop hai nguyen nhan lam mot — giao dien se noi 'ban chua co tai lieu' "
        "voi mot nguoi vua tai len")


# ── 3. Quyền vẫn giữ ở lớp này ────────────────────────────────────────────

def test_nguoi_LA_khong_lay_duoc_trich_dan_cua_chu(db):
    """⛔ Một lớp mới là một cửa quyền mới. Nó không được vay bất biến của lớp
    dưới — `cho_tool` phải tự lọc chủ, kể cả khi `tim()` đã lọc."""
    from apps.chatltt.services import tim_doan

    _canh(db)
    ra = tim_doan.cho_tool(db, user_id=LA, conversation_id="c1",
                           cau_hoi="credit")
    assert ra["doan"] == []
    assert ra["co_tai_lieu"] is False, (
        "nguoi la biet duoc hoi thoai nay CO tai lieu — mot ro ri nho nhung that")


def test_ten_tep_KHONG_lay_duoc_tu_tep_cua_nguoi_KHAC(db):
    """🔴 Lớp này phải TỰ vệ, không vay bất biến của lớp dưới.

    ⛔ **Bản đầu của phép kiểm này không thể đỏ.** Nó chỉ tạo một `ChatlttTep`
       của người lạ rồi kiểm tên tệp ấy không lọt ra. Nhưng id của tệp ấy **không
       bao giờ** vào tập tra, vì `tim()` đã lọc chủ ở lớp dưới — nên bỏ hẳn bộ
       lọc `user_id` khỏi phép tra `ten_tep` thì **7/7 vẫn xanh**. Tôi đang đo
       một bộ lọc thừa trong đúng cảnh tôi tự dựng.

    ⭐ Cảnh phân biệt được phải là cảnh **chéo**: một đoạn của CHỦ trỏ tới một
       tệp của NGƯỜI LẠ. Trạng thái ấy không xảy ra hôm nay, và đó chính là lý
       do phải chốt nó — nó là thứ sẽ xảy ra vào ngày một bản sửa ở `tim()` nới
       phạm vi, và khi đó lớp này là hàng phòng thủ còn lại.
    """
    from apps.chatltt.services import chia_doan, tim_doan
    from apps.chatltt.tables import ChatlttDoan, ChatlttTep

    _canh(db)
    la = ChatlttTep(user_id=LA, conversation_id="c1", upload_id="up9",
                    ten_tep="tai lieu rieng cua nguoi khac.pdf",
                    content_type="application/pdf")
    db.add(la)
    db.flush()

    # Trang thai CHEO: doan mang `user_id` cua CHU nhung `tep_id` cua NGUOI LA.
    noi = "Doan cheo noi ve credit va token."
    db.add(ChatlttDoan(user_id=CHU, conversation_id="c1", tep_id=la.id,
                       thu_tu=99, trang=3, noi_dung=noi, so_ky_tu=len(noi),
                       bam=chia_doan.bam(noi)))
    db.flush()

    ra = tim_doan.cho_tool(db, user_id=CHU, conversation_id="c1",
                           cau_hoi="credit token", so_doan=10)
    assert any(d["trich_dan"]["tep_id"] == la.id for d in ra["doan"]), (
        "canh sai: doan cheo phai LOT vao ket qua thi phep kiem moi co nghia")
    ten = {d["trich_dan"]["ten_tep"] for d in ra["doan"]}
    assert "tai lieu rieng cua nguoi khac.pdf" not in ten, (
        "ten tep cua nguoi khac lo ra qua phep tra `ten_tep` khong loc chu")


# ── 4. Nền tảng vẫn tự khai ───────────────────────────────────────────────

def test_ket_qua_NOI_RA_no_den_tu_duong_nao(db):
    """⭐ Giữ tiếp ranh giới của `test_826`: người đọc kết quả phải biết nó đến
    từ đường thật hay đường phụ. Một kết quả không tự khai là một kết quả sẽ bị
    đọc nhầm thành bằng chứng."""
    from apps.chatltt.services import tim_doan

    _canh(db)
    ra = tim_doan.cho_tool(db, user_id=CHU, conversation_id="c1",
                           cau_hoi="credit")
    assert ra["nen_tang"] == "sqlite"
