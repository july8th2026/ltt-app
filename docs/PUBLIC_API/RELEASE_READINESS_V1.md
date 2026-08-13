# Public API V1 — Release readiness (Prompt 17)

Ngày: 2026-08-13. Quyết định nền tảng: **Q92**.
Kết luận ở cuối file. **Pack này không deploy production** — deploy là lệnh riêng
của chủ sản phẩm.

---

## A. Inventory freeze

### Endpoint (24)

```
GET    /api/v1/health                    GET    /api/v1/capabilities
GET    /api/v1/me                        GET    /api/v1/openapi.json
GET    /api/v1/tools                     GET    /api/v1/tools/{tool_name}
GET    /api/v1/models                    GET    /api/v1/models/{model_name}
POST   /api/v1/quotes
POST   /api/v1/jobs                      GET    /api/v1/jobs
GET    /api/v1/jobs/{job_id}             POST   /api/v1/jobs/{job_id}/cancel
POST   /api/v1/uploads                   POST   /api/v1/uploads/{id}/content
POST   /api/v1/uploads/{id}/confirm
GET    /api/v1/artifacts/{id}            GET    /api/v1/artifacts/{id}/content
POST   /api/v1/webhooks                  GET    /api/v1/webhooks
GET    /api/v1/webhooks/deliveries        DELETE /api/v1/webhooks/{webhook_id}
GET    /api/v1/credits/balance           GET    /api/v1/usage
```

Bề mặt phiên (không thuộc `/api/v1`): `/developers` — nơi **duy nhất** tạo khóa.

### Tool đang mở (5) và giá

| Tool | Giá | Ghi chú |
|---|---|---|
| `image.thumbnail` | 5 credit/ảnh | ẩn `model` (giá không theo model) |
| `image.generate` | 5/5/8/16 theo alias | 4 alias, 1 ảnh tham chiếu qua upload |
| `image.upscale` | 2 (fast) / 4 (quality) | đường GPU |
| `text.prompt_package` | theo `scene_count` | kết quả là dữ liệu |
| `story.storyboard` | theo `scene_count` | kết quả là dữ liệu |

Disposition đầy đủ 14/14 app ở `APP_DISPOSITION_V1.md`, **máy kiểm** bằng
`tests/test_190_public_api_coverage.py`.

### Migration

`b6c7d8e9f0a1` → `a7b8c9d0e1f2` (developer keys) → `b8c9d0e1f2a3` (idempotency)
→ **`c9d0e1f2a3b4`** (webhooks). Cả ba có `downgrade()` chạy được; vòng
tiến–lùi–tiến xanh; hai UNIQUE mới đã vào `tools/restore_drill_schema.py`.

### Config / feature flag

| Biến | Mặc định | Vai trò |
|---|---|---|
| `LTT_PUBLIC_API` | `0` | công tắc chính — **tắt** |
| `LTT_PUBLIC_API_TOOLS` | rỗng | allowlist tool — **rỗng = không tool nào** |
| `LTT_PUBLIC_API_READ_ONLY` | `0` | công tắc khẩn cấp (chặn mọi ghi) |
| `LTT_API_KEY_PEPPER` | **bắt buộc** | thiếu ⇒ không cấp/không xác minh được khóa |
| `LTT_API_KEY_PEPPER_VERSION` / `_V<n>` | `1` / — | xoay pepper |
| `LTT_PUBLIC_API_RPM` / `_CREATE_RPM` | 120 / 20 | nhịp theo khóa |
| `LTT_PUBLIC_API_MAX_ACTIVE_JOBS` | 5 | job đồng thời theo tài khoản |
| `LTT_PUBLIC_API_CLASS_CONCURRENCY` | rỗng | trần theo lớp tài nguyên (vd `gpu:1`) |
| `LTT_PUBLIC_API_DAILY_CREDIT` | `0` (tắt) | **nên đặt trước khi mở** |
| `LTT_PUBLIC_API_MAX_BODY_BYTES` | 256 KiB | trần body |
| `LTT_PUBLIC_API_CORS_ORIGINS` | rỗng | trình duyệt gọi API (mặc định không) |
| `LTT_PUBLIC_API_TRUSTED_PROXIES` | `127.0.0.1,::1` | ai được nói `CF-Connecting-IP` |
| `LTT_PUBLIC_API_AUTH_FAILURES` / `_WINDOW` | 20 / 300 s | chống dò khóa |

