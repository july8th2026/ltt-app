# FULL PLATFORM GAP MATRIX — EXT-01

Ngày: 2026-08-13. Nền: Public API V2 (Q92) đã xong 17/17.
Nguồn chân lý: **code + migration + test thật**, không phải ý định của prompt.

Mỗi dòng dưới đây có: trạng thái → **bằng chứng cụ thể** (file/test/lệnh) → prompt
sở hữu phần còn thiếu. Một domain chỉ được `DONE` khi có test hoặc route thật
chứng minh; "prompt V2 từng yêu cầu" **không** phải bằng chứng.

Ký hiệu: `DONE` / `PARTIAL` / `MISSING` / `CONFLICT` / `NOT_APPLICABLE` /
`DEFERRED_WITH_ADR`.

---

## 0. Entry gate — V2 có đủ ổn định để mở rộng không?

| Câu hỏi | Bằng chứng | Kết luận |
|---|---|---|
| Kernel còn đổi không? | `server/api/inventory.py` đóng băng 22 route; `tests/test_178` so khớp **hai chiều** route thực tế ↔ inventory ↔ OpenAPI | Ổn định |
| Auth còn đổi không? | `platform_core/public_api/keys.py` + 35 test `test_179` + 19 test `test_180`; định dạng token `ltt_sk_<key_id>_<secret>` đã có test hồi quy cho ký tự `_` | Ổn định |
| Credit/idempotency còn đổi không? | `test_182`, `test_193`: 839 request trùng khoá → **1 job, 1 hold**; 7 kịch bản bơm lỗi đều `reconcile ok` | Ổn định |
| Tool contract schema còn đổi không? | `platform_core/registry.py:344` khoá cứng 7 khoá hợp đồng (`public_name, description, models, enums, hidden, scopes, deprecated`), fail-closed; golden `tests/golden/public_api_catalog_v1.json` | Ổn định |
| Migration head | `c9d0e1f2a3b4` (webhooks), sau `b8c9d0e1f2a3` (idempotency), `a7b8c9d0e1f2` (developer keys) | Cố định |
| Gate | `python tools\gate.py` → `RESULT: PASS` 10/10, pytest 2.530,9 s | Xanh |
| Test Public API | 317 test (`test_178`…`test_193`, `--collect-only`) | Có |
| Git | nhánh `master`, cây **bẩn**: toàn bộ V2 chưa commit (26 `M`, 31 `??`) | Rủi ro thao tác, xem §5 |

→ **V2 đủ ổn định. Không có blocker. Extension được phép bắt đầu.**

---

## 1. Domain A–N (những gì V2 đụng tới)

> **Cập nhật sau EXT-08 (2026-08-13):** Extension domain 11
> (`playground`) `MISSING` → `DONE`. Trang gọi thẳng `/api/v1` bằng
> khóa của khách — không có endpoint portal nào chạy tool, nên không
> có đường thứ hai tới tính tiền.

> **Cập nhật sau EXT-07 (2026-08-13):** Extension domain 10
> (`quickstart/env/recipes`) `MISSING` → `DONE`; snippet sinh từ hợp
> đồng cho 6 dạng client + n8n/Make, và một test E2E đi đúng bảy
> bước tài liệu mô tả.

> **Cập nhật sau EXT-06 (2026-08-13):** Extension domain 9
> (`variable reference`) `PARTIAL` → `DONE`: 29/29 tham số công khai
> có mô tả + ví dụ, trang tham chiếu từng tool sinh từ hợp đồng, và
> registry từ chối tài liệu lệch. Đổi tên tham số tiếng Việt →
> EXT-17.

> **Cập nhật sau EXT-05 (2026-08-13):** domain K (developer portal)
> `PARTIAL` → `DONE`; Extension domain 8 (`Developer API tab`)
> `PARTIAL` → `DONE`. **Rủi ro X4 đóng.** Playground/logs/thông báo
> vẫn thuộc EXT-08/09/11 và hiện là mục có tên, chưa có link.

> **Cập nhật sau EXT-04 (2026-08-13):** Extension domain 4 (`projects`) và 6
> (`IP restriction / key expiry`) `MISSING` → `DONE`; domain 5 (`service
> accounts`) và 7 (`OAuth`) → `DEFERRED_WITH_ADR` (D6, D7, D1). Domain C
> `PARTIAL` → `DONE`. Rủi ro X4 vẫn mở (portal chưa có lối vào từ header) —
> EXT-05.

