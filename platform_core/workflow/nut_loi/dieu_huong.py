"""`core.if` · `core.switch` · `core.stop` — ba node RẼ ĐƯỜNG (spec §5.4).

🔴 CHÚNG KHÔNG SINH JOB, VÀ ĐÓ LÀ CẢ LÝ DO CHÚNG TỒN TẠI

`dieu_khien.py` đã ghi con số: *"hôm nay mỗi bước đều đi qua hàng đợi job, nên
một node `IF` cũng sinh một job — và **một job là một bút toán**. Rẽ nhánh tạo
một dòng trong sổ tiền, dù nó chỉ so sánh hai giá trị."*

⇒ `thi_hanh="inline"`: động cơ tự tính, không hàng đợi, không lease, không bút
  toán. `Gia.mien_phi()` nên `bao_gia._gia_node` trả 0 — đúng, không phải một
  chỗ bỏ sót.

## Biểu thức nằm TRONG node, cạnh chỉ mang TÊN NHÁNH (§5.4)

    "Node `core.if` xuất nhánh `true`/`false`; `core.switch` xuất nhánh theo tên
     khai. Cạnh CONTROL mang `condition = "<tên nhánh>"`; chỉ cạnh khớp nhánh
     được kích hoạt. (Chốt `Q1` của ADR-WF-001 … Một nơi viết biểu thức, một nơi
     hiện trên Canvas.)"

⛔ Nên tuyệt đối không thêm một `condition` là **biểu thức** trên cạnh. Hai nơi
   viết biểu thức là hai nơi để một luật rẽ nhánh sống, và Canvas chỉ vẽ được một.
"""
from __future__ import annotations

from platform_core.i18n import N_
from platform_core.workflow import he_kieu, ngon_ngu
from platform_core.workflow.chinh_sach import LoiNgonNgu
from platform_core.workflow.nut import Gia, NodeDefinition
from platform_core.workflow.nut_loi.chay import KetQua

#: Hai nhánh của `core.if`. Tên CỐ ĐỊNH — không cho khai lại, vì Canvas vẽ hai
#: cổng ra theo đúng hai chuỗi này.
NHANH_IF = ("true", "false")

#: Trạng thái mà `core.stop` được phép kết thúc run. ⛔ Danh sách ĐÓNG: một
#: chuỗi lạ ở đây là một run kết thúc ở trạng thái máy trạng thái không biết,
#: và `ket_so` sẽ quyết toán theo một nhánh không ai kiểm.
TRANG_THAI_STOP = ("SUCCEEDED", "FAILED")


def _tinh(bieu_thuc: str, moi_truong: dict):
    """Tính một biểu thức §6; lỗi của người khai ⇒ `bieu_thuc_loi` (§5.6)."""
    return ngon_ngu.tinh(str(bieu_thuc), moi_truong)


def chay_if(db, run, node: dict, *, moi_truong: dict, **_) -> KetQua:
    dk = (node.get("params") or {}).get("dieu_kien", "")
    try:
        gia_tri = _tinh(dk, moi_truong)
    except LoiNgonNgu as loi:
        return KetQua(sang="FAILED", error=f"bieu_thuc_loi: {loi}"[:2000])
    # ⚠️ Ép về bool bằng `bool()` của Python là CỐ Ý và đã cân nhắc: §6.4 cấm ép
    #    ngầm giữa chuỗi và số cho các TOÁN TỬ, không cấm một node hỏi
    #    "giá trị này có thật không". `[] `/`""`/`0` là "không" — đúng trực giác
    #    của người soạn, và là hành vi của mọi công cụ cùng hạng.
    return KetQua(nhanh=NHANH_IF[0] if bool(gia_tri) else NHANH_IF[1],
                  output={"gia_tri": bool(gia_tri)})


