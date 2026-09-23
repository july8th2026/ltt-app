"""Hệ kiểu cổng và luật nối dây — MỘT nguồn luật cho cả client lẫn server.

Nguồn thiết kế: `docs/architecture/workflow_v2_audit/25_26 §7`
(`WF-701`/`G37` kiểu · `WF-702`/`G38` cardinality · `G39` một nguồn luật).

🔴 **Khiếm khuyết đang có, đo được:** 13 kiểu tham số gộp còn **9** kiểu cổng, và
   `int` · `number` · `bool` · `dict` **đều thành `json`**. Hệ quả: validator
   không phân biệt được cổng số với cổng object — nối một cổng trả số vào một
   cổng nhận object là **hợp lệ** với nó.

🔴 **`M9`** đòi luật nối dây của client và server trùng khớp **100 %**. Cách đạt
   được không phải "viết cẩn thận hai lần" mà là **một nguồn luật**:
   `xuat_luat_noi_day()` xuất ra dữ liệu, client dựng `connectionAllowed()` từ
   đó. Hai bản cài đặt song song thì lệch — chỉ là chưa ai đo.
"""
from __future__ import annotations

from dataclasses import dataclass, field

#: 15 kiểu. Bốn nhóm, và ranh giới giữa `number`/`integer`/`json` là toàn bộ
#: điểm của `G37`: gộp chúng lại là mất khả năng bắt một lỗi nối dây thật.
KIEU_CO_BAN = frozenset({
    # Nguyên thuỷ
    "text", "number", "integer", "boolean", "json", "file",
    # Media
    "image", "video", "audio", "document",
    # Tham chiếu — giá trị THẬT không bao giờ vào `WorkflowVersion` (`WF-902`)
    "model_ref", "connection_ref", "artifact_ref", "workflow_ref", "secret_ref",
    # ⭐ Spec §4.7. `any` chỉ dành cho node `core.*` dữ liệu (set/transform/
    #    aggregate): chúng đi qua giá trị mà KHÔNG diễn giải nó, nên bắt chúng
    #    khai một kiểu là bắt khai một điều không đúng. `event` là cổng ra của
    #    trigger — một biến cố, không phải dữ liệu người dùng nối vào ô nhập.
    "any", "event",
})

_HAU_TO = "[]"


def la_tap_hop(kieu: str) -> bool:
    return kieu.endswith(_HAU_TO)


def kieu_phan_tu(kieu: str) -> str:
    """`image[]` → `image`. Không phải tập hợp thì trả chính nó."""
    return kieu[:-len(_HAU_TO)] if la_tap_hop(kieu) else kieu


def hop_le(kieu: str) -> bool:
    """Chuỗi kiểu này có nằm trong hệ không?

    ⛔ `image[][]` bị từ chối: khai chỉ có **một** tầng tập hợp. Cho phép lồng
       nhau là mở một nhánh mà không ai định nghĩa ngữ nghĩa — và một kiểu
       không có ngữ nghĩa vẫn sẽ được ai đó dùng.
    """
    if not kieu:
        return False
    return kieu_phan_tu(kieu) in KIEU_CO_BAN


def ep_duoc(tu: str, den: str) -> bool:
    """Ép kiểu — **ĐÚNG MỘT luật**: `T → T[]` (bọc).

    ⛔ Mọi ép kiểu khác **từ chối**, kể cả những hướng trông "an toàn" như
       `integer → number`. Lý do không phải là an toàn kiểu mà là **nhìn thấy
       được**: một phép biến đổi ngầm không hiện trên đồ thị, nhưng nó vẫn đổi
       dữ liệu. Bắt nó thành một node chuyển đổi làm thứ đang xảy ra hiện ra.
    """
    if not (hop_le(tu) and hop_le(den)):
        return False
    if tu == den:
        return True
    # ⭐ `any` là CỬA MỞ, không phải CẦU. Nó cho một node lõi dữ liệu nhận/nhả
    #    bất cứ gì, nhưng KHÔNG làm `image -> video` hợp lệ: hai cổng thật vẫn
    #    phải trùng kiểu. Nếu `any` là cầu thì mọi phép kiểm kiểu trong đồ thị
    #    biến mất ngay khi có một node lõi nằm giữa.
    if "any" in (kieu_phan_tu(tu), kieu_phan_tu(den)) or "any" in (tu, den):
        return True
    return (not la_tap_hop(tu)) and la_tap_hop(den) and kieu_phan_tu(den) == tu


