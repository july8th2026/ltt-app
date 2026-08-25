# Public API kernel V1 — vận hành và hợp đồng (Prompt 02)

Áp dụng cho `/api/v1`. Quyết định nền tảng: **Q92**.

## 1. Bật/tắt

| Biến môi trường | Mặc định | Ý nghĩa |
|---|---|---|
| `LTT_PUBLIC_API` | `0` (**tắt**) | `1` mới mount `/api/v1`. Tắt = router không tồn tại, bề mặt route y hệt trước khi có Public API. |
| `LTT_PUBLIC_API_READ_ONLY` | `0` | `1` = **công tắc khẩn cấp**: đọc vẫn chạy, mọi `POST/PUT/PATCH/DELETE` trả 503 `read_only`. Không đụng UI, không đụng worker, không đụng job đang chạy. |
| `LTT_PUBLIC_API_TOOLS` | rỗng | Allowlist tên tool được phép ra API (`image.thumbnail,video.generate`). Rỗng = **không tool nào**. Prompt 05 chồng thêm catalog policy; đây là công tắc ngoài cùng để operator tắt nhanh một tool. |
| `LTT_PUBLIC_API_MAX_BODY_BYTES` | `262144` (256 KiB) | Trần body cho route control-plane JSON. Kẹp trong [1 KiB, 100 MiB] — trên 100 MB thì Cloudflare đã chặn trước khi tới máy chủ nên hứa cao hơn là nói dối. |
| `LTT_PUBLIC_API_TRUSTED_PROXIES` | `127.0.0.1,::1` | Peer nào được phép nói `CF-Connecting-IP`. Rỗng = không tin header nào, dùng IP socket. |

Đặt trong `secrets/app.env` trên máy chủ. **Không** có biến nào chứa host: đường
dẫn chuẩn là `/api/v1`, còn `api.lttstudios.com` (nếu có) là chuyện proxy.

Bật/tắt chỉ có hiệu lực khi tiến trình web khởi động lại (cấu hình đọc một lần
lúc `create_app`) — cố ý: một cờ đọc lại giữa chừng làm hai request cùng lúc
chạy hai luật khác nhau.

## 2. Đặt code ở đâu

```
platform_core/public_api/
  config.py       cờ + kill switch, đọc từ env
  errors.py       hợp đồng lỗi RFC 9457 + scrub_detail dùng chung với Q88
  pagination.py   PageRequest/Page, trần cứng 100 item
server/api/
  __init__.py     dựng sub-application, mount, liệt kê route
  guard.py        middleware read-only + trần body cho TOÀN bộ bề mặt
  deps.py         Principal placeholder (deny-all), bearer parsing
  errors.py       exception handler của riêng sub-app
  context.py      request id + client IP tin cậy
  inventory.py    danh sách route V1 được khai báo
server/app.py     đúng ba chỗ: mount, một nhánh lỗi, và dùng chung scrub_detail
```

`platform_core/public_api/` không import FastAPI/Starlette và không biết tên app
nào (`AGENTS.md` 8.4) — nhờ vậy luật kiểm được bằng unit test không cần dựng app.

## 3. Vì sao là sub-application chứ không phải router

FastAPI/Starlette bản này **không làm phẳng** `include_router`: mỗi lần include
để lại một `_IncludedRouter` không có `.path` (đã có ghi chú ở
`tests/test_152_socialbot_route_flag.py` và `tests/test_51_oauth_web.py` — cả
hai đã bị xoá cùng app socialbot ngày 2026-08-25; hành vi Starlette không đổi).
Mount một sub-app cho ba thứ miễn phí:

1. **Inventory** — route của bề mặt là một danh sách, không phải một cuộc duyệt cây.
2. **Tách spec** — `/api/v1/openapi.json` chỉ mô tả route công khai và schema của
   chúng; `/openapi.json` của nền tảng vẫn chỉ bật ở development vì nó liệt kê
   mọi route nội bộ.
3. **Tách error boundary** — handler đăng ký trên sub-app không đụng tới hợp đồng
   JSON của Q88 (`/health`, `/<slug>/api/*`) và ngược lại.

