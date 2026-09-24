"""`core.set` · `core.transform` · `core.filter` · `core.aggregate` · `core.output`.

⛔ **KHÔNG THÊM HÀM NÀO NGOÀI BẢNG ĐÓNG §6.3.** P2 chốt 49 hàm trong
`ham_bieu_thuc.BANG_HAM`. Bốn node ở đây chỉ **gọi** bảng ấy: `core.aggregate`
không tự viết `sum`, nó tra `BANG_HAM["sum"]`. Một phép `sum` thứ hai trong kho
sẽ khác phép thứ nhất ở đúng ca biên không ai thử — rỗng, `null`, chuỗi lẫn số —
và cả hai đều trông hợp lý.
`test_1785::test_banh_coc_aggregate_khong_tu_viet_phep` cưỡng chế điều đó.

## `vars` (§6.5) — nối dây, không viết lại luật

`bien_vars` đã có `gop_vars` và `kiem_ghi_xung_dot`, đã được P2 test. Tệp này chỉ
khai node `core.set`; cổng xung đột ghi được gọi ở `bien_dich` — trước Task 6 nó
là một hàm **không ai gọi**, tức một cổng mở.
"""
from __future__ import annotations

from typing import Any

from platform_core.i18n import N_
from platform_core.workflow import chinh_sach, he_kieu, ngon_ngu
from platform_core.workflow.chinh_sach import LoiNgonNgu
from platform_core.workflow.ham_bieu_thuc import BANG_HAM
from platform_core.workflow.nut import Gia, NodeDefinition
from platform_core.workflow.nut_loi.chay import KetQua

#: Phép gộp của `core.aggregate`. ⭐ MỖI TÊN LÀ MỘT KHOÁ CỦA `BANG_HAM` §6.3 —
#: danh sách này là một lát cắt của bảng đóng, không phải một bảng thứ hai.
PHEP_GOP = ("count", "sum", "min", "max", "first", "last", "unique",
            "flatten", "sort")


def _tinh(bieu_thuc: str, mt: dict) -> Any:
    return ngon_ngu.tinh(str(bieu_thuc), mt)


def _mt_phan_tu(mt: dict, phan_tu: Any, i: int, tong: int) -> dict:
    """Môi trường cho MỘT phần tử — dùng lại namespace `loop` của §6.2.

    ⚠️ Không đặt ra một namespace `item` thứ hai. Người khai đã học `loop.item`
       trong thân `foreach`; một tên khác cho cùng ý nghĩa là một thứ phải nhớ
       hai lần, và `moi_truong_wf` sẽ phải mọc thêm một tham số.
    """
    ra = dict(mt)
    ra["loop"] = {"item": phan_tu, "index": i, "total": tong}
    return ra


def _mang(gia_tri: Any, ten: str) -> list:
    if not isinstance(gia_tri, list):
        raise LoiNgonNgu(
            f"dau_vao_sai: `{ten}` phai la mang, nhan "
            f"{chinh_sach._ten_kieu(gia_tri)}")
    return gia_tri


def chay_set(db, run, node: dict, *, moi_truong: dict, **_) -> KetQua:
    """Ghi biến vào `vars` (§6.5). Output của node **LÀ** tập biến nó ghi.

    ⭐ Không có bảng `vars` nào cả: `bien_vars.gop_vars` gộp output của các node
       `core.set` là tổ tiên. Trạng thái sửa được dùng chung là thứ §6.5 tránh
       từ đầu — *"Không có trạng thái sửa được dùng chung"*.
    """
    ra: dict[str, Any] = {}
    for ten, bt in (node.get("params") or {}).get("bien", {}).items():
        try:
            ra[str(ten)] = _tinh(bt, moi_truong)
        except LoiNgonNgu as loi:
            return KetQua(sang="FAILED",
                          error=f"bieu_thuc_loi: {ten}: {loi}"[:2000])
    return KetQua(output=ra)


