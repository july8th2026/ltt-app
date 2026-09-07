"""`MayThat` — client **mỏng** tới WanGP, không phải một engine abstraction.

🔴 **Viết lại 07/09 (HM-2).** Tệp này trước tên là `test_722_lttvideo_wangp_client`
   và kiểm `apps/lttvideo/wangp_client.py`, nay đã gỡ.

⛔ Không một mệnh đề nào bị xoá theo. Mệnh đề chúng canh — *gửi nguyên văn* ·
   *khoá đi theo mọi lệnh kể cả GET* · *lỗi mạng thành lỗi của app* · *client
   không biết gì về tiền* · *huỷ khác hỏng* — **không đổi một chữ** khi mã đổi
   chỗ. Xoá một phép kiểm vì mã đổi chỗ là bỏ một đảm bảo, không phải dọn dẹp.

Hai mệnh đề **mạnh lên** sau lần viết lại, và một mệnh đề **chuyển nhà**:

| Cũ | Nay |
|---|---|
| `result()` đoán huỷ bằng **dò chuỗi** `"cancelled"` trong lỗi | đọc thẳng trường `huy` (= `GenerationResult.cancelled`) |
| *(không có)* | `tai_ve` phải **tồn tại** — bản cũ không có nó, và mọi lượt thật đều chết ở đó |
| `health()` | chuyển sang `dieu_phoi` — nó hỏi về **máy**, không hỏi về **engine** |

Kiểm bằng hàm vận chuyển tiêm vào, nên chạy được **không cần mạng, không cần GPU**.
"""
from __future__ import annotations

import pytest

from apps.lttvideo.cong.giao_uoc import LoiMay
from apps.lttvideo.cong.may_that import MayThat


class GoiGia:
    """Hàm vận chuyển giả — ghi lại mọi lượt gọi để phép kiểm soi được."""

    def __init__(self, dap: dict | None = None):
        self.dap = dap or {}
        self.da_goi: list[tuple[str, str, dict | None]] = []

    def __call__(self, method: str, duong: str, *, than=None, tho=None,
                 timeout: float = 30.0, nhi_phan: bool = False):
        self.da_goi.append((method, duong, than))
        for mau, gia_tri in self.dap.items():
            if mau in duong:
                if isinstance(gia_tri, Exception):
                    raise gia_tri
                return gia_tri
        return b"" if nhi_phan else {}


def _may(dap=None):
    g = GoiGia(dap)
    return MayThat("https://c-cloud.test", khoa="KHOA", goi=g), g


# ── Tra cứu: bốn đường, đúng bốn đường dẫn ─────────────────────────────────

@pytest.mark.parametrize("ten_ham,doi_so,duong_mong_doi,khoa_dap", [
    ("so_do", ("t2v_2_2",), "/model/t2v_2_2/so-do", "so_do"),
    ("mac_dinh", ("t2v_2_2",), "/model/t2v_2_2/mac-dinh", "mac_dinh"),
    ("kha_dung", ("t2v_2_2",), "/model/t2v_2_2/kha-dung", "kha_dung"),
])
def test_tra_cuu_goi_dung_duong_va_boc_dung_khoa(ten_ham, doi_so,
                                                 duong_mong_doi, khoa_dap):
    m, g = _may({duong_mong_doi: {khoa_dap: {"x": 1}}})
    assert getattr(m, ten_ham)(*doi_so) == {"x": 1}
    method, duong, than = g.da_goi[0]
    assert method == "GET" and duong == duong_mong_doi and than is None


def test_liet_ke_model_dua_bo_loc_vao_QUERY_va_gia_tri_lap_thanh_nhieu_cap():
    """`docs_API.md` nói nhiều giá trị là phép HOẶC. Gộp chúng thành một chuỗi
    ngăn bằng dấu phẩy sẽ thành **một** giá trị không khớp gì."""
    m, g = _may({"/model": {"model": [{"model_type": "a"}]}})
    assert m.liet_ke_model(main_output="video", inputs=["image", "video"]) == [
        {"model_type": "a"}]
    _, duong, _ = g.da_goi[0]
    assert "main_output=video" in duong
    assert duong.count("inputs=") == 2, f"gia tri lap bi gop lai: {duong}"


