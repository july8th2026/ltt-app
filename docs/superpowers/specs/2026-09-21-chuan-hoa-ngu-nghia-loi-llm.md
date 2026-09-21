# Đặc tả chuẩn hoá và bảo toàn ngữ nghĩa lỗi LTT LLM

**Ngày:** 21/09/2026  
**Phạm vi:** máy B (`llm_gateway`, llama.cpp/llama-swap) → máy A
(`platform_core`, `/api/v1/*`) → mọi API client, gồm LTTCODE/DeepSeek Harness.  
**Trạng thái:** đặc tả để triển khai; phiên lập đặc tả không sửa code và không
thay đổi dịch vụ production.

## 1. Kết luận kiến trúc

Lỗi hiện tại không nằm ở việc thiếu thêm một câu tiếng Việt. Lỗi nằm ở chỗ hệ
thống đang dùng **HTTP status và câu chữ** để đoán nguyên nhân. Cụ thể, cửa
stream của máy A coi mọi `413` từ B là `qua_dai=True`; trong khi B cũng dùng
`413` cho quá nhiều ảnh, ảnh quá lớn, URL ảnh bị cấm và xin quá nhiều output
token. LTTCODE lại đổi mọi `413`/`payload_too_large` thành
`CONTEXT_WINDOW_EXCEEDED`, làm DeepSeek Harness nén văn bản cho cả lỗi ảnh.

Thiết kế đích có ba lớp, không trộn lẫn:

1. **`canonical_code`**: nguyên nhân chính xác, ổn định do LTT sở hữu, đi xuyên
   suốt B → A → client.
2. **`protocol_code`**: mã tương thích mà OpenAI/Anthropic/DeepSeek Harness cần
   để kích hoạt hành vi chuẩn. Nó không được ghi đè hay làm mất
   `canonical_code`.
3. **`recovery` + `retry`**: chỉ dẫn máy đọc được về hành động và việc có được
   gửi lại cùng yêu cầu hay không. Client không suy ra hành động từ message.

Mục tiêu “đúng 100%” được định nghĩa chặt như sau:

- 100% lỗi **đã đăng ký** phải giữ đúng `canonical_code`, trường, trần, số đo,
  tính retry và hành động phục hồi qua mọi đường đi.
- 100% lỗi **chưa biết** phải thành `upstream_unknown`; tuyệt đối không gán nhầm
  thành context, ảnh, thiếu tiền hay bận.
- Không cam kết đoán 100% nguyên nhân vật lý nếu thượng nguồn chỉ trả HTML rỗng,
  đóng socket hoặc lỗi không có mã. Gọi đúng là “không xác định” mới là bảo toàn
  sự thật.
- Khi đạt trạng thái cuối, không có `message.includes(fragment)`, regex câu chữ hoặc
  `status == 413` nào quyết định nén, offload ảnh, nạp tiền hay retry.

## 2. Nguồn sự thật và điều rút ra

- [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457.html) quy định Problem
  Details có `type`, `status` và extension members; client phải bỏ qua extension
  chưa biết. Đây là nền để công bố mã LTT mà vẫn tương thích client cũ.
