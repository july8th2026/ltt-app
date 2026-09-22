# Chuẩn hoá ngữ nghĩa lỗi LTT LLM end-to-end Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mọi lỗi model/gateway được định danh đúng một lần ở máy B, giữ nguyên mã và dữ kiện qua máy A, rồi được render tương thích nhưng không mất nghĩa cho mọi API client; không còn lỗi ảnh, output token hay payload byte bị gọi nhầm là lỗi context.

**Architecture:** `llm_gateway.error_contract` sở hữu vocabulary dây B→A; B chuẩn hoá lỗi của chính nó và llama.cpp thành envelope versioned. A dùng một `ModelFailure` decoder chung cho sync/stream và một renderer chung cho RFC 9457, Anthropic, OpenAI Chat và Responses. LTTCODE đọc structured code, giữ `lttCode` chính xác và ánh xạ riêng sang mã hành vi DeepSeek Harness. Rollout cộng thêm trước, xoá fallback sau khi telemetry legacy về 0.

**Tech Stack:** Python 3.13, FastAPI/Starlette, httpx, pytest; TypeScript/Node test runner trong `D:\LTTCODEAPP\plugins\llm-ltt`; llama.cpp/llama-swap trên máy B; RFC 9457, OpenAI-compatible SSE và Anthropic SSE.

**Spec:** [`docs/superpowers/specs/2026-09-21-chuan-hoa-ngu-nghia-loi-llm.md`](../specs/2026-09-21-chuan-hoa-ngu-nghia-loi-llm.md)

## Global Constraints

- Đọc `docs/00_LTT_OPERATING_CONTRACT.md`, `docs/ltt_llm_dual/RUNBOOK.md`,
  `docs/ltt_llm_dual/BAN_DO_DUONG_DI.md` và spec trên trước dòng code đầu tiên.
- Máy A và B đều là production. Mỗi task làm trên worktree riêng từ `main`, thay
  đổi nhỏ, test đỏ trước và test nhắm đúng cụm vừa sửa. Từ Task 10 trở đi không
  chạy L2 giữa các phase; chỉ chạy L1 khi cần gate cho deploy/gộp. Các L2 đã ghi
  ở Task 1-9 là lịch sử thật, không phải nhịp tiếp tục. Không chạy L3 giữa các
  task; một L3 duy nhất sau toàn bộ phiên triển khai.
- Trước gate, `test_nhanh.py` hoặc pytest từ ba tệp: chạy
  `python tools\cua_so_yen.py trang-thai` và `python tools\tai_may.py`; pytest
  thủ công `-n` tối đa 6.
- Không sửa/chạy ghi vào `D:\BOT GEMINI`. Không in credential, request body,
  prompt, ảnh hay thân lỗi thô chứa dữ liệu người dùng.
- Không đổi model, giá, trần vật lý, chính sách fallback hoặc trạng thái dịch vụ
  trong các task hợp đồng lỗi.
- Mọi thay đổi B đi qua `llm_gateway/deploy/deploy.ps1`; mọi thay đổi A đi qua
  quy trình `docs/16_CAP_NHAT_VA_DEPLOY.md`; chỉ deploy SHA có gate đúng cấp xanh.
- Giữ tương thích cộng thêm: A đọc old+v1 trước khi xoá legacy; B không đổi HTTP
  status cùng lúc thêm code; client mới không phụ thuộc message.
- Renderer public mới nằm sau `LTT_PUBLIC_API_STRUCTURED_MODEL_ERRORS`, mặc định
  `0`. Cờ chỉ dùng cho rollout/rollback, được xoá ở Task 13; không trở thành hai
  hợp đồng sống vĩnh viễn.
- Không ghép `canonical_code` và `protocol_code`. Mã trước là sự thật; mã sau là
  adapter tương thích.
- Lỗi không đủ bằng chứng phải là `upstream_unknown`. Cấm “đoán cho đẹp”.
- Tệp `tests/StudioShell.test.tsx` đang không được theo dõi và không thuộc hạng
  mục; không stage, sửa hay xoá.

## Review Focus

- Kiểm kỹ đường **sau HTTP 200**, ranh giới chunk SSE, abrupt EOF và cancellation;
  đây là nơi dễ có test shape nhưng không đo hành vi.
- Kiểm mọi action compact/offload/retry bằng `canonical_code`, không bằng status
  hoặc message.
- Kiểm bận/timeout/cancel/client disconnect không phạt key và không retry vô hạn.
- Kiểm response không lộ lỗi thô/VRAM/path/prompt; request ID phải truy vết được.
- Kiểm rollback từng lớp và tương thích client cũ trước mỗi deploy.

---

## Milestones, Dependencies, and GO/NO-GO