def chay_transform(db, run, node: dict, *, moi_truong: dict, **_) -> KetQua:
    """Dựng một giá trị bằng biểu thức §6."""
    try:
        gia_tri = _tinh((node.get("params") or {}).get("gia_tri", ""),
                        moi_truong)
    except LoiNgonNgu as loi:
        return KetQua(sang="FAILED", error=f"bieu_thuc_loi: {loi}"[:2000])
    return KetQua(output={"gia_tri": gia_tri})


def chay_filter(db, run, node: dict, *, moi_truong: dict, **_) -> KetQua:
    """Giữ các phần tử thoả `dieu_kien`; `loop.item/index/total` có mặt."""
    p = node.get("params") or {}
    try:
        muc = _mang(_tinh(p.get("items", ""), moi_truong), "items")
        giu = [x for i, x in enumerate(muc)
               if bool(_tinh(p.get("dieu_kien", ""),
                             _mt_phan_tu(moi_truong, x, i, len(muc))))]
    except LoiNgonNgu as loi:
        ma = "dau_vao_sai" if "dau_vao_sai" in str(loi) else "bieu_thuc_loi"
        return KetQua(sang="FAILED", error=f"{ma}: {loi}"[:2000])
    return KetQua(output={"results": giu, "so_bo": len(muc) - len(giu)})


def chay_aggregate(db, run, node: dict, *, moi_truong: dict, **_) -> KetQua:
    """Gộp một mảng bằng MỘT hàm của bảng đóng §6.3."""
    p = node.get("params") or {}
    phep = str(p.get("phep") or "")
    ham = BANG_HAM.get(phep) if phep in PHEP_GOP else None
    if ham is None:
        # Không thể tới đây qua publish (`_kiem_tham_so_loi` chặn enum), nhưng
        # một version publish TRƯỚC khi `PHEP_GOP` bị thu hẹp thì tới được.
        return KetQua(sang="FAILED",
                      error=f"dau_vao_sai: phep gop {phep!r} khong co trong "
                            f"bang dong (co: {list(PHEP_GOP)})")
    try:
        muc = _mang(_tinh(p.get("items", ""), moi_truong), "items")
        gia_tri = ham(muc)
    except LoiNgonNgu as loi:
        ma = "dau_vao_sai" if "dau_vao_sai" in str(loi) else "bieu_thuc_loi"
        return KetQua(sang="FAILED", error=f"{ma}: {loi}"[:2000])
    except Exception as loi:                              # noqa: BLE001
        return KetQua(sang="FAILED",
                      error=f"bieu_thuc_loi: {phep}: {loi}"[:2000])
    return KetQua(output={"gia_tri": gia_tri})


def chay_output(db, run, node: dict, *, moi_truong: dict, **_) -> KetQua:
    """Khai một đầu ra của CẢ run. Kết quả run đọc bằng `ket_qua_run.doc`.

    ⚠️ KHÔNG ghi vào một cột mới trên `workflow_run`: kết quả run là thứ **dẫn
       xuất** từ các ảnh chụp `core.output`, và một cột thứ hai là một chỗ để
       hai câu trả lời lệch nhau sau một lần chạy lại.
    """
    p = node.get("params") or {}
    try:
        gia_tri = _tinh(p.get("gia_tri", ""), moi_truong)
    except LoiNgonNgu as loi:
        return KetQua(sang="FAILED", error=f"bieu_thuc_loi: {loi}"[:2000])
    return KetQua(output={"ten": str(p.get("ten") or ""), "gia_tri": gia_tri})


_VAO = (("in", he_kieu.Cong(type="any", required=False, nhan="in")),)

