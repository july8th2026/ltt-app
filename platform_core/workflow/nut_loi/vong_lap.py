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
from platform_core.workflow.nut_loi import cho
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
          error: str = "", vong=()) -> None:
    """PENDING → READY → `sang`. Hai bước vì `NODE_CHUYEN` không cho nhảy cóc.

    ⭐ Và nó KHÔNG nên cho: một node đi thẳng PENDING → SUCCEEDED là một node
       chưa bao giờ được tuyên bố là đủ đầu vào. Giữ bảng chặt, đi qua đủ hai
       bước, và lịch sử ảnh chụp vẫn đọc được.
    """
    if may_trang_thai.trang_thai_node(db, run.id, nid, vong) == "PENDING":
        may_trang_thai.chuyen_node(db, run.id, nid, sang="READY",
                                   mo_ta=mo_ta, vong=vong)
    may_trang_thai.chuyen_node(db, run.id, nid, sang=sang, mo_ta=mo_ta,
                               error=error, output_ref=dict(ra), vong=vong)


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


#: Khoá trong `ForeachMuc.ket_qua` đánh dấu một phần tử **hỏng**. Lưu vào CSDL
#: chứ không giữ trong bộ nhớ: một vòng lặp có node job sống qua nhiều lượt
#: động cơ, nên mọi thứ cần nhớ giữa hai lượt phải nằm trong bảng.
KHOA_LOI = "_loi"
#: Phần tử bị BỎ (`on_item_error = "skip"`) — không vào `results`, không vào
#: `errors`. Khác `KHOA_LOI`: `collect` muốn kể lại, `skip` thì không.
KHOA_BO = "_bo"


def _vong_cua(db, run_id: str, node_id: str):
    """`ForeachVong` đang mở của một node, hoặc `None`."""
    from platform_core.models import ForeachVong

    return db.query(ForeachVong).filter_by(run_id=run_id,
                                           node_id=str(node_id)).first()


#: Bao nhiêu hàng `foreach_muc` lấy về mỗi LẦN HỎI trong một tick.
#:
#: 🔴 Không phải một con số cho đẹp. Bản cũ đọc **cả bảng** mỗi tick, và làn
#:    p3b đo trên PostgreSQL thật (`docs/superpowers/reports/p3b-do-tai/`):
#:    tổng công là `N²/P` — **127 000 hàng, 31,67 giây** bookkiping thuần cho
#:    MỘT run ở `N=1000, P=8`, tức trần `max_items ≤ 1000` hôm nay đã là một
#:    rào trước khi mở cho khách.
#:
#: ⭐ Vì sao lấy theo LÔ chứ không lấy đúng `parallelism` hàng: một thân toàn
#:    node **inline** hoàn tất ngay trong tick, nên nó không bao giờ tăng
#:    `dang_cho` — lấy đúng `P` hàng sẽ bắt nó hỏi `N/P` lần trong cùng một
#:    tick. Lô rộng hơn `P` một chút giữ cả hai ca ở mức thấp: thân job đọc
#:    ~một lô mỗi tick (HẰNG theo N), thân inline đọc tổng cộng ~N hàng cho cả
#:    vòng lặp (TUYẾN TÍNH theo N).
LO_DOC = 16


def _muc_theo_chi_so(db, vong) -> dict:
    """⛔ ĐÃ GỠ KHỎI ĐƯỜNG NÓNG — còn lại chỉ cho phép kiểm đối chứng.

    Đọc **cả bảng** `foreach_muc` của một vòng. Bên lái vòng lặp không được gọi
    hàm này nữa: gọi nó mỗi tick chính là `O(N²/P)` mà `LO_DOC` mô tả.
    """
    from platform_core.models import ForeachMuc

    return {int(m.chi_so): m for m in
            db.query(ForeachMuc).filter_by(vong_id=vong.id).all()}


