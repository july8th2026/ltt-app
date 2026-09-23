# Audit runtime LTT WORKFLOW V2 — main @ 5fc64f03 (22/09/2026, CHỈ ĐỌC)

Bằng chứng = mã + test. Chưa kiểm trên trình duyệt: các kết luận về Canvas là SUY RA TỪ MÃ.

## 1. Runtime thật

| | CURRENT | GAP |
|---|---|---|
| Ai import `platform_core.workflow` ngoài gói | `server/api/workflows.py:51` (bao_gia, may_trang_thai, thi_hanh, tien) · `apps/agent/routes/drafts_v3.py:38` (bao_gia, dinh_nghia) · `platform_core/registry.py:1110` (bieu_thuc, dùng cho timeout ToolSpec) · `platform_core/credit.py:656` (RUN_KET_THUC) · `tools/chay_m1_tren_production.py:101` (di_tru_m1) | **KHÔNG ai** gọi `dieu_phoi`, `danh_thuc`, `cho_doi`, `foreach`, `join`, `trigger`, `canh`, `artifact`, `he_kieu` ngoài test (grep toàn kho trừ tests/.claude) |
| Scheduler | `dieu_phoi.mot_vong` `platform_core/workflow/dieu_phoi.py:198`, sau cờ `LTT_WORKFLOW_V2` mặc định TẮT (`:32`, `:68`) | Không worker/tick/job kind nào gọi `mot_vong`/`enqueue`/`dequeue`/`ttl`; cờ không được đặt ở đâu ngoài chính mô-đun. `thi_hanh.py:5` tự ghi *"chưa nối vào đường chạy nào"*; nhật ký `31:886,1073,1177` xác nhận |
| Không có node→job bridge | `tien.py` docstring: *"attempt() mới ghi lượt thử, chưa nộp job"* | Không có mã nào nộp job cho một node v2, không có handler thi hành node |
| Runtime đang chạy thật | `platform_core/agent/executor.py:223 tick()` — DAG trên `AgentRun.plan` (Plan v1). Được gọi bởi `apps/agent/jobs.py:16 advance()` ← job type `agent.advance` (`apps/agent/manifest.py:18`, tự nộp lại `jobs.py:33-38` mỗi 2 s) và ← `POST /agent/api/runs/{id}/tick` (`routes/runs.py:133`), `routes/legacy_runs.py:128` | — |
| HAI runtime song song? | Có **hai mô hình**, nhưng chỉ **một** thi hành: agent executor (AgentRun) | WorkflowRun v2 chỉ là sổ ghi + tiền, không có bộ máy |
| Đường Canvas → run | Canvas lưu/đọc **v3** (`frontend/agent-canvas/src/CanvasShell.tsx:183,229,367` → `/agent/api/v3/workflows`, bảng `workflow`/`workflow_draft`). Nút Run gọi `validateWorkflow` + `createRun` (`workflowApi.ts:360,371`) → `/agent/api/workflows/{id}/validate|runs` (`library.py:34`, `runs.py:28`) → `platform_core/agent/workflows.get_owned` đọc bảng **`agent_workflows` (v2)** (`agent/workflows.py:229`) → `canvas_to_plan` → AgentRun → executor | **LỆCH**: `v3_luu` (`drafts_v3.py:113-136`) không ghi ngược `AgentWorkflow`. ⇒ workflow tạo mới ở v3 (`drafts_v3.py:89`) không có hàng `agent_workflows` → 404 khi Run; workflow đã di trú (`di_tru_m1.py:222` giữ cùng id) → If-Match mang revision v3 so với revision v2 → 409, hoặc nếu trùng số thì chạy **nội dung v2 cũ**, không phải bản vừa lưu. Cần kiểm trình duyệt để xác nhận |
| Đường API công khai v2 | `server/api/__init__.py:167` mắc `register_workflow_routes`; `POST /api/v1/workflows/{id}/runs` tạo `WorkflowRun` + giữ credit (`workflows.py:217,241`) | Run nằm `status="queued"` (`models.py` WorkflowRun default) **mãi mãi**: không ai `enqueue`; `ttl()` chỉ hết hạn run có `started_at` (`dieu_phoi.py:171-173`) và chỉ khi cờ bật. Khoản giữ chỉ được cứu bởi lưới tự hoàn `credit.TU_HOAN_SAU=24h` (`credit.py:701`) |