# ── Chạy việc ──────────────────────────────────────────────────────────────

def test_gui_viec_gui_tham_so_va_nhan_ve_ma():
    m, g = _may({"/submit": {"job_id": "J-1"}})
    assert m.gui_viec({"model_type": "t2v_2_2", "prompt": "x"}) == "J-1"


def test_gui_viec_KHONG_tu_them_tham_so_nao():
    """⭐ Mệnh đề gốc, giữ nguyên: client **chuyển tiếp**, không diễn giải.

    Thêm một tham số "cho tiện" ở đây là dựng một bảng mặc định thứ hai, song
    song với `get_default_settings()` của WanGP — và hai bảng mặc định thì một
    cái sai."""
    m, g = _may({"/submit": {"job_id": "J-1"}})
    goc = {"model_type": "t2v_2_2", "prompt": "x", "seed": 7}
    m.gui_viec(dict(goc))
    _, _, than = g.da_goi[0]
    assert than["settings"] == goc, "client tu them/bot tham so"


def test_tien_do_tra_ve_NGUYEN_VAN_su_kien_cua_wangp():
    m, g = _may({"/progress/J-1": {"phase": "denoising", "current_step": 3}})
    assert m.tien_do("J-1") == {"phase": "denoising", "current_step": 3}


def test_huy_goi_dung_viec():
    m, g = _may()
    m.huy("J-9")
    method, duong, than = g.da_goi[0]
    assert method == "POST" and duong == "/cancel/J-9"


# ── Huỷ khác hỏng — và nay đọc TRƯỜNG, không dò CHUỖI ──────────────────────

def test_ket_qua_nhan_dien_luot_bi_HUY_bang_TRUONG_chu_khong_bang_chuoi():
    """🔴 Mệnh đề mạnh lên. Bản cũ (`KetQua.da_huy`) tìm chuỗi `"cancelled"`
    trong thông điệp lỗi để đoán người dùng có bấm huỷ không.

    Đó là một phép phân biệt **về tiền** — huỷ thì hoàn phần chưa dùng, hỏng
    thì không trừ — đặt trên **cách diễn đạt của thượng nguồn**. Một lần WanGP
    đổi chữ là một lần cách tính tiền ở đây đổi theo, lặng lẽ, và không phép
    kiểm nào thấy vì phép kiểm cũng dùng đúng chuỗi ấy.
    """
    m, _ = _may({"/result/J-1": {"success": False, "huy": True,
                                 "errors": ["bat ky chu gi"], "generated_files": []}})
    assert m.ket_qua("J-1")["huy"] is True


def test_hong_that_thi_KHONG_bi_coi_la_huy():
    m, _ = _may({"/result/J-2": {"success": False, "huy": False,
                                 "errors": ["CUDA out of memory"],
                                 "generated_files": []}})
    kq = m.ket_qua("J-2")
    assert kq["huy"] is False and kq["loi"] == ["CUDA out of memory"]


def test_chuoi_cancelled_trong_LOI_khong_con_bien_mot_luot_HONG_thanh_HUY():
    """⛔ Đối chứng cho phép kiểm trên. Một lỗi thật vô tình chứa chữ
    `cancelled` (ví dụ *"upstream connection cancelled by peer"*) là **hỏng**,
    không phải người dùng bấm huỷ — và tiền của hai ca ấy khác nhau."""
    m, _ = _may({"/result/J-3": {"success": False, "huy": False,
                                 "errors": ["upstream connection cancelled by peer"],
                                 "generated_files": []}})
    assert m.ket_qua("J-3")["huy"] is False


def test_ket_qua_thanh_cong_tra_danh_sach_tep():
    m, _ = _may({"/result/J-4": {"success": True, "huy": False, "errors": [],
                                 "generated_files": ["/data/out/a.mp4"]}})
    kq = m.ket_qua("J-4")
    assert kq["tep"] == ["/data/out/a.mp4"] and not kq["loi"]


# ── Lấy ra: mệnh đề MỚI, sinh ra từ một lỗi thật ───────────────────────────