- [RFC 9110 §15.5.14](https://www.rfc-editor.org/rfc/rfc9110.html#section-15.5.14)
  định nghĩa `413 Content Too Large` theo kích thước nội dung, không phải cửa sổ
  ngữ cảnh model.
- [Anthropic Errors](https://platform.claude.com/docs/en/api/errors) tách rõ
  `request_too_large` 413, `invalid_request_error` 400, `rate_limit_error` 429,
  `overloaded_error` 529; lỗi còn có thể tới sau HTTP 200 trong SSE.
- [llama.cpp server-common.cpp](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/server-common.cpp)
  có các type riêng như `invalid_request_error`, `unavailable_error`,
  `exceed_context_size_error`; context hiện được trả 400. Vì vậy không được
  đồng nhất lỗi llama.cpp với status 413 của gateway.
- [llama.cpp issue #14566](https://github.com/ggml-org/llama.cpp/issues/14566)
  cho thấy lỗi có thể xuất hiện sau 200 dưới dạng dòng
  `error: {"message":"example"}` không phải
  SSE chuẩn. Bộ giải mã phải làm việc trên event/line xuyên qua mọi ranh giới
  chunk, không tìm chuỗi trong từng chunk mạng.
- [vLLM protocol.py](https://github.com/vllm-project/vllm/blob/main/vllm/entrypoints/openai/engine/protocol.py)
  dùng `message`, `type`, `param`, `code` và cho phép trường mở rộng; đây là mẫu
  tương thích tốt cho OpenAI-compatible API.
- [OpenAI Responses streaming reference](https://platform.openai.com/docs/api-reference/responses-streaming/response/failed)
  định nghĩa terminal event `response.failed` với `error.code` và
  `error.message`; [OpenAI OpenAPI](https://github.com/openai/openai-openapi) là
  nguồn schema máy đọc được. LTT phải kiểm cả shape HTTP và terminal SSE, không
  chỉ exception của một SDK cụ thể.
- [Qwen3.5-9B model card](https://huggingface.co/Qwen/Qwen3.5-9B) và
  [Qwen3-VL](https://github.com/QwenLM/Qwen3-VL) là nguồn về khả năng/cửa sổ
  context và giới hạn xử lý ảnh. Model card **không phải** hợp đồng lỗi; gateway
  LTT phải biến giới hạn model thành mã lỗi ổn định.
- [DeepSeek Harness retry policy](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/llm/llm/src/retry-policy.ts)
  chỉ retry mặc định `EMPTY_RESPONSE`, `RATE_LIMIT`, `SERVER`, `TIMEOUT`,
  `TRANSPORT`; [compaction-basic](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/compaction/compaction-basic/README.md)
  chỉ nên nén khi provider xác nhận `CONTEXT_WINDOW_EXCEEDED`. Vì vậy đổi nhầm
  mã không chỉ sai hiển thị mà còn kích hoạt sai hành vi.
- Bản rà nội bộ `docs/ltt_llm_dual/AUDIT_API_2026-09-14.md` tự chấm hợp đồng lỗi
  sau 14/09 chỉ đạt 80: mới xử lý tốt họ “vượt trần”; các họ bận, huỷ, thiếu
  credit chưa được rà trọn. Commit `eadd31f7` giữ được chi tiết ở cửa đồng bộ,
  nhưng cửa stream vẫn rút mọi 413 thành một boolean.

## 3. Hợp đồng dây B → A phiên bản 1

Máy B tiếp tục giữ HTTP status hiện có trong giai đoạn tương thích. Mọi lỗi do B
chủ động phát phải có `detail` là object sau; các khoá cũ tiếng Việt được giữ
trong một chu kỳ phát hành rồi mới bỏ:

```json
{
  "detail": {
    "schema_version": 1,
    "canonical_code": "image_count_exceeded",
    "category": "invalid_request",
    "message": "Too many images in one request.",
    "field": "images",
    "limit": 4,
    "actual": 6,
    "retry": "after_fix",
    "recovery": "offload_images",
    "request_id": "req_ltt_example_01",
    "legacy": {
      "ly_do": "Qua nhieu anh trong mot yeu cau.",
      "truong": "images",
      "tran": 4,
      "thay": 6
    }
  }
}
```

### Bất biến

- `schema_version`, `canonical_code`, `category`, `message`, `retry`,
  `recovery`, `request_id` luôn có.
- `field`, `limit`, `actual`, `retry_after_s`, `provider_type`,
  `provider_code`, `upstream_status` là tuỳ chọn, nhưng kiểu dữ liệu cố định.
- `message` là câu an toàn do LTT sở hữu. Thân lỗi thô của llama.cpp chỉ vào log
  vận hành đã lọc; không đi ra client vì có thể lộ prompt, đường dẫn, VRAM hoặc
  chi tiết hạ tầng.
- `request_id` do A tạo, B nhận qua `X-LTT-Request-Id`, và cùng giá trị phải có
  trong header, envelope, log A và log B.
- `retry` thuộc `never | after_fix | after_delay | ambiguous`.
- `recovery` thuộc `none | reduce_input | reduce_output | offload_images |
  replace_image | choose_model | wait | reauthenticate | top_up |
  retry_same_request | report_request_id`.
- Không một lớp nào được đổi mã chỉ vì HTTP status giống nhau.

## 4. Danh mục ngữ nghĩa lỗi chuẩn

Status dưới đây là status công bố đề nghị. Trong pha chuyển tiếp, decoder phải
chấp nhận status cũ của B nhưng vẫn lấy nghĩa từ `canonical_code`.

| `canonical_code` | Nhóm | HTTP | retry | recovery | Ý nghĩa duy nhất |
|---|---:|---:|---|---|---|
| `invalid_request` | request | 400 | never | none | Body hợp lệ JSON nhưng yêu cầu nói chung không hợp lệ |
| `unsupported_parameter` | request | 400 | after_fix | none | Tham số có tên nhưng endpoint/model không hỗ trợ |
| `unsupported_modality` | request | 400 | after_fix | choose_model | Model không nhận loại input này, gồm model text nhận ảnh |
| `model_not_found` | model | 404 | after_fix | choose_model | Tên model không được công bố/phục vụ |
| `model_loading` | availability | 503 | after_delay | wait | Model hợp lệ nhưng đang nạp/chưa sẵn sàng |
| `request_body_too_large` | transport | 413 | after_fix | none | Tổng byte HTTP vượt trần; không nói gì về token/context |
| `image_count_exceeded` | image | 400 | after_fix | offload_images | Số ảnh vượt `max_images` |
| `image_too_large` | image | 400 | after_fix | offload_images | Một ảnh vượt `max_image_bytes` |
| `image_url_not_allowed` | image/security | 400 | after_fix | replace_image | URL từ xa bị cấm; cần data URL/upload hợp lệ |
| `image_decode_failed` | image | 400 | after_fix | replace_image | Dữ liệu ảnh/base64/MIME không giải mã được |
| `input_tokens_exceeded` | token | 400 | after_fix | reduce_input | Input vượt trần tiếp nhận của hồ sơ model |
| `max_output_tokens_exceeded` | token | 400 | after_fix | reduce_output | Số token đầu ra xin cấp vượt trần |
| `context_window_exceeded` | token | 400 | after_fix | reduce_input | Input + output dự kiến vượt context vật lý |
| `tool_call_parse_failed` | generation | 502 | ambiguous | none | Parser tool-call của engine không hiểu output model |
| `structured_output_failed` | generation | 502 | ambiguous | none | Output không thoả schema/grammar đã yêu cầu |
| `unauthorized` | auth | 401 | never | reauthenticate | Không xác thực; không phân rã thêm để tránh key oracle |
| `forbidden` | auth | 403 | never | none | Đã xác thực nhưng không có quyền |
| `insufficient_credit` | billing | 409 | after_fix | top_up | Không đủ credit cho lần gọi |
| `quota_exceeded` | billing | 429 | after_fix | wait | Trần sử dụng tài khoản/kỳ đã hết |
| `rate_limited` | capacity | 429 | after_delay | wait | Vượt tốc độ theo tài khoản/API |
| `concurrency_limited` | capacity | 429 | after_delay | wait | Hết suất đồng thời do LTT quản lý |
| `provider_overloaded` | capacity | 503 | after_delay | wait | Engine/GPU tạm không nhận thêm việc |
| `upstream_timeout` | transport | 504 | ambiguous | report_request_id | Hết giờ; kết quả có thể chưa biết, không phạt API key |
| `upstream_unreachable` | transport | 502 | after_delay | retry_same_request | Không kết nối được tới engine |
| `provider_oom` | provider | 503 | after_fix | report_request_id | Engine thiếu VRAM; retry nguyên trạng thường thất bại |
| `request_cancelled` | lifecycle | 499 | never | none | Yêu cầu bị huỷ chủ động |
| `stream_idle_timeout` | stream | 504 | ambiguous | report_request_id | Stream đã mở nhưng không có event quá hạn |
| `stream_truncated` | stream | 502 | ambiguous | report_request_id | Stream kết thúc trước terminal event hợp lệ |
| `malformed_upstream_response` | protocol | 502 | ambiguous | report_request_id | Body/event của engine không giải mã được |
| `empty_response` | protocol | 502 | ambiguous | report_request_id | Thành công HTTP nhưng không có nội dung/terminal event |
| `upstream_protocol_error` | protocol | 502 | ambiguous | report_request_id | Vi phạm trình tự sự kiện của giao thức |
| `internal_error` | internal | 500 | after_delay | report_request_id | Lỗi đã biết thuộc A/B nhưng không an toàn để công bố sâu hơn |
| `upstream_unknown` | unknown | 502 | ambiguous | report_request_id | Không đủ bằng chứng để phân loại; không được tự nén/offload |

`client_disconnected` là mã **chỉ dùng trong log**, không phát về socket đã đóng
và không được tính là lỗi provider/key.

### 4.1. Mức chứng cứ của danh mục — không biến dự đoán thành sự thật

33 mã trên là vocabulary đích, nhưng không được ghi rằng cả 33 đã xuất hiện trên
production:

- **Đang có nhánh phát rõ trong code B:** `unsupported_modality`,
  `image_count_exceeded`, `image_url_not_allowed`, `image_too_large`,
  `max_output_tokens_exceeded`, `input_tokens_exceeded`,
  `context_window_exceeded`, `model_not_found`, `concurrency_limited`,
  `provider_overloaded`, `request_cancelled`, `upstream_timeout`,
  `upstream_unreachable`.
- **Đang có ở A/public API nhưng chưa đi cùng một model envelope:**
  `request_body_too_large`, `unauthorized`, `forbidden`, `insufficient_credit`,
  `quota_exceeded`, `rate_limited`, `internal_error`.
- **Có typed signal từ engine/protocol và phải chuẩn hoá ở adapter B:**
  `invalid_request`, `unsupported_parameter`, `model_loading`,
  `tool_call_parse_failed`, `structured_output_failed`, `provider_oom`.
  Chỉ phát mã khi field/type/code hoặc detector hẹp có bằng chứng; thiếu bằng
  chứng thì dùng `upstream_unknown`.
- **Trạng thái mới cần detector/test tường minh:** `image_decode_failed`,
  `stream_idle_timeout`, `stream_truncated`, `malformed_upstream_response`,
  `empty_response`, `upstream_protocol_error`. Chúng không được phát chỉ vì
  message “trông giống”.

Phép đo production 21/09 tại
`tmp/audit_ltt_llm_live_20260921/report.md` thấy 9 lỗi 413 có detail
`truong=images, tran=4, thay=6`; cùng cửa sổ đó B có 35 lượt Qwen 3.8 trả 200,
không có lỗi model. Đây là bằng chứng cho lỗi **dịch nghĩa ở A/client**, không
phải bằng chứng model B hỏng. Báo cáo tạm không được dùng làm golden test; golden
đến từ registry/spec độc lập.

## 5. Mô hình dữ liệu trên máy A

`platform_core.llm.model_failure.ModelFailure` là đối tượng chuẩn nội bộ:

```python
@dataclass(frozen=True)
class ModelFailure:
    canonical_code: str
    category: str
    message: str
    http_status: int
    retry: str
    recovery: str
    request_id: str
    field: str | None = None
    limit: int | None = None
    actual: int | None = None
    retry_after_s: int | None = None
    provider_type: str | None = None
    provider_code: str | int | None = None
    upstream_status: int | None = None
```

Một hàm duy nhất `decode_gateway_failure(status, headers, body) -> ModelFailure`
được cả cửa đồng bộ và stream dùng. Thứ tự tin cậy:

1. envelope v1 có `canonical_code` đã đăng ký;
2. envelope B cũ có cấu trúc `{truong, tran, thay}` — ánh xạ theo **field chính
   xác**, không theo câu chữ;
3. lỗi llama.cpp đã được lớp adapter B chuẩn hoá theo `type/code`;
4. dữ liệu không đủ → `upstream_unknown`.

Mã lạ từ một schema đã biết cũng thành `upstream_unknown` nhưng giữ mã gốc trong
log. Không tự động coi mã lạ là retryable.

## 6. Tách trách nhiệm B, A và client

### Máy B

- Là nơi biết giới hạn vật lý/model và chi tiết llama.cpp; phát
  `canonical_code`.
- Chuẩn hoá lỗi HTTP trước 200 và lỗi terminal sau 200 của engine.
- Dùng parser SSE/line tăng dần, chịu được JSON/event bị chia ở bất kỳ byte nào.
- Không dựng lại success event. Bộ quan sát chỉ giữ tối đa một event chưa hoàn
  chỉnh; event thành công được phát nguyên byte, event lỗi được thay bằng terminal
  envelope do gateway sở hữu.
- Không đổi model, không retry âm thầm, không để lỗi bận/timeout/cancel làm hỏng
  trạng thái key.

### Máy A

- Không hiểu chi tiết riêng của llama.cpp; chỉ hiểu hợp đồng B v1 và nhánh legacy
  có thời hạn.
- Một decoder cho sync/stream; bỏ các boolean `qua_dai`, `ban`, `het_gio` làm
  nguồn nghĩa.
- Một renderer chung biến `ModelFailure` thành RFC 9457, Anthropic, OpenAI Chat
  hoặc OpenAI Responses, trước và sau HTTP 200.
- Ghi cả `canonical_code` và `protocol_code`; không đưa lỗi thô B ra ngoài.

### Client/LTTCODE

- Quyết định hành động từ `canonical_code`/`recovery`; chỉ dùng message để hiển
  thị.
- Giữ một trường `lttCode` khi phải đổi sang mã tương thích DeepSeek Harness.
- Mã lạ là terminal/ambiguous có request ID, không tự compact và không retry
  vô hạn.

## 7. Ánh xạ giao thức mà không mất nghĩa

| Nguyên nhân LTT | `protocol_code` tương thích | Hành vi LTTCODE/DSH |
|---|---|---|
| `context_window_exceeded` | `context_length_exceeded` / `CONTEXT_WINDOW_EXCEEDED` | compact text |
| `input_tokens_exceeded` | `context_length_exceeded` / `CONTEXT_WINDOW_EXCEEDED` | compact text, vẫn hiển thị `lttCode=input_tokens_exceeded` |
| `image_count_exceeded` | `IMAGE_OFFLOAD_REQUIRED` khi có offloader | offload bớt ảnh; nếu không có thì terminal `INVALID_REQUEST` |
| `image_too_large` | `IMAGE_OFFLOAD_REQUIRED` khi offloader giảm được byte | offload/resize; nếu không có thì terminal |
| `max_output_tokens_exceeded` | `invalid_request_error` / `INVALID_REQUEST` | giảm output budget; tuyệt đối không compact input |
| `rate_limited`, `concurrency_limited` | `rate_limit_error` / `RATE_LIMIT` | tôn trọng `Retry-After`, backoff có trần |
| `provider_overloaded`, `model_loading` | `overloaded_error` / `SERVER` | retry có trần và jitter |
| `upstream_timeout`, `stream_idle_timeout` | `timeout_error` / `TIMEOUT` | outcome mơ hồ; chỉ retry an toàn theo chính sách/idempotency |
| `upstream_unreachable` | `api_error` / `TRANSPORT` | retry có trần |
| `request_cancelled` | `cancelled_error` / `ABORTED` | không retry |
| `malformed_upstream_response` | `api_error` / `MALFORMED_RESPONSE` | terminal hoặc retry có trần do client quyết |
| `upstream_unknown` | `api_error` / `UPSTREAM_UNKNOWN` | không compact/offload; hiện request ID |

OpenAI/Anthropic không chuẩn hoá extension `canonical_code`, nên A thêm extension
`ltt_error` bên cạnh shape tương thích. Client cũ bỏ qua; client LTT đọc nó.
RFC 9457 giữ `type=/errors/{canonical_code}` làm định danh problem chính theo
hợp đồng hiện có; extension `code` bằng đúng `canonical_code`, và chỉ thêm
`protocol_code` khi một adapter giao thức thực sự cần mã khác. Không dùng
`about:blank` cho các lỗi đã có ngữ nghĩa LTT riêng.

HTTP status chỉ còn là tín hiệu lớp giao thức, không phải nguồn phân loại:

- Trước khi gửi header, generic API dùng status ở §4; OpenAI-compatible dùng
  status tương ứng nhưng vẫn giữ `ltt_error`; Anthropic dùng 529 cho
  `provider_overloaded`, 413 chỉ cho `request_body_too_large`, 400 cho lỗi
  request/token/image.
- Sau HTTP 200, status không thể đổi. `/v1/messages` phát `event: error`,
  `/v1/responses` phát `response.failed`, Chat Completions phát một terminal
  error event đúng shape mà adapter đã công bố.
- `upstream_status` chỉ là dữ kiện chẩn đoán đã lọc. Client không được dùng nó
  thay `canonical_code`.

## 8. Catalog và preflight

`GET /api/v1/models` phải công bố từ manifest cùng các trường:

- `max_input_tokens`, `max_output_tokens`, `context_window`;
- `max_images`, `max_image_bytes`, `accepted_image_schemes`;
- modality và mức reasoning hỗ trợ.

Shape `models[]` dành cho Codex/LTTCODE cũng phải có các trần ảnh; không chỉ
`items[].constraints`. Preflight giúp lỗi tới sớm nhưng B vẫn là thẩm quyền cuối
cùng. Không hardcode số `4` trong LTTCODE.

## 9. Quan sát vận hành

Mỗi lỗi ghi một record có cấu trúc, không chứa prompt/ảnh/token bí mật:

```text
request_id, gateway_code, canonical_code, protocol_code, category,
http_status, upstream_status, protocol, stream_phase, retry, recovery,
model, elapsed_ms
```

Counter tối thiểu:

- tổng theo `canonical_code`, model, endpoint và `before_headers|after_headers`;
- số `upstream_unknown`;
- số envelope legacy;
- số mã B mà A không đăng ký;
- số lỗi thiếu/mất `request_id`;
- số action client đã kích hoạt: compact, image offload, retry, terminal.

Canary chỉ đạt nếu đối chiếu một request ID tìm được cùng mã ở client, A và B.
Mốc hoàn thành là `unknown=0` cho tập lỗi được tiêm kiểm thử, không phải ép lỗi
production không rõ nguyên nhân vào một nhãn đẹp.

## 10. Tương thích và thứ tự phát hành

1. A nhận được cả envelope cũ lẫn v1, nhưng chưa bỏ nhánh cũ.
2. B bắt đầu phát v1, vẫn kèm `legacy`; không đổi status trong bước này.
3. A có renderer mới sau cờ `LTT_PUBLIC_API_STRUCTURED_MODEL_ERRORS`, mặc định
   tắt; khi tắt phải giữ nguyên response cũ từng byte có ý nghĩa.
4. LTTCODE đọc structured code trước, message fallback chỉ để telemetry cảnh báo;
   phát hành client này trước khi bật cờ A.
5. Bật renderer A: bề mặt public dùng status đúng §4 (ảnh/token/output là 400;
   chỉ body byte quá lớn là 413), đồng thời luôn gửi `canonical_code`.
6. Chạy canary và ma trận tương thích; dashboard legacy phải về 0.
7. Xoá message/status inference ở LTTCODE và A, đồng thời bỏ cờ chuyển tiếp.
8. Sau ít nhất một chu kỳ phát hành không còn client cũ, bỏ `legacy` khỏi B.
9. Status **nội bộ B→A** có thể giữ 413 trong cả chu kỳ chuyển tiếp; chuẩn hoá nó
   thành 400 là thay đổi riêng sau khi A không còn đọc nghĩa từ status.

Rollback theo từng lớp: client → A renderer → A decoder → B envelope. Vì v1 là
thay đổi cộng thêm ở đầu quá trình, rollback A/client không buộc rollback B.

## 11. Tiêu chí nghiệm thu

- Ma trận mọi mã tại §4 qua ba protocol × sync/stream × lỗi trước/sau 200 có
  golden rõ ràng.
- Tiêm lại nhánh cũ `413 => context` phải làm test đỏ.
- Chia mỗi fixture SSE tại mọi byte boundary vẫn cho cùng kết quả.
- Lỗi ảnh không tăng counter compact; lỗi context không tăng counter offload.
- Lỗi bận, timeout, cancel, client disconnect không gọi `danh_dau_loi` cho key.
- Không có thông tin hạ tầng thô trong response; mọi lỗi có request ID.
- Catalog và B cùng trần; preflight client và phán quyết B trả cùng mã.
- Client cũ vẫn nhận shape hợp lệ; LTTCODE mới giữ được `lttCode` chính xác.
- Không còn điều kiện hành vi dựa trên câu chữ/status ngoài adapter legacy có
  ngày xoá và counter sử dụng.

## 12. Ngoài phạm vi

- Không đổi chính sách giá, model mặc định, context vật lý hay số ảnh tối đa.
- Không thêm fallback model im lặng.
- Không công bố lỗi nội bộ nhạy cảm chỉ để tên lỗi “chi tiết hơn”.
- Không sửa production trong phiên lập đặc tả/kế hoạch này.
