"""test_390 — điều khoản API: mọi con số phải là con số THẬT, và không được bịa.

🔴 VÌ SAO TỆP NÀY TỒN TẠI. Đo 01/09 trên bản đang chạy: trang điều khoản duy
nhất mà `/register` trỏ tới (`https://lttstudios.com/terms/`) có **21.335 ký tự**
và **không nhắc** `API`, `credit`, `hoàn tiền`, `trách nhiệm`, `SLA`, `thanh
toán`. Nền tảng bán một dịch vụ tính tiền theo mức dùng mà điều khoản không mô
tả dịch vụ đó.

⭐ Bài học chép từ `apps/vps/dieu_khoan.py`, nơi đã trả giá: bản WordPress
   `/vps-terms/` **trả 404 suốt** trong khi clickwrap đã trỏ vào nó — khách
   "đồng ý" với một trang không tồn tại, đúng lúc sắp trả tiền.

⛔ VÀ MỘT LUẬT NỮA, RIÊNG CHO TỆP NÀY: điều khoản **không được chứa lời hứa
   chưa ai đưa ra**. Phép kiểm cuối cùng ở đây canh đúng chuyện đó — nó bắt
   `san_sang()` phải `False` chừng nào còn mục chưa quyết, để ô tích "tôi đồng ý"
   không thể xuất hiện trước khi có gì thật để đồng ý.
"""
from __future__ import annotations

import pytest

from platform_core.public_api import dieu_khoan as dk


# ── 1. Số trong điều khoản = số ra hoá đơn ──────────────────────────────────

def test_bang_gia_LA_bang_cua_ham_ra_hoa_don():
    """Không phải một bảng thứ hai — phải là **chính** hàm tính tiền.

    ⛔ Bản chép thứ hai của một bảng giá là một bảng giá thứ hai, và ngày hai
       bảng lệch nhau thì bảng nào cũng không đáng tin.
    """
    from platform_core.llm import gia_token

    assert dk.bang_gia() == gia_token.bang_gia()


def test_KHONG_go_tay_con_so_gia_nao_trong_tep():
    """Bánh cóc: cấm ai đó 'dọn cho gọn' bằng cách gõ số vào điều khoản.

    ⚠️ Đọc **AST**, không quét văn bản — chú thích trong tệp có nêu số làm ví dụ
       (`21.335 ký tự`, `404`), và một bánh cóc không phân biệt được mã với lời
       kể về mã sẽ cấm luôn việc ghi lại bài học.
    """
    import ast
    import pathlib

    from platform_core.llm import gia_token

    cam = {gia_token.GIA_VAO_MOI_CREDIT_1M,
           gia_token.GIA_VAO_CACHE_CREDIT_1M,
           gia_token.GIA_RA_CREDIT_1M}
    cay = ast.parse(pathlib.Path(dk.__file__).read_text(encoding="utf-8"))
    xau = [n.lineno for n in ast.walk(cay)
           if isinstance(n, ast.Constant) and isinstance(n.value, int)
           and n.value in cam]
    assert not xau, (
        f"so gia bi go tay o dong {xau}. Doi gia trong gia_token.py thi dieu "
        f"khoan phai doi THEO, khong phai doi CUNG LUC o hai cho")


def test_gioi_han_model_DOC_tu_ban_khai_khong_import_app():
    """Mỗi alias phải nói giới hạn của **chính nó**, và phải đọc từ registry.

    🔴 Đây đúng lớp lỗi P08 F-02: trước 01/09 `ltt_llm_vision` được quảng cáo
       "same 89K usable input context" trong khi trần thật là 65.536 — một con
       số dùng cho hai model là một con số sai cho ít nhất một trong hai.

    ⛔ VÀ BẢN ĐẦU CỦA PHÉP KIỂM NÀY `import apps.ltt_llm` ĐỂ ĐỐI CHIẾU — tức nó
       chấp nhận một mô-đun `platform_core` cũng làm thế. Hai chốt phân tầng bắt
       được (`test_147`, `test_60`). Nay đối chiếu với **registry**, đúng đường
       mà chính nền tảng phải đi.
    """
    from platform_core.registry import discover

    khai = {}
    for it in discover():
        for tool in it.manifest.tools:
            for alias, spec in ((getattr(tool, "api_contract", None) or {})
                                .get("models") or {}).items():
                rb = (spec or {}).get("constraints") or {}
                if rb.get("context_window"):
                    khai[alias] = int(rb["context_window"])

    gh = dk.gioi_han_model()
    assert set(gh) == set(khai), "dieu khoan lech voi ban khai cua app"
    for alias, cong_bo in khai.items():
        assert gh[alias]["cong_bo"] == cong_bo


