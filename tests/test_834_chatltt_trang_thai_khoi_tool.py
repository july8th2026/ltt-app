"""
test_834 — khối `tool_call` phải phân biệt ĐANG CHẠY với ĐÃ XONG. (H44 P09 bước 1)

## Lỗ này chưa bao giờ nổ, và đó là lý do nó sống lâu

`_them_khoi` bản trước tuần tự hoá **ba cờ rời** (`ok`, `cho_duyet`) và bỏ hẳn
`cho_job`. Đo bằng thí nghiệm 06/09:

    DANG CHO JOB -> ok=True   cho_duyet=False  tom_tat=''
    DA XONG      -> ok=True   cho_duyet=False  tom_tat='{"key": "a.png"}'

Hai ca chỉ khác nhau **một chuỗi rỗng**. Không phép kiểm nào đỏ, không log nào
kêu, vì **không ai vẽ khối này** — P09 mới là lúc nó ra màn hình. Ngày ấy nó
thành một lời nói dối: người dùng đọc *"đã xong ✓"* trong khi job còn xếp hàng.

⭐ Đây là hình dạng *"một lỗi không bao giờ nổ vẫn là một lỗi"*: nó không có
   triệu chứng cho tới đúng lúc có người tin vào nó.

## Vì sao chốt ở tầng SERIALISATION chứ không ở giao diện

Bản vá dễ hơn nằm ở phía React: *"`tom_tat` rỗng thì vẽ spinner"*. Nó chạy đúng
hôm nay và **sai về nguyên tắc**: `tom_tat` rỗng là **thứ đại diện** cho "chưa
có kết quả". Một tool trả kết quả rỗng hợp lệ sẽ quay mãi mãi.

⇒ Phép kiểm hỏi thứ backend **ghi ra**, không hỏi thứ giao diện suy ra.
"""
from __future__ import annotations

import pytest


class _TinGia:
    """Đủ để `_them_khoi` làm việc: nó chỉ đọc/ghi `.blocks`."""

    def __init__(self, blocks=None):
        self.blocks = list(blocks or [{"type": "text", "text": "chao"}])


def _khoi_tool(buoc):
    from apps.chatltt.services import dieu_phoi as DP
    from apps.chatltt.services import luot_v3 as LV

    tin = _TinGia()
    LV._them_khoi(tin, DP.Run(buoc=[buoc]))
    ra = [k for k in tin.blocks if k.get("type") == "tool_call"]
    assert len(ra) == 1, tin.blocks
    return ra[0]


def _buoc(**kw):
    from apps.chatltt.services import dieu_phoi as DP

    kw.setdefault("ten", "image.ltt")
    kw.setdefault("doi_so", {"prompt": "con meo"})
    return DP.Buoc(0, "tool", **kw)


def _ket_qua(ok: bool, noi_dung=None, **kw):
    from apps.chatltt.services import thi_hanh

    return thi_hanh.KetQua(ok, noi_dung, **kw)


# ── 1. Bốn trạng thái, và chúng phải KHÁC NHAU ─────────────────────────────

def test_BON_trang_thai_deu_phan_biet_duoc():
    """🔴 PHÉP KIỂM QUYẾT ĐỊNH.

    Nó so **tập hợp bốn giá trị**, không kiểm từng ca — nên một bản gộp hai ca
    lại (đúng lỗi đang sửa) sẽ trượt dòng `== 4`, dù mọi ca lẻ vẫn "có giá trị".
    """
    ca = {
        "cho_duyet": _buoc(cho_duyet="ap_1"),
        "dang_chay": _buoc(cho_job="job_1"),
        "xong": _buoc(ket_qua=_ket_qua(True, {"key": "a.png"})),
        "loi": _buoc(ket_qua=_ket_qua(False, ma_loi="het_tien")),
    }
    ra = {ten: _khoi_tool(b)["trang_thai"] for ten, b in ca.items()}
    assert ra == {k: k for k in ca}, ra
    assert len(set(ra.values())) == 4


def test_doi_chung_AM_hai_truong_CU_khong_phan_biet_duoc_hai_ca_nay():
    """⭐ Đối chứng: chứng minh phép kiểm trên **đo được** thứ nó nói.

    Với `ok` + `cho_duyet` — đúng bộ trường bản cũ ghi ra — bước *đang chờ job*
    và bước *đã xong* cho **cùng một cặp giá trị**. Không có gì để phân biệt.
    """
    cho_job = _khoi_tool(_buoc(cho_job="job_1"))
    xong = _khoi_tool(_buoc(ket_qua=_ket_qua(True, {"key": "a.png"})))
    assert (cho_job["ok"], cho_job["cho_duyet"]) == (xong["ok"], xong["cho_duyet"])
    # ... va DUNG hai truong do van con, cho kha nang doc nguoc khoi CU:
    assert cho_job["trang_thai"] != xong["trang_thai"]


# ── 2. Mặc định nghiêng về phía CHƯA XONG ──────────────────────────────────

def test_buoc_khong_ket_qua_khong_co_khoa_nao_van_la_dang_chay():
    """Một bước vừa dựng, chưa chờ ai. Mặc định phải là **chưa hoàn thành**.

    ⛔ `ok=True` khi `ket_qua is None` (bản cũ) là mặc định nghiêng về phía
       **đã thành công** — hướng sai, vì nó biến một trạng thái chưa biết thành
       một lời khẳng định.
    """
    assert _khoi_tool(_buoc())["trang_thai"] == "dang_chay"


def test_ket_qua_thang_moi_co_cho():
    """`dieu_phoi` xoá `cho_duyet` khi đặt `cho_job`, nhưng phép kiểm không được
    dựa vào bất biến của module bên cạnh: đã có kết quả thì luôn thắng."""
    b = _buoc(cho_duyet="ap_1", cho_job="job_1",
              ket_qua=_ket_qua(True, {"x": 1}))
    assert _khoi_tool(b)["trang_thai"] == "xong"


# ── 3. Hợp đồng ────────────────────────────────────────────────────────────

def test_moi_trang_thai_deu_nam_trong_ban_khai():
    """Bánh cóc: thêm một trạng thái mà quên khai ⇒ đỏ ở đây."""
    from apps.chatltt.tables import TRANG_THAI_KHOI_TOOL

    for b in (_buoc(cho_duyet="a"), _buoc(cho_job="j"), _buoc(),
              _buoc(ket_qua=_ket_qua(True)), _buoc(ket_qua=_ket_qua(False))):
        assert _khoi_tool(b)["trang_thai"] in TRANG_THAI_KHOI_TOOL


def test_hai_truong_cu_VAN_con_de_doc_khoi_cu():
    """⚠️ 220 hội thoại thật có thể đang mang khối **không có** `trang_thai`.

    Bỏ `ok`/`cho_duyet` là làm chúng không đọc được — và triệu chứng sẽ là những
    lượt cũ hiện sai trạng thái, không phải một lỗi.
    """
    k = _khoi_tool(_buoc(ket_qua=_ket_qua(False, ma_loi="x")))
    assert set(k) >= {"type", "ten", "doi_so", "trang_thai", "ok", "cho_duyet",
                      "tom_tat"}


@pytest.mark.parametrize("truong", ["ten", "doi_so", "tom_tat"])
def test_khong_mat_truong_nao_giao_dien_can(truong):
    assert truong in _khoi_tool(_buoc(ket_qua=_ket_qua(True, {"k": 1})))