```text
Task 1 contract
  ├─> Tasks 2–4 B origin/stream normalization
  └─> Tasks 5–8 A decoder/runtime/renderer/catalog
Tasks 1–8 ─> Tasks 9–10 measurement/telemetry ─> Task 11 A+B rollout
Task 11 A+B verified ─> Task 12 LTTCODE (last implementation phase)
Task 12 + one clean release window ─> Task 13 legacy removal ─> Task 14 closeout
```

- **M0 — Spec accepted:** chủ dự án duyệt taxonomy, public fields và action map.
  NO-GO nếu một code có hai nghĩa hoặc một nghĩa dẫn tới hai action mâu thuẫn.
- **M1 — Offline contract green:** Tasks 1–11 đã gộp, cờ public vẫn tắt, toàn
  matrix fixture và mutation test xanh, chưa đổi response production. NO-GO nếu
  success bytes bị thay đổi, unknown bị gán thành lỗi biết trước, hoặc request
  body lọt vào log.
- **M2 — Compatibility bridge live:** A đọc old+v1, B phát v1+legacy, renderer
  cũ vẫn hợp lệ. NO-GO nếu request ID không nối được hoặc key bị phạt bởi
  busy/timeout/cancel.
- **M3 — A+B complete:** renderer A bật structured code và được nghiệm thu trực
  tiếp bằng ba giao thức, không dựa vào LTTCODE. NO-GO nếu A/B còn mất code,
  request ID hoặc public status sai nghĩa.
- **M4 — LTTCODE last:** chỉ sau M3 mới sửa/phát hành LTTCODE và kiểm
  compact/offload/retry. NO-GO nếu client còn suy nghĩa từ 413/message.
- **M5 — Legacy removed:** chỉ mở Task 13 khi counter legacy và mismatch bằng 0
  suốt chu kỳ đã chốt. Đây là **phiên phát hành sau**, không gộp chung lượt rollout
  đầu. Mỗi phiên triển khai vẫn chỉ chạy một L3 cuối phiên theo hợp đồng.

---

## File Structure

| Tệp | Trách nhiệm sau thay đổi |
|---|---|
| `llm_gateway/error_contract.py` (mới) | schema, enum code/category/retry/recovery và builder envelope B→A, thuần stdlib |
| `llm_gateway/upstream_errors.py` (mới) | chuẩn hoá lỗi llama.cpp HTTP/SSE, parser event tăng dần |
| `llm_gateway/ngan_sach.py` | mỗi chốt giới hạn ném mã chính xác, không chỉ `truong` |
| `llm_gateway/api.py` | mọi lỗi gateway dùng envelope v1 + request ID; terminal stream đi qua normalizer |
| `llm_gateway/upstream.py` | quan sát event có giới hạn, giữ nguyên byte success, phân biệt EOF/cancel/protocol error |
| `platform_core/llm/model_failure.py` (mới) | `ModelFailure`, decoder old/v1 và policy fail-closed |
| `platform_core/llm/cong_vlm.py` | cửa đồng bộ dùng decoder chung |
| `platform_core/llm/luong_vlm.py` | cửa stream dùng decoder chung, bỏ nghĩa từ boolean/status |
| `platform_core/runtime_noi_bo/luong.py` | mang nguyên `ModelFailure` qua hàng chờ và luồng công khai |
| `server/api/su_kien_loi.py` | renderer chung cho bốn shape trước/sau 200 |
| `server/api/streaming.py`, `server/api/chat.py` | gọi renderer, không tự dịch lỗi |
| `platform_core/public_api/errors.py`, `error_registry.py`, `config.py` | mã public/retry/action, RFC 9457 extensions và cờ rollout tạm thời |
| `server/api/tools.py` | công bố trần ảnh/token trong cả `items[]` và `models[]` |
| `tools/kiem_hop_dong_loi_llm.py` (mới) | canary/read-only matrix và report request-ID A↔B |
| `D:\LTTCODEAPP\plugins\llm-ltt\src\wire.ts` | kiểu envelope/extension mới |
| `D:\LTTCODEAPP\plugins\llm-ltt\src\errors.ts` | decoder structured, giữ `lttCode` |
| `D:\LTTCODEAPP\plugins\llm-ltt\src\translate.ts` | ánh xạ canonical → DeepSeek Harness |
| `D:\LTTCODEAPP\plugins\llm-ltt\src\adapter.ts` | preflight catalog + action theo code |

---

### Task 1: Khoá taxonomy bằng code registry và contract test

**Files:** Create `llm_gateway/error_contract.py`; create
`tests/test_1700_hop_dong_ma_loi_llm.py`. Public constants/registry are wired at
Task 7 together with the feature-gated renderer, so Task 1 cannot change the
live public error table prematurely.

**Interfaces:**

```python
def error_spec(code: str) -> GatewayErrorSpec:
    """Return the registered spec; raise KeyError for an unknown code."""

def make_error(code: str, *, request_id: str, field: str | None = None,
               limit: int | None = None,
               actual: int | None = None, retry_after_s: int | None = None,
               provider_type: str | None = None,
               provider_code: str | int | None = None,
               upstream_status: int | None = None) -> dict[str, object]:
    """Build v1 using the registry's safe message, never raw exception text."""
```

