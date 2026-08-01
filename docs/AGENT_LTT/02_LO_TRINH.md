# Kế hoạch triển khai App LTT Agent AI

> Đây là lộ trình thi công chính thức của H12. Đặc tả kỹ thuật nằm ở
> [`01_DAC_TA_AGENT.md`](01_DAC_TA_AGENT.md); thiết kế file/CSDL nằm ở
> [`06_XAY_DUNG_APP_AGENT.md`](06_XAY_DUNG_APP_AGENT.md). Trạng thái thật phải đo
> bằng [`04_KIEM_CHUNG_CODE.md`](04_KIEM_CHUNG_CODE.md), không suy từ bảng này.
>
> Mỗi phase là một cổng độc lập. Không mở phase sau nếu chưa có bằng chứng PASS
> của phase trước. Không đánh `[x]` dựa trên code đã viết hoặc test collect được.

---

## 0. Đích đến và phạm vi v1

LTT Agent AI nhận yêu cầu tiếng Việt, lập Plan có cấu trúc, kiểm tra Plan bằng
code tất định, báo trần credit, chờ duyệt, điều phối các job app hiện hữu, kiểm
tra output và retry trong giới hạn, rồi quyết toán đúng chi phí thật.

Sản phẩm hoàn chỉnh có bốn trạng thái nghiệp vụ:

1. Nhập yêu cầu + file đầu vào + ngân sách.
2. Xem/sửa Plan trên Canvas, giá từng bước và trần tối đa.
3. Duyệt rồi theo dõi trạng thái trực tiếp trên node.
4. Xem kết quả, tiền thật, phần hoàn và decision log.

Theo Q38–Q39, Canvas và cả 7 tool ảnh/text/video/GPU nằm trong cùng lộ trình,
không hoãn. V1 vẫn không có auto-run không duyệt, multi-agent hoặc RAG workflow.
Plan chỉ được sửa trước approval; sửa sau approval tạo version mới và báo giá lại.

---

## 1. Baseline và tài sản dùng lại

### 1.1 Baseline đo gần nhất

- Registry có 10 app/đặc cách.
- 7 app job-based phù hợp ToolSpec v1: `thumbnail`, `taoanh`, `kichban`,
  `taovideo`, `autosubvideo`, `upscalevideo`, `taoclipngan`.
- `chataistudio` dùng SSE/sidecar, chưa ép vào ToolSpec job-based.
- `demo` chỉ kiểm hạ tầng; `socialbot` đóng băng.
- R2, `Storage.url_for()`, `Storage.put_url()`, media helper, API pool, credit
  ledger, PostgreSQL job queue và app-contract linter đã có.
- Baseline kiểm gần nhất: `1705 passed, 4 skipped, 23 subtests`; secret scan 0;
  app linter 0 ERROR/0 WARN. Phải đo lại khi bắt đầu P0.

### 1.2 Không được xây lại

| Nhu cầu Agent | Primitive bắt buộc tái sử dụng |
|---|---|
| Khám phá app/job/giá | `registry.discover()`, `credit_for()` |
| Chạy việc nền | `job_submit`, `jobs`, `job_runner` |
| Tiền | `credit.giu_cho/quyet_toan/hoan` |
| Model/API key | `providers`, `api_pool`, `api_keys` |
| Artifact | `storage` Local/R2 + presigned GET/PUT |
| Video technical check | `platform_core.media` |
| UI/progress | Jinja, HTMX, `ltt.css`, job progress pattern |
| Auth/CSRF/access | `server/auth`, `app_access` |

---

## 2. Sơ đồ phase và quy tắc cổng

```text
P0 Duyệt kiến trúc + đóng baseline
 │
P1 ToolSpec core ──► P2 Khai ToolSpec cho app
 │                         │
 └───────────────┬─────────┘
                 ▼
P3 Data model + checkpoint/fan-out
                 ▼
P4 Planner + normalizer + validator
                 ▼
P5 Budget + approval + credit atomic
                 ▼
P6 Executor + resume + fan-out
                 ▼
P7 Verifier + bounded retry
                 ▼
P8 App/UX nghiệp vụ + E2E backend
                 ▼
P9 Nền build Canvas React/Vite
                 ▼
P10 Canvas data model + API
                 ▼
P11 Node editor đầy đủ
                 ▼
P12 Agent ↔ Canvas ↔ Run integration
                 ▼
P13 Hardening + rollout production
```

Quy tắc chung cho mọi phase:

- Có test hành vi mới trước khi báo PASS.
- Chạy test hẹp trước, full suite sau.
- Phase có UI phải kiểm browser thật, console error và failed request.
- Phase có migration phải test upgrade, downgrade/rollback hợp lý và DB trống.
- Phase có tiền phải test concurrent/idempotent trên PostgreSQL thật.
- Mỗi phase ghi lệnh/kết quả thật vào `NHAT_KY.md`; chỉ P9 mới deploy production.

---

## P0 — Duyệt quyết định và đóng baseline

### Mục tiêu

Biến các phương án nghiên cứu thành quyết định chính thức trước khi sửa
`platform_core/`.

### Việc làm

1. Chạy đủ A1–A7 trong `04_KIEM_CHUNG_CODE.md`.
2. Lập bảng `nhu cầu / đã có / khoảng trống / quyết định`.
3. Chủ dự án duyệt hoặc sửa các điểm:
   - LT-1: công cụ → Agent → canvas;
   - ToolSpec additive trong `AppManifest`;
   - PA-1+: planner một lần, executor lặp hữu hạn;
   - chưa duyệt thì không giữ/tiêu credit;
   - trần credit tính được trước;
   - Q38: hybrid HTMX + React/Vite Canvas, Node chỉ dùng build;
   - `chataistudio` không thuộc tool job-based v1;
   - Q39: full 7 app job-based ảnh/text/video/GPU, không cắt còn ảnh/text.
4. Ghi quyết định Q40–Q43 theo giao thức quyết định (Q38–Q39 đã chốt Canvas/phạm vi).
5. Thêm H12 vào `KE_HOACH_TRIEN_KHAI.md` và ghi rollback cấp kiến trúc.

### PASS gate

- [x] Q38–Q43 có trạng thái duyệt thật và không mâu thuẫn quyết định cũ.
- [x] H12 tồn tại trong kế hoạch nền tảng.
- [x] Baseline full suite xanh, scan 0, linter 0 ERROR/WARN.
- [x] Không có secret trong tài liệu hoặc output lưu lại.
- [x] Phạm vi full theo Q39 được phản ánh trong H12, không còn lựa chọn treo.

### Rollback

Chưa có code. Nếu không duyệt, giữ bộ nghiên cứu và dừng H12.

---

## P1 — ToolSpec core: metadata, không tạo runtime mới

### Entry gate

P0 PASS và đã duyệt sửa `platform_core/registry.py`.

### Thay đổi

- Thêm immutable `ToolSpec` với `name`, `job_type`, `description`,
  `params_schema`, `returns`, `verifiable`.
- `AppManifest.tools: tuple = ()` để app cũ tương thích.
- Validation lúc discover:
  - tool name duy nhất;
  - tên dạng `<domain>.<action>`;
  - job type thuộc chính app;
  - schema/returns dùng kiểu cổng hợp lệ;
  - enum động `source=prompts/<group>` không thoát khỏi app;
  - `depends_on` trỏ tới trường/model có thật.
- `platform_core/agent/tools.py` chỉ gom/resolve metadata qua registry.
- Không sửa job runner, credit, storage hoặc handler app.

### Test bắt buộc

- Tool hợp lệ discover được.
- Trùng name bị từ chối sớm.
- Job type lạ bị từ chối.
- Schema rỗng/kiểu lạ/path traversal ở `source` bị từ chối.
- Enum prompt đọc đúng `_labels.json`.
- `depends_on=model` resolve đúng capability.
- Manifest không có `tools` vẫn chạy nguyên.
- Test chống hardcode slug vẫn xanh.

### PASS gate

- [x] Test hẹp ToolSpec xanh.
- [x] `tests/test_60_app_registry.py` xanh.
- [x] Full suite xanh; scan 0; linter xanh.
- [x] A2 tìm thấy ToolSpec nhưng không xuất hiện runtime/queue thứ hai.

### Rollback

Revert field/dataclass/module mới; không migration và không dữ liệu cần phục hồi.

---

## P2 — Khai ToolSpec cho các app đã chạy

### Entry gate

P1 PASS.

### Thứ tự

1. `kichban` → `text.script`.
2. `taoanh` → `image.generate`.
3. `thumbnail` → `image.thumbnail`.
4. `taovideo` → `video.generate`.
5. `autosubvideo` → `video.subtitle`.
6. `upscalevideo` → `video.upscale`.
7. `taoclipngan` → `video.short_clips`.

