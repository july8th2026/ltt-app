"""
thi_hanh.py — chạy MỘT lời gọi tool và trả kết quả có cấu trúc. (H44 P03)

    validate ten  ->  validate doi so  ->  chinh sach  ->  chay  ->  KetQua

## ⛔ LỖI LÀ KẾT QUẢ, KHÔNG PHẢI NGOẠI LỆ

Mọi đường ra của tệp này đều là một `KetQua`. Không ném lên vòng lặp điều phối.

Lý do không phải phong cách: `02_HOP_DONG.md` §1 có hai chuyển đổi
`… -> TOOL_RESULT_READY` cho **đúng** các ca hỏng — đối số sai schema, tool bị
từ chối, handler ném. Model **sửa và gọi lại** là hành vi đúng, và P01 đã đo
model làm được điều đó (nhóm N8: xử lý *"LỖI: chia cho không"*, *"TỪ CHỐI: vi
phạm chính sách"* đều đúng cách).

⇒ Giết một run vì model gõ hụt một dấu ngoặc là đổi **một lỗi sửa được** thành
  **một lượt hỏng**, và khách vẫn trả tiền cho các vòng đã chạy.

## Cắt bớt phải THẤY ĐƯỢC

`CLAUDE.md` bất biến: *"không cắt xén âm thầm"*. Một kết quả tìm kiếm 200 KB
nhét nguyên vào ngữ cảnh sẽ đẩy hội thoại chạm trần — nhưng cắt lặng lẽ thì
model **kết luận trên dữ liệu thiếu mà tưởng là đủ**. Nên cắt xong phải nói ra,
trong chính chuỗi model đọc.

## P03 chỉ chạy tool MIỄN PHÍ

Gói prompt: *"Implement P02 with fake/free tools only."* Tool có phí đi qua
`runtime_noi_bo.job` và cần duyệt bền — đó là P04/P05. Ở đây, chạm vào lớp
`PAID` trở lên thì trả `KetQua` báo **cần duyệt**, không chạy gì.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from apps.chatltt.services import chieu_tool

#: Trần ký tự của một kết quả tool khi đưa **trở lại model**.
#:
#: 8.000 ký tự ≈ 3.000 token. Tám vòng × 3.000 = 24K token chỉ riêng kết quả tool,
#: trên một cửa sổ ChatLTT dùng thật ~80K. Nới số này là đổi chỗ cho hội thoại
#: lấy chỗ cho một kết quả mà model hiếm khi cần trọn.
TRAN_KY_TU_KET_QUA = 8_000

#: Mã lỗi. Chuỗi ổn định — giao diện và test bám vào chúng, không bám vào câu chữ.
LOI_TEN_LA = "ten_la"
LOI_DOI_SO = "doi_so"
LOI_CAN_DUYET = "can_duyet"
LOI_HANDLER = "handler_nem"
LOI_CHUA_CAI = "chua_cai"


@dataclass
class KetQua:
    """Một lần thi hành. `ok=False` **vẫn là** một kết quả để trả về model."""

    ok: bool
    noi_dung: Any = None
    ma_loi: str = ""
    thong_diep: str = ""
    da_cat: bool = False
    #: Lớp chính sách đã suy ra — điều phối ghi vào `chatltt_step`.
    lop: str = ""

    def cho_model(self) -> str:
        """Chuỗi đưa **trở lại model**. Đây là thứ model đọc, nên nó phải tự đủ nghĩa."""
        if not self.ok:
            # ⭐ Nói RÕ đây là lỗi của lời gọi, kèm mã — model dùng mã để quyết
            #    định sửa hay bỏ, thay vì đoán từ câu chữ tiếng Việt.
            return f"LOI[{self.ma_loi}]: {self.thong_diep}"
        chu = _thanh_chuoi(self.noi_dung)
        if len(chu) > TRAN_KY_TU_KET_QUA:
            chu = chu[:TRAN_KY_TU_KET_QUA]
            # ⛔ Nói ra việc cắt, TRONG chuỗi model đọc. Cắt lặng lẽ thì model
            #    kết luận trên dữ liệu thiếu mà tưởng là đủ.
            chu += (f"\n\n[DA CAT: ket qua dai hon {TRAN_KY_TU_KET_QUA} ky tu. "
                    f"Phan tren la phan dau. Neu can phan sau, hay thu hep yeu cau.]")
        return chu

    def tom_tat(self, gioi_han: int = 160) -> str:
        """Cho sự kiện `tool.result` — SSE chỉ mang tóm tắt (`02_HOP_DONG.md` §5)."""
        t = self.cho_model().replace("\n", " ")
        return t if len(t) <= gioi_han else t[:gioi_han] + "…"


def _thanh_chuoi(gt: Any) -> str:
    if isinstance(gt, str):
        return gt
    try:
        return json.dumps(gt, ensure_ascii=False, indent=None)
    except (TypeError, ValueError):
        return str(gt)


# ── Sổ handler nội bộ. P03: chỉ tool MIỄN PHÍ, tất định. ───────────────────

_SO_HANDLER: dict = {}


def dang_ky(ten: str) -> Callable:
    """Trang trí một handler nội bộ. Chữ ký: `(db, user_id, doi_so) -> Any`."""
    def bao(f):
        _SO_HANDLER[str(ten)] = f
        return f
    return bao


def da_cai(ten: str) -> bool:
    return str(ten) in _SO_HANDLER


# ── Cửa duy nhất ───────────────────────────────────────────────────────────

def thi_hanh(db, *, user_id: str, ten: str, doi_so: dict,
             schema: Optional[dict] = None,
             cho_chay_co_phi: bool = False) -> KetQua:
    """Chạy một lời gọi tool. **Luôn** trả `KetQua`, không bao giờ ném.

    `schema` là `parameters` của chính mục `tools` đã chiếu cho model — không
    phải `ToolSpec` thô. Model được cho cái gì thì bị kiểm theo cái đó; kiểm
    theo một hợp đồng khác với hợp đồng đã đưa là bắt lỗi model vì lỗi của ta.
    """
    ten = str(ten or "")
    lop = chieu_tool.lop_chinh_sach(ten)

    # 1. Tên — cổng thứ tư. Rào này phải đứng cả khi model tệ đi.
    try:
        chieu_tool.kiem_cho_model_goi(ten)
    except chieu_tool.KhongChoModelGoi:
        return KetQua(False, ma_loi=LOI_TEN_LA, lop=lop,
                      thong_diep=(f"khong co tool ten {ten!r}. Hay dung mot trong "
                                  f"cac tool da duoc cung cap."))

    # 2. Đối số — theo đúng schema đã đưa cho model.
    thieu = _kiem_schema(doi_so, schema)
    if thieu:
        return KetQua(False, ma_loi=LOI_DOI_SO, lop=lop, thong_diep=thieu)

    # 3. Chính sách. P03 chưa có duyệt bền ⇒ chạm PAID trở lên là dừng ở đây.
    if chieu_tool.can_duyet(ten) and not cho_chay_co_phi:
        return KetQua(False, ma_loi=LOI_CAN_DUYET, lop=lop,
                      thong_diep=(f"tool {ten!r} thuoc lop {lop} — can nguoi dung "
                                  f"duyet truoc khi chay."))

    # 4. Chạy.
    ham = _SO_HANDLER.get(ten)
    if ham is None:
        return KetQua(False, ma_loi=LOI_CHUA_CAI, lop=lop,
                      thong_diep=f"tool {ten!r} chua co handler noi bo.")
    try:
        return KetQua(True, noi_dung=ham(db, user_id, dict(doi_so or {})), lop=lop)
    except Exception as e:                                      # noqa: BLE001
        # ⛔ Bắt rộng CÓ CHỦ Ý. Một handler ném là dữ liệu để model đọc, không
        #    phải sự cố để cả run chết. Nhưng KHÔNG nuốt: kiểu ngoại lệ đi vào
        #    thông điệp, và điều phối ghi nó vào `chatltt_step.ket_qua`.
        return KetQua(False, ma_loi=LOI_HANDLER, lop=lop,
                      thong_diep=f"{type(e).__name__}: {e}"[:400])


def _kiem_schema(doi_so: dict, schema: Optional[dict]) -> str:
    """`""` nếu hợp lệ, ngược lại một câu **model đọc được để sửa**."""
    if not schema:
        return ""
    if not isinstance(doi_so, dict):
        return "doi so phai la mot object JSON."
    thuoc = (schema.get("properties") or {})
    for k in (schema.get("required") or []):
        if k not in doi_so:
            return f"thieu tham so bat buoc {k!r}."
    for k, v in doi_so.items():
        mo = thuoc.get(k)
        if mo is None:
            return (f"tham so {k!r} khong co trong hop dong. "
                    f"Cho phep: {sorted(thuoc) or '(khong co)'}.")
        if "enum" in mo and str(v) not in [str(x) for x in mo["enum"]]:
            return f"{k!r} phai la mot trong {mo['enum']}, nhan {v!r}."
        kieu = mo.get("type")
        if kieu == "integer" and not isinstance(v, int):
            return f"{k!r} phai la so nguyen, nhan {type(v).__name__}."
        if kieu == "number" and not isinstance(v, (int, float)):
            return f"{k!r} phai la so, nhan {type(v).__name__}."
        if kieu == "string" and not isinstance(v, str):
            return f"{k!r} phai la chuoi, nhan {type(v).__name__}."
    return ""


__all__ = ["KetQua", "thi_hanh", "dang_ky", "da_cai", "TRAN_KY_TU_KET_QUA",
           "LOI_TEN_LA", "LOI_DOI_SO", "LOI_CAN_DUYET", "LOI_HANDLER", "LOI_CHUA_CAI"]