## 4. Hợp đồng lỗi

Mọi lỗi `/api/v1` trả `application/problem+json` + `Cache-Control: no-store`:

```json
{
  "type": "/errors/not_found",
  "title": "Not found",
  "status": 404,
  "code": "not_found",
  "detail": "…",
  "instance": "/api/v1/jobs/abc",
  "request_id": "…"
}
```

- `code` là phần **ổn định** của hợp đồng; `title`/`detail` có thể sửa câu chữ.
- `type` là URI **tương đối** (RFC 9457 cho phép) — nhúng host vào payload là
  đúng thứ Q92 cấm.
- `request_id` = `X-Correlation-ID` của cùng request → nối được với log tiến
  trình và `job_events`.
- Lỗi 5xx **luôn** trả một câu cố định. Nội dung exception có thể chứa credential
  provider hoặc dữ liệu khách; traceback là thông tin do thám miễn phí.
- Chi tiết validation đã bỏ `input` và `ctx` (dùng chung `scrub_detail` với Q88).

Mã hiện có: `invalid_request`, `unauthorized`, `forbidden`, `not_found`,
`method_not_allowed`, `conflict`, `payload_too_large`, `unprocessable_request`,
`rate_limited`, `read_only`, `service_unavailable`, `internal_error`.

## 5. Route đang có (Prompt 02)

| Method | Path | Auth | Trong spec |
|---|---|---|---|
| GET | `/api/v1/health` | không | có |
| GET | `/api/v1/capabilities` | không | có |
| GET | `/api/v1/openapi.json` | không | không |

`/health` cố tình **nông**: không chạm CSDL, không chạm worker. Một health công
khai mà đo hạ tầng bên trong là vừa tặng người lạ cách đo sự cố, vừa tặng một bộ
khuếch đại tải. Readiness cho operator đã có ở `/health/ready`.

`/capabilities` chỉ trả `api_version`, `read_only` và danh sách capability (rỗng
cho tới Prompt 05). Không trả tên provider, model, backend storage hay dump cờ.

Thêm route mới **bắt buộc** khai vào `server/api/inventory.py`, nếu không
`tests/test_178_public_api_kernel.py` đỏ theo cả hai chiều (mount mà không khai,
khai mà không mount).

## 6. Danh tính (placeholder ở prompt này)

`server/api/deps.py` khoá sẵn hình dạng ranh giới:

- chỉ đọc `Authorization: Bearer`. **Không bao giờ** đọc cookie/`request.session`
  — bề mặt này không có CSRF token, nên chấp nhận cookie là mở đường cho một
  site khác ép trình duyệt đã đăng nhập tiêu credit của khách;
- chưa có resolver thật → `require_principal()` trả 401 cho mọi request.
  Fail-closed thay vì một stub "tạm cho qua".

Prompt 03/04 gọi `set_principal_resolver()` để cắm bộ xác minh thật.

## 7. IP khách

`server/api/context.py:client_ip()` chỉ tin `CF-Connecting-IP` **khi peer là
proxy tin cậy** (mặc định loopback — `cloudflared` vào origin qua loopback), và
**không bao giờ** đọc `X-Forwarded-For`.

Khác với `server/auth/session.py:client_ip()` đang tin header vô điều kiện. Hợp
lý cho bề mặt trình duyệt (origin chỉ nhận loopback), nhưng không đủ cho bề mặt
máy-gọi-máy: chỉ cần một đường khác chạm được tiến trình là caller tự khai IP,
và mọi rate-limit/antifraud khoá theo IP thành vô nghĩa. Chưa sửa đường cũ —
ngoài phạm vi Prompt 02, ghi lại ở PROGRESS.

## 8. Pagination

`PageRequest.parse(limit, offset)`: mặc định 20, **trần cứng 100**, offset tối đa
100.000. `limit` âm/0/không phải số → 400 `invalid_request`; `limit` quá lớn thì
kẹp (thường là ý "cho tôi tất cả"). Lấy `fetch_limit = limit + 1` rồi
`Page.of(rows, request)` để biết `has_more` mà không cần `COUNT(*)`.
