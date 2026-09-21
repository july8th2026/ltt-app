# Public API V1 — chuẩn giao thức (EXT-02)

Ai đọc file này: người viết client, người thêm tool mới, người sẽ xây playground
và SDK. Đây là **hợp đồng chung**; hợp đồng của từng tool ở
`DEVELOPER_GUIDE.md`.

Nguồn chân lý là code: `platform_core/public_api/protocol.py` (chế độ chạy +
quy ước) và `platform_core/public_api/error_registry.py` (bảng lỗi). Bảng lỗi
trong file này **sinh tự động** từ registry và bị `--check` chặn khi lệch.

---

## 1. Chế độ chạy (execution mode)

V2 xuất xưởng 5 tool và cả 5 đều là job bất đồng bộ, nên "một operation chạy
kiểu gì" chưa bao giờ phải viết ra — nó chỉ đơn giản là *điều mà một hiện thực
đang làm*. Đúng lúc có capability thứ sáu rẻ và đồng bộ, hoặc streaming, hoặc
theo lô, câu trả lời sẽ được **bịa ra tại route**, rồi docs, SDK, playground và
client mỗi bên học một câu trả lời khác nhau.

Nên mode được **khai báo**, và khai báo bị kiểm.

| Mode | Dùng khi | Lời hứa bắt buộc |
|---|---|---|
| `ASYNC_JOB` | mặc định: tốn tiền, chạy lâu, đụng provider/GPU/FFmpeg | quote đã ký + `Idempotency-Key`; giữ credit và ghi job trong **một** transaction; trả 201 kèm `Location`; trạng thái kết thúc `succeeded`/`failed`/`cancelled`; kết sổ **đúng một lần** |
| `SYNC` | đọc, và chỉ đọc | miễn phí; không đẩy hàng đợi; không gọi provider/GPU; xong trong **5 giây**; phản hồi ≤ **1 MiB** |
| `STREAM` | kết quả tăng dần (chat) | đã đặc tả đầy đủ, **chưa operation nào dùng** — xem §1.1 |
| `BATCH` | một lời gọi mang nhiều lời gọi con | đã đặc tả đầy đủ, **chưa operation nào dùng** — xem §1.1 |
| `NOT_PUBLIC` | năng lực nội bộ | không có đường nào ra `/api/v1` |

Hôm nay: **23 route `SYNC`, 1 route `ASYNC_JOB`** (`POST /jobs` — route duy nhất
tiêu tiền), và **5 tool đều `ASYNC_JOB`**.

Manifest khai mode qua `api_contract["execution_mode"]`. Vắng mặt = `ASYNC_JOB`,
vì mọi tool đang có đều chạy trên worker và tính tiền. `platform_core/registry.py`
**từ chối nạp** app khai một mode mà nền tảng chưa thi hành — không có đường
khai trước rồi tính sau.

### 1.1 Vì sao STREAM và BATCH được đặc tả nhưng chưa dùng

Đặc tả trước, thi hành sau, là có chủ ý. Khi capability đầu tiên cần đến chúng
xuất hiện, luật đã có sẵn để nó tuân theo — thay vì luật được viết bởi chính
hiện thực đầu tiên, vốn là cách một quirk trở thành hợp đồng.

`STREAM` cần trước khi có operation đầu tiên: danh sách loại sự kiện, heartbeat,
huỷ khi mất kết nối, **một sự kiện usage cuối cùng mang số credit thật sự bị
tính**, và resume không được tính tiền hai lần. `BATCH` cần: id cha/con, kiểm
từng phần tử **trước khi** động tới tiền, một quote cho cả lô, báo thành công
từng phần, huỷ phần còn lại, và một `Idempotency-Key` cho lô.

Quyết định D5 (`EXTENSION_DECISIONS.md`) giải thích vì sao chat **không** phải
operation STREAM đầu tiên.

## 2. Quy ước chung