### Worker / nền

Không có tiến trình mới. Worker hiện tại thêm hai việc định kỳ: **giao webhook**
(15 s) và **in metrics** (5 phút).

### OpenAPI / SDK

`GET /api/v1/openapi.json` (chỉ route công khai). SDK: `sdk/python/` (không phụ
thuộc ngoài), `sdk/typescript/` (fetch + `crypto.subtle`).

### Hai domain credential vẫn tách

`api_keys` (provider, mã hoá, giải mã được) ≠ `developer_api_keys` (khách, digest
một chiều). Có test chốt ở `test_193`.

---

## B. Test pyramid — kết quả thật

| Tầng | Bằng chứng |
|---|---|
| Unit (config, lỗi, pagination, scope, quote, limits, metrics) | test_178, 179, 184, 192 |
| Integration CSDL/credit | test_182, 186, 193 |
| Contract / OpenAPI / drift | test_181, 187, 191 (golden + `--check` tài liệu) |
| Tenant & security | test_180, 192 (10 lớp OWASP API) |
| Upload / artifact | test_183 |
| Webhook | test_185 |
| SDK / portal | test_191 (+ kiểm trình duyệt thật) |
| App adapter (wave 1–3) | test_187, 188, 189 |
| Coverage 100% app | test_190 |
| Release gate | test_193 |
| Gate toàn repo | `python tools\gate.py` |
| Quét bí mật | 0 finding |

Tổng test của Public API: **~230**, trên tổng ~2.900 test của repo.

---

## C. Canary (stub provider)

`test_193::test_the_full_chain_runs_and_settles_exactly_once` chạy nguyên chuỗi
với `image.thumbnail`: auth → scope → quote → idempotency → hold → queue →
**worker thật** → storage → artifact → settle → usage → webhook. Sổ tiền sau đó:
**1 hold, 1 settle, 0 refund**.

Canary **thật** (có khóa provider, tốn tiền) là việc của deployment: chạy trên
máy chủ sau khi bật cờ, theo runbook mục 4 của `THREAT_MODEL_V1.md`.

---

## D. Load / soak — số đo thật

Harness: `tools/public_api_load_test.py` (in-process, SQLite tạm, **không** chạm
production).

| Kịch bản | Kết quả |
|---|---|
| `reads` 6 luồng × 6 s | 1.063 request, **~177 rps**, p50 29 ms, p95 47 ms, p99 88 ms, 100% 200 |
| `duplicates` 6 luồng × 6 s (cùng một `Idempotency-Key`) | 839 request → **1 job, 1 hold**; 1×201, 838×200 replay |
| `abusive` 1 khóa dồn + 3 khóa lịch sự × 8 s | khóa dồn: 120×200 rồi **1.375×429**; khóa lịch sự: **24×200, 0×429** |

Diễn giải: throughput control-plane đủ xa nhu cầu hiện tại; **bất biến tiền giữ
được dưới đồng thời**; và một khóa lạm dụng **không** làm suy giảm khóa khác —
đúng tiêu chí chấp nhận của Prompt 08.

Chưa đo: tải trên deployment thật qua Cloudflare (cần phê duyệt riêng), soak dài
giờ, và hành vi khi hàng đợi có hàng nghìn job GPU.

---

## E. Failure recovery — đã bơm lỗi và chứng minh

| Sự cố bơm vào | Kết quả |
|---|---|
| Crash **giữa hold và queue** | 0 hold, 0 job, reconcile `ok` |
| Worker chết giữa job (orphan) | job được nhặt lại; **1 hold, đúng 1 lần kết sổ** (settle *hoặc* refund, không bao giờ hai) |
| Provider timeout | hoàn đủ, `refund` đúng 1 dòng, reconcile `ok` |
| Storage lỗi (đĩa đầy) | khách không bị trừ; hoàn đúng 1 lần |
| Webhook receiver chết | job vẫn `succeeded`, settle đúng 1 lần |
| Retry trùng khóa (tuần tự + đồng thời) | 1 job, 1 hold |
| Crash sau promote file | file trả về `staging/`, không orphan |