> **Cập nhật sau EXT-03 (2026-08-13):** domain D chuyển `PARTIAL` → `DONE`;
> Extension domain 3 (`models/capabilities catalog`) `MISSING` → `DONE`. Thêm
> `GET /models`, `GET /models/{name}`, capability suy từ tên tool,
> `contract_hash`, alias tool, và schema của mọi tool nằm trong OpenAPI.
> Riêng "contract compatibility checker" vẫn thuộc EXT-17.

> **Cập nhật sau EXT-02 (2026-08-13):** domain A chuyển `PARTIAL` → `DONE`;
> Extension domain 1 (`execution mode`) và 2 (`error/retry catalog`) chuyển
> `MISSING`/`PARTIAL` → `DONE`. Rủi ro X5 đã đóng. Chi tiết ở
> `PROTOCOL_V1.md` và mục EXT-02 của `EXTENSION_PROGRESS.md`. Các dòng "Thiếu"
> bên dưới giữ nguyên làm hồ sơ **tại thời điểm audit**, không xoá — mất lý do
> là mai sau lặp lại đúng cuộc tranh luận đã xong.

### A. Kernel / versioning / request-id / errors — `PARTIAL` → **`DONE`** (EXT-02)

| Có | Bằng chứng |
|---|---|
| `/api/v1` là sub-application mount riêng, kill switch ở middleware | `server/api/__init__.py`, `server/api/guard.py:30` |
| Inventory đóng băng + kiểm hai chiều | `server/api/inventory.py`, `test_178` |
| RFC 9457 `application/problem+json`, 12 mã lỗi ổn định | `platform_core/public_api/errors.py:31-56` |
| Correlation id trong **mọi** problem body và **mọi** dòng log | `server/api/errors.py:51`, `server/api/guard.py:71` |
| Phân trang offset, trần 100/trang, trần offset 100.000 | `platform_core/public_api/pagination.py` |

| Thiếu | Bằng chứng thiếu | Prompt |
|---|---|---|
| **Header `X-Correlation-ID` chỉ có trên phản hồi bị guard chặn**, không có trên phản hồi thành công → khách không cầm được id để mở ticket | `guard.py:44` đặt header trong nhánh `except ApiError`; nhánh `call_next` không đặt | EXT-02 |
| **`Retry-After` chỉ nằm trong body** (`{"retry_after": n}`), không phải header HTTP chuẩn → proxy/SDK generic không hiểu | `platform_core/public_api/limits.py:93-95`; grep `Retry-After` toàn repo: không có | EXT-02 |
| Không có catalog lỗi ↔ **retryable/không** ↔ hành động khuyến nghị | `errors.py` chỉ ánh xạ status→code | EXT-02 |
| Không khai báo `API-Version`/deprecation header, không có changelog | grep `changelog`, `deprecat` trong `server/api`: không có (`deprecated` chỉ là field của tool contract) | EXT-17 |
| Không có cursor pagination (đã cố ý chọn offset) | `pagination.py:8-12` ghi rõ lý do | `DEFERRED_WITH_ADR`, EXT-02 xác nhận lại |

### B. Developer API keys — `DONE`

`platform_core/public_api/keys.py` + bảng `developer_api_keys`
(`alembic/versions/20260813_1000_developer_api_keys.py`): HMAC-SHA256 + pepper
ngoài CSDL, so sánh hằng thời gian, lộ plaintext đúng một lần, xoay pepper theo
`LTT_API_KEY_PEPPER_V<n>`, revoke/rotate. 35 test.

Thiếu (thuộc domain khác, không phải lỗi của B): **hết hạn theo thời gian** và
**giới hạn IP** — xem C.

### C. Scopes / tenant — `PARTIAL`

| Có | Bằng chứng |
|---|---|
| 9 scope, mặc định chỉ đọc | `platform_core/public_api/scopes.py` |
| Owner nằm trong `WHERE`; sai chủ → 404 giống hệt "không tồn tại" | `principal.py`, `test_192::test_bola_*` |
| BFLA: thiếu scope → 403 ở biên, trước mọi thao tác tiền | `test_192::test_bfla_*` |
| `allowed_tools` theo từng khoá | `keys.py`, `principal.ensure_tool_allowed` |