| Chủ đề | Quy ước |
|---|---|
| Content type | request `application/json`; phản hồi `application/json`; lỗi `application/problem+json` |
| Thời gian | ISO 8601, **luôn UTC**, luôn có offset tường minh (`…Z`) |
| Định danh | chuỗi mờ, không tuần tự. Job/upload/webhook là UUID4; artifact là `<job_id>.<field>.<index>`; **không có tiền tố kiểu `job_`** — thêm bây giờ nghĩa là phải dịch hai chiều mãi mãi, đổi lấy một lợi ích thẩm mỹ |
| Phân trang | `limit`/`offset`, `limit ≤ 100`, `offset ≤ 100.000`, có cờ `has_more` và `next_offset` |
| Sắp xếp | mới nhất trước; chưa cho client chọn thứ tự cho tới khi có listing thật sự cần |
| Lọc | chỉ khớp chính xác (`status`, `tool`, `key_id`) |
| Phiên bản | `X-LTT-API-Version: v1` trên **mọi** phản hồi; thay đổi phá vỡ đi đường version mới, **không** sửa v1 tại chỗ |
| Truy vết | `X-Correlation-ID` trên **mọi** phản hồi và trong **mọi** problem document |
| Ngừng hỗ trợ | `Deprecation` + `Sunset` (RFC 8594) khi một operation đã có lịch gỡ; hiện chưa cái nào |

### 2.1 `Idempotency-Key`

Bắt buộc trên **mọi mutation tốn tiền** (hôm nay: `POST /jobs`).

- cùng key + **cùng** body → phát lại đúng câu trả lời đầu tiên, kèm
  `Idempotency-Replayed: true`, **không** tạo job thứ hai;
- cùng key + **khác** body → `idempotency_conflict` (409), không bao giờ nên
  thử lại;
- cùng key trong khi lần đầu **còn đang chạy** → `idempotency_in_progress`
  (409), thử lại sau vài giây sẽ nhận được kết quả.

Ba tình huống này trước EXT-02 dùng chung một mã `conflict`.

### 2.2 `mode` — live hay test (EXT-12)

Mỗi khoá thuộc **đúng một** môi trường và tiền tố token nói ra điều đó:
`ltt_sk` = live, `ltt_tk` = test. Mọi job và mọi payload webhook mang trường
`mode` tương ứng.

- Khoá test đi qua **cùng** một chuỗi: xác thực, scope, catalog, kiểm tham số,
  báo giá đã ký, `Idempotency-Key`, hàng đợi job, artifact, webhook + chữ ký.
  Đúng **một** mắt xích bị thay — handler trả kết quả mẫu dựng theo
  `output_schema` đã công bố, không gọi provider.
- Khoá test **không chạm sổ credit**. Báo giá vẫn nói giá live; `credit.held` và
  `credit.charged` của job test luôn bằng 0. Vì thế trần chi tiêu (ngày, ngân
  sách EXT-11) **không** áp lên test — chúng đo một việc không thể xảy ra — còn
  giới hạn nhịp và số job song song **vẫn** áp.
- **Cách ly cứng**: khoá test chỉ thấy job test, khoá live chỉ thấy job live.
  Hỏi chéo trả `404` y hệt tài nguyên của tài khoản khác — không tạo oracle.
  Job không có `mode` (tạo từ giao diện web, hoặc có trước EXT-12) là **live**.

## 3. Vòng đời một job

```
POST /quotes                      → giá + token đã ký (sống 15 phút)
POST /jobs  (quote + Idempotency-Key)
        201 + Location: /api/v1/jobs/{id}       → status queued
GET  /jobs/{id}                   → queued → running → succeeded|failed|cancelled
POST /jobs/{id}/cancel            → chỉ khi chưa kết thúc
GET  /artifacts/{id}              → URL tải, ngắn hạn
```

Trạng thái kết thúc là **ba**: `succeeded`, `failed`, `cancelled`. Chuyển sang
trạng thái kết thúc là một chiều, và tiền được kết sổ **đúng một lần** tại đó.

