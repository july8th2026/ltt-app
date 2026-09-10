# 01 — KIẾN TRÚC LTTSTUDIOSAPP HIỆN TẠI (đo thật, không đọc tài liệu)

> **Phạm vi.** Đây là bước 1 của cuộc khảo sát *LTT WORKFLOW V2*. Tài liệu này
> KHÔNG so sánh với dự án mã nguồn mở nào, KHÔNG đề xuất kiến trúc mới, và
> KHÔNG sửa một dòng mã sản phẩm nào. Nó chỉ trả lời một câu: **hôm nay hệ
> thống thật sự là gì.**
>
> **Cây đo:** `D:\LTTSTUDIOSAPP` · nhánh `admin-mvp-v3` · commit `9e73bf1f`
> **Bản đang chạy trên production:** commit `a365fa80` (`/health/version`,
> `build_luc` 2026-09-07T15:08:56, `asset_ver` `ae960b57`) — **chậm hơn cây đo
> đúng 1 commit**.
> **Ngày đo:** 2026-09-07.
>
> **Chuẩn bằng chứng.** Mỗi kết luận quan trọng gắn nhãn:
> `CONFIRMED` (chạy được / test xanh) · `HIGH` (đọc thẳng mã, nhiều điểm khớp) ·
> `INFERRED` (suy luận kiến trúc) · `UNKNOWN` (chưa đủ bằng chứng).

---

## 0. TÓM TẮT ĐIỀU HÀNH (đọc mục này trước)

LTTSTUDIOSAPP **không phải** một workflow engine có thêm vài app. Nó là một
**nền tảng job SaaS trưởng thành** (hàng đợi, credit, GPU lease, Public API,
webhook, multi-tenant) mà **trên đó** có gắn một **lớp orchestration mỏng**
(Agent/Canvas, ~1.843 dòng) mới ở mức MVP.

Hai lớp này có độ chín **hoàn toàn khác nhau**, và đó là phát hiện quan trọng
nhất của tài liệu này:

| Lớp | Dòng mã | Độ chín đo được |
|---|---|---|
| Hàng đợi job + credit + GPU + Public API | ~44.000 (`platform_core/`) | Sản phẩm thật, đang thu tiền, có bánh cóc test dày |
| Agent / Canvas / Plan / Executor | **1.843** (`platform_core/agent/`) | MVP, mặc định **TẮT** ở production, nhiều nguyên hàm còn thiếu |

🔴 **Và một dữ kiện đổi cả bài toán** (Phụ lục A, đo từ log production 28 ngày):
**lớp orchestration đó chưa từng chạy một lần nào trên production.** 0 job
`agent.advance` trong 37.963 dòng log. Nghĩa là không có khách nào đang đứng
trên engine cũ ⇒ **ràng buộc "không được viết lại một phát" KHÔNG áp dụng cho
tầng executor**, nhưng vẫn áp dụng đầy đủ cho tầng job/credit/GPU đang thu tiền.

Ba con số đo được, mỗi con số phủ định một giả định thường gặp:

1. **Executor chỉ chạy tối đa 4 *step* cùng lúc, bất kể đồ thị rộng bao nhiêu.**
   Đo: một plan 100 step độc lập, tick đầu tiên tạo đúng **4** child job.
   (`max_parallel: int = 4`, `platform_core/agent/executor.py:238`)
2. **Mỗi tick tốn `31 + N` câu SQL với N là số step trong plan**, và tick lặp
   **mỗi 2 giây** suốt vòng đời run. Đo được: 5 step → 36 câu; 100 step → 131
   câu.
3. **Canvas nhiều page, nhưng chỉ page đang mở được thi hành.** Node ở page
   khác không bao giờ chạy. (`_page_graph` trả về `active` page,
   `platform_core/agent/workflows.py:97`)

Kết luận định hướng cho V2: **phần cần giữ và phần cần viết lại nằm ở hai lớp
khác nhau, và ranh giới giữa chúng đã khá sạch.** Chi tiết ở §11–§13.

---

## 1. BẢN ĐỒ TỔNG THỂ

```
                             NGƯỜI DÙNG (web)                 KHÁCH API (/api/v1)
                                    │                                  │
                                    ▼                                  ▼
                        server/ (FastAPI, 13.997 dòng)      platform_core/public_api/
                        auth · i18n · CSRF · access          12.475 dòng · 24 route
                                    │                        đóng băng (inventory.py)
                                    │                                  │
        ┌───────────────────────────┼──────────────────────────────────┘
        │                           │
        ▼                           ▼
   apps/<slug>/               platform_core/registry.py  ◄── HỢP ĐỒNG DUY NHẤT
   16 app · 46.862 dòng       AppManifest + ToolSpec           (1.228 dòng)
   manifest/routes/jobs/          (nền tảng KHÔNG biết
   services/tables                 tên app nào tồn tại)
        │
        │  ┌──────────────── LỚP ORCHESTRATION (mỏng, MVP) ────────────────┐
        │  │  platform_core/agent/ — 1.843 dòng                            │
        │  │                                                              │
        │  │   planner.py ──► normalizer.py ──► Plan v1 (JSON)             │
        │  │   workflows.py  Canvas v2 (JSON) ◄──► Plan v1                 │
        │  │   validator.py  kiểm tất định, không LLM, không tiền          │
        │  │   budget.py     quote → hold → ensure_can_spend → settle      │
        │  │   executor.py   tick() — DAG scheduler, mỗi lần 1 bước        │
        │  │   verifier.py   technical / face_identity / vlm_judge         │
        │  └──────────────────────────┬───────────────────────────────────┘
        │                             │  submit_child()
        ▼                             ▼
   ╔══════════════════════════════════════════════════════════════════════╗
   ║  platform_core/jobs.py — HÀNG ĐỢI (bảng `jobs`, PostgreSQL)          ║
   ║  submit · claim(FOR UPDATE SKIP LOCKED) · heartbeat · complete/fail  ║
   ║  reclaim_orphans · dedupe_key · fair-share theo account · aging      ║
   ╚══════════════════════════════════════════════════════════════════════╝
                                      │
                                      ▼
   ╔══════════════════════════════════════════════════════════════════════╗
   ║  platform_core/job_runner.py — WORKER (1.658 dòng, dịch vụ riêng)    ║
   ║  admission lease (máy B) → GPU lease → handler → complete/fail       ║
   ║  + vòng bảo trì dưới singleton lease (webhook, metrics, dọn, canary) ║
   ╚══════════════════════════════════════════════════════════════════════╝
        │                   │                    │                  │
        ▼                   ▼                    ▼                  ▼
   credit.py           gpu_lease.py        storage.py         public_api/
   sổ append-only      lease theo UUID     Local | R2         webhooks.py
   hold/settle/refund  card, heartbeat     key dạng chuỗi     HMAC + retry
```

---

## 2. (A) APP DISCOVERY / REGISTRY

**Nguồn:** `platform_core/registry.py` (1.228 dòng).

### 2.1 App là gì

`AppManifest` là **bản khai dữ liệu bất biến** (frozen dataclass). Nền tảng
quét `apps/*/manifest.py`, đọc biến `MANIFEST`. Nguyên tắc ghi thẳng trong
docstring: *"Nền tảng KHÔNG được biết tên app nào tồn tại."* Có test cưỡng chế
(`test_60`, `test_147_layering`). `CONFIRMED`

Manifest khai (trích những trường ảnh hưởng tới workflow):

| Trường | Ý nghĩa cho Workflow V2 |
|---|---|
| `job_types` | tập làn scheduler app sở hữu |
| `requires` | `api`/`ffmpeg`/`gpu`/`browser` → lọc worker lúc `claim` |
| `credit_cost(params) -> int` | **giá là một HÀM, không phải một số** |
| `gpu_vram_mb{job_type: MB}` | sàn xếp chỗ GPU |
| `max_runtime_s{job_type: s}` | trần treo |
| `cho_tai_nguyen_s{job_type: s}` | giãn cách thử lại khi tài nguyên bận |
| `so_lan_thu{job_type: n}` | số lần thử tối đa |
| `bao_tri` + `bao_tri_moi_giay` | việc nền định kỳ, chạy dưới singleton lease |
| `bang_gia()` / `suc_khoe()` / `hop_dong_cong_khai` | thu thập ngược từ app |
| `tools: tuple[ToolSpec]` | năng lực cho Agent/Canvas |
| `table_prefix` | bảng CSDL riêng của app |

⭐ **Điểm mạnh nhất của toàn hệ thống.** Hợp đồng này đã bị *ép* mở rộng nhiều
lần bởi sự cố thật, và mỗi lần mở rộng đều được ghi lý do ngay trong mã (ví dụ
`cho_tai_nguyen_s` sinh ra vì một hằng số toàn cục 20 giây làm mất 75% thông
lượng của một app job-5-giây). Đây là một hợp đồng **đã trả giá**, không phải
một hợp đồng thiết kế trên giấy. `HIGH`

### 2.2 Tool là gì — và `ToolSpec` là gì

`ToolSpec` (frozen dataclass, `registry.py:112`) là **metadata thuần**, KHÔNG
chứa handler. `CONFIRMED`

```
name              "video.generate"       — <domain>.<action>, regex ép
job_type          "taovideo.render"      — làn MẶC ĐỊNH trong hàng đợi
params_schema     dict[str, rule]        — đầu vào
returns           dict[str, port_type]   — đầu ra
verifiable        tuple                  — verifier tool chấp nhận
customer_visible  bool                   — hiện trong palette Canvas
api_exposed       bool + api_contract    — cửa /api/v1 (mặc định TẮT)
admission_resource / admission_slots     — slot tài nguyên dùng chung
sync_executor     "module:attr"          — đường chạy đồng bộ (chỉ ltt_llm dùng)
tuy_chon_dong     {"field": "module:fn"} — enum động THEO NGƯỜI DÙNG
job_type_by / job_type_lanes             — chọn làn theo tham số
```

