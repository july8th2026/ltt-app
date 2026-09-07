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
        # ⭐ `dict` thì cắt theo MỤC rồi mới tuần tự hoá — xem `_cat_dict`.
        if isinstance(self.noi_dung, dict):
            return _cat_dict(self.noi_dung)
        chu = _thanh_chuoi(self.noi_dung)
        if len(chu) > TRAN_KY_TU_KET_QUA:
            chu = chu[:TRAN_KY_TU_KET_QUA]
            # ⛔ Nói ra việc cắt, TRONG chuỗi model đọc. Cắt lặng lẽ thì model
            #    kết luận trên dữ liệu thiếu mà tưởng là đủ.
            #
            # ⚠️ Đường này chỉ còn cho kết quả KHÔNG phải `dict` (chuỗi trần).
            #    Ở đó không có cấu trúc nào để giữ, nên cắt theo ký tự là
            #    lựa chọn duy nhất — và một tài liệu vẫn giả mạo được câu
            #    báo cắt này. Với `dict` thì `_cat_dict` đóng cả hai lỗ.
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

#: Khoá báo cắt, nằm **trong** JSON. Một tài liệu không giả mạo được nó —
#: đo 07/09: `json.dumps` thoát mọi ngoặc kép, nên chữ trong `noi_dung`
#: không thành một trường được.
KHOA_DA_CAT = "_da_cat"


def _cat_dict(goc: dict) -> str:
    """Cắt một kết quả `dict` theo **mục**, không theo ký tự. (H44 P10)

    ## 🔴 Vì sao cắt theo ký tự là một lỗi, không phải một lựa chọn thô

    Đo 07/09 với một kết quả `noi_bo.tim_tai_lieu` cỡ thường (12 đoạn):

        json phan tich duoc : KHONG (JSONDecodeError o char 8000)
        doan co "noi_dung"  : 10
        doan co "trich_dan" : 9      <- MOT DOAN MAT NGUON

    ⛔ Đó đúng là thứ **P06 bước 5 dùng cả một bước để chặn**: *"chữ và
       nguồn nằm trong CÙNG một đối tượng… hình dạng dữ liệu, không phải
       một quy ước nhớ kèm nguồn"*. Một phép cắt theo ký tự ở tầng dưới
       tháo đúng mọi mối mà bước ấy khâu lại — và tháo **im lặng**.

    ⇒ Bỏ **cả mục**, giữ mọi mục còn lại **nguyên vẹn**. Một đoạn hoặc có
      mặt đầy đủ, hoặc không có mặt. Không có trạng thái thứ ba.

    ⭐ Và câu báo cắt vào **trong** JSON (`_da_cat`), nên kết quả vẫn phân
      tích được, và một tài liệu độc không giả mạo được nó.
    """
    chu = _thanh_chuoi(goc)
    if len(chu) <= TRAN_KY_TU_KET_QUA:
        return chu

    # Danh sách dài nhất là chỗ tốn chỗ nhất — bỏ từ CUỐI, vì bộ truy hồi
    # đã xếp giảm dần theo điểm, nên mục cuối là mục ít liên quan nhất.
    khoa = max((k for k, v in goc.items() if isinstance(v, list)),
               key=lambda k: len(goc[k]), default="")
    if not khoa:
        # Không có danh sách nào để bỏ ⇒ không cắt khéo được. Nói ra, và
        # KHÔNG cắt giữa chuỗi: trả nguyên rồi để tầng trên chịu, còn hơn
        # giao cho model một JSON hỏng.
        return _thanh_chuoi(dict(goc, **{KHOA_DA_CAT: "khong_cat_duoc"}))

    muc = list(goc[khoa])
    bo = 0
    while muc:
        muc.pop()
        bo += 1
        thu = dict(goc)
        thu[khoa] = muc
        thu[KHOA_DA_CAT] = {"da_bo": bo, "truong": khoa,
                            "ly_do": "qua dai, hay thu hep yeu cau"}
        chu = _thanh_chuoi(thu)
        if len(chu) <= TRAN_KY_TU_KET_QUA:
            return chu

    # Bỏ hết vẫn quá dài ⇒ phần **ngoài** danh sách đã quá trần. Trả về một
    # kết quả rỗng nói rõ lý do, chứ không trả một mảnh.
    return _thanh_chuoi({khoa: [],
                         KHOA_DA_CAT: {"da_bo": bo, "truong": khoa,
                                       "ly_do": "qua dai, hay thu hep yeu cau"}})


# ── Sổ handler nội bộ. P03: chỉ tool MIỄN PHÍ, tất định. ───────────────────

_SO_HANDLER: dict = {}