**Job hỏng.** Trường `error` hiện chỉ mang một thông điệp chung và **chưa phân
loại** nguyên nhân. Nói thẳng vì sao chưa: phân loại đúng đòi hỏi worker **gắn
nhãn** lúc hỏng; đoán bằng cách dò chuỗi lỗi nội bộ sẽ có lúc nói sai, và một
nhãn "thử lại được" sai chỗ khiến khách chạy lại một job chắc chắn hỏng — mất
tiền thật. Trong lúc chờ: job hỏng **đã được hoàn tiền**, nên bạn không mất gì;
hãy kiểm input trước khi gửi lại. Việc gắn nhãn thuộc EXT-16.

## 4. Bảng lỗi

Mỗi mã trả lời đúng một câu hỏi: **thử lại có ích không, và với điều kiện gì.**

<!-- BEGIN GENERATED ERRORS -->

| Code | HTTP | Retry | Reuse Idempotency-Key | What to do |
|---|---|---|---|---|
| `context_window_exceeded` | 400 | `after_fix` | no | reduce_input |
| `image_count_exceeded` | 400 | `after_fix` | no | offload_images |
| `image_decode_failed` | 400 | `after_fix` | no | replace_image |
| `image_too_large` | 400 | `after_fix` | no | offload_images |
| `image_url_not_allowed` | 400 | `after_fix` | no | replace_image |
| `input_tokens_exceeded` | 400 | `after_fix` | no | reduce_input |
| `invalid_request` | 400 | `never` | no | Read `detail`; it names the field. Fix the request. |
| `max_output_tokens_exceeded` | 400 | `after_fix` | no | reduce_output |
| `model_not_found` | 400 | `after_fix` | no | That `model` is not served here. Call GET /api/v1/models for the names in service and send one of those. |
| `quote_expired` | 400 | `after_fix` | no | Quotes live 15 minutes. Request a new quote and submit that. |
| `quote_invalid` | 400 | `never` | no | The quote does not belong to this account/tool/input. Request one for the exact call you are making. |
| `unsupported_modality` | 400 | `after_fix` | no | choose_model |
| `unsupported_parameter` | 400 | `after_fix` | no | none |
| `unauthorized` | 401 | `never` | no | The key is missing, malformed, unknown, revoked or expired — the API will not say which. Check the key in the developer portal. |
| `forbidden` | 403 | `never` | no | This key may not perform this action. |
| `missing_scope` | 403 | `after_fix` | no | The key lacks a scope this endpoint needs. `required_scope` names it; issue a key that has it. |
| `tool_not_allowed` | 403 | `after_fix` | no | This key is restricted to a tool allowlist that excludes this tool, or the deployment does not publish it. |
| `not_found` | 404 | `never` | no | No such resource, or it belongs to another account — the two are indistinguishable by design. |
| `method_not_allowed` | 405 | `never` | no | Wrong HTTP method for this path. |
| `conflict` | 409 | `never` | no | The resource is not in a state that allows this. |
| `idempotency_conflict` | 409 | `never` | no | This Idempotency-Key was already used with a different body. Use a new key for a new call — never reuse one across different inputs. |
| `idempotency_in_progress` | 409 | `after_delay` | yes | Your first attempt is still running. Retry the identical request with the same key in a moment and you will get its answer. |
| `insufficient_credit` | 409 | `after_fix` | yes | Top up credit, then submit again with the same Idempotency-Key. |
| `price_changed` | 409 | `after_fix` | yes | The price moved between quote and submit. Request a new quote; the old one is refused rather than silently repriced. |
| `payload_too_large` | 413 | `never` | no | Send large media through the upload endpoints, not in the JSON body. |
| `request_body_too_large` | 413 | `after_fix` | no | none |
| `unprocessable_request` | 422 | `never` | no | The body parsed but failed validation. Read `detail`. |
| `concurrency_limited` | 429 | `after_delay` | yes | Too many of your jobs are running. Wait for one to finish; polling harder will not start it sooner. |
| `quota_exceeded` | 429 | `after_delay` | yes | The account's daily credit ceiling is reached. It rolls forward continuously, so retry later or raise the ceiling. |
| `rate_limited` | 429 | `after_delay` | yes | Wait for `Retry-After` seconds, then retry with the same Idempotency-Key if the call was chargeable. |
| `request_cancelled` | 499 | `never` | no | none |
| `internal_error` | 500 | `after_delay` | yes | Retry with backoff and the same Idempotency-Key. Quote the X-Correlation-ID if it persists. |
| `empty_response` | 502 | `ambiguous` | no | report_request_id |
| `malformed_upstream_response` | 502 | `ambiguous` | no | report_request_id |
| `stream_truncated` | 502 | `ambiguous` | no | report_request_id |
| `structured_output_failed` | 502 | `ambiguous` | no | none |
| `tool_call_parse_failed` | 502 | `ambiguous` | no | none |
| `upstream_protocol_error` | 502 | `ambiguous` | no | report_request_id |
| `upstream_unknown` | 502 | `ambiguous` | no | report_request_id |
| `upstream_unreachable` | 502 | `after_delay` | no | retry_same_request |
| `model_loading` | 503 | `after_delay` | no | wait |
| `provider_oom` | 503 | `after_fix` | no | report_request_id |
| `provider_overloaded` | 503 | `after_delay` | no | wait |
| `read_only` | 503 | `after_delay` | yes | The API is accepting reads only. Writes resume without any change on your side. |
| `service_unavailable` | 503 | `after_delay` | yes | Retry with backoff and the same Idempotency-Key. |
| `stream_idle_timeout` | 504 | `ambiguous` | no | report_request_id |
| `upstream_timeout` | 504 | `ambiguous` | no | report_request_id |