def _mot_phan_tu(db, run, g, node, than, i: int, phan_tu, *, cong_cu):
    """Đẩy MỘT phần tử đi một bước. Trả `("xong"|"cho"|"hong", giá trị|lý do)`.

    🔴 Vì sao trạng thái thân đọc từ CSDL chứ không giữ trong bộ nhớ: một node
       thân sinh job thì vòng lặp **sống qua nhiều lượt động cơ**. Giữa hai lượt
       chỉ có bảng còn lại — và đó chính là lý do `node_run` phải khoá theo
       ĐƯỜNG THI HÀNH: `f:0/x` và `f:1/x` là hai trạng thái, không phải một.
    """
    from platform_core.workflow import cau_noi, thi_hanh

    nid = str(node["id"])
    ngu = ((nid, i),)
    # ⚠️ `so_muc` đọc từ hàng `foreach_vong` đã nạp sẵn trong phiên (`db.get`
    #    đi qua identity map), không phải một `SELECT … WHERE run_id AND
    #    node_id` mới cho MỖI phần tử — hàm này chạy N lần mỗi run.
    loop = {"item": phan_tu, "index": i,
            "total": int(_vong_cua(db, run.id, nid).so_muc)}
    phu: dict[str, dict] = {}
    from platform_core.workflow import nut_loi

    for bn in than:
        bid = str(bn["id"])
        tt = may_trang_thai.trang_thai_node(db, run.id, bid, ngu)
        if tt in ("QUEUED", "RUNNING", "WAITING"):
            # Job của phần tử này chưa xong — thử áp kết quả trước khi bỏ cuộc.
            cau_noi.ap_ket_qua(db, run, bid, cong_cu=cong_cu, vong=ngu)
            # ⭐ …và nếu nó là một node CHỜ (`core.delay`/`wait`/`human`) thì
            #    thử mở điểm chờ CỦA CHÍNH VÒNG NÀY. `ngu = ((nid, i),)` là thứ
            #    tách `f:0/d` khỏi `f:1/d`; thiếu nó, vòng 2 đọc điểm chờ của
            #    vòng 1 và bỏ qua lần chờ của nó (activepieces `000015`).
            if tt == "WAITING" and str(bn.get("thi_hanh")) == "run_con":
                # ⭐ `core.call_workflow` trong thân vòng lặp: run con của
                #    CHÍNH chỉ số này. `ap_ket_qua_con` cấp run đi khoá trần
                #    nên nó không bao giờ thấy `f:0/g` — đo được 24/09: hai
                #    run con xong, cha đứng WAITING 20 giờ, tiền vẫn bị giữ.
                from platform_core.workflow import run_con as _run_con
                _run_con.ap_ket_qua_mot(db, run, bn, vong=ngu)
            if tt == "WAITING" and cho.la_node_cho(bn):
                kq = cho.tiep_mot(db, run, bn, vong=ngu)
                if kq is not None:
                    _chot(db, run, bid, sang=kq.sang,
                          ra=dict(kq.output or {}),
                          mo_ta=f"diem cho da mo [{i}]", error=kq.error,
                          vong=ngu)
            tt = may_trang_thai.trang_thai_node(db, run.id, bid, ngu)
            if tt in ("QUEUED", "RUNNING", "WAITING"):
                return ("cho", "")
        anh = thi_hanh.anh_chup_hien_tai(db, run.id, bid, ngu)
        if tt == "SUCCEEDED":
            phu[bid] = {"status": "SUCCEEDED",
                        "output": moi_truong_mod_cong_ra(anh), "error": ""}
            continue
        if tt in may_trang_thai.NODE_KET_THUC:
            return ("hong", (anh.error if anh else "") or "than_foreach_loi")
        if tt == "PENDING":
            may_trang_thai.chuyen_node(db, run.id, bid, sang="READY",
                                       mo_ta=f"than foreach {nid}", vong=ngu)
        if str(bn.get("thi_hanh")) == "job":
            cau_noi.nop_job(db, run, bn, cong_cu=cong_cu, vong=ngu)
            tt = may_trang_thai.trang_thai_node(db, run.id, bid, ngu)
            if tt in ("QUEUED", "RUNNING", "WAITING"):
                return ("cho", "")
            anh = thi_hanh.anh_chup_hien_tai(db, run.id, bid, ngu)
            return ("hong", (anh.error if anh else "") or "nop_job_tu_choi")
        ham = nut_loi.bo_thi_hanh(str(bn["type"]))
        if ham is None:
            return ("hong", f"loi_he_thong: {bn['type']!r} khong co bo thi hanh")
        try:
            kq = ham(db, run, bn, g=g, cong_cu=cong_cu, vong=ngu,
                     moi_truong=_mt_than(db, run, g, phu=phu, loop=loop))
        except Exception as loi:                          # noqa: BLE001
            kq = KetQua(sang="FAILED",
                        error=f"loi_he_thong: {type(loi).__name__}: {loi}")
        _chot(db, run, bid, sang=kq.sang, ra=dict(kq.output or {}),
              mo_ta=f"than foreach {nid}[{i}]", error=kq.error, vong=ngu)
        # ⭐ `WAITING` KHÔNG phải hỏng: một `core.delay` trong thân vòng lặp
        #    vừa mở điểm chờ của chỉ số này. Phần tử ấy "đang chờ", y như một
        #    phần tử có node job chưa xong — nó chiếm một suất `parallelism`
        #    và sẽ được `tiep_mot` đẩy tiếp ở lượt động cơ sau.
        if kq.sang == "WAITING":
            return ("cho", "")
        if kq.sang != "SUCCEEDED":
            return ("hong", kq.error or "than_foreach_loi")
        phu[bid] = {"status": "SUCCEEDED", "output": dict(kq.output or {}),
                    "error": ""}
    if not than:
        return ("xong", None)
    return ("xong", _rut_gon(phu[str(than[-1]["id"])]["output"]))