Tất cả đều kèm `usage.reconcile(...)` → `ok=True`.

---

## F. Gate PASS/FAIL

| Gate | Kết quả |
|---|---|
| Full repo gate (`tools\gate.py`) | **PASS 10/10** — pytest 2.531 s, xem PROGRESS mục Prompt 17 |
| Security suite (10 lớp OWASP) | **PASS** |
| Secret scan | **PASS** (0 finding) |
| Contract drift (catalog ↔ golden ↔ docs) | **PASS** |
| Coverage 100% app | **PASS** |
| Migration tiến–lùi–tiến | **PASS** |
| Backup/restore rehearsal (SQLite) | **PASS** |
| Backup/restore trên PostgreSQL | **CHƯA CHẠY** — cần cụm riêng, việc của operator |
| Load/soak in-process | **PASS** |
| Load qua Cloudflare | **CHƯA CHẠY** — cần phê duyệt riêng |
| Quét CVE phụ thuộc | **CHƯA CHẠY** — không có công cụ cài sẵn |
| Kiểm trình duyệt (portal) | **PASS** (server dùng-một-lần, 0 lỗi console) |

### Gate này đã bắt được một lỗi thật

Lần chạy full gate đầu tiên **đỏ**: `test_25 …::test_gap8_web_app_starts_daemon`.
Nguyên nhân không phải flaky — `tools/public_api_load_test.py` đặt
`LTT_DATABASE_URL` / `LTT_DATA_DIR` / `LTT_API_KEY_PEPPER` vào `os.environ` và
không trả lại; `test_193` gọi hàm đó, nên mọi test sau thấy `LTT_DATA_DIR` trỏ
vào thư mục tạm đã xoá → `load_settings()` ném → `core_settings=None` →
**MaintenanceDaemon lặng lẽ không khởi động**. Đã sửa ở gốc (`run()` khôi phục
env + `reset_engine()` trong `finally`) và có test hồi quy. Ghi lại ở đây vì nó
là bằng chứng chạy gate đầy đủ có giá trị: `pytest` một file thì xanh, chỉ toàn
bộ suite mới lộ.

## Giới hạn đã biết (nói thẳng, không giấu)

1. **Giới hạn nhịp là per-process.** Một tiến trình web thì đúng; chạy nhiều
   instance thì lớp nhịp nhân lên theo số instance (lớp job/credit vẫn đúng).
2. **Không có sandbox.** Mọi lời gọi tiêu credit thật.
3. **Trần credit ngày mặc định tắt** — cần chủ sản phẩm chọn số.
4. **3 tool bị hoãn vì một nguyên nhân gốc**: giá theo thời lượng client khai +
   worker nâng hold (`video.upscale`, `video.subtitle`, `video.short_clips`).
5. **`video.generate` hoãn** vì tập giá trị hợp lệ phụ thuộc model.
6. **Chat và Agent DEFER** — chat chưa có Job; agent là runtime điều phối.
7. **SDK TypeScript chưa có toolchain kiểm** trong repo.
8. **Chưa quét CVE phụ thuộc**; nhiều gói có bản mới hơn.
9. **Media dạng mảng** (`image_keys`) chưa hỗ trợ qua API.
10. **Artifact qua storage cục bộ** đi qua tiến trình web; production dùng R2 nên
    đi presigned URL.

## Rollback — cụ thể, ba mức

| Mức | Lệnh | Ảnh hưởng |
|---|---|---|
| 1. Dừng ghi | `LTT_PUBLIC_API_READ_ONLY=1` + restart web | Đọc vẫn chạy; job mới bị từ chối; job đang chạy và settlement **không** đổi |
| 2. Tắt API | bỏ `LTT_PUBLIC_API` + restart web | `/api/v1` không được mount; UI/worker/job cũ nguyên vẹn |
| 3. Lùi schema | `alembic downgrade b6c7d8e9f0a1` | Xoá 4 bảng của Public API. **Chỉ làm khi chưa có khách dùng** — nó xoá khóa, bản ghi idempotency và webhook. Job/credit/upload của nền tảng **không** bị chạm. |