| Thiếu | Bằng chứng | Prompt |
|---|---|---|
| **Project / Application** (nhóm khoá theo tích hợp) | grep `project_id` trong `platform_core/public_api` + `server/api`: **0 kết quả** | EXT-04 |
| **Service account** | grep `service_account`: **0 kết quả** | EXT-04 |
| **Giới hạn IP / hết hạn khoá** | bảng `developer_api_keys` không có cột `expires_at`/`allowed_ips` | EXT-04 |
| **OAuth delegated access** (client, PKCE, redirect chính xác, refresh rotation) | grep `oauth`/`pkce` trong code: **0**; chỉ xuất hiện trong docs như lý do đóng băng `socialbot` | EXT-04 — phải ra quyết định, được `DEFERRED_WITH_ADR` nhưng **không** được để UNKNOWN |

### D. Tool contract / OpenAPI — `PARTIAL`

Có: hợp đồng fail-closed 7 khoá (`registry.py:322`), catalog dựng từ manifest
(`catalog.py`), `/api/v1/openapi.json` chỉ chứa route công khai, golden file +
`tools/build_public_api_docs.py --check` chặn drift, 23 test (`test_181`).

| Thiếu | Bằng chứng | Prompt |
|---|---|---|
| **Catalog model/capability công khai** — alias model nằm *bên trong* contract của từng tool, không có `/models` và không có khái niệm capability | `registry.py:344` có khoá `models`; không có route nào liệt kê model | EXT-03 |
| **Execution mode** không tồn tại như một khái niệm khai báo được | grep `execution_mode|ASYNC_JOB|STREAM`: **0 kết quả** | EXT-02 (chuẩn) + EXT-03 (khai trong contract) |
| Không có contract **compatibility checker** (đổi schema kiểu gì là breaking) | chỉ có golden so sánh bằng nhau, không phân loại thay đổi | EXT-17 |

### E. Quotes / jobs / credit / idempotency — `DONE`

Quote ký `itsdangerous` khoá theo user+tool+fingerprint input+TTL 15 phút
(`quotes.py`); idempotency UNIQUE `(key_id, operation, idempotency_key)`
(`idempotency.py`); hold→settle/refund dùng đúng sổ credit hiện có
(`invocation.submit` → `platform_core/job_submit.submit_with_credit`). Bằng
chứng mạnh nhất: `test_193` — crash giữa hold và queue để lại **0 hold, 0 job**;
worker chết giữa job kết sổ **đúng một lần**.

Thiếu, và là thiếu **thương mại** chứ không phải kỹ thuật: **pricing version**.
Giá lấy trực tiếp từ `registry.credit_for(job_type, params)`
(`invocation.py:220-230`), không có bản ghi "quote này định giá theo bảng giá
phiên bản nào" → đổi giá là đổi hồi tố cách đọc lịch sử. → EXT-15.

### F. Uploads / artifacts — `DONE`

Staging → promote sau khi giữ chỗ (Q85), bù trừ khi lỗi, artifact lọc theo
**output schema đã publish** (`media.storage_key_for`), 23 test (`test_183`).
Giới hạn đã biết: mảng media (`image_keys`) chưa hỗ trợ → ẩn trong contract.

### G. Rate / quota / concurrency / capacity — `PARTIAL`

Có 5 lớp: chặn dò khoá, RPM, create-RPM, job đồng thời (CSDL), trần credit ngày
(`limits.py`, 19 test `test_184`), cộng trần theo lớp tài nguyên
(`LTT_PUBLIC_API_CLASS_CONCURRENCY`). Đo thật: một khoá lạm dụng → khoá ngoan
**0×429** (`test_193`).

| Thiếu | Bằng chứng | Prompt |
|---|---|---|
| Giới hạn nằm **trong tiến trình** | `limits.py` dùng bộ đếm bộ nhớ; đúng với 1 web process (ADR-005) nhưng không đúng nếu scale ngang | EXT-14 |
| Không có **tier/policy** (mọi khoá cùng một bộ số từ env) | `config.py` chỉ có biến toàn cục | EXT-14 |
| Không có **kill switch theo tool/theo khoá** (chỉ có toàn cục `READ_ONLY` và danh sách tool) | `config.py` | EXT-14 |

### H. Webhooks — `PARTIAL`

Outbox ghi **trong** transaction của job (`job_runner._enqueue_webhooks`), worker
giao sau, ký HMAC, chống SSRF (chỉ https, kiểm mọi IP phân giải, kiểm lại sau mỗi
redirect), backoff → `dead` sau 6 lần. 28 test (`test_185`).

