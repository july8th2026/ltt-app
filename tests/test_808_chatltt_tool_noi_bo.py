"""
test_808 — hai tool nội bộ: đồng hồ và máy tính. (H44 P03)

Đối số của một tool đến từ **model**, và model đọc nội dung do **người dùng**
đưa vào. Nên `noi_bo.tinh` là một trình thông dịch nhận đầu vào của người lạ
qua hai lớp gián tiếp — và phần lớn tệp này là về chuyện đó, không phải về
chuyện `2+2` có ra `4` không.

Ba nhóm mệnh đề:

  1. **Không có bề mặt thực thi.** Tên, lời gọi, thuộc tính, chỉ số, lambda —
     tất cả bị chặn ở tầng AST, kể cả khi vô hại.
  2. **Không treo được.** `2 ** 10_000_000` không ném ở Python; nó *chạy*, ăn
     hết RAM và giữ worker vài phút. Đây là đường DoS thật của một "máy tính".
  3. **Lỗi đi ra bằng cửa `KetQua`.** Không ngoại lệ nào lọt lên điều phối.
"""
from __future__ import annotations

import ast
import inspect
import time

import pytest

from apps.chatltt.services import chieu_tool as C
from apps.chatltt.services import thi_hanh as T
from apps.chatltt.services import tool_noi_bo as TN


# ── 1. Máy tính: tính đúng ─────────────────────────────────────────────────

@pytest.mark.parametrize("bt,mong", [
    ("2+2", 4), ("7*6", 42), ("10/4", 2.5), ("10//4", 2), ("10%4", 2),
    ("2**10", 1024), ("-5", -5), ("+3", 3), ("(1+2)*(3+4)", 21),
    ("1_000_000*3", 3_000_000), ("2 - -2", 4),
])
def test_tinh_dung(bt, mong):
    assert TN.tinh_bieu_thuc(bt) == mong


# ── 2. Không có bề mặt thực thi ────────────────────────────────────────────

@pytest.mark.parametrize("bt", [
    "__import__('os').system('dir')",
    "open('x')",
    "().__class__",
    "[1,2][0]",
    "(lambda: 1)()",
    "[x for x in range(3)]",
    "{'a':1}",
    "'chuoi' * 3",
    "x",
    "True + 1",
    "1 if 1 else 2",
    "print",
])
def test_moi_thu_ngoai_SO_HOC_deu_bi_chan(bt):
    """⛔ Danh sách TRẮNG, không phải danh sách đen.

    `"chuoi" * 3` và `{'a':1}` vô hại. Chúng vẫn bị chặn — vì cái quyết định an
    toàn ở đây không phải *"nút này có nguy hiểm không"* mà *"nút này có nằm
    trong danh sách không"*. Một danh sách đen phải đoán trước mọi cách lách;
    một danh sách trắng thì không cần đoán gì.
    """
    with pytest.raises(TN.BieuThucSai):
        TN.tinh_bieu_thuc(bt)


