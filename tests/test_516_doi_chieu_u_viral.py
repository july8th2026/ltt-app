r"""ĐỐI CHIẾU `U-` — ghim khối trạng thái ở đầu `VIRAL_VOICE_AUDIT_2026-09-07.md`.

## Vì sao tệp này tồn tại

Bản kiểm toán 07/09 liệt kê **19** phát hiện `U-`. Ba ngày sau, phần lớn đã
xong — nhưng bảng vẫn liệt kê chúng như việc còn mở, và một mục (`U-06`) là
**phát hiện sai** do chính tác giả đính chính. Ai đọc theo mặt chữ sẽ **làm lại
việc đã xong**.

Ngày 10/09 tôi chèn một khối **đối chiếu có ngày tháng** vào đầu tệp ấy.

## ⛔ Nhưng một bảng đối chiếu cũng là một bảng chép tay

Đó là toàn bộ lý do tệp này tồn tại. Bản vá cho *"bảng cũ nói sai"* mà lại là
**một bảng nữa** thì chỉ dời ngày hết hạn ra xa, không gỡ được lớp lỗi. Ba tháng
sau nó cũ y hệt, và tệ hơn: nó **trông mới hơn** nên đáng tin hơn.

⇒ Nên mỗi mục khai **XONG** phải viện dẫn một thứ **máy kiểm được**, và tệp này
  kiểm lại chúng mỗi lượt gate. Gỡ `muc_dung.py` mà quên sửa bảng ⇒ đỏ.

⚠️ Nó **không** kiểm được các mục `CHƯA` / `MỘT PHẦN` — không có gì để trỏ tới.
   Đó là giới hạn thật, và nó được nói ra thay vì giấu: bảng ấy chốt được chiều
   *"khai xong mà đã mất"*, không chốt được chiều *"khai chưa mà thật ra đã có"*.
"""
from __future__ import annotations

import pathlib
import re

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]
AUDIT = GOC / "docs/LTT_VOICE/VIRAL_VOICE_AUDIT_2026-09-07.md"

#: `U-xx` -> đường dẫn (và ký hiệu nếu có) mà bảng đối chiếu viện dẫn.
#:
#: Chỉ liệt kê mục khai **XONG** hoặc **XONG CƠ CHẾ** — mục `CHƯA` không có gì
#: để ghim, và giả vờ ghim chúng sẽ là một phép kiểm luôn xanh.
VIEN_DAN = {
    "U-01": ("apps/ltt_voice/ho_so_giong.py", None),
    "U-02": ("apps/ltt_voice/lui_giong.py", "def chon"),
    "U-03": ("apps/ltt_voice/templates/_voice_chon.html", "data-chon-vung"),
    "U-05": ("apps/ltt_voice/tham_chieu.py", "_dieu_kien_kho_chung"),
    "U-07": ("apps/ltt_voice/routes/_p_phat_dan.py", "def phat_dan"),
    "U-08": ("voice_sidecar/kiem_model.py", "def kiem"),
    "U-12": ("apps/ltt_voice/muc_dung.py", None),
    "U-13": ("apps/ltt_voice/nghe_thu_cua_toi.py", "TRAN_KY_TU"),
    "U-14": ("apps/ltt_voice/chi_so_giong.py", None),
    "U-15": ("apps/ltt_voice/text_pipeline.py", "KhuonChuanHoa"),
}


def _khoi_doi_chieu() -> str:
    t = AUDIT.read_text(encoding="utf-8")
    i = t.find("ĐỐI CHIẾU 10/09/2026")
    assert i > 0, "khoi doi chieu da bien mat khoi ban kiem toan"
    return t[i:t.find("## ⛔ ĐỌC DÒNG NÀY TRƯỚC", i)]


def test_khoi_doi_chieu_dung_TRUOC_bang_U():
    """⛔ Vị trí là nửa của bản vá, không phải chi tiết trình bày.

    Khối đối chiếu nằm **sau** bảng 19 mục thì người quét nhanh đọc bảng trước,
    rút ra danh sách việc, rồi đi làm — đúng kiểu hỏng nó sinh ra để chặn.
    """
    t = AUDIT.read_text(encoding="utf-8")
    vt_doi_chieu = t.find("ĐỐI CHIẾU 10/09/2026")
    vt_bang = t.find("| 1 | **U-01**")
    assert 0 < vt_doi_chieu < vt_bang, (
        "khoi doi chieu phai dung TRUOC bang 19 muc")


def test_moi_muc_XONG_deu_co_mat_trong_bang():
    """Bảng thiếu một mục đã ghim ⇒ đỏ. Chặn kiểu sửa bảng mà quên tệp này."""
    khoi = _khoi_doi_chieu()
    thieu = [u for u in VIEN_DAN if f"| {u} |" not in khoi
             and f"~~{u}~~" not in khoi]
    assert not thieu, f"cac muc nay khong con trong bang doi chieu: {thieu}"


@pytest.mark.parametrize("ma", sorted(VIEN_DAN))
def test_thu_ma_muc_XONG_vien_dan_VAN_CON(ma):
    """🔑 Đây là chốt thật: bảng khai "XONG" thì thứ nó trỏ tới phải còn sống.

    Ai gỡ `muc_dung.py` mà quên sửa bảng sẽ thấy đỏ ở đây, chứ không phải ba
    tháng sau khi có người đọc bảng rồi đi tìm một tệp không tồn tại.
    """
    duong, ky_hieu = VIEN_DAN[ma]
    tep = GOC / duong
    assert tep.exists(), (
        f"{ma}: bang doi chieu khai XONG va vien dan `{duong}`, nhung tep do "
        f"KHONG con — hoac khoi phuc ma, hoac sua bang")
    if ky_hieu:
        assert ky_hieu in tep.read_text(encoding="utf-8"), (
            f"{ma}: `{duong}` con nhung khong con `{ky_hieu}` — bang doi chieu "
            f"dang noi ve mot thu da doi")


def test_U06_van_duoc_danh_dau_la_PHAT_HIEN_SAI():
    """⛔ Mục dễ bị "sửa lại cho gọn" nhất, và sửa là mất bản ghi.

    `U-06` gạch ngang **có chủ đích**: nó ghi lại việc một lượt soát đã kết luận
    sai. Xoá nó đi thì bảng đẹp hơn và kho **nghèo đi** — lần sau không ai biết
    lượt soát ấy có thể sai ở đâu.
    """
    khoi = _khoi_doi_chieu()
    assert re.search(r"~~U-06~~", khoi), "U-06 phai giu dang gach ngang"
    assert "PHÁT HIỆN SAI" in khoi, "phan quyet cua U-06 da bien mat"


def test_con_so_tong_ket_KHOP_voi_bang():
    """Bảng tổng kết ở cuối khối phải cộng đúng 19 — nếu không thì có mục rơi."""
    khoi = _khoi_doi_chieu()
    so = [int(x) for x in
          re.findall(r"^ {4}[A-Z][A-Za-z ,]*?:\s*(\d+)", khoi, re.M)]
    assert len(so) == 5, (
        f"bang tong ket phai co dung 5 dong (XONG · XONG CO CHE · MOT PHAN · "
        f"CHUA · PHAT HIEN SAI), doc duoc {len(so)}: {so}")
    assert sum(so) == 19, (
        f"tong ket cong ra {sum(so)}, phai la 19 muc U- ({so})")
