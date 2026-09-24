"""N-03: hai con số hệ thống ĐÃ ĐO phải HIỆN RA trên trang khách, render thật.

## Vì sao tệp này tách khỏi `test_3000`

`test_3000` §5 chốt rằng template **có chứa** `bang_chung.ngu_nghia` và
`bang_chung.con_lai`. Đó là một phép kiểm **tĩnh**, và nó xanh cả khi khối đó
không bao giờ render — ví dụ khi `quan_sat` đặt khoá khác tên với cái template
đọc, hoặc khi điều kiện `{% if %}` không bao giờ đúng.

⛔ Đúng lớp lỗi G-01 trong sổ lỗi phiên này: *`dung_cai_dat` duyệt giá trị rồi
KHÔNG đặt vào hồ sơ trả về — mỗi phép kiểm hỏi một mắt xích, và không phép nào
bắt được*. Một phép kiểm hỏi "template có chữ đó không" và một phép kiểm hỏi
"`quan_sat` có trả khoá đó không" đều xanh trong khi **đường dây** đứt ở giữa.

⇒ Nên tệp này **render trang thật qua HTTP** và tìm đúng con số trên HTML.

## Con số ở đây là số THẬT của lượt B (24/09)

Không phải số tròn cho dễ đọc: `44/95` ngữ nghĩa và `85` mục còn lại là đúng cái
lượt nghiệm thu B đo được trên phim khách, và đúng cái màn hình đã **im lặng** về
nó. Một phép kiểm dùng số thật thì khi nó đỏ, người đọc biết ngay nó nói về cái gì.
"""
from __future__ import annotations

import pytest

from tests import test_2101_asv_gui_bang_chung_chat_luong as _g
from tests import test_423_asv_giao_dien as _mt

moi_truong = _mt.moi_truong

#: Số đo THẬT của lượt B 24/09 (phim khách `深度解析…`, zh→vi, giữ hình).
SO_LUOT_B = {
    "transcribe": {"dinh_tuyen": {"che_do": "auto", "nguon_loi": "ocr",
                                  "ly_do": ["khong_co_phu_de_nhung"]}},
    "qc": {"qc_ky_thuat_dat": True, "qc_so_muc_hong": 0,
           "qc_muc_hong": [], "qc_phien_ban": 4},
    "qc_do_luong": {"so_doan_do": 95,
                    "do_luong": {"giong": "xong", "chat_luong_tieng": "xong",
                                 "dich": "xong"},
                    "so_giong_khong_dat": 14,
                    "canh_bao_tieng": [{"ma": f"seg_{i:04d}"} for i in range(8)]},
    "qc_ai": {"qc_ai_bat": True, "so_muc": 95, "so_co_phan_quyet": 95,
              "so_khong_dat": 44, "qc_hinh_khong_dat": [],
              "qc_hinh_la_tu_van": True, "qc_hinh_so_cho_noi": 0},
}


def _gieo_so_cai_con_lai(run_id: str, so_muc: int = 85) -> None:
    """Ghi dong `sua_chua_con_lai` vao SO CAI.

    🔴 **Con so 85 KHONG nam trong `asv_stage.outputs`** — no nam trong
       `asv_usage`, vi `jobs.py:264` ghi no vao SO CAI chu khong vao `outputs`
       (*"mot dong log bien mat sau mot tuan, va cau hoi 'vi sao doan nay nghe hoi
       don' se duoc hoi sau do lau hon the"*).

    ⛔ Va chinh cho nay la ly do tep test nay ton tai. Ban dau bo canh chi gieo
       `outputs`, va phep kiem 85 **DO** — dung nhu no nen do. Mot phep kiem tinh
       ("template co chua `bang_chung.con_lai` khong") se XANH o dung tinh huong
       do, vi template co that, chi la khong co du lieu nao toi no.
    """
    import platform_core.db as dbmod

    from apps.auto_scan_video import tables as T

    db = next(dbmod.get_session())
    try:
        run = db.get(T.AsvRun, run_id)
        db.add(T.AsvUsage(
            run_id=run_id, owner_id=run.owner_id, stage="qc",
            item_key="sua_chua", attempt=1, nang_luc="sua_chua_con_lai",
            app_chu="auto_scan_video", trang_thai="da_giao", don_vi="luot",
            so_luong=float(so_muc), credit=0, ma_dispatch="sua-con-lai:1",
            ghi_chu={"vong": 1, "can_sua": True, "con_vong": False}))
        db.commit()
    finally:
        db.close()


