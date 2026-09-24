"""`core.foreach` · `core.foreach_end` · `core.join` — và `core.transform`.

## Ai LÁI vòng lặp

`core.foreach` chạy **cả vòng lặp** trong lượt thi hành của chính nó: mở
`ForeachVong`, chạy thân cho từng phần tử, ghi kết quả, rồi chốt trạng thái cho
mọi node thân **và** cho `core.foreach_end`.

🔴 VÌ SAO KHÔNG PHẢI "ĐỘNG CƠ LÁI TỪNG VÒNG"

`node_run` khoá theo `(run_id, node_id)`. Một node thân chạy 30 lần cần 30 trạng
thái, và mô hình C **cấm sửa ảnh chụp** — nên không có chỗ để 30 trạng thái ấy
sống. Activepieces giải đúng bài này bằng cách **khoá theo đường thi hành**
(`loop_1:3/loop_2:0/approval`, quyết định `000015`); ta đã làm điều đó cho
`wakeup` (Task 1) nhưng **chưa** cho `node_run` — đó là một migration trên bảng
đang chạy thật, và plan này không mở nó.

⇒ Hệ quả, khai thẳng ra: **thân `foreach` hôm nay chỉ nhận node `inline`.** Thân
  có node `job` bị từ chối **lúc publish** (`than_foreach_co_node_job`) và phải
  đi qua run con (`body_workflow`, spec §5.9) — Task 7. Từ chối ở publish trung
  thực hơn là chạy được nửa đường rồi treo.
"""
from __future__ import annotations

from typing import Any

from platform_core.i18n import N_
from platform_core.workflow import (bao_gia, chinh_sach, foreach as _foreach,
                                    he_kieu, may_trang_thai, moi_truong,
                                    ngon_ngu)
from platform_core.workflow.chinh_sach import LoiNgonNgu
from platform_core.workflow.nut import Gia, NodeDefinition
from platform_core.workflow.nut_loi.chay import KetQua

#: §5.9: `on_item_error ∈ {fail, skip, collect}`. ⛔ Danh sách ĐÓNG. Mặc định
#: `"fail"` là lựa chọn an toàn: dừng sớm tốn ít hơn chạy nốt 999 phần tử sau
#: một phần tử đã sai.
ON_ITEM_ERROR = ("fail", "skip", "collect")


def than_cua(graph: dict) -> dict[str, tuple[str, tuple[str, ...]]]:
    """`{id foreach: (id foreach_end, thân)}` — hỏi THẲNG `bao_gia`.

    ⛔ Không tính lại. `bao_gia.than_foreach` là chỗ con số **tiền** được nhân
       lên; nếu động cơ có một định nghĩa "thân" thứ hai thì ngày hai bên trôi
       khỏi nhau, trần chi phí và thứ thật sự chạy nói hai chuyện khác nhau —
       và không ai bắt khớp.
    """
    return bao_gia.than_foreach(graph)


def _tinh(bieu_thuc: str, mt: dict) -> Any:
    return ngon_ngu.tinh(str(bieu_thuc), mt)


def _rut_gon(ra: dict) -> Any:
    """Kết quả của MỘT vòng: output node thân cuối, bỏ lớp bọc nếu chỉ một cổng.

    ⚠️ Luật này là một QUY ƯỚC, và nó được viết ra chứ không để ngầm: một node
       thân có đúng một cổng ra (`core.transform` → `gia_tri`) thì `results` là
       danh sách các **giá trị**, không phải danh sách các object một khoá.
       Nhiều cổng ⇒ giữ nguyên object, vì bỏ lớp bọc khi đó là chọn hộ một cổng.
    """
    return next(iter(ra.values())) if len(ra) == 1 else dict(ra)


def _chot(db, run, nid: str, *, sang: str, ra: dict, mo_ta: str,
          error: str = "") -> None:
    """PENDING → READY → `sang`. Hai bước vì `NODE_CHUYEN` không cho nhảy cóc.

    ⭐ Và nó KHÔNG nên cho: một node đi thẳng PENDING → SUCCEEDED là một node
       chưa bao giờ được tuyên bố là đủ đầu vào. Giữ bảng chặt, đi qua đủ hai
       bước, và lịch sử ảnh chụp vẫn đọc được.
    """
    if may_trang_thai.trang_thai_node(db, run.id, nid) == "PENDING":
        may_trang_thai.chuyen_node(db, run.id, nid, sang="READY", mo_ta=mo_ta)
    may_trang_thai.chuyen_node(db, run.id, nid, sang=sang, mo_ta=mo_ta,
                               error=error, output_ref=dict(ra))