def test_moi_alias_cong_bo_con_so_cua_CHINH_NO():
    """Đối chứng cho phép kiểm trên — và nó đo **nguồn**, không đo **sự khác nhau**.

    🔴 BẢN CŨ ĐÒI HAI CON SỐ PHẢI KHÁC NHAU, và đó là một phép đo **lệch chiều**.

       Nó ra đời để bắt F-02 (alias vision quảng cáo con số của alias text), và
       lúc ấy hai model tình cờ có cửa sổ khác nhau, nên "khác nhau" trông như
       một phép đo tốt. Từ D02 (11/09/2026) hai model công khai chạy **cùng một
       ngữ cảnh engine** — nên phép kiểm cũ đỏ vì bản khai ĐÚNG, và cách duy
       nhất làm nó xanh lại là nói dối khách về một trong hai con số.

    ⭐ Thứ F-02 thật sự là: *một alias nói con số của model KHÁC*. Mệnh đề ấy
       viết được mà không cần hai số khác nhau — hỏi thẳng `ngan_sach` theo
       **id nội bộ của chính alias đó**. Bằng nhau hay không thành chuyện của
       phần cứng, không còn là điều kiện để phép kiểm có nghĩa.
    """
    from apps.ltt_llm import ngan_sach
    from platform_core.llm.canonical import ALIAS_SANG_ID

    gh = dk.gioi_han_model()
    assert gh, "khong alias nao cong bo gioi han — phep kiem nay khong do gi ca"
    for alias, v in gh.items():
        noi_bo = ALIAS_SANG_ID.get(alias)
        if noi_bo is None:          # alias của app khác, không thuộc model nhà
            continue
        assert v["cong_bo"] == ngan_sach.cong_bo_cua(noi_bo), (
            f"{alias} cong bo {v['cong_bo']} nhung cua so that cua {noi_bo} "
            f"cho {ngan_sach.cong_bo_cua(noi_bo)}")


def test_dong_thoi_DOC_tu_admission_slots_cua_ban_khai():
    """Chỉ nói con số nào **thật sự được cưỡng chế**.

    `admission_slots = 0` nghĩa là tool không khai giới hạn — đưa nó vào điều
    khoản là hứa một thứ không ai giữ.
    """
    from platform_core.registry import discover

    khai = {}
    for it in discover():
        for tool in it.manifest.tools:
            suat = int(getattr(tool, "admission_slots", 0) or 0)
            if suat > 0 and ((getattr(tool, "api_contract", None) or {})
                             .get("models")):
                khai[tool.name] = suat
    assert dk.dong_thoi() == khai
    assert all(v > 0 for v in dk.dong_thoi().values())


def test_dieu_khoan_KHONG_import_app_nao():
    """⛔ BẤT BIẾN PHÂN TẦNG, chốt ngay tại tệp thay vì chỉ ở `test_147`.

    Nền tảng biết tên một app cụ thể nghĩa là **gỡ app đó ra sẽ làm nền tảng
    vỡ**, chứ không phải chỉ mất một app. Kho này đã gỡ `socialbot`, `demo`,
    `kichban`, `mediatools` — đường ấy còn dùng nữa.
    """
    import ast
    import pathlib

    cay = ast.parse(pathlib.Path(dk.__file__).read_text(encoding="utf-8"))
    xau = []
    for n in ast.walk(cay):
        if isinstance(n, ast.ImportFrom) and (n.module or "").startswith("apps"):
            xau.append(n.lineno)
        if isinstance(n, ast.Import):
            xau += [n.lineno for a in n.names if a.name.startswith("apps")]
    assert not xau, f"import `apps` o dong {xau} — registry la duong duy nhat"


def test_du_lieu_luu_tru_DOC_tu_governance_khong_chep():
    """`governance.py` tự viết: *a second copy of a legal promise is a second
    promise, and the two will differ*. Nên điều khoản **đọc** nó."""
    from platform_core.public_api import governance

    ds = dk.du_lieu_luu_gi()
    assert len(ds) == len(governance.STORES), "so bang lech => co ban chep"
    assert {d["bang"] for d in ds} == {s.table for s in governance.STORES}


# ── 2. Mỗi lời hứa phải có phép đo đứng sau ─────────────────────────────────

@pytest.mark.parametrize("muc", dk.MUC_DA_DO, ids=lambda m: m["khoa"])
def test_moi_muc_da_do_deu_NEU_phep_do_sinh_ra_no(muc):
    """Một điều khoản không nói được nó dựa trên đâu là một điều khoản không
    kiểm chứng được — và nó sẽ sống sót rất lâu sau khi hệ thống đổi."""
    assert muc["do_bang"].strip(), f"{muc['khoa']}: khong noi duoc do bang gi"
    assert muc["tieu_de"] and muc["noi_dung"]


def test_khoa_cua_cac_muc_la_duy_nhat():
    khoa = [m["khoa"] for m in dk.MUC_DA_DO]
    assert len(khoa) == len(set(khoa))