**`ToolSpec` là hợp đồng runtime, không phải metadata trang trí.** Bằng chứng:
`lane_for()` quyết định VRAM giữ chỗ; `admission_slots` quyết định lease;
`credit_for(job_type, params)` quyết định tiền. `CONFIRMED`

**Đếm thật:** **15 `ToolSpec`** trên **11/16 app**. `CONFIRMED`

```
anhnoibo 1 · autosubvideo 1 · chatltt 2 · ltt_llm 1 · ltt_voice 1
prompt_ai_ommi 2 · taoanh 2 · taoclipngan 1 · taovideo 1 · thumbnail 1
upscalevideo 2
(agent, chataistudio, nexus, qualitylab, vps: 0 tool)
```

Tên tool hiện có: `chatltt.nghien_cuu`, `chatltt.trich_tep`,
`image.batch_generate`, `image.generate`, `image.ltt`, `image.thumbnail`,
`image.upscale`, `speech.ltt`, `story.storyboard`, `text.chat`,
`text.prompt_package`, `video.generate`, `video.short_clips`, `video.subtitle`,
`video.upscale`.

### 2.3 Hệ kiểu tham số vs hệ kiểu cổng — **hai bảng khác nhau**

`registry.py:66` và `registry.py:78`:

```
TOOL_PARAM_TYPES (13)  string int number bool enum model_ref text
                       image image[] video video[] audio json json[]
TOOL_PORT_TYPES  (9)   text image image[] video video[] audio json json[] model_ref
```

`validator._port_for_param()` gộp:
`string|text|enum → text`, `int|number|bool → json`, còn lại giữ nguyên.

⚠️ **Hệ quả đo được:** một cổng `int` và một cổng `dict` đều là `json`, nên
validator **không phân biệt** được chúng khi nối dây. Đây là mất mát thông tin
kiểu ngay tại biên Canvas↔Plan. `CONFIRMED` (đọc
`platform_core/agent/validator.py:38-45`)

### 2.4 Ba cổng độc lập cho Public API

Một tool ra `/api/v1` chỉ khi: `api_exposed=True` **và** `api_contract` đủ
**và** operator bật trong `LTT_PUBLIC_API_TOOLS`. Mặc định fail-closed. Xác
nhận bằng canary production: `/api/v1` đòi khoá, đúng ý muốn. `CONFIRMED`

---

## 3. (B) MÔ HÌNH WORKFLOW — Canvas, Plan, và chỗ nối giữa chúng

**Nguồn:** `platform_core/agent/workflows.py` (314 dòng).

### 3.1 Hai biểu diễn, một chiều chân lý

```
   AgentWorkflow.document  (Canvas v2 JSON)   ◄── NGUỒN CHÂN LÝ của trình soạn
            │
            │  canvas_to_plan()   ← dựng lại ở SERVER mỗi lần cần
            ▼
        Plan v1 (JSON)  ──► validator ──► quote ──► AgentRun.plan (đóng băng)
            ▲
            │  plan_to_canvas()   ← chỉ dùng khi NHẬP kết quả planner
```

`AgentWorkflow` giữ cả `document` (v2, lossless) **lẫn** các cột chiếu
`nodes`/`edges`/`viewport` (v1) — cố ý, để rollback vẫn đọc được (chú thích
`models.py:511`, "Q62"). `HIGH`

### 3.2 Cấu trúc Canvas v2

```
CanvasDocument { version:2, goal, budget_max_credit, active_page_id, pages[] }
  CanvasPage  { id, name, nodes[], edges[], viewport, frames[], notes[],
                comments[], view{grid,connections,minimap} }
    CanvasNode { id, type:'tool', position{x,y}, label?, data{} }
    CanvasEdge { id, source, target, sourceHandle?, targetHandle?,
                 data{condition:'success'|'error', modality, running} }
```

Trần cứng: `MAX_PAGES=20`, `MAX_FRAMES_PER_PAGE=50`,
`MAX_ANNOTATIONS_PER_PAGE=200`, `MAX_CANVAS_BYTES=512 KiB`,
`MAX_JSON_DEPTH=20`. `CONFIRMED`

### 3.3 🔴 PHÁT HIỆN LỚN #1 — chỉ page đang mở được thi hành

`_page_graph()` (`workflows.py:60-99`) trả về `nodes/edges` của **`active`
page** rồi mới đưa cho `canvas_to_plan`. Node ở 19 page còn lại **không bao giờ
vào Plan, không bao giờ chạy, không báo lỗi**. `CONFIRMED`

Đây không phải bug — nó nhất quán: page là *khái niệm của trình soạn*, không
phải subgraph. Nhưng nó có nghĩa là **hôm nay LTT chưa có subworkflow ở bất kỳ
hình thức nào**, và "nhiều page" dễ bị hiểu nhầm là có.

### 3.4 🔴 PHÁT HIỆN LỚN #2 — Edge KHÔNG mang dữ liệu

Đọc `canvas_to_plan` (`workflows.py:130-170`):

* Edge chỉ đóng góp **thứ tự**: `after` (condition `success`) và `after_error`
  (condition `error`). **`sourceHandle`/`targetHandle` bị VỨT BỎ.**
* Dữ liệu thật chảy qua **chuỗi tham chiếu trong `node.data.params`**, dạng
  `"$<step_id>.<port>"`, khớp regex
  `^\$(input|[a-z][a-z0-9_-]{0,31})\.([a-z][a-z0-9_]*)$`.

Nghĩa là hệ thống có **hai biểu diễn song song của cùng một cạnh dữ liệu**:

| | Ai giữ | Ai đồng bộ |
|---|---|---|
| Cạnh trực quan (handle→handle) | `page.edges` | trình duyệt |
| Cạnh dữ liệu thật (`$n.port`) | `node.data.params` | trình duyệt |

Frontend giữ chúng khớp nhau bằng tay: `clearEdgeReferences()`
(`frontend/agent-canvas/src/editorState.ts:66`) xoá tham chiếu khi xoá cạnh;
`insertToolOnEdge` viết lại tham chiếu khi chèn node giữa cạnh. `CONFIRMED`

Validator bắt được **một** chiều lệch: tham chiếu `$a.x` mà `a` không có trong
`after` → lỗi `reference_order`. Nhưng chiều còn lại **không** bị bắt: một cạnh
không kèm tham chiếu là hợp lệ và trở thành **cạnh điều khiển thuần**
(control edge) — một năng lực có thật nhưng **không ai khai là có**, và không
có cách nào vẽ nó có chủ đích trên Canvas. `HIGH`

⇒ Đây chính là chỗ mục 3.4 của đề bài ("DATA FLOW VS CONTROL FLOW") sẽ phải
quyết: hôm nay LTT **đã** có control edge, chỉ là do tai nạn chứ không do thiết kế.

### 3.5 Tính không mất mát của chuyển đổi

| Chiều | Mất gì |
|---|---|
| `Canvas → Plan` | position, label, page, frame, note, comment, viewport, **handle của edge** |
| `Plan → Canvas` | không mất trường thi hành nào; position được **sinh ra** (`x = index*280, y = 0`) |
| `Canvas → Plan → Canvas` | **CÓ MẤT** toàn bộ layout/tổ chức |

Hệ thống tránh mất mát bằng cách **không bao giờ đi vòng đó**: `document` là
chân lý, Plan luôn là *dẫn xuất*. `plan_to_canvas` chỉ dùng cho đầu ra planner.
`CONFIRMED`

### 3.6 Phòng thủ ở biên client

`_CLIENT_FORBIDDEN` = `owner_id, user_id, estimated, price, credit_cost,
credential, secret, csrf_token, callback_url, webhook_url, storage_key` — quét
đệ quy toàn Canvas, từ chối nếu khách gửi lên. `owner_id` được server tiêm
**sau** khi khoá run (`runs.submit_child`). `CONFIRMED`

---

## 4. (C) VALIDATOR

**Nguồn:** `platform_core/agent/validator.py` (261 dòng). Docstring:
*"Deterministic Plan v1 validator. No LLM, network, job or credit writes."*

### 4.1 Trần cứng

```
MAX_STEPS  = 100      MAX_FANOUT = 4      MAX_RETRY = 2
_ON_FAIL   = {retry_same, refine, regenerate, switch_model}
```

### 4.2 Danh mục kiểm — đo thật

| # | Kiểm | Mã lỗi |
|---|---|---|
| 1 | `version == 1` | `version` |
| 2 | 1 ≤ số step ≤ 100 | `steps` |
| 3 | id thiếu/trùng | `step_id` |
| 4 | `after` / `after_error` là list[str] | `after` |
| 5 | một dep không được vừa success vừa error | `branch` |
| 6 | dep trỏ step không tồn tại | `dependency` |
| 7 | **chu trình** (DFS 3 màu trên `after ∪ after_error`) | `cycle` |
| 8 | tool tồn tại **và người dùng có quyền app** | `tool` |
| 9 | payload không chứa URL/đường dẫn/secret (`_unsafe_payload`) | `unsafe_param` |
| 10 | artifact (`image/video/audio/...[]`) **phải** là `$ref` | `artifact_ref` |
| 11 | cú pháp tham chiếu | `reference` |
| 12 | **thứ tự**: nguồn tham chiếu phải nằm trong `after` | `reference_order` |
| 13 | **kiểu cổng** khớp | `port_type` |
| 14 | tham số hợp `params_schema` (min/max/enum/max_length) | `params` |
| 15 | 1 ≤ fanout ≤ 4 | `fanout` |
| 16 | 0 ≤ max_retry ≤ 2 | `retry` |
| 17 | `on_fail` trong tập cho phép | `on_fail` |
| 18 | verifier tồn tại **và** tool khai `verifiable` | `verify` |
| 19 | tính được giá | `price` |
| 20 | tổng ≤ `budget_max_credit` | `budget` |
| 21 | tổng ≤ số dư | `balance` |