# ── Cổng ──────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Cong:
    """Một cổng của node.

    ⭐ `multiple` và kiểu tập hợp là **hai chuyện khác nhau**, và *"hôm nay hai
       thứ này không phân biệt được"* (`25_26 §7`):

         Cong(type="image",   multiple=True)   nhan BA CANH, moi canh mot anh
         Cong(type="image[]", multiple=False)  nhan MOT CANH mang mot mang ba anh

       Gộp chúng lại là mất khả năng nói *"node này nhận nhiều nguồn"* khác với
       *"node này nhận một danh sách"*.
    """

    type: str
    required: bool = True
    multiple: bool = False
    variadic: bool = False
    nhan: str = ""
    meta: dict = field(default_factory=dict)

    def la_tap_hop(self) -> bool:
        return la_tap_hop(self.type)

    def nhan_nhieu_canh(self) -> bool:
        return bool(self.multiple)


@dataclass(frozen=True)
class KetQuaNoi:
    duoc: bool
    ly_do: str = ""


def noi_duoc(ra: Cong, vao: Cong, *, so_canh_dang_co: int = 0) -> KetQuaNoi:
    """Cổng `ra` nối được vào cổng `vao` không?

    Hai điều kiện độc lập, và **thứ tự báo lỗi có ý nghĩa**: kiểu trước, sức
    chứa sau — người đang kéo dây cần biết *"sai kiểu"* khác *"đã đủ dây"*.
    """
    if not hop_le(ra.type):
        return KetQuaNoi(False, f"kieu khong hop le o cong ra: {ra.type!r}")
    if not hop_le(vao.type):
        return KetQuaNoi(False, f"kieu khong hop le o cong vao: {vao.type!r}")
    if not ep_duoc(ra.type, vao.type):
        return KetQuaNoi(
            False, f"khong ep duoc {ra.type} -> {vao.type}; chi co T -> T[]")
    if not vao.multiple and so_canh_dang_co >= 1:
        return KetQuaNoi(
            False,
            f"cong vao {vao.type} khong khai `multiple` nen chi nhan MOT canh "
            f"(dang co {so_canh_dang_co})")
    return KetQuaNoi(True)


# ── 🔴 MỘT nguồn luật (`G39`, `M9`) ──────────────────────────────────────────

def xuat_luat_noi_day() -> dict:
    """Xuất toàn bộ luật nối dây ra **dữ liệu** để client dựng lại.

    ⭐ Đây là chỗ `M9` được giải. Client **không** cài đặt lại luật; nó đọc
       `cap_noi_duoc` và tra bảng. Hai bản cài đặt song song thì lệch — câu hỏi
       duy nhất là bao lâu và ở đâu.

    ⚠️ Bảng liệt kê **tường minh** thay vì mô tả luật, có chủ ý: một mô tả
       (*"T sang T ngoặc vuông"*) vẫn cần client **diễn giải**, và diễn giải là
       chỗ hai bên lệch nhau. Một bảng cặp thì không diễn giải được sai.
    """
    moi_kieu = sorted(KIEU_CO_BAN) + [f"{k}{_HAU_TO}" for k in sorted(KIEU_CO_BAN)]
    cap = [[a, b] for a in moi_kieu for b in moi_kieu if ep_duoc(a, b)]
    return {
        "phien_ban": 2,
        "kieu": sorted(KIEU_CO_BAN),
        "hau_to_tap_hop": _HAU_TO,
        "ep_kieu": [["T", "T[]"]],
        "cap_noi_duoc": cap,
        "ghi_chu": ("Client dung connectionAllowed() TU bang nay. Dung cai dat "
                    "lai luat — hai ban song song thi lech."),
    }