def chay_switch(db, run, node: dict, *, moi_truong: dict, **_) -> KetQua:
    p = node.get("params") or {}
    try:
        gia_tri = _tinh(p.get("bieu_thuc", ""), moi_truong)
    except LoiNgonNgu as loi:
        return KetQua(sang="FAILED", error=f"bieu_thuc_loi: {loi}"[:2000])
    ten = str(gia_tri)
    khai = [str(x) for x in (p.get("nhanh") or [])]
    mac_dinh = str(p.get("mac_dinh") or "")
    if ten in khai:
        return KetQua(nhanh=ten, output={"gia_tri": gia_tri})
    # ⛔ Không khớp và không có nhánh mặc định ⇒ **không nhánh nào** kích hoạt.
    #    Node vẫn SUCCEEDED (nó đã tính xong) và mọi đích SKIPPED. Đoán một
    #    nhánh ở đây là chạy một việc không ai yêu cầu — và việc đó tiêu tiền.
    return KetQua(nhanh=mac_dinh, output={"gia_tri": gia_tri})


def chay_stop(db, run, node: dict, **_) -> KetQua:
    p = node.get("params") or {}
    return KetQua(output={"ly_do": str(p.get("ly_do") or "")},
                  dung_run=str(p.get("trang_thai") or "SUCCEEDED"))


DINH_NGHIA = (
    (NodeDefinition(
        type="core.if", type_version=1, kind="control", category="FLOW",
        title=N_("Rẽ nhánh"),
        description=N_("Chạy nhánh true hoặc false theo một điều kiện."),
        icon="⑂",
        cong_vao=(("in", he_kieu.Cong(type="any", required=False, nhan="in")),),
        cong_ra=tuple(
            (t, he_kieu.Cong(type="control", required=False, nhan=t))
            for t in NHANH_IF),
        tham_so={"type": "object",
                 "properties": {"dieu_kien": {"type": "string"}},
                 "required": ["dieu_kien"], "additionalProperties": False},
        thi_hanh="inline", gia=Gia.mien_phi(), quyen=frozenset(),
        cho=(), ma_loi=("bieu_thuc_loi",), publish_duoc=True), chay_if),
    (NodeDefinition(
        type="core.switch", type_version=1, kind="control", category="FLOW",
        title=N_("Rẽ nhiều nhánh"),
        description=N_("Chọn nhánh theo giá trị của một biểu thức."),
        icon="⑃",
        cong_vao=(("in", he_kieu.Cong(type="any", required=False, nhan="in")),),
        cong_ra=(("nhanh", he_kieu.Cong(type="control", required=False,
                                        nhan="nhanh")),),
        tham_so={"type": "object",
                 "properties": {"bieu_thuc": {"type": "string"},
                                "nhanh": {"type": "array"},
                                "mac_dinh": {"type": "string"}},
                 "required": ["bieu_thuc", "nhanh"],
                 "additionalProperties": False},
        thi_hanh="inline", gia=Gia.mien_phi(), quyen=frozenset(),
        cho=(), ma_loi=("bieu_thuc_loi",), publish_duoc=True), chay_switch),
    (NodeDefinition(
        type="core.stop", type_version=1, kind="control", category="FLOW",
        title=N_("Dừng"),
        description=N_("Kết thúc lượt chạy ngay tại đây."),
        icon="■",
        cong_vao=(("in", he_kieu.Cong(type="any", required=False, nhan="in")),),
        cong_ra=(),
        tham_so={"type": "object",
                 "properties": {"trang_thai": {"type": "enum",
                                               "values": list(TRANG_THAI_STOP)},
                                "ly_do": {"type": "string"}},
                 "required": [], "additionalProperties": False},
        thi_hanh="inline", gia=Gia.mien_phi(), quyen=frozenset(),
        cho=(), ma_loi=(), publish_duoc=True), chay_stop),
)

__all__ = ["DINH_NGHIA", "NHANH_IF", "TRANG_THAI_STOP", "chay_if",
           "chay_stop", "chay_switch"]