- [x] **Step 1 — test đỏ:** trong `test_1700`, chép nguyên tập 33 mã ở spec §4
  thành `EXPECTED_CODES`; assert registry không thiếu/thừa, mọi spec có category,
  status, retry, recovery hợp lệ và `make_error()` tạo đủ trường bắt buộc.
- [x] Assert riêng `request_body_too_large != context_window_exceeded`,
  `image_count_exceeded != input_tokens_exceeded`, và unknown code làm
  `error_spec()` ném `KeyError`.
- [x] Chạy
  `python -m pytest tests/test_1700_hop_dong_ma_loi_llm.py -q`; kỳ vọng FAIL vì
  module chưa tồn tại.
- [x] Cài đặt dataclass `GatewayErrorSpec`, tuple hằng hợp lệ và registry đúng
  spec. `make_error` chỉ nhận mã đăng ký, message mặc định an toàn nằm trong
  registry, không nhận raw exception.
- [x] Chạy lại test → PASS. Đột biến bằng tay: tạm đổi recovery của
  `image_count_exceeded` thành `reduce_input`; test phải FAIL; hoàn nguyên.
- [x] Chạy test nhắm `gateway:llm`, rồi L2 phạm vi đó;
  commit `feat(llm): define versioned model error taxonomy`.

### Task 2: Máy B phát envelope v1 cho mọi lỗi do gateway sở hữu

**Files:** Modify `llm_gateway/ngan_sach.py`; modify `llm_gateway/api.py`;
create `tests/test_1701_gateway_error_envelope.py`; extend các test budget/gateway
đã được `python tools\thanh_phan.py --test gateway:llm` liệt kê.

- [x] **Step 1 — test đỏ theo bảng:** parameterize từng nhánh thật:
  text-model nhận ảnh → `unsupported_modality`; quá số ảnh →
  `image_count_exceeded`; URL ngoài → `image_url_not_allowed`; ảnh byte lớn →
  `image_too_large`; output lớn → `max_output_tokens_exceeded`; input lớn →
  `input_tokens_exceeded`; tổng input+output lớn → `context_window_exceeded`.
  Assert cả `field/limit/actual`, không chỉ code.
- [x] Thêm ca 404 model, 429 hết suất, 499 huỷ, 504 timeout, 502 không nối được;
  assert `request_id` ở header và body giống request vào.
- [x] Chạy `python -m pytest tests/test_1701_gateway_error_envelope.py -q` → FAIL
  vì body hiện chỉ có `ly_do/truong/tran/thay` hoặc prose.
- [x] Đổi `VuotNganSach.__init__` nhận `code`; từng nơi raise truyền literal từ
  registry. `as_dict` gọi `make_error`, đồng thời kèm object `legacy` trong pha
  tương thích.
- [x] Tạo một helper trong `llm_gateway/api.py` để mọi `HTTPException` trên
  đường model do gateway sở hữu dùng cùng envelope. Không sửa status hiện tại
  trong task này.
- [x] Log structured fields, không log request body. Nếu caller không gửi
  `X-LTT-Request-Id`, B tự tạo và trả lại; nếu có thì bảo toàn nguyên giá trị đã
  validate độ dài/ký tự.
- [x] PASS test mới (16 ca) và test gateway hiện có (57 ca). Đột biến `images` thành
  `context_window_exceeded` phải làm đúng case đỏ.
- [ ] Test nhắm + L2 `gateway:llm`; commit
  `feat(gateway): emit structured error envelope`.

### Task 3: Chuẩn hoá lỗi HTTP từ llama.cpp tại biên máy B

**Files:** Create `llm_gateway/upstream_errors.py`; modify
`llm_gateway/api.py`; create `tests/test_1702_loi_http_llama_cpp.py`.

**Interface:**

```python
def decode_upstream_http(status: int, headers: Mapping[str, str],
                         body: bytes, *, request_id: str) -> dict[str, object]:
    """Return one sanitized version-1 envelope; never parse prose for meaning."""
```

- [x] **Step 1 — fixtures đỏ:** thêm body theo source llama.cpp cho
  `exceed_context_size_error`, `invalid_request_error`, `not_found_error`,
  `unavailable_error`, generic `server_error`; thêm body rỗng, HTML proxy, JSON
  sai, JSON có mã lạ và message chứa giả chữ “context”.
- [x] Assert chỉ `exceed_context_size_error` thành
  `context_window_exceeded`; message chứa “context” nhưng không có typed code
  phải thành `upstream_unknown`.
- [x] Chạy test → FAIL vì decoder chưa có.
- [x] Cài decoder ưu tiên typed field (`type`, `code`) theo mapping hữu hạn.
  Status chỉ chọn fallback transport chung; không phân loại semantic bằng text.
