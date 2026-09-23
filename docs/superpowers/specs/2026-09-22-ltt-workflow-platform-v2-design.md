# LTT Workflow Platform V2 — Đặc tả thiết kế

```
Mã            ADR-WF-002 (bổ sung ADR-WF-001, không thay thế)
Ngày          2026-09-22
Trạng thái    CHỜ PHÊ DUYỆT — chưa có dòng mã sản phẩm nào theo đặc tả này
Nhánh         phien/wf-v2 (BASE_SHA 5f936d01)
Phụ lục       docs/architecture/workflow_v2_audit/32_AUDIT_2026-09-22_*.md (6 báo cáo audit, file:dòng)
```

Đặc tả này là **nguồn chân lý duy nhất** cho Workflow Platform V2 từ ngày trên.
`docs/architecture/workflow_v2_audit/23_24`, `25_26`, `27_29` vẫn đúng ở mọi chỗ
đặc tả này không nói khác; chỗ nào hai bên khác nhau, **đặc tả này thắng**, và
§23 liệt kê từng chỗ khác.

---

## 0. Bốn quyết định của chủ dự án (22/09/2026)

| # | Câu hỏi | Chốt | Hệ quả thiết kế |
|---|---|---|---|
| Q1 | Bỏ chốt F4 *"LTT không phải Zapier"*? | **(c)** — pipeline AI/media trước, connector chỉ là cửa vào/ra; tự động hoá tổng quát **sau khi có số đo** | Runtime tối ưu cho *ít node đắt*; node inline đúng + tất định, không tối ưu thông lượng; catalog connector hẹp (§11.6) |
| Q2 | Connector chạy bằng gì? | **(b)** — runner Node chạy piece Activepieces ghim version, allowlist | §11: runner LTT tự viết, **không** dùng engine Activepieces; runner là một loại job |
| Q3 | OAuth? | **(c)** — chỉ đăng ký OAuth app **Google** (YouTube là đầu ra chính); dịch vụ khác dùng token | §9: khung OAuth2 thật, provider đầu tiên Google; Sheets/Drive vòng đầu dùng service account; Gmail ra khỏi phase 8 |
| Q4 | Node không-AI tính tiền thế nào? | **(a)** — control/data miễn phí; HTTP + connector tính credit cố định mỗi lượt; hạn mức số node/run | §7 |

---

## 1. Vì sao

Bằng chứng (audit 22/09, `main@5fc64f03`, chi tiết ở phụ lục):

1. **Hai mô hình, một động cơ.** Runtime duy nhất đang chạy là
   `platform_core/agent/executor.py:tick()` (Plan v1, trần cứng 4 step, trạng
   thái một khối JSON), nuôi bằng job `agent.advance` tự nộp lại mỗi 2 s
   (`apps/agent/jobs.py`). Lõi V2 (`platform_core/workflow/`, 19 mô-đun, 12 bảng,
   migration `a4f81c2d6b95`…`e8f35c1a7d64`) có đủ nguyên hàm nhưng **không ai
   gọi** `dieu_phoi.mot_vong` ngoài test; cờ `LTT_WORKFLOW_V2` không bao giờ bật.
2. **Canvas lưu v3, chạy v2.** `CanvasShell.tsx` lưu qua `/agent/api/v3/workflows`
   (bảng `workflow_draft`), nút Run gọi `/agent/api/workflows/{id}/runs` đọc bảng
   `agent_workflows`.
3. **Tiền sai ở cửa công khai.** `server/api/workflows.py:141` báo giá
   `graph["nodes"]` trong khi đồ thị v3 là `{"pages":[…]}` ⇒ luôn 0;
   `bao_gia._gia_node` lấy giá từ `params.gia` do client đặt.
4. **Thiếu hẳn**: động cơ, cầu nối node→job, thi hành node điều khiển, subworkflow,
   cron, webhook trigger, credential, HTTP, connector, `{{ }}`, NodeRenderer theo
   loại. Toàn bộ 22 tệp test V2 chạy **SQLite**.
5. **Lỗi đã biết trong mã chưa nối**: JOIN `ALL` mở sau tín hiệu đầu
   (`join.py:176` niêm phong lúc tạo, `cho_doi.da_mo` không đọc `so_nhanh`).

Tầng nền thì trưởng thành và **giữ nguyên**: hàng đợi job (`SKIP LOCKED`, lọc sức
chứa, dedupe, reclaim, aging), sổ credit append-only, lease GPU ba tầng,
`registry.py` (ToolSpec đã có 6 trường V2), `storage.py`, Public API.

---

## 2. Phạm vi

**Trong phạm vi (phase 0–13, §19):** một runtime; hợp đồng node; node điều khiển +
dữ liệu; waitpoint bền; trigger; biểu thức; credential + OAuth2 Google; node HTTP;
runner connector với allowlist; node AI; Agent Designer; Supervisor có luật;
Canvas V2; quan sát + replay.

**Ngoài phạm vi (không làm, không dựng chỗ chờ):** marketplace; node do cộng đồng
viết; node Code; sandbox chạy mã người dùng; APP_WEBHOOK của piece (Slack sự kiện
thời gian thực); Gmail; catalog piece ngoài allowlist; vòng `while`/`break`/
`continue`; tự động hoá tổng quát cho thông lượng lớn (Q1: làm sau khi đo).

---

## 3. Kiến trúc và ranh giới

```text
Canvas ─┐  Agent Designer ─┐  /api/v1 ─┐  Trigger Engine (manual·api·webhook·cron·event·poll) ─┐
        └────────► workflow_draft.document (v3, soạn thảo) ──COMPILER──► workflow_version.graph
                                                              (BẤT BIẾN, graph_hash, bảng giá đóng băng)
                                 VALIDATOR tất định: kiểu cổng · chu trình · quyền · credential_ref · trần tiền
                                                          │
                          workflow_run ─► ĐỘNG CƠ (platform_core/workflow/dong_co.py)
                                          nhặt wakeup (SKIP LOCKED) → tính node sẵn sàng →
                                          chuyển trạng thái → ghi snapshot → (nộp job | tự tính inline)
                     ┌────────────────────────┴─────────────────────────┐
              NODE INLINE (trong động cơ)                   NODE JOB (hàng đợi sẵn có)
              core.if · switch · join · foreach ·            app.* (19 ToolSpec) · core.http ·
              set · transform · filter · aggregate ·         piece.* (runner Node) · connector.youtube.* ·
              stop · delay · wait · human · output           ai.* · (core.call_workflow = run con)
              — không I/O, không tiền                        └► job_submit.submit_with_credit(origin="workflow")
                                                               jobs.complete/fail/cancel ──(cùng transaction)──►
                                                               waitpoint_signal + wakeup ──► động cơ
                     ═════════ NỀN — GIỮ NGUYÊN ═════════
                     jobs · job_scheduler · leases · gpu_lease · gpu_claims · credit · registry · storage
```

### 3.1 Tám luật ranh giới

1. **Một runtime.** `platform_core/workflow/` là runtime chuẩn duy nhất. Agent
   executor v1 bị gỡ trong phase 1 (§17). Không lớp tương thích.
2. **Động cơ không làm I/O.** Việc có mạng, GPU, tiền hoặc tiến trình con đều thành
   job. Động cơ chỉ đọc/ghi CSDL.
3. **Tầng nền không biết workflow.** Cầu nối đi một chiều: `jobs.py` gọi đúng một
   hàm `workflow.cau_noi.bao_ket_thuc(db, job)` khi `job.origin == "workflow"`;
   không mô-đun nào khác của tầng nền import `platform_core.workflow`
   (ngoại lệ đã có: `registry.py` dùng `bieu_thuc`, `credit.py` dùng `RUN_KET_THUC`).
4. **Nền tảng không biết tên app.** Node app sinh từ ToolSpec; node piece sinh từ
   catalog piece; Canvas render theo `kind`, không theo tên. Phép kiểm cơ học §18.4.
5. **Product App ≠ node.** `AppManifest` quyết định trang chủ. Node `core.*`,
   `piece.*`, `connector.*` không bao giờ có trang chủ.
6. **Workflow JSON không chứa bí mật.** Chỉ `credential_ref` (id). Bí mật chỉ giải
   mã trong tiến trình job, ngay trước lời gọi (§9.4).
7. **Media không đi qua trạng thái.** Mọi tệp là `artifact_ref` (`<backend>:<key>`,
   `workflow/artifact.py`). Snapshot chỉ giữ tham chiếu.
8. **LLM không nằm trên đường thi hành bắt buộc.** Run đã publish chạy xong được khi
   mọi LLM chết, trừ node `ai.*` (node đó FAILED, nhánh `error` đi tiếp).

---

## 4. Hợp đồng chuẩn

### 4.1 Tài liệu soạn thảo (draft) và đồ thị biên dịch (version)

`workflow_draft.document` giữ nguyên hình dạng v3 hiện tại (`version: 3`, `pages[]`,
mỗi trang `nodes[]`, `edges[]`, `viewport`…). **Trang chỉ là tab bố cục**:

