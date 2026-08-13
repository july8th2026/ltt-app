# Public API V1 — Quyết định khóa ở Prompt 01

Mỗi quyết định ghi: **chốt gì**, **vì sao**, **bằng chứng trong code**, **hệ quả**.
Đây là quyết định phạm vi Public API; nguồn chân lý toàn nền tảng vẫn là
`docs/QUYET_DINH_NEN_TANG.md`.

---

## PA-1. Đường dẫn chuẩn là `/api/v1`, host là chuyện deploy

**Chốt:** mọi endpoint công khai nằm dưới `/api/v1/...`. `api.lttstudios.com`
(nếu có) chỉ là proxy/route ở Cloudflare; code **không** phụ thuộc host.

**Vì sao:** Q30 đã chốt path-based một host; thêm phụ thuộc host vào code sẽ
khoá nền tảng vào một cấu hình DNS và làm test/loopback lệch production.

**Hệ quả:** không có middleware nào được phân nhánh theo `Host`.

---

## PA-2. Public API là adapter layer của nền tảng, KHÔNG phải một app

**Chốt:** code ở `platform_core/public_api/` (domain) + `server/api/` (HTTP).
`server/app.py` thay đổi đúng một dòng để mount router.

**Vì sao:** một app trong `apps/` không được biết app khác (`AGENTS.md` 8.4),
không mount được path ngoài `route_prefix`, và không được cấp phát credential
toàn hệ thống. Ép Public API thành app là đi vòng qua hợp đồng, đúng thứ
`AGENTS.md` mục 2.3 cấm.

**Hệ quả bắt buộc:** trước khi viết kernel (Prompt 02) phải thêm dòng **Q92**
vào `docs/QUYET_DINH_NEN_TANG.md` theo giao thức đổi/thêm quyết định
(`AGENTS.md` mục 6). Không sửa đè dòng cũ.

---

## PA-3. Billing principal V1 = `User` hiện hữu. Không phát minh Organization

**Chốt:** developer key thuộc về một `users.id`; credit vẫn là ledger hiện tại
(`credit_entries.user_id`, FK RESTRICT tới `users`). Không có tenant/org table.

**Vì sao:** codebase chỉ có `User` (`platform_core/models.py:62`), toàn bộ
ownership (`jobs.user_id`, `app_projects.user_id`, `upload_sessions.user_id`)
đều bám user. Dựng org billing bây giờ là tạo hai nguồn chân lý về tiền.

**Hệ quả:** organization/team billing là ADR tương lai, không làm ở pack này.
Mọi truy vấn owner-scope trong Public API dùng `user_id` của key.

---

## PA-4. Developer API key là domain MỚI, không đụng `platform_core.ApiKey`

**Chốt:** bảng mới (Prompt 03). `api_keys` hiện tại là **provider credential**
của LTT (Fernet, `lay_credential()` giải mã được) và tuyệt đối không dùng cho
xác thực khách.

**Vì sao:** hai loại credential ngược hướng nhau: provider credential phải giải
mã được; customer credential phải **không** giải mã được. Trộn chúng là biến
một lỗ đọc DB thành lộ cả khoá của khách lẫn khoá provider.

**Thiết kế khóa ở đây (chi tiết ở Prompt 03):** token opaque entropy cao, dạng
`prefix/key-id` công khai để lookup O(1) + verifier one-way nhanh
(HMAC-SHA256 có pepper ngoài DB, so sánh constant-time). **Không** dùng KDF đắt
(bcrypt/argon2) trên mọi request — đó là cửa DoS ở đường nóng; threat model +
benchmark phải ghi vào Prompt 03.

**Plaintext chỉ hiện đúng một lần lúc tạo.**

---

## PA-5. Auth chỉ qua `Authorization: Bearer`, cookie bị bỏ qua

**Chốt:** `/api/v1` không đọc `request.session`, không nhận cookie làm danh
tính, và không dùng CSRF token.

**Vì sao:** `SessionMiddleware` chạy cho mọi request; nếu kernel chấp nhận
cookie thì trình duyệt của một user đã đăng nhập có thể bị site khác ép gọi API
tính tiền (confused deputy) trên bề mặt không có CSRF.

---

## PA-6. Fail-closed exposure — `customer_visible` KHÔNG phải cờ public

**Chốt:** một tool chỉ ra `/api/v1` khi có **allowlist tường minh** của Public
Tool Catalog. Manifest `public=True`, `customer_visible=True`, `enabled=True`
đều không đủ.

**Vì sao (bằng chứng):** `apps/kichban` có `lifecycle="retired"`,
`surface="runtime"` nhưng vẫn khai ToolSpec `text.generate` với
`customer_visible=True`; `apps/mediatools` là `internal/runtime` nhưng có 9
ToolSpec `customer_visible=True`, trong đó `video.social_import` nhận **URL do
người gọi cung cấp** (SSRF trực tiếp). Suy diễn "customer_visible → public" sẽ
mở đúng những thứ không được mở.