`CONFIRMED` — 13 test ở `tests/test_90_agent_planner_validator.py`, xanh.

### 4.3 Công thức trần chi phí — và ý nghĩa của nó

```
maximum(step) = (credit_for(tool, params) + verifier_cost(verify))
                × fanout × (1 + max_retry)
total         = Σ maximum(step)
```

⭐ Đây là **tài sản kiến trúc lớn nhất của lớp Agent**: **mức phơi nhiễm tối đa
của khách hàng được tính TRƯỚC khi chạy, tất định, không cần LLM.** Đề bài mục
3.15 yêu cầu đúng tính chất này — LTT **đã có**. `CONFIRMED`

Cái giá phải trả cũng đo được: vì trần phải hữu hạn, `fanout ≤ 4` và
`max_retry ≤ 2` là *hằng số cứng*, và **không có ForEach** (§8.4).

### 4.4 Điểm yếu của validator

* Chỉ chấp `version == 1`. Không có đường di trú schema.
* `_placeholder()` thay giá trị thật bằng giá trị giả để gọi
  `validate_tool_params` — nghĩa là **ràng buộc min/max của một giá trị đến từ
  upstream không bao giờ được kiểm**. Chỉ kiểm được kiểu. `HIGH`
* Không kiểm `_unsafe_payload` cho toàn bộ Plan, chỉ cho `params`.
* Đệ quy `_has_cycle` không giới hạn độ sâu — với 100 step thì an toàn; đó là
  lý do `MAX_STEPS` phải nhỏ. `INFERRED`

---

## 5. (D) EXECUTOR — lần theo một workflow chạy thật

**Nguồn:** `platform_core/agent/executor.py` (334 dòng), điểm vào duy nhất:
`tick(db, run_id, user_id, max_parallel=4, probe, judge, face_compare, retry_adapter)`.

### 5.1 Không có vòng lặp — chỉ có tick, và tick tự hẹn lại chính nó

```
POST /agent/api/workflows/{id}/runs           (người dùng bấm Chạy)
   └─ _prepare_run: validate → create_run_capped → set_quote
   └─ POST .../approve → budget.approve → credit.giu_cho(estimated)
   └─ _enqueue_advance → jobs.submit(job_type="agent.advance")
                                       │
                                       ▼
                          WORKER nhặt job "agent.advance"
                          apps/agent/jobs.py:handle()
                             ├─ executor.tick(...)
                             └─ nếu run VẪN running:
                                submit job "agent.advance" kế tiếp
                                next_run_at = now + 2 GIÂY
```

`CONFIRMED` (`apps/agent/jobs.py:23-46`)

⇒ **Đây là một vòng polling bền, không phải một scheduler hướng sự kiện.**
Ưu điểm: sống sót qua crash worker, restart, deploy — trạng thái nằm hết trong
CSDL. Nhược điểm: mọi run đang chạy **đóng góp một job vào hàng đợi mỗi 2 giây**,
và mỗi tick trả giá SQL tuyến tính theo số step (§5.6).

### 5.2 Một tick làm gì (theo đúng thứ tự trong mã)

```
1. runs.get_owned(lock=True)          ← SELECT ... FOR UPDATE trên agent_runs
2. nếu trạng thái terminal → trả về ngay
3. _sync_children()                    ← đọc job con, cập nhật checkpoint
     • có job error       → step = "error"
     • đủ fanout & all done → chạy verifier → "done" | "retry_needed" | "error"
     • còn lại            → "submitted"
4. _advance_branch_states()            ← lan truyền "skipped" tới bão hoà
5. _terminal_status()                  ← mọi step terminal chưa? lỗi có handler chưa?
     • nếu có → budget.settle(actual_cost) và KẾT THÚC
6. duyệt step theo THỨ TỰ KHAI BÁO:
     • dừng nếu active >= max_parallel (mặc định 4)
     • bỏ qua nếu đã có state (trừ "retry_needed")
     • điều kiện READY:  after ⊆ done   VÀ   after_error ⊆ errored
     • resolve_params: thay "$x.y" bằng giá trị thật từ checkpoint
     • nếu fanout==1 và cache bật → tìm job cũ trùng params → dùng lại, cost 0
     • budget.ensure_can_spend(actual_hiện_tại + chi_phí_kế)
     • submit `fanout` child job, dedupe_key = agent:{run}:v{ver}:{sid}:a{n}:{i}
     • checkpoint[sid] = {"status":"submitted", job_ids, attempt}
7. run.checkpoint = checkpoint; db.flush()
```

### 5.3 🔴 PHÁT HIỆN LỚN #3 — song song bị chặn ở 4, và đếm theo *step*

```python
active = sum(state.get("status") == "submitted"
             for state in (run.checkpoint or {}).values())
...
if active >= max(1, int(max_parallel)):
    break
```

* `max_parallel` mặc định **4** và `apps/agent/jobs.py` **không truyền tham số
  này**, nên production luôn là 4. `CONFIRMED`
* `active` đếm **step**, không đếm job. Một step `fanout=4` chiếm **1** suất.
  Nên số job đồng thời thật có thể tới 16, còn số *nhánh* thì tối đa 4.
* **Đo trực tiếp:** plan 100 step độc lập → tick đầu tạo đúng **4** child job.

Trả lời câu hỏi §3.5 của đề bài (`A → {B, C, D}` có chạy song song không?):
**CÓ, nhưng trần là 4 nhánh cho toàn bộ run**, và không có cách nào khai khác
đi từ Canvas. `CONFIRMED`

### 5.4 Join / merge

Chỉ có **một** ngữ nghĩa: **ALL**. Step `j` với `after = [a, b]` chỉ READY khi
cả `a` và `b` đều `done`. Không có `ANY`, `N-of-M`, `FIRST_SUCCESS`, barrier.
`CONFIRMED` (test `test_hai_nhanh_song_song_join_cho_du_va_fanout`: `j` không
sinh child cho tới khi `b` xong).

Fan-in dữ liệu có: `_aggregate()` — nếu step có 1 job thì output là giá trị;
nếu nhiều job (fanout) thì mỗi khoá thành **list**. Kiểu đổi âm thầm theo
fanout. `HIGH`

### 5.5 Nhánh, lỗi, và "skipped"

`_advance_branch_states()` lan truyền tới bão hoà (`while changed`):

* step có **success dep** ở trạng thái `error`/`skipped` → `skipped`
* step có **error dep** ở trạng thái `done`/`skipped` → `skipped`

⇒ Đây là **routing bằng cạnh có điều kiện**, không phải node Router. Ngữ nghĩa
nhánh nằm trên `edge.data.condition ∈ {success, error}`. `CONFIRMED`

`_terminal_status()`: run thành `error` **chỉ khi** có step lỗi mà **không**
handler `after_error` nào của nó `done`. Có handler chạy xong → run `done`.
`CONFIRMED` (test `test_error_branch_runs_handler_skips_success_path_and_settles_done`)

### 5.6 🔴 PHÁT HIỆN LỚN #4 — chi phí SQL mỗi tick tuyến tính theo số step

**Đo thật** (script `do_tick_query.py`, đếm `before_cursor_execute` trên engine,
SQLite, plan gồm N step độc lập, tick đầu tiên):

| N step | Câu SQL / 1 tick | Child job tạo ra |
|---:|---:|---:|
| 5 | 36 | 4 |
| 20 | 51 | 4 |
| 50 | 81 | 4 |
| 100 | **131** | 4 |

⇒ Hồi quy sạch: **SQL ≈ 31 + N**. `CONFIRMED`

Nguồn của N: `_sync_children()` gọi `runs.children(db, run, step_id=sid)` **một
lần cho mỗi step** (`executor.py:79`) — N+1 kinh điển. Ngoài ra trong vòng lặp
submit còn `actual_cost(run, runs.children(db, run))` **mỗi step READY**
(`executor.py:296`), tức thêm một truy vấn toàn bộ job con cho mỗi lần submit.

Nhân với nhịp: một run 100 node đang chạy tiêu **~65 câu SQL/giây**, mãi mãi,
kể cả khi không có gì thay đổi. 50 run đồng thời ⇒ ~3.300 câu/giây chỉ để hỏi
"có gì mới không". `INFERRED` (phép nhân từ số đo)

### 5.7 Cache — mạnh và nguy hiểm

`_cached_result()` (`executor.py:158`): với step `fanout==1`, quét **50 job
`done` gần nhất của cùng user + cùng `job_type`**, so sánh `dict(params) ==
{**params, owner_id}` , rồi kiểm `storage.exists()` cho mọi giá trị trông giống
đường dẫn media.

* Ưu: tránh trả tiền lại cho việc y hệt; `_result_available` chặn "cache trỏ
  vào file đã bị dọn".
* Nhược: **quét tuyến tính 50 dòng + N lời gọi storage cho MỖI step submit**.
  Với R2 (mạng) thì đây là I/O ngoài trong đường nóng của scheduler. `HIGH`
* Nhược: cache **bật mặc định** (`_cache_enabled` trả `True` khi không có sự
  kiện `workflow_source`), và điều kiện trùng là *bằng nhau tuyệt đối của
  params* — nên một tool không tất định (sinh ảnh có seed ngẫu nhiên nằm ngoài
  params) sẽ trả lại **kết quả cũ** cho khách. `INFERRED`

### 5.8 Retry — hai tầng, tách bạch có chủ ý