Gỡ mã nguồn (nếu cần): xoá `platform_core/public_api/`, `server/api/`,
`server/routes/developer.py`, `sdk/`, hoàn nguyên 3 chỗ sửa nhỏ trong
`server/app.py` và một dòng import trong `platform_core/models.py`.

## Checklist trước khi bật (Cloudflare + cấu hình)

1. `LTT_API_KEY_PEPPER` đã sinh, đã cất, **đã vào backup Q28**.
2. `LTT_PUBLIC_API_DAILY_CREDIT` đã đặt một con số.
3. `alembic upgrade head` → `c9d0e1f2a3b4`.
4. Cloudflare: `/api/v1/*` đi cùng host `app.lttstudios.com` — **không cần rule
   mới**; nhưng kiểm hai điều: (a) không có rule cache nào chạm `/api/v1`
   (response đã `no-store`, nhưng edge rule sai có thể phục vụ bản cũ như từng
   xảy ra với `ltt.css`); (b) trần 100 MB và 100 giây vẫn áp — upload lớn phải
   đi presigned R2, job dài phải qua hàng đợi (đã đúng theo thiết kế).
5. Bật `LTT_PUBLIC_API=1` + liệt kê tool trong `LTT_PUBLIC_API_TOOLS`.
6. Restart **web và worker**.
7. Canary thật bằng một khóa: `/me` → `/tools` → `/quotes` → `/jobs` → artifact.

## Giám sát sau khi bật

- Log `ltt.public_api.access`: mỗi request một dòng, có `status`, `latency_ms`,
  `key_id`, `credit_delta`.
- Log `ltt.public_api.auth`: mã lý do từ chối + `key_id`.
- Counters in mỗi 5 phút bởi worker.
- Đáng chú ý sớm: `auth_failure` tăng vọt (dò khóa), `rate_limited` tăng
  (một tích hợp sai), `responses_5xx` > 0, `idempotency_conflict` (client bug),
  `webhook_failed` tăng (receiver của khách chết).

## Kế hoạch canary rollout đề nghị

1. Bật cờ, `LTT_PUBLIC_API_TOOLS=image.thumbnail` — **một tool rẻ nhất**.
2. Một khóa nội bộ, chạy thật vài job, đối chiếu `usage` với sổ credit.
3. Mở `image.generate`, rồi `image.upscale` (GPU) với
   `LTT_PUBLIC_API_CLASS_CONCURRENCY=gpu:1`.
4. Cuối cùng hai tool văn bản.
5. Mỗi bước: xem log truy cập + counters 24 giờ trước khi mở bước sau.

---

# Kết luận

## `READY_FOR_CONTROLLED_DEPLOY`

Cơ sở: mọi gate bắt buộc xanh; bất biến tiền được chứng minh dưới cả crash lẫn
đồng thời; bề mặt mặc định **tắt** và mở theo từng tool; có ba mức rollback,
trong đó hai mức đầu chỉ là một biến môi trường.

Điều kiện kèm theo (không phải tuỳ chọn):

1. Sinh + **sao lưu** `LTT_API_KEY_PEPPER` trước khi bật.
2. Đặt `LTT_PUBLIC_API_DAILY_CREDIT`.
3. Chạy canary thật theo kế hoạch trên; không mở nhiều tool cùng lúc.
4. Chạy `tools/restore_drill_schema.py` trên cụm PostgreSQL test trước khi coi
   là "đã diễn tập khôi phục" ở mức production.

Ba việc chưa chạy được ở đây (PostgreSQL drill, tải qua Cloudflare, quét CVE)
**không** phải lỗi đang mở — chúng cần tài nguyên hoặc phê duyệt ngoài phạm vi
pack này, và đã ghi rõ ở trên để không ai nhầm là đã làm.
