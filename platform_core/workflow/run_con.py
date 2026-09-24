"""Run CON của `core.call_workflow` (spec §5.10) — và đường tiền của cả cây.

## 🔴 MỘT KHOẢN GIỮ CHO CẢ CÂY

`tien.py` viết ra bất biến gốc: *"Nếu run cũng giữ và node cũng giữ thì khách
trả **hai lần** cho cùng một việc."* Run con là đúng cái bẫy ấy ở một tầng khác —
gọi `tao_run.tao_run` cho run con nghĩa là mỗi tầng gọi giam thêm một khoản.

⇒ Ba luật, và cả ba phải đi cùng nhau, bỏ một là sổ sai:

1. **Run con không giữ chỗ.** `tao_run_con` không gọi `tien.giu_cho_run`
   (`test_1786::test_banh_coc_MOT_khoan_giu_cho_CA_CAY` ghim rằng chỉ
   `tao_run.py` được gọi hàm ấy).
2. **Trần của con nằm trong trần của cha.** `dinh_nghia.xuat_ban_draft` ghim
   `version_id` và ghi `gia_con = estimated_max` của version con; `bao_gia`
   đọc đúng con số đó (§7.2).
3. **Chi phí THẬT của con nằm trong chi phí của cha.** `ket_so` của cha tính
   `tong_chi_phi_hop_le(cha) + tong_chi_phi_con(cha)` — một hàm **dẫn xuất**,
   không phải một phép cộng dần. Nếu không, tiền thật của con **không bao giờ
   được thu**: con không có `hold_id` nên `tien.ket_so_tien` bỏ qua nó.

⚠️ Bỏ (3) mà giữ (1) là chỗ dễ sai nhất: mọi phép kiểm về "không giữ hai lần"
   vẫn xanh, và nền tảng lặng lẽ **cho không** phần việc chạy trong run con.
   Bản đầu của chính tệp này cộng dần lúc con xong và bị `ket_so` của cha GHI
   ĐÈ ngay sau đó — xem `tong_chi_phi_con`.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select

from platform_core.models import WorkflowRun, WorkflowVersion
from platform_core.workflow import danh_thuc, may_trang_thai, su_kien, thi_hanh

#: §10 bảng "Vòng vô hạn": *"độ sâu subworkflow 5"*. Cưỡng chế lúc **publish**
#: (độ sâu tính TĨNH được vì `version_id` đã ghim và version là bất biến), nên
#: lúc chạy không cần đếm lại — nhưng vẫn kiểm, vì một version publish TRƯỚC khi
#: trần bị siết vẫn chạy được.
DO_SAU_TOI_DA = 5

LOAI_GOI = "core.call_workflow"

#: Khoá trong `output_ref` của node gọi, giữ id run con đang chờ.
KHOA_RUN_CON = "_run_con"


def _bay_gio() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class QuaSau(ValueError):
    pass


def tao_run_con(db, *, cha: WorkflowRun, node_id: str, version_id: str,
                inputs: dict) -> WorkflowRun:
    """Mở một run con. ⛔ KHÔNG giữ chỗ credit — xem đầu tệp.

    Không commit: bên gọi (`_pha_inline` của động cơ) commit cùng lượt.
    """
    if int(cha.do_sau or 0) + 1 > DO_SAU_TOI_DA:
        raise QuaSau(f"do sau {int(cha.do_sau or 0) + 1} > {DO_SAU_TOI_DA}")
    ver = db.get(WorkflowVersion, version_id)
    if ver is None:
        raise ValueError(f"version {version_id!r} khong ton tai")
    con = thi_hanh.tao_run(
        db, workflow_id=ver.workflow_id, version_id=ver.id,
        owner_id=cha.owner_id, trigger_kind="run_con",
        # ⛔ `estimated_max = 0`: con số ấy là ĐẦU VÀO của `tien.giu_cho_run`,
        #    và một run con mang một trần khác 0 là một run con **có thể** bị
        #    giữ tiền nếu ai đó gọi nhầm hàm ấy. Trần thật của con đã nằm trong
        #    `gia_con` của node gọi ở đồ thị cha.
        estimated_max=0)
    con.parent_run_id = cha.id
    con.parent_node_id = str(node_id)
    con.do_sau = int(cha.do_sau or 0) + 1
    may_trang_thai.chuyen_run(db, con.id, sang="QUEUED")
    danh_thuc.hen(db, run_id=con.id, kind="start", due_at=_bay_gio())
    su_kien.ghi(db, con.id, "WorkflowStarted",
                du_lieu={"trigger_kind": "run_con", "version_id": ver.id,
                         "inputs": dict(inputs or {}),
                         "parent_run_id": cha.id})
    return con


def tong_chi_phi_con(db, run_id: str) -> int:
    """Tổng `actual_cost` của các run CON. Dùng ở `ket_so` của CHA.

    🔴 VÌ SAO CỘNG Ở `ket_so`, KHÔNG PHẢI CỘNG DẦN LÚC CON XONG

    Bản đầu cộng vào `cha.actual_cost` ngay khi con kết sổ. Nó **không sống nổi
    một dòng**: `ket_so` của cha sau đó GHI ĐÈ `actual_cost` bằng
    `tong_chi_phi_hop_le` của riêng cha, và phần tiền của con biến mất — đo được
    bằng `test_1786::test_chi_phi_that_cua_CON_cong_len_CHA` (`0 == 3`).

    ⇒ Chi phí của một run là một hàm **DẪN XUẤT**: ảnh chụp của chính nó cộng
      chi phí các con. Một chỗ tính, không hai. Lồng nhiều tầng tự đúng: chi phí
      cháu đã nằm trong `actual_cost` của con lúc con kết sổ, và con luôn kết sổ
      trước cha (cha đang WAITING chờ nó).
    """
    return int(db.execute(
        select(func.coalesce(func.sum(WorkflowRun.actual_cost), 0))
        .where(WorkflowRun.parent_run_id == run_id)).scalar() or 0)


def bao_cha(db, con: WorkflowRun) -> bool:
    """Run con vừa kết thúc ⇒ **đánh thức cha**. Trả `True` nếu có cha.

    ⛔ KHÔNG đụng tới tiền ở đây — xem `tong_chi_phi_con`.
    """
    if not con.parent_run_id:
        return False
    cha = db.get(WorkflowRun, con.parent_run_id)
    if cha is None:
        return False
    # 🔴 `parent_node_id` ĐÃ LÀ đường thi hành (`chay_call_workflow` ghi
    #    `thi_hanh.khoa_node(id, vong)` vào đó), nên ⛔ KHÔNG mã hoá nó lần
    #    thứ hai: `duong_thi_hanh("f:0/g")` **ném** (`:`/`/` không nằm trong
    #    tập id hợp lệ), và trước khi ném thì nó cũng cho ra một khoá mà
    #    không ai khác sinh được. Cùng bài học đã ghi ở
    #    `noi_lai.danh_thuc_node_cua`.
    danh_thuc.hen_luy_dang(
        db, run_id=cha.id, kind="child_run", due_at=_bay_gio(),
        node_run_id=str(con.parent_node_id or "goi"))
    db.flush()
    from platform_core.workflow import tao_run
    tao_run.danh_thuc_dong_co(db)
    return True


def ap_ket_qua_con(db, cha: WorkflowRun, graph: dict) -> int:
    """Node `core.call_workflow` đang WAITING mà run con đã xong ⇒ chốt nó.

    Trả số node đã chốt. Đọc kết quả con bằng `ket_qua_run.doc` — **dẫn xuất**
    từ các node `core.output` của con, không phải một cột thứ hai.
    """
    dem = 0
    for n in graph.get("nodes") or []:
        if str(n.get("type")) != LOAI_GOI:
            continue
        dem += 1 if ap_ket_qua_mot(db, cha, n) else 0
    return dem


def ap_ket_qua_mot(db, cha: WorkflowRun, node: dict, *, vong=()) -> bool:
    """Chốt MỘT node `core.call_workflow` — **của một lần chạy cụ thể**.

    🔴 VÌ SAO HÀM NÀY NHẬN `vong`, VÀ VÌ SAO ĐÓ LÀ MỘT LỖ TIỀN

    `ap_ket_qua_con` duyệt `graph["nodes"]` và tra trạng thái với `vong=()`.
    Sau khi `node_run` đổi sang khoá **đường thi hành**, một
    `core.call_workflow` nằm TRONG thân `foreach` có ảnh chụp ở `f:0/g`, nên
    lần tra `vong=()` **không thấy gì** và node bị bỏ qua.

    Đo được (24/09, đồ thị `foreach` 2 vòng, có đối chứng là cùng đồ thị
    nhưng `call_workflow` nằm NGOÀI `foreach`):

        trong foreach : run=RUNNING  node={f:0/g: WAITING, f:1/g: WAITING}
                        so_con=2  ket_so=False      ⇐ run con ĐÃ XONG
        ngoai (đối chứng): run=SUCCEEDED  node={g: SUCCEEDED}  ket_so=True

    ⇒ Cả hai run con chạy xong, cha đứng `WAITING` tới `TRAN_RUN` 20 giờ, và
      `ket_so_luc` là `NULL` nghĩa là **khoản giữ chỗ credit vẫn bị giam**.
      Đúng hạng lỗi bốn lỗ tiền của phase gốc 4: im lặng, không ném.

    ⚠️ Bên gọi trong thân `foreach` là `vong_lap._mot_phan_tu`, chỗ duy nhất
       biết chỉ số vòng. Chốt node ở HAI nơi (ở đây với `vong=()` **và** ở đó
       với `ngu`) là cách để một node được chuyển hai lần bằng hai khoá khác
       nhau — nên `ap_ket_qua_con` chỉ đi khoá trần, và thân vòng lặp tự gọi
       hàm này với chỉ số của nó.
    """
    from platform_core.workflow import ket_qua_run

    nid = str(node["id"])
    # ⭐ MOT lan doc, khong hai (ban truoc hoi `trang_thai_node` roi hoi
    #    `anh_chup_hien_tai` — hai truy van cho CUNG mot hang, va phep thu hep
    #    `None` di vong qua mot ham khac nen mypy khong theo duoc: `union-attr`,
    #    gate L1 24/09 cua phien VPS bat duoc).
    anh = thi_hanh.anh_chup_hien_tai(db, cha.id, nid, vong)
    if anh is None or anh.execution_status != "WAITING":
        return False
    rid = str((anh.output_ref or {}).get(KHOA_RUN_CON) or "")
    con = db.get(WorkflowRun, rid) if rid else None
    if con is None or con.status not in may_trang_thai.RUN_KET_THUC:
        return False
    xong = con.status == "SUCCEEDED"
    may_trang_thai.chuyen_node(
        db, cha.id, nid, sang="SUCCEEDED" if xong else "FAILED",
        mo_ta="run con ket thuc", vong=vong,
        error="" if xong else f"run_con_loi: {con.status}",
        attempt_number=int(anh.attempt_number or 1),
        output_ref={KHOA_RUN_CON: rid,
                    "outputs": ket_qua_run.doc(db, rid) if xong else {},
                    "status": con.status})
    return True


def con_dang_chay(db, run_id: str) -> list[str]:
    return list(db.execute(
        select(WorkflowRun.id).where(
            WorkflowRun.parent_run_id == run_id,
            WorkflowRun.status.not_in(may_trang_thai.RUN_KET_THUC))).scalars())


__all__ = ["DO_SAU_TOI_DA", "KHOA_RUN_CON", "LOAI_GOI", "QuaSau",
           "ap_ket_qua_con", "bao_cha", "con_dang_chay", "tao_run_con",
           "tong_chi_phi_con"]