| Tầng | Ai làm | Đếm ở đâu |
|---|---|---|
| Runtime/provider | `jobs.fail()` — backoff `10 × 2^(n-1)`, trần 600 s | `Job.attempts` |
| Ngữ nghĩa (verifier) | `executor` — `retry_same`/`refine`/`regenerate`/`switch_model` | `checkpoint[sid].attempt` |

Chú thích ngay tại chỗ submit: `max_attempts=1` — *"Provider/runtime retry is
separate from verifier regeneration."* `CONFIRMED`

⚠️ `refine` và `switch_model` **cần `retry_adapter`**, và
`apps/agent/jobs.py:advance()` **không truyền adapter nào**. Nên trong production
hai chính sách đó luôn rơi vào nhánh `retry_unavailable` → step thành `error`.
Chỉ `tools/agent_browser_server.py` truyền `judge`. `CONFIRMED` (đọc
`executor.py:270-283` + `apps/agent/jobs.py:16`)

⇒ **Hai trong bốn giá trị `on_fail` hợp lệ theo validator là cửa giả trên đường
production.**

### 5.9 Resume sau crash

`tick()` được thiết kế idempotent: mọi trạng thái nằm ở `AgentRun.checkpoint`
(JSON) + bảng `jobs`; step đã có state thì bỏ qua; `dedupe_key` chặn submit
trùng. Test `test_restart_va_tick_lap_khong_submit_lai_step` gọi `tick` bốn lần
và khẳng định vẫn đúng **1** child. `CONFIRMED`

⚠️ Nhưng đây là **resume mức step**, không phải durable execution mức bước:
nếu worker chết *giữa* handler, job đó đi theo `reclaim_orphans` (5 phút không
heartbeat) → `fail()` hoặc `mark_ambiguous()`. Không có replay lịch sử, không
có event sourcing.

### 5.10 Ranh giới transaction

`tick()` **không commit**. Nó `flush()`; caller quyết định. `apps/agent/jobs.py`
commit một lần ở cuối. Toàn bộ một tick — sync children, verify, settle, submit
child — nằm trong **một transaction** giữ khoá `FOR UPDATE` trên `agent_runs`.

⚠️ `verifier.verify()` được gọi **bên trong** transaction đó, và verifier
`vlm_judge` gọi model (mạng). ⇒ **một lời gọi mạng nằm trong một transaction
đang giữ khoá dòng.** `HIGH` — đây là loại lỗi mà job_runner đã cố tình tránh
cho handler (docstring `job_runner.py:11-15`) nhưng lớp Agent lại tái phạm.

---

## 6. (E) HỆ THỐNG JOB — phần trưởng thành nhất

**Nguồn:** `platform_core/jobs.py` (478) + `job_runner.py` (1.658) +
`models.Job`.

### 6.1 Vòng đời

```
queued ──claim(FOR UPDATE SKIP LOCKED)──► running ──► done
   ▲                                         │
   │                                         ├──► error   (hết lượt)
   ├──fail(retry, backoff 10·2^n ≤600s)──────┤
   ├──defer_resource(không tiêu lượt)────────┤    ("đang bận")
   ├──_tra_ve_hang_doi (GPU bận)─────────────┤
   └──reclaim_orphans (5' không heartbeat)───┘
                                             └──► cancelled
```

### 6.2 Những thứ đã có mà một workflow engine thường phải tự làm

