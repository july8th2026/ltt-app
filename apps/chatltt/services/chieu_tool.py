"""
chieu_tool.py — registry đã duyệt → khối `tools` gửi cho model. (H44 P03)

## Vì sao KHÔNG viết phép chiếu thứ hai

`platform_core/public_api/catalog.project_tool` đã làm đúng việc khó: bỏ id
model nội bộ (`test_212`), ẩn tham số máy chủ tự quyết (`hidden`), giữ đúng
kiểu số/chuỗi của enum. `runtime_noi_bo/danh_muc.py` mượn lại nó và ghi rõ lý
do: *"Viết một phép chiếu thứ hai cho sản phẩm web là mời hai bản hợp đồng
lệch nhau."*

Tệp này đi qua **cùng một cửa** đó rồi chỉ **đổi hình dạng** sang khuôn OpenAI
`tools`. Không đọc `ToolSpec` trực tiếp, không tự lọc tham số.

## Ba cổng, và đây là cổng THỨ TƯ

  `ToolSpec.customer_visible`                 palette Agent/Canvas
  `api_exposed` + `LTT_PUBLIC_API_TOOLS`      bán qua `/api/v1`
  `chinh_sach.CONG_CU_CHO_PHEP`               thứ ChatLTT MỜI người dùng
  **`CHO_MODEL_GOI` (tệp này)**               thứ MODEL được phép tự gọi

⛔ Cổng thứ tư hẹp hơn cổng thứ ba, và đó là điểm chính. Người dùng **bấm nút**
tạo ảnh là một chuyện; **model tự quyết** tiêu 3–12 credit của họ là chuyện
khác. Một tool có thể ở cổng ba mà không ở cổng bốn.

⭐ Fail-closed: tên không có trong `CHO_MODEL_GOI` thì không được chiếu, kể cả
   khi `chinh_sach` đã mời nó.
"""
from __future__ import annotations

from typing import Optional

from apps.chatltt.services import chinh_sach

#: Lớp chính sách (`02_HOP_DONG.md` §3). Hai lớp cuối rỗng mà vẫn phải có: ngày
#: đầu tiên có một tool ghi ra ngoài, chỗ để nó rơi vào phải ĐÃ fail-closed sẵn.
READ_ONLY = "READ_ONLY"
FREE = "FREE"
PAID = "PAID"
EXTERNAL_WRITE = "EXTERNAL_WRITE"
DESTRUCTIVE = "DESTRUCTIVE"

CAN_DUYET = frozenset({PAID, EXTERNAL_WRITE, DESTRUCTIVE})

#: Tên năng lực → lớp chính sách. **Khai tay, không suy từ tên tool.**
#:
#: ⛔ Cùng lý do `luot.doc_anh_duoc()` đọc `constraints.reads_images` chứ không
#:    tìm chữ "vision" trong tên: tên là quy ước đặt tên, hợp đồng là lời hứa.
#:    Ngày ai đó thêm `image.xoa_het` mà phép suy theo tên xếp nó vào `PAID` vì
#:    có chữ "image", ta mất cổng duyệt cho một thao tác phá huỷ.
LOP_CUA: dict = {
    "image.ltt": PAID,
    "speech.ltt": PAID,
    # Tool NỘI BỘ của ChatLTT (`tool_noi_bo.py`) — không tốn credit, không gọi
    # máy B, không ghi gì. Lớp khai **ở đây** chứ không import từ tệp kia: nơi
    # khai chính sách phải là nơi đọc chính sách, để một tool mới không thể tự
    # nâng lớp cho mình bằng cách khai trong tệp của chính nó.
    "noi_bo.thoi_gian": READ_ONLY,
    "noi_bo.tinh": READ_ONLY,
    # ⚠️ Thêm 06/09 (P06 bước 6). READ_ONLY vì **trích đã thu tiền một lần**
    #    (`chatltt.trich_tep`); tìm trong đoạn đã trích là một truy vấn CSDL
    #    trên dữ liệu của chính người hỏi. Bắt duyệt lần nữa là tính tiền hai
    #    lần cho một việc.
    #
    # 🔴 Quên dòng này thì `lop_chinh_sach()` trả **DESTRUCTIVE** — mặc định
    #    chặt nhất, fail-closed đúng thiết kế. Tôi đã quên nó thật, và bánh cóc
    #    `test_808::test_lop_khai_o_chieu_tool_khop_voi_tool_noi_bo` bắt được.
    "noi_bo.tim_tai_lieu": READ_ONLY,
    # ⚠️ Thêm 06/09 (B4 bước 5). **`FREE`, không `READ_ONLY`** — nó GHI. Lớp
    #    này khai bằng tay ở đây chứ không import từ `tool_noi_bo`: nơi khai
    #    chính sách phải là nơi đọc chính sách, để một tool mới không tự nâng
    #    lớp cho mình bằng cách khai trong tệp của chính nó.
    #
    # 🔴 Và nó **không** có trong `CHO_MODEL_GOI` dưới đây. `FREE` nghĩa là
    #    *"không cần phiếu duyệt"*, và điều đó chỉ chấp nhận được vì người dùng
    #    **sửa lại được** — mà "sửa lại được" đòi họ **nhìn thấy** nó đã xảy ra.
    #    Khối `tool_call` hiện chưa được vẽ (P09). Mở cửa bốn trước P09 là biến
    #    một hành động ghi thành một hành động vô hình.
    "noi_bo.ghi_nho": FREE,
}