- [x] `provider_type/provider_code/upstream_status` chỉ vào envelope/log đã lọc;
  giới hạn kích thước body đọc để tránh lỗi proxy lớn làm tăng RAM.
- [x] Thay các nhánh `>=500`, 400/404/422 trong `api.py` dùng decoder; giữ quy
  tắc 597/598/599 nội bộ thành cancel/timeout/unreachable.
- [x] PASS 18 ca; đột biến để status 413 tự thành context làm đúng case đỏ.
- [ ] Test nhắm + L2 `gateway:llm`; commit
  `feat(gateway): classify llama http errors by typed code`.

### Task 4: Bắt lỗi terminal sau HTTP 200 mà không phá luồng thành công

**Files:** Modify `llm_gateway/upstream.py`; modify
`llm_gateway/upstream_errors.py`; modify `llm_gateway/api.py`; create
`tests/test_1703_loi_sau_200_may_b.py`.

**Interfaces:**

```python
class UpstreamEventObserver:
    def feed(self, chunk: bytes) -> list[ObservedFrame]:
        """Consume arbitrary byte chunks and return complete observed frames."""

    def finish(self) -> list[ObservedFrame]:
        """Flush EOF and classify an incomplete terminal stream if present."""
```

- [x] **Step 1 — test đỏ:** fixtures gồm SSE chuẩn `event:error/data`, OpenAI
  `data:{"error":{"code":"server_error"}}`, Responses `response.failed`,
  llama.cpp raw `error: {"message":"example"}`, event JSON chia tại **mọi byte
  boundary**, CRLF/LF, multi-line
  `data`, comment/heartbeat và UTF-8 chia giữa code point.
- [x] Thêm success golden; nối bytes output phải bằng bytes input tuyệt đối.
  Thêm abrupt EOF trước terminal → `stream_truncated`; terminal `[DONE]`/completed
  không được tạo lỗi; client cancellation → log-only `client_disconnected`.
- [x] Chạy test → FAIL.
- [x] Cài state machine có buffer bị chặn kích thước, xử lý event/line đầy đủ;
  không parse từng network chunk, không json-load dữ liệu chưa đủ.
- [x] Event thành công phát nguyên byte. Event lỗi chưa phát raw; chuyển thành một
  gateway terminal envelope có `canonical_code`. Lỗi mã lạ →
  `upstream_unknown`.
- [x] Gắn observer vào generator B. Đảm bảo close/cancel giải phóng socket/slot
  đúng một lần và không chuyển cancellation thành provider failure.
- [x] PASS 13 ca/permutation. Chạy test dưới điều kiện chunk một byte và chunk
  nguyên body; kết quả semantic phải giống nhau.
- [ ] Test nhắm + L2 `gateway:llm`; commit
  `feat(gateway): normalize terminal stream errors`.

### Task 5: Một decoder typed duy nhất trên máy A

**Files:** Create `platform_core/llm/model_failure.py`; modify
`platform_core/llm/cong_vlm.py`; modify `platform_core/llm/luong_vlm.py`; create
`tests/test_1704_model_failure_decoder.py`; modify `tests/test_251_cong_vlm.py`.

**Interface:**

```python
def decode_gateway_failure(status: int, headers: Mapping[str, str],
                           body: bytes) -> ModelFailure:
    """Decode v1 or bounded legacy data; fail closed as upstream_unknown."""
```

- [ ] **Step 1 — test đỏ:** cùng một fixture v1 phải tạo `ModelFailure` bằng nhau
  ở sync và stream. Fixture legacy `{truong: images, tran: 4, thay: 6}` phải ra
  `image_count_exceeded`; `{truong: context}` mới ra context.
- [ ] Assert body lạ/status 413 → `upstream_unknown`, **không** context; 429 giữ
  `Retry-After`; request ID ưu tiên body đã validate rồi header.
- [ ] Chạy `test_1704` + `test_251` → FAIL.
- [ ] Cài dataclass và decoder. Import registry B→A chỉ từ module thuần stdlib;
  thêm test import không kéo FastAPI/httpx để tránh coupling runtime vòng.
- [ ] `cong_vlm` và `luong_vlm` dùng decoder chung. Thay
  `KhongMoDuocLuong(ban, qua_dai, het_gio)` bằng exception mang
  `failure: ModelFailure`; giữ property tương thích chỉ trong một chu kỳ nếu
  caller cũ còn dùng và ghi counter legacy.
- [ ] Gỡ `_loi_parser_tool_call` khỏi đường quyết định khi B đã phát typed code;
  giữ fallback có telemetry trong pha rollout, không retry mã unknown.
- [ ] PASS. Đột biến khôi phục `if status == 413: qua_dai=True` phải làm test đỏ.
- [ ] Test nhắm `core:provider` (lệnh nặng, kiểm máy trước), L2; commit
  `refactor(llm): share typed gateway failure decoder`.

