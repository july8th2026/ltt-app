# Public API V1 — Kiến trúc khóa (Prompt 01)

> Nguồn: `docs/QUYET_DINH_NEN_TANG.md` (Q1–Q91) + code/test thật ngày 2026-08-13.
> Tài liệu này KHÔNG cao hơn quyết định nền tảng, code và test. Khi lệch, code
> và quyết định thắng; sửa tài liệu này.

## 0. Một câu

Public API là **lớp adapter/policy mới** đặt trước hạ tầng đã có. Nó **không**
tạo credit ledger, hàng đợi job, provider pool hay storage lifecycle thứ hai.

## 1. Chuỗi đích

```
External client (API key)
  → /api/v1/...                         (API kernel: router + error + version)
  → Developer API auth                  (bảng MỚI, KHÔNG dùng platform_core.ApiKey)
  → scope + tenant policy               (principal = User hiện hữu)
  → rate/quota/concurrency              (per-key, per-user; khác allocator provider)
  → Public Tool Catalog                 (allowlist tường minh trên ToolSpec)
  → quote → hold → submit               (platform_core.job_submit.submit_with_credit)
  → bảng `jobs` (PostgreSQL)            (Q26: một nguồn chân lý duy nhất)
  → worker (LTTWorker, tiến trình riêng — Q6)
      → platform_core.registry.resolve_handler → apps/<slug>/jobs.py
      → provider (platform_core.api_pool/providers) | GPU (gpu_lease) | FFmpeg
      → platform_core.storage (Local | R2)
  → complete + credit.quyet_toan        (Q84: thu ≤ hold, variance là của nền tảng)
  → artifact URL + usage + webhook      (webhook: chưa tồn tại, Prompt 09)
```

## 2. Cái đã có (Observed — đọc code thật)

| Năng lực | Nơi ở | Ghi chú quan trọng cho Public API |
|---|---|---|
| Hợp đồng app | `platform_core/registry.py` | `discover()` quét `apps/*/manifest.py`; nền tảng không biết trước slug nào. 14 app nạp sạch, 0 lỗi. |
| Tool contract | `AppManifest.tools: tuple[ToolSpec]` | 21 ToolSpec, có `params_schema`/`returns` typed → **nền cho Public Tool Catalog**. `customer_visible` là cờ palette của Agent, KHÔNG phải cờ public API. |
| Hàng đợi job | `platform_core/jobs.py` + bảng `jobs` | `SELECT … FOR UPDATE SKIP LOCKED`, heartbeat, reclaim orphan, retry backoff, `dedupe_key`. |
| Nộp job + giữ credit | `platform_core/job_submit.py` | `submit_with_credit()` = giá → submit → hold, **cùng một transaction**, caller commit. |
| Sổ credit | `platform_core/credit.py` | Append-only; `pg_advisory_xact_lock` chống double-spend và tuần tự hóa settle/refund; `quyet_toan()` cap thu ≤ hold (Q84). |
| Báo giá ký | `apps/taovideo/quotes.py` | `itsdangerous` + `intent` uuid + dedupe key per-variant. **Chỉ có ở một app** — chưa phải hợp đồng nền tảng. |
| Upload lifecycle | `platform_core/upload_sessions.py` + bảng `upload_sessions` | staging → actual-size + magic signature → `promote(job)` **sau hold** (Q85) hoặc `attach_to_project` (Q89); quota/TTL/sweeper/compensation đã có. |
| Storage | `platform_core/storage.py` | `Storage` interface; Local + R2; `url_for()` presigned; `try_url_for/try_put_url` không nuốt lỗi. |
| Provider credential | `platform_core/api_keys.py`, bảng `api_keys` | **Credential của LTT gọi Gemini/BytePlus/…**, mã hoá Fernet. Tuyệt đối không tái dụng cho customer key. |
| Danh tính người dùng | `platform_core/models.User`, `Session`, `server/auth/session.py` | Session cookie + bảng `sessions` (lưu SHA-256 của token). Không có model organization. |
| Phân quyền app | `platform_core/app_access.py` + middleware | **Mặc định MỞ** (Q25) và ánh xạ path→app theo `route_prefix`. |
| Job event/timeline | `platform_core/job_events.py`, bảng `job_events` | Tách `customer`/`internal`, có sanitize secret, retention 365/30 ngày (Q75/Q76). |
| Log tiến trình | `platform_core/observability.py` | JSONL redacted, rotate; context `job_id/app_slug/worker_id/correlation_id`. |
| Hợp đồng lỗi | `server/app.py:322-351` (Q88) | Mọi path chứa `/api/` trả JSON `{detail, correlation_id}` + `Cache-Control: no-store`, đã bỏ `input`/`ctx`. |

## 3. Cái CHƯA có (khoảng trống Public API phải lấp)

1. **Developer API key domain** — không có bảng/model nào cho customer key (Prompt 03).
2. **Principal không phải cookie** — mọi đường auth hiện tại đều đi qua
   `request.session`; chưa có principal dạng bearer token (Prompt 04).
3. **Public Tool Catalog** — chưa có allowlist; `ToolSpec` hiện phục vụ Agent
   (Prompt 05).
4. **Quote nền tảng** — quote ký/idempotent mới chỉ có trong `apps/taovideo`;
   `apps/autosubvideo`, `apps/upscalevideo`, `apps/prompt_ai_ommi` mỗi nơi một
   kiểu (Prompt 06).