### Việc làm cho mỗi app

- Đối chiếu `Form(...)`, handler params, cost và result thật.
- Schema phủ mọi tham số user/Agent được phép điều khiển.
- Không đưa `owner_id`, storage key nội bộ, CSRF hoặc secret vào tham số LLM tự đặt.
- Returns phải khớp result handler thật.
- Cost của ToolSpec gọi đúng `credit_cost` hiện hữu.
- Viết contract test “schema → params handler → result → returns”.
- Không sửa logic handler để ép vừa metadata; nếu lệch, ghi finding trước.

### PASS gate từng app

- [ ] Tool discover được, tên không trùng.
- [ ] Một bộ params tối thiểu và tối đa đều validate.
- [ ] Params sai enum/range/model bị chặn trước submit.
- [ ] Giá ToolSpec bằng giá submit hiện hành.
- [ ] Result fixture khớp returns.
- [ ] Test hiện hữu của app xanh.

### PASS gate phase

- [ ] Cả 7 app có ToolSpec hoặc có quyết định ghi rõ vì sao loại khỏi v1.
- [ ] `demo`, `socialbot`, `chataistudio` không bị ép sai mô hình.
- [ ] Full suite, scan và linter xanh.

### Rollback

Gỡ `tools=` khỏi manifest từng app; handler và dữ liệu production không đổi.

---

## P3 — Data model Agent, checkpoint và fan-out

### Entry gate

P1–P2 PASS; backup PostgreSQL có restore test gần nhất.

### Thay đổi dữ liệu

- `jobs`: thêm nullable/default-safe `parent_id`, `plan_id`, `step_id` và index.
- Bảng `agent_runs`: owner, goal, normalized plan, status, budget/estimated/actual,
  approval, decision log, timestamps, version.
- Nếu cần chi tiết step, ưu tiên JSON checkpoint trong `agent_runs` v1; chỉ tạo
  bảng riêng khi chứng minh truy vấn/concurrency cần nó.
- Migration additive, chain đúng head, không sửa dữ liệu job cũ.

### State machine cần chốt

```text
planning → awaiting_approval → running → done
    └──────── error              ├────→ error
                                └────→ cancelled
```

Chuyển trạng thái sai phải bị từ chối. `approved_at` bất biến sau khi chạy.

### Test bắt buộc

- Migration DB trống; upgrade từ head hiện tại.
- Job cũ đọc/claim/complete nguyên.
- AgentRun cô lập theo user.
- Transition hợp lệ/sai.
- Hai worker không claim trùng child job.
- Orphan child được reclaim.
- 4 child job cùng parent hoàn tất; một child lỗi được ghi đúng.
- PostgreSQL concurrency test, không chỉ SQLite.

### PASS gate

- [ ] Migration upgrade sạch và rollback đã được diễn tập trên DB test.
- [ ] Full suite xanh; test concurrency PostgreSQL xanh.
- [ ] Backup/restore vẫn đọc được schema và dữ liệu.
- [ ] Chưa có route production nào tạo AgentRun ngoài test.

### Rollback

Dừng web/worker, downgrade migration trên DB test trước. Production chỉ rollback
trước khi có AgentRun thật; sau khi có dữ liệu thật dùng forward-fix, không drop.

---

## P4 — Planner, normalizer và validator tất định

### Entry gate

P3 PASS; ToolSpec đủ cho phạm vi v1.

### Planner

- Gọi model qua `api_pool`, không env key.
- Prompt làm phẳng: công cụ, schema, input, ngân sách, yêu cầu.
- LLM sinh schema phẳng; server normalizer chuyển thành Plan v1.
- Fallback bóc JSON bằng code an toàn, có giới hạn kích thước/độ sâu.
- Planner retry tối đa 2 lần chỉ để sửa Plan không hợp lệ.

### Validator

1. Version Plan hỗ trợ.
2. Tool tồn tại và user có quyền dùng app.
3. Params đúng kiểu/range/enum/dependency.
4. Reference `$input`/`$step.field` tồn tại.
5. Input/output type tương thích.
6. DAG không chu trình; step id duy nhất.
7. Fan-out/retry không vượt cap hệ thống.
8. Mọi bước tra được giá.
9. Tổng tối đa không vượt ngân sách user/cap nền tảng.
10. Không cho LLM đặt owner, secret, storage path hoặc callback URL tùy ý.

### Test bắt buộc