### Task 6: Mang nguyên lỗi qua runtime/hàng chờ, không nén thành boolean

**Files:** Modify `platform_core/runtime_noi_bo/luong.py`; modify
`server/api/streaming.py`; modify `server/api/chat.py`; create
`tests/test_1705_bao_toan_loi_qua_runtime.py`.

- [ ] **Step 1 — test đỏ:** fake `mo_thuong_nguon` ném từng `ModelFailure`; assert
  `luong_co_cho` nhận nguyên object và không đổi code/field/limit/actual/retry.
- [ ] Thêm ca `image_count_exceeded`, `max_output_tokens_exceeded`, context,
  capacity, timeout, unknown và cancellation; assert chỉ lỗi provider thật mới
  gọi `danh_dau_loi`, bận/timeout/cancel/client disconnect thì không.
- [ ] Chạy test → FAIL vì `KhongMoDuoc` hiện chỉ giữ ba boolean.
- [ ] Đổi `KhongMoDuoc` mang `failure`; mọi catch/rethrow dùng exception chaining
  nhưng public response không lấy `str(exc)`.
- [ ] Tách quyết định retry provider parser thành policy theo code với số lần
  hữu hạn. Không retry `provider_oom`, invalid request, image, token hay unknown.
- [ ] PASS; đối chứng tiêm lại boolean-only phải làm case ảnh đỏ.
- [ ] Test nhắm `core:provider` + `server:api`; L2; commit
  `refactor(runtime): preserve model failure semantics`.

### Task 7: Renderer thống nhất cho RFC 9457 và ba giao thức model

**Files:** Modify `server/api/su_kien_loi.py`; modify
`platform_core/public_api/errors.py`; modify
`platform_core/public_api/error_registry.py`; modify
`platform_core/public_api/config.py`; modify `server/api/errors.py`; create
`tests/test_1706_loi_model_xuyen_giao_thuc.py`.

**Interface:**

```python
def render_model_failure(path: str, failure: ModelFailure, *,
                         phase: Literal["before_headers", "after_headers"],
                         stream: bool) -> Response | bytes:
    """Render one failure without changing its canonical semantics."""
```

- [ ] **Step 1 — golden đỏ:** cho mỗi mã ở spec §4, tạo golden cho generic
  problem+json, `/v1/messages`, `/v1/chat/completions`, `/v1/responses`; kiểm cả
  trước header và terminal SSE sau 200 nơi giao thức cho phép.
- [ ] Thêm test cờ tắt giữ response legacy hiện tại; cờ bật dùng renderer mới.
  Cấu hình đọc qua `load_public_api_config(env)` để test không phụ thuộc env máy.
- [ ] Assert `canonical_code`, `protocol_code`, `request_id`, field/limit/actual
  không mất. Assert Anthropic/OpenAI shape vẫn hợp lệ với client cũ.
- [ ] Chạy test → FAIL vì `_MA` hiện có bốn nhãn và `loi_sse` nhận string rời.
- [ ] Thay `_MA` bằng mapping registry → protocol renderer. `ltt_error` là
  extension an toàn; message giao thức có thể giữ câu tương thích
  `prompt is too long`, nhưng action không đọc câu đó.
- [ ] Chỉ hai mã token phù hợp được render protocol context-compatible; lỗi ảnh
  và output-token không bao giờ dùng `context_length_exceeded`.
- [ ] Ở public surface khi cờ bật, ảnh/input-output validation dùng 400; 413 chỉ
  cho `request_body_too_large`. Status nội bộ B→A vẫn được decoder chấp nhận và
  không phải public status.
- [ ] RFC 9457 trả `application/problem+json`; `type=/errors/{canonical_code}` là
  định danh problem chính và `code` bằng canonical. Test cả hai để chúng không
  trôi khỏi nhau. Authentication tiếp tục gom một `unauthorized`, không tạo key
  oracle.
- [ ] PASS; snapshot phải đỏ nếu xoá `ltt_error` hoặc đổi ảnh thành context.
- [ ] Test nhắm `server:api` + `core:api_cong_khai`; L2; commit
  `feat(api): render typed model errors for every protocol`.

### Task 8: Công bố giới hạn model để client preflight đúng

**Files:** Modify `server/api/tools.py`; modify
`tests/golden/public_api_catalog_v1.json`; create
`tests/test_1707_catalog_gioi_han_model.py`; đọc nguồn từ
`apps/ltt_llm/manifest.py`, không tạo hằng số mới.

- [ ] **Step 1 — test đỏ:** với từng model public, assert `items[].constraints`
  và `models[]` cùng có/cùng giá trị `max_input_tokens`, `max_output_tokens`,
  `context_window`, `max_images`, `max_image_bytes`, modality và scheme ảnh.