def dang_ky(ten: str) -> Callable:
    """Trang trí một handler nội bộ. Chữ ký: `(db, user_id, doi_so, boi_canh)`.

    ⚠️ Tham số thứ tư thêm 06/09 (H44 P06 bước 6). Nó mang thứ **người gọi**
       biết mà model không được đặt — hôm nay là `conversation_id`. Handler nào
       không cần thì đặt tên `_boi_canh` và bỏ qua; handler nào cần thì **ném**
       khi thiếu, chứ đừng lặng lẽ bỏ mất phạm vi.
    """
    def bao(f):
        _SO_HANDLER[str(ten)] = f
        return f
    return bao


def _nap_noi_bo() -> None:
    """Nạp `tool_noi_bo` để các handler tự đăng ký. Rẻ, và `import` tự nhớ.

    🔴 Không có hàm này thì sổ handler phụ thuộc **thứ tự import**: các
    handler chỉ tồn tại nếu ai đó đã nhập `tool_noi_bo` trước đó — và duy nhất
    `chieu()` làm việc đó. Mọi đường **không** đi qua `chieu()` (chạy tiếp một
    run sau khi duyệt, một job nền, một lệnh CLI) sẽ thấy `LOI_CHUA_CAI` cho một
    tool hoàn toàn bình thường.

    ⭐ Đo thật: `test_812` đỏ ba phép kiểm vì chính chuyện này. Chạy riêng từng
       tệp thì xanh hay đỏ tùy **tệp nào chạy trước** — đúng họ với
       `bay-trang-thai-ngoai-ro-vao-test`.

    ⛔ Nhập trong hàm, có chủ ý: `tool_noi_bo` nhập tệp này, nên nhập ở đầu
       tệp là một vòng.
    """
    from apps.chatltt.services import tool_noi_bo  # noqa: F401


def da_cai(ten: str) -> bool:
    _nap_noi_bo()
    return str(ten) in _SO_HANDLER


# ── Cửa duy nhất ───────────────────────────────────────────────────────────

def thi_hanh(db, *, user_id: str, ten: str, doi_so: dict,
             schema: Optional[dict] = None,
             cho_chay_co_phi: bool = False,
             boi_canh: Optional[dict] = None) -> KetQua:
    """Chạy một lời gọi tool. **Luôn** trả `KetQua`, không bao giờ ném.

    `schema` là `parameters` của chính mục `tools` đã chiếu cho model — không
    phải `ToolSpec` thô. Model được cho cái gì thì bị kiểm theo cái đó; kiểm
    theo một hợp đồng khác với hợp đồng đã đưa là bắt lỗi model vì lỗi của ta.

    ## `boi_canh` — thứ NGƯỜI GỌI biết mà model KHÔNG được đặt (H44 P06 bước 6)

    Thêm 06/09 cho `noi_bo.tim_tai_lieu`: một tool tìm trong tài liệu của **hội
    thoại hiện tại** cần biết hội thoại nào, và đó là một **ranh giới phạm vi**.

    ⛔ Lối tưởng dễ — để model tự truyền `conversation_id` trong `doi_so` — sai
       theo thiết kế: một tham số **do model kiểm soát** không thể là ranh giới
       phạm vi. Model đọc được id hội thoại khác từ chính lịch sử trò chuyện, và
       khi ấy tool trở thành đường đọc chéo hội thoại.

    ⇒ `boi_canh` do **người gọi** (`bo_chay_tool`) đặt, không đi qua schema, nên
      model không nhìn thấy lẫn không sửa được. Handler nào cần thì đọc, và
      **ném** khi thiếu — fail-closed, không im lặng tìm toàn tài khoản.
    """
    ten = str(ten or "")
    lop = chieu_tool.lop_chinh_sach(ten)
    _nap_noi_bo()

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
        return KetQua(True, lop=lop,
                      noi_dung=ham(db, user_id, dict(doi_so or {}),
                                   dict(boi_canh or {})))
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


#: Tên công khai của `_kiem_schema`. `bo_chay_tool` phải kiểm đối số **trước**
#: khi mở phiếu duyệt — hỏi người dùng có đồng ý chạy một lời gọi sai hợp đồng
#: là bắt họ đọc một thứ chắc chắn sẽ hỏng.
#:
#: ⛔ Một **tên khác cho cùng một hàm**, không phải một bản chép. Hai bản kiểm
#:    đối số là hai bản sẽ lệch, và chúng lệch ở chỗ tốn tiền.
kiem_doi_so = _kiem_schema

__all__ = ["KetQua", "thi_hanh", "dang_ky", "da_cai", "kiem_doi_so",
           "_nap_noi_bo",
           "TRAN_KY_TU_KET_QUA",
           "LOI_TEN_LA", "LOI_DOI_SO", "LOI_CAN_DUYET", "LOI_HANDLER", "LOI_CHUA_CAI"]