#: Năng lực MODEL được phép tự gọi. Hẹp hơn `chinh_sach.CONG_CU_CHO_PHEP`.
#:
#: ✅ **P05 mở `image.ltt` và `speech.ltt`.** Điều kiện để mở đã đủ từ P04:
#:    phiếu duyệt bền, báo giá trước khi hỏi, chạy tiếp sau khi bấm, và job nền.
#:
#: 🔴 Hai tên này thuộc lớp `PAID` (`LOP_CUA`), nên mặt định chúng **không
#:    chạy thẳng**: `thi_hanh` bước 3 chặn, và `bo_chay_tool` mở một phiếu
#:    duyệt. Cổng thứ tư (tệp này) nói *"model được phép ĐỀ NGHỊ"*, không nói
#:    *"model được phép TIÊU TIỀN"*. Hai câu khác nhau, và cái thứ hai cần
#:    `LTT_CHATLTT_V3_PAID_TOOLS` — một cờ **riêng**, mặc định tắt.
#:
#: ⛔ `image.edit` KHÔNG có ở đây vì nó **không tồn tại**: không `manifest.py`
#:    nào khai nó (đo 05/09, `05_E2_ANH_TIENG_THANH_TOOL.md` §1). Mời một tool
#:    nền tảng không làm được là bảo đảm model sẽ gọi nó — P01 đo 98,8 % chọn
#:    đúng tool **trong số được mời**.
#: ⚠️ `noi_bo.tim_tai_lieu` thêm 06/09 — **bước 6 và là bước CUỐI** của P06.
#:    Năm bước trước không mở một cửa nào; đây là dòng duy nhất đổi hành vi
#:    người dùng thấy, và nó đứng sau cùng đúng theo §4 của kế hoạch.
#:
#: ⭐ Nó READ_ONLY nên **không** cần vào `chinh_sach.CONG_CU_CHO_PHEP`: cổng ba
#:    là thứ ChatLTT **mời người dùng bấm**, cổng bốn là thứ **model tự gọi**.
#:    Tìm trong tài liệu của chính mình không phải một nút để bấm — cùng chỗ
#:    đứng với `noi_bo.tinh`.
CHO_MODEL_GOI: tuple = ("noi_bo.thoi_gian", "noi_bo.tinh",
                        "noi_bo.tim_tai_lieu",
                        "image.ltt", "speech.ltt")


class KhongChoModelGoi(PermissionError):
    """Năng lực không nằm trong cổng thứ tư."""


def lop_chinh_sach(ten: str) -> str:
    """Lớp của một năng lực. Không khai ⇒ **`DESTRUCTIVE`**, không phải `FREE`.

    🔴 Mặc định phải là lớp NGẶT NHẤT. Một tool mới quên khai lớp thì hậu quả
       đúng là *"nó đòi duyệt trong khi lẽ ra không cần"* — phiền, và sửa trong
       một dòng. Mặc định lỏng thì hậu quả là *"nó tiêu tiền của khách mà không
       hỏi"* — và cái đó không sửa lại được sau khi đã xảy ra.
    """
    return LOP_CUA.get(str(ten), DESTRUCTIVE)


