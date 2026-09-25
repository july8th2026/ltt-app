"""Agent Designer (spec §12.2) — planner sinh **draft v3**, thôi sinh Plan v1.

`planner.plan_once()` sinh **Plan v1** (`{"steps": [...]}`), một hình dạng mà
động cơ v3 không chạy: `tao_run` chỉ nhận `workflow_version.graph`, và graph ấy
là đầu ra của `bien_dich.bien_dich(draft_v3)`. Nên một kế hoạch Plan v1 phải đi
qua `plan_v1.plan_to_canvas` rồi `di_tru_m1` rồi mới tới compiler — ba lần dịch,
mỗi lần một cơ hội đánh rơi (M-1 đã đánh rơi cổng cạnh đúng như thế). Mô-đun này
bỏ cả ba: model sinh thẳng hình dạng mà **cổng publish** đọc.

## Nguồn (tra trước khi tự suy)

`n8n-io/n8n` `packages/@n8n/ai-workflow-builder.ee/src/tools/add-node.tool.ts`
(bộ dựng workflow bằng AI của n8n). Hai điều lấy về nguyên văn:

1. **Model không dựng node; nó chỉ nêu ý định.** `createAddNodeTool` nhận một
   lược đồ zod (`nodeCreationSchema`), rồi mã tất định mới dựng node:
   `findNodeType(nodeType, nodeVersion, nodeTypes)` trả `null` ⇒ trả lỗi
   `NODE_TYPE_NOT_FOUND`. Ta làm đúng thế bằng `bien_dich`, vốn đã có mã
   `node_khong_ton_tai` — ⛔ **không** viết một bảng tra thứ hai ở đây.
2. **Vị trí do MÃ tính** (`calculateNodePosition`), không do model bịa. Một toạ
   độ do model đặt là một trường không ai kiểm được: nó không sai được kiểu,
   không sai được lược đồ, và làm hỏng bố cục một cách im lặng. Ở đây
   `_vi_tri()` tính theo chỉ số, và toạ độ model gửi bị **bỏ**.

⛔ **Mô-đun này KHÔNG publish** (spec §12.2: *"Agent không publish: nó ghi
   draft, người dùng xem báo giá rồi bấm publish"*). Nó không import
   `dinh_nghia`; bánh cóc cơ học `test_2933` ghim rằng không có đường gọi nào
   từ đây tới `xuat_ban*`.
"""
from __future__ import annotations

import json
import re
from typing import Callable, Optional

from platform_core.agent.normalizer import PlanNormalizeError, extract_json
from platform_core.workflow import bien_dich, nut
from platform_core.workflow.di_tru_m1 import _canh_v3

#: Hình dạng tài liệu soạn thảo (spec §4.1).
SCHEMA_DRAFT = 3
TRANG_MAC_DINH = "p1"

#: Trần số node một lượt soạn được phép trả về. §10 cho đồ thị tới 10 000 node;
#: đây là trần của **một lượt model**, hẹp hơn hẳn, vì một câu tiếng Việt không
#: sinh ra 10 000 node — 41 node là dấu hiệu model đang lặp.
MAX_NUT = 40

#: Bố cục do mã tính (xem docstring, nguồn n8n `calculateNodePosition`).
BUOC_X, BUOC_Y = 280, 160
_MOT_HANG = 6

_ID = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")


class LoiSoan(ValueError):
    """Đầu ra model KHÔNG dùng được. `ma` là mã máy đọc, cho giao diện."""

    def __init__(self, ma: str, thong_diep: str, node_id: str = ""):
        super().__init__(f"{ma}: {thong_diep}")
        self.ma, self.node_id = ma, node_id