def _mt_than(db, run, g: dict, *, phu: dict, loop: dict) -> dict:
    """Môi trường §6.2 cho một node THÂN ở một vòng cụ thể.

    `phu` là output của các node thân **trong CHÍNH vòng này** — chúng đè lên
    ảnh chụp CSDL, vì ảnh chụp chỉ giữ được một trạng thái cho mỗi node còn
    vòng lặp thì có nhiều.
    """
    anh = moi_truong.anh_chup_nodes(db, run.id,
                                    [n["id"] for n in g.get("nodes") or []])
    anh.update(phu)
    return chinh_sach.moi_truong_wf(
        trigger={"kind": str(run.trigger_kind or "")}, workflow_input={},
        nodes=anh, loop=loop, run={"id": run.id, "status": run.status})


def chay_transform(db, run, node: dict, *, moi_truong: dict, **_) -> KetQua:
    """Dựng một giá trị bằng biểu thức §6 (spec §4.5 `core.transform`)."""
    try:
        gia_tri = _tinh((node.get("params") or {}).get("gia_tri", ""),
                        moi_truong)
    except LoiNgonNgu as loi:
        return KetQua(sang="FAILED", error=f"bieu_thuc_loi: {loi}"[:2000])
    return KetQua(output={"gia_tri": gia_tri})


def chay_foreach(db, run, node: dict, *, moi_truong: dict, g: dict,
                 **_) -> KetQua:
    """Chạy CẢ vòng lặp, rồi chốt trạng thái thân + `foreach_end`."""
    nid = str(node["id"])
    p = node.get("params") or {}
    try:
        muc = _tinh(p.get("items", ""), moi_truong)
    except LoiNgonNgu as loi:
        return KetQua(sang="FAILED", error=f"bieu_thuc_loi: {loi}"[:2000])
    if not isinstance(muc, list):
        return KetQua(sang="FAILED",
                      error=f"dau_vao_sai: `items` phai la mang, nhan "
                            f"{type(muc).__name__}")
    dong, than_ids = than_cua(g).get(nid, ("", ()))
    theo_id = {str(n["id"]): n for n in g.get("nodes") or []}
    than = [theo_id[k] for k in than_ids]
    try:
        vong = _foreach.mo_vong(db, run_id=run.id, node_id=nid, muc=muc,
                                max_items=int(p.get("max_items") or 0),
                                parallelism=p.get("parallelism"))
    except _foreach.VuotTran as loi:
        # ⛔ `foreach.VuotTran` ném TRƯỚC khi chạy, không dừng giữa chừng —
        #    "dừng giữa chừng nghĩa là đã tiêu một phần tiền cho một lượt chạy
        #    chắc chắn thất bại".
        return KetQua(sang="FAILED", error=f"vuot_max_items: {loi}"[:2000])
    except ValueError as loi:
        return KetQua(sang="FAILED", error=f"dau_vao_sai: {loi}"[:2000])

    cach = str(p.get("on_item_error") or "fail")
    from platform_core.workflow import nut_loi

    ket_qua: list[Any] = []
    loi_muc: list[dict] = []
    cuoi: dict[str, dict] = {}
    for i, phan_tu in enumerate(muc):
        loop = {"item": phan_tu, "index": i, "total": len(muc)}
        phu: dict[str, dict] = {}
        hong = ""
        for bn in than:
            ham = nut_loi.bo_thi_hanh(str(bn["type"]))
            try:
                kq = ham(db, run, bn,
                         moi_truong=_mt_than(db, run, g, phu=phu, loop=loop),
                         g=g)
            except Exception as loi:                      # noqa: BLE001
                kq = KetQua(sang="FAILED",
                            error=f"loi_he_thong: {type(loi).__name__}: {loi}")
            if kq.sang != "SUCCEEDED":
                hong = kq.error or "than_foreach_loi"
                break
            phu[str(bn["id"])] = {"status": "SUCCEEDED",
                                  "output": dict(kq.output or {}), "error": ""}
        if hong:
            if cach == "fail":
                return KetQua(sang="FAILED",
                              error=f"than_foreach_loi[{i}]: {hong}"[:2000])
            if cach == "collect":
                loi_muc.append({"index": i, "error": hong[:500]})
            continue
        gia_tri = _rut_gon(phu[str(than[-1]["id"])]["output"]) if than else None
        _foreach.ghi_ket_qua(db, vong, chi_so=i, ket_qua={"v": gia_tri})
        ket_qua.append(gia_tri)
        cuoi = phu

    for bn in than:
        bid = str(bn["id"])
        _chot(db, run, bid, sang="SUCCEEDED",
              ra=(cuoi.get(bid) or {}).get("output") or {},
              mo_ta=f"than foreach {nid} (vong cuoi)")
    if dong:
        _chot(db, run, dong, sang="SUCCEEDED",
              ra={"results": ket_qua, "errors": loi_muc},
              mo_ta=f"foreach_end cua {nid}")
    return KetQua(output={"so_muc": len(muc), "so_loi": len(loi_muc)})


def chay_foreach_end(db, run, node: dict, **_) -> KetQua:
    """Chỉ tới được đây khi KHÔNG có `core.foreach` nào chốt hộ nó.

    ⛔ Đó là một đồ thị sai (một `foreach_end` mồ côi), và nói thẳng ra rẻ hơn
       là trả một `results` rỗng trông như một vòng lặp không có phần tử nào.
    """
    return KetQua(sang="FAILED",
                  error="dau_vao_sai: foreach_end khong co core.foreach nao "
                        "mo vong cho no")


