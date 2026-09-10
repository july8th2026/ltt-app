"""`M-1` — chuyển bản nháp Canvas v2 (`agent_workflows`) sang lược đồ V2.

Nguồn: `docs/architecture/workflow_v2_audit/27_29 §27.2`.

## 🔴 HẠNG MỤC NÀY TỪNG ĐƯỢC XẾP LÀ "GẦN NHƯ KHÔNG TỒN TẠI"

`§27.1` viết vậy dựa trên một phép đo **đúng**: `0 job agent.advance / 28 ngày`.
Kết luận rút ra: *"không có khách đứng trên đường cũ ⇒ thay thẳng, gỡ bản cũ"*.

⚠️ Đo `D2` ngày 08/09/2026 trên chính CSDL production:

    agent_workflows 10 · agent_runs 4 · agent_workflow_snapshots 83
    doi chung: users 27 · jobs 1770 · credit_entries 5500

⇒ `0 run` **đúng**, nhưng nó nói **KHÔNG AI CHẠY** — không nói **KHÔNG AI ĐÃ
  DỰNG**. Đó là hai mệnh đề khác nhau, và cả tài liệu lẫn `CLAUDE.md` đã đọc
  mệnh đề thứ nhất thành mệnh đề thứ hai.

## ⭐ HÌNH DẠNG THẬT quyết cách làm, không phải con số tổng

Đo tiếp (chỉ đọc, 08/09):

    10/10 mang ten mac dinh "Workflow moi"   khong ai doi ten
    toi da 3 node, toi da 2 canh             khong do thi nao that su
    4/10 `document` RONG                     khong co Canvas v2 de chuyen
    6/10 `document` 5 khoa                   active_page_id · budget_max_credit
                                             · goal · pages · version
    3 `validated` · 7 `draft` · tat ca `plan_version = 1`

⇒ `M-1` **có thật** nhưng **nhỏ**, và nó phải xử **ba lớp** chứ không một.

## ⛔ HAI TÍNH CHẤT BẮT BUỘC

**Mặc định là CHẠY THỬ.** Một script di trú mặc định ghi là một script chỉ cần
gõ nhầm một lần. Mặc định chạy thử biến "lỡ tay" thành một **báo cáo**.

**Luỹ đẳng.** Một script chạy lại vì hoảng không được biến thành một sự cố
thật.
"""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select

from platform_core.models import AgentWorkflow, Workflow, WorkflowDraft

#: Khoá của Canvas v2 mang **ý nghĩa nghiệp vụ** — phải sang v3 nguyên vẹn.
#: `budget_max_credit` là một con số về TIỀN: mất nó là mất trần chi phí.
_GIU_NGUYEN = ("goal", "budget_max_credit", "active_page_id")


def _canh_v3(canh: dict) -> dict:
    """Cạnh v2 → v3, **giữ lại** `sourceHandle`/`targetHandle`.

    ⭐ Đây là toàn bộ giá trị của `M-1`. `27_29 §27.2`:

        "du lieu de dung canh co kieu DA CO SAN — hom nay `canvas_to_plan()`
         VUT NO DI. Script chuyen GIU LAI thu dang bi vut."

    Tức việc này không phải chép dữ liệu sang chỗ mới, mà **cứu phần thông tin
    mà đường cũ đang đánh rơi**. Sau khi Plan v1 bị gỡ, thứ đã rơi không lấy
    lại được.

    ⛔ **LUỸ ĐẲNG: nhận cả cạnh v2 lẫn cạnh v3.** Không phải để chiều lòng ai —
       `va_trang()` cho cạnh **đã là v3** đi qua đây, và một bản chỉ đọc khoá v2
       sẽ không thấy `source_port` rồi **rơi về `"out"`**. Tức công cụ vá sẽ
       **xoá sạch cổng**, đúng thứ `M-1` được viết để cứu.

       `tests/test_963::test_va_trang_GIU_viewport_va_node_dang_co` bắt được
       điều đó trước khi nó chạm production lần thứ hai.
    """
    return {
        "id": str(canh.get("id", "")),
        # v3 truoc, v2 sau. Thu tu nay la ca cai luy dang.
        "source_node": str(canh.get("source_node") or canh.get("source") or ""),
        "target_node": str(canh.get("target_node") or canh.get("target") or ""),
        "source_port": str(canh.get("source_port")
                           or canh.get("sourceHandle") or "out"),
        "target_port": str(canh.get("target_port")
                           or canh.get("targetHandle") or "in"),
        "kind": str(canh.get("kind") or "DATA"),
    }