- [ ] Assert model text có `max_images=0`; model vision dùng đúng manifest; không
  có literal trần ảnh trong `server/api/tools.py`.
- [ ] Chạy test → FAIL vì `_dang_codex` hiện bỏ các trần ảnh.
- [ ] Mở rộng `_dang_codex` đọc manifest/catalog source hiện có; cập nhật golden.
- [ ] PASS; test nhắm `server:api` + `app:ltt_llm`; L2; commit
  `feat(catalog): publish exact model input constraints`.

### Task 9: Bộ đo contract hai chiều bằng dữ liệu thật, không gây tải giả

**Files:** Create `tools/kiem_hop_dong_loi_llm.py`; create
`tests/test_1708_bo_do_hop_dong_loi_llm.py`; create
`docs/ltt_llm_dual/LOI_MODEL_RUNBOOK.md`.

**CLI:**

```text
python tools\kiem_hop_dong_loi_llm.py fixture --output <dir>
python tools\kiem_hop_dong_loi_llm.py live --minutes 20 --output <dir>
python tools\kiem_hop_dong_loi_llm.py inject --base-url <test-url> --output <dir>
```

- [ ] **Step 1 — test đỏ:** kiểm CLI fixture không cần network và sinh
  `report.json`/`report.md` với matrix code, protocol, phase, status,
  canonical/protocol code, action và pass/fail.
- [ ] Cài `fixture`: replay corpus đã khử dữ liệu nhạy cảm; không tự lấy log thật
  làm golden. Golden lấy từ registry/spec độc lập.
- [ ] Cài `live` mặc định read-only/passive: lấy cửa sổ log/counter định sẵn,
  không gửi prompt, không chạm GPU, không in token; thống kê request ID coverage,
  unknown, legacy, mismatch và action.
- [ ] Cài `inject` chỉ chạy với test URL/credential do operator cấp; từ chối
  hostname production trừ cờ rõ ràng được runbook yêu cầu. Các request lỗi rẻ,
  không sinh dài và không dùng ảnh người dùng.
- [ ] Test hai chiều lớp C: (1) fixture không đổi dưới tải máy giả lập; (2) tiêm
  decoder cũ 413→context làm report đỏ. Mở tay hai mismatch đầu tiên trước khi
  biến phép đo thành gate.
- [ ] `test_1708` PASS; test nhắm `gateway:llm`, `core:provider`, `server:api`;
  L2; commit `test(llm): add end-to-end error contract monitor`.

### Task 10: Telemetry và cảnh báo drift

**Files:** Modify logging tại `llm_gateway/api.py`,
`platform_core/llm/model_failure.py`, `server/api/streaming.py`; extend
`tests/test_1708_bo_do_hop_dong_loi_llm.py`.

- [ ] **Step 1 — test đỏ:** capture log cho known, legacy, unknown, mismatch và
  client disconnect; assert đủ trường ở spec §9 và không chứa prompt, data URL,
  Authorization, raw body hay credential.
- [ ] Thêm counter `llm_error_total`, `llm_error_unknown_total`,
  `llm_error_legacy_total`, `llm_error_contract_mismatch_total`,
  `llm_error_request_id_missing_total`, gắn label hữu hạn; tuyệt đối không label
  request ID/message để tránh cardinality bùng nổ.
- [ ] Thêm log action ở A/B: retry/terminal/legacy/unknown; không ghi nội dung
  cuộc hội thoại. Action compact/offload của LTTCODE để Task 12 bổ sung sau.
- [ ] PASS; kiểm một fixture chứa secret giả không xuất hiện trong caplog/report.
- [ ] Test nhắm các thành phần; khép riêng mọi phép kiểm đã đỏ. Không chạy lại
  L2; chỉ dùng L1 nếu cần gate cho deploy/gộp; commit
  `feat(observability): trace model errors across A and B`.

### Task 11: Hoàn tất và nghiệm thu máy B + máy A trước LTTCODE

**Files:** Modify `docs/ltt_llm_dual/LOI_MODEL_RUNBOOK.md`; use report directory
`tmp/kiem_loi_model_<timestamp>` (không commit dữ liệu vận hành).

- [ ] Chụp baseline 20 phút bằng `live`: traffic thật đang có, không phát job
  mới. Ghi tổng request, code hiện thấy, legacy/unknown và tỷ lệ request ID; dữ
  liệu nhạy cảm không vào báo cáo.
- [ ] Deploy **A decoder/runtime/telemetry tương thích old+v1** trước, với
  `LTT_PUBLIC_API_STRUCTURED_MODEL_ERRORS=0`. Nghiệm thu health, một request test
  không lỗi, fixture replay và response legacy. Rollback: bản A trước thay đổi.
- [ ] Deploy **B envelope + normalizer** trong cửa sổ yên theo runbook; không đổi
  llama model/config. Nghiệm thu health, model ready, request bình thường và bảy
  lỗi budget rẻ. Rollback: artifact B trước thay đổi.