- Mỗi điều kiện validator có positive + negative test.
- Cycle, dangling ref, sai output type, unknown tool, model-resolution sai.
- JSON fenced/plain/tool-call đều normalize được.
- Text rác/truncated/JSON bomb báo lỗi an toàn.
- Planner không làm lộ credential trong prompt/log/error.
- Cùng fixture Plan cho kết quả validate và báo giá tất định.

### PASS gate

- [ ] 100% fixture invalid bị chặn trước job/credit.
- [ ] Planner lỗi không tạo child job và không giữ credit thực thi.
- [ ] Test với provider mock xanh; một smoke planner thật chỉ chạy khi được phép.
- [ ] Full suite, scan, linter xanh.

### Rollback

Tắt planner bằng feature flag; AgentRun ở `planning/error` không có hold thực thi.

---

## P5 — Báo giá, cổng duyệt và credit atomic

### Entry gate

P4 PASS; công thức giá được review riêng.

### Hợp đồng tiền

```text
max = planning_cost + Σ(step_cost × fanout × (1 + max_retry))
```

- Planner cost được ghi riêng, không giấu trong tool cost.
- Chưa duyệt: không có hold thực thi.
- Duyệt: lock AgentRun + kiểm ownership/status/số dư + tạo hold một lần.
- Approval lặp/F5/web retry không giữ hai lần.
- Actual không được vượt max; nếu có dấu hiệu vượt thì dừng trước lần gọi trả phí.
- Cancel/error quyết toán phần đã tiêu và hoàn phần chưa dùng theo policy đã duyệt.

### Test bắt buộc

- Chưa duyệt = 0 hold thực thi.
- Hai request approve đồng thời = một hold.
- Không đủ credit = không chuyển running, không child job.
- Fanout/retry tính đúng trần.
- Actual thấp hơn max hoàn đúng.
- Retry tới cap không vượt max.
- Settle/refund idempotent.
- User A không approve/cancel run của B.
- CSRF tất cả POST approval/cancel.

### PASS gate

- [ ] PostgreSQL concurrency test tiền xanh.
- [ ] Sổ credit append-only, balance bằng tổng sổ.
- [ ] Không đường chạy nào bỏ qua approval.
- [ ] Full suite, scan, linter xanh.

### Rollback

Feature flag chặn approval mới; run đã hold phải settle/refund bằng service hiện
có trước khi rollback code.

---

## P6 — Executor: DAG, resume và fan-out

### Entry gate

P5 PASS.

### Thay đổi

- Executor chỉ chọn step ready theo DAG và checkpoint.
- Resolve reference server-side.
- Nộp handler qua job runtime hiện có; không giữ credit lại ở child.
- Cap concurrency mỗi run và theo capability worker.
- Persist trước/sau mỗi side effect để resume không lặp bước done.
- Tái sử dụng idempotency/dedupe của app; với provider async phải resume remote id.
- Cancel ngăn submit step mới; step đang chạy xử lý theo khả năng app.

### Test bắt buộc

- Chuỗi text → image → video đúng thứ tự.
- Hai nhánh độc lập chạy song song.
- Join chỉ chạy khi dependency đủ.
- Worker chết sau submit/trước checkpoint không double-bill provider.
- Restart web/worker resume từ bước chưa xong.
- Step done không chạy lại.
- Child lỗi theo policy, decision log đủ.
- Capability API/GPU không bị định tuyến sai.

### PASS gate

- [ ] E2E headless với fake tools chạy tuần tự, fan-out, join, cancel, resume.
- [ ] PostgreSQL thật: nhiều worker không chạy trùng.
- [ ] Actual credit đúng với số attempt thật.
- [ ] Full suite, scan, linter xanh.

### Rollback

Feature flag không nhận run mới; để run đang chạy drain hoặc cancel có kiểm soát.
Không downgrade migration khi còn run active.

---

## P7 — Verifier và bounded retry

### Entry gate

P6 PASS.

### Thứ tự triển khai

1. `technical`: file tồn tại, MIME, kích thước, duration, frame/probe.
2. `vlm_judge`: schema JSON, rubric, score/fault/reason.
3. `face_identity`: chỉ sau khi kiểm kê OpenCV/Haar nội tại; thêm recognition nếu cần.

### Quy tắc

- Chạy verifier rẻ trước, đắt sau.
- `policy` dừng, không retry.
- `partial` cho refine nếu tool hỗ trợ; nếu không, policy fallback đã khai.
- `structural` regenerate.
- Verifier lỗi kỹ thuật không tự động coi output tốt; trạng thái `inconclusive`
  phải có policy rõ và không retry vô hạn.