@pytest.fixture()
def trang(moi_truong, tmp_path):  # noqa: F811
    _app, a, csrf, _b, _csrf_b = moi_truong
    run_id = _g._tao(a, csrf, tmp_path)
    _g._gieo(run_id, SO_LUOT_B)
    _gieo_so_cai_con_lai(run_id, 85)
    return a.get(f"/auto-scan-video/run/{run_id}").text


def test_man_khach_NOI_RA_44_tren_95_cau_dich_chua_sat(trang):
    """⛔ Lượt B giao một video mà hệ thống tự chấm 46% câu là dịch chưa sát.

    Màn hình **không nói** — và đó là khiếm khuyết TRUNG THỰC, nặng hơn khiếm
    khuyết chất lượng: khách không thể hỏi về một con số không ai cho họ thấy.
    """
    assert "Soát nghĩa bản dịch" in trang
    assert "44" in trang and "95" in trang
    khoi = trang.split("Soát nghĩa bản dịch", 1)[1][:300]
    assert "44" in khoi, khoi


def test_man_khach_NOI_RA_85_muc_con_chua_sua(trang):
    """Vòng sửa chạy ĐÚNG một vòng (`VONG_SUA_TOI_DA = 1`) rồi giao hàng.

    Khách phải biết điều đó, chứ không chỉ thấy chữ *"Đã xong."*
    """
    assert "Còn chưa sửa" in trang
    khoi = trang.split("Còn chưa sửa", 1)[1][:300]
    assert "85" in khoi, khoi


def test_nhan_QC_ky_thuat_KHONG_noi_rong_hon_pham_vi(trang):
    """N-02: `qc_ky_thuat_dat=True` + 44 mục ngữ nghĩa không đạt, CÙNG một trang.

    ⛔ Nhãn cũ (*"Kiểm chất lượng tự động … đạt toàn bộ"*) đứng cạnh 44 mục dịch
       chưa sát là một câu **đúng về chữ, sai về điều người đọc sẽ hiểu**. Đó đúng
       hình dạng lỗi gate vá ở `f4c4f064`.
    """
    assert "Kiểm kỹ thuật tự động" in trang
    assert "Kiểm chất lượng tự động" not in trang


def test_cau_ve_doan_doc_lai_khong_con_NOI_SAI(trang):
    """`so_giong_khong_dat` = số đoạn VẪN chưa khớp ở lần đo CUỐI, không phải
    số đoạn "đã được đọc lại"."""
    assert "đã được đọc lại vì chưa khớp lời" not in trang
    assert "chưa khớp lời ở lần đo cuối" in trang


def test_khong_co_qc_ai_thi_KHONG_bay_ra_mot_so_KHONG(moi_truong, tmp_path):  # noqa: F811
    """⛔ `qc_ai` TẮT (mặc định vận hành) ⇒ **không** hiện khối ngữ nghĩa.

    🔑 Vì "0 câu bị chấm" và "chưa đo" là hai điều rất khác nhau, và gộp chúng
       thành một số 0 là đúng bẫy *"số 0 cần đối chứng"*: một lượt không đo gì sẽ
       trông như một lượt sạch.
    """
    _app, a, csrf, _b, _csrf_b = moi_truong
    khong_qc_ai = {k: v for k, v in SO_LUOT_B.items() if k != "qc_ai"}
    run_id = _g._tao(a, csrf, tmp_path)
    _g._gieo(run_id, khong_qc_ai)
    trang = a.get(f"/auto-scan-video/run/{run_id}").text
    assert "Soát nghĩa bản dịch" not in trang