def test_ma_nguon_KHONG_goi_eval_hay_exec():
    """⭐ Kiểm bằng **AST**, không bằng `"eval" in src`.

    Chuỗi `eval` có mặt trong chính docstring giải thích vì sao không dùng nó —
    một phép dò theo văn bản sẽ báo động vào đúng đoạn giải thích nó. Đây đúng
    là cái bẫy đã sinh ra `bo-do-quet-van-ban-trung-phat-viec-giai-thich`.
    """
    cay = ast.parse(inspect.getsource(TN))
    goi = {n.func.id for n in ast.walk(cay)
           if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert not ({"eval", "exec", "compile", "__import__"} & goi)


# ── 3. Không treo được ─────────────────────────────────────────────────────

def test_so_mu_khong_lo_bi_chan_NGAY_khong_phai_sau_khi_tinh():
    """🔴 Mệnh đề đắt nhất của tệp này, và nó phải đo **thời gian**.

    `2 ** 10_000_000` không ném ở Python — nó chạy. Một phép kiểm chỉ khẳng
    định "có ném" vẫn xanh với bản sửa nào tính xong rồi mới kiểm kết quả, tức
    vẫn xanh trong khi worker đã bị giữ vài phút.
    """
    t0 = time.perf_counter()
    with pytest.raises(TN.BieuThucSai):
        TN.tinh_bieu_thuc(f"2 ** {TN.TRAN_SO_MU + 1}")
    assert time.perf_counter() - t0 < 0.5, "phai chan TRUOC khi tinh"


def test_so_mu_am_khong_lo_cung_bi_chan():
    """`2 ** -10_000_000` cũng là một phép tính rất đắt. Trần phải theo **trị
    tuyệt đối**, không theo dấu."""
    with pytest.raises(TN.BieuThucSai):
        TN.tinh_bieu_thuc(f"2 ** -{TN.TRAN_SO_MU + 1}")


def test_so_mu_trong_tran_van_chay():
    assert TN.tinh_bieu_thuc("2 ** 10") == 1024


def test_bieu_thuc_qua_dai_bi_chan():
    with pytest.raises(TN.BieuThucSai):
        TN.tinh_bieu_thuc("1+" * (TN.TRAN_DAI // 2 + 10) + "1")


@pytest.mark.parametrize("bt", ["1/0", "1//0", "1%0"])
def test_chia_cho_khong_ra_BieuThucSai_khong_ro_ri_ZeroDivisionError(bt):
    with pytest.raises(TN.BieuThucSai):
        TN.tinh_bieu_thuc(bt)


def test_ket_qua_vo_han_bi_chan():
    """`1e308 * 10` ra `inf` — không ném, và `inf` đi tiếp vào JSON là một giá
    trị mà `json.dumps` sinh ra chữ `Infinity`, thứ không phải JSON hợp lệ."""
    with pytest.raises(TN.BieuThucSai):
        TN.tinh_bieu_thuc("1e308 * 10")


@pytest.mark.parametrize("bt", ["", "   ", "1 +", ")("])
def test_bieu_thuc_rong_hay_sai_cu_phap(bt):
    with pytest.raises(TN.BieuThucSai):
        TN.tinh_bieu_thuc(bt)


# ── 4. Lỗi đi ra bằng cửa `KetQua` ─────────────────────────────────────────

def test_loi_may_tinh_thanh_KetQua_khong_thanh_ngoai_le():
    """`thi_hanh` bắt rộng có chủ ý — điều phối không bao giờ thấy ngoại lệ."""
    kq = T.thi_hanh(None, user_id="u1", ten=TN.TEN_TINH,
                    doi_so={"bieu_thuc": "__import__('os')"})
    assert kq.ok is False
    assert kq.ma_loi == T.LOI_HANDLER
    assert "BieuThucSai" in kq.thong_diep
    assert "LOI[" in kq.cho_model(), "model phai doc duoc rang no that bai"


def test_tinh_chay_that_qua_cua_thi_hanh():
    kq = T.thi_hanh(None, user_id="u1", ten=TN.TEN_TINH,
                    doi_so={"bieu_thuc": "123*456"})
    assert kq.ok is True and kq.noi_dung["ket_qua"] == 56088


def test_thieu_tham_so_bat_buoc_bi_schema_chan_TRUOC_handler():
    schema = TN.KHOI[1]["function"]["parameters"]
    kq = T.thi_hanh(None, user_id="u1", ten=TN.TEN_TINH, doi_so={}, schema=schema)
    assert kq.ok is False and kq.ma_loi == T.LOI_DOI_SO


# ── 5. Đồng hồ ─────────────────────────────────────────────────────────────

def test_thoi_gian_mac_dinh_gio_VN():
    kq = T.thi_hanh(None, user_id="u1", ten=TN.TEN_THOI_GIAN, doi_so={})
    assert kq.ok is True
    assert kq.noi_dung["mui_gio"] == "vn"
    assert len(kq.noi_dung["ngay"]) == 10


def test_vn_di_truoc_utc_dung_BAY_gio():
    """Không so với một giờ chép tay — so hai đầu ra với nhau. Một hằng số giờ
    trong test là một hằng số sẽ sai vào 17:00 mỗi ngày."""
    from datetime import datetime
    a = T.thi_hanh(None, user_id="u", ten=TN.TEN_THOI_GIAN, doi_so={"mui_gio": "vn"})
    b = T.thi_hanh(None, user_id="u", ten=TN.TEN_THOI_GIAN, doi_so={"mui_gio": "utc"})
    d = (datetime.fromisoformat(a.noi_dung["iso"])
         - datetime.fromisoformat(b.noi_dung["iso"])).total_seconds()
    assert 6.9 * 3600 < d < 7.1 * 3600


def test_mui_gio_la_bi_enum_chan():
    schema = TN.KHOI[0]["function"]["parameters"]
    kq = T.thi_hanh(None, user_id="u1", ten=TN.TEN_THOI_GIAN,
                    doi_so={"mui_gio": "Asia/Tokyo"}, schema=schema)
    assert kq.ok is False and kq.ma_loi == T.LOI_DOI_SO


# ── 6. Khối chiếu + sổ handler ─────────────────────────────────────────────

def test_ca_hai_tool_da_dang_ky_handler():
    """⛔ Một tool có trong khối `tools` mà không có handler là một tool model
    sẽ gọi rồi nhận `LOI_CHUA_CAI` — ta mời nó vào một cánh cửa khoá."""
    for t in TN.KHOI:
        assert T.da_cai(t["function"]["name"])


def test_moi_tool_noi_bo_deu_co_MO_TA():
    """Model chọn tool bằng mô tả (P01 nhóm N3). Không mô tả = sẽ bị chọn sai."""
    for t in TN.KHOI:
        assert len(t["function"]["description"]) > 40


def test_lop_khai_o_chieu_tool_khop_voi_tool_noi_bo():
    """🔴 Hai tệp cùng nói về một tool. Nếu chúng lệch, `chieu_tool` là nơi
    đúng (chính sách đọc ở đó) — nhưng lệch âm thầm thì không ai biết bên nào."""
    for ten, lop in TN.LOP.items():
        assert C.lop_chinh_sach(ten) == lop


def test_tool_noi_bo_KHONG_thuoc_lop_can_duyet():
    for ten in TN.LOP:
        assert not C.can_duyet(ten)


# ── 7. Sổ handler KHÔNG phụ thuộc thứ tự import ────────────────────────────

def test_handler_co_mat_trong_MOT_TIEN_TRINH_MOI_chi_nhap_thi_hanh():
    """🔴 Phép kiểm duy nhất tái hiện được lỗi này, và nó cần một **tiến trình
    mới**.

    Trong tiến trình pytest, một tệp chạy trước có thể đã nhập `tool_noi_bo`,
    và khi ấy mọi phép kiểm ở đây xanh — kể cả khi `thi_hanh` hoàn toàn không tự
    nạp. Đó là lý do `test_812` đỏ ba phép kiểm rồi xanh lại chỉ vì đổi thứ tự.

    ⭐ Đo cái thật: khởi động Python sạch, nhập **đúng một** module, và hỏi.
    """
    import subprocess
    import sys
    from pathlib import Path

    ma = (
        "from apps.chatltt.services import thi_hanh as T\n"
        "assert T.da_cai('noi_bo.tinh'), 'da_cai khong tu nap'\n"
        "kq = T.thi_hanh(None, user_id='u', ten='noi_bo.tinh',\n"
        "                doi_so={'bieu_thuc': '6*7'})\n"
        "assert kq.ok and kq.noi_dung['ket_qua'] == 42, kq.thong_diep\n"
        "print('OK')\n"
    )
    goc = Path(__file__).resolve().parents[1]
    r = subprocess.run([sys.executable, "-c", ma], cwd=str(goc),
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "OK" in r.stdout