- Mỗi attempt ghi model/key-id tham chiếu, score, fault, reason và credit; không
  ghi credential.

### Test bắt buộc

- Pass đi tiếp; fail retry đúng `max_retry`; policy không retry.
- Verifier timeout/rác/mất key xử lý `inconclusive` đúng policy.
- Technical reject file hỏng trước VLM.
- Retry actual không vượt reserved max.
- Decision log không lộ secret/PII thừa.
- Mock VLM deterministic; smoke thật opt-in.

### PASS gate

- [ ] Không có vòng lặp không giới hạn.
- [ ] Mọi nhánh fault có test.
- [ ] Chi phí verifier nằm trong báo giá.
- [ ] Full suite, scan, linter xanh.

### Rollback

Tắt verifier theo feature flag để executor chạy một attempt; không xóa decision log.

---

## P8 — App `apps/agent/` và UX nghiệp vụ

### Entry gate

P4–P7 PASS ở backend; route vẫn chưa public.

### File app

```text
apps/agent/
├── manifest.py
├── routes.py
├── jobs.py
└── templates/
    ├── agent.html
    ├── agent_plan.html
    ├── agent_run.html
    └── _agent_progress.html
```

### UX bắt buộc trước Canvas

- Input rõ giới hạn file/ngân sách.
- Plan API trả đủ tool, params, dependency, retry, verifier và giá để Canvas render.
- Nút duyệt ghi rõ “tối đa N credit”; không nút mơ hồ.
- Progress API hiển thị step/attempt/fan-out/waiting/failed/cancelled.
- Result hiển thị artifact qua URL storage có kiểm quyền.
- Decision log giải thích tiền và retry bằng ngôn ngữ người dùng.
- Mobile/keyboard/focus/error state; không chỉ happy path.

### Browser flows nền bắt buộc bằng Playwright

1. Ẩn danh click Agent → login return-to đúng.
2. User lập Plan → xem giá → chưa duyệt không bị hold.
3. Duyệt → progress API/HTML → kết quả → số dư/hoàn đúng.
4. Plan invalid → lỗi hữu ích, không child job.
5. Không đủ credit → chặn trước chạy.
6. Cancel run.
7. Verifier fail rồi retry.
8. User A không xem run/artifact của B.
9. Refresh/reopen vẫn thấy trạng thái đúng.

Sau mỗi flow kiểm console error và failed network request.

### PASS gate

- [ ] 9 flow browser PASS và có regression test phù hợp.
- [ ] CSP không chặn HTMX/R2/media.
- [ ] Không secret/stack trace/raw provider body trong UI.
- [ ] Full suite, scan, linter xanh.

### Rollback

Đặt manifest `enabled=False`/feature flag; backend giữ dữ liệu run để kiểm toán.

---

## P9 — Nền build Canvas React/TypeScript/Vite

### Entry gate

P8 PASS; Q38 đã ghi trong nguồn chân lý.

### Kiến trúc build

```text
frontend/agent-canvas/
├── package.json + package-lock.json
├── tsconfig.json
├── vite.config.ts
├── src/
└── tests/
        │ npm ci + npm run build
        ▼
server/static/agent-canvas/   ← bundle hashed do FastAPI phục vụ
```

- React + TypeScript + `@xyflow/react`.
- Node.js build version theo Vite hiện hành: `20.19+` hoặc `22.12+`; pin một bản
  LTS cụ thể trong tài liệu cài/build, không dùng `latest` trôi nổi.
- Vite `base` trỏ đúng `/static/agent-canvas/`.
- Node LTS chỉ ở máy dev/build; production không chạy Node service.
- Pin dependency bằng lockfile; scanner/release phải bao gồm frontend source,
  lockfile và bundle manifest.
- Build output deterministic; release fail nếu source mới hơn bundle hoặc build lỗi.
- CSP chỉ mở đúng asset/API cần thiết; không `unsafe-eval`, không CDN runtime.

### Test bắt buộc

- `npm ci`, TypeScript check, unit test, production build.
- Bundle load dưới route prefix qua FastAPI.
- Asset hashing/cache; HTML no-store, bundle immutable.
- Không source map public chứa nội dung nhạy cảm.
- Build từ clean checkout cho cùng lockfile.
- `setup/2`, build_release và rollback mang đủ bundle.

