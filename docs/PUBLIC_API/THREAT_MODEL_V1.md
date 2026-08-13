# Public API V1 — threat model và runbook vận hành (Prompt 16)

Đối tượng: bề mặt `/api/v1` khi mở ra Internet. Chi tiết cơ chế ở
`SECURITY_MATRIX_V1.md`; file này trả lời **ai tấn công được gì, bằng đường
nào, và cái gì chặn**, cộng với những việc operator phải làm trước khi bật.

---

## 1. Tài sản và kẻ tấn công

| Tài sản | Mất nó nghĩa là gì |
|---|---|
| Credit của khách | Mất tiền thật của khách hàng |
| Credential provider (`api_keys`) | Kẻ khác tiêu quota Gemini/BytePlus của LTT |
| `LTT_API_KEY_PEPPER` | Mọi developer key **ngừng hoạt động** (fail-closed) |
| Khoá ký quote (`LTT_SESSION_SECRET`) | Tự ký báo giá 0 credit → chạy job miễn phí |
| Artifact/upload của khách | Rò dữ liệu khách hàng |
| Năng lực nội bộ (mediatools, retired app) | Lộ thứ không bán, có cái mở đường SSRF |
| GPU/worker/hàng đợi | Một khách chặn mọi khách khác |

| Kẻ tấn công | Có gì trong tay |
|---|---|
| Người lạ trên Internet | Không có khoá; dò endpoint và key id |
| Khách có khoá hợp lệ | Một khoá thật, muốn chạm dữ liệu tài khoản khác hoặc tiêu quá phần mình |
| Khoá bị lộ (log, repo, laptop mất) | Toàn quyền của khoá đó cho tới khi thu hồi |
| Receiver webhook thù địch | Một URL do khách khai, muốn kéo request vào mạng nội bộ |
| Provider bị lỗi/độc | Trả về nội dung lạ, giá cao bất thường, treo lâu |

---

## 2. Đường tấn công và cái đang chặn

| # | Đường | Chặn bởi | Test |
|---|---|---|---|
| T1 | Dò key id bằng cách so sánh phản hồi | Một 401 duy nhất cho mọi thất bại; luôn tính HMAC kể cả khi token sai định dạng | `test_192::test_auth_enumeration_gives_nothing_away` |
| T2 | Vét cạn khoá | Throttle theo IP **và** theo key_id (20 lỗi/300 s) | `test_184` |
| T3 | Đọc job/artifact/upload/webhook của người khác | Owner nằm trong `WHERE`; sai chủ → **404 giống hệt** không tồn tại | `test_192::test_bola_…` |
| T4 | Gọi endpoint ngoài quyền của khoá | Scope kiểm ở biên, **trước** mọi thao tác tiền | `test_192::test_bfla_…` |
| T5 | Nhét field lạ để đổi chủ/giá | `additionalProperties: false` thực thi ở submit | `test_192::test_mass_assignment_…` |
| T6 | Chạy job không qua báo giá, hoặc tính tiền hai lần | Quote ký + `Idempotency-Key` bắt buộc + UNIQUE trong CSDL | `test_192::test_charge_bypass_…`, `test_182` |
| T7 | Tự ký quote | Chữ ký `itsdangerous` bằng `LTT_SESSION_SECRET`, khoá theo user + tool + fingerprint input + TTL 15 phút | `test_182` |
| T8 | Làm nghẽn hệ thống | 5 lớp giới hạn (auth-fail, RPM, create-RPM, job đồng thời, trần credit ngày) + trần body 256 KiB + trần trang 100 | `test_184`, `test_192::test_resource_consumption_…` |
| T9 | Dùng webhook để chọc vào mạng nội bộ | Chỉ `https`, kiểm **mọi** IP phân giải, chặn loopback/private/link-local/metadata, kiểm lại sau mỗi redirect, không đính credential nào | `test_185`, `test_192::test_ssrf_…` |
| T10 | Kéo dữ liệu nội bộ qua kết quả job | `outputs`/`result` lọc theo **output schema đã publish** | `test_192::test_unsafe_upstream_…` |
| T11 | Đọc log để lấy khoá | Không log Authorization/token/secret; chỉ `key_id` công khai | `test_192::test_the_access_log_never_carries_a_credential` |
| T12 | Giả IP để né rate-limit | `CF-Connecting-IP` chỉ tin từ peer tin cậy; **không đọc** `X-Forwarded-For` | `test_192::test_a_forged_forwarding_header_…` |
| T13 | Trang web bất kỳ gọi API bằng cookie của khách | API **từ chối cookie**; CORS mặc định tắt, chỉ allowlist tường minh, không `allow_credentials` | `test_180`, `test_192::test_no_cors_headers_…` |
| T14 | Mở nhầm năng lực nội bộ | 3 cổng fail-closed + bảng disposition máy kiểm | `test_190` |

## 3. Rủi ro **chưa** đóng (nói thẳng)