Thiếu: **event catalog** công khai, **resend/replay** thủ công, console cho
khách xem payload/attempt. → EXT-10.

### I. Usage / audit — `PARTIAL`

`/api/v1/usage` + `/credits/balance` dựng **từ sổ credit**, không lưu hai lần
(`usage.py`), có `reconcile()` và `tools/reconcile_public_api_usage.py`. 15 test.

Thiếu: **request log cho khách** (hiện chỉ có log file của operator),
**budget/alert**, **notification**. → EXT-09, EXT-11.

### J. App disposition / coverage — `DONE` (có sửa một sai lệch)

`APP_DISPOSITION_V1.md` + `test_190` (22 test) máy kiểm 14/14 app.

**OBSERVED_DIFFERENCE (đã sửa trong lượt này):** §2 của tài liệu ghi "6/21
ToolSpec" và "15 ToolSpec còn lại", trong khi `registry.discover()` thật cho
**21 tool, 5 exposed, 16 không public**. Tài liệu đã sửa. Test `test_190` không
bắt được vì nó kiểm *tập hợp* app/tool, không kiểm *con số trong câu văn*.

### K. Developer portal — `PARTIAL`

Có `/developers` (một trang): tạo/xoay/thu hồi khoá, danh sách webhook, job API
gần đây (`server/routes/developer.py`, `server/templates/developers.html`), 15
test + đã kiểm trình duyệt thật.

| Thiếu | Bằng chứng | Prompt |
|---|---|---|
| **Không có link nào tới `/developers` trong header** — khách không tìm thấy | `server/templates/_header.html` không chứa `/developers` | EXT-05 |
| Không có Overview/Projects/Playground/Logs/Usage/Docs/Notifications/Settings | portal chỉ có 4 handler | EXT-05…EXT-12 |

### L. Admin — `MISSING`

`server/admin.py` có 14 view, **không view nào** cho Public API: grep
`DeveloperApiKey` trong `server/admin.py` → **0**. `ApiKeyAdmin` ở đó là **khoá
provider**, một domain khác (bất biến §3 của COMMON_RULES). Không có nơi nào cho
admin xem/thu hồi khoá khách, xem request, chỉnh policy, đổi giá, hay tra cứu hỗ
trợ. → EXT-13, EXT-14, EXT-15, EXT-16.

### M. Docs / SDK — `PARTIAL`

Có `DEVELOPER_GUIDE.md` (sinh bởi `tools/build_public_api_docs.py`, có `--check`
chặn drift), SDK Python (`sdk/python/ltt_public_api.py`) và TypeScript
(`sdk/typescript/ltt-public-api.ts`).

Thiếu: quickstart/env-var/recipe (n8n, Make, cURL thuần), Postman collection,
CLI, OpenAPI tải về từ portal, và **toolchain kiểm SDK TypeScript**. → EXT-07,
EXT-18.

### N. Security / load / recovery — `DONE`

`THREAT_MODEL_V1.md` (T1–T14) + 18 test `test_192` (10 lớp OWASP API) +
`test_193` (tải + 7 kịch bản bơm lỗi) + `RELEASE_READINESS_V1.md`.

Ba việc **chưa chạy được** và đã ghi rõ: diễn tập khôi phục trên PostgreSQL,
đo tải qua Cloudflare, quét CVE phụ thuộc. Extension không xoá được ba việc này
bằng code — chúng cần tài nguyên/phê duyệt. → EXT-21 nhắc lại.

---

## 2. Domain Extension (những gì V2 **không** làm)