def moi_truong_mod_cong_ra(anh) -> dict:
    """Cổng ra THẬT của một ảnh chụp (bỏ khoá nội bộ `_`)."""
    return {k: v for k, v in (getattr(anh, "output_ref", None) or {}).items()
            if not str(k).startswith("_")}


def _lai_vong(db, run, node: dict, g: dict, *, cong_cu=None) -> KetQua:
    """Đẩy vòng lặp đi một bước. `WAITING` = còn phải chờ job của thân.

    ⛔ Hàm này chạy **nhiều lần** cho cùng một vòng lặp (mỗi lượt động cơ một
       lần, khi một job của thân xong). Nên nó phải LUỸ ĐẲNG: mọi trạng thái
       nằm trong `foreach_vong`/`foreach_muc`/`node_run`, không trong biến cục bộ.
    """
    nid = str(node["id"])
    p = node.get("params") or {}
    vong = _vong_cua(db, run.id, nid)
    if vong is None:
        return KetQua(sang="FAILED", error="loi_he_thong: chua mo vong lap")
    dong, than_ids = than_cua(g).get(nid, ("", ()))
    theo_id = {str(n["id"]): n for n in g.get("nodes") or []}
    than = [theo_id[k] for k in than_ids]
    cach = str(p.get("on_item_error") or "fail")
    tran_song_song = max(1, int(vong.parallelism or 1))

    # ⭐ KEYSET, không phải "đọc cả bảng rồi lọc bằng Python". Phần tử đã xong
    #    không bao giờ được nạp lại; con trỏ `sau` chỉ đi tới.
    dang_cho = 0
    sau = -1
    lo = max(tran_song_song, LO_DOC)
    while dang_cho < tran_song_song:
        hang = _foreach.muc_chua_xong(db, vong, sau_chi_so=sau, gioi_han=lo)
        if not hang:
            break
        for i, phan_tu in hang:
            if dang_cho >= tran_song_song:
                break
            sau = i
            trang_thai, gia_tri = _mot_phan_tu(
                db, run, g, node, than, i, phan_tu, cong_cu=cong_cu)
            if trang_thai == "cho":
                dang_cho += 1
                continue
            if trang_thai == "hong":
                if cach == "fail":
                    return KetQua(
                        sang="FAILED",
                        error=f"than_foreach_loi[{i}]: {gia_tri}"[:2000])
                khoa = KHOA_LOI if cach == "collect" else KHOA_BO
                _foreach.ghi_ket_qua(db, vong, chi_so=i,
                                     ket_qua={khoa: str(gia_tri)[:500]})
                continue
            _foreach.ghi_ket_qua(db, vong, chi_so=i, ket_qua={"v": gia_tri})

    if _foreach.chi_so_chua_xong(db, vong):
        # ⚠️ `WAITING` chứ không `RUNNING`: node này không tính toán gì trong lúc
        #    chờ, và `NODE_DANG_CHAY` có `WAITING` nên nó vẫn chiếm một suất song
        #    song của run — đúng, vì thân nó đang chạy job thật.
        return KetQua(sang="WAITING", output={"so_muc": int(vong.so_muc)})

    # ⚠️ Đây là phép đọc `O(N)` **một lần**, ở cuối vòng — khác hẳn một phép
    #    đọc `O(N)` **mỗi tick**, và tách hai vai đó ra là toàn bộ bản sửa.
    ket = _foreach.ket_qua_theo_chi_so(db, vong)
    results = [r["v"] for _i, r in ket if "v" in r]
    errors = [{"index": i, "error": r[KHOA_LOI]}
              for i, r in ket if KHOA_LOI in r]
    if dong:
        _chot(db, run, dong, sang="SUCCEEDED",
              ra={"results": results, "errors": errors},
              mo_ta=f"foreach_end cua {nid}")
    return KetQua(output={"so_muc": int(vong.so_muc), "so_loi": len(errors)})