### PASS gate

- [ ] Canvas shell render production bundle, không dùng Vite dev server.
- [ ] Node không xuất hiện như service production.
- [ ] CSP/console/network sạch trong Playwright.
- [ ] Python full suite, frontend test/build, scan và linter xanh.

### Rollback

Feature flag quay về UX P8; bundle version cũ nằm trong release rollback.

---

## P10 — Canvas data model, versioning và API

### Entry gate

P9 PASS.

### Nguồn chân lý

- Bảng `agent_workflows`: owner, name, plan version, nodes, edges, viewport,
  status draft/validated/approved/archived, revision, timestamps.
- Canvas JSON chỉ chứa layout + config ToolSpec; không credential, owner override,
  storage path tùy ý hoặc giá do client khai.
- Server chuyển Canvas → Plan chuẩn và chạy cùng validator P4.
- Server chuyển Plan của planner → Canvas draft; round-trip không mất semantics.
- Optimistic locking bằng `revision`/ETag; save stale trả conflict, không ghi đè.
- Autosave debounce client; save API idempotent.

### API

- CRUD workflow theo user.
- Validate/requote workflow.
- Clone/version/archive; không hard-delete workflow đã có run.
- Import/export JSON có version, size/depth cap và schema validation.
- API palette lấy trực tiếp ToolSpec + model capability.

### Test bắt buộc

- User A không đọc/sửa/clone workflow B.
- Stale revision conflict; hai save đồng thời không mất dữ liệu.
- Canvas↔Plan round-trip cho linear, fan-out, join và video/GPU.
- Cycle/type mismatch/unknown tool bị server từ chối.
- Import JSON độc/pathological bị chặn.
- Workflow đã approved sửa config → draft mới, approval/quote cũ vô hiệu.
- Migration upgrade/rollback test; backup/restore có workflow.

### PASS gate

- [ ] PostgreSQL concurrency/ownership/round-trip test xanh.
- [ ] Client không thể bypass validator hoặc tự đặt giá.
- [ ] Full suite, frontend tests, scan và linter xanh.

### Rollback

Tắt API write/Canvas flag; giữ workflow JSON. Sau dữ liệu thật chỉ forward-fix schema.

---

## P11 — Node editor đầy đủ

### Entry gate

P10 PASS.

### Tính năng bắt buộc

- Palette nhóm Text/Ảnh/Video/GPU sinh động từ ToolSpec.
- Drag/drop node; typed input/output handles; connect/disconnect có validation sớm.
- Custom node hiển thị icon, app/tool, model, cost estimate, validation/run status.
- Inspector form sinh từ `params_schema`, gồm enum động và depends_on model.
- Pan/zoom/fit/minimap/controls, multi-select, copy/paste, duplicate, delete.
- Undo/redo local có giới hạn; autosave server có revision.
- Auto-layout chỉ thay vị trí, không thay semantics.
- Keyboard/focus/ARIA và mobile read-only hoặc editor giới hạn có chủ đích.
- Empty/loading/error/conflict/offline-retry state.

### Quy tắc an toàn

- Edge client chỉ là đề xuất; server validate lại.
- Không thực thi node trong browser.
- Không gọi provider/R2 bằng secret từ browser; upload chỉ qua presigned target.
- Node video/GPU hiển thị capability/wait estimate nhưng server quyết routing.

### Test bắt buộc

- Component/unit: reducer, undo/redo, schema form, connection guard.
- Playwright: add/config/connect/move/delete/undo/redo/save/reload.
- Keyboard-only tạo và nối workflow tối thiểu.
- Conflict hai tab; refresh không mất layout.
- 100 node/150 edge vẫn pan/zoom/edit trong ngưỡng hiệu năng đã chốt.
- Screenshot desktop/mobile/dark theme; console/network sạch.

### PASS gate

- [ ] Tất cả thao tác editor và a11y flow PASS.
- [ ] Save/reload round-trip không mất node/edge/viewport/config.
- [ ] Bundle size/performance budget PASS.
- [ ] Full Python/frontend suite, scan và linter xanh.

### Rollback

Feature flag về viewer/list P8; workflow data không mất.

---

## P12 — Tích hợp Agent ↔ Canvas ↔ Executor

### Entry gate

P11 PASS và backend P4–P7 PASS.

### Luồng hoàn chỉnh