**Hệ quả:** app `lifecycle` ∈ {retired, internal, maintenance} hoặc
`surface` ∈ {admin, runtime} mặc định **không bao giờ** public, trừ khi có ADR
riêng ghi rõ.

---

## PA-7. Không tạo engine song song

**Chốt:** Public API dùng đúng `platform_core.job_submit.submit_with_credit()`,
`platform_core.jobs`, `platform_core.credit`, `platform_core.upload_sessions`,
`platform_core.storage`, `platform_core.api_pool`. Không có "đường test", không
có "route miễn phí" đi vòng cổng tính tiền.

**Vì sao:** Q26/Q5/Q85 và các bất biến ở mục 2 của quyết định nền tảng. Một
hàng đợi hay sổ tiền thứ hai là hỏng dữ liệu không sửa được bằng test.

---

## PA-8. Idempotency là bảng riêng, không tái dụng `dedupe_key`

**Chốt:** mọi request chargeable nhận header `Idempotency-Key`; lưu DB có
unique constraint `(principal, endpoint, key)` + hash canonical request.
Cùng key + cùng request → cùng kết quả logic; cùng key + payload khác → 409.

**Vì sao (bằng chứng):** `platform_core/jobs.py:71-80` chỉ dedupe khi job cũ còn
`queued/running`. Sau khi job `done`, gửi lại **tạo job mới và hold lần hai** —
đúng kịch bản retry mạng của client API. `apps/taovideo/quotes.py` đã giải bài
này bằng `intent` + dedupe key per-variant nhưng chỉ trong một app; nền tảng
cần bản dùng chung.

---

## PA-9. Quote ký, có hạn, khóa cấu hình ảnh hưởng giá

**Chốt:** quote là token ký (mẫu đã chạy: `apps/taovideo/quotes.py`), khóa
`user_id` + cấu hình + số lượng + `unit_hold`, TTL ngắn, mang `intent` dùng làm
idempotency của cả batch. Validate + scope check **trước** hold; hold thành
công **trước** khi vào hàng đợi.

**Vì sao:** Q84 (canary Seedance giữ 29 thu 78) và bất biến "job không tra được
giá thì bị từ chối chạy".

---

## PA-10. Hợp đồng lỗi: RFC 9457 cho `/api/v1`, giữ nguyên Q88 cho app API

**Chốt:** `/api/v1` trả `application/problem+json` với `type/title/status/
detail/instance` + `code` ổn định + `correlation_id`, `Cache-Control: no-store`.
Handler của Q88 (`server/app.py:322-351`) giữ nguyên cho `/health` và
`/<slug>/api/*`.

**Vì sao:** Q88 đang có test chốt (`tests/test_176_api_error_contract.py`); đổi
nó là phá hợp đồng frontend hiện có. Bề mặt mới thì được chọn chuẩn mới.

**Hệ quả:** handler mới phải đăng ký sao cho `/api/v1` không rơi vào nhánh
`"/api/" in path` của handler cũ.

---

## PA-11. Rate/quota theo principal, tách hẳn khỏi allocator provider

**Chốt:** giới hạn của khách (rpm, concurrency, quota ngày) là lớp riêng, đo
theo `key_id`/`user_id`. Giới hạn `rpm_limit/tpm_limit` trong bảng `api_keys`
là **của nền tảng với provider**, không được dùng làm giới hạn khách.

**Vì sao:** hai lớp trả lời hai câu hỏi khác nhau; trộn chúng làm khách này
chặn khách kia và làm sai cả hai phép đo.

**Bằng chứng cần sửa:** `server/usage_rate_limit.py` khóa theo `request.session`
rồi fallback `request.client.host` — sau Tunnel mọi peer là loopback, nên
fallback đó là DoS toàn hệ thống nếu áp cho client API.

---

## PA-12. Không thêm hạ tầng mới nếu chưa có bằng chứng

**Chốt:** không Redis/Kafka/service mới ở V1. Rate-limit, idempotency, outbox
webhook đều làm trên PostgreSQL đang có.

**Vì sao:** nền tảng chạy trên một máy Windows, hai dịch vụ NSSM (Q6/Q28); thêm
một dịch vụ nữa là thêm một thứ phải cài, giám sát, backup và làm sập lúc 2 giờ
sáng. Nếu về sau cần thật, viết ADR kèm failure mode + gánh nặng vận hành.

**Ghi rõ giới hạn đã biết:** rate-limit in-memory hiện tại chỉ đúng khi web là
**một tiến trình** (ADR-005). Public API phải chọn: hoặc giữ ràng buộc một tiến
trình và ghi vào tài liệu vận hành, hoặc chuyển bộ đếm xuống PostgreSQL. Quyết
ở Prompt 08 kèm số đo, không đoán ở đây.

---

## PA-13. Versioning và inventory

**Chốt:** mọi route V1 phải nằm trong registry của kernel và có contract test
đếm đủ; không route nào được tạo ngoài registry. Deprecate = đánh dấu trong
inventory + `Sunset` header, không xoá lặng lẽ.

**Vì sao:** COMMON_RULES §3; và bài học Q70 (URL cũ redirect 308 một chu kỳ
trước khi 410).