def chay_join(db, run, node: dict, **_) -> KetQua:
    """Điểm gặp của nhiều nhánh.

    ⭐ Với `ALL`, luật lan truyền của động cơ **đã là** join: một node chỉ READY
       khi mọi cạnh vào đã kích hoạt. Nên node này không dựng thêm cơ chế chờ
       nào — nó chỉ là một điểm neo có tên trên Canvas. `ANY`/`N_OF_M` đổi điều
       kiện READY, và điều đó sống ở `dong_co._lan_truyen` (một luật, một chỗ),
       không phải ở đây.
    """
    return KetQua(output={"che_do": str((node.get("params") or {})
                                        .get("che_do") or "ALL")})


DINH_NGHIA = (
    (NodeDefinition(
        type="core.transform", type_version=1, kind="data", category="DATA",
        title=N_("Biến đổi"),
        description=N_("Dựng một giá trị mới bằng một biểu thức."),
        icon="ƒ",
        cong_vao=(("in", he_kieu.Cong(type="any", required=False, nhan="in")),),
        cong_ra=(("gia_tri", he_kieu.Cong(type="any", required=True,
                                          nhan="gia_tri")),),
        tham_so={"type": "object",
                 "properties": {"gia_tri": {"type": "bieu_thuc"}},
                 "required": ["gia_tri"], "additionalProperties": False},
        thi_hanh="inline", gia=Gia.mien_phi(), quyen=frozenset(),
        cho=(), ma_loi=("bieu_thuc_loi",), publish_duoc=True), chay_transform),
    (NodeDefinition(
        type="core.foreach", type_version=1, kind="control", category="FLOW",
        title=N_("Lặp"),
        description=N_("Chạy thân vòng lặp một lần cho mỗi phần tử."),
        icon="↻",
        cong_vao=(("in", he_kieu.Cong(type="any", required=False, nhan="in")),),
        cong_ra=(("so_muc", he_kieu.Cong(type="int", required=True,
                                         nhan="so_muc")),
                 ("so_loi", he_kieu.Cong(type="int", required=True,
                                         nhan="so_loi"))),
        tham_so={"type": "object",
                 "properties": {"items": {"type": "bieu_thuc"},
                                "max_items": {"type": "int",
                                              "max": bao_gia.MAX_ITEMS_TRAN},
                                "parallelism": {"type": "int", "max": 16},
                                "on_item_error": {"type": "enum",
                                                  "values": list(ON_ITEM_ERROR)}},
                 "required": ["items", "max_items"],
                 "additionalProperties": False},
        thi_hanh="inline", gia=Gia.mien_phi(), quyen=frozenset(),
        cho=(), ma_loi=("bieu_thuc_loi", "dau_vao_sai", "vuot_max_items"),
        publish_duoc=True), chay_foreach),
    (NodeDefinition(
        type="core.foreach_end", type_version=1, kind="control",
        category="FLOW", title=N_("Hết lặp"),
        description=N_("Gom kết quả của vòng lặp theo thứ tự đầu vào."),
        icon="⇤",
        cong_vao=(("in", he_kieu.Cong(type="any", required=False, nhan="in")),),
        cong_ra=(("results", he_kieu.Cong(type="any[]", required=True,
                                          nhan="results")),
                 ("errors", he_kieu.Cong(type="any[]", required=True,
                                         nhan="errors"))),
        tham_so={"type": "object",
                 "properties": {"foreach": {"type": "string"}},
                 "required": ["foreach"], "additionalProperties": False},
        thi_hanh="inline", gia=Gia.mien_phi(), quyen=frozenset(),
        cho=(), ma_loi=("dau_vao_sai",), publish_duoc=True), chay_foreach_end),
    (NodeDefinition(
        type="core.join", type_version=1, kind="control", category="FLOW",
        title=N_("Gộp nhánh"),
        description=N_("Chờ nhiều nhánh gặp nhau: ALL, ANY hoặc N trong M."),
        icon="⋈",
        cong_vao=(("in", he_kieu.Cong(type="any", required=False, nhan="in",
                                      multiple=True)),),
        cong_ra=(("che_do", he_kieu.Cong(type="text", required=True,
                                         nhan="che_do")),),
        tham_so={"type": "object",
                 "properties": {"che_do": {"type": "enum",
                                           "values": ["ALL", "ANY", "N_OF_M"]},
                                "can": {"type": "int", "max": 64}},
                 "required": [], "additionalProperties": False},
        thi_hanh="inline", gia=Gia.mien_phi(), quyen=frozenset(),
        cho=(), ma_loi=(), publish_duoc=True), chay_join),
)

__all__ = ["DINH_NGHIA", "ON_ITEM_ERROR", "chay_foreach", "chay_foreach_end",
           "chay_join", "chay_transform", "than_cua"]
