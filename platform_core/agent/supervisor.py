"""Supervisor (spec §12.4) — hành động **có luật**, và cấm bằng SỰ VẮNG MẶT.

## Hình dạng: một sổ đăng ký ĐÓNG, không phải một chuỗi `if`

`HANH_DONG` là **toàn bộ** thứ supervisor làm được. `lam()` là cửa duy nhất, và
nó chỉ gọi được thứ có trong sổ. Một hành động không có trong sổ thì **không có
hàm nào làm nó** — không phải "có hàm nhưng bị một `if` chặn".

⭐ Nguồn (⛔ không tự suy): `langchain-ai/langgraph-swarm-py`
   `langgraph_swarm/handoff.py`. Ở đó, quyền chuyển giao cho một agent tồn tại
   **vì và chỉ vì** `create_handoff_tool(agent_name=…)` đã sinh ra một công cụ
   cho nó; `get_handoff_destinations()` đọc ngược tập đích **từ những công cụ
   có thật trong đồ thị**, không từ một bảng khai song song. Tức: tập quyền là
   một **sự kiện về mã**, đo được — đúng điều kiện ra của phase gốc 12
   (*"các hành động cấm không có đường gọi"*), và `test_2933` đo nó bằng đồ thị
   gọi chứ không bằng lời hứa trong docstring này.

## 🔴 HAI CHỖ SPEC §12.4 PHẢI THU HẸP — đo được, không phải ý kiến

1. **Không đụng run ĐÃ KẾT SỔ.** §12.4 viết *"đọc run đang FAILED/WAITING
   lâu"*. Nhưng `FAILED` nằm trong `may_trang_thai.RUN_KET_THUC`, và một run
   kết thúc là một run `ket_so.ket_so()` **đã quyết toán**: khoản giữ đã nhả,
   `hold_id` đã xoá. Hồi sinh nó nghĩa là chạy tiếp một lượt **không còn tiền
   bị giam** — tức nền tảng làm không công, và sổ của khách đã chốt. Nên
   `quet()` chỉ trả run **chưa kết sổ** (`RUNNING`/`WAITING`) đang treo, và
   `lam()` từ chối mọi run đã kết sổ bằng mã `run_da_ket_so`.

2. **`doi_model` KHÔNG có trong sổ.** §12.4 cho phép *"chọn model khác trong
   enum khai sẵn của node"*. Không làm được mà không phạm một luật khác:
   `params` của node sống trong `workflow_version.graph`, một bản ghi **bất
   biến** (§4.2) — ghi đè nó chính là *"sửa version đã publish"*, đúng thứ
   §12.4 **cấm**. Chỗ hợp lệ duy nhất là một ô ghi đè **theo run**, và ô ấy
   chưa tồn tại (cần cột/bảng mới). ⇒ Không đăng ký một cửa giả luôn từ chối:
   một hành động **vắng mặt** đọc được, một hành động luôn ném thì không. Lược
   đồ đề xuất nằm ở `docs/superpowers/reports/p8-agent/task-3-report.md`.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

from sqlalchemy import func, select

from platform_core.models import WorkflowRun, WorkflowVersion
from platform_core.workflow import (cho_doi, danh_thuc, may_trang_thai as mtt,
                                    su_kien, thi_hanh, thu_lai)

#: Treo bao lâu thì supervisor mới nhìn tới. Đủ dài để một lượt job bình thường
#: (kể cả retry có backoff) tự xong — supervisor không được tranh việc với
#: động cơ.
NGUONG_TRE_S = 900

#: Mã lý do khi TỪ CHỐI. Mỗi mã là một luật, và mỗi luật có một phép kiểm.
MA_TU_CHOI = (
    "hanh_dong_khong_ton_tai", "run_da_ket_so", "node_khong_ton_tai",
    "trang_thai_node_sai", "het_luot_thu_lai", "khong_thu_lai_duoc",
    "khong_co_nhanh_error", "node_van_quan_trong",
)


@dataclass(frozen=True)
class KetQua:
    lam: bool
    ma: str = ""
    chi_tiet: str = ""


def _bay_gio() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _node(graph: dict, node_id: str) -> Optional[dict]:
    for n in (graph or {}).get("nodes") or []:
        if str(n.get("id")) == str(node_id):
            return n
    return None


def do_thi(db, run: WorkflowRun) -> dict:
    ver = db.get(WorkflowVersion, run.version_id)
    return dict(ver.graph or {}) if ver is not None else {}


# ── Hành động ĐƯỢC PHÉP. Mỗi hàm tự kiểm; không hàm nào tin bên gọi. ────────

def thu_lai_node(db, run: WorkflowRun, *, node_id: str, graph: dict,
                 **_) -> KetQua:
    """Hẹn lượt thử kế — **trong `retry.max` còn lại** (§12.4)."""
    n = _node(graph, node_id)
    if n is None:
        return KetQua(False, "node_khong_ton_tai", node_id)
    anh = thi_hanh.anh_chup_hien_tai(db, run.id, node_id)
    hien = anh.execution_status if anh is not None else mtt.NODE_BAT_DAU
    if hien in thu_lai.KHONG_THU_LAI:
        # ⛔ `ABANDONED` ở đây KHÔNG phải "chưa chạy": provider **có thể đã
        #    nhận**. Thử lại là rủi ro side effect đôi, và §12.4 cấm đúng ca
        #    này. `KHONG_THU_LAI` là bản khai có sẵn — ⛔ không chép lại.
        return KetQua(False, "khong_thu_lai_duoc", f"{node_id}: {hien}")
    if hien != "FAILED":
        return KetQua(False, "trang_thai_node_sai", f"{node_id}: {hien}")
    lan = int(anh.attempt_number or 1) if anh is not None else 1
    if not thu_lai.con_luot(n, lan):
        return KetQua(False, "het_luot_thu_lai", f"{node_id}: lan {lan}")
    han = thu_lai.hen(db, run_id=run.id, node=n, lan=lan)
    if not mtt.chuyen_node(db, run.id, node_id, sang="RETRY_SCHEDULED",
                           mo_ta="supervisor hen thu lai",
                           attempt_number=lan,
                           output_ref={thu_lai.KHOA_HAN: han.isoformat()}):
        return KetQua(False, "trang_thai_node_sai", f"{node_id}: {hien}")
    return KetQua(True, chi_tiet=f"{node_id}: lan {lan + 1} luc {han}")


def di_nhanh_loi(db, run: WorkflowRun, *, node_id: str, graph: dict,
                 **_) -> KetQua:
    """Đánh thức động cơ để nó đi nhánh `error` **đã khai** của node (§12.4).

    ⛔ Supervisor KHÔNG tự chọn node kế. Nhánh lỗi là một cạnh `kind="ERROR"`
       trong đồ thị đã publish, và bên duy nhất được lan truyền theo cạnh là
       động cơ. Ở đây chỉ kiểm *"nhánh ấy có thật không"* rồi gọi động cơ —
       một bản sao của luật lan truyền ở tầng này là một bản sao sẽ trôi.
    """
    if _node(graph, node_id) is None:
        return KetQua(False, "node_khong_ton_tai", node_id)
    co = [e for e in (graph.get("edges") or [])
          if str(e.get("source_node")) == str(node_id)
          and str(e.get("kind")) == "ERROR"]
    if not co:
        return KetQua(False, "khong_co_nhanh_error", node_id)
    danh_thuc.hen_luy_dang(db, run_id=run.id, kind="supervisor",
                           due_at=_bay_gio())
    return KetQua(True, chi_tiet=f"{node_id}: {len(co)} canh ERROR")


def hoi_nguoi(db, run: WorkflowRun, *, node_id: str, graph: dict,
              cau_hoi: str = "", **_) -> KetQua:
    """Mở một waitpoint HUMAN — hỏi người thay vì tự đoán (§12.4)."""
    if node_id and _node(graph, node_id) is None:
        return KetQua(False, "node_khong_ton_tai", node_id)
    wp = cho_doi.tao_waitpoint(
        db, run_id=run.id, owner_id=run.owner_id, kind="HUMAN",
        required_successes=1,
        idempotency_key=f"supervisor:{run.id}:{node_id}")
    return KetQua(True, chi_tiet=f"waitpoint {wp.id}: {cau_hoi[:200]}")


def bo_qua_node(db, run: WorkflowRun, *, node_id: str, graph: dict,
                **_) -> KetQua:
    """Bỏ qua node có `settings.khong_quan_trong = true` (§12.4).

    ⛔ Cờ ấy do NGƯỜI SOẠN workflow đặt lúc publish, không do supervisor đặt.
       Supervisor chỉ **đọc** nó — nếu nó đặt được cờ thì luật *"chỉ bỏ qua
       node không quan trọng"* tự nó vô nghĩa.
    """
    n = _node(graph, node_id)
    if n is None:
        return KetQua(False, "node_khong_ton_tai", node_id)
    if (n.get("settings") or {}).get("khong_quan_trong") is not True:
        return KetQua(False, "node_van_quan_trong", node_id)
    anh = thi_hanh.anh_chup_hien_tai(db, run.id, node_id)
    hien = anh.execution_status if anh is not None else mtt.NODE_BAT_DAU
    if not mtt.chuyen_node(db, run.id, node_id, sang="SKIPPED",
                           mo_ta="supervisor bo qua node khong quan trong",
                           attempt_number=int(
                               anh.attempt_number or 1) if anh else 1):
        return KetQua(False, "trang_thai_node_sai", f"{node_id}: {hien}")
    danh_thuc.hen_luy_dang(db, run_id=run.id, kind="supervisor",
                           due_at=_bay_gio())
    return KetQua(True, chi_tiet=node_id)


#: 🔴 SỔ ĐÓNG. Thêm một khoá ở đây là thêm một quyền cho supervisor, và
#:    `test_2933` sẽ đòi đường gọi của nó sạch. Thứ KHÔNG có ở đây thì
#:    supervisor không có hàm nào để làm.
HANH_DONG: dict[str, Callable[..., KetQua]] = {
    "thu_lai_node": thu_lai_node,
    "di_nhanh_loi": di_nhanh_loi,
    "hoi_nguoi": hoi_nguoi,
    "bo_qua_node": bo_qua_node,
}


def lam(db, run: WorkflowRun, *, hanh_dong: str, node_id: str = "",
        graph: Optional[dict] = None, **kw) -> KetQua:
    """CỬA DUY NHẤT. Mọi lượt — làm được hay không — đều ghi nhật ký."""
    ham = HANH_DONG.get(str(hanh_dong))
    if ham is None:
        kq = KetQua(False, "hanh_dong_khong_ton_tai", str(hanh_dong)[:80])
    elif run.status in mtt.RUN_KET_THUC:
        kq = KetQua(False, "run_da_ket_so", f"{run.id}: {run.status}")
    else:
        kq = ham(db, run, node_id=str(node_id),
                 graph=graph if graph is not None else do_thi(db, run), **kw)
    su_kien.ghi(db, run.id, "SupervisorDecision", node_id=str(node_id or ""),
                du_lieu={"hanh_dong": str(hanh_dong), "lam": bool(kq.lam),
                         "ma": kq.ma, "chi_tiet": kq.chi_tiet})
    return kq


def quet(db, *, bay_gio: Optional[datetime] = None, tre_s: int = NGUONG_TRE_S,
         gioi_han: int = 50) -> list:
    """Run **chưa kết sổ** mà đã treo quá `tre_s`. Mới nhất trước."""
    # ⚠️ `workflow_run` KHÔNG có `updated_at` — nên "treo bao lâu" ở đây là
    #    *"sống từ bao giờ"* (`started_at`, rơi về `created_at`), KHÔNG phải
    #    *"lần cuối có tiến triển"*. Một run dài mà vẫn đang chạy ngon sẽ lọt
    #    vào danh sách này; đó là lý do MỌI hành động tự kiểm lại điều kiện
    #    của nó thay vì tin `quet()`.
    moc = (bay_gio or _bay_gio()) - timedelta(seconds=max(0, int(tre_s)))
    song_tu = func.coalesce(WorkflowRun.started_at, WorkflowRun.created_at)
    return list(db.execute(
        select(WorkflowRun)
        .where(WorkflowRun.status.in_(("RUNNING", "WAITING")),
               song_tu < moc,
               WorkflowRun.parent_run_id == "")
        .order_by(song_tu.asc())
        .limit(max(1, int(gioi_han)))).scalars())


__all__ = ["HANH_DONG", "MA_TU_CHOI", "NGUONG_TRE_S", "KetQua", "bo_qua_node",
           "di_nhanh_loi", "do_thi", "hoi_nguoi", "lam", "quet",
           "thu_lai_node"]