DINH_NGHIA = (
    (NodeDefinition(
        type="core.set", type_version=1, kind="data", category="DATA",
        title=N_("Đặt biến"),
        description=N_("Ghi một hoặc nhiều biến dùng được ở các bước sau."),
        icon="=",
        cong_vao=_VAO, cong_ra=(),
        tham_so={"type": "object",
                 "properties": {"bien": {"type": "bang_bieu_thuc"}},
                 "required": ["bien"], "additionalProperties": False},
        thi_hanh="inline", gia=Gia.mien_phi(), quyen=frozenset(),
        cho=(), ma_loi=("bieu_thuc_loi",), publish_duoc=True), chay_set),
    (NodeDefinition(
        type="core.transform", type_version=1, kind="data", category="DATA",
        title=N_("Biến đổi"),
        description=N_("Dựng một giá trị mới bằng một biểu thức."),
        icon="ƒ",
        cong_vao=_VAO,
        cong_ra=(("gia_tri", he_kieu.Cong(type="any", required=True,
                                          nhan="gia_tri")),),
        tham_so={"type": "object",
                 "properties": {"gia_tri": {"type": "bieu_thuc"}},
                 "required": ["gia_tri"], "additionalProperties": False},
        thi_hanh="inline", gia=Gia.mien_phi(), quyen=frozenset(),
        cho=(), ma_loi=("bieu_thuc_loi",), publish_duoc=True), chay_transform),
    (NodeDefinition(
        type="core.filter", type_version=1, kind="data", category="DATA",
        title=N_("Lọc"),
        description=N_("Giữ lại các phần tử thoả một điều kiện."),
        icon="⚟",
        cong_vao=_VAO,
        cong_ra=(("results", he_kieu.Cong(type="any[]", required=True,
                                          nhan="results")),
                 ("so_bo", he_kieu.Cong(type="int", required=True,
                                        nhan="so_bo"))),
        tham_so={"type": "object",
                 "properties": {"items": {"type": "bieu_thuc"},
                                "dieu_kien": {"type": "bieu_thuc"}},
                 "required": ["items", "dieu_kien"],
                 "additionalProperties": False},
        thi_hanh="inline", gia=Gia.mien_phi(), quyen=frozenset(),
        cho=(), ma_loi=("bieu_thuc_loi", "dau_vao_sai"),
        publish_duoc=True), chay_filter),
    (NodeDefinition(
        type="core.aggregate", type_version=1, kind="data", category="DATA",
        title=N_("Gộp"),
        description=N_("Đếm, cộng, lấy nhỏ nhất/lớn nhất… trên một mảng."),
        icon="Σ",
        cong_vao=_VAO,
        cong_ra=(("gia_tri", he_kieu.Cong(type="any", required=True,
                                          nhan="gia_tri")),),
        tham_so={"type": "object",
                 "properties": {"items": {"type": "bieu_thuc"},
                                "phep": {"type": "enum",
                                         "values": list(PHEP_GOP)}},
                 "required": ["items", "phep"], "additionalProperties": False},
        thi_hanh="inline", gia=Gia.mien_phi(), quyen=frozenset(),
        cho=(), ma_loi=("bieu_thuc_loi", "dau_vao_sai"),
        publish_duoc=True), chay_aggregate),
    (NodeDefinition(
        type="core.output", type_version=1, kind="data", category="DATA",
        title=N_("Đầu ra"),
        description=N_("Khai một giá trị là kết quả của cả lượt chạy."),
        icon="⇥",
        cong_vao=_VAO,
        cong_ra=(("ten", he_kieu.Cong(type="text", required=True, nhan="ten")),
                 ("gia_tri", he_kieu.Cong(type="any", required=True,
                                          nhan="gia_tri"))),
        tham_so={"type": "object",
                 "properties": {"ten": {"type": "string"},
                                "gia_tri": {"type": "bieu_thuc"}},
                 "required": ["ten", "gia_tri"], "additionalProperties": False},
        thi_hanh="inline", gia=Gia.mien_phi(), quyen=frozenset(),
        cho=(), ma_loi=("bieu_thuc_loi",), publish_duoc=True), chay_output),
)

__all__ = ["DINH_NGHIA", "PHEP_GOP", "chay_aggregate", "chay_filter",
           "chay_output", "chay_set", "chay_transform"]