1. User nhập tiếng Việt hoặc tự kéo node.
2. Planner sinh Plan → server validate → tạo Canvas draft.
3. User sửa graph/config → validate + báo giá lại.
4. User duyệt đúng revision + quote hash.
5. Server hold credit atomic rồi executor chạy.
6. Node/edge nhận trạng thái live: queued/running/verifying/retrying/done/error.
7. Artifact hiện trên output node; decision log/actual/refund gắn với run.
8. “Run again” tạo run mới từ immutable workflow version, không dùng draft đã đổi.

### Video/GPU bắt buộc

- Workflow E2E có `taovideo`, `autosubvideo`, `upscalevideo`, `taoclipngan`.
- Upload input lớn qua R2 presigned PUT; output qua presigned GET.
- Remote async task resume không submit trùng.
- GPU capability routing/concurrency không làm starvation job API; nếu P3 worker
  đa tiến trình chưa xong, phải hoàn thành trong phase này trước PASS.
- Duration/token thật có thể tăng hold theo hợp đồng hiện hữu nhưng tổng Agent
  không vượt quote max; quote phải bảo thủ cho video.

### Playwright E2E bắt buộc

- Prompt → Canvas → sửa → requote → approve → run → result.
- Canvas tự dựng linear, fan-out và join.
- Tool ảnh/text/video/GPU đều có ít nhất một flow thật hoặc fixture production-like.
- Verifier fail → node retry và actual/refund cập nhật.
- Worker restart giữa video; reload browser giữa run.
- Cancel; insufficient credit; stale quote/revision; cross-user 404.
- Console 0 error không giải thích; network 0 failed request ngoài lỗi cố tình.

### PASS gate

- [ ] Canvas và danh sách Plan cùng biểu diễn một semantics.
- [ ] Không đường Canvas nào bypass approval/credit/validator.
- [ ] Full 7 tool nằm trong palette và contract test.
- [ ] Video/GPU E2E thật PASS trên worker production-like.
- [ ] Full Python/frontend suite, scan, linter, browser PASS.

### Rollback

Tắt tạo/run từ Canvas; run active drain/cancel/settle; workflow vẫn xem/export được.

---

## P13 — Hardening, vận hành và rollout

### Entry gate

P12 PASS trên development/staging với dữ liệu test.

### Security và abuse

- Rate limit planner, approve và run theo user/IP.
- Cap step, fanout, retry, input bytes, Plan bytes và số run đồng thời.
- Sanitize prompt/error/log; không cho arbitrary URL/path/command.
- Ownership check ở run, job, input, output, decision log.
- Sentry lọc PII theo Q21 nếu bật.

### Observability

- Correlation: request → agent_run → step → child job.
- Metrics: planning latency/error, approval rate, run success, retry count,
  verifier pass, estimated/actual ratio, credit refund, worker wait theo capability.
- Admin chỉ đọc run/decision log và có đường cancel/refund an toàn.

### Load/failure drills

- 10 run đồng thời với fake tools.
- Worker restart giữa fan-out.
- PostgreSQL/R2/provider tạm lỗi.
- API key cooldown/cạn toàn bộ.
- GPU worker bận nhưng job API vẫn tiến triển; worker routing/concurrency là điều
  kiện PASS, không được ẩn tool GPU để lách Q39.
- Backup + restore có AgentRun, workflow Canvas, revision và decision log.

### Rollout

1. Feature flag off sau deploy/migration.
2. Admin-only canary.
3. Một tài khoản test thật, ngân sách nhỏ.
4. Nhóm user nội bộ.
5. Public khi metrics/alert/rollback đã xác nhận.

### PASS gate cuối

- [ ] Full suite xanh.
- [ ] Secret scan 0; linter 0 ERROR/WARN.
- [ ] Migration production thành công; health ready.
- [ ] Browser production đủ chuỗi qua Cloudflare edge.
- [ ] Console 0 error không giải thích được; network 0 failed request không mong đợi.
- [ ] Credit estimated/actual/refund khớp sổ.
- [ ] Backup và restore thử thành công.
- [ ] Rollback/feature-off diễn tập thành công.
- [ ] Cập nhật Q/H12/NHAT_KY và commit có lý do.

### Rollback

Tắt feature flag, ngăn run mới, drain/cancel run active, settle/refund, giữ schema
và audit data. Rollback binary chỉ sau khi xác nhận không còn run active.

---

## 3. Ma trận test tối thiểu xuyên phase