## 2. Mô hình dữ liệu (`platform_core/models.py`)

| Bảng | Dòng | Migration (revision) |
|---|---|---|
| agent_runs | 669 | `b2c3d4e5f6a7` (20260802_1200) |
| agent_workflows | 704 | `c3d4e5f6a7b8`; canvas v2 cột `e5f6a7b8c9d0` |
| agent_workflow_snapshots, agent_workflow_shares | 736, 754 | `f6a7b8c9d0e1` |
| workflow, workflow_draft, workflow_version, workflow_version_node, workflow_version_edge | 1147,1177,1197,1223,1238 | `a4f81c2d6b95` (down `e7b2c94a1d38`) |
| workflow_run, node_run, node_run_snapshot | 1273,1322,1345 | `b5c92e3f7a41` (+ `ux_workflow_run_idem` UNIQUE(owner_id, idempotency_key) :95) |
| waitpoint, waitpoint_signal, node_run_waitpoint, wakeup | 1385,1438,1458,1480 | `c6d13a8e4b72` |
| workflow_run.ket_so_luc / ly_do_ket_so | — | `d7e24b9f1c53` |
| foreach_vong, foreach_muc, artifact, workflow_trigger | 1515,1539,1566,1607 | `e8f35c1a7d64` |

AgentWorkflow/AgentRun **còn và là runtime sống**. GAP nhỏ: idem index là (owner_id, key) nhưng route tra theo (owner, workflow, key) (`server/api/workflows.py:207-232`) ⇒ cùng key cho workflow khác → IntegrityError → tra lại ra None → `raise` 500.

## 3. Máy trạng thái (`may_trang_thai.py`)

- Run (`:131-143`): `queued|CREATED→VALIDATING→QUEUED→RUNNING⇄WAITING→{SUCCEEDED,FAILED,SYSTEM_FAILURE,CANCELLED,TIMED_OUT}`. Kết thúc `:124`. Vào kết thúc ⇒ `ket_so` cùng transaction (`:229-232`).
- Node (`:155-166`): `PENDING→READY→QUEUED→RUNNING⇄RUNNING_WITH_WAITPOINTS→{SUCCEEDED,FAILED,ABANDONED,CANCELLED}`; `SKIPPED` từ PENDING/READY.
- Từ chối chuyển sai: CÓ — `chuyen_node` ghi snapshot `is_valid=False`, con trỏ đứng yên, trả False (`:189-199`); `chuyen_run` trả False (`:219`). Không có HTTP nào lộ chuyển node.
- So với mong muốn: **thiếu** `WAITING` (node, thay bằng RUNNING_WITH_WAITPOINTS), `RESUMING`, `RETRY_SCHEDULED`; không có chuyển FAILED→retry (node kết thúc là cuối; retry chỉ là `attempt()` ghi READY `dieu_phoi.py:131-146`, mà READY từ FAILED sẽ bị từ chối). Thêm `ABANDONED`, `SYSTEM_FAILURE`, `TIMED_OUT`, `VALIDATING`. Trạng thái khởi tạo lẫn hoa/thường (`"queued"` vs `"CREATED"`).

## 4. Loại node

| | CURRENT | GAP |
|---|---|---|
| Control | `dieu_khien.py:15-24`: IF, SWITCH, MERGE, FOREACH, JOIN, DELAY, SET_VAR, NOOP — chỉ là **tập tên** + `sinh_job()` | **Không loại nào thi hành được**: không có hàm evaluate IF/SWITCH, không SET_VAR, không DELAY runtime. JOIN/FOREACH có kho dữ liệu (`join.py`, `foreach.py`) nhưng không ai gọi |
| Input/Const/Router/Approval/Subworkflow/Collect | Không có trong v2 | Approval chỉ tồn tại ở v1 (AgentRun `AGENT_AWAITING_APPROVAL`, `agent/runs.py:24-31`) và là duyệt cả run, không phải node |
| Node tool (job) | Mặc định mọi type lạ = job (`dieu_khien.py:27-34`) | v1 executor chạy step tool thật + nhánh success/error (`executor.py` `_advance_branch_states`), fanout ≤4, retry ≤2 (`agent/validator.py:14-16`) |