### Retry matrix by status

| Response | Retry | Note |
|---|---|---|
| 4xx (except 409/429) | `never` | The request is wrong. Repeating it unchanged is a bug in the client. |
| 409 | `after_fix` | State, not syntax. The code says which state; two of the three are fixable and then retryable with the same Idempotency-Key. |
| 422 | `never` | Validation failed. Fix the body. |
| 429 | `after_delay` | Honour Retry-After. Exponential backoff with jitter after that; do not retry faster than the header says. |
| 5xx | `after_delay` | Retry with backoff, capped attempts. Always reuse the Idempotency-Key. |
| network timeout / connection reset | `after_delay` | The dangerous one: the request may have succeeded. Retry ONLY with the original Idempotency-Key — that turns an unknown outcome into a replay of the first answer instead of a second purchase. |

> A chargeable POST may only be retried when it carries the same Idempotency-Key as the original attempt. Without one, a retry after a timeout is a second job and a second hold; with one, the server replays the first answer and no money moves twice.

<!-- END GENERATED ERRORS -->

### 4.1 Một chỗ cố ý **không** tách

Mọi thất bại về credential — thiếu header, token sai định dạng, key id không
tồn tại, secret sai, khoá bị thu hồi, khoá hết hạn — đều trả **cùng một**
`401 unauthorized`. Tách ra sẽ thân thiện hơn với người gọi thật, và đồng thời
biến endpoint thành **máy tra key id**: kẻ tấn công đoán một triệu key id và học
được cái nào tồn tại. Người gọi thật có portal, nơi nói chính xác khoá của họ
sao lại chết. `tests/test_192` khoá tính chất này.

Đây là điểm EXT-02 **không** làm theo yêu cầu của pack (pack liệt kê
`invalid_api_key`, `key_expired/revoked` như những mã riêng). Ghi lại như
`OBSERVED_DIFFERENCE`: code + test thắng prompt.

## 5. Client nên thử lại thế nào

1. Chỉ thử lại khi bảng trên nói được.
2. **Timeout mạng là ca nguy hiểm nhất**: request *có thể* đã thành công. Chỉ
   thử lại với **đúng `Idempotency-Key` cũ** — làm vậy thì kết quả xấu nhất là
   nhận lại câu trả lời đầu tiên, thay vì mua lần thứ hai.
3. Tôn trọng `Retry-After` khi có (429 và 503 luôn có, ở **cả** header lẫn body).
4. Backoff luỹ thừa kèm jitter, giới hạn số lần.
5. Ghi lại `X-Correlation-ID` của mọi phản hồi hỏng — đó là thứ hỗ trợ cần.