| Năng lực | Mã |
|---|---|
| Chống nhặt trùng nhiều worker | `SELECT ... FOR UPDATE SKIP LOCKED` |
| Chống double-submit | `dedupe_key` + trạng thái chưa terminal |
| Job mồ côi | `heartbeat_at` + `reclaim_orphans` (5 phút) |
| **Công bằng đa tenant** | aging 5' → account chưa từng phục vụ → `last_claimed_at` → FIFO. **Không có giá tiền trong thứ tự** |
| Định tuyến theo năng lực | `manifest.requires ⊆ worker capabilities` |
| Phân loại lỗi | `LoiNguoiGoi` (đừng thử lại) vs `DangBan` (thử lại, đừng đếm) |
| **Bán trạng thái provider** | `dispatched` → `completed`/`rejected`/**`ambiguous`** |
| Lineage | `parent_id`, `plan_id`, `step_id`, `correlation_id`, `retry_of_id` |
| Timeline | `JobEvent` append-only, tách `public_message` / `details` nội bộ |
| Hết hạn nội dung | `content_expired_at` — hàng vẫn còn làm bằng chứng cho sổ tiền |
| Index đúng câu claim | `ix_jobs_claim`, `ix_jobs_admission_queue`, `ix_jobs_fairness` |

⭐ **`provider_state = ambiguous` đáng chú ý riêng.** Khi worker chết *sau khi*
đã gửi request tới provider, job KHÔNG được tự thử lại — nó thành terminal có
lý do. Đây chính là bài toán "exactly-once với side effect ngoài" ở mục 3.22 đề
bài, và LTT đã giải theo hướng đúng (at-most-once cho side effect + báo cho
người dùng). `CONFIRMED`

### 6.3 Điều KHÔNG có

* Không có ưu tiên (priority) — chỉ có công bằng.
* Không có "job phụ thuộc job" ở tầng hàng đợi; phụ thuộc chỉ tồn tại ở tầng
  Agent (checkpoint).
* Không có delayed-until-event; chỉ `next_run_at` (thời gian).
* Không có hàng đợi thứ hai (Redis/Kafka) — cố ý, docstring nói rõ.

---

## 7. (F) CREDIT — ai sở hữu việc thu tiền

**Nguồn:** `platform_core/credit.py` (702), `agent/budget.py` (136),
`billing.py`, `billing_math.py`.

### 7.1 Bốn nguyên tắc bất di bất dịch (docstring `credit.py`)

1. Số dư = `SUM` của sổ. Không có ô `balance` bị ghi đè.
2. Sổ **chỉ ghi thêm**. Sai thì ghi bút toán bù.
3. Giữ chỗ / quyết toán / hoàn nằm trong **transaction của caller**.
4. Quyết toán/hoàn **idempotent theo job**.

Chống double-spend bằng `pg_advisory_xact_lock` theo user. `CONFIRMED`

### 7.2 🔴 PHÁT HIỆN LỚN #5 — có HAI mô hình thu tiền song song

```
ĐƯỜNG JOB ĐƠN (web + /api/v1)          ĐƯỜNG AGENT RUN
─────────────────────────────          ────────────────────────────
credit.giu_cho(job_id, ước tính)       budget.approve
   ↓                                     → credit.giu_cho(RUN_ID, estimated)
worker chạy                                ↓
   ↓                                     mỗi step: ensure_can_spend(
credit.quyet_toan(job_id, thật)            actual_cost + next_cost) ≤ estimated
   ↓                                       ↓
credit.hoan(job_id) nếu lỗi              child job submit với credit_cost=0
                                           ↓
                                         budget.settle(RUN_ID, actual_cost)
```

Hai đường **không** lồng nhau: child job của Agent **không** tự giữ chỗ (nếu
có thì khách bị thu hai lần — xem ghi chú tương tự trong `apps/*`). Hold nằm ở
**RUN**, không ở job. `HIGH`

`actual_cost()` (`executor.py:118`) tính lại từ:
`planning_cost` (từ decision_log) + `Σ credit_for(job_type, params) × attempts`
+ `Σ credit từ sự kiện verify`.

⚠️ Nó gọi `registry.credit_for(row.job_type, row.params)` **cho mỗi job con,
mỗi lần được gọi**, và nó được gọi **mỗi step READY mỗi tick** (§5.6). Giá là
một *hàm*, nên đây là công việc CPU lặp lại không cần thiết. `HIGH`

### 7.3 Lớp nào sở hữu việc thu tiền — trả lời

| Lớp | Sở hữu |
|---|---|
| Provider | Không (chỉ báo giá vốn qua `gia_von.py`) |
| **Tool / App** | **`manifest.credit_cost(params) -> int` — GIÁ** |
| Job | Hold/settle cho đường job đơn |
| **Agent Run** | **Hold/settle cho đường workflow (một hold cho cả run)** |
| Workflow (AgentWorkflow) | Không — chỉ giữ `budget_max`, `estimated` để hiển thị |

⭐ **Nguyên tắc đã trả giá và phải giữ:** *cửa số dư là ĐIỀU KIỆN, không phải
GIÁ*; và *đặt giá ở tầng job khi runtime đã thu là thu hai lần*.

---

## 8. (G) MÔ HÌNH TÀI NGUYÊN GPU

**Nguồn:** `gpu.py` (112) · `gpu_lease.py` (254) · `gpu_claims.py` (361) ·
`leases.py` (146) · `llm/admission` · `models.GpuLease`, `models.ExecutionLease`,
`models.SingletonLease`.

### 8.1 Ba tầng giành tài nguyên, giành theo đúng thứ tự này

```
job claim (hàng đợi)
   │
   ├─1─ ExecutionLease  (admission slot của tài nguyên TỪ XA, vd máy B)
   │      UNIQUE(resource, slot) → giành nguyên tử; heartbeat để thu hồi
   │      giành TRƯỚC GPU cục bộ — "không giữ card chỉ để ngồi chờ máy B"
   │
   ├─2─ GpuLease        (một card cục bộ, theo UUID)
   │      chọn card đủ VRAM theo manifest.gpu_vram_mb[job_type]
   │      heartbeat 60 s bằng LUỒNG RIÊNG (không dựa vào ctx.progress)
   │      ORPHAN_TIMEOUT 10 phút
   │
   └─3─ gpu_claims      (mặt phẳng CẤP MÁY, dữ liệu ở ProgramData)
          để tiến trình NGOÀI nền tảng cũng thấy card đang bị giữ
```

`CONFIRMED` (`job_runner._chay_mot_job:194-250`)

### 8.2 Ai chọn card

**Nền tảng**, không phải app. `JobContext.gpu_uuid` + `ctx.gpu_env()` ghim
`CUDA_VISIBLE_DEVICES` cho tiến trình con. Chú thích nói rõ lý do: hai handler
tự chọn "GPU 0 trống" sẽ cùng nạp model và OOM. `CONFIRMED`

### 8.3 Nhả tài nguyên khi bận

Bận GPU → `_tra_ve_hang_doi()`: job về `queued`, `next_run_at = now + delay`
(delay do app khai qua `cho_tai_nguyen_s`), **không tiêu lượt thử**. Đây là
"nhả worker" đúng nghĩa. `CONFIRMED`

### 8.4 🔴 Cái KHÔNG có

* **Không có "waitpoint" ở tầng workflow.** Một node GPU 20 phút được biểu diễn
  bằng: child job chạy 20 phút trên worker + Agent tick hỏi lại mỗi 2 giây.
  Worker của *job* bị chiếm 20 phút (đúng — nó đang làm việc), nhưng *executor*
  không bị chiếm (nó chỉ hỏi). Nên yêu cầu §3.11 đề bài **đã được đáp ứng một
  nửa, bằng polling chứ không bằng callback**. `HIGH`
* Không có provider GPU ngoài (Runpod/Vast). Chỉ card cục bộ + "máy B" qua
  admission slot. `CONFIRMED` (grep không thấy runpod/vast trong `platform_core/`)
* Không có ForEach/map với concurrency riêng — chỉ `fanout ≤ 4`, và fanout là
  **N bản sao CÙNG params**, không phải map trên một danh sách. `CONFIRMED`
  (`executor.py:308-316`: vòng `for index in range(fanout)` dùng chung `params`)

---

## 9. (H) AGENT — cái gì là Agent, cái gì thật ra là Workflow Engine

### 9.1 Mạch đầy đủ

```
goal (ngôn ngữ tự nhiên)
  └─ planner.plan_once     LLM: ltt_llm (model nhà) → gemini-2.5-flash
      │                    prompt liệt kê TOÀN BỘ tool + schema + returns
      ▼
  └─ normalizer.normalize_plan   64 KiB · depth ≤ 20 · nhận cả ```json fence
      ▼
  Plan v1 (JSON)
      ▼
  └─ validator.validate_plan     TẤT ĐỊNH — 21 phép kiểm, không LLM, không tiền
      ▼
  └─ budget.quote                maximum = planning + Σ step
      ▼
  └─ [NGƯỜI DÙNG PHÊ DUYỆT]      version pinning: approve(expected_version)
      ▼
  └─ budget.approve              credit.giu_cho(estimated) — MỘT hold nguyên tử
      ▼
  └─ executor.tick × N           deterministic, không cần LLM sống
      ▼
  └─ verifier.verify             technical(0) · face_identity(0) · vlm_judge(1)
      ▼
  └─ budget.settle               actual, hoàn phần chưa dùng
```

`CONFIRMED` — `tests/test_89..test_99`, 103 test xanh (đo 2026-09-07, 20,19 s).

### 9.2 ⭐ Nguyên tắc đã đúng sẵn: LLM không nằm trên đường thi hành

`executor.py` **không import gì thuộc `planner`**. Sau khi Plan được duyệt, việc
chạy hoàn toàn tất định. Nếu LLM chết, run vẫn chạy tiếp. Đây chính là điều mục
20 của đề bài yêu cầu — **LTT đã làm đúng, không cần chứng minh lại.** `CONFIRMED`

### 9.3 Cái gì THẬT RA thuộc về Workflow Engine, đang bị đặt trong "agent"

| Nằm ở `platform_core/agent/` | Thật ra là gì |
|---|---|
| `workflows.py` | **Workflow document store + versioning (snapshot)** |
| `validator.py` | **Graph validator + type checker + cost estimator** |
| `executor.py` | **DAG scheduler** |
| `budget.py` | **Cost/quote/hold/settle của workflow run** |
| `runs.py` | **WorkflowRun state service** |
| `verifier.py` | Đây mới thật là AI-specific |
| `planner.py`, `normalizer.py` | Đây mới thật là Agent |

⇒ **Sáu trên tám mô-đun trong `agent/` không có gì thuộc về agent.** Tên thư
mục đang nói sai về nội dung, và mỗi phiên đọc mã đều phải trả lại phí đó.
`HIGH`

### 9.4 Cổng rollout

`_run_rollout_mode()` (`apps/agent/routes/_shared.py:60`):

```
LTT_AGENT_CANVAS_RUN_ROLLOUT ∈ {off, admin, allowlist, public}
mặc định khi LTT_ENV=production và biến KHÔNG đặt  →  "off"
mặc định khi không phải production                  →  "public"
```

⇒ **Trên production, tạo run Canvas mặc định TRẢ 503**, trừ khi operator đã đặt
biến. Giá trị thật trên máy chủ: `UNKNOWN` — phải đọc cấu hình dịch vụ
(`setup/nap_lai_env.ps1` là nơi ENV được nướng vào nssm, xem cảnh báo trong
memory dự án). **Cần xác minh trước khi lập kế hoạch V2.**

---

## 10. (I) CANVAS / FRONTEND

**Nguồn:** `frontend/agent-canvas/` — **2.061 dòng TS/TSX**, React **19.2.8**,
**@xyflow/react 12.11.2** (React Flow v12), Vite 8, Vitest 4, TypeScript 5.9.

| Tệp | Dòng | Vai trò |
|---|---:|---|
| `CanvasShell.tsx` | 892 | toàn bộ tương tác (quá lớn) |
| `editorState.ts` | 360 | reducer + undo/redo + kiểm nối |
| `workflowApi.ts` | 285 | kiểu + fetch |
| `ToolNode.tsx` | 202 | node + Handle |
| `presentationAdapter.ts` | 119 | **lớp trình bày "creative"** |
| `nodePresentation.ts` | 99 | nhãn |
| `Inspector.tsx` / `RunInspector.tsx` / `CanvasEdgeView.tsx` | 95 | panel |

### 10.1 Có gì

| Năng lực | Có | Bằng chứng |
|---|:--:|---|
| Kéo thả tự do, vị trí lưu bền | ✅ | `page.nodes[].position` |
| Cổng có kiểu (Handle theo tên tham số) | ✅ | `ToolNode.tsx:85,88,179,182` |
| **Chặn nối sai kiểu** | ✅ | `connectionAllowed()` `editorState.ts:291` |
| **Chặn tạo chu trình ngay ở client** | ✅ | `connectionCreatesCycle()` (BFS reachability) |
| Undo / Redo (50 bước, Ctrl+Z / Ctrl+Shift+Z / Ctrl+Y) | ✅ | `editorState.ts:181-195` |
| Copy/paste có remap tham chiếu `$id` | ✅ | `cloneGraphSelection()` |
| Chèn node **vào giữa một cạnh** (tự nối lại 2 đầu + viết lại `$ref`) | ✅ | `insertToolOnEdge` |
| Pages · Frames · Notes · Comments | ✅ | `editorState` actions |
| Minimap · grid · Controls · fitView | ✅ | React Flow |
| Autosave + optimistic concurrency (`revision`, HTTP 409) | ✅ | `WorkflowConflictError` |
| Snapshot / restore / share link / export / import | ✅ | routes `apps/agent/routes/` |
| Hiển thị trạng thái run trên Canvas | ✅ | `edge.data.running`, `RunInspector` |
| Hai chế độ trình bày (`creative` / `legacy`) | ✅ | `presentationAdapter.ts` |

### 10.1b Phủ test của Canvas — đo bằng cách CHẠY, không bằng cách đọc

```
cd frontend/agent-canvas && npm test        →  6 tệp · 52 test · XANH · 14,32 s
```

`CONFIRMED` (chạy 2026-09-07 trên cây chính, vitest 4.1.10)

Bốn bundle frontend trong cây chính, đo cùng lượt:

| Bundle | Tệp test | Test | Kết quả |
|---|---:|---:|---|
| `agent-canvas` | 6 | **52** | xanh |
| `chatltt` | 15 | 178 | 1 tệp không nạp được *(thiếu `axe-core` trong `node_modules` cục bộ; nó **có** khai trong `package.json`, chỉ chưa `npm install`)* |
| `prompt-ai-ommi` | 5 | 28 | xanh |
| `autosub-studio` | 2 | 15 | xanh |
| **Tổng** | 28 | **273** | |

⚠️ **`CLAUDE.md` ghi "77 test frontend".** Số thật hôm nay là **273**. Con số cũ
không sai lúc nó được viết — `frontend/chatltt` (178 test) ra đời sau. Đây đúng
là cơ chế mà chính `CLAUDE.md` cảnh báo: *một giá trị chép lại là một giá trị sẽ
trôi.*

🔴 **Và một khẳng định ngược chiều cần bác bỏ tại đây.** Một phiên khác báo rằng
`agent-canvas` **bị `[BOQUA]` ở mọi lượt gate** vì thiếu `node_modules` — tức
Canvas không có phép kiểm nào chạy. **Sai với cây chính.**
`frontend/agent-canvas/node_modules` tồn tại (108 mục, có `vitest` binary), và
52 test chạy thật. Điều họ quan sát đúng — nhưng đúng **trong worktree của họ**,
và `tools/gate.py:767` đã ghi sẵn lý do:

> *"CAY RIENG KHONG CO `node_modules`, va do khong phai mot loi."*

⇒ Kết luận đúng là: **Canvas được kiểm khá kỹ ở tầng trình soạn (52 test), và
executor được kiểm ở tầng Python (103 test) — nhưng KHÔNG cái nào từng chạy
trước một khách hàng thật** (Phụ lục A). Phủ test không phải vấn đề của lớp
này; **lưu lượng bằng 0** mới là.

### 10.2 Không có / yếu

| Thiếu | Ghi chú |
|---|---|
| **Auto-layout thật** | `case 'layout'` chỉ xếp lưới 4 cột, bước 430 px. Không dagre/ELK. `CONFIRMED` |
| Subgraph / node "workflow con" | không tồn tại |
| Ước lượng chi phí trực tiếp trên canvas | có route `/api/tools/{tool}/quote`, nhưng tổng chi phí chỉ đến từ `validate` |
| Chỉ báo tài nguyên (GPU/hàng đợi) | không |
| **`presentationAdapter` có bảng tra CỨNG theo tên tool** | `explicitModalities`, `actionLabels`, `coreTools` liệt kê `image.generate`, `video.generate`… ⇒ **frontend biết tên tool cụ thể**, đúng thứ hợp đồng app cấm ở backend |
| `CanvasShell.tsx` 892 dòng một tệp | nợ kỹ thuật rõ ràng |

### 10.3 🔴 PHÁT HIỆN LỚN #6 — luật kiểu nằm ở HAI nơi, viết bằng HAI ngôn ngữ

```
Frontend  editorState.connectionAllowed()   TypeScript
Backend   validator._port_for_param() + kiểm port_type   Python
```

Hai bản không sinh ra từ một nguồn. Chúng **gần** giống nhau nhưng không bằng
nhau: frontend có thêm luật đặc thù (`targetHandle === 'refs'` bị chặn,
`prompt` + `source_text` bị chặn, `asset.*` không nhận đầu vào) mà backend
không có; backend có `reference_order` mà frontend không kiểm.

⇒ Frontend là **UX guard**, backend là **security/correctness guard**. Điều đó
đúng — nhưng hai bảng luật viết tay sẽ trôi, và đây đúng là cơ chế đã hỏng năm
lần ở chỗ khác trong dự án này (bảng chép tay trong `CLAUDE.md`). `HIGH`

---

## 11. ĐỊNH NGHĨA THỰC THỂ — từ vựng HÔM NAY

| Từ đề bài dùng | LTT hôm nay gọi là | Nơi ở | Có thật? |
|---|---|---|:--:|
| App | `AppManifest` | `apps/<slug>/manifest.py` | ✅ |
| Tool / Capability | `ToolSpec` | trong manifest | ✅ |
| **NodeType** | *không có tên riêng* — chính là `ToolSpec` | | ⚠️ trùng khái niệm |
| **NodeInstance** | `CanvasNode` (soạn) / `step` trong Plan (chạy) | JSON | ⚠️ hai tên |
| Port | key của `params_schema` / `returns` | | ✅ |
| **Edge** | `CanvasEdge` (soạn) → tan thành `after`/`after_error` (chạy) | | ⚠️ **không phải thực thể ở runtime** |
| Workflow | `AgentWorkflow` | bảng `agent_workflows` | ✅ |
| **WorkflowVersion** | `AgentWorkflow.revision` + `AgentWorkflowSnapshot` | | ⚠️ **snapshot ≠ version bất biến được ghim** |
| WorkflowRun | `AgentRun` | bảng `agent_runs` | ✅ |
| **NodeRun / StepRun** | `AgentRun.checkpoint[step_id]` — **một khoá JSON** | | ⚠️ **không phải hàng CSDL** |
| **Attempt** | `checkpoint[sid].attempt` (int) + `Job.attempts` | | ⚠️ hai bộ đếm khác nhau |
| Job | `Job` | bảng `jobs` | ✅ |
| Worker | tiến trình `job_runner.run_forever` | | ✅ |
| **Waitpoint** | — | | ❌ |
| **Artifact** | chuỗi storage key trong `Job.result` | | ⚠️ **không có bảng, không có id ổn định** |
| GPU Resource | `GpuLease` / `ExecutionLease` / `gpu_claims` | | ✅ |
| Agent | `planner` + `normalizer` | | ✅ |
| Trigger | manual + `scheduled_at` (≤30 ngày) | decision_log | ⚠️ chỉ 2 loại |
| Connection / Secret | `ApiKey` + `api_pool` (theo nền tảng, không theo node) | | ⚠️ khác mô hình |

### 11.1 Về Artifact — nói rõ vì nó ảnh hưởng V2

Không có bảng `artifact`. Danh tính artifact được **suy ra**:
`public_api/media.py:artifact_id(job_id, field, index)`. Đường web thì thậm chí
suy bằng cách quét tên khoá kết thúc bằng `_key`/`_keys`
(`apps/agent/routes/_shared.py:_artifact_key`).

Nghĩa là: **không có lineage, không có TTL riêng, không có checksum, không có
dedupe, không có quyền theo artifact.** Quyền = quyền trên job cha; TTL =
`Job.content_expired_at`. `CONFIRMED`

Điểm tốt: **workflow chuyển tham chiếu, không chuyển bytes.** Output media là
chuỗi khoá lưu trữ nằm trong `Job.result` → sao chép vào `checkpoint`. Không
bao giờ có bytes trong state. `CONFIRMED`

Điểm xấu: `checkpoint` là **một cột JSON bị đọc–sửa–ghi TOÀN BỘ mỗi tick**. Với
100 step, mỗi 2 giây ghi lại cả tài liệu. `CONFIRMED` (`run.checkpoint =
checkpoint; db.flush()`)

---

## 12. ĐIỂM MẠNH — thứ KHÔNG được viết lại

Xếp theo mức độ "viết lại sẽ là sai lầm".

1. **Hợp đồng app (`registry.py`).** Nền tảng không biết tên app nào. Đã bị ép
   mở rộng bởi sự cố thật 8+ lần, mỗi lần ghi lại lý do. Đây là thứ khó tái tạo
   nhất. **KEEP.**
2. **Hàng đợi job (`jobs.py` + `job_runner.py`).** SKIP LOCKED, dedupe, orphan
   reclaim, công bằng đa tenant có aging, phân loại lỗi ba nhánh
   (`LoiNguoiGoi`/`DangBan`/thường), `provider_state=ambiguous`. Một workflow
   engine mới sẽ mất nhiều tháng để có lại chừng này. **KEEP.**
3. **Sổ credit (`credit.py`).** Append-only, số dư là SUM, idempotent theo job,
   advisory lock chống double-spend. **KEEP.**
4. **Trần chi phí tính trước, tất định** (`validator` + `budget.quote`). Rất ít
   hệ thống có. **KEEP nguyên tắc, mở rộng công thức.**
5. **Ranh giới `ensure_can_spend` trước mỗi lời gọi provider.** Chi phí thực tế
   không bao giờ vượt hold đã duyệt. **KEEP.**
6. **Tách LLM khỏi đường thi hành.** **KEEP.**
7. **Ba tầng lease GPU + nền tảng chọn card, không phải app.** **KEEP.**
8. **Public API kernel**: 24 route đóng băng có test hai chiều, idempotency,
   webhook HMAC + retry, ba chế độ thi hành (`SYNC`/`SYNC_BILLED`/`ASYNC_JOB`/
   `STREAM`), scope, rate limit, sandbox. **KEEP — và đây là nơi Waitpoint của
   V2 nên cắm vào.**
9. **`JobEvent` append-only tách public/internal.** Nền tảng observability đã có.
   **KEEP.**
10. **Canvas: kiểm kiểu + chặn chu trình + undo/redo + chèn-giữa-cạnh +
    optimistic concurrency.** UX đã vượt mức MVP. **KEEP, refactor chứ đừng
    thay React Flow.**

---

## 13. NỢ KỸ THUẬT, COUPLING NGẪU NHIÊN, NGUYÊN HÀM CÒN THIẾU

### 13.1 Nợ kỹ thuật (có số đo)

| # | Nợ | Bằng chứng | Mức |
|---|---|---|---|
| D1 | Tick tốn `31+N` SQL, lặp mỗi 2 s, mãi mãi | đo §5.6 | 🔴 |
| D2 | `checkpoint` là JSON bị ghi lại toàn bộ mỗi tick | `executor.py:330` | 🔴 |
| D3 | Song song trần cứng **4 step**, không khai được | `executor.py:238` | 🔴 |
| D4 | `verifier.verify()` (gọi mạng) chạy **trong** transaction giữ khoá | `executor.py:89-97` | 🔴 |
| D5 | `on_fail = refine / switch_model` là **cửa giả** trên production (không có adapter) | `apps/agent/jobs.py:16` | 🟠 |
| D6 | Cache quét 50 job + `storage.exists()` trong đường nóng scheduler | `executor.py:158-176` | 🟠 |
| D7 | `actual_cost()` gọi lại `credit_for` cho mọi job con, mọi step READY | `executor.py:296` | 🟠 |
| D8 | `CanvasShell.tsx` 892 dòng | đo | 🟠 |
| D9 | Luật kiểu nối dây viết tay ở 2 nơi, 2 ngôn ngữ | §10.3 | 🟠 |
| D10 | Thư mục `agent/` chứa 6/8 mô-đun không thuộc agent | §9.3 | 🟡 |
| D11 | `AgentWorkflow` giữ **cả** `document` v2 **lẫn** `nodes/edges/viewport` v1 | `models.py:520-527` | 🟡 |
| D12 | `_placeholder()` khiến min/max của giá trị đến từ upstream không được kiểm | `validator.py:47` | 🟡 |

### 13.2 Coupling ngẫu nhiên

| # | Chỗ nối không nên có |
|---|---|
| C1 | **Frontend biết tên tool cụ thể** (`presentationAdapter.ts`: `image.generate`, `video.generate`, `asset.*`…). Backend cấm điều này (`test_60`, `test_147`); frontend không có bánh cóc tương đương. |
| C2 | Suy ra artifact bằng **quy ước đặt tên khoá** (`_key`, `_keys`) thay vì bằng khai báo `returns`. Hai nơi làm khác nhau (`public_api/media.py` vs `routes/_shared.py`). |
| C3 | `executor` biết `verifier` (AI-specific) ngay trong vòng lặp scheduler — scheduler tổng quát không nên biết verifier là gì. |
| C4 | `Job.plan_id`/`step_id` là cột trên bảng job dùng chung, chỉ để phục vụ Agent. Không sai, nhưng là rò khái niệm từ tầng trên xuống tầng dưới. |
| C5 | `planner.py` phải tự đi tìm `admission_resource` của app `ltt_llm` bằng cách duyệt registry và **so tên slug** (`if it.manifest.slug != "ltt_llm"`). Một mô-đun lõi biết tên một app. |

### 13.3 Nguyên hàm CÒN THIẾU (đối chiếu §3 đề bài)

| Đề bài | LTT hôm nay |
|---|---|
| 3.1 DAG tổng quát, edge là thực thể | ⚠️ DAG có; **edge không phải thực thể runtime** |
| 3.2 NodeType vs NodeInstance | ⚠️ có trên thực tế, **chưa có tên** |
| 3.3 Cổng có kiểu | ✅ 9 kiểu, nhưng **gộp mất thông tin** (int→json) |
| 3.4 Tách data edge / control edge | ⚠️ tồn tại do tai nạn, **không khai báo được** |
| 3.5 Song song có ràng buộc | ⚠️ **trần cứng 4**, không theo tài nguyên/rate-limit/GPU |
| 3.6 JOIN: ALL/ANY/N-of-M/FIRST | ❌ **chỉ ALL** |
| 3.7 Loop / ForEach / map | ❌ **KHÔNG CÓ** (fanout là N bản sao cùng params) |
| 3.8 Router / Switch / If | ⚠️ chỉ `success`/`error` trên cạnh; **không có điều kiện dữ liệu** |
| 3.9 Mô hình lỗi | ⚠️ có retry/timeout/error-branch; **không có compensation, không có fallback tool** |
| 3.10 Durable execution | ⚠️ **resume mức step**; không replay, không event sourcing |
| 3.11 Waitpoint | ❌ **KHÔNG CÓ** — thay bằng polling 2 s |
| 3.12 Subworkflow | ❌ **KHÔNG CÓ** |
| 3.13 Artifact có danh tính | ⚠️ chỉ là chuỗi khoá; **không bảng, không lineage, không checksum** |
| 3.14 GPU/AI workload | ✅ **mạnh** (lease 3 tầng, VRAM theo làn) |
| 3.15 Credit/cost | ✅ **mạnh** (trần tính trước, hold một lần, settle idempotent) |
| 3.16 Agent tách khỏi engine | ✅ **đã đúng** |
| 3.17 Human-in-the-loop | ⚠️ **chỉ 1 điểm**: phê duyệt báo giá. Không có form/review giữa chừng |
| 3.18 Trigger | ⚠️ manual + schedule một lần. **Không cron, không webhook, không event** |
| 3.19 Connector SDK | ✅ `ToolSpec` + `AppManifest` — **đây là điểm mạnh** |
| 3.20 Versioning bất biến | ⚠️ `AgentRun.plan` **được đóng băng** (tốt), nhưng `AgentWorkflow.revision` là bộ đếm chứ không phải version publish được ghim |
| 3.21 Observability | ⚠️ `JobEvent` mạnh ở tầng job; **tầng workflow chỉ có `decision_log` JSON** |
| 3.22 Idempotency | ✅ `dedupe_key` theo `run:version:step:attempt:index`; `ambiguous` cho side effect |
| 3.23 Multi-tenant / bảo mật | ✅ mạnh (`app_access`, `_CLIENT_FORBIDDEN`, `owner_id` server-side, sandbox API) |
| 3.24 Public API chạy workflow | ❌ `/api/v1` **chỉ có job, không có workflow** |
| 3.25 Scale | ⚠️ xem §14 |

---

## 14. GIỚI HẠN QUY MÔ — đo, không đoán

| Kịch bản | Kết luận | Nhãn |
|---|---|---|
| 100 node trong một workflow | Chạm trần `MAX_STEPS=100`. Canvas 512 KiB có thể chạm trước. | `CONFIRMED` |
| 500 / 1.000 node | **Không thể** — validator từ chối. | `CONFIRMED` |
| 1 run 100 node đang chạy | ~131 câu SQL / 2 s ≈ **65 câu/s**, chỉ để hỏi. | `CONFIRMED` |
| 100 run đồng thời | Mỗi user tối đa **3** run hoạt động (`MAX_ACTIVE_RUNS_PER_USER=3`) ⇒ cần ≥34 user. Tải SQL ước tính hàng nghìn câu/s. | `INFERRED` |
| Đồ thị rộng (fan-out 50) | Không tăng thông lượng: vẫn 4 step/lần. | `CONFIRMED` |
| Job dài 20 phút (GPU) | OK — worker bị chiếm, executor thì không. | `HIGH` |
| Artifact 2 GB | OK ở tầng workflow (chỉ chuyển khoá). Cloudflare 100 MB/request là ràng buộc ở **cửa vào**, không ở workflow. | `HIGH` |

**Điểm nghẽn thật, theo thứ tự:**
1. `max_parallel=4` — trần thông lượng, không phải trần tài nguyên.
2. Vòng polling 2 s × (31+N) SQL — trần số run đồng thời.
3. `checkpoint` JSON đọc–sửa–ghi toàn bộ — trần số step.
4. `MAX_STEPS=100` + Canvas 512 KiB — trần kích thước đồ thị.

---

## 15. LƯỢC ĐỒ CSDL LIÊN QUAN (hiện trạng)

```
users ──< credit_entries        (append-only; hold/settle/refund/topup/grant)
      │
      ├─< agent_workflows       document(JSON v2) + nodes/edges/viewport(JSON v1)
      │      │                  revision, status, budget_max, estimated
      │      ├─< agent_workflow_snapshots   (revision UNIQUE, document JSON)
      │      └─< agent_workflow_shares      (SHA-256 token digest, expires)
      │
      ├─< agent_runs            plan(JSON, ĐÓNG BĂNG) · checkpoint(JSON)
      │      │                  decision_log(JSON) · version · estimated/actual
      │      └─< jobs (plan_id, step_id)
      │
      └─< jobs ──< job_events   (append-only, public/internal)
             │
             ├── execution_leases   UNIQUE(resource, slot)
             ├── gpu_leases         theo GPU UUID
             └── singleton_leases   việc nền toàn cụm
```

**Không có bảng:** `workflow_node`, `workflow_edge`, `node_run`, `attempt`,
`waitpoint`, `artifact`, `workflow_trigger`, `workflow_schedule`,
`workflow_event`. Toàn bộ nằm trong JSON hoặc không tồn tại. `CONFIRMED`

---

## 16. TRÌNH TỰ RUNTIME ĐẦY ĐỦ (một node video GPU)

```
Người dùng ─► POST /agent/api/workflows/{id}/runs
                 validate_plan → create_run_capped(≤3) → set_quote
Người dùng ─► POST /agent/api/runs/{id}/approve
                 budget.approve → credit.giu_cho(estimated)   [TRANSACTION]
                 jobs.submit("agent.advance")
                                    │
WORKER ─────────────────────────────┘
  claim("agent.advance")  ──► apps/agent/jobs.handle()
     └─ executor.tick()   [TRANSACTION, FOR UPDATE agent_runs]
          _sync_children (N truy vấn)
          _advance_branch_states
          step READY → resolve_params ("$s1.image" → khoá thật)
                     → ensure_can_spend
                     → jobs.submit(job_type="taovideo.render",
                                   params + owner_id, dedupe_key=..., max_attempts=1)
          checkpoint[sid]="submitted"
     └─ jobs.submit("agent.advance", next_run_at = +2s)     ◄── VÒNG LẶP
                                    │
WORKER (cùng hoặc khác) ────────────┘
  claim("taovideo.render")
     ├─ admission.hold_persisted(resource, slots)     ← ExecutionLease
     ├─ _giu_gpu(need_mb từ manifest.gpu_vram_mb)     ← GpuLease + heartbeat 60s
     │    (bận → defer_resource / _tra_ve_hang_doi, KHÔNG tiêu lượt)
     ├─ mark_admitted → metrics LATENCY_ADMISSION
     ├─ handler(params, ctx)   ctx.gpu_env() ghim CUDA_VISIBLE_DEVICES
     │    ctx.provider_dispatched() trước outbound HTTP
     │    ctx.progress(%) mỗi mốc  → JobEvent + heartbeat
     ├─ complete(result={"video_key": "..."})
     ├─ _quyet_toan_credit  (đường job đơn) / bỏ qua (đường agent: credit_cost=0)
     └─ _enqueue_webhooks
                                    │
tick kế tiếp (≤2 s sau) ────────────┘
  _sync_children thấy job done → verifier.verify(outputs)  ← GỌI MẠNG TRONG TX
  checkpoint[sid]="done", outputs={"video_key": ...}
  step kế READY → resolve "$sid.video_key" → submit …
  …
  mọi step terminal → budget.settle(actual) → credit.quyet_toan + hoàn phần dư
```

---

## 17. CÁI ĐÃ ĐO ĐƯỢC vs CÁI CÒN LÀ `UNKNOWN`

### Đã chạy được (`CONFIRMED`)
* 103 test agent xanh, 20,19 s (`test_87/89/90/91/92/93/96/97/98/99`, `-n 6`).
* SQL/tick = 31 + N (N = 5/20/50/100 → 36/51/81/131).
* Tick đầu tiên của plan 100 step độc lập tạo đúng **4** child job.
* Production đang ở commit `a365fa80`, chậm hơn cây đo 1 commit.
* Bề mặt công khai production: `/`, `/vps`, `/gia-api` mở; `/developers` đòi
  đăng nhập; `/api/v1` fail-closed.

### Đã giải quyết sau khi viết bản đầu (xem Phụ lục A)
1. ~~Canvas run có sống ở production không?~~ → **KHÔNG. Chưa từng chạy một lần
   nào trong 28 ngày log.** `CONFIRMED`

### Chưa đủ bằng chứng (`UNKNOWN`)
2. **Có bao nhiêu `AgentWorkflow` / `AgentRun` thật trong CSDL production?**
   Không đọc được: `C:\LTTPlatform\secrets\` bị ACL chặn (cố ý, đúng W1.5) nên
   không lấy được `LTT_DATABASE_URL`. Cần nâng quyền — **để người dùng quyết**.
   *Ghi chú:* Phụ lục A đã trả lời phần quan trọng hơn (chưa có run nào chạy),
   nên câu này chỉ còn ảnh hưởng tới việc có phải di trú **bản nháp đã lưu** hay
   không.
3. **Giá trị thật của `LTT_AGENT_CANVAS_RUN_ROLLOUT`.** Đọc registry dịch vụ bị
   chặn ở phiên này. Không còn quan trọng: dù giá trị là gì, §A.1 cho thấy
   **không có run nào từng chạy**.
4. **Chi phí thật của một tick trên PostgreSQL** (số ở §5.6 đo trên SQLite; kế
   hoạch truy vấn của Postgres khác — hằng số đổi, độ dốc `O(N)` thì không).
5. Có worker nào đang chạy với `capabilities` bị giới hạn không.
   *Gợi ý từ Phụ lục A:* log cho thấy tối đa 2 tiến trình worker
   (`ltt-job-worker-0/1`) và dòng `chay <n> tien trinh worker: da nangx<n>`
   ⇒ đội hình **đa năng**, không chia làn.

---

## 18. KẾT LUẬN CỦA BƯỚC 1

**LTT hôm nay là:** một nền tảng job SaaS đa tenant trưởng thành, có hợp đồng
app xuất sắc, sổ tiền đúng, quản lý GPU thật, Public API có kỷ luật — **cộng
với** một lớp orchestration MVP 1.843 dòng đã đúng về *nguyên tắc* (tất định,
báo giá trước, tách LLM) nhưng còn thiếu phần lớn *nguyên hàm* của một workflow
engine (waitpoint, ForEach, join đa ngữ nghĩa, subworkflow, artifact có danh
tính, trigger, versioning ghim được) và có bốn nút thắt quy mô đã đo được.

**Điều đó có nghĩa gì cho V2** — nêu ở đây như *giả thuyết cần kiểm chứng ở các
bước sau*, chưa phải khuyến nghị:

> Ranh giới đúng để cắt **không phải** "giữ LTT hay thay LTT", mà là
> **"giữ tầng dưới, thiết kế lại tầng trên"**: hàng đợi/credit/GPU/registry/
> Public API là tài sản; `agent/executor.py` + mô hình lưu `checkpoint` JSON là
> thứ cần được thay bằng một mô hình có `node_run`, `edge`, `waitpoint` và
> `artifact` là thực thể thật.

**Bước tiếp theo (chưa làm):** `02_LTT_WORKFLOW_V2_REQUIREMENTS.md` — chốt yêu
cầu của LTT **trước khi** tải bất kỳ kho mã nguồn mở nào, đúng như §3 đề bài
yêu cầu.

---

---

## PHỤ LỤC A — BẰNG CHỨNG TỪ PRODUCTION THẬT

**Nguồn:** `C:\LTTPlatform\logs\ltt-job-worker{,-0,-1}.jsonl` — 37.963 dòng,
cửa sổ liên tục **2026-08-11T01:39Z → 2026-09-07T10:04Z (28 ngày)**.
Chỉ đọc, chỉ trích số đếm; không đọc payload của khách. `CONFIRMED`

### A.1 🔴 Agent/Canvas CHƯA TỪNG CHẠY MỘT LẦN NÀO trên production

```
grep -c "agent.advance"  →  0
```

Không có một job `agent.advance` nào trong 28 ngày. Kết hợp với
`_run_rollout_mode()` mặc định `"off"` khi `LTT_ENV=production` (§9.4), kết
luận: **toàn bộ lớp orchestration hiện tại là mã chưa vận hành.**

⭐ **Đây là dữ kiện quan trọng nhất của cả tài liệu**, vì nó đổi bản chất bài
toán V2: **không có khách đang chạy trên engine cũ**, nên "di trú" gần như
không tồn tại, và ràng buộc *"không được big-bang rewrite"* (§22 đề bài) **không
áp dụng cho tầng executor**. Nó vẫn áp dụng đầy đủ cho tầng job/credit/GPU —
tầng đó **đang** phục vụ khách thật.

### A.2 Hỗn hợp tải thật — LTT hôm nay chạy gì

| Loại job | Lượt worker nhặt | Tỉ lệ |
|---|---:|---:|
| `ltt_llm.chat` | 10.663 | 89,4 % |
| `anhnoibo.generate` | 1.075 | 9,0 % |
| `ltt_voice.synthesize` | 147 | 1,2 % |
| `ltt_voice.enroll` | 28 | 0,2 % |
| `vps.provision` / `vps.destroy` | 14 | 0,1 % |
| `taoclipngan.render` / `taoanh.generate` | 2 | ~0 % |
| **`agent.advance`** | **0** | **0 %** |
| **Tổng lượt nhặt** | **11.929** | |
| **Job báo `xong`** | **868** | |

⇒ Tải thật **không** giống Zapier (nhiều bước ngắn nối nhau). Nó là
**ít loại việc, mỗi việc nặng, và tranh nhau một tài nguyên khan hiếm.**

### A.3 🔴 Vòng `claim → defer` đang đốt 92 % số lượt nhặt

```
9.833 dòng:  job <id> (ltt_llm.chat) hoãn <n>s: tài nguyên llm_remote đang bận
```

9.833 / 10.663 = **92,2 %** lượt nhặt `ltt_llm.chat` kết thúc bằng *nhả ra và
xếp lại*. Tính trên toàn bộ: 11.929 lượt nhặt cho **868** job hoàn tất —
**13,7 lượt nhặt cho mỗi job xong**.

Nguyên nhân kiến trúc: `claim()` **không biết** tài nguyên có rảnh hay không.
Nó nhặt trước, giành `ExecutionLease` sau, thất bại thì `defer_resource`. Với
`DONG_THOI_MAY_B=1` (máy B chỉ một suất) thì mọi job chat loại trừ nhau, nên
đây là **trạng thái bình thường, không phải sự cố**.

⇒ Yêu cầu rút ra cho V2: **hàng đợi phải nhận biết tài nguyên (resource-aware
admission trước khi claim)**, chứ không phải "claim rồi thử".

### A.4 Ngoại lệ thật, xếp theo tần suất

| Lớp ngoại lệ | Lượt | Ý nghĩa |
|---|---:|---|
| `DangBan` | 1.055 | cổng tạo ảnh bận — *đã* được xử lý đúng (không tiêu lượt thử) |
| `KhongCoProviderNao` | 34 | hết provider khả dụng |
| `LoiGiongNoi` | 19 | lỗi người gọi (`LoiNguoiGoi`) — không thử lại, đúng |
| **`AmbiguousProviderError`** | **10** | **bài toán exactly-once là CÓ THẬT, không phải giả thuyết** |
| `RouterError` | 6 | |
| `LoiTaoAnh` | 5 | |
| `VuotNganSachError` | 4 | trần ngân sách đã thật sự chặn chi |
| `ChuaCauHinh` | 2 | |

`AmbiguousProviderError` xảy ra **10 lần trong 28 ngày** ⇒ trung bình ~2,6
lần/tuần một job rơi vào tình trạng "không biết provider đã làm hay chưa". V2
**bắt buộc** phải giữ ngữ nghĩa `at-most-once cho side effect` này.

### A.5 Sổ tiền có rò rỉ trạng thái treo

```
145 dòng:  GIU CHO TREO: <n> khoan, <n> credit cua khach dang bi giu
           ma khong ai ket so duoc
           (đỉnh quan sát được: 53 khoản · 203 credit)
```

Cơ chế `credit.giu_cho_treo()` + `tu_hoan_treo()` **đang chạy và đang bắt được
việc thật**. Nhưng nó là *bộ dọn*, nghĩa là con đường chính vẫn để lọt hold
không ai kết sổ — 145 lần báo trong 28 ngày.

### A.6 Nhiễu nền cần biết khi thiết kế V2

| Dấu hiệu | Lượt | Ghi chú |
|---|---:|---|
| `GET /health` + `/live` tới máy B | 7.614 | thăm dò sức khoẻ chiếm 20 % số dòng log |
| `thu hoi lease 'maintenance' … qua han dap nhip` | 334 | lease bảo trì bị mất nhịp thường xuyên |
| `loi trong vong worker, tiep tuc` | 551 | lỗi bị nuốt trong vòng lặp |
| `loi trong vong bao tri, tiep tuc` | 476 | như trên, vòng bảo trì |
| `worker … bat dau` | 380 | worker khởi động lại 380 lần / 28 ngày ≈ 13,6 lần/ngày |

⇒ **Worker restart 13,6 lần mỗi ngày là chuyện thường ở đây.** Một thiết kế V2
giả định worker sống lâu sẽ sai. Tính bền qua restart không phải "tính năng
nâng cao" — nó là điều kiện vận hành hằng ngày của chính máy này.

---

*Không có dòng mã sản phẩm nào bị sửa khi lập tài liệu này. Phép đo SQL dùng
một tệp tạm nằm ngoài kho (thư mục scratchpad của phiên), không ghi vào cây làm
việc. Log production chỉ được đọc ở mức đếm; không trích nội dung của khách.*