def test_tai_ve_TON_TAI_va_goi_theo_CHI_SO():
    """🔴 Bản cũ **không có** `tai_ve`, mà `jobs.py` gọi nó qua
    `getattr(client, "tai_ve", None)` rồi báo lỗi tử tế khi thiếu.

    ⇒ Mọi lượt chạy thật đều dừng ở *"Không tải được kết quả về"*, và thông điệp
      tử tế ấy làm một **lỗ hổng** trông như một **trường hợp biên đã xử lý**.
      Đây là lý do phép kiểm này tồn tại.
    """
    m, g = _may({"/tai/J-5/0": b"NOI DUNG VIDEO"})
    assert m.tai_ve("J-5", 0) == b"NOI DUNG VIDEO"
    method, duong, _ = g.da_goi[0]
    assert method == "GET" and duong == "/tai/J-5/0"


def test_don_dep_goi_dung_viec():
    m, g = _may()
    m.don_dep("J-6")
    method, duong, _ = g.da_goi[0]
    assert method == "POST" and duong == "/cleanup/J-6"


def test_nap_media_tu_choi_byte_RONG():
    """Một tệp 0 byte đi trót lọt sẽ làm WanGP hỏng ở tận khâu giải mã, và
    thông điệp lỗi lúc đó nói về VAE chứ không nói về tệp đầu vào."""
    m, _ = _may()
    with pytest.raises(LoiMay, match="rong"):
        m.nap_media(b"")


# ── Bất biến về xác thực, lỗi, và ranh giới ────────────────────────────────

def test_khoa_endpoint_di_theo_MOI_lenh_goi_ke_ca_GET():
    """Header chứ không phải thân — nếu không thì đường `GET` không xác thực
    được, và bốn đường tra cứu đều là `GET`."""
    import inspect

    ma = inspect.getsource(MayThat._goi)
    assert "HEADER_KHOA" in ma and "add_header" in ma
    assert "if self.khoa" in ma


def test_loi_mang_duoc_boc_thanh_LoiMay():
    m, _ = _may({"/result/J-7": TimeoutError("timed out")})
    with pytest.raises(LoiMay):
        m.ket_qua("J-7")


def test_may_KHONG_biet_gi_ve_credit_hay_nguoi_dung():
    """⭐ Mệnh đề ranh giới, giữ nguyên từ bản cũ. Tiền và quyền sở hữu thuộc
    **LTT**; C-CLOUD chỉ biết GPU và tệp (PHẦN 7 — khoá security)."""
    import inspect

    ma = inspect.getsource(MayThat)
    for cam in ("credit", "user_id", "nguoi_dung", "gia_", "billing"):
        assert cam not in ma, f"client biet ve {cam!r} — sai ranh gioi so huu"


def test_luot_tra_cuu_DAU_TIEN_duoc_cho_lau_hon_cac_luot_sau():
    """🔴 Đo trên máy thật 08/09: lượt tra cứu đầu tiên **hết giờ ở 30 giây**,
    rồi sau khi phiên WanGP ấm thì cùng lệnh ấy về trong **1 giây**.

    Nguyên nhân: bốn đường tra cứu đúng là *không nhân ma trận* — nhưng chúng
    gọi `_lay_phien()`, và lần đầu `init()` nạp cả runtime WanGP. Hợp đồng nói
    **chưa đủ**, không phải nói sai.

    ⛔ Cách sửa sai là nâng `CHO_MAC_DINH_S` lên cho vừa: thế thì **mọi** lượt
       tra cứu về sau đều chờ được mười lăm phút trước khi chịu báo hỏng, và một
       cầu nối chết sẽ giữ một worker mười lăm phút thay vì hỏng ngay.
    """
    from apps.lttvideo.cong import may_that as mt

    ghi: list[float] = []

    def goi(method, duong, *, than=None, tho=None, timeout=30.0, nhi_phan=False):
        ghi.append(timeout)
        return {"model": [], "so_do": {}}

    m = mt.MayThat("https://x.test", khoa="K", goi=goi)
    m.liet_ke_model()
    m.so_do("bat_ky")
    assert ghi[0] == mt.CHO_HAM_NONG_S, "luot dau khong duoc cho lau hon"
    assert ghi[1] == mt.CHO_MAC_DINH_S, "luot sau van cho lau — cau noi chet se giu worker"
    assert mt.CHO_HAM_NONG_S > mt.CHO_MAC_DINH_S