| Bất biến | Phase phải chốt |
|---|---|
| Không hardcode app/runtime thứ hai | P1, P2, P4, P6, P10, P12, P13 |
| Plan/Canvas schema tất định + round-trip | P2, P4, P5, P6, P7, P10–P13 |
| Chưa duyệt không hold | P5, P6, P8, P10, P12, P13 |
| Không vượt trần credit | P2, P4–P8, P10, P12, P13 |
| Idempotent/concurrent | P3, P5–P8, P10, P12, P13 |
| Resume/orphan/provider không submit trùng | P3, P6–P8, P12, P13 |
| Cô lập user/workflow/run/artifact | P3–P8, P10–P13 |
| Không lộ secret | mọi phase có code/build |
| Frontend build/CSP/cache | P9, P11–P13 |
| Browser thật | P8, P9, P11–P13 |
| Video/GPU/R2/capability | P2, P6–P8, P10–P13 |
| Backup/restore/rollback | P3, P5, P6, P10, P12, P13 |

---

## 4. Lệnh cổng chuẩn cho mỗi phase

```powershell
python -m pytest <test-hep-cua-phase> -q
python -m pytest -q
python tools\scan_source_secrets.py
python tools\lint_app_contract.py --strict
git status --short
```

Phase P9–P13 chạy thêm trong `frontend/agent-canvas/`:

```powershell
npm ci
npm run typecheck
npm test
npm run build
```

Phase có UI chạy Playwright theo `AGENTS.md`. Phase có concurrency/migration chạy
test PostgreSQL thật. Không ghi kết quả giả vào bảng dưới.

---

## 5. Bảng theo dõi thực thi

| Phase | Trạng thái | Ngày | Commit | Test hẹp | Full suite | Scan/lint | Browser/PG | Rollback |
|---|---|---|---|---|---|---|---|---|
| P0 Quyết định + baseline | ✅ | 2026-08-02 | commit P0–P1 | 23 pass | 1710 pass, 4 skip, 23 subtest | scan 0; lint 0/0 | N/A | docs-only trước P1 |
| P1 ToolSpec core | ✅ | 2026-08-02 | commit P0–P1 | 34 pass | 1721 pass, 4 skip, 23 subtest | scan 0; lint 0/0 | N/A (không UI/DB) | revert field/dataclass/module mới |
| P2 ToolSpec app | ⬜ | | | | | | | |
| P3 Data/checkpoint/fan-out | ⬜ | | | | | | | |
| P4 Planner/validator | ⬜ | | | | | | | |
| P5 Budget/approval/credit | ⬜ | | | | | | | |
| P6 Executor/resume | ⬜ | | | | | | | |
| P7 Verifier/retry | ⬜ | | | | | | | |
| P8 App/UX nghiệp vụ | ⬜ | | | | | | | |
| P9 React/Vite build foundation | ⬜ | | | | | | | |
| P10 Canvas model/API | ⬜ | | | | | | | |
| P11 Node editor | ⬜ | | | | | | | |
| P12 Agent–Canvas–Run + video/GPU | ⬜ | | | | | | | |
| P13 Hardening/rollout | ⬜ | | | | | | | |

Chỉ chuyển ⬜ → ✅ khi toàn bộ PASS gate của phase có bằng chứng thật trong
`NHAT_KY.md`. Nếu fail, ghi `FAIL` và nguyên nhân; không làm phase kế tiếp.

---

## 6. Ước lượng và thứ tự thực hiện

| Phase | Ước lượng |
|---|---:|
| P0 | 0,5–1 ngày |
| P1 | 2–3 ngày |
| P2 | 2–4 ngày |
| P3 | 3–5 ngày |
| P4 | 4–6 ngày |
| P5 | 3–5 ngày |
| P6 | 5–8 ngày |
| P7 | 4–7 ngày |
| P8 | 4–7 ngày |
| P9 | 2–4 ngày |
| P10 | 4–6 ngày |
| P11 | 8–12 ngày |
| P12 | 6–10 ngày |
| P13 | 4–7 ngày |
| **Tổng hoàn chỉnh** | **51–83 ngày làm việc** |

Không rút ngắn bằng cách gộp P5–P7: tiền, resume và retry là ba rủi ro độc lập.
Theo Q39 không được thu hẹp sản phẩm cuối xuống ảnh/text hoặc hoãn Canvas/video.
Có thể dùng fixture ảnh/text để phát triển sớm, nhưng P12–P13 chỉ PASS khi cả 7
tool, video/GPU và Canvas đã nghiệm thu.