5. **Idempotency-Key DB-backed** — hiện chỉ có `dedupe_key` (chỉ dedupe job
   **chưa terminal**) và `intent` của taovideo. Chưa có bảng idempotency chung
   (Prompt 06).
6. **Artifact contract** — mỗi app tự serve output theo route riêng; không có
   `/api/v1/artifacts` owner-scoped chung (Prompt 07).
7. **Rate/quota/concurrency theo principal** — `server/usage_rate_limit.py`
   in-memory, khóa theo `sid`/`user` hoặc IP, chỉ áp cho POST (Prompt 08).
8. **Webhook/outbox** — không tồn tại (Prompt 09).
9. **Usage/metering API** — có `job_events` + ledger nhưng chưa có bề mặt đọc
   (Prompt 10).

## 4. Ranh giới đặt code (quan trọng — có luật repo chặn)

`AGENTS.md` mục 2.3: *thêm app = thêm folder trong `apps/`; không sửa
`platform_core/` hay `server/`; nếu buộc phải sửa thì DỪNG và nói rõ vì sao.*

**Public API không phải một app.** Nó là năng lực nền tảng: một app không thể
tự cấp phát credential toàn hệ thống, không thể mount `/api/v1` ngoài
`route_prefix` của mình, và không được biết tên app khác. Vì vậy V1 đặt:

```
platform_core/public_api/      domain: developer key, scope, catalog policy,
                               idempotency, usage — KHÔNG biết tên app nào (8.4)
server/api/                    bề mặt HTTP: router /api/v1, auth dependency,
                               problem+json handler, OpenAPI
server/app.py                  đúng MỘT thay đổi: include_router(api_v1)
```

Hệ quả bắt buộc, phải làm ở Prompt 02 trước khi viết code kernel:

- Thêm **một dòng quyết định mới (Q92)** vào `docs/QUYET_DINH_NEN_TANG.md` theo
  giao thức `AGENTS.md` mục 6: Public API là adapter layer của nền tảng, không
  phải app; billing principal V1 = `User`. Không sửa đè dòng cũ.
- `platform_core/public_api/` phải tuân `AGENTS.md` 8.4: **không hardcode slug
  app nào**, kể cả trong comment (`test_no_app_slug_is_hardcoded_in_the_platform`
  đang chốt).

## 5. Bảy điểm va chạm đã đo được với hạ tầng hiện tại

Đây là các chỗ Public API **sẽ** đụng nếu làm ngây thơ. Ghi ra để prompt sau
không phải phát hiện lại.

1. **Error handler nuốt `/api/v1`.** `server/app.py:335` bắt mọi path chứa
   `/api/` và trả `{"detail": …}`. Kernel muốn RFC 9457 `application/problem+json`
   thì phải đăng ký handler riêng cho `/api/v1` và **giữ nguyên** hành vi Q88
   cho `/<slug>/api/*` (đang có test `tests/test_176_api_error_contract.py`).
2. **AccessControlMiddleware không phủ `/api/v1`.** `app_cho_path()` khớp theo
   `route_prefix` của app; `/api/v1/...` không thuộc app nào → **không** có phân
   quyền app tự động. Kernel phải tự gọi `app_access.muc_quyen()` và **fail
   closed** (ngược mặc định-mở của Q25, vì Q25 nói về UI của khách đã đăng nhập).
3. **UsageRateLimitMiddleware khóa sai principal.** Nó đọc `request.session`;
   client API không có session → rơi về `ip:`, mà sau Cloudflare Tunnel mọi IP
   peer đều là loopback (xem `server/auth/session.py:126-142`). Nếu không sửa,
   một client làm nghẽn tất cả. Rate-limit của Public API phải khóa theo
   `key_id`/`user_id`, đọc IP qua `CF-Connecting-IP` (Prompt 08).
4. **Cookie session tuyệt đối không được là đường auth của `/api/v1`.**
   `SessionMiddleware` vẫn chạy cho mọi request; nếu kernel chấp nhận cookie thì
   sinh confused-deputy + CSRF trên bề mặt không có CSRF token. Chỉ nhận
   `Authorization: Bearer`.
5. **`dedupe_key` không phải idempotency key.** `jobs.submit()` chỉ trả job cũ
   khi job còn `queued/running`. Retry sau khi job đã `done` sẽ tạo job mới và
   **hold lần hai**. Public API bắt buộc dùng bảng idempotency riêng có unique
   constraint (Prompt 06).
6. **Cloudflare 100 s / 100 MB.** Mọi endpoint chargeable phải async-job; upload
   đi `upload_sessions` + presigned PUT (R2 browser-upload còn tắt theo Q48 —
   nhưng client API **không chịu CORS**, nên presigned PUT dùng được như Watch
   Agent).
7. **Chat không có Job.** `apps/chataistudio/routes.py` giữ/quyết toán credit
   với `job_id` là **id tin nhắn**, không có dòng `jobs`. Bất cứ ý định public
   hóa chat đều phải migrate sang hợp đồng job trước (xem APP_DISPOSITION).

## 6. Bất biến Public API kế thừa

- Job trả phí: validate → quote → hold → queue → worker → settle/refund.
- Không job miễn phí ngoài ý muốn: `registry.credit_for()` raise nếu app không
  khai giá — Public API không được bắt lỗi này rồi chạy tiếp.
- Thu ≤ hold (Q84); variance là chi phí nền tảng, ghi warning để đối soát.
- Secret không vào log/response: Authorization header, developer key thô,
  provider credential, presigned URL đầy đủ, đường dẫn local.
- Public name không lộ provider/worker/storage path.