#: Khoá của một trang mà **trình soạn đọc thẳng rồi `.map()`**, không kiểm.
#:
#: 🔴 Bản đầu của `_trang_v3` chỉ sinh 4 khoá (`id`/`name`/`nodes`/`edges`), và
#:    Canvas **trắng màn** với `Cannot read properties of undefined (reading
#:    'map')`. Kiểu `CanvasPage` khai cả 8 khoá là **bắt buộc** — TypeScript tin
#:    lời khai ấy nên nó không sinh một phép kiểm nào, và JSON từ CSDL không đi
#:    qua trình biên dịch.
#:
#: ⛔ Không bộ kiểm Python nào bắt được: chúng đọc `document` như một `dict` và
#:    `dict` thiếu khoá vẫn là một `dict` hợp lệ. Không bộ kiểm TypeScript nào
#:    bắt được: chúng dựng dữ liệu giả **đúng kiểu**. Chỗ duy nhất thấy được là
#:    một trình duyệt thật mở một bản ghi thật.
_TRANG_MAC_DINH: dict = {
    "viewport": {"x": 0, "y": 0, "zoom": 1},
    "frames": [],
    "notes": [],
    "comments": [],
    "view": {"grid": True, "connections": True, "minimap": True},
}


def _trang_v3(trang: dict) -> dict:
    # ⚠️ Khai kieu TUONG MINH. Khong khai thi mypy suy `dict[str, Sequence]` tu
    #    ba gia tri dau (str/list/list), roi gan `viewport` — mot `dict` — vao
    #    do la `assignment` error. Mot trang v3 KHONG dong nhat ve kieu gia tri,
    #    va lam no dong nhat de chieu long bo suy kieu se lam no sai voi thuc te.
    ra: dict[str, Any] = {
        "id": str(trang.get("id", "p1")),
        "name": str(trang.get("name", "")),
        "nodes": list(trang.get("nodes") or []),
        "edges": [_canh_v3(c) for c in (trang.get("edges") or [])],
    }
    # GIỮ thứ bản cũ có, ĐIỀN thứ nó thiếu. Không ghi đè: một `viewport` người
    # dùng đã kéo là thông tin thật, và di trú không được làm mất nó.
    for khoa, mac_dinh in _TRANG_MAC_DINH.items():
        gia_tri = trang.get(khoa)
        ra[khoa] = gia_tri if gia_tri is not None else (
            dict(mac_dinh) if isinstance(mac_dinh, dict) else list(mac_dinh))
    return ra


def _tu_document(doc: dict) -> Optional[dict]:
    trang = doc.get("pages") or []
    if not trang:
        return None
    ra: dict[str, Any] = {"version": 3,
                          "pages": [_trang_v3(t) for t in trang]}
    for k in _GIU_NGUYEN:
        if k in doc:
            ra[k] = doc[k]
    return ra


def _tu_nodes_edges(cu: AgentWorkflow) -> Optional[dict]:
    """Đường dự phòng cho **4/10** bản ghi production có `document` rỗng.

    ⛔ Bỏ qua chúng là bỏ mất **40 %** thứ cần chuyển, và bỏ theo cách im lặng:
       script báo *"đã chuyển 6"* và không ai hỏi *6 trên mấy*.
    """
    nodes = list(cu.nodes or [])
    edges = list(cu.edges or [])
    if not nodes and not edges:
        return None
    return {
        "version": 3,
        "goal": cu.goal or "",
        "budget_max_credit": int(cu.budget_max or 0),
        "active_page_id": "p1",
        # ⛔ DÙNG LẠI `_trang_v3`, không dựng trang lần thứ hai bằng tay. Bản
        #    đầu dựng tay ở cả hai chỗ và **cả hai** cùng thiếu bốn khoá —
        #    một bản sao của một khiếm khuyết là hai chỗ phải nhớ sửa.
        "pages": [_trang_v3({"id": "p1", "name": "", "nodes": nodes,
                             "edges": edges,
                             "viewport": cu.viewport or None})],
    }


