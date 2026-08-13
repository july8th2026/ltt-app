# API FULL EXTENSION — PROGRESS

Pack: `LTT_API_FULL_EXTENSION_PACK_V2_OPTIMIZED` (v2.0), 21 prompt.
Chạy **sau** Public API V2 (Q92, 17/17 PASS).

**Chế độ chạy:** pack này khai `strict sequential; one prompt per Claude turn`
(`MANIFEST.json`) và `START_HERE.md` viết "Mỗi lượt chỉ 1 prompt". Chủ sản phẩm
cũng ra lệnh "dừng sau EXT-01". → **Không** áp dụng chế độ chạy liên tục của pack
V2. Mỗi lượt một prompt, dừng và báo cáo.

Checkpoint chạy **full gate**: EXT-04, 08, 12, 16, 20, 21.

| # | Prompt | Trạng thái | Ngày |
|---|---|---|---|
| 01 | V2 reconciliation, master gap matrix, dependency graph | **PASS** | 2026-08-13 |
| 02 | Protocol / execution modes / error-retry standards | chưa chạy | — |
| 03 | Models / capabilities / tool catalog / schema chain | chưa chạy | — |
| 04 | Projects / service accounts / delegated auth decision | chưa chạy | — |
| 05 | Developer API tab / information architecture | chưa chạy | — |
| 06 | Schema-driven apps/models/tools variable reference | chưa chạy | — |
| 07 | Quickstart / env vars / examples / recipes | chưa chạy | — |
| 08 | Playground / request builder / job inspector | chưa chạy | — |
| 09 | Request logs / trace / job timeline | chưa chạy | — |
| 10 | Webhook console / event catalog / resend | chưa chạy | — |
| 11 | Usage / budgets / credit alerts / notifications | chưa chạy | — |
| 12 | Sandbox / test mode / live isolation | chưa chạy | — |
| 13 | API admin console core | chưa chạy | — |
| 14 | Admin policy / tiers / quota / kill switch | chưa chạy | — |
| 15 | Pricing catalog / versioned credits / margin | chưa chạy | — |
| 16 | Admin operations / security / support trace | chưa chạy | — |
| 17 | Versioning / changelog / deprecation / status | chưa chạy | — |
| 18 | SDK / CLI / Postman / OpenAPI ecosystem | chưa chạy | — |
| 19 | Privacy / retention / export / delete | chưa chạy | — |
| 20 | Full app/tool/model/execution-mode certification | chưa chạy | — |
| 21 | Final audit / load / chaos / security / release gate | chưa chạy | — |

---

## EXT-01 — V2 RECONCILIATION, MASTER GAP MATRIX, DEPENDENCY GRAPH ✅

### Entry gate — V2 có ổn định không?

**Có.** Không có blocker; Extension được phép bắt đầu. Bằng chứng (không phải ý
định của prompt V2):

| Trục | Bằng chứng thật |
|---|---|
| Kernel | `server/api/inventory.py` đóng băng 22 route; `test_178` so khớp **hai chiều** route ↔ inventory ↔ OpenAPI |
| Auth | `keys.py` + 54 test (`test_179` 35, `test_180` 19) |
| Credit/idempotency | `test_193`: 839 request trùng khoá → **1 job, 1 hold**; crash giữa hold và queue → **0 hold, 0 job**; 7 kịch bản bơm lỗi đều `reconcile ok` |
| Tool contract | `registry.py:322` fail-closed, 7 khoá hợp đồng cố định; golden `tests/golden/public_api_catalog_v1.json` |
| Migration head | `c9d0e1f2a3b4`, không đổi trong lượt này |
| Gate | `tools\gate.py` → **PASS 10/10** (pytest 2.530,9 s) trước khi bắt đầu |
| Quy mô test Public API | **317 test** (`--collect-only` trên `test_178`…`test_193`) |

### Reused V2 components (không xây lại gì)

EXT-01 là audit — **không thêm route, không thêm bảng, không thêm phụ thuộc**.
Bảng REUSE (engine nào Extension bắt buộc dùng lại) ở §4 của gap matrix.

### Status before → after

| | Before | After |
|---|---|---|
| Bản đồ nợ của API Platform | không có | 14 domain V2 + 24 domain Extension, mỗi domain có trạng thái + bằng chứng + prompt sở hữu |
| Disposition | 14/14 app (V2) | thêm **21/21 ToolSpec**, mỗi tool có execution mode đề xuất — **không UNKNOWN** |
| Thứ tự thi công | theo ROADMAP của pack | có đồ thị phụ thuộc chứng minh từng cạnh |

### Evidence — những phát hiện đáng kể

1. **`APP_DISPOSITION_V1.md` đếm sai.** Tài liệu ghi "6/21 ToolSpec public" và
   "15 còn lại"; `registry.discover()` thật cho **21 tool, 5 public, 16 không**.
   Đã sửa tài liệu. `test_190` không bắt được vì nó kiểm *tập hợp*, không kiểm
   *con số trong câu văn* — ghi lại như một `OBSERVED_DIFFERENCE`.
2. **`X-Correlation-ID` chỉ xuất hiện trên phản hồi bị guard chặn**
   (`server/api/guard.py:44` nằm trong nhánh `except`); phản hồi thành công
   không có header nào. Khách không cầm được id để mở ticket → chặn support
   trace (EXT-16), sửa ở EXT-02.