| Rủi ro | Trạng thái | Vì sao chấp nhận được lúc này |
|---|---|---|
| Giới hạn nhịp là **per-process** | Mở | Nền tảng chạy một tiến trình web (ADR-005). Chạy nhiều instance thì lớp 1–3 nhân lên theo số instance; lớp 4–5 vẫn đúng. Phải viết ADR trước khi scale ngang. |
| **Không có sandbox** | Mở | Mọi lời gọi tiêu credit thật. Tài liệu nói thẳng; giảm rủi ro bằng trần credit ngày. |
| Trần credit ngày mặc định **tắt** | Mở | Là quyết định sản phẩm (số bao nhiêu), không phải mặc định kỹ thuật. **Nên đặt trước khi mở cho khách ngoài.** |
| SDK TypeScript chưa có toolchain kiểm | Mở | Repo chưa có TS toolchain ngoài ba app Vite; hợp đồng được kiểm ở mức văn bản. |
| Quét lỗ hổng phụ thuộc | Mở | Không có `pip-audit` cài sẵn và không có chính sách lấy advisory. `pip list --outdated` cho thấy nhiều gói có bản mới — nâng cấp là việc riêng, Q17 buộc pin cận trên. |
| Diễn tập khôi phục trên **PostgreSQL** | Mở | Cụm PostgreSQL trên máy này phục vụ production; không tự tạo DB. Diễn tập tương đương đã chạy trên SQLite (dữ liệu + ràng buộc + từ chối trùng sau restore). Lệnh cho operator: `python tools/restore_drill_schema.py --pg-bin "…"`. |

---

## 4. Runbook — trước khi bật `/api/v1` lần đầu

1. **Sinh và cất `LTT_API_KEY_PEPPER`** (≥32 ký tự ngẫu nhiên) vào
   `secrets\app.env`. **Thêm nó vào bản sao lưu Q28** — mất pepper là mọi khóa
   khách chết, và không có đường khôi phục nào khác ngoài phát lại khóa.
2. **Đặt trần credit ngày**: `LTT_PUBLIC_API_DAILY_CREDIT=<số>`. Đây là bán
   kính thiệt hại khi một khóa bị lộ.
3. Cân nhắc `LTT_PUBLIC_API_CLASS_CONCURRENCY=gpu:1` (hoặc 2) để một khách
   không chiếm hết GPU.
4. Chạy migration: `alembic upgrade head` (head hiện tại `c9d0e1f2a3b4`).
5. Bật: `LTT_PUBLIC_API=1`, rồi liệt kê tool muốn mở trong
   `LTT_PUBLIC_API_TOOLS` (mặc định **rỗng = không tool nào**).
6. Khởi động lại dịch vụ web **và** worker (cấu hình đọc một lần lúc khởi động;
   worker là nơi giao webhook và in metrics).
7. Kiểm bằng một khóa thật: `/api/v1/me` → `/tools` → `/quotes` → `/jobs`.

## 5. Runbook — khi có sự cố

| Triệu chứng | Hành động đầu tiên |
|---|---|
| Nghi ngờ lộ khóa của một khách | Thu hồi khóa đó ở `/developers` (hoặc `devkeys.revoke`). Có hiệu lực ở **request kế tiếp**. |
| Bị lạm dụng diện rộng / hoá đơn provider tăng vọt | `LTT_PUBLIC_API_READ_ONLY=1` + khởi động lại web. Đọc vẫn chạy, **mọi job mới bị từ chối**; job đang chạy và settlement không bị ảnh hưởng. |
| Cần tắt hẳn | Bỏ `LTT_PUBLIC_API` → router không được mount; UI, worker, job cũ không đổi. |
| Một tool có vấn đề | Bỏ tên tool khỏi `LTT_PUBLIC_API_TOOLS` — không cần đụng code. |
| Rò rỉ pepper | Thêm `LTT_API_KEY_PEPPER_V<n>` = pepper cũ, đặt pepper mới + tăng `LTT_API_KEY_PEPPER_VERSION`, rồi `rotate()` từng khóa. Khóa cũ vẫn chạy trong lúc xoay. |
| Webhook của một khách chết | Không cần làm gì: giao thất bại sẽ backoff rồi vào trạng thái `dead` sau 6 lần; job và tiền không bị ảnh hưởng. |

## 6. Cái operator đọc được

- **Log truy cập** (`ltt.public_api.access`, một dòng/request):
  `request_id, method, route, status, latency_ms, key_id, owner, tool, job_id,
  credit_delta, ip`. Không có token, không có body, không có văn bản provider.
- **Log từ chối xác thực** (`ltt.public_api.auth`): mã lý do + `key_id` công khai.
- **Counters** (`platform_core.public_api.metrics`): auth success/failure, 4xx,
  5xx, rate-limited, idempotency replay/conflict, job tạo/huỷ, credit
  held/settled/refunded, webhook delivered/failed, latency request. Worker in
  ra mỗi 5 phút.

Không thêm Prometheus/Grafana: nền tảng là một tiến trình web + một worker, và
một dịch vụ giám sát nữa là thêm một thứ phải cài, sao lưu và mất lúc 2 giờ
sáng — cùng lý do đã giữ Redis ở ngoài.