- `id` node duy nhất trên **toàn tài liệu** (validator từ chối trùng).
- Cạnh **không được** nối khác trang (validator từ chối).
- Biên dịch gộp **mọi trang** thành một đồ thị. (Chấm dứt khiếm khuyết *"chỉ trang
  đang mở được chạy"*.)

Node trong draft:

```json
{"id": "n_sheet", "type": "piece.google-sheets.find_rows", "type_version": 1,
 "position": {"x": 0, "y": 0}, "label": "Đọc Sheet",
 "params": {"spreadsheet_id": "…", "only_status": "{{ workflow.input.trang_thai }}"},
 "credential_ref": "cred_7f…", "settings": {"retry": {"max": 2}, "timeout_s": 120,
 "on_error": "fail"}}
```

Cạnh trong draft: `{"id","source_node","source_port","target_node","target_port","kind"}`
(khoá v3 hiện có — `di_tru_m1._canh_v3`, `workflowApi.edgeToV3`),
`kind ∈ {DATA, CONTROL, ERROR}`, thêm `"condition"` (chỉ trên cạnh CONTROL ra từ
`core.if`/`core.switch`, là tên nhánh — không phải biểu thức; §5.4).

`workflow_version.graph` là **đầu ra của compiler** (`platform_core/workflow/bien_dich.py`),
không phải bản sao draft:

```json
{"schema": "ltt.workflow/3",
 "inputs":  [{"name": "trang_thai", "kieu": "text", "required": false, "default": "READY"}],
 "outputs": [{"name": "video", "kieu": "video", "from": "n_out.video"}],
 "settings": {"max_concurrency": 4, "timeout_s": 21600, "on_finally": ""},
 "nodes": [ {"id","type","type_version","params","credential_ref","settings",
             "gia_tran": 12, "thi_hanh": "job"} ],
 "edges": [ {"id","source_node","source_port","target_node","target_port","kind","condition"} ],
 "thu_tu": ["n_trigger", "n_sheet", "…"],
 "bang_gia": {"n_sheet": 2, "n_video": 80}}
```

`graph_hash = sha256(json chuẩn hoá của graph trừ vị trí/nhãn)`, `UNIQUE(workflow_id,
graph_hash)` (đã có). Compiler **bắt buộc** sửa hai chỗ đang đọc `graph["nodes"]`
theo hình `pages` (`server/api/workflows.py:141`, `dinh_nghia._sinh_chi_muc`) —
sau phase 1, mọi nơi đọc `workflow_version.graph` đọc hình dạng trên, không đọc
`pages`.

### 4.2 Vòng đời phiên bản

```
Draft ──validate──► (kết quả kiểm, không lưu trạng thái) ──publish──► Published (workflow_version, bất biến)
                                                                          │ workflow.published_version_id trỏ tới
Workflow ──archive──► Archived (workflow.archived_at; không nhận run mới; run đang chạy chạy nốt)
```

"Validated" không phải trạng thái lưu: validate là hàm thuần, publish gọi lại nó
trong cùng transaction. Run **luôn** ghim `version_id`. Publish bản mới **không**
đổi run đang chạy.

### 4.3 Định danh và phiên bản node

`type` = `<không_gian>.<tên>`; `type_version` = số nguyên.

| Không gian | Nguồn | Ví dụ | `type_version` lấy từ |
|---|---|---|---|
| `core.*` | `platform_core/workflow/nut_loi/*.py` | `core.if` | khai trong mã |
| `app.*` | ToolSpec (`registry.py`) | `app.image.generate` | `ToolSpec.type_version` |
| `ai.*` | node lõi bọc ToolSpec AI | `ai.llm` | khai trong mã |
| `piece.*` | `connector_runner/catalog.json` | `piece.google-sheets.find_rows` | major của version piece đã ghim |
| `connector.*` | Python native | `connector.youtube.upload` | khai trong mã |
| `trigger.*` | node lõi | `trigger.cron` | khai trong mã |

Luật: thay đổi **phá vỡ** `params`/cổng ⇒ tăng `type_version`. Registry giữ **mọi**
`type_version` còn được version đã publish tham chiếu; bỏ một version chỉ được khi
không còn version publish nào dùng (phép kiểm §18.4). Node lạ/khác version lúc
compile ⇒ từ chối publish, không đoán.

### 4.4 NodeDefinition

Không lưu vào CSDL; là **khung nhìn dẫn xuất** do `platform_core/workflow/nut.py`
dựng từ ba nguồn (§4.5). Một dataclass đóng băng:

| Trường | Kiểu | Nghĩa |
|---|---|---|
| `type`, `type_version` | str, int | §4.3 |
| `kind` | `trigger\|control\|data\|app\|ai\|connector\|subworkflow` | nhóm render + palette |
| `category` | str | nhóm palette: `TRIGGERS FLOW DATA NETWORK AI LTT_APPS CONNECTORS SUBWORKFLOWS` |
| `title`, `description`, `icon` | str | hiển thị (i18n qua `_()`) |
| `cong_vao`, `cong_ra` | tuple[`Cong`] | cổng có kiểu (`he_kieu.Cong`: tên, kiểu, bắt buộc, nhiều cạnh) |
| `tham_so` | dict | **JSON Schema 2020-12 tập con** (§4.6) — form Canvas sinh từ đây |
| `thi_hanh` | `inline\|job\|run_con` | §5 |
| `job_type` | str | với `job` |
| `side_effect` | `none\|external\|irreversible` | từ ToolSpec hoặc khai |
| `idempotency_key_fields` | tuple[str] | trường tham số tạo khoá khử trùng |
| `resource` | dict | `{class, vram_min_mb, slots, est_duration_s}` từ ToolSpec |
| `timeout_expr` | str | biểu thức `bieu_thuc` trên `params` |
| `retry_mac_dinh` | `{max:int, backoff_s:int}` | mặc định node |
| `gia` | `Gia` | `mien_phi` \| `co_dinh(n)` \| `theo_registry(job_type)` (§7) |
| `credential` | tuple[str] | kiểu credential chấp nhận (§9.1); rỗng = không cần |
| `quyen` | frozenset | `network credential gpu filesystem subprocess` (§15.1) |
| `mock` | Callable\|None | kết quả giả cho dry-run (§18.1) |
| `cho` | tuple[str] | loại waitpoint node có thể tạo (§5.7) |
| `ma_loi` | tuple[str] | mã lỗi node công bố (§5.6) |

### 4.5 Ba nguồn NodeDefinition — không nguồn nào trùng

1. **Node lõi** (`core.*`, `trigger.*`, `ai.*`, `connector.*`): mỗi node một hàm
   đăng ký trong `platform_core/workflow/nut_loi/`. Đây là nơi duy nhất khai chúng.
2. **Node app** (`app.*`): `nut.tu_toolspec(tool)` đọc ToolSpec — **không** sao chép
   trường nào ra chỗ khác. ToolSpec thêm hai trường tuỳ chọn (sửa `registry.py`):
   - `cong: dict = {}` — `{"vao": {...}, "ra": {...}}` ánh tên tham số/khoá kết
     quả sang kiểu cổng; rỗng ⇒ adapter suy: mỗi thuộc tính `params_schema` là
     cổng vào kiểu suy từ JSON Schema, `returns` là cổng ra.
   - `workflow: bool = True` — `False` ẩn tool khỏi palette workflow (thay cho
     việc lọc tên trong Canvas).
   Tool chỉ lên palette workflow khi khai đủ `side_effect`, `idempotency`,
   `resource` (hôm nay 4/19; phase 2 khai đủ 19 — §19).
3. **Node piece** (`piece.*`): `connector_runner/catalog.json` sinh lúc build bằng
   lệnh `node connector_runner/xuat_catalog.js` từ `piece.metadata()` của các piece
   trong allowlist, **commit vào kho**, và phép kiểm §18.4 so nó với
   `package-lock.json`. `nut.tu_piece(muc)` dựng NodeDefinition từ đó.

`nut.tat_ca()` hợp ba nguồn; trùng `type` ⇒ `RegistryError` lúc khởi động.

### 4.6 Lược đồ tham số

Tập con JSON Schema: `type ∈ {string, number, integer, boolean, object, array}`,
`enum`, `minimum`, `maximum`, `maxLength`, `maxItems`, `items`, `properties`,
`required`, `default`, `description`, và ba khoá mở rộng:

- `x-ltt-kieu`: kiểu cổng (`image`, `video[]`, `artifact`, `model_ref`…) khi giá trị
  là tham chiếu.
- `x-ltt-control`: gợi ý widget (`textarea`, `code-json`, `credential`, `dropdown-dong`).
- `x-ltt-dong`: nguồn lựa chọn động **theo một tham số khác của cùng node** —
  `{"nguon": "piece_property", "prop": "…"}` (runner `run_property`, §11) hoặc
  `{"nguon": "app_property", "prop": "…"}` (`params_schema` khai `depends_on`;
  vd `taovideo.resolution` hợp lệ tuỳ `model` đã chọn, giải qua
  `providers.model_capabilities`). ⛔ `"nguon"` là marker gửi client, không phải
  tên trường nội bộ — palette test cấm tên cơ chế (`tuy_chon_dong`,
  `sync_executor`, …) rò ra JSON công khai (plan 02, Task 8).

  ⛔ **Không nhầm với `ToolSpec.tuy_chon_dong`** (enum động theo NGƯỜI DÙNG, vd
  giọng nhân bản của chính họ). Cơ chế đó KHÔNG sinh `x-ltt-dong`: palette giải
  nó ngay lúc phục vụ (`resolve_params_schema(db=, user_id=)`) và trả thẳng
  `enum` + `x-ltt-nhan`. `enum: []` nghĩa là "bạn chưa có lựa chọn nào" — vẫn
  khác `string` tự do, và sự khác đó chính là GENERIC_GAP D10.

Mọi giá trị `params` có thể là literal hoặc chuỗi biểu thức `{{ … }}` (§6). Validator
kiểm literal theo lược đồ lúc publish; giá trị biểu thức kiểm lúc thi hành, sau khi tính.

### 4.7 Cổng và kiểu

Giữ `he_kieu.py` (15 kiểu + hậu tố `[]` + luật ép `T→T[]`), thêm:

- Kiểu `any` (nối được với mọi kiểu; chỉ cho node `core.*` dữ liệu).
- Kiểu `table` = `json[]` có `x-ltt-cot` (tên cột) — không phải kiểu nền mới.
- Kiểu `event` cho cổng ra của trigger.
- PORT `types_compatible()` + `TYPE_MIGRATIONS` của Langflow (MIT, ~15 dòng) vào
  `he_kieu.ep_duoc` cho bảng ép đổi tên kiểu; ghi notice ở `THIRD_PARTY_NOTICES.md`.

`image`, `video`, `audio`, `file`, `document` ở tầng dữ liệu **luôn** là
`artifact_ref` + metadata (`mime`, `size_bytes`, `w/h/duration` nếu có) — không bao
giờ là byte. Validator publish gọi `he_kieu.noi_duoc` cho **mọi** cạnh DATA (hôm nay
không ai gọi). Canvas lấy luật từ `GET /agent/api/v3/luat-noi-day`
(`he_kieu.xuat_luat_noi_day()`), không tự chép.

---

## 5. Runtime

### 5.1 Động cơ

Mô-đun mới `platform_core/workflow/dong_co.py`. Một **job nền đơn** `workflow.dong_co`
(khai trong `apps/agent/manifest.py` — app `agent` là chủ UI Canvas và các job điều
phối; `dedupe_key="workflow:dong_co"`, `origin="workflow"`) chạy một vòng rồi tự nộp
lại với `next_run_at = min(wakeup.due_at kế tiếp, now + 2 s)` khi còn việc — cùng
khuôn `agent.advance` nhưng **một job cho cả hệ**, không một job mỗi run. Hết việc thì
không nộp lại; `tao_run` và `cau_noi.bao_ket_thuc` nộp nó khi có việc mới (khử trùng
chỉ cho job chưa kết thúc ⇒ luôn tối đa một job chờ). Lưới đỡ: `AppManifest.bao_tri`
của app `agent` (mỗi 60 s, dưới lease bảo trì) nộp lại job động cơ nếu có wakeup tới
hạn mà không có job động cơ nào đang chờ/chạy.

Một vòng (`dong_co.mot_vong(db, gioi_han=50)`):

```
1. NHẶT: SELECT … FROM wakeup WHERE claimed_at IS NULL AND due_at <= now
         ORDER BY due_at LIMIT :n FOR UPDATE SKIP LOCKED     (chỉ số bộ phận đã có)
2. Với mỗi run có wakeup (khoá hàng workflow_run FOR UPDATE SKIP LOCKED — run đang
   được vòng khác xử lý thì bỏ qua, wakeup vẫn chưa claim):
   a. đọc graph (cache theo version_id, bất biến) + con trỏ node_run
   b. áp tín hiệu mới: waitpoint mở ⇒ node WAITING → RUNNING/SUCCEEDED/FAILED
   c. lan truyền: tính tập node READY (§5.4), SKIPPED (§5.5)
   d. thi hành node READY: inline ⇒ tính ngay trong transaction; job ⇒ nộp job;
      run_con ⇒ tạo run con. Tôn trọng trần song song (§5.9)
   e. run kết thúc? ⇒ chuyen_run(...) ⇒ ket_so trong cùng transaction (đã có)
   f. đánh claimed_at cho các wakeup đã dùng
3. COMMIT mỗi run một transaction (lỗi một run không kéo run khác).
4. ttl(): run quá settings.timeout_s ⇒ TIMED_OUT; waitpoint quá hạn ⇒ tín hiệu
   TIMED_OUT (§5.7).
```

Nhiều worker cùng chạy `workflow.dong_co` là **an toàn** nhờ `SKIP LOCKED` cả hai
tầng; dedupe_key giữ bình thường chỉ một job chờ. `LISTEN/NOTIFY` (kênh
`workflow_wakeup`) chỉ để worker giữ job động cơ thức sớm; mất NOTIFY không mất việc.
Node inline được xử lý **liên tiếp trong cùng vòng** tới khi gặp node job/wait (giới
hạn 500 bước inline mỗi run mỗi vòng, vượt thì để vòng sau — chống vòng vô hạn).

Cờ `LTT_WORKFLOW_V2` bị gỡ ở phase 1 (không còn đường cũ để chọn).

### 5.2 Máy trạng thái run

```
CREATED → QUEUED → RUNNING ⇄ WAITING → {SUCCEEDED, FAILED, CANCELLED, TIMED_OUT, SYSTEM_FAILURE}
CREATED → FAILED            (validate/tiền thất bại trước khi chạy)
QUEUED  → CANCELLED
```

- `VALIDATING` bị gỡ (validate chạy lúc publish; tạo run chỉ kiểm tiền + quyền).
- Chuẩn hoá chữ hoa: giá trị mặc định cột `workflow_run.status` đổi `"queued"` →
  `"CREATED"`; migration đổi các hàng cũ.
- `WAITING` = mọi node chưa kết thúc đều đang WAITING (không node nào READY/QUEUED/
  RUNNING). Động cơ tự chuyển RUNNING⇄WAITING sau mỗi vòng.
- Vào trạng thái kết thúc ⇒ `ket_so` cùng transaction (đã có, `may_trang_thai:229`).

### 5.3 Máy trạng thái node

| Trạng thái | Nghĩa |
|---|---|
| `PENDING` | chưa đủ đầu vào |
| `READY` | đủ đầu vào, chờ động cơ thi hành (trần song song) |
| `QUEUED` | job đã nộp, chưa worker nhặt |
| `RUNNING` | job đang chạy, hoặc node inline đang tính (chỉ trong transaction) |
| `WAITING` | có ≥1 waitpoint mở (thay tên `RUNNING_WITH_WAITPOINTS`) |
| `RETRY_SCHEDULED` | lần thử hỏng, lần thử kế có `wakeup.due_at` |
| `SUCCEEDED` · `FAILED` · `SKIPPED` · `CANCELLED` · `ABANDONED` | kết thúc |

`ABANDONED` giữ lại: lần thử của node `irreversible` kết thúc **mơ hồ** (§5.6) — khác
`FAILED` vì hệ không biết side effect đã xảy ra hay chưa.

**`RESUMING` không phải trạng thái lưu.** Resume = một transaction: nhặt wakeup →
đọc tín hiệu → chuyển WAITING→(RUNNING|SUCCEEDED|FAILED). Không có khoảng nào quan sát
được giữa hai bước, nên một trạng thái trung gian chỉ tạo thêm một hàng snapshot
không mang thông tin. Sự kiện `NodeResumed` vẫn được ghi (§5.11).

Chuyển hợp lệ (`NODE_CHUYEN`, thay bảng hiện có):

```
PENDING  → READY | SKIPPED | CANCELLED
READY    → QUEUED | RUNNING | WAITING | SKIPPED | CANCELLED
QUEUED   → RUNNING | CANCELLED | FAILED(job hỏng trước khi chạy)
RUNNING  → SUCCEEDED | FAILED | WAITING | RETRY_SCHEDULED | ABANDONED | CANCELLED
WAITING  → RUNNING | SUCCEEDED | FAILED | CANCELLED
RETRY_SCHEDULED → READY | CANCELLED
```

Chuyển sai ⇒ `chuyen_node` ghi snapshot `is_valid=False`, con trỏ đứng yên, trả
`False` (giữ nguyên cơ chế đang có). Thêm: trigger CSDL trên PostgreSQL chặn
`UPDATE`/`DELETE` bảng `node_run_snapshot` (migration phase 1); SQLite dùng listener
`before_flush` từ chối — bất biến hết là quy ước.

### 5.4 Lan truyền và điều kiện

- Node READY khi **mọi** cổng vào bắt buộc có cạnh DATA từ node SUCCEEDED, và mọi
  cạnh CONTROL vào (nếu có) đã được **kích hoạt**.
- Node `core.if` xuất nhánh `true`/`false`; `core.switch` xuất nhánh theo tên khai.
  Cạnh CONTROL mang `condition = "<tên nhánh>"`; chỉ cạnh khớp nhánh được kích hoạt.
  (Chốt `Q1` của ADR-WF-001 — *điều kiện trên cạnh* — cụ thể hoá thành: **biểu thức
  nằm trong node if/switch, cạnh chỉ mang tên nhánh**. Một nơi viết biểu thức, một
  nơi hiện trên Canvas.)
- `skip_if` cấp node (biểu thức) giữ: đúng ⇒ SKIPPED.
- Cạnh `ERROR` ra từ cổng `error` của mọi node: kích hoạt khi node FAILED với
  `settings.on_error = "route"`. `on_error ∈ {fail (mặc định), route, continue}`;
  `continue` ⇒ node coi như SUCCEEDED với output `{error: {...}}`.

### 5.5 Lan truyền SKIPPED

Node PENDING mà **không còn đường nào** có thể kích hoạt nó (mọi nguồn đã kết thúc,
và ít nhất một cổng bắt buộc/cạnh CONTROL cần không bao giờ tới) ⇒ SKIPPED, lan tiếp.
`core.join` với `mode=ANY/N_OF_M` nhận nhánh SKIPPED là "không tới", không phải lỗi.

### 5.6 Lỗi, thử lại, idempotency, side effect

Bảo đảm **viết ra** (không hứa exactly-once với bên ngoài):

| Tầng | Bảo đảm |
|---|---|
| Lập lịch node | at-least-once |
| Side effect `external` | at-least-once **cộng** khoá idempotency gửi cho provider nếu provider hỗ trợ |
| Side effect `irreversible` | at-most-once khi kết quả mơ hồ ⇒ `ABANDONED`, không tự thử |
| Bút toán credit | exactly-once theo run (hold id = run id, đã có) |

Khoá:

- `attempt_id` = `node_run_snapshot.id` của lần chuyển vào RUNNING.
- `idempotency_key` của node = `sha256(run_id, node_id, loop_index, attempt_number
  nếu side_effect=none, ngược lại các trường idempotency_key_fields đã tính)`; đi vào
  `job.dedupe_key` (chặn nộp đôi khi job còn chạy) và vào `params["_idem"]` để job
  handler chuyển cho provider (chặn side effect đôi khi thử lại `external`).
- Job giữ nguyên retry của nó (`max_attempts`, backoff mũ, reclaim). **Retry node**
  chỉ xảy ra khi job đã kết thúc ERROR: `settings.retry = {max ≤ 5, backoff_s}`,
  mặc định `{max: 0}` (retry job đã đủ cho lỗi tạm).
- Job kết thúc với `provider_state = ambiguous`:
  `none` ⇒ RETRY_SCHEDULED; `external` ⇒ RETRY_SCHEDULED với **cùng**
  idempotency_key; `irreversible` ⇒ `ABANDONED`, nhánh `error` với mã
  `ket_qua_mo_ho`, không bao giờ tự thử.

Mã lỗi node công bố (`NodeError.ma`): `dau_vao_sai`, `bieu_thuc_loi`, `het_gio`,
`vuot_tran_bao_gia`, `thieu_credential`, `credential_bi_thu_hoi`, `bi_chan_mang`,
`provider_loi`, `ket_qua_mo_ho`, `bi_huy`, `loi_he_thong`. Lỗi hệ thống (lỗi của
LTT) ⇒ run `SYSTEM_FAILURE`, hoàn toàn bộ hold (đã có).

### 5.7 Waitpoint

Bảng `waitpoint`/`waitpoint_signal`/`node_run_waitpoint`/`wakeup` giữ nguyên, thêm
cột `waitpoint.het_han_luc` (hạn chờ, NULL = không hạn) và `waitpoint.che_do_het_han`
(`fail|route|approve|reject`). Loại:

| `kind` | Tạo bởi | Mở khi | Tín hiệu |
|---|---|---|---|
| `DELAY` | `core.delay` (`duration_s` hoặc `until`) | `due_at` tới | động cơ tự ghi khi nhặt wakeup `kind=delay` |
| `JOB` | mọi node job | job kết thúc | `cau_noi.bao_ket_thuc` (§5.8) |
| `WEBHOOK` | `core.wait` `mode=webhook` | POST vào URL resume | route §8.3 |
| `EVENT` | `core.wait` `mode=event` | sự kiện khớp bộ lọc | bộ phát sự kiện §8.4 |
| `HUMAN` | `core.human` | người duyệt/nhập | route `POST /agent/api/v3/runs/{id}/human/{wp}` |
| `BARRIER` | `core.join` | đủ theo policy | tín hiệu từ node nguồn |
| `CHILD_RUN` | `core.call_workflow` | run con kết thúc | `ket_so` của run con |

**Worker được nhả**: node job đợi = waitpoint JOB; không worker nào giữ chỗ trong lúc
chờ. `core.delay` **không bao giờ** `sleep`: ghi waitpoint + wakeup rồi kết thúc
vòng. Delay ≤ 60 s vẫn đi cùng đường (không có đường tắt trong bộ nhớ — một đường
duy nhất để kiểm).

**Tín hiệu tới trước khi WAITING** (race): tín hiệu ghi vào `waitpoint_signal` theo
`waitpoint_id`; waitpoint được **tạo trước** khi nộp job/phát URL (cùng transaction
chuyển node sang WAITING hoặc QUEUED). Do đó không tồn tại tín hiệu cho waitpoint chưa
có. `da_mo()` tính lại từ bảng tín hiệu mỗi lần ⇒ thứ tự tới không quan trọng.
`UNIQUE(waitpoint_id, seq)` chống cộng đôi; tín hiệu từ nguồn bên ngoài dùng
`seq = hash ổn định của idempotency_key` của nguồn (webhook: header
`Idempotency-Key` hoặc sha256 thân).

**Resume luỹ đẳng**: wakeup `UNIQUE(run_id, node_run_id, kind, due_at)` (đã có) +
khoá hàng run khi xử lý + chuyển node kiểm trạng thái hiện tại ⇒ nhặt hai lần cùng
wakeup cho kết quả như một lần (lần hai: chuyển sai bị ghi `is_valid=False`, không
đổi gì).

**Sửa lỗi JOIN ALL** (phase 1): BARRIER lưu `so_nguon` (số cạnh vào) vào cột mới
`waitpoint.so_nguon`; `da_mo` với ALL = `số tín hiệu kết thúc == so_nguon`;
`sealed` chỉ đặt khi mọi nguồn đã kết thúc hoặc SKIPPED. Test đối chứng: ALL 3 nhánh,
1 tín hiệu ⇒ chưa mở.

**Hết hạn**: `ttl()` ghi tín hiệu `TIMED_OUT`; node xử lý theo `che_do_het_han`
(`core.human` mặc định `reject`, `core.wait` mặc định `fail`).

### 5.8 Cầu nối job ↔ node

Nộp (`platform_core/workflow/cau_noi.py::nop_job`), một transaction:

1. tạo waitpoint `JOB` + `node_run_waitpoint`;
2. `gia_that = registry.credit_for(job_type, params_da_tinh)` (node `co_dinh`: giá
   khai); `gia_that > bang_gia[node]` ⇒ node FAILED `vuot_tran_bao_gia`, dừng;
3. `jobs.submit(..., origin="workflow", plan_id=run.id, parent_id=waitpoint.id,
   dedupe_key=idempotency_key, params=params_da_tinh, admission_resource=…)` —
   **`jobs.submit`, không phải `submit_with_credit`**: run đã giữ một lần (§7.2;
   `tien.py` + `test_965` chốt *đúng một* `CREDIT_HOLD` mỗi run). Job không có hold
   riêng nên `job_runner._quyet_toan_credit`/`_hoan_credit` tự bỏ qua (chúng đã kiểm
   `credit.so_da_giu(job.id) == 0`) — không cần sửa `job_runner`;
4. node → QUEUED, snapshot mang `job_id` và `gia_that`.

Bước 1–4 **cùng một transaction**: đây là thứ bảo đảm *một attempt = một job*.
`jobs.submit` chỉ khử trùng job **chưa kết thúc** cùng `dedupe_key`; nó không phải
chốt idempotency sau khi job xong — chốt đó là transaction này cộng với việc node đã
rời READY.

Kết thúc (`jobs.complete/fail/cancel` → `cau_noi.bao_ket_thuc(db, job)` khi
`job.origin == "workflow"`), cùng transaction với việc đóng job:

1. `waitpoint_signal(waitpoint_id=job.parent_id, seq=1, status, result_ref)`;
2. chi phí: job DONE ⇒ `chi_phi = min(result.credit_cost nếu handler báo, ngược lại
   gia_that; bang_gia[node])`, ghi `snapshot.cost_credit`, cộng
   `workflow_run.actual_cost` (`tien.ghi_chi_phi_node`); job ERROR/CANCELLED ⇒ 0 —
   cùng luật với job đơn lẻ (thành công thu, thất bại hoàn);
3. `wakeup(run_id=job.plan_id, node_run_id=…, kind="job", due_at=now)`.

`job.step_id` (String(32)) **không** dùng — id node dài tới 64 ký tự (bài học M-1:
`"m1:"+id` 39 ký tự vào cột 36). Cột `plan_id`/`parent_id` đủ 36.

Kết quả job → output node: `result` chuẩn hoá qua `cong_ra` của NodeDefinition; khoá
nào là tệp ⇒ đăng ký `artifact` (`created_by_snapshot_id`), output giữ `artifact_ref`.
Output JSON > 256 KB ⇒ lưu thành artifact `kind=json`, output giữ ref.

### 5.9 ForEach, Join, song song

- `core.foreach`: vào `items` (`T[]`), tham số `max_items` (bắt buộc, ≤ 1000),
  `parallelism` (1–16, mặc định 4). Thân = **một subworkflow đã publish**
  (`body_workflow`, ghim version) *hoặc* một chuỗi node nằm giữa `foreach` và
  `core.foreach_end` trên cùng trang. Mỗi phần tử một `foreach_muc` (đã có, giành bằng
  SQL — commit R1). Namespace `loop.item`, `loop.index`.
  Kết quả: `core.foreach_end` ra `results` (`T[]`, theo chỉ số) + `errors`.
  `on_item_error ∈ {fail, skip, collect}`.
- `core.join`: `mode ∈ {ALL, ANY, N_OF_M}`, `n`, `release_on_first_failure`.
- Trần song song bốn tầng, mỗi tầng `behavior ∈ {QUEUE, FAIL}`: run
  (`settings.max_concurrency`, mặc định 4) · người dùng (`settings.py`:
  `WF_MAX_RUN_DONG_THOI_MOI_NGUOI = 5`) · node (`parallelism`) · **tài nguyên** — tầng
  thật sự chặn, do `jobs.claim` lọc sức chứa (đã có). Động cơ **không** giữ GPU; nó
  chỉ nộp job.

### 5.10 Subworkflow

`core.call_workflow`: tham số `workflow_id`, `version_id` (ghim lúc **publish cha**:
compiler thay `"latest"` bằng id version publish hiện tại, ghi vào graph cha),
`inputs` (ánh xạ biểu thức), `wait = true`.

- Run con: `workflow_run` thêm cột `parent_run_id`, `parent_node_id`, `do_sau`
  (độ sâu). `do_sau ≤ 5`.
- Chặn chu trình **lúc publish**: compiler duyệt đồ thị gọi qua các version đã ghim;
  gặp lại `workflow_id` đang duyệt ⇒ từ chối. Vì version con bất biến và ghim, không
  có chu trình mới xuất hiện sau publish.
- Tiền: `estimated_max` con cộng vào trần node cha lúc báo giá; run con **không giữ
  hold riêng** — chi phí ghi vào hold của run gốc (`hold_id` kế thừa).
- Quyền: run con chạy dưới `owner_id` của run cha; chỉ gọi được workflow cùng chủ
  (chia sẻ workflow qua lại giữa người dùng: ngoài phạm vi).
- Huỷ cha ⇒ huỷ con (đệ quy, cùng transaction huỷ). Con FAILED ⇒ node cha FAILED
  (lỗi mang `child_run_id`). Retry node cha = một run con **mới**.

### 5.11 Nhật ký sự kiện

Khuyến nghị cho LTT hiện tại: **ảnh chụp trạng thái + chuỗi chỉ-thêm**, không phải
event sourcing thuần (không replay để dựng trạng thái — ADR-WF-001 đã đo, Temporal
chỉ *đếm* vi phạm tất định, không cần cho LTT).

- Cấp node: `node_run_snapshot` **là** nhật ký (mỗi chuyển một hàng, cả chuyển bị từ
  chối). Tên sự kiện suy ra từ `(trạng thái trước, trạng thái sau)`.
- Cấp run: bảng mới `workflow_event` (chỉ thêm): `id, run_id, seq, loai, node_id,
  du_lieu (JSON đã che), created_at`, `UNIQUE(run_id, seq)`. Loại: `WorkflowStarted
  TriggerReceived NodeResumed WaitpointOpened WaitpointSignalled BudgetChecked
  SupervisorDecision WorkflowCompleted WorkflowFailed WorkflowCancelled`.
- Cùng bảng làm **outbox** cho trigger `event` (§8.4).
- TTL: 90 ngày cho run kết thúc (gộp vào `purge_expired` hiện có).

---

## 6. Biểu thức và ánh xạ dữ liệu

### 6.1 Cú pháp

Giá trị tham số là chuỗi có `{{ … }}`:

- Chuỗi **chỉ gồm một** `{{ expr }}` ⇒ giá trị có kiểu (số, danh sách, object…).
- Chuỗi trộn chữ ⇒ nối chuỗi, mỗi `{{ }}` ép `to_string`.
- `\{{` là chữ thường.

`expr` là **tập con biểu thức Python**, phân tích bằng `ast.parse(mode="eval")` và
**duyệt AST với danh sách nút cho phép** — mở rộng `bieu_thuc.py` đang có (không eval,
không `compile`, không `getattr` động):

- literal: số, chuỗi, `true/false/null` (và `True/False/None`), list, dict;
- tham chiếu: `Name` thuộc namespace §6.2, `.thuoc_tinh`, `[chi_so]`, `["khoa"]`;
- toán tử: `+ - * / // %`, so sánh, `and or not`, `in`, `not in`, `x if c else y`;
- gọi hàm: **chỉ** tên trong bảng §6.3, không keyword tuỳ ý ngoài bảng.

Cấm: lambda, comprehension, gán, `**`, truy cập thuộc tính bắt đầu `_`, gọi phương thức
của đối tượng.

Chọn tự viết (mở rộng `bieu_thuc.py`) thay vì `simpleeval`/Jinja2 sandbox/JMESPath
vì: (a) đã có bộ duyệt AST đã test; (b) `simpleeval` có lịch sử thoát sandbox; Jinja2
sandbox không trả kiểu và không tất định theo phiên bản; JMESPath chỉ là truy vấn,
không có toán tử số học/chuỗi cần cho mapping; (c) một ngôn ngữ duy nhất cho cả
`timeout_expr`, `skip_if`, if/switch, mapping.

### 6.2 Namespace (chỉ đọc)

| Tên | Nội dung |
|---|---|
| `trigger` | payload trigger đã che (`body`, `headers` an toàn, `query`, `fired_at`) |
| `workflow.input` | đầu vào run (theo `graph.inputs`) |
| `vars` | biến do `core.set` ghi (§6.5) |
| `nodes.<id>.output.<cổng>` | output node **tổ tiên** đã SUCCEEDED |
| `nodes.<id>.status`, `.error` | trạng thái/lỗi node tổ tiên |
| `loop.item`, `loop.index`, `loop.total` | trong thân ForEach |
| `run.id`, `run.started_at`, `run.owner` | metadata run |
| `params` | tham số của chính node (cho `timeout_expr`) |

Không có `env`, không có `credentials`, không có `now()`: thời điểm dùng
`run.started_at` hoặc `trigger.fired_at` ⇒ tính lại cho kết quả như nhau.

Validator lúc publish: mọi tham chiếu `nodes.X` phải là **tổ tiên** của node dùng nó
(nếu không: lỗi `tham_chieu_khong_phai_to_tien`); cổng phải tồn tại trong
NodeDefinition của X. ⇒ Tham chiếu tới output **có kiểu**; Canvas autocomplete dùng
đúng dữ liệu này.

### 6.3 Hàm (bảng đóng, `platform_core/workflow/ham_bieu_thuc.py`)

Chuỗi: `len lower upper trim split join replace contains starts_with ends_with
substring slugify`. (Không có hàm regex: `re` của Python có thể quay lui thảm hoạ
với mẫu do người dùng viết; khi cần sẽ thêm cùng một engine không quay lui, không
phải trong đặc tả này.) Số: `to_number round floor ceil abs min max sum`.
Kiểu: `to_string to_bool to_int is_null default coalesce type_of`. JSON: `json_parse
json_string`. Danh sách: `first last slice sort sort_by(list, "khoa") unique
pluck(list, "khoa") flatten range(n ≤ 1000) count`. Object: `keys values get(obj,
"a.b", mac_dinh) merge pick omit`. Ngày: `date_parse(s, fmt, tz) date_format(d, fmt,
tz) date_add(d, n, "day|hour|minute") date_diff(a, b, don_vi)` — múi giờ bắt buộc
tường minh, mặc định `Asia/Ho_Chi_Minh`.

### 6.4 Ép kiểu, giới hạn, lỗi

- Không ép ngầm giữa chuỗi và số trong `+` (`"1" + 1` ⇒ lỗi `kieu_khong_khop`); dùng
  `to_number`. So sánh khác kiểu ⇒ `false` với `==`, lỗi với `<`.
- Giới hạn: 10.000 nút AST được thăm mỗi lần tính; kết quả ≤ 1 MB; chuỗi ≤ 1 MB;
  độ sâu lồng ≤ 32. Vượt ⇒ `bieu_thuc_loi`.
- Lỗi mang `vi_tri` (cột), `bieu_thuc` (đã cắt 200 ký tự), `ly_do` tiếng Việt — cùng
  khuôn `LoiBieuThuc` đang có.
- Tính ở động cơ (inline) hoặc ngay trước khi nộp job; tham số đã tính lưu vào
  snapshot RUNNING (để replay/xem lại).

### 6.5 Trạng thái workflow

Không có trạng thái sửa được dùng chung. `vars` = gộp output của mọi `core.set` là
**tổ tiên** của node đang tính, theo thứ tự `graph.thu_tu`. Hai `core.set` ghi cùng
khoá mà không có quan hệ tổ tiên ⇒ validator từ chối (`ghi_bien_xung_dot`). ⇒ Tất
định, không khoá, không cần cột trạng thái run.

---

## 7. Tiền

### 7.1 Giá node (Q4 = a)

| Loại | `gia` | Giá trị khởi đầu |
|---|---|---|
| `core.*` điều khiển/dữ liệu, trigger | `mien_phi` | 0 |
| `core.http` | `co_dinh` | 1 credit/lượt |
| `piece.*` action | `co_dinh` | 2 credit/lượt |
| `piece.*` trigger poll | `mien_phi` (hạn mức §7.3) | 0 |
| `connector.youtube.upload` | `co_dinh` | 5 credit/lượt |
| `app.*`, `ai.*` | `theo_registry` = `registry.credit_for(job_type, params)` | theo bảng giá hiện hành |

Giá cố định khai trong **NodeDefinition**, đổi qua mã + review. Không còn đọc
`params.gia` (xoá `bao_gia._GIA_MAC_DINH` và `_gia_node`).

### 7.2 Báo giá, giữ, kết sổ

- Báo giá lúc publish = **trần tất định** `estimated_max` (đã có) tính lại theo luật:
  - node `theo_registry` có tham số là biểu thức: tham số ảnh hưởng giá mà có `enum`
    ⇒ lấy max trên enum; có `maximum` ⇒ dùng `maximum`; không có cả hai ⇒ **từ chối
    publish** (`khong_bao_gia_duoc`, chỉ rõ tham số). Tham số ảnh hưởng giá = tham số
    mà đổi giá trị làm `credit_for` đổi — xác định bằng cách gọi `credit_for` trên
    các mẫu biên của lược đồ (`bao_gia.tham_so_anh_huong_gia`).
  - nhánh if/switch: **tổng mọi nhánh có thể chạy** (không phải max — sai khi hai
    nhánh cùng chạy qua join ANY).
  - ForEach: `max_items × trần thân`; subworkflow: `estimated_max` của version con.
- Tạo run ⇒ `tien.giu_cho_run(run)` giữ **một lần** `estimated_max` (đã có).
- Mỗi node job trước khi nộp: `gia_that = credit_for(params đã tính)`;
  `gia_that > bang_gia[node]` ⇒ node FAILED `vuot_tran_bao_gia` (không bao giờ thu
  vượt phần đã duyệt). Chi phí thật ghi `snapshot.cost_credit` khi job kết thúc.
- Run kết thúc ⇒ `ket_so` thu tổng thật, hoàn phần dư (đã có, `M10`).

### 7.3 Hạn mức (`platform_core/settings.py`, đổi được không cần deploy mã)

`WF_MAX_NODE_MOI_WORKFLOW = 200` · `WF_MAX_RUN_DONG_THOI_MOI_NGUOI = 5` ·
`WF_MAX_RUN_MOI_NGAY_MOI_NGUOI = 500` · `WF_MAX_TRIGGER_POLL_MOI_NGUOI = 20` ·
`WF_POLL_TOI_THIEU_S = 300` · `WF_WEBHOOK_MOI_PHUT_MOI_TRIGGER = 60`.

---

## 8. Trigger

### 8.1 Mô hình

`workflow_trigger` (đã có) thêm cột: `version_mode ∈ {published, pinned}`,
`pinned_version_id`, `cursor` (JSON — trạng thái poll), `last_fired_at`,
`loi_lien_tiep` (int). Kích hoạt = `enabled=true` **và** workflow có bản publish.
Trigger bắn ⇒ tạo run bằng **đúng đường** của `/api/v1/workflows/{id}/runs`
(`platform_core/workflow/tao_run.py::tao_run` — một hàm, ba cửa gọi: API, trigger,
Canvas), `trigger_kind` = loại, `idempotency_key` = khoá khử trùng trigger.

| Loại | Kích hoạt | Khoá khử trùng |
|---|---|---|
| `manual` | Canvas "Run" | `ui:<request_id>` |
| `api` | `POST /api/v1/workflows/{id}/runs` | header `Idempotency-Key` |
| `webhook` | §8.3 | `Idempotency-Key` hoặc `sha256(body)` + phút |
| `cron` | §8.2 | `cron:<trigger_id>:<thời điểm lịch ISO>` |
| `event` | §8.4 | `evt:<trigger_id>:<workflow_event.id>` |
| `poll` (piece) | §11.4 | `poll:<trigger_id>:<id bản ghi từ piece>` |

`UNIQUE(owner_id, idempotency_key)` trên `workflow_run` (đã có) chặn trùng. Sửa lỗi
route API: tra cứu theo đúng khoá của chỉ mục `(owner_id, key)`; trùng khoá khác
workflow ⇒ `409 idempotency_conflict`, không 500.

### 8.2 Cron

Thư viện `croniter` (MIT, duy trì bởi pallets-eco, bản 6.2.4 tháng 07/2026) — thêm
vào `requirements.txt`. Cấu hình `{"cron": "0 7 * * *", "tz": "Asia/Ho_Chi_Minh",
"bo_lo": "chay_mot_lan|bo_qua"}`. Động cơ mỗi vòng đọc `next_fire_at <= now`
(`FOR UPDATE SKIP LOCKED`), tạo run, đặt `next_fire_at` kế tiếp. Lỡ lịch (máy tắt):
`chay_mot_lan` ⇒ một run cho mốc lỡ gần nhất; `bo_qua` ⇒ không run bù. Chu kỳ tối
thiểu 5 phút. Trigger `SCHEDULE` theo giây hiện có bị thay bằng `cron`.

### 8.3 Webhook

Route `POST /hooks/wf/{trigger_id}` (router mới trong `server/`, ngoài `/api/v1` —
không đụng 24 route đóng băng). Xác thực: header `X-LTT-Token` so với
`sha256` lưu trong `config.token_hash` (so hằng thời gian); tuỳ chọn HMAC
`X-LTT-Signature` với bí mật lưu trong credential. Thân ≤ 1 MB, JSON hoặc form;
lớn hơn ⇒ 413. Trả `202 {"run_id"}` ngay (không đợi run). Hạn mức §7.3 ⇒ 429.
`core.webhook_response` (trả thân tuỳ biến cho người gọi) **chỉ** có hiệu lực khi
trigger cấu hình `phan_hoi = "dong_bo"` và run kết thúc trong 25 s; quá hạn ⇒ 202 như
thường (Cloudflare cắt ở 100 s — không bao giờ giữ kết nối lâu).

Resume URL cho `core.wait mode=webhook`: `POST /hooks/wp/{waitpoint_id}` + token một
lần (`waitpoint.token_hash`, đã có cột).

### 8.4 Event

Nguồn sự kiện trong phạm vi: **chỉ** `workflow.run.finished` (dòng
`WorkflowCompleted/Failed/Cancelled` của `workflow_event`) — đủ để nối workflow này
sau workflow khác. Sự kiện của job ngoài workflow (`job.finished` theo tool) **không**
làm: nó buộc `jobs.py` ghi vào bảng của workflow cho mọi job, phá luật §3.1-3.
Bộ lọc: biểu thức §6 trên `event` (`event.workflow_id`, `event.status`,
`event.outputs`). Động cơ quét `workflow_event` theo con trỏ lưu ở `trigger.cursor`
(`created_at` + `id` của dòng cuối đã xử lý).

---

## 9. Credential và OAuth

### 9.1 Mô hình

Bảng mới `credential`:

```
id (36) · owner_id · kieu (api_key|bearer|basic|oauth2|google_service_account|piece_custom)
· nha_cung_cap (google|slack|notion|github|http|…) · ten · bi_mat_ma_hoa (Text, Fernet)
· pham_vi (JSON: scopes) · meta (JSON, không bí mật: email tài khoản, hạn token)
· het_han_luc · thu_hoi_luc · dung_lan_cuoi · created_at · updated_at
```

- Mã hoá: `secretbox.ma_hoa` (Fernet). Xoay khoá: `secretbox` đổi sang `MultiFernet`
  đọc danh sách khoá từ `secrets/` (khoá mới đứng đầu), lệnh
  `python tools/xoay_khoa_credential.py` mã hoá lại mọi hàng. (Không dùng mã hoá hai
  tầng kiểu n8n: một chủ máy, một kho khoá — tầng thứ hai không thêm ranh giới nào.)
- Sở hữu: một người dùng. Chia sẻ credential: **không** (ngoài phạm vi).
- Workflow chỉ lưu `credential_ref`. Validator publish: ref phải thuộc `owner_id` của
  workflow, chưa thu hồi, `kieu` nằm trong `NodeDefinition.credential`.
- Thu hồi = đặt `thu_hoi_luc` + xoá `bi_mat_ma_hoa` (ghi đè chuỗi rỗng). Node gặp ref
  đã thu hồi ⇒ FAILED `credential_bi_thu_hoi`.
- Nhật ký: bảng `credential_nhat_ky(credential_id, hanh_dong, run_id, node_id,
  created_at)` — tạo/sửa/thu hồi/làm mới/dùng. Không bao giờ ghi bí mật.

### 9.2 API credential

`/agent/api/v3/credentials`: `GET` (liệt kê, chỉ `meta` + `preview`), `POST` (tạo),
`PUT /{id}` (thay bí mật), `POST /{id}/test` (gọi thử qua job, không lộ bí mật),
`DELETE /{id}` (thu hồi). Session + CSRF như các route v3 khác.

### 9.3 OAuth2 (Google trước — Q3)

- App OAuth Google do chủ dự án đăng ký; `client_id/secret` nằm trong `secrets/`
  (không vào CSDL, không vào kho). Scope vòng đầu: `youtube.upload`,
  `youtube.readonly`.
- Luồng: `GET /agent/api/v3/oauth/google/bat-dau` ⇒ tạo `oauth_state` (bảng mới:
  `state_hash, owner_id, provider, pkce_verifier_ma_hoa, redirect_after, het_han_luc`
  10 phút, dùng một lần) ⇒ chuyển hướng Google (PKCE S256) ⇒
  `GET /oauth/callback/google` ⇒ đổi code, lưu credential `oauth2`.
- Làm mới: trong job, `credential.lay_de_dung(db, ref)` khoá hàng `FOR UPDATE`; nếu
  `het_han_luc < now + 5 phút` ⇒ làm mới, ghi lại, commit ngắn, rồi mới trả token.
  Hai job cùng lúc ⇒ một người làm mới, người kia đọc token mới.
- `invalid_grant` ⇒ đánh dấu `meta.can_ket_noi_lai = true`, node FAILED
  `credential_bi_thu_hoi`, UI hiện nút kết nối lại.
- ⚠️ Vận hành (đã tra 22/09): app Google ở chế độ **Testing** phát refresh token hết
  hạn sau **7 ngày**; `youtube.upload` là scope nhạy cảm cần xác minh app để lên
  Production. Việc của chủ dự án, ghi ở §19 phase 7 (điều kiện ra phase).

### 9.4 Tiêm và che bí mật

- Chỉ **tiến trình job** gọi `credential.lay_de_dung`. Động cơ, validator, API không
  bao giờ giải mã.
- Bí mật truyền cho runner Node qua **stdin** của tiến trình con, không qua biến môi
  trường, không qua dòng lệnh.
- Che: `job_events.redact_details` (đã có) mở rộng — mọi chuỗi bằng bí mật đang dùng
  trong job được thay `«đã che»` trong `result`, `error`, log. Header
  `authorization`, `cookie`, `set-cookie`, `x-api-key`, `proxy-authorization` luôn
  bị che trong output HTTP.
- Phép kiểm §18.3: tiêm bí mật mồi vào 5 đường lỗi, khẳng định không xuất hiện trong
  `node_run_snapshot`, `workflow_event`, `job_events`, log tệp.

---

## 10. Node HTTP (`core.http`, job `workflow.http`, lane CPU nhẹ)

Tham số: `method`, `url`, `query` (object), `headers` (object), `body_type
(none|json|form|text|artifact)`, `body`, `auth` (`credential_ref` kiểu
`api_key|bearer|basic`), `timeout_s` (1–120, mặc định 30), `response_type
(auto|json|text|artifact)`, `follow_redirects` (≤ 5), `ok_status` (mặc định 2xx).
Phân trang: **không** trong phase 7 (dùng ForEach + subworkflow).

Đầu ra: `status`, `headers` (đã che), `body` (json/text ≤ 5 MB; lớn hơn hoặc
`artifact` ⇒ `artifact_ref`, trần 100 MB), `duration_ms`, `request` (`method`,
`url` đã che query nhạy cảm, `bytes_sent`).

SSRF — tách `public_api/webhooks.validate_target` thành
`platform_core/mang_an_toan.py` (một nguồn, webhook công khai gọi lại chính nó):

- chỉ `http`/`https`, cổng 80/443/8080/8443;
- phân giải DNS **một lần**, từ chối mọi địa chỉ loopback, private (RFC1918, ULA),
  link-local, CGNAT, multicast, `0.0.0.0/8`, metadata cloud; **ghim IP** cho kết nối
  (`httpx` transport với địa chỉ đã phân giải + SNI theo host) — chặn DNS rebinding;
- mỗi lần chuyển hướng kiểm lại từ đầu;
- ngoại lệ nội bộ: **không có** (node HTTP không bao giờ gọi được dịch vụ trên máy A/B).

Retry mặc định: job `max_attempts=3` cho lỗi mạng/5xx với method `GET/HEAD/PUT/DELETE`;
`POST/PATCH` chỉ thử lại khi người dùng đặt `Idempotency-Key` header. Node HTTP khai
`side_effect = external`.

---

## 11. Connector

### 11.1 Hình dạng runner (Q2 = b)

```
connector_runner/                    (Node 22 LTS, TypeScript biên dịch sẵn)
  package.json · package-lock.json   ghim @activepieces/pieces-framework + từng piece (phiên bản chính xác)
  allowlist.json                     {piece: version} — nguồn duy nhất
  src/runner.ts                      một lần chạy = một lệnh
  src/xuat_catalog.ts                sinh catalog.json từ piece.metadata()
  catalog.json                       commit; §4.5
```

Runner **không** dùng engine/worker/API của Activepieces; gọi thẳng
`action.run(ctx)` / `trigger.run(ctx)` / `property.options(ctx)`.

Giao thức: Python (`platform_core/workflow/connector.py`) mở một tiến trình con
`node dist/runner.js`, ghi **một** JSON vào stdin, đọc **một** JSON từ stdout, stderr
vào log (đã che).

```json
// vào
{"op": "run_action|run_trigger|run_property|trigger_on_enable|trigger_on_disable",
 "piece": "@activepieces/piece-google-sheets", "version": "0.14.2",
 "name": "find_rows", "props": {...đã tính...}, "auth": {...đã giải mã...},
 "store": {"<khoá>": <giá trị>}, "tmp_dir": "C:\\LTTPlatform\\data\\tmp\\conn\\<job_id>",
 "han_ms": 110000}
// ra
{"ok": true, "output": {...}, "store_ops": [{"op": "put|delete", "key": "…", "value": …}],
 "files": [{"path": "…", "name": "…", "mime": "…"}], "logs": ["…"]}
{"ok": false, "error": {"ma": "provider_loi|dau_vao_sai|het_gio", "thong_diep": "…", "status": 429}}
```

`ctx` runner dựng: `auth`, `propsValue`, `store` (trong bộ nhớ từ `store`, ghi lại
thành `store_ops`), `files.write` (ghi vào `tmp_dir`, trả đường dẫn), `server`
(`publicUrl` của LTT), `run.id`. **Không** hỗ trợ `run.createWaitpoint`/`run.pause`:
action dùng chúng bị loại khỏi allowlist (phép kiểm tĩnh trong `xuat_catalog`).

### 11.2 Cô lập trên Windows (máy A là production)

- Mỗi lệnh một tiến trình con, gán vào **Windows Job Object** (qua `ctypes`,
  `platform_core/workflow/job_object.py`): `JOB_OBJECT_LIMIT_PROCESS_MEMORY` 512 MB,
  `JOB_OBJECT_LIMIT_ACTIVE_PROCESS` 4, `KILL_ON_JOB_CLOSE`; Node chạy với
  `--max-old-space-size=384`. Thời gian: `han_ms` + giết cứng sau 120 s.
- CPU: job `workflow.connector` chạy trên lane riêng với `admission_resource =
  "connector"` trần 2 slot đồng thời trên máy A.
- Mạng đi ra: runner cài `undici` global dispatcher kiểm đích bằng cùng luật
  `mang_an_toan` (bản TS sinh từ cùng danh sách dải chặn, phép kiểm §18.4 so hai bản).
- Chạy dưới tài khoản dịch vụ worker hiện có; `tmp_dir` xoá sau mỗi lệnh.

### 11.3 Chuỗi cung ứng

`npm ci --ignore-scripts` từ `package-lock.json` lúc **cài đặt/deploy**
(`setup/2-cai-dat.ps1` thêm bước; Node bản portable ghim SHA256 trong
`setup/node-version.txt`). Không cài gì lúc chạy. Nâng version piece = sửa
`allowlist.json` + lock + `catalog.json` trong một commit, chạy smoke test §18.2, ghi
`THIRD_PARTY_NOTICES.md`. Phép kiểm: gói nào trong lock không thuộc cây phụ thuộc
của allowlist ⇒ đỏ.

### 11.4 Store, file, trigger poll

- Store: bảng mới `connector_store(owner_id, pham_vi, khoa, gia_tri JSON,
  updated_at)`, `pham_vi = "trigger:<id>"` hoặc `"run:<id>"`. Python áp `store_ops`
  trong cùng transaction đóng job.
- File: Python chuyển từng tệp trong `files` sang `storage.py` ⇒ `artifact`, output
  thay đường dẫn bằng `artifact_ref`.
- Poll: trigger `poll` (piece trigger kiểu POLLING) có `trigger.config.chu_ky_s ≥ 300`.
  Động cơ nộp job `workflow.connector` `op=run_trigger` khi tới hạn; mỗi bản ghi mới
  ⇒ một run (khoá khử trùng §8.1). `trigger_on_enable/disable` gọi khi bật/tắt.
  5 lần lỗi liên tiếp ⇒ tự tắt trigger + thông báo người dùng.
- Trigger WEBHOOK/APP_WEBHOOK của piece: ngoài phạm vi (§2).

### 11.5 Auth piece

`PieceAuth` → `credential.kieu`: `SecretText` → `api_key`; `BasicAuth` → `basic`;
`CustomAuth` → `piece_custom` (JSON theo `props` của auth, form sinh từ lược đồ);
`OAuth2` → `oauth2` **chỉ** khi provider là Google (Q3), ngược lại piece đó chỉ dùng
đường CustomAuth/SecretText thay thế.

### 11.6 Allowlist vòng đầu

| Piece | Auth dùng | Action/trigger đưa lên palette (phần còn lại ẩn) |
|---|---|---|
| `google-sheets` | service account (`piece_custom`) | find_rows, get_rows, insert_row, update_row, clear_row · trigger poll new_row |
| `google-drive` | service account | upload_file, create_folder, list_files, share_file |
| `slack` | bot token | send_message_to_a_channel, send_direct_message, upload_file |
| `notion` | integration token | create_database_item, update_database_item, find_database_item · trigger poll new_database_item |
| `github` | token cá nhân | create_issue, create_comment_on_issue |
| `airtable` | token | find_record, create_record, update_record |
| `telegram-bot` | bot token | send_text_message, send_media |
| `discord` | bot token / webhook url | send_message_webhook |

Tên action chính xác chốt ở bước đầu phase 8 bằng `xuat_catalog` (danh sách trên là
đích; action không tồn tại ở phiên bản ghim thì bỏ, không thay bằng action khác mà
không review).

`connector.youtube.upload` (Python native, `httpx`, REST resumable upload): piece
YouTube của Activepieces **không có** action upload (đã kiểm ở tag 0.90.2:
`download-caption, get-channel, get-video, list-captions, list-comments,
list-playlist-items, list-playlists, search`). Tham số: `video` (artifact_ref),
`title`, `description`, `tags`, `privacy (private|unlisted|public)`,
`category_id`, `thumbnail` (artifact_ref, tuỳ chọn), `publish_at` (tuỳ chọn).
`side_effect = irreversible` ⇒ mơ hồ thì `ABANDONED`, không tự đăng lại.

---

## 12. AI, Agent Designer, Supervisor

### 12.1 Node AI (phase 10) — bọc ToolSpec có sẵn, không runtime AI mới

| Node | Bọc | Ghi chú |
|---|---|---|
| `ai.llm` | `text.chat` | ra `text`; `json_schema` tuỳ chọn ⇒ ra `json` đã kiểm |
| `ai.extract` | `text.chat` + lược đồ bắt buộc | kết quả không khớp lược đồ ⇒ FAILED `dau_ra_sai_luoc_do` |
| `ai.router` | `text.chat` | chọn **một** nhánh trong enum khai sẵn (`ai_choice`, ADR Q8); không khớp ⇒ nhánh `mac_dinh` |
| `ai.vision` | tool ảnh→chữ hiện có qua registry (tool có `cong.vao` kiểu `image`) | nếu registry chưa có tool nào như vậy lúc phase 10 ⇒ node không lên palette |
| `ai.agent` | executor agent có giới hạn (§12.3) | |

`core.if` **không bao giờ** gọi LLM; chỉ `ai.router` gọi.

### 12.2 Agent Designer (phase 11)

`planner.py` giữ vai, đổi đầu ra: sinh **draft v3** (§4.1) thay Plan v1, bằng
**tool-calling có lược đồ**: danh mục node (`nut.tat_ca()` rút gọn) + lược đồ
tham số là đầu vào của prompt; đầu ra đi qua đúng validator publish. Agent **không**
publish: nó ghi draft, người dùng xem báo giá rồi bấm publish. Agent không tạo
credential; draft tham chiếu credential có sẵn hoặc để trống (validator báo thiếu).
FLOW G (§18.5) là phép nghiệm thu.

### 12.3 Agent Node (phase 11)

`ai.agent`: tham số `muc_tieu`, `cong_cu_cho_phep` (danh sách `type` node job,
≤ 10), `so_buoc_toi_da` (≤ 8), `ngan_sach_credit` (bắt buộc, ≤ trần báo giá của
node), `timeout_s`, `luoc_do_dau_ra`. Mỗi lần agent gọi công cụ = một **run con**
một-node (dùng lại §5.10: tiền, quyền, credential, nhật ký). Nhật ký quyết định ghi
`workflow_event` `SupervisorDecision`/`AgentStep`. Trần báo giá node = `ngan_sach_credit`.

### 12.4 Supervisor (phase 12)

Chạy như job định kỳ đọc run đang FAILED/WAITING lâu. Hành động **được phép** (mỗi
hành động là một hàm có kiểm, ghi `workflow_event`): thử lại node (trong
`retry.max` còn lại), chọn model khác **trong enum khai sẵn của node**, đi nhánh
`error` đã khai, tạo waitpoint HUMAN hỏi người, bỏ qua nhánh node có
`settings.khong_quan_trong = true`. **Cấm** (không có hàm nào làm được): tăng hold,
sửa version đã publish, gắn credential, vượt validator, thử lại node `irreversible`
`ABANDONED`.

---

## 13. Canvas V2 và palette

### 13.1 Một đường API

Canvas chỉ gọi `/agent/api/v3/*`: workflows (đã có), `publish` (đã có), **mới**:
`POST /workflows/{id}/validate` (trả lỗi có `node_id`/`duong_dan`), `POST
/workflows/{id}/runs` (gọi `tao_run`), `GET /runs/{id}` (trạng thái + node),
`GET /runs/{id}/su-kien?sau=<seq>` (SSE, §14), `POST /runs/{id}/cancel`,
`GET /palette` (NodeDefinition rút gọn), `GET /luat-noi-day`, `GET /bieu-thuc/goi-y`
(namespace + cổng tổ tiên của một node), credentials §9.2. Gỡ mọi lời gọi
`/agent/api/workflows*` v2.

### 13.2 NodeRenderer

`src/nodes/NodeRenderer.tsx` chọn component theo `definition.kind`:
`TriggerNode` (không cổng vào) · `ControlNode` (nhiều cổng ra có tên nhánh) ·
`DataNode` · `AppNode` (ảnh xem trước, giá, tài nguyên GPU) · `ConnectorNode` (trạng
thái credential) · `AINode` · `SubworkflowNode` (tên + version ghim). Tất cả dùng một
`NodeKhung` chung (tiêu đề, cổng có kiểu từ `cong_vao/cong_ra`, huy hiệu trạng thái
run). **Không** component riêng cho từng connector/app. Xoá
`nodePresentation.ts`/`presentationAdapter.ts` hardcode slug; thông tin trình bày
đến từ NodeDefinition (`icon`, `category`, `kind`).

### 13.3 Inspector sinh từ lược đồ

`src/inspector/FormTuLuocDo.tsx` render §4.6: string/number/integer/boolean/enum/
object/array + `x-ltt-control` (textarea, code-json, credential picker, dropdown
động gọi `POST /palette/{type}/tuy-chon`). Mọi ô nhận `{{ }}` với autocomplete từ
`/bieu-thuc/goi-y`, và nút "chọn output" mở cây output tổ tiên.

### 13.4 Palette

Nhóm theo `category` (§4.4), tìm kiếm (tên, mô tả, type), thẻ node hiện: mô tả,
`type@version`, giá, tài nguyên (`resource.class`, VRAM), trạng thái credential
(đã có/thiếu). Gần đây/yêu thích lưu `localStorage`.

### 13.5 Nối dây

Client kiểm bằng luật tải từ `/luat-noi-day`; validator server là phán quyết cuối.
Cạnh mang `kind` thật (DATA/CONTROL/ERROR theo cổng nguồn), không gán cứng `DATA`.

---

## 14. Quan sát

- **Run**: trạng thái, thời điểm, thời lượng, đếm node theo trạng thái, số lần thử,
  chi phí giữ/thật, job đã nộp (liên kết timeline job hiện có), sự kiện.
- **Node Inspector** (khi xem run): tham số đã tính, output (ref artifact xem trước),
  trạng thái, attempt, thời điểm, chi phí, `resource` + worker, lỗi + mã, lịch sử
  thử lại = chuỗi snapshot.
- **Trực tiếp**: SSE `GET /agent/api/v3/runs/{id}/su-kien` đọc `workflow_event` +
  snapshot theo `seq`/thời điểm, poll CSDL 1 s phía server, đóng sau 90 s (client nối
  lại với `sau=`) — dưới trần 100 s của Cloudflare.
- **Thử lại node** (phase 13): run đang FAILED ⇒ `POST /runs/{id}/nodes/{node}/thu-lai`
  tạo attempt mới (cần hold còn đủ; không thì 402).
- **Chạy lại từ node** (phase 13): tạo run **mới** cùng version, sao output các node
  không phải hậu duệ của node chọn từ run cũ (tham chiếu artifact, không chép byte),
  chạy từ node đó. `workflow_run.chay_lai_tu_run_id` ghi nguồn gốc.
- **So sánh run**: API trả hai danh sách node với tham số/output/chi phí; UI diff.
- **Chỉ số**: `platform_core/observability.py` thêm đếm run theo trạng thái, độ trễ
  wakeup→xử lý, số wakeup chờ, số tín hiệu chuyển sai (`is_valid=False`).

---

## 15. Bảo mật

### 15.1 Quyền node

`NodeDefinition.quyen` khai năng lực; `canh.py` (middleware quyền đã có, fail-closed,
hôm nay không ai gọi) được gọi ở **hai** chỗ: validator publish (node đòi `gpu` mà gói
người dùng không có ⇒ từ chối) và `cau_noi.nop_job` (kiểm lại lúc chạy). `filesystem`
và `subprocess` chỉ cấp cho `piece.*` qua runner (trong Job Object); node khác khai
thì validator từ chối.

### 15.2 Mô hình đe doạ

| Mối đe doạ | Chặn bằng |
|---|---|
| SSRF qua `core.http` / piece | `mang_an_toan` + ghim IP + kiểm lại mỗi redirect; runner cùng luật |
| Thực thi lệnh | Không node Code; biểu thức không eval; runner không nhận mã người dùng, chỉ piece trong allowlist |
| Đọc tệp ngoài phạm vi | Runner chỉ ghi `tmp_dir`; `artifact_ref` kiểm `owner_id` khi đọc |
| Rò bí mật | §9.4 + phép kiểm tiêm bí mật mồi |
| Lấy dữ liệu người khác | Mọi truy vấn run/node/credential/artifact lọc `owner_id`; phép kiểm hai người dùng |
| Tràn tiền | Trần tất định, `vuot_tran_bao_gia`, hạn mức §7.3 |
| Webhook giả / lặp | token hash + HMAC tuỳ chọn + khoá khử trùng + hạn mức |
| Chuỗi npm | lock + `--ignore-scripts` + allowlist + phép kiểm cây phụ thuộc |
| Vòng vô hạn | DAG (chặn chu trình), `max_items`, độ sâu subworkflow 5, 500 bước inline/vòng |

---

## 16. Mô hình dữ liệu

Thêm (một migration mỗi phase chạm CSDL, đều có `downgrade`):

| Bảng/cột | Phase |
|---|---|
| `workflow_event` (§5.11) | 1 |
| trigger CSDL chặn UPDATE/DELETE `node_run_snapshot` (PostgreSQL) | 1 |
| `waitpoint.so_nguon` | 1 |
| `waitpoint.het_han_luc`, `waitpoint.che_do_het_han` | 5 |
| `workflow_run.status` mặc định `CREATED` + chuẩn hoá hàng cũ | 1 |
| `workflow_run.parent_run_id`, `parent_node_id`, `do_sau` | 4 |
| `workflow_trigger.version_mode`, `pinned_version_id`, `cursor`, `last_fired_at`, `loi_lien_tiep` | 6 |
| `credential`, `credential_nhat_ky`, `oauth_state` | 7 |
| `connector_store` | 8 |
| `workflow_run.chay_lai_tu_run_id` | 13 |

Gỡ (phase 1, sau khi cắt chuyển §17): bảng `agent_runs`, `agent_workflows`,
`agent_workflow_snapshots`, `agent_workflow_shares`; job type `agent.advance`.
Không bảng nào của tầng nền bị đổi ngoài: `jobs.complete/fail/cancel` gọi
`cau_noi.bao_ket_thuc` (mã, không lược đồ).

Không tạo bảng `node_definitions`, `idempotency_records`, `side_effect_records`,
`connector_installations`: NodeDefinition là khung nhìn dẫn xuất (§4.5); khoá
idempotency sống ở `jobs.dedupe_key` (UNIQUE) + snapshot; allowlist là tệp trong kho.

---

## 17. Di trú và cắt chuyển (phase 1)

Lớp này **chưa có khách** (CLAUDE.md, chốt 07/09) ⇒ không lớp tương thích, không cờ
bật dần. Trình tự trong **một** nhánh:

1. Đếm trên production (`tools/api_prod_canary.py` / truy vấn chỉ đọc): số
   `agent_workflows` chưa có `workflow_draft` tương ứng, số `agent_runs` chưa kết
   thúc. M-1 đã chuyển 9 bản nháp (log 31).
2. Chạy lại `di_tru_m1` (luỹ đẳng) cho mọi `agent_workflows` còn thiếu.
3. `agent_runs` đang chạy: đánh `CANCELLED` + hoàn hold (dùng `credit` sẵn có). Ghi số
   lượng vào `NHAT_KY.md`.
4. Canvas chuyển sang API v3 (§13.1) — cùng commit gỡ route v2.
5. Gỡ `agent/executor.py`, `canvas_to_plan`, `plan_to_canvas`, `AgentRun.checkpoint`,
   `apps/agent/jobs.py::advance/handle`, routes `runs.py`/`legacy_runs.py` v1; bảng
   bị drop ở migration **sau** khi deploy mã mới chạy xanh một ngày (hai bước: mã
   ngừng dùng → drop), để đường lui chỉ cần deploy lại bản trước.
6. `validator.py`, `verifier.py`, `planner.py` ở lại (planner đổi đầu ra ở phase 11;
   trong phase 1 nút "AI dựng canvas" bị ẩn nếu còn sinh Plan v1).

Đường lui phase 1: deploy lại bản trước (`app.previous\`), bảng cũ còn nguyên tới
bước drop.

---

## 18. Kiểm thử

### 18.1 Mock, dry-run, báo giá

- `mock` trên NodeDefinition (ToolSpec `mock_result`; piece: `sampleData` trong
  metadata nếu có, không thì `{}` theo lược đồ). Chế độ run `mode ∈ {that, thu,
  chi_bao_gia, chi_kiem}`:
  `chi_kiem` = validator; `chi_bao_gia` = báo giá; `thu` = chạy thật động cơ, mọi
  node job trả `mock` (không nộp job, không tiền, không GPU, không mạng).
- Connector giả: piece `@ltt/piece-gia` (trong `connector_runner/test/`) có action
  thành công/lỗi/429/chậm/mơ hồ, chỉ nạp khi `LTT_TEST=1`.
- GPU giả: job type `test.gpu_gia` (chỉ đăng ký trong test) khai `resource.class=gpu`
  để kiểm admission mà không chạm card.

### 18.2 Tầng test

| Tầng | Nội dung | Nơi |
|---|---|---|
| Đơn vị | biểu thức, compiler, validator, máy trạng thái, báo giá | SQLite, `tests/test_97x–` (dải cấp theo `check_so_test`) |
| Tích hợp động cơ | FLOW A–F + H trên động cơ thật, job mock | **PostgreSQL** (`tests/pg_scratch.py`) — bắt buộc |
| Đồng thời | hai vòng động cơ song song; 100 tín hiệu cùng lúc; wakeup nhặt đôi | PostgreSQL |
| Runner | smoke mỗi piece allowlist với piece giả + một lần thật có credential test | `connector_runner/test` + pytest đánh dấu `can_mang` |
| Frontend | vitest (renderer, form lược đồ, nối dây) + Playwright (FLOW A, E trên Canvas) | `frontend/agent-canvas` |
| Migration | up/down/up trên bản sao lược đồ production | pytest + alembic |
| Hiệu năng | §18.6 | `bench/` |

### 18.3 Bất biến phải có test **trước** khi xây phase dựa trên nó

DAG + chặn chu trình · rẽ nhánh đúng cạnh · fan-out · join ALL/ANY/N · checkpoint +
resume · hai vòng động cơ đồng thời · dedupe job · hold/kết sổ run · admission GPU ·
publish bất biến + `graph_hash` · round-trip Canvas v3 · validate node · worker chết
giữa chừng · provider mơ hồ theo 3 lớp side effect · khoá idempotency · retry node ·
connector lỗi/429 · tín hiệu trước WAITING · trigger trùng · subworkflow đệ quy/chu
trình · cách ly credential hai người dùng · SSRF (10 dải chặn + rebinding + redirect) ·
biểu thức không eval (phép thoát `__class__`, `__import__`, gọi phương thức) · bí mật
không rò.

Audit 22/09 xếp các mục đang MISSING/PARTIAL (phụ lục `audit_tests.md`); phase 1 viết
các test MISSING của nền (đồng thời PG, mơ hồ, JOIN ALL) **trước** khi viết động cơ.

### 18.4 Phép kiểm cơ học (vào gate)

- `platform_core/`, `server/`, `frontend/agent-canvas/src` không chứa tên tool/app cụ
  thể (mở rộng phép kiểm "không hardcode tên tool" hiện có sang frontend).
- Chỉ `jobs.py` (một lời gọi) import `platform_core.workflow` trong tầng nền, ngoài
  hai ngoại lệ §3.1.
- `catalog.json` khớp `allowlist.json` + `package-lock.json`.
- Danh sách dải chặn SSRF Python == bản TS.
- Mọi `type_version` được version publish tham chiếu vẫn còn trong registry.
- Không tệp nào dưới `connector_runner/` chép từ `packages/ee` hay `app/ee`.

### 18.5 Nghiệm thu nền (Definition of Done — theo đề bài §57)

| Flow | Đồ thị | Chứng minh |
|---|---|---|
| A | manual → set → if → (true) http / (false) stop | nhánh đúng, nhánh kia SKIPPED |
| B | manual → delay 120 s → http | không worker bị giữ trong lúc chờ; restart dịch vụ worker giữa chừng, run vẫn xong |
| C | input array → foreach(max 5, par 2) → app mock → foreach_end → aggregate | 5 kết quả đúng thứ tự, trần song song tôn trọng |
| D | trigger poll Sheets → filter → app | chỉ bản ghi mới tạo run; poll lần hai không trùng |
| E | app video (mock) → human → approve đi tiếp / reject đi nhánh khác | cả hai nhánh, và hết hạn ⇒ reject |
| F | trigger → call_workflow (version ghim) → output | output con về cha; huỷ cha huỷ con; chu trình bị từ chối lúc publish |
| G | câu *"Đọc Sheet mỗi sáng, lấy READY, tạo video, chờ tôi duyệt"* | Agent sinh draft v3 qua validator không lỗi, có cron + sheets + filter + foreach + video + human |
| H | run đang RUNNING và WAITING, giết worker + động cơ, khởi động lại | resume đúng, `dedupe_key` chặn nộp lại job đã xong, không side effect đôi |

Flow A–F, H chạy trên PostgreSQL; A, E thêm Playwright trên Canvas; nghiệm thu cuối
trên `https://app.lttstudios.com` bằng tài khoản test (CLAUDE.md luật 7).

### 18.6 Hiệu năng (đo trước, không tối ưu mù)

Đồ thị 100 node và 500 node (compile + validate + chạy mock); fan-out 200 phần tử;
10 run đồng thời; 100 node inline đồng thời; hỗn hợp GPU giả + CPU; wait/resume 1.000
waitpoint; Canvas 300 node (FPS kéo thả). Ngưỡng ghi vào kế hoạch từng phase, đo trên
máy A qua `chay_nang.py`.

### 18.7 Diễn tập lỗi (trước khi mở cho khách)

Restart web · restart worker · restart động cơ · CSDL mất kết nối 30 s · provider hết
giờ · provider mơ hồ · webhook trùng · tín hiệu trước WAITING · retry · huỷ · trigger
đồng thời · credential hết hạn/thu hồi · GPU bận · connector 429 · publish version mới
khi run đang chạy · subworkflow hỏng · human hết hạn.

---

## 19. Lộ trình

Mỗi phase = một kế hoạch riêng trong `docs/superpowers/plans/`, ra phần mềm chạy và
test được độc lập, gộp `main` khi test nhắm + L1/L2 xanh (hợp đồng vận hành). Đường
lui mỗi phase: deploy lại bản trước; migration có `downgrade`; bảng chỉ drop ở phase
sau khi mã mới chạy xanh.

| Phase | Kết quả chạy được | Điều kiện ra |
|---|---|---|
| **0** | Đặc tả này được duyệt | APPROVE |
| **1** Lõi | động cơ + cầu nối job + compiler + `tao_run` + Canvas trên API v3 + gỡ v1 + sửa báo giá / JOIN ALL / idempotency route + `workflow_event` + bộ test PostgreSQL | đồ thị thẳng `trigger.manual → app mock → app mock` chạy trên PG; FLOW H trên đồ thị đó; Canvas lưu–chạy cùng một bản (Playwright) |
| **2** Node SDK + Canvas | `nut.py`, adapter ToolSpec, `/palette`, `/luat-noi-day`, 19 tool khai đủ trường V2, `NodeRenderer` + `FormTuLuocDo` + palette §13 | mọi app cũ vẫn chạy qua trang app; palette sinh từ registry; phép kiểm không-hardcode-tên ở frontend xanh |
| **3** Biểu thức | `{{ }}`, bảng hàm, validator tham chiếu tổ tiên, `/bieu-thuc/goi-y`, autocomplete + picker trong Inspector | phép thoát sandbox đỏ đúng; tham chiếu không-tổ-tiên bị từ chối |
| **4** Node điều khiển | if, switch, join, foreach/foreach_end, stop, set, transform, filter, aggregate, output, call_workflow | FLOW A (HTTP **mock**), C, F |
| **5** Chờ bền | delay, wait (webhook/event), human, hết hạn, router `/hooks/*` | FLOW B, E |
| **6** Trigger | cron, webhook, event, dedupe, hạn mức | cron bắn đúng + lỡ lịch; webhook trùng không tạo 2 run |
| **7** Credential + HTTP + OAuth | vault, API credential, `core.http` + `mang_an_toan`, OAuth Google | FLOW A với HTTP thật; SSRF 10 dải; chủ dự án đã tạo app OAuth Google (việc thủ công, skill `wizard`) |
| **8** Connector | runner + Job Object + allowlist §11.6 + store + poll + `connector.youtube.upload` | FLOW D; upload YouTube thật ở chế độ private bằng tài khoản test |
| **9** Nghiệm thu runner | đo tải runner (RAM/CPU/độ trễ), diễn tập lỗi connector | báo cáo số; quyết định mở rộng catalog hay không (Q1) |
| **10** Node AI | ai.llm, ai.extract, ai.router, ai.vision | nhánh router đúng enum; lược đồ sai ⇒ FAILED |
| **11** Agent | planner ra draft v3; `ai.agent` | FLOW G |
| **12** Supervisor | hành động có luật | các hành động cấm không có đường gọi (phép kiểm) |
| **13** Quan sát | SSE, inspector run, thử lại node, chạy lại từ node, so sánh | diễn tập §18.7 đủ |
| **14** | sandbox/community/marketplace | **hoãn** — không lập kế hoạch |

Phụ thuộc: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 (5 trước 6 vì cả hai dùng router
`/hooks/*` tạo ở 5). Nhánh song song: **10 cần 2 + 3**, nên chạy cùng lúc với 4–9
(tệp riêng `nut_loi/ai_*.py`); 11 cần 4 + 10; 12 cần 11; 13 cần 5.

---

## 20. Ma trận xây / dùng lại (catalog V1)

| Node | Nhóm | Quyết định | Nguồn/Lý do |
|---|---|---|---|
| trigger.manual / api | TRIGGERS | GENERALIZE_EXISTING | `trigger.py` + route `/api/v1` có sẵn |
| trigger.webhook | TRIGGERS | BUILD_NATIVE | chưa có route; ý tưởng n8n |
| trigger.cron | TRIGGERS | BUILD_NATIVE + `croniter` | thay SCHEDULE theo giây |
| trigger.event | TRIGGERS | BUILD_NATIVE | outbox `workflow_event` |
| trigger.poll (piece) | TRIGGERS | ADAPT_ACTIVEPIECES | piece trigger POLLING qua runner |
| core.if / switch | FLOW | GENERALIZE_EXISTING | tên có ở `dieu_khien.py`, thêm thi hành |
| core.join | FLOW | GENERALIZE_EXISTING | `join.py` + sửa ALL; mẫu BarrierPolicy Activepieces |
| core.foreach / foreach_end | FLOW | GENERALIZE_EXISTING | `foreach.py` (R1) |
| core.stop | FLOW | BUILD_NATIVE | |
| core.delay | FLOW | GENERALIZE_EXISTING | waitpoint DELAY + wakeup |
| core.wait (webhook/event) | FLOW | BUILD_NATIVE | waitpoint WEBHOOK/EVENT; ADOPT Activepieces |
| core.human (duyệt/nhập) | FLOW | BUILD_NATIVE | ADOPT Flowise/Langflow HumanInput (resume bằng API, timeout định tuyến) |
| core.call_workflow | SUBWORKFLOWS | BUILD_NATIVE | CHILD_RUN |
| loop while / break / continue | FLOW | DEFER | foreach + subworkflow đủ cho Q1(c) |
| error handler / retry | FLOW | REJECT làm node | là `settings.on_error`/`retry` + cạnh ERROR + `finally` |
| core.set | DATA | BUILD_NATIVE | §6.5 |
| core.transform | DATA | BUILD_NATIVE | dựng object bằng biểu thức |
| core.filter | DATA | BUILD_NATIVE | biểu thức trên `item` |
| core.aggregate | DATA | BUILD_NATIVE | gộp danh sách/đếm/tổng |
| core.output | DATA | BUILD_NATIVE | ánh vào `graph.outputs` |
| JSON/Date/Sort/Limit/Dedupe/Type convert | DATA | REJECT làm node | là hàm biểu thức §6.3 |
| core.http | NETWORK | BUILD_NATIVE | `httpx` + `mang_an_toan` |
| core.webhook_response | NETWORK | BUILD_NATIVE | chỉ chế độ đồng bộ ≤ 25 s |
| ai.llm / extract / router / vision | AI | WRAP_LTT_APP | `text.chat`, tool ảnh |
| ai.agent | AI | BUILD_NATIVE | trên run con |
| ai.evaluator | AI | DEFER | chưa có yêu cầu đo |
| app.* (19 tool) | LTT_APPS | WRAP_LTT_APP | adapter ToolSpec |
| piece.* (8 piece) | CONNECTORS | COMPATIBILITY_RUNNER | runner Node, allowlist |
| connector.youtube.upload | CONNECTORS | BUILD_NATIVE | piece không có upload |
| Gmail | CONNECTORS | DEFER | Q3 |
| Code node | — | REJECT (tới khi có sandbox) | §2 |
| Pipeline đóng gói (vd "AI VIDEO PIPELINE") | SUBWORKFLOWS | WRAP_SUBWORKFLOW | workflow publish dùng qua call_workflow |

---

## 21. Giấy phép

| Nguồn | Giấy phép | Dùng | Ghi chú |
|---|---|---|---|
| Activepieces `packages/pieces/*`, `pieces-framework` | MIT | chạy (npm) | notice vào `THIRD_PARTY_NOTICES.md`; ⛔ `packages/ee/**`, `server/api/src/app/ee/**` (Enterprise) — không đọc để chép, không dùng; ⛔ `secrets.activepieces.com` |
| Langflow `types_compatible`/`TYPE_MIGRATIONS` | MIT | port ~15 dòng | notice |
| Flowise | Apache-2.0 (ngoài `enterprise/`) | chỉ ý tưởng | không chép mã |
| n8n | Sustainable Use License | chỉ ý tưởng | ⛔ không chép mã |
| Temporal | MIT | chỉ nguyên tắc | không phụ thuộc |
| `croniter` | MIT | phụ thuộc Python | |
| Node.js | MIT | runtime runner | bản portable ghim SHA256 |

---

## 22. Rủi ro

| Mức | Rủi ro | Giảm thiểu |
|---|---|---|
| 🔴 | Phase 1 gỡ runtime v1 trong khi Canvas đang phục vụ | cắt chuyển §17 hai bước (ngừng dùng → drop); nghiệm thu Playwright trên production |
| 🔴 | Đồng thời động cơ chưa từng chạy trên PostgreSQL | bộ test PG viết trước động cơ; diễn tập §18.7 |
| 🔴 | Runner Node trên máy production: RAM/CPU, chuỗi npm | Job Object + lane `connector` 2 slot + lock + ignore-scripts + allowlist; đo ở phase 9 |
| 🟠 | Tiền: tham số ảnh hưởng giá không có enum/maximum | từ chối publish thay vì đoán (§7.2) |
| 🟠 | Rò bí mật qua lỗi/log provider | che theo giá trị + phép kiểm bí mật mồi |
| 🟠 | Google chưa xác minh app ⇒ token 7 ngày | điều kiện ra phase 7/8; test bằng tài khoản test |
| 🟠 | `node_run_snapshot` + `workflow_event` phình | TTL 90 ngày, chỉ số `(run_id, created_at)` |
| 🟠 | Trôi version piece/framework | nâng theo đợt + smoke test; ghim chính xác |
| 🟡 | Độ trễ node HTTP/connector = một lượt claim job | chấp nhận theo Q1(c); đo ở phase 9 trước khi làm tự động hoá tổng quát |
| 🟡 | Phiên khác sửa `platform_core/agent`, `frontend/agent-canvas` | kiểm worktree khác trước mỗi phase; `??` lạ = phiên khác |

---

## 23. Khác với ADR-WF-001 / tài liệu 23–29 (và vì sao)

| Chỗ | Trước | Nay | Vì sao |
|---|---|---|---|
| F4 | không connector/HTTP | connector cửa vào/ra + HTTP | Q1(c), Q2(b) |
| Điều kiện | "trên cạnh" | biểu thức trong if/switch, cạnh mang tên nhánh | một nơi viết biểu thức, một nơi hiển thị |
| Biểu thức | tập toán tử cố định, chỉ `params` | + tham chiếu có kiểu, `{{ }}`, bảng hàm đóng | ánh xạ dữ liệu giữa node (đề bài §15) |
| Máy trạng thái node | `RUNNING_WITH_WAITPOINTS`, không retry | `WAITING`, `RETRY_SCHEDULED`; `RESUMING` không lưu | §5.3 |
| Run | có `VALIDATING`, `"queued"` thường | bỏ `VALIDATING`, `CREATED` | validate ở publish |
| Trigger lịch | `SCHEDULE` theo giây | `cron` | đề bài §17 |
| Node điều khiển | 8 loại (Input·Const·Router·Join·Delay·Approval·Subworkflow·Collect) | catalog §20 | Router → if/switch; Approval → human; Collect → foreach_end/aggregate; Input/Const → `graph.inputs` + literal |
| Nhật ký | chỉ snapshot | snapshot + `workflow_event` cấp run | trigger event cần outbox; timeline run |
| Credential | không có | §9 | connector/HTTP |

---

## 24. Tự rà đặc tả (22/09)

| Phép rà | Kết quả |
|---|---|
| Chỗ trống | Không `TBD`/`TODO`. Tên action piece §11.6 là **đích**, có luật chốt tất định (xuất catalog; không tồn tại thì bỏ, không thay nếu không review). |
| Mâu thuẫn | Đã sửa: §5.4 định nghĩa lại "điều kiện trên cạnh" (ghi ở §23); §7.2 tổng mọi nhánh khớp ADR §12. |
| Phạm vi | Quá lớn cho một kế hoạch ⇒ 13 kế hoạch theo phase (§19). |
| Mơ hồ | Đã chốt: trang = tab bố cục (§4.1); `RESUMING` không lưu (§5.3); `vars` tất định (§6.5); giá cố định có số (§7.1). |
| Nguồn chân lý | NodeDefinition dẫn xuất, không lưu; ToolSpec vẫn là nguồn app; allowlist một tệp; một `tao_run` cho ba cửa. |
| Runtime trùng | Gỡ executor v1 (§17); runner không có state/retry riêng; động cơ không làm I/O. |
| Giấy phép | §21; phép kiểm đường dẫn `ee`. |
| Di trú | 0 khách ⇒ cắt thẳng; hai bước drop; đường lui = deploy bản trước. |
| Kiểm được | Mỗi phase có điều kiện ra đo được (§19); FLOW A–H (§18.5). |