3. **`Retry-After` không phải header HTTP** — chỉ là trường trong body
   (`limits.py:93`). SDK của LTT hiểu, mọi client generic thì không.
4. **`/developers` không có lối vào**: `server/templates/_header.html` không có
   link nào tới portal. Tính năng có nhưng không ai tìm thấy → EXT-05.
5. **Không có view admin nào cho Public API**: grep `DeveloperApiKey` trong
   `server/admin.py` = 0. `ApiKeyAdmin` ở đó là **khoá provider**, domain khác.
6. **4 bảng Public API không nằm trong bất kỳ chính sách retention nào.**
   `platform_core/job_events.py` có purge cho job event (365/30 ngày);
   `webhook_deliveries` thì phình vô hạn → EXT-19, và là rủi ro thật nếu bật API
   trước khi tới prompt đó.
7. **Không tồn tại khái niệm execution mode** (grep = 0). Mọi tool hiện là
   async-job ngầm định; `chataistudio` là ứng viên STREAM đầu tiên nhưng không
   có Job nên chưa có ngữ nghĩa credit/cancel.
8. **Giá không có phiên bản**: `invocation.price()` gọi thẳng
   `registry.credit_for(job_type, params)`. Đổi bảng giá là đổi hồi tố cách đọc
   lịch sử → EXT-15.

### Files / migrations / config

Mới: `docs/PUBLIC_API/FULL_PLATFORM_GAP_MATRIX.md`,
`docs/PUBLIC_API/FULL_PLATFORM_DEPENDENCY_GRAPH.md`,
`docs/PUBLIC_API/FULL_PLATFORM_TARGET.md`, `docs/PUBLIC_API/EXTENSION_PROGRESS.md`.

Sửa: `docs/PUBLIC_API/APP_DISPOSITION_V1.md` (hai con số đếm sai).

**Không** migration, **không** biến cấu hình mới, **không** route mới, **không**
phụ thuộc mới. Head vẫn `c9d0e1f2a3b4`.

### Tests

Không thêm test — prompt này không thêm hành vi. Bằng chứng dùng để audit lấy từ
test sẵn có (317 test Public API) và từ `registry.discover()` chạy thật.

Regression: `python tools\gate.py --quick` → **PASS** (secret scan, lint hợp đồng
app, undefined names, silent-except, i18n, system profile, 3 frontend).
Full gate không chạy lại: EXT-01 không đổi một dòng mã chạy được, và lần chạy
full ngay trước đó (cùng cây mã, cộng thêm 4 file `.md`) đã PASS 10/10.
Checkpoint full gate kế tiếp theo `MANIFEST.json` là EXT-04.

### Performance / browser

Không áp dụng — không đổi mã chạy, không đổi giao diện.

### Risks / deferred

| # | Rủi ro | Mức | Xử lý |
|---|---|---|---|
| X1 | **Toàn bộ V2 chưa commit** (26 `M` + 31 `??`) và Extension sẽ chồng thêm lên cùng cây bẩn | **Cao** | Nên commit V2 **trước EXT-02**. Là lệnh của chủ sản phẩm, tôi không tự commit |
| X2 | `webhook_deliveries` không retention | Trung bình | EXT-19 |
| X3 | Giới hạn nhịp per-process | Trung bình | EXT-14, phải có ADR nếu muốn scale ngang |
| X4 | Portal không có lối vào từ header | Thấp | EXT-05 |
| X5 | Không có correlation header trên phản hồi thành công | Trung bình | EXT-02 |

**Năm quyết định sản phẩm chặn phía trước** (chi tiết ở §4 của dependency graph):
delegated OAuth có hay không; sửa gốc giá-theo-thời-lượng bằng cách nào; con số
trần credit ngày; sandbox mock hay tốn tiền thật; có mở STREAM cho chat không.
Bốn trong năm chặn ngay tại EXT-02/EXT-04 — nêu sớm để không va giữa chừng.

### Rollback

Xoá 4 file `.md` mới và hoàn nguyên 2 con số trong `APP_DISPOSITION_V1.md`.
Không có tác động runtime.

### Acceptance Gate

| Yêu cầu của EXT-01 | Kết quả |
|---|---|
| Mọi domain có status + evidence + owner prompt | ✅ 14 domain V2 + 24 domain Extension |
| Không đánh DONE chỉ vì prompt V2 từng yêu cầu | ✅ mỗi `DONE` trỏ tới test/route thật; và audit đã bắt được 1 sai lệch tài liệu + 4 lỗ hổng chưa ai ghi |
| 100% app/tool có disposition, không UNKNOWN | ✅ 14/14 app, 21/21 ToolSpec (model và execution mode được nêu rõ là **chưa** có disposition → chủ sở hữu EXT-03/EXT-20) |
| Dependency graph chứng minh thứ tự EXT-02…21 | ✅ từng cạnh có lý do; có cả danh sách cạnh **không** tồn tại |
| Không xây feature lớn | ✅ 0 route, 0 bảng, 0 migration |

**NEXT_EXTENSION_PROMPT_ALLOWED=true**
Prompt kế tiếp: `prompts/02_PUBLIC_API_PROTOCOL_EXECUTION_MODES_ERROR_RETRY_STANDARDS.txt`
Khuyến nghị **trước** khi chạy: commit V2 (rủi ro X1).