| # | Domain | Trạng thái | Bằng chứng (grep/route/bảng) | Prompt |
|---|---|---|---|---|
| 1 | Execution mode SYNC/ASYNC/STREAM/BATCH | `MISSING` | grep `execution_mode|ASYNC_JOB|STREAM` = 0; mọi tool hiện là async-job ngầm định | EXT-02 |
| 2 | Error/retry catalog | `PARTIAL` | 12 mã có, phân loại retry không | EXT-02 |
| 3 | Models/capabilities catalog công khai | `MISSING` | không có route; alias model nằm trong contract từng tool | EXT-03 |
| 4 | Projects / Applications | `MISSING` | grep `project_id` = 0 | EXT-04 |
| 5 | Service accounts | `MISSING` | grep = 0 | EXT-04 |
| 6 | IP restriction / key expiry | `MISSING` | cột không tồn tại | EXT-04 |
| 7 | OAuth delegated access | `MISSING` (cần quyết định) | grep `oauth|pkce` trong code = 0 | EXT-04 |
| 8 | Developer API tab (IA đầy đủ) | `PARTIAL` | 1 trang, không có trong nav | EXT-05 |
| 9 | Variable reference tự sinh | `PARTIAL` | `DEVELOPER_GUIDE.md` có schema nhưng không có bảng biến theo app/model | EXT-06 |
| 10 | Quickstart / env vars / recipes | `MISSING` | không có n8n/Make/Postman | EXT-07 |
| 11 | Playground | `MISSING` | không có route UI nào gọi API thật | EXT-08 |
| 12 | Request log / trace / job timeline cho khách | `MISSING` | log chỉ vào file của operator (`ltt.public_api.access`) | EXT-09 |
| 13 | Webhook console / event catalog / resend | `MISSING` | chỉ có list deliveries qua API | EXT-10 |
| 14 | Budgets / credit alerts / notifications | `MISSING` | chỉ có trần credit ngày (chặn cứng), không có cảnh báo; `platform_core/mailer.py` có sẵn để tái dùng | EXT-11 |
| 15 | Sandbox / test mode | `MISSING` | grep `sandbox|test_mode` trong code = 0 (chỉ là chữ trong docs nói *chưa có*) | EXT-12 |
| 16 | Admin API console | `MISSING` | xem §1.L | EXT-13 |
| 17 | Policy/tier/quota/kill switch | `MISSING` | xem §1.G | EXT-14 |
| 18 | Pricing version / margin / quote simulator | `MISSING` | giá lấy thẳng từ `credit_for`, không snapshot | EXT-15 |
| 19 | Support trace / ops console | `MISSING` | không có nơi tra một `request_id` ra job/credit/webhook | EXT-16 |
| 20 | Versioning / changelog / deprecation / status / incidents | `MISSING` | `/status` hiện là trang **admin** về sức khoẻ hệ thống, không phải status công khai của API | EXT-17 |
| 21 | CLI / Postman / OpenAPI tải về / recipes | `MISSING` | xem §1.M | EXT-18 |
| 22 | Privacy / retention / export / delete cho dữ liệu API | `MISSING` | `platform_core/job_events.py` có retention cho job event (365/30 ngày); **4 bảng Public API không nằm trong bất kỳ purge nào** — `webhook_deliveries` sẽ phình vô hạn | EXT-19 |
| 23 | Chứng nhận 100% app/tool/model/execution mode | `PARTIAL` | app 14/14 có disposition; **model và execution mode chưa có disposition** | EXT-20 |
| 24 | Load/chaos/security/recovery cho toàn nền tảng API | `PARTIAL` | đã có cho `/api/v1` V2; chưa có cho portal/admin/OAuth/stream/batch | EXT-21 |

---

## 3. Disposition 100% — 21 ToolSpec, không UNKNOWN

Nguồn: `registry.discover()` chạy thật ngày 2026-08-13.
Cột **Execution mode** là *đề xuất* của EXT-01, sẽ được **chốt** ở EXT-02/EXT-03.

| # | App | Tool | Public V2 | Execution mode (đề xuất) | Disposition |
|---|---|---|---|---|---|
| 1 | thumbnail | `image.thumbnail` | ✅ | ASYNC_JOB | EXPOSED |
| 2 | taoanh | `image.generate` | ✅ | ASYNC_JOB | EXPOSED (4 alias model) |
| 3 | taoanh | `image.batch_generate` | — | BATCH | DEFER — trùng năng lực với `count` của `image.generate`; mở khi EXT-02 chốt ngữ nghĩa BATCH |
| 4 | upscalevideo | `image.upscale` | ✅ | ASYNC_JOB (GPU) | EXPOSED |
| 5 | upscalevideo | `video.upscale` | — | ASYNC_JOB | MIGRATE_THEN_EXPOSE — giá theo thời lượng client khai + worker nâng hold |
| 6 | prompt_ai_ommi | `text.prompt_package` | ✅ | ASYNC_JOB | EXPOSED |
| 7 | prompt_ai_ommi | `story.storyboard` | ✅ | ASYNC_JOB | EXPOSED |
| 8 | autosubvideo | `video.subtitle` | — | ASYNC_JOB | MIGRATE_THEN_EXPOSE — cùng nguyên nhân gốc |
| 9 | taoclipngan | `video.short_clips` | — | ASYNC_JOB (GPU) | MIGRATE_THEN_EXPOSE — cùng nguyên nhân gốc |
| 10 | taovideo | `video.generate` | — | ASYNC_JOB | MIGRATE_THEN_EXPOSE — enum hợp lệ phụ thuộc model |
| 11-12 | kichban | `text.script`, `text.generate` | — | NOT_PUBLIC | RETIRED (Q69) |
| 13-21 | mediatools | `asset.image`, `asset.images`, `asset.video`, `asset.audio`, `audio.generate`, `video.extract_frames`, `media.merge_image`, `media.merge_video`, `video.social_import` | — | NOT_PUBLIC | INTERNAL_ONLY (`surface=runtime`, Q72; `video.social_import` nhận URL → SSRF) |