def _vi_tri(chi_so: int) -> dict:
    return {"x": (chi_so % _MOT_HANG) * BUOC_X,
            "y": (chi_so // _MOT_HANG) * BUOC_Y}


#: Tiền tố node app/tool trong tài liệu draft (spec §4.1) — khớp
#: `TIEN_TO_APP` của `frontend/agent-canvas/src/nodeDefinition.ts`.
_TIEN_TO_APP = "app."


def _data_canvas(loai: str, params: dict) -> dict:
    """`data.tool`/`data.params` — hình dạng CanvasNode cần để RENDER.

    ⛔ Đây KHÔNG phải hình dạng cổng biên dịch đọc (`_node`/`_node_loi` đọc
       top-level `type`/`params`) — nó là một bản MIRROR thêm vào riêng cho
       canvas, y hệt cách `frontend/agent-canvas/src/nodeDefinition.ts
       ::slugCongCu` đặt tên: bỏ tiền tố `app.` cho node app/tool
       (`app.video.generate` → `video.generate`), GIỮ NGUYÊN cho node lõi
       (`core.if` → `core.if`, không có tiền tố đó để bỏ).

    Thiếu khoá `data` này (bản trước `chuan_hoa()` không viết) làm
    `CanvasShell.tsx::displayNodes` đọc `node.data.tool` trên một
    `node.data` `undefined` ⇒ `TypeError` giữa `useMemo` render — trình
    soạn "sập" đúng lúc nạp tài liệu `/soan` vừa trả về (`test_4250`).
    """
    slug = loai[len(_TIEN_TO_APP):] if loai.startswith(_TIEN_TO_APP) else loai
    return {"tool": slug, "params": params}


def danh_muc(*, cong_cu: Optional[dict] = None,
             dinh_nghia: Optional[dict] = None) -> list[dict]:
    """Danh mục node **rút gọn** làm đầu vào prompt (spec §12.2).

    ⛔ Chỉ node `publish_duoc`. Mời model kéo một node mà cổng publish sẽ từ
       chối là mời nó sinh ra một bản nháp không bao giờ chạy được — cùng lý do
       palette hiện node chưa hỗ trợ ở trạng thái vô hiệu (`nut_loi/__init__`).
    """
    so = nut.tat_ca(cong_cu=cong_cu) if dinh_nghia is None else dinh_nghia
    ra = []
    for nd in sorted(so.values(), key=lambda x: x.type):
        if not nd.publish_duoc:
            continue
        ra.append({"type": nd.type, "type_version": nd.type_version,
                   "kind": nd.kind, "title": nd.title,
                   "description": nd.description,
                   "cong_vao": [ten for ten, _c in nd.cong_vao],
                   "cong_ra": [ten for ten, _c in nd.cong_ra],
                   "tham_so": nd.tham_so})
    return ra


def build_prompt(goal: str, *, muc: list[dict], ngan_sach_credit: int,
                 input_types: Optional[dict] = None) -> str:
    """Prompt cho một lượt soạn (spec §12.2).

    ⭐ Dòng danh mục KHÔNG còn viết `type@version` dính liền (24/09 sửa lại
       sau lượt gọi model THẬT đầu tiên qua máy B, plan wf-v2 P-B task FLOW
       G). Bản trước ghi mỗi node là `- core.http@1 (job): ...`, và model
       (`ltt-3.5`) **chép nguyên chuỗi ấy vào trường `type`** của mọi node nó
       sinh ra (`"type": "core.http@1"` thay vì `"type": "core.http"`) —
       đúng bài học "ví dụ trong lời nhắc là mệnh lệnh ngầm": model học
       HÌNH THỨC hiển thị, không phải lược đồ JSON. Hậu quả: **100% node**
       trong lượt gọi thật đó bị `bien_dich` từ chối bằng `node_khong_ton_tai`
       dù `type` gốc (bỏ hậu tố) nằm đúng trong danh mục.

    ⭐ `[QUY_UOC_KIND]` là dòng MỚI. Bản trước liệt `"kind"` như một khoá rỗng
       trong mẫu JSON mà KHÔNG bao giờ nói giá trị hợp lệ là gì
       (`bien_dich._KIND = {"DATA","CONTROL","ERROR"}`, xem
       `platform_core/workflow/bien_dich.py`). Cùng lượt gọi thật đó, model
       đoán `"kind": "json"` cho mọi cạnh — một cái đoán hợp lý (nó đang nói
       về ĐỊNH DẠNG dữ liệu chảy qua cạnh) nhưng sai Ô cần điền, và bị từ
       chối bằng `canh_khong_hop_le`. Không phải model kém; đây là một chỗ
       lược đồ chưa từng được nói ra.

    ⭐ `[QUY_UOC_BIEU_THUC]` là dòng MỚI (25/09, làn `wfk`, lượt gọi thật thứ
       hai qua máy B — `tests/test_4190_flow_g_goi_model_that.py::_LOT2_25_09`).
       `check_ready` (`core.if`) sinh
       `dieu_kien = "{{ nodes.fetch_sheet.output.json.status === 'READY' }}"`
       — HAI lỗi cùng lúc mà bản trước không hề cảnh báo:
       1. bọc trong `{{ }}` dù tham số kiểu `bieu_thuc`/`bang_bieu_thuc` của
          NODE LÕI (`bien_dich.KIEU_BIEU_THUC`) phải TRẦN — bản trước chỉ có
          MỘT câu `[DAU_RA]` chung cho mọi tham số ("Tham chiếu … bằng
          `{{ nodes.<id>.output.<cong> }}`"), không phân biệt tham số CHUỖI
          của node app/tool (đúng là cần `{{ }}` để nội suy) với tham số
          BIỂU THỨC của node lõi (không ngoặc, đọc thẳng bằng
          `ngon_ngu.tinh`/`ast.parse`);
       2. `===` của JavaScript — ngôn ngữ §6 chỉ có `==`/`!=`
          (`chinh_sach.py`: `ast.Eq`/`ast.NotEq`), và vì được phân tích bằng
          `ast.parse` (cú pháp Python), `===` không bị từ chối bằng một
          thông điệp rõ ràng — nó là lỗi cú pháp thẳng.
       Bài học lặp lại của `vi-du-trong-loi-nhac-la-menh-lenh-ngam.md`: một
       lược đồ chưa từng được GIẢI NGHĨA (chỉ dump JSON thô
       `"dieu_kien":{"type":"bieu_thuc"}`) là một lược đồ model phải ĐOÁN —
       và đoán theo mẫu quen (`{{ }}` của app/tool, `===` của JS) chứ không
       theo Sec6.
    """
    dong = ["[DANH_MUC_NODE]"]
    for m in muc:
        luoc_do = json.dumps(m["tham_so"], ensure_ascii=False,
                             separators=(",", ":"))
        dong.append(f"- type={m['type']} type_version={m['type_version']}"
                    f" kind={m['kind']}: {m['title']} - {m['description']}\n"
                    f"  cong_vao={m['cong_vao']} cong_ra={m['cong_ra']}\n"
                    f"  tham_so={luoc_do}")
    mau = ('{"nodes": [{"id","type","type_version","params"}], '
           '"edges": [{"source_node","source_port","target_node",'
           '"target_port","kind"}]}')
    dong += [
        "[CONG_VAO_WORKFLOW] " + json.dumps(input_types or {},
                                            ensure_ascii=False),
        f"[NGAN_SACH] {max(0, int(ngan_sach_credit))} credit",
        "[QUY_UOC_KIND] Canh (`edges[].kind`) chi nhan DUNG mot trong ba gia"
        " tri: DATA (du lieu thuong), CONTROL (chi dieu khien, khong mang"
        " du lieu), ERROR (nhanh xu ly loi). Khong dung ten dinh dang du"
        " lieu (vd 'json') lam kind.",
        "[QUY_UOC_BIEU_THUC] Trong `tham_so` cua danh muc tren, mot tham so"
        " co luoc do `\"type\":\"bieu_thuc\"` (vi du `dieu_kien` cua"
        " core.if, `bieu_thuc` cua core.switch) hoac `\"bang_bieu_thuc\"`"
        " la mot BIEU THUC ngon ngu Sec6 TRAN — KHONG duoc boc trong"
        " `{{ }}`. Viet thang, vi du:"
        " dieu_kien = nodes.fetch_sheet.output.json.status == 'READY'"
        " (KHONG phai \"{{ nodes.fetch_sheet.output.json.status === 'READY'"
        " }}\"). Ngon ngu Sec6 CHI co hai toan tu so sanh bang la `==` va"
        " `!=` — KHONG co `===`/`!==` cua JavaScript, dung se bi tu choi.",
        "[MUC_TIEU] " + (goal or "").strip()[:8000],
        "[DAU_RA] Tra ve DUNG mot object JSON: " + mau
        + " . `type` phai DUNG Y HET mot chuoi trong [DANH_MUC_NODE] (phan"
        " sau `type=`), KHONG duoc noi them `@version` hay bat ky hau to"
        " nao vao `type` — phien ban ghi rieng o truong `type_version`."
        " Voi tham so CHUOI thuong (KHONG phai bieu thuc TRAN da noi o"
        " [QUY_UOC_BIEU_THUC]), tham chieu ket qua buoc truoc bang"
        " {{ nodes.<id>.output.<cong> }}."
        " Khong markdown, khong giai thich.",
    ]
    return "\n".join(dong)


def _nut_tho(obj: dict) -> tuple:
    """Nhận cả `{"nodes","edges"}` lẫn `{"pages":[...]}` model có thể trả."""
    trang = obj.get("pages")
    if isinstance(trang, list) and trang:
        nodes: list = []
        edges: list = []
        for t in trang:
            if not isinstance(t, dict):
                raise LoiSoan("hinh_dang_sai", "pages[] phai la object")
            nodes += list(t.get("nodes") or [])
            edges += list(t.get("edges") or [])
        return nodes, edges
    return obj.get("nodes"), obj.get("edges") or []


def chuan_hoa(raw, *, goal: str = "", budget_max_credit: int = 0) -> dict:
    """Đầu ra model (KHÔNG tin được) → tài liệu draft v3 đúng hình dạng §4.1.

    ⛔ Chỉ kiểm **hình dạng**. Phán quyết về ngữ nghĩa (loại node có thật, tổ
       tiên, cổng, chu trình) thuộc về `bien_dich` — xem `kiem()`.

    ⭐ `goal`/`budget_max_credit` — hai tham số THÊM (25/09, làn `wfk`, vá lần
       hai trong một lần cho CÙNG Lỗi 1). Bản trước chỉ trả `{version, pages}`
       — thiếu đúng ba khoá `CanvasDocument`/`CanvasDocumentV3`
       (`frontend/agent-canvas/src/workflowApi.ts`) cần ở **CẤP TÀI LIỆU**:
       `goal`, `budget_max_credit`, `active_page_id`. `CanvasShell.tsx
       ::soanBangAI` ghi thẳng `dispatch({type:'replace', document:
       fromV3(kq.document)})` — `fromV3()` chỉ spread nguyên tài liệu rồi đổi
       `version`/`pages`, nên khoá nào tài liệu gốc không có thì tài liệu sau
       cũng không có, `undefined`; dòng KẾ NGAY `state.document.goal.trim()`
       (JSX render, không chỉ trong lúc bấm) ném `TypeError` — Playwright
       THẬT (`tests/browser/wf_v2_pa_4180_canvas_bam_that.js`) đỏ đúng ở đây.
       `test_4252` chốt hợp đồng CẤP TÀI LIỆU bằng cách đọc thật khai báo kiểu
       TS (như `test_968` đã làm ở CẤP TRANG cho `_trang_v3`), không phải một
       danh sách ba tên chép tay.
    """
    try:
        obj = extract_json(raw)
    except PlanNormalizeError as loi:
        raise LoiSoan("khong_doc_duoc", str(loi)) from None
    nodes, edges = _nut_tho(obj)
    if not isinstance(nodes, list) or not isinstance(edges, list):
        raise LoiSoan("hinh_dang_sai", "`nodes`/`edges` phai la danh sach")
    if not nodes:
        raise LoiSoan("do_thi_rong", "model khong tra ve node nao")
    if len(nodes) > MAX_NUT:
        raise LoiSoan("qua_nhieu_node", f"{len(nodes)} > {MAX_NUT}")

    ra_nodes, da_co = [], set()
    for i, n in enumerate(nodes):
        if not isinstance(n, dict):
            raise LoiSoan("hinh_dang_sai", f"node {i} phai la object")
        nid = str(n.get("id", ""))
        if not _ID.match(nid):
            raise LoiSoan("id_khong_hop_le", f"id node {nid[:70]!r}", nid[:64])
        if nid in da_co:
            raise LoiSoan("id_trung", nid, nid)
        da_co.add(nid)
        params = n.get("params") or {}
        if not isinstance(params, dict):
            raise LoiSoan("hinh_dang_sai",
                          f"params cua {nid!r} phai la object", nid)
        loai = str(n.get("type", ""))
        ra_nodes.append({
            "id": nid, "type": loai,
            "type_version": int(n.get("type_version") or 1),
            # ⛔ Toạ độ model gửi bị BỎ — xem docstring mô-đun.
            "position": _vi_tri(i), "label": str(n.get("label") or "")[:160],
            "params": params,
            # ⭐ Khoá THÊM cho canvas — xem `_data_canvas.__doc__`. Đây là
            #    hình dạng `frontend/agent-canvas/src/editorState.ts
            #    ::nextNode()` tự dựng cho MỌI node (lõi lẫn app); thiếu nó
            #    `CanvasShell.tsx::displayNodes` đọc `node.data.tool` trên
            #    một `node.data` KHÔNG TỒN TẠI ⇒ `TypeError` giữa render.
            #    ⛔ KHÔNG thay `type`/`params` top-level bằng khoá này — cổng
            #    biên dịch (`bien_dich._node`/`_node_loi`) đọc đúng hai khoá
            #    top-level đó, không đụng `data` (test_4250 ghim cả hai).
            "data": _data_canvas(loai, params),
            "credential_ref": str(n.get("credential_ref") or ""),
            "settings": dict(n.get("settings") or {}),
        })

    ra_edges = []
    for i, c in enumerate(edges):
        if not isinstance(c, dict):
            raise LoiSoan("hinh_dang_sai", f"edge {i} phai la object")
        e = _canh_v3(c)
        e["id"] = e["id"] or f"e{i + 1}"
        e["kind"] = str(c.get("kind") or "DATA")
        e["condition"] = str(c.get("condition") or "")
        ra_edges.append(e)

    return {"version": SCHEMA_DRAFT,
            "goal": str(goal or ""),
            "budget_max_credit": max(0, int(budget_max_credit or 0)),
            "active_page_id": TRANG_MAC_DINH,
            "pages": [{"id": TRANG_MAC_DINH, "name": "Trang 1",
                       "nodes": ra_nodes, "edges": ra_edges,
                       "viewport": {"x": 0, "y": 0, "zoom": 1}}]}


def _bien_dich(document: dict, cong_cu: Optional[dict]) -> tuple:
    """`(graph | None, tuple lỗi)` — đi qua ĐÚNG cổng publish, không bản sao."""
    try:
        return bien_dich.bien_dich(document, cong_cu=cong_cu), ()
    except bien_dich.LoiBienDich as loi:
        return None, ({"ma": loi.ma, "thong_diep": str(loi),
                       "node_id": loi.node_id},)


def kiem(document: dict, *, cong_cu: Optional[dict] = None) -> tuple:
    graph, loi = _bien_dich(document, cong_cu)
    return graph is not None, loi


def soan_draft(db, *, goal: str, ngan_sach_credit: int,
               cong_cu: Optional[dict] = None,
               input_types: Optional[dict] = None,
               llm_call: Optional[Callable[[str], object]] = None) -> dict:
    """Một lượt soạn: model → draft v3 → **cổng publish**. ⛔ KHÔNG publish."""
    from platform_core.agent import planner

    muc = danh_muc(cong_cu=cong_cu)
    prompt = build_prompt(goal, muc=muc, ngan_sach_credit=ngan_sach_credit,
                          input_types=input_types)
    raw = (llm_call(prompt) if llm_call is not None
           else planner.goi_model(db, prompt))
    goal_sach = (goal or "").strip()
    ngan_sach_sach = max(0, int(ngan_sach_credit))
    document = chuan_hoa(raw, goal=goal_sach, budget_max_credit=ngan_sach_sach)
    graph, loi = _bien_dich(document, cong_cu)
    return {"document": document, "graph": graph, "hop_le": graph is not None,
            "loi": loi, "goal": goal_sach,
            "ngan_sach_credit": ngan_sach_sach}


__all__ = ["BUOC_X", "BUOC_Y", "LoiSoan", "MAX_NUT", "SCHEMA_DRAFT",
           "TRANG_MAC_DINH", "build_prompt", "chuan_hoa", "danh_muc", "kiem",
           "soan_draft"]