def chuyen(db, *, chay_that: bool = False) -> dict:
    """Chuyển mọi `AgentWorkflow` sang `workflow` + `workflow_draft`.

    Trả một báo cáo **cộng lại được**:

        da_chuyen + rong + da_co == tong so ban ghi

    ⭐ Bất biến ấy là thứ làm báo cáo kiểm được: không có nó, một nhánh
       `continue` bị bỏ quên sẽ làm vài bản ghi biến mất khỏi **mọi** con số,
       và một báo cáo không cộng lại được là một báo cáo không ai kiểm được.
    """
    cu_ds = list(db.execute(select(AgentWorkflow)).scalars())
    ra: dict[str, Any] = {
        "chay_that": bool(chay_that), "tong": len(cu_ds),
        "da_chuyen": 0, "rong": 0, "da_co": 0, "se_chuyen": 0,
        "anh_xa": {},
    }

    for cu in cu_ds:
        # ⭐ Danh tính: bản mới GIỮ NGUYÊN `id` của bản cũ. Luỹ đẳng thành một
        #    phép tra khoá chính, và ánh xạ cũ→mới là phép đồng nhất.
        #
        # 🔴 Bản đầu đánh dấu bằng `published_version_id = f"m1:{cu.id}"`. Nó
        #    chạy trên SQLite và **chết trên PostgreSQL**: `m1:` + id 36 ký tự
        #    = **39**, còn cột là `String(36)`. SQLite không cưỡng chế độ dài
        #    `VARCHAR`, PostgreSQL có — nên phép diễn tập trên bản sao SQLite
        #    của chính dữ liệu production vẫn **xanh**.
        #
        #    Cùng họ với `BOOLEAN DEFAULT 1` ở các migration: SQLite nhận thứ
        #    PostgreSQL từ chối. Khác ở chỗ `tools/do_migration_tren_postgres.py`
        #    **không** đỡ được ca này — nó kiểm *migration*, còn đây là *đường
        #    chạy lúc runtime*. Một trục nữa còn thiếu.
        #
        # ⛔ Và cách sửa KHÔNG phải cắt ngắn chuỗi cho vừa 36. Ép một dấu vào
        #    một cột mang nghĩa khác ("version đang xuất bản") là chỗ sinh ra
        #    lỗi ấy. `published_version_id` nay giữ đúng nghĩa của nó: rỗng =
        #    chưa xuất bản lần nào — đúng với mọi bản vừa di trú.
        da = db.get(Workflow, cu.id)
        if da is not None:
            ra["da_co"] += 1
            ra["anh_xa"][cu.id] = da.id
            continue

        doc = cu.document if isinstance(cu.document, dict) else {}
        moi = _tu_document(doc) or _tu_nodes_edges(cu)
        if moi is None:
            # Rỗng hoàn toàn. Vẫn đếm — gộp nó vào `da_chuyen` là nói dối một
            # cách dễ chịu: con số đẹp hơn, và người đọc tưởng có 10 đồ thị
            # được cứu.
            ra["rong"] += 1
            continue

        if not chay_that:
            ra["se_chuyen"] += 1
            continue

        # ⚠️ GIỮ NGUYÊN tên: 10/10 bản ghi production mang tên mặc định
        #    "Workflow mới". Đặt tên mới cho chúng là **bịa** một thông tin mà
        #    không người dùng nào cung cấp.
        wf = Workflow(id=cu.id, owner_id=cu.user_id, name=cu.name)
        db.add(wf)
        db.flush()
        db.add(WorkflowDraft(workflow_id=wf.id, document=moi, revision=1))
        db.flush()
        ra["da_chuyen"] += 1
        ra["anh_xa"][cu.id] = wf.id

    return ra


def va_trang(db, *, chay_that: bool = False) -> dict:
    """Điền khoá trang còn thiếu cho những `WorkflowDraft` **đã di trú rồi**.

    🔴 **Vì sao cần một đường riêng.** `chuyen()` luỹ đẳng theo khoá chính: chạy
       lại thấy `Workflow` đã có thì trả `da_co` và **không đụng** vào draft.
       Đó là tính chất đúng — nhưng nó cũng có nghĩa là một khiếm khuyết trong
       `_trang_v3` **không tự lành** ở những bản đã chuyển.

    ⇒ Ngày 09/09/2026 đúng tình huống ấy: `_trang_v3` sinh 4 khoá thay vì 8, 9
      workflow production đã ở dạng thiếu, và Canvas trắng màn khi mở chúng.

    ⭐ **Chỉ THÊM, không xoá, không ghi đè.** Hàm đi qua đúng `_trang_v3` mà một
       lượt di trú mới dùng, nên bản vá và bản mới không thể lệch nhau — một
       định nghĩa, không phải hai chỗ phải nhớ sửa cùng lúc.

    ⚠️ **Mặc định chạy thử**, cùng lý do với `chuyen()`.
    """
    from platform_core.models import WorkflowDraft as _WD

    ra: dict[str, Any] = {"chay_that": bool(chay_that), "tong": 0,
                          "da_va": 0, "da_du": 0, "se_va": 0}
    for draft in db.execute(select(_WD)).scalars():
        ra["tong"] += 1
        doc = draft.document if isinstance(draft.document, dict) else {}
        trang_cu = doc.get("pages") or []
        if not trang_cu:
            ra["da_du"] += 1
            continue
        trang_moi = [_trang_v3(t) for t in trang_cu]
        if trang_moi == trang_cu:
            ra["da_du"] += 1
            continue
        if not chay_that:
            ra["se_va"] += 1
            continue
        # Gán một `dict` MỚI: SQLAlchemy không theo dõi thay đổi bên trong một
        # cột JSON đã nạp, nên sửa tại chỗ sẽ không được ghi xuống.
        draft.document = {**doc, "pages": trang_moi}
        draft.revision = int(draft.revision or 0) + 1
        db.flush()
        ra["da_va"] += 1
    return ra