def _bo_dong(db, run, node: dict, g: dict) -> None:
    """Vòng lặp hỏng ⇒ `foreach_end` SKIPPED, để nhánh sau nó lan tiếp.

    ⛔ SKIPPED chứ không FAILED: `foreach_end` không hỏng, nó **không còn
       đường nào tới** (§5.5). Và phải chốt nó bằng tay vì lan truyền cấp
       run không đụng tới nó nữa (`dong_co._cuoi_foreach`).
    """
    dong, _than = than_cua(g).get(str(node["id"]), ("", ()))
    if dong and may_trang_thai.trang_thai_node(db, run.id, dong) \
            not in may_trang_thai.NODE_KET_THUC:
        _chot(db, run, dong, sang="SKIPPED", ra={},
              mo_ta=f"vong lap {node['id']} hong")


def chay_foreach(db, run, node: dict, *, moi_truong: dict, g: dict,
                 cong_cu=None, **_) -> KetQua:
    """Mở vòng lặp rồi đẩy nó bước đầu tiên."""
    nid = str(node["id"])
    p = node.get("params") or {}
    if _vong_cua(db, run.id, nid) is None:
        try:
            muc = _tinh(p.get("items", ""), moi_truong)
        except LoiNgonNgu as loi:
            _bo_dong(db, run, node, g)
            return KetQua(sang="FAILED", error=f"bieu_thuc_loi: {loi}"[:2000])
        if not isinstance(muc, list):
            _bo_dong(db, run, node, g)
            return KetQua(sang="FAILED",
                          error=f"dau_vao_sai: `items` phai la mang, nhan "
                                f"{type(muc).__name__}")
        try:
            _foreach.mo_vong(db, run_id=run.id, node_id=nid, muc=muc,
                             max_items=int(p.get("max_items") or 0),
                             parallelism=p.get("parallelism"))
        except _foreach.VuotTran as loi:
            _bo_dong(db, run, node, g)
            # ⛔ `foreach.VuotTran` ném TRƯỚC khi chạy, không dừng giữa chừng —
            #    "dừng giữa chừng nghĩa là đã tiêu một phần tiền cho một lượt
            #    chạy chắc chắn thất bại".
            return KetQua(sang="FAILED", error=f"vuot_max_items: {loi}"[:2000])
        except ValueError as loi:
            _bo_dong(db, run, node, g)
            return KetQua(sang="FAILED", error=f"dau_vao_sai: {loi}"[:2000])
    kq = _lai_vong(db, run, node, g, cong_cu=cong_cu)
    if kq.sang == "FAILED":
        _bo_dong(db, run, node, g)
    return kq


def tiep_vong(db, run, g: dict, *, cong_cu=None) -> int:
    """Đẩy tiếp MỌI `core.foreach` đang `WAITING`. Trả số vòng đã chốt xong.

    ⭐ Đây là cửa RESUME: một job của thân xong ⇒ wakeup ⇒ động cơ gọi hàm này.
       Không có nó, vòng lặp có node job sẽ đứng `WAITING` tới hạn 20 giờ.
    """
    dem = 0
    for n in g.get("nodes") or []:
        if str(n.get("type")) != "core.foreach":
            continue
        nid = str(n["id"])
        if may_trang_thai.trang_thai_node(db, run.id, nid) != "WAITING":
            continue
        kq = _lai_vong(db, run, n, g, cong_cu=cong_cu)
        if kq.sang == "WAITING":
            continue        # vẫn chờ: KHÔNG chuyển (WAITING -> WAITING vô nghĩa)
        if kq.sang == "FAILED":
            _bo_dong(db, run, n, g)
        may_trang_thai.chuyen_node(db, run.id, nid, sang=kq.sang,
                                   mo_ta="vong lap ket thuc", error=kq.error,
                                   output_ref=dict(kq.output or {}))
        dem += 1
    return dem


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

__all__ = ["DINH_NGHIA", "KHOA_BO", "KHOA_LOI", "ON_ITEM_ERROR",
           "chay_foreach", "chay_foreach_end", "chay_join",
           "tiep_vong", "than_cua"]