- [ ] Bật **A renderer/catalog** bằng
  `powershell -ExecutionPolicy Bypass -File C:\LTTPlatform\setup\dat_bien_env.ps1 -Ten LTT_PUBLIC_API_STRUCTURED_MODEL_ERRORS -Gia_tri 1`, rồi dùng
  `python tools\nang_quyen.py --lenh` theo §9.3 để chạy
  `C:\LTTPlatform\setup\nap_lai_env.ps1 -Services LTTStudioWeb`. Chỉ restart web,
  không restart worker/Codex đang giữ job. Nghiệm thu cả ba protocol,
  sync/stream, public status đúng nghĩa và request ID A↔B. Rollback nhanh: đặt
  cờ về `0` và chỉ nạp lại `LTTStudioWeb`; không cần rollback B.
- [ ] Chạy canary A+B 20 phút bằng HTTP client chuẩn và fixture, **không qua
  LTTCODE**: `contract_mismatch=0`, lỗi tiêm có `unknown=0`, mọi request kiểm có
  request ID xuyên suốt; ảnh/context/output token có canonical code và public
  status đúng spec.
- [ ] Nếu bất kỳ invariant đỏ: dừng rollout, lưu report, rollback lớp vừa deploy;
  không “chữa” bằng đổi mapping khi chưa có evidence B/A cùng request ID.
- [ ] Chỉ đánh dấu A+B hoàn tất khi direct API matrix xanh và traffic thật không
  tăng `unknown`, mismatch hay lỗi key. Sau mốc này mới được mở Task 12.
- [ ] Commit runbook với **lệnh/kết quả thật** sau triển khai, không chép secret.
- [ ] Trước mỗi deploy chỉ dùng L1 trên đúng SHA theo hợp đồng; không chạy L2
  giữa các bước rollout. L3 dành duy nhất cho Task 14 sau khi mọi phase kết thúc.

### Task 12: LTTCODE đọc mã có cấu trúc và kích hoạt đúng recovery — làm cuối

**Precondition:** Task 11 đã nghiệm thu máy A+B trên production bằng direct API;
không dùng LTTCODE để che hoặc bù lỗi server.

**Repository:** `D:\LTTCODEAPP`. Trước khi sửa, kiểm `git status`, đọc mọi
`AGENTS.md` nếu xuất hiện và không chạm thay đổi ngoài plugin `llm-ltt`.

**Files:** Modify `plugins/llm-ltt/src/wire.ts`, `src/errors.ts`,
`src/translate.ts`, `src/adapter.ts`, `test/adapter.test.mjs`, `CONTRACT.md`.

- [ ] **Step 1 — test đỏ:** thay test cũ “mọi 413 → context” bằng matrix:
  `request_body_too_large` terminal; `image_count_exceeded` offload;
  `max_output_tokens_exceeded` invalid request; chỉ token/context phù hợp compact.
- [ ] Thêm fixture lấy từ response A+B đã nghiệm thu cho RFC 9457, Anthropic,
  Chat, Responses `response.failed`, lỗi sau 200, unknown code, body cũ và body
  sai. Fixture phải khử request ID/dữ liệu thật.
- [ ] Assert object lỗi có `lttCode`, `protocolCode`, `requestId`, `recovery`,
  `retryAfter`; tên hiển thị lấy `lttCode`, không lấy enum chung của DSH.
- [ ] Chạy lệnh test thật khai trong `plugins/llm-ltt/package.json`; kỳ vọng FAIL.
- [ ] Mở rộng wire types; decoder ưu tiên `ltt_error.canonical_code`, rồi RFC
  `code`; legacy message parser chỉ là fallback có warning/counter.
- [ ] `translate.ts` ánh xạ đúng spec §7. Unknown thành `UPSTREAM_UNKNOWN`, không
  tự compact/offload/retry. Giữ `IMAGE_OFFLOAD_REQUIRED` chỉ khi plugin offload
  thực sự có thể xử lý.
- [ ] `adapter.ts` đọc trần catalog thay vì số cứng; preflight tạo cùng
  `canonical_code` mà B sẽ tạo. B vẫn là authoritative.
- [ ] Thêm log action LTTCODE `compact|offload|retry|terminal`, không ghi nội dung
  hội thoại; đối chiếu request ID với A+B.
- [ ] PASS toàn bộ plugin test. Đột biến `status === 413` thành context phải làm
  ít nhất ba case đỏ.
- [ ] Commit/phát hành riêng tại repo LTTCODE:
  `fix(llm-ltt): preserve server error semantics`.
- [ ] Chạy canary LTTCODE 20 phút: lỗi ảnh không compact, lỗi context không
  offload, output-token không compact, unknown không retry; không phát job tải
  nặng chỉ để tạo lỗi.

### Task 13: Xoá suy diễn cũ sau khi telemetry chứng minh không còn dùng