Ba app **không có ToolSpec** nên không xuất hiện ở bảng trên nhưng vẫn có
disposition trong `APP_DISPOSITION_V1.md`: `chataistudio` (DEFER — không có Job,
là ứng viên **STREAM** đầu tiên nếu EXT-02 chốt được ngữ nghĩa credit/cancel cho
stream), `agent` (DEFER — runtime điều phối), `demo`/`qualitylab`/`socialbot`
(INTERNAL_ONLY).

**Model:** hôm nay chỉ `image.generate` khai alias công khai (`standard`,
`standard-lite`, `enhanced`, `pro`). Mọi tool khác **ẩn** `model`. Chưa có
disposition cấp model → EXT-03 phải lập bảng model và EXT-20 chứng nhận.

---

## 4. REUSE — cái Extension phải dùng lại, không được xây lại

| Cần gì | Dùng lại cái gì | Cấm làm gì |
|---|---|---|
| Chạy việc | `Job` + worker + `job_submit.submit_with_credit` | Tạo hàng đợi thứ hai |
| Tiền | sổ credit hiện có (`platform_core/credit.py`) | Tạo ledger thứ hai cho API |
| Định danh khách | `DeveloperApiKey` + `Principal` | Dùng provider `api_keys` làm khoá khách |
| Lỗi | `platform_core/public_api/errors.py` | Định dạng lỗi riêng cho route mới |
| Phân trang | `pagination.PageRequest` | Tham số trang tuỳ hứng |
| Giới hạn | `limits.py` | Bộ đếm riêng cho từng tính năng |
| Webhook | `outbox.py` + `delivery.py` | Gửi HTTP thẳng trong request |
| Email | `platform_core/mailer.py` (Resend) | Client SMTP mới |
| Lưu trữ | `platform_core/storage.py` | Đường ghi file riêng |
| Bảng mới | Alembic + thêm UNIQUE vào `tools/restore_drill_schema.py` | `create_all()` lúc chạy |
| Trang UI | `server/templating.py` + `asset_ver` | Chuỗi HTML không cache-bust |

---

## 5. Rủi ro thấy được từ EXT-01

| # | Rủi ro | Mức | Ghi chú |
|---|---|---|---|
| X1 | **Toàn bộ V2 chưa commit** (26 `M` + 31 `??`). Extension sẽ chồng thêm hàng chục file lên cùng một cây bẩn; hỏng ở giữa thì không có điểm lùi | **Cao** | Nên commit V2 trước EXT-02. Là việc của chủ sản phẩm, không tự làm |
| X2 | `webhook_deliveries` không có retention → phình vô hạn | Trung bình | EXT-19, nhưng nếu bật API trước đó thì phải theo dõi |
| X3 | Giới hạn nhịp per-process | Trung bình | Chặn scale ngang; EXT-14 phải viết ADR chứ không âm thầm thêm Redis |
| X4 | Portal không có lối vào từ header | Thấp (UX) | EXT-05 |
| X5 | Không có `X-Correlation-ID` trên phản hồi thành công → hỗ trợ khách hàng phải đoán | Trung bình | EXT-02, chặn EXT-16 |
| X6 | 21 prompt Extension sẽ thêm nhiều bảng/route; ngân sách gate (~42 phút/lần chạy full) là chi phí thật | Thấp | Dùng `--quick` giữa chừng, full ở checkpoint 4/8/12/16/20/21 |