## 5. Biểu thức · kiểu · artifact

- `bieu_thuc.py`: duyệt AST, **không eval** (`:168-220`). Toán tử + - * / // %, unary ±, so sánh < <= > >= == !=, and/or, ternary, gọi `min`/`max`; hằng chỉ số/bool. Namespace = **chỉ `params` của chính node** (`:23-25`); không tham chiếu node khác. Lỗi `LoiBieuThuc` có câu chỉ chỗ sai (`:62-122`). Dùng duy nhất cho biểu thức timeout ToolSpec (`registry.py:1110`). ⇒ GAP: không có ngôn ngữ ánh xạ dữ liệu giữa node; tham chiếu liên node chỉ có ở v1 `$step.port` (`executor.py:19`).
- `he_kieu.py:22-29`: 15 kiểu: text number integer boolean json file · image video audio document · model_ref connection_ref artifact_ref workflow_ref secret_ref; hậu tố `[]`; một luật ép `T→T[]` (`:55-67`); `xuat_luat_noi_day()` cho client (`:129`). Không ai ngoài test gọi (publish không kiểm kiểu).
- `artifact.py`: id `"<backend>:<key>"` backend ∈ {local, r2} (`:23,44`), TTL_CLASS EPHEMERAL 6h/RUN 7d/PROJECT 90d/PERMANENT (`:31-38`), lineage `created_by_snapshot_id`. `het_han` chỉ khai trong governance (`governance.py:545`); không ai ghi danh artifact trong đường chạy thật.

## 6. Waitpoint

- Loại khai (chỉ comment): DELAY | JOB | WEBHOOK | HUMAN | CHILD_RUN | BARRIER (`models.py:1390`); mã chỉ dùng BARRIER (`join.py:171`). Không EVENT.
- Tín hiệu: `UNIQUE(waitpoint_id, seq)` chống cộng đôi (`cho_doi.py:274-288`); `da_mo()` tính lại từ bảng tín hiệu nên tín hiệu-đến-trước không mất (không có "đăng ký sau"). Resume: không có mã resume; `wakeup` UNIQUE(run,node_run,kind,due_at) (`danh_thuc.py:362-377`), `nhat()` chỉ đánh `claimed_at`, không khoá (`:401-417`). Nhả worker: không áp dụng — không worker nào chạy.
- **LỖI**: JOIN `ALL` niêm phong ngay lúc tạo (`join.py:176-177`) và `da_mo` với ALL chỉ đòi *mọi tín hiệu đã có* đều xong (`cho_doi.py:329-331`); `so_nhanh` chỉ nằm ở `output_ref` và không được đọc ⇒ ALL 3 nhánh **mở sau tín hiệu đầu tiên**. Test `test_join_ALL_ANY_N_of_M...` (tests, dòng 161-175) chỉ kiểm `sealed`, không kiểm `da_mo`.
- `ttl()` đánh EXPIRED waitpoint nhưng không đánh thức/huỷ node nào (`dieu_phoi.py:178-184`).

## 7. Trigger

`trigger.py:82-84`: MANUAL, API, WEBHOOK (không lịch) + SCHEDULE (`moi_giay` giây, **không phải cron**). Không dedupe (không UNIQUE/idempotency), `den_han()` chỉ đọc, không ai gọi; không cập nhật `next_fire_at`. **Không có route HTTP webhook trigger**; không bộ quét cron. Chỉ "API" có thật dưới dạng `trigger_kind="api"` (`server/api/workflows.py:219`).

## 8. Credit / quote