# ── 3. 🔴 Không được bịa lời hứa ────────────────────────────────────────────

def test_KHONG_rang_buoc_khach_khi_con_muc_chua_quyet():
    """⛔ PHÉP KIỂM QUAN TRỌNG NHẤT TỆP NÀY.

    `san_sang()` là thứ giữ cho ô tích "tôi đồng ý" không xuất hiện trước khi
    có gì thật để đồng ý. Giới hạn trách nhiệm, SLA, hoàn tiền credit chưa
    dùng, chấm dứt tài khoản — **không cái nào có trong mã**, nên không đo được,
    nên không được viết ra.

    ⭐ Một điều khoản do máy đoán ra, đặt trước một ô tích mà khách bấm, là một
       lời hứa không ai từng đưa ra.

    🔴 BẢN ĐẦU CỦA PHÉP KIỂM NÀY LÀ MỘT TAUTOLOGY, và đột biến bắt được:

           assert dk.san_sang() is (len(dk.CAN_CHU_SAN_PHAM_QUYET) == 0)

       `san_sang()` được **định nghĩa** bằng đúng vế phải, nên câu đó đúng ở mọi
       trạng thái — kể cả khi ai đó xoá sạch danh sách chưa-quyết. Tôi viết nó
       ngay dưới dòng chữ "phép kiểm quan trọng nhất tệp này", trong chính phiên
       đi dọn những bằng chứng-không-thể-sai. Nó chỉ lộ ra vì phép đột biến hỏi
       "phép kiểm này có ĐỎ được không", chứ không hỏi "nó có xanh không".

    ⇒ Nay chốt hai thứ **có thể sai**: sáu câu hỏi pháp lý phải còn nguyên (đừng
      ai lặng lẽ bỏ bớt một câu), và trạng thái hôm nay là **chưa ràng buộc**.
      Răng thật nằm ở phía tiêu thụ — mọi chỗ vẽ ô tích phải gọi `san_sang()` —
      và nó được chốt ở `test_can_dieu_khoan` phía dưới.
    """
    phai_co = {"credit_het_han", "hoan_tien_chua_dung", "sla",
               "gioi_han_trach_nhiem", "cham_dut", "noi_dung_cam"}
    dang_co = {m["khoa"] for m in dk.CAN_CHU_SAN_PHAM_QUYET}
    thieu = phai_co - dang_co
    assert not thieu, (
        f"cau hoi phap ly bien mat ma khong ai tra loi: {sorted(thieu)}")
    assert dk.san_sang() is False, (
        "dieu khoan tu khai da du de RANG BUOC khach. Neu that su da co van ban "
        "do chu san pham duyet thi cap nhat phep kiem nay CUNG LUC voi van ban, "
        "va noi ro ai duyet")


@pytest.mark.parametrize("muc", dk.CAN_CHU_SAN_PHAM_QUYET, ids=lambda m: m["khoa"])
def test_moi_muc_chua_quyet_deu_NOI_RO_hien_trang(muc):
    """Nêu câu hỏi mà không nêu hiện trạng thì người quyết phải đi tra lại từ
    đầu — và phần lớn sẽ không tra."""
    assert muc["cau_hoi"] and muc["hien_trang"]


def test_phien_ban_co_dinh_dang_truy_duoc():
    """Bản ghi đồng ý lưu nhãn này. Nhãn tái sử dụng ⇒ câu hỏi 'họ đã đồng ý với
    cái gì' không còn trả lời được — cùng luật với `PHIEN_BAN_GIA`."""
    assert dk.PHIEN_BAN.startswith("api-")
    assert len(dk.PHIEN_BAN) >= len("api-2026-09-01")


def test_can_dieu_khoan_NEM_khi_chua_du():
    """Răng thật: chỗ nào sắp lấy chữ ký của khách phải gọi hàm này, và nó NÉM.

    ⭐ Khác `san_sang()` ở đúng điểm khiến bản đầu thành tautology: một giá trị
       không ai đọc thì không chặn được gì, còn một ngoại lệ thì hiện ra ngay
       trên đường thi hành. Và phép kiểm cho nó **đỏ được thật** — bỏ danh sách
       chưa-quyết đi là nó thôi ném.
    """
    with pytest.raises(dk.ChuaDuDeRangBuoc) as e:
        dk.can_dieu_khoan_san_sang()
    # Thông điệp phải NÊU TÊN thứ còn thiếu, không chỉ nói "chưa đủ": người đọc
    # nó đang đứng trước một ô tích không hiện ra và cần biết vì sao.
    for khoa in ("sla", "gioi_han_trach_nhiem", "cham_dut"):
        assert khoa in str(e.value), f"thong diep khong neu {khoa}"