**Files:** Modify `platform_core/llm/luong_vlm.py`,
`platform_core/llm/model_failure.py`, `server/api/su_kien_loi.py`;
modify `platform_core/public_api/config.py`;
modify LTTCODE `src/errors.ts`; modify `llm_gateway/ngan_sach.py`; modify test
1603/1605/1606/1608 và plugin tests.

- [ ] Điều kiện vào task: ít nhất một chu kỳ phát hành có
  `llm_error_legacy_total=0` và `contract_mismatch=0` trong cửa sổ vận hành đã
  chốt; report được lưu và dẫn trong nhật ký.
- [ ] **Test đỏ chống hồi quy:** assert source/runtime không còn nhánh
  `status == 413 => context`, không còn message substring quyết định action và
  B không còn phát khoá legacy. Đây là test hành vi bằng fixture, không chỉ grep.
- [ ] Xoá property boolean compatibility và legacy decoder/message fallback;
  mã lạ vẫn fail closed thành `upstream_unknown`.
- [ ] Xoá `LTT_PUBLIC_API_STRUCTURED_MODEL_ERRORS` và nhánh renderer cũ; renderer
  structured trở thành đường duy nhất sau khi telemetry chứng minh an toàn.
- [ ] Xoá `legacy` khỏi envelope B. Không đổi HTTP status trong cùng commit; nếu
  muốn chuẩn hoá status, mở quyết định/API change riêng.
- [ ] Chạy toàn ma trận lỗi và LTTCODE. Đột biến đưa nhánh 413 cũ trở lại phải
  làm test đỏ.
- [ ] Test nhắm đúng cụm; không chạy L2 giữa phase; commit riêng từng repo:
  `refactor(llm): remove legacy error inference`.

### Task 14: Đồng bộ tài liệu, quyết định và tổng kết phiên

**Files:** Modify `docs/QUYET_DINH_NEN_TANG.md`; modify
`docs/ltt_llm_dual/DECISION_LOG.md`; modify
`docs/ltt_llm_dual/AUDIT_API_2026-09-14.md` bằng ghi chú hậu kiểm, không sửa lịch
sử; modify docs API được `tools/build_public_api_docs.py` sinh; modify
`docs/KE_HOACH_TRIEN_KHAI.md`; modify `docs/NHAT_KY.md`; modify LTTCODE
`CONTRACT.md`.

- [ ] Ghi quyết định mới: status không phải semantic; canonical/protocol code
  tách biệt; unknown fail closed; B sở hữu origin, A sở hữu public rendering.
  Không sửa đè quyết định cũ — đánh dấu `ĐÃ THAY` theo đúng giao thức quyết định.
- [ ] Sửa mọi tài liệu nói “413 = context” hoặc “client nhận ra bằng câu chữ”;
  `git grep -n` toàn hai repo và phân loại từng hit còn hợp lệ/đã chết.
- [ ] Sinh lại docs error registry/catalog bằng công cụ repo; không sửa file dẫn
  xuất bằng tay.
- [ ] Rà toàn bộ tài liệu và source mới để không còn chỗ giữ chỗ, tên tạm hoặc
  câu “làm sau”; mọi interface và đường dẫn phải là tên cuối cùng.
- [ ] Chạy toàn bộ test nhắm của 14 task. Sau khi mọi pha của phiên kết thúc mới
  chạy một L3 theo hợp đồng; nếu đỏ, sửa tại chỗ rồi khép bằng lệnh gate in sẵn,
  không chạy L3 lần hai.
- [ ] Cập nhật kế hoạch/nhật ký bằng lệnh và kết quả thật; commit, gộp main và
  deploy tài liệu nếu cần theo hợp đồng.

---

## Definition of Done

- [ ] 33 mã ở spec có registry, test và renderer đầy đủ; không có mã orphan.
- [ ] Cùng một lỗi giữ nguyên `canonical_code` qua B log/envelope, A log/response
  và LTTCODE `lttCode`.
- [ ] Toàn ma trận protocol × phase × stream qua; byte-boundary stream test qua.
- [ ] Không có action dựa vào message/status; unknown không bị gắn nhãn giả.
- [ ] Ảnh chỉ offload, context/input token mới compact, output token chỉ giảm
  output, capacity mới backoff.
- [ ] Bận/timeout/cancel/disconnect không làm hỏng key; không có retry vô hạn.
- [ ] Request ID truy được qua client↔A↔B; response không lộ dữ liệu nhạy cảm.
- [ ] Catalog/preflight và B cùng giới hạn; B vẫn là thẩm quyền cuối.
- [ ] Rollout/rollback đã được diễn tập, report canary lưu ngoài git.
- [ ] Test nhắm từng cụm đều xanh; L1 chỉ khi deploy/gộp cần gate; một L3 duy
  nhất cuối phiên xanh trên đúng SHA.