- Hold 1 lần/run: `tien.giu_cho_run` luỹ đẳng theo `hold_id=run.id` (`tien.py`), gọi ở `server/api/workflows.py:241` cùng transaction; settle ở `ket_so` (`ket_so.py`) khi run kết thúc; SYSTEM_FAILURE hoàn toàn bộ.
- Trần ForEach: `max_items` bắt buộc, `max_items × tổng thân` (`bao_gia.py` `_tran_node` FOREACH), nhánh lấy max; `VuotTran` trước khi chạy (`foreach.py:49`).
- **GAP lớn**: giá node = `params.gia` hoặc 10 cố định (`bao_gia.py` `_GIA_MAC_DINH=10`, `_gia_node`) — **client tự đặt giá**, không đọc registry/ToolSpec. **Lệch hình dạng**: đồ thị v3 là `{"pages":[{nodes,edges}]}` (`di_tru_m1.py:131`, `drafts_v3.py:45-48`), nhưng `/api/v1 .../quotes` báo giá `ver.graph.get("nodes")` (`server/api/workflows.py:141`) ⇒ luôn **0 credit** → `giu_cho_run` bỏ qua khi 0 ⇒ run không giữ credit nào. Cùng lý do `_sinh_chi_muc` (`dinh_nghia.py:162-175`) không sinh hàng `workflow_version_node/edge` cho bản v3. Publish nội bộ thì báo giá `pages[0].nodes` (`drafts_v3.py:162`) — hai cửa hai con số.

## 9. Subworkflow

Không có. Chỉ dấu vết: kiểu `workflow_ref` (`he_kieu.py:28`), waitpoint kind `CHILD_RUN` và wakeup kind `child_run` (comment `models.py:1390,1486`). Không ghim version con, không chặn đệ quy. Ghim version run cha: có (`WorkflowRun.version_id`, `_ban_publish` `server/api/workflows.py:91-104`).

## 10. Log sự kiện

`node_run_snapshot` = chuỗi chỉ-thêm có `previous_snapshot_id`, `is_valid`, `attempt_number`, `cost_credit` (`thi_hanh.py:42-89`); `node_run` là con trỏ. Bất biến **chỉ theo quy ước** — không trigger CSDL / listener chặn UPDATE (grep rỗng). Không có bảng event workflow riêng (chỉ `JobEvent` `models.py:589` cho job; v1 dùng `append_decision` vào AgentRun `agent/runs.py:97`).

## 11. Endpoint

- `/api/v1` (API key, `server/api/workflows.py`): `POST /workflows/{id}/quotes` :127 · `POST /workflows/{id}/runs` :167 · `GET /runs/{id}` :251 · `POST /runs/{id}/cancel` :261 · `GET /runs/{id}/artifacts` :281. Không có list workflows/runs, không CRUD workflow qua API công khai.
- `/agent` v3 (session): `GET|POST /api/v3/workflows`, `GET|PUT /api/v3/workflows/{id}`, `POST .../{id}/publish` (`drafts_v3.py:76-139`). Không có run v3 (chủ ý, `drafts_v3.py:21-26`).
- `/agent` v1/v2 (AgentWorkflow/AgentRun): workflows CRUD+snapshots (`routes/workflows.py:18-84`), validate/clone/archive/export/import/activity (`library.py`), runs create/approve/restore/list/get/again/tick/cancel/artifact/bundle (`runs.py:28-180`), assistant plan/preview/apply, sharing, admin runs/metrics/cancel, legacy HTML (`legacy_runs.py`).

## 12. Credential / HTTP node / connector

Chưa có gì cho workflow: không bảng credential/connection, không HTTP node, không connector. Có sẵn để dùng lại: `platform_core/secretbox.py` (Fernet `ma_hoa/giai_ma/preview` :55-70) và bộ chặn SSRF của webhook công khai `platform_core/public_api/webhooks.py:86-150`. Kiểu `connection_ref`/`secret_ref` chỉ là tên trong `he_kieu.py:28`.

## Tài liệu vs mã

- Tài liệu 31 ghi Đợt 1–5 "✅" nhưng tự nhận chưa nối (`31:1073,1177`); đúng với mã. 5.5 (`/api/v1/workflows/{id}/runs`) từng ghi "BỊ CHẶN" (`31:1487`) nhưng nay **đã mắc thật** và nhận tiền/khởi tạo run không ai chạy.
- `canh.py` (middleware quyền WF-903) tồn tại, fail-closed, **không ai gọi** ⇒ chưa có kiểm quyền lúc thi hành cho v2.
- `dieu_khien.py` nói "8 loại chạy trong scheduler" — không có scheduler.