def can_duyet(ten: str) -> bool:
    return lop_chinh_sach(ten) in CAN_DUYET


def cho_model_goi() -> frozenset:
    return frozenset(CHO_MODEL_GOI)


def kiem_cho_model_goi(ten: str) -> str:
    """Trả lại `ten` nếu model được phép gọi; ném nếu không. Không có nhánh gần đúng.

    ⛔ Đây là chỗ chặn model bịa tên tool. P01 đo 0/266 lượt bịa, nhưng con số đó
       là **chất lượng**, không phải **rào**: rào phải đứng vững cả khi model tệ đi.
    """
    if str(ten) not in cho_model_goi():
        raise KhongChoModelGoi(f"model khong duoc tu goi {ten!r}")
    return str(ten)


def _mot_tool(nang_luc) -> Optional[dict]:
    """Một `NangLuc` (đã qua `catalog.project_tool`) → một mục `tools` OpenAI."""
    hd = dict(getattr(nang_luc, "hop_dong", None) or {})
    schema = hd.get("input_schema") or {}
    if not isinstance(schema, dict) or schema.get("type") != "object":
        # Fail-closed: hợp đồng không nói được đầu vào thì không mời model dùng.
        return None
    ten = str(nang_luc.ten)
    mo_ta = str(getattr(nang_luc, "nhan", "") or hd.get("description") or "").strip()
    if not mo_ta:
        # ⛔ Model chọn tool bằng MÔ TẢ. Một tool không mô tả là một tool sẽ bị
        #    chọn sai — P01 nhóm N3 cho thấy model đọc mô tả rất sát.
        return None
    return {"type": "function",
            "function": {"name": ten, "description": mo_ta,
                         "parameters": schema}}


def chieu(db, *, user_id: str, apps: Optional[list] = None) -> list:
    """Khối `tools` cho một người dùng. Rỗng ⇒ **đừng gửi khoá `tools`**.

    ⭐ Rỗng khác `[]`: gửi `tools: []` là nói với model *"bạn có 0 tool"*, còn
       không gửi khoá là nói *"lượt này không có tool"*. Hai câu khác nhau với
       văn phạm GBNF của llama.cpp (`01_M1_NATIVE_HAY_GENERIC.md` §5b): có khoá
       `tools` là **bật** cưỡng chế sinh. Bên gọi kiểm rỗng rồi mới đính vào.
    """
    # Nhập TRONG hàm, có chủ ý: `tool_noi_bo` → `thi_hanh` → tệp này, nên nhập ở
    # đầu tệp là một vòng. Nhập tại chỗ cắt vòng mà không cần một sổ đăng ký
    # toàn cục — thứ mà thứ tự import quyết định, và thứ tự import là đúng cái
    # đã làm test xanh khi chạy riêng và đỏ trong gate.
    from apps.chatltt.services import tool_noi_bo

    ra = [t for t in tool_noi_bo.khoi_cho(user_id)
          if t["function"]["name"] in cho_model_goi()]
    for n in chinh_sach.danh_muc(db, user_id=user_id, apps=apps):
        if n.ten not in cho_model_goi():
            continue
        if getattr(n, "san_sang", "san_sang") != "san_sang":
            # Năng lực đang bận/chưa sẵn sàng thì đừng mời model gọi — nó sẽ gọi,
            # rồi ta phải giải thích một lỗi lẽ ra không cần tồn tại.
            continue
        muc = _mot_tool(n)
        if muc is not None:
            ra.append(muc)
    return ra


def lop_theo_ten(khoi_tools: list) -> dict:
    """`{tên: lớp}` cho một khối đã chiếu — để thi hành khỏi tra lại."""
    return {t["function"]["name"]: lop_chinh_sach(t["function"]["name"])
            for t in (khoi_tools or [])}


__all__ = ["chieu", "cho_model_goi", "kiem_cho_model_goi", "lop_chinh_sach",
           "can_duyet", "lop_theo_ten", "KhongChoModelGoi",
           "READ_ONLY", "FREE", "PAID", "EXTERNAL_WRITE", "DESTRUCTIVE"]
