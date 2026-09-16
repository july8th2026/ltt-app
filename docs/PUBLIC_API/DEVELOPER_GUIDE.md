# LTT Studios Public API — hướng dẫn cho lập trình viên

Bản này viết cho người tích hợp. Quy tắc nội bộ ở `KERNEL_V1.md`,
`SECURITY_MATRIX_V1.md`, `DEVELOPER_KEYS_V1.md`.

Đường dẫn chuẩn: `/api/v1` trên `https://app.lttstudios.com`.
Spec máy đọc: `GET /api/v1/openapi.json`.

---

## 0. Biến môi trường

<!-- BEGIN GENERATED ENV -->

| Biến | Ví dụ | Để làm gì |
|---|---|---|
| `LTT_BASE_URL` | `https://app.lttstudios.com` | Where the API lives. No trailing slash; /api/v1 is added for you. |
| `LTT_API_KEY` | `ltt_sk_…` | Your developer key. Create it in the portal; it is shown once. |
| `LTT_PROJECT_ID` | — | Optional. The key already belongs to a project — set this only if your own code routes by project. |

**bash / zsh (macOS, Linux)**

```
export LTT_BASE_URL="https://app.lttstudios.com"
export LTT_API_KEY="ltt_sk_…"
```

**PowerShell (Windows)**

```
$env:LTT_BASE_URL = "https://app.lttstudios.com"
$env:LTT_API_KEY  = "ltt_sk_…"
```

**cmd.exe (Windows)**

```
set LTT_BASE_URL=https://app.lttstudios.com
set LTT_API_KEY=ltt_sk_…
```

Lời gọi đầu tiên (`image.generate`) — báo giá trước, chạy sau:

```bash
curl -X POST "$LTT_BASE_URL/api/v1/quotes" \
  -H "Authorization: Bearer $LTT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
  "tool": "image.generate",
  "input": {
    "prompt": "a paper boat on a rain-soaked street at night",
    "image_key": "upl_from_POST_/api/v1/uploads",
    "aspect_ratio": "16:9",
    "count": 1
  }
}'
```

```bash
curl -X POST "$LTT_BASE_URL/api/v1/jobs" \
  -H "Authorization: Bearer $LTT_API_KEY" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{
  "tool": "image.generate",
  "quote": "<quote from the step above>",
  "input": {
    "prompt": "a paper boat on a rain-soaked street at night",
    "image_key": "upl_from_POST_/api/v1/uploads",
    "aspect_ratio": "16:9",
    "count": 1
  }
}'
```

Không viết khóa thẳng vào mã nguồn: nó sẽ đi theo mã vào git, vào log và vào ảnh chụp màn hình.

<!-- END GENERATED ENV -->

## 1. Bắt đầu trong 5 phút

**Bước 1 — lấy khóa.** Đăng nhập, mở **`/developers`**, bấm *Tạo khóa*. Chuỗi
bí mật hiện **đúng một lần**; chép ngay. Máy chủ chỉ giữ dấu vân tay một chiều,
không ai lấy lại được — mất thì tạo khóa mới.

**Bước 2 — kiểm tra khóa.**

```bash
curl -s https://app.lttstudios.com/api/v1/me \
  -H "Authorization: Bearer $LTT_API_KEY"
```

```json
{"key_id":"…","account_id":"…","scopes":["tools:read","jobs:read"],"allowed_tools":[]}
```

**Bước 3 — xem công cụ.**

```bash
curl -s https://app.lttstudios.com/api/v1/tools \
  -H "Authorization: Bearer $LTT_API_KEY"
```

**Bước 4 — báo giá rồi chạy.** Luôn hai bước: báo giá cho biết **chính xác** số
credit sẽ bị trừ, và bạn chỉ bị trừ khi gửi báo giá đó lên `/jobs`.

```bash
QUOTE=$(curl -s https://app.lttstudios.com/api/v1/quotes \
  -H "Authorization: Bearer $LTT_API_KEY" -H "Content-Type: application/json" \
  -d '{"tool":"image.thumbnail","input":{"topic":"cách nướng bánh mì","count":2}}')

echo "$QUOTE"      # {"quote":"…","tool":"image.thumbnail","credit":10,…}

curl -s https://app.lttstudios.com/api/v1/jobs \
  -H "Authorization: Bearer $LTT_API_KEY" -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d "{\"tool\":\"image.thumbnail\",\"quote\":$(echo "$QUOTE" | jq .quote),
       \"input\":{\"topic\":\"cách nướng bánh mì\",\"count\":2}}"
```

**Bước 5 — chờ và lấy kết quả.**

```bash
curl -s https://app.lttstudios.com/api/v1/jobs/$JOB_ID \
  -H "Authorization: Bearer $LTT_API_KEY"
# {"status":"succeeded","credit":{"held":10,"charged":10},
#  "outputs":[{"id":"<job>.image_keys.0",…}]}

curl -s https://app.lttstudios.com/api/v1/artifacts/$ARTIFACT_ID \
  -H "Authorization: Bearer $LTT_API_KEY"
# {"url":"https://…","expires_in":300}
```

---

## 1b. Cửa chat — trả lời ngay trong request

Từ 2026-08-23 (Q106) có **hai cửa chạy việc**, và chọn nhầm cửa là nguồn nhầm
lẫn lớn nhất khi bắt đầu:

| | `POST /api/v1/jobs` | `POST /api/v1/chat/completions` |
|---|---|---|
| số bước | 3 (báo giá → nộp → hỏi kết quả) | **1** |
| báo giá | bắt buộc | **không có** |
| biết giá trước khi chạy | có | **không** — xem dưới |
| hàng đợi | có | không |
| trần thời gian | không | **có** |
| `Idempotency-Key` | bắt buộc | bắt buộc |
| hợp với | ảnh, video, việc dài | chat, coding, việc trả lời được ngay |

### Lời gọi đầu tiên

```bash
curl -X POST "$LTT_BASE_URL/api/v1/chat/completions" \
  -H "Authorization: Bearer $LTT_API_KEY" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{"model":"ltt-3.8",
       "messages":[{"role":"user","content":"Viết một câu chào bằng tiếng Việt."}],
       "max_tokens":300}'
```

```json
{
  "object": "chat.completion",
  "model": "ltt-3.8",
  "choices": [{"index":0,"message":{"role":"assistant","content":"…"},"finish_reason":"stop"}],
  "usage": {"prompt_tokens":12,"completion_tokens":18,"total_tokens":30},
  "x_ltt": {
    "credit_charged": 1,
    "credit_held": 4,
    "usage_measured": true,
    "cached_prompt_tokens": 0,
    "duration_seconds": 1.8,
    "test_mode": false
  }
}
```

`usage` giữ **đúng hình dạng OpenAI** để mã sẵn có của bạn đọc được. Mọi thứ
riêng của nền tảng nằm trong `x_ltt` — nhét chúng vào `usage` sẽ làm vỡ những
client parse chặt.

### Dùng SDK của OpenAI

Trỏ `base_url` vào `/api/v1` là xong — **trừ một chỗ**:

```python
# pip install openai
import os, uuid
from openai import OpenAI

client = OpenAI(api_key=os.environ["LTT_API_KEY"],
                base_url=os.environ["LTT_BASE_URL"].rstrip("/") + "/api/v1")

answer = client.chat.completions.create(
    model="ltt-3.8",
    messages=[{"role": "user", "content": "Viết một câu chào bằng tiếng Việt."}],
    max_tokens=300,
    extra_headers={"Idempotency-Key": uuid.uuid4().hex},   # ← bắt buộc
)
print(answer.choices[0].message.content)
print("đã trả:", answer.model_extra["x_ltt"]["credit_charged"], "credit")
```

🔴 **Vì sao phải thêm `extra_headers`.** Đây là sự thật **đã đo** với `openai`
2.30.0, không phải phỏng đoán: SDK của OpenAI **tự sinh** một khoá idempotency
cho mỗi lượt POST và dùng lại nó qua các lần thử lại của chính nó — nhưng chỉ
**gửi** khi `_idempotency_header` được đặt, mà với client OpenAI thì nó là
`None`. Khoá được sinh ra rồi vứt đi. Nên một lượt gọi đúng y tài liệu OpenAI sẽ
nhận **400** ở đây, và thông báo lỗi nói rõ phải thêm gì.

⛔ **Đừng đưa khoá vào `default_headers` của client.** Nó thành **một** khoá cho
**mọi** lượt gọi, và hỏng theo hai kiểu — một kiểu ồn ào, một kiểu im lặng:

- câu hỏi khác lần trước → **409** `idempotency_conflict`;
- câu hỏi **giống hệt** lần trước → bạn nhận lại **câu trả lời cũ**, không có
  dấu hiệu gì, và không có lượt chạy mới nào.

Khoá thuộc về **một lượt gọi**, không thuộc về client. Sinh nó ngay trước lượt
gọi, và chỉ dùng lại đúng khoá đó khi bạn thử lại đúng lượt đó.

### Tiền: giữ một TRẦN, thu theo số ĐO

Giá phụ thuộc số token model sinh ra — mà số đó **chưa tồn tại** lúc bạn gọi.
Nên cửa này không có báo giá, và thay vào đó:

1. nền tảng **giữ một trần** ước cao (giả định không có cache và sinh đủ
   `max_tokens`) **trước khi** chạm tới model;
2. chạy;
3. **thu theo token đã đo**, và hoàn phần chênh.

Vì vậy `x_ltt.credit_charged` thường **thấp hơn nhiều** `x_ltt.credit_held`.
Số bạn thật sự trả là `credit_charged`.

Ba trường hợp không tốn tiền, và cả ba đều hoàn **đủ** phần đã giữ:

- **model bận** → `503` kèm `Retry-After`;
- **lỗi phía máy chủ** → `5xx`;
- **không đo được `usage`** → bạn vẫn nhận câu trả lời, `usage_measured` là
  `false`, và `credit_charged` là **0**. Thu tiền mà không có bằng chứng thì tệ
  hơn mất một ít tiền.

Muốn **biết giá trước khi chạy** thì dùng cửa job: `POST /api/v1/quotes`.

### Trần thời gian, và trần `max_tokens` sinh ra từ nó

Lượt gọi phải xong trong ngân sách đồng bộ của máy chủ (nằm **dưới** trần 100
giây của Cloudflare, có biên). Từ đó suy ra một trần `max_tokens`.

Xin quá trần thì bạn nhận **400 ngay lập tức**, kèm con số cụ thể và lời chỉ
sang `POST /api/v1/jobs` — thay vì bị cắt giữa chừng bằng một cái `524` không
phân biệt được "hỏng" với "xong rồi nhưng mất kết nối".

### Streaming — có, nhưng ở hai cửa khác

`POST /api/v1/chat/completions` **không** stream: `"stream": true` ở đây bị từ
chối bằng **400**. Nhận rồi trả một lượt không-stream sẽ làm SDK vỡ ở chỗ khó
lần ra hơn nhiều, nên máy chủ nói thẳng.

🔴 **Mục này trước đây mang tiêu đề *"Chưa có streaming"* và câu ấy SAI.** Sửa
14/09/2026. Nền tảng có **hai cửa stream đang chạy**, và chúng là đường mà
Codex CLI, Claude Code, các tiện ích VS Code và Claude Desktop đang dùng — chỉ
là tài liệu này chưa bao giờ nhắc tới chúng. Một năng lực không ai đọc được
trong tài liệu là một năng lực không ai dùng được.

| cửa | giao thức | trường đầu vào | trường token ra |
|---|---|---|---|
| `POST /api/v1/messages` | Anthropic Messages | `messages`, `system` riêng | `max_tokens` |
| `POST /api/v1/responses` | OpenAI Responses | `input` (chuỗi hoặc mảng) | `max_output_tokens` |

Cả hai trả `text/event-stream`, và cả hai **bắt buộc `Idempotency-Key`** như mọi
cửa có tính tiền.

```bash
curl -N -X POST "$LTT_BASE_URL/api/v1/messages" \
  -H "Authorization: Bearer $LTT_API_KEY" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{"model":"ltt-3.8","max_tokens":300,"stream":true,
       "system":"Trả lời ngắn gọn.",
       "messages":[{"role":"user","content":"Chào"}]}'
```

```
event: message_start
data: {"type":"message_start","message":{"id":"chatcmpl-…","role":"assistant",…}}
```

```bash
curl -N -X POST "$LTT_BASE_URL/api/v1/responses" \
  -H "Authorization: Bearer $LTT_API_KEY" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{"model":"ltt-3.8","max_output_tokens":300,"stream":true,"input":"Chào"}'
```

```
event: response.created
data: {"type":"response.created","response":{"id":"resp_…","status":"in_progress",…}}
```

⭐ **Vì sao nên dùng stream cho việc dài.** Cửa đồng bộ có trần thời gian (mục
trên); stream gửi byte đầu tiên sớm nên Cloudflare không cắt, và bạn thấy chữ
chạy ngay thay vì chờ trọn câu trả lời.

### Bận là 503, không phải 429

Hai mã này nói hai chuyện khác hẳn, và nhầm chúng dẫn tới xử lý sai:

- **503** — máy không phục vụ được lúc này (model đang bận). Bạn **không** bị
  thu tiền. `Retry-After` nói khi nào quay lại.
- **429** — **bạn** đang gọi quá nhanh, hoặc chạm hạn mức của tài khoản.

### Chế độ thử

Khoá ở chế độ test trả về một câu trả lời có hình dạng thật, `x_ltt.test_mode`
là `true`, **không** gọi model và **không** trừ credit. Dùng nó để chạy CI mà
không đốt GPU.

## 2. Xác thực

- Chỉ `Authorization: Bearer <khóa>`. Cookie **không** được chấp nhận, và API
  không dùng CSRF token — bearer chỉ được đính bởi client đã có nó.
- Mọi lỗi xác thực trả **401 với cùng một thông điệp**: sai định dạng, không có
  khóa đó, sai bí mật, đã thu hồi/hết hạn đều giống nhau. Đừng phân tích thông
  điệp để đoán nguyên nhân — hãy kiểm tra `key_id` ở `/developers`.
- Khóa có dạng `ltt_sk_<key_id>_<secret>`. Phần `key_id` là **công khai**: dùng
  nó khi cần hỗ trợ. Đừng bao giờ gửi cả chuỗi.

## 3. Scope

| Scope | Cho phép |
|---|---|
| `tools:read` | xem catalog |
| `jobs:create` | báo giá và tạo job (**tiêu credit**) |
| `jobs:read` | xem job và kết quả |
| `jobs:cancel` | hủy job |
| `uploads:write` | tạo vé upload |
| `artifacts:read` | tải kết quả |
| `credits:read` | xem số dư |
| `usage:read` | xem thống kê sử dụng |
| `webhooks:manage` | quản lý webhook |

Đọc **không** suy ra từ ghi. Khóa không chọn gì nhận mặc định
`tools:read` + `jobs:read` — đủ để khám phá, **không đủ để tiêu tiền**.

Thiếu scope → **403** và có nêu tên scope còn thiếu. Không có credit nào bị
trừ: scope được kiểm ở biên, trước mọi thao tác tiền.

## 4. Lỗi

Mọi lỗi là `application/problem+json` (RFC 9457):

```json
{"type":"/errors/insufficient_credit","title":"Insufficient credit",
 "status":409,"code":"insufficient_credit",
 "detail":"Not enough credit for this call. The balance is checked against the maximum this request could consume, not its typical cost.",
 "instance":"/api/v1/jobs","request_id":"9f1c…",
 "retry":"after_fix","reuse_idempotency_key":true,
 "required_credit":10,"balance":3}
```

> ⚠️ **Sửa 14/09/2026:** ví dụ trên trước đây ghi `"code":"conflict"`. Sai — cửa
> này gửi `insufficient_credit`, và ai nhánh theo `conflict` sẽ bắt nhầm cả lỗi
> idempotency lẫn lỗi giá đổi.

`code` là phần **ổn định** — hãy nhánh theo nó, đừng nhánh theo `detail`.

**Hết credit — cùng một hợp đồng ở MỌI cửa** (`/jobs`, `/chat/completions`,
`/messages`, `/responses`, `/workflows/runs`): mã `insufficient_credit`, 409, và
khi biết số thì kèm `required_credit` + `balance`. Số dư được so với **trần** mà
yêu cầu *có thể* tiêu, không phải chi phí điển hình của nó — nên một yêu cầu
`max_tokens` lớn có thể bị từ chối dù số dư trông vẫn đủ; hạ `max_tokens` xuống
là cách sửa.

**Bận (429)** kèm `retry_after` (giây) và `reason`:

| `reason` | nghĩa |
|---|---|
| `suat` | hết suất thực thi trên GPU |
| `het_cho` | hàng chờ của cổng đã chạm trần |
| `thuong_nguon` | máy chạy model trả 429 |

Ba nguyên nhân đi chung một mã HTTP, nên client điều phối tải hãy nhánh theo
`reason`, và hãy dùng `retry_after` **của phản hồi** thay vì một số cố định.

| code | status | Nghĩa |
|---|---|---|
| `invalid_request` | 400 | input sai, quote sai/hết hạn, tham chiếu upload sai |
| `unauthorized` | 401 | khóa thiếu/sai/thu hồi/hết hạn |
| `forbidden` | 403 | thiếu scope, hoặc khóa bị giới hạn công cụ |
| `not_found` | 404 | không có, **hoặc** không thuộc tài khoản bạn |
| `conflict` | 409 | trùng `Idempotency-Key` khác nội dung; không đủ credit; giá đã đổi |
| `payload_too_large` | 413 | body vượt trần |
| `unprocessable_request` | 422 | body không parse được |
| `rate_limited` | 429 | vượt nhịp — xem `retry_after` |
| `concurrency_limited` | 429 | quá nhiều job đang chạy |
| `quota_exceeded` | 429 | chạm trần credit ngày |
| `read_only` | 503 | API đang tạm khóa ghi |
| `internal_error` | 500 | lỗi phía chúng tôi; gửi `request_id` khi báo lỗi |

`request_id` trùng header `X-Correlation-ID` — luôn kèm nó khi hỏi hỗ trợ.

## 5. Idempotency — điều quan trọng nhất về tiền

**Hai** route bắt buộc header `Idempotency-Key` (8–255 ký tự, nên là một UUID
mỗi lần gọi logic): `POST /api/v1/jobs` và `POST /api/v1/chat/completions`.

Ở cửa job, khoá là hàng rào **thứ hai** — báo giá đã ký sẵn một mức giá. Ở cửa
chat **không có báo giá**, nên khoá là hàng rào **duy nhất** giữa một lần timeout
và việc trả tiền hai lần. Và SDK của OpenAI **không tự gửi** nó — xem mục 1b.

- Cùng khóa + cùng nội dung → trả lại **đúng job cũ**, kèm header
  `Idempotency-Replayed: true`, **không** trừ tiền lần hai. Kể cả khi job cũ đã
  chạy xong.
- Cùng khóa + nội dung khác → **409**.
- Đang xử lý dở → **409**, thử lại sau.

**Quy tắc retry:** timeout thì gửi lại **đúng cùng khóa**. Đổi khóa khi retry là
cách chắc chắn nhất để bị tính tiền hai lần.

## 6. Giá và credit

- `POST /quotes` trả báo giá **đã ký**, gắn với tài khoản + công cụ + **đúng
  input đó**, hạn 15 phút. Đổi input là phải xin báo giá mới.
- Số credit bạn trả **không bao giờ vượt** số đã giữ theo báo giá đã xác nhận.
  Nếu chi phí thực tế của chúng tôi cao hơn, phần chênh là của chúng tôi.
- Job lỗi hoặc bị hủy → hoàn **toàn bộ** phần đã giữ.
- **Bạn trả cho thứ nhận được, không phải thứ đã xin.** Với các công cụ trả về
  nhiều tệp (`count`), số credit tính theo số tệp **thật sự sinh ra được**: xin
  4 ảnh mà chỉ ra 2 thì trả tiền 2 ảnh, phần chênh hoàn ngay khi job xong. Với
  `text.chat`, tính theo token đã sinh, không theo `max_tokens`.
- Giá niêm yết công khai ở `/gia-api`, kèm phiên bản bảng giá. Kết quả job có
  `phien_ban_gia` để bạn đối chiếu đúng bảng đã sinh ra hoá đơn đó.
- Xem số dư: `GET /credits/balance`. Xem chi tiết: `GET /usage`.

## 7. Giới hạn

Mặc định (quản trị viên có thể đổi; xem `/developers`):

| Lớp | Mặc định |
|---|---|
| Request/phút mỗi khóa | 120 |
| Tạo job/phút mỗi khóa | 20 |
| Job đang chạy mỗi tài khoản | 5 |
| Trần credit/ngày | tắt |
| Body JSON | 256 KiB |

429 luôn kèm `retry_after` (giây). Ngân sách theo **khóa**, nên một tích hợp ồn
ào không ảnh hưởng khóa khác của bạn; còn trần job/credit tính theo **tài khoản**
nên đổi khóa không lách được.

## 8. Upload

File đi theo ba bước, và **chỉ trở thành dữ liệu bền vững sau khi job đã giữ
credit** — bỏ dở thì hệ thống tự dọn.

```bash
# 1. Xin vé
curl -s .../api/v1/uploads -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{"tool":"image.generate","field":"image_key","filename":"ref.png",
       "content_type":"image/png","size":20480}'
# → {"id":"…","upload":{"method":"PUT","url":"https://…"}}   (hoặc method POST)

# 2. Gửi bytes tới `upload.url` (PUT thẳng lên object storage khi có)
# 3. Xác nhận
curl -s .../api/v1/uploads/$UPLOAD_ID/confirm -X POST -H "Authorization: Bearer $KEY"
```

Sau đó dùng `id` của vé làm giá trị cho tham số ảnh/video/audio. Kích thước và
định dạng khai lúc xin vé được kiểm lại bằng **bytes thật** khi xác nhận.

## 9. Kết quả

- File → `outputs`: danh sách `{"id": "<artifact id>"}`. Gọi
  `GET /artifacts/{id}` để lấy URL ký **hạn 300 giây**; đừng lưu URL đó.
- Dữ liệu → `result`: chỉ các trường có trong hợp đồng của công cụ.

Artifact chỉ chủ sở hữu đọc được; id của người khác trả 404 y hệt id không tồn
tại.

## 10. Webhook

```bash
curl -s .../api/v1/webhooks -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://ban.example.com/hook","events":["job.succeeded"]}'
# → {"id":"…","secret":"…"}   ← bí mật hiện MỘT LẦN
```

Sự kiện: `job.succeeded`, `job.failed`, `job.cancelled`. Payload chỉ có định
danh và trạng thái — lấy chi tiết qua API.

**Xác minh chữ ký** (bắt buộc):

```python
expected = hmac.new(secret.encode(), f"{timestamp}.{event_id}.".encode() + raw_body,
                    hashlib.sha256).hexdigest()
ok = hmac.compare_digest(f"v1={expected}", signature_header)
```

Header: `X-LTT-Signature`, `X-LTT-Timestamp`, `X-LTT-Event-Id`. Từ chối nếu
timestamp lệch quá 5 phút (chống replay). Chúng tôi thử lại tối đa 6 lần với
giãn cách tăng dần; endpoint của bạn nên **idempotent theo `X-LTT-Event-Id`**.

Chỉ chấp nhận `https` và địa chỉ công khai.

## 11. SDK

- Python: `sdk/python/ltt_public_api.py` — không phụ thuộc thư viện ngoài.
- TypeScript: `sdk/typescript/ltt-public-api.ts` — dùng `fetch`.

Cả hai: GET có retry, **POST tính tiền chỉ retry với cùng `Idempotency-Key`**.

## 12. Sandbox (môi trường test)

Tạo khóa ở tab **Khóa** trong cổng lập trình viên, chọn **Môi trường = Test**.
Khóa test có tiền tố `ltt_tk` thay vì `ltt_sk` — nhìn là biết, không cần tra
cơ sở dữ liệu.

Khóa test đi qua **đúng** chuỗi mà khóa live đi qua: xác thực, scope, catalog,
kiểm tham số, báo giá đã ký, `Idempotency-Key`, hàng đợi job, upload/artifact,
webhook và chữ ký. Chỉ **một** mắt xích bị thay: handler không gọi nhà cung
cấp mà trả kết quả mẫu dựng theo đúng `output_schema` đã công bố của công cụ.
Sandbox mà bỏ qua bất kỳ bước nào ở trên sẽ cho một tích hợp "chạy được" ở đây
rồi vỡ ở production — tệ hơn là không có sandbox.

Hai luật cứng:

- **Khóa test không tiêu được credit.** Không phải "tiêu ít" — nó không bao giờ
  chạm vào sổ credit, nên khóa test lộ ra thì cũng không mất tiền. Báo giá vẫn
  cho biết lời gọi đó *sẽ* tốn bao nhiêu ở live; phần ghi nhận đã tiêu là 0.
  Vì thế trần chi tiêu (ngày, ngân sách) không áp lên khóa test — chúng đo một
  việc không thể xảy ra — còn giới hạn tần suất và số job chạy song song thì
  vẫn áp, vì lời gọi test vẫn dùng máy.
- **Live và test không bao giờ trộn.** Khóa test chỉ thấy job test; khóa live
  chỉ thấy job live. Hỏi chéo trả `404` y hệt job của người khác. Job tạo từ
  giao diện web, và mọi job có trước khi có chế độ này, đều là live.

Job và webhook đều mang trường `mode` (`"live"` hoặc `"test"`), nên một endpoint
nhận webhook phục vụ được cả hai thế giới. Chữ ký, header và hình dạng payload
của webhook test giống hệt live — đó chính là thứ cần thử.

Sandbox **không** chứng minh được **chất lượng** đầu ra. Muốn biết kết quả thật
trông thế nào thì gọi một lần bằng khóa live trên công cụ rẻ nhất; giả vờ ngược
lại là biến mô phỏng thành lời nói dối.

---

## 13. Công cụ đang mở

*(Phần dưới đây sinh tự động từ catalog — đừng sửa tay; chạy
`python tools/build_public_api_docs.py`.)*

<!-- BEGIN GENERATED TOOLS -->

### `image.generate`

Generate one to four images from a text prompt, optionally guided by one reference image.

Execution mode: `ASYNC_JOB`

Scopes: `jobs:create`

Input:

- `prompt` — string, **required**, max length 4000, What to draw. Everything about the image comes from this text.
- `image_key` — string, Optional reference image, given as the id of an upload you confirmed or of an artifact from an earlier job. The result follows its subject and composition.
- `aspect_ratio` — string, one of `16:9`, `9:16`, `1:1`, `4:3`, `3:4`, default 16:9, Shape of the output image.
- `count` — integer, min 1, max 4, default 1, How many images to generate. Each one is charged.

Output: `image_keys` (artifact[]), `prompt` (string)

Contract hash: `6b31aa3ae3590f99`

### `image.ltt`

Generate images with LTT Studios' own model. Supports text-to-image, instruction editing of a reference image, and keeping the same subject across a new scene.

Execution mode: `ASYNC_JOB`

Scopes: `jobs:create`

Input:

- `prompt` — string, **required**, max length 4000, What to draw. Written in any language - the platform translates it to English before the model sees it, because this model only understands English and Chinese. Text you want DRAWN INSIDE the image must be in double quotes; it is kept exactly as written.
- `mode` — string, one of `t2i`, `edit`, `subject`, default t2i, t2i = from text only. edit = change one reference image while keeping the rest. subject = keep the same person or object across a new scene. edit and subject both need image_key and both cost three times more because they take about three times as long; t2i refuses a reference image.
- `count` — integer, min 1, max 4, default 1, How many images to return, 1 to 4.
- `image_key` — string, Reference image, given as the id of an upload you confirmed or of an artifact from an earlier job. Required for edit and subject. Sending it with t2i is REJECTED, not ignored.
- `negative_prompt` — string, max length 1000, What to avoid. Optional.

Output: `image_keys` (artifact[]), `prompt` (string)

Contract hash: `f049eda67a1f475a`

### `image.thumbnail`

Generate one to four YouTube thumbnail background images from a topic. The images carry NO text: the internal model cannot render legible lettering, so add your own title afterwards.

Execution mode: `ASYNC_JOB`

Scopes: `jobs:create`

Input:

- `topic` — string, **required**, max length 2000, What the thumbnail is about. The whole image is generated from this, so be specific about subject and mood.
- `phong_cach` — string, one of `chuyen_nghiep_toi_gian`, `hoat_hinh_cartoon`, `cinematic`, `flat_design`, `3d_render`, `collage`, `retro_vintage`, Visual style of the image itself. The name is Vietnamese because it is a stable identifier, not a label; the values are listed in `enum`.
- `kieu_trend` — string, one of `khuon_mat_cam_xuc`, `so_sanh_truoc_sau`, `bi_an_gay_to_mo`, `huong_dan_tutorial`, `reaction_phan_ung`, `storytelling`, `mui_ten_chi_dan`, Composition pattern — what makes the thumbnail work as a thumbnail (a reacting face, a before/after split, a mystery crop, and so on).
- `aspect_ratio` — string, one of `16:9`, `9:16`, `1:1`, `4:3`, `3:4`, default 16:9, Shape of the output. 16:9 is the YouTube thumbnail shape.
- `count` — integer, min 1, max 4, default 1, How many variations to generate. Each one is charged, so a quote for count=4 costs four times a quote for count=1.

Output: `image_keys` (artifact[]), `prompt` (string)

Contract hash: `6a9ef0c81ac9e3d9`

### `image.upscale`

Upscale an image to four times its original size. Costs 2 credits at the fast preset and 4 at the quality preset.

Execution mode: `ASYNC_JOB`

Scopes: `jobs:create`

Input:

- `image_key` — string, **required**, The image to enlarge, given as the id of an upload you confirmed or of an artifact from an earlier job.
- `preset` — string, one of `fast`, `quality`, default fast, How hard to work on the result. `fast` costs 2 credits, `quality` costs 4 and takes longer.

Output: `image_key` (artifact)

Contract hash: `3e20b273b2ad950a`

### `speech.ltt`

Turn Vietnamese or English text into natural speech. Use a built-in preset voice, or one of your own cloned voices by its stable voice id.

Execution mode: `ASYNC_JOB`

Scopes: `jobs:create`

Input:

- `text` — string, **required**, max length 100000, What to say. Vietnamese, English, or both mixed. Up to 100,000 characters per call. You do NOT need to split long text yourself - it is segmented on sentence boundaries, spoken in several passes and joined back into one continuous audio file. For anything longer, use Projects, where each block is its own pass.
- `voice_id` — string, max length 40, One of your own cloned voices, as returned when you created it. Stays valid across engine upgrades. Leave empty to use a built-in voice.
- `preset` — string, max length 64, A built-in voice name. Ignored when voice_id is given; sending both is rejected.
- `speed` — number, min 0.5, max 2.0, default 1.0, Playback speed. 1.0 is normal. Range 0.5 (half speed) to 2.0 (double speed). Applied as a post-synthesis time-stretch — it does not change how the model speaks, only how fast the output plays. Billing is based on the original duration before speed change. Omit or send 1.0 for normal speed.
- `language` — string, one of `auto`, `vi`, `en`, default auto, Language lane for quality enforcement. 'auto' (default) detects language from the text. 'vi' or 'en' overrides detection. If the detected or declared language does not match the voice's lane, the request is rejected with voice_language_mismatch.

Output: `audio_key` (artifact), `text` (string)

Contract hash: `ebedbcc38dfcd9d6`

### `story.storyboard`

Turn a story brief into a storyboard: one shot description per scene plus a master prompt. Priced by scene count.

Execution mode: `ASYNC_JOB`

Scopes: `jobs:create`

Input:

- `title` — string, **required**, max length 160, Working title of the piece. Used for tone and for naming the result.
- `story` — string, **required**, max length 12000, The story or brief, in prose. This is the source everything else is derived from.
- `scene_count` — integer, min 1, max 20, default 6, How many scenes to produce. This is what the price depends on.
- `aspect_ratio` — string, one of `16:9`, `9:16`, `1:1`, `4:3`, `3:4`, `21:9`, default 16:9, Shape the scenes are written for; it changes framing advice, not the file.
- `style` — string, max length 500, Visual or narrative style to aim for, in your own words.

Output: `storyboard` (object), `master_prompt` (string)

Contract hash: `9c7cfd84114e0c1b`

### `text.chat`

Generate text from a conversation. Handles coding, chat, agentic tool use, summarisation and image reading. OpenAI-compatible message format.

Execution mode: `ASYNC_JOB`

Scopes: `jobs:create`

Input:

- `messages` — array, **required**, Conversation so far, OpenAI format: a list of {role, content}. `content` may be a string, or a list of parts for images.
- `model` — string, one of `ltt-3.8`, `ltt-3.5`, default ltt-3.8, `ltt-3.8` is the deepest model and reads images (171K usable input context). `ltt-3.5` answers faster, costs much less and reads images, with 209K usable input context.
- `max_tokens` — integer, min 1, max 32768, default 32768, Ceiling on generated tokens. Credit is held against this and refunded down to what was actually generated.
- `temperature` — number, min 0.0, max 2.0, Sampling temperature.
- `tools` — array, Function definitions, OpenAI format. The model may answer with `tool_calls`.
- `reasoning_effort` — string, one of `low`, `medium`, `xhigh`, How much the model thinks before answering. Deeper costs more output tokens but can improve hard answers. When omitted, LTT 3.8 uses `xhigh`; LTT 3.5 keeps thinking on with compatible `medium`. Use `low` when you want the shortest answers - do NOT reach for a small `max_tokens` instead: thinking spends that same budget, so the model can reason until it is cut off and return empty content with finish_reason=length.
- `response_format` — object, Constrain the answer's shape. `{"type":"json_object"}` returns bare JSON; `{"type":"json_schema","json_schema":{"name":...,"schema":{...}}} ` forces the answer to match that schema. The constraint is enforced by the decoder, not by prompting, so the output cannot drift out of shape.
- `tool_choice` — string, one of `none`, `auto`, `required`, Whether the model may, must, or must not call a tool: `none`, `auto` or `required`. Without it `tools` is only ever a suggestion.
- `parallel_tool_calls` — boolean, Allow several tool calls in one turn. Support depends on the model's own template.
- `top_p` — number, min 0.0, max 1.0, Nucleus sampling cutoff, in (0..1]. Lower keeps only the likeliest tokens.
- `seed` — integer, Same seed plus same input gives the same answer back, which is what makes a test over this API repeatable.
- `stop` — array, Up to four strings; generation ends as soon as one appears. Four is the ceiling the wire format itself sets, not one we invented.

Output: `content` (string), `tool_calls` (array), `usage` (object)

Contract hash: `9d23c67b17de285f`

### `text.prompt_package`

Turn a story brief into a structured prompt package: one prompt per scene plus a master prompt. Priced by scene count.

Execution mode: `ASYNC_JOB`

Scopes: `jobs:create`

Input:

- `title` — string, **required**, max length 160, Working title of the piece. Used for tone and for naming the result.
- `story` — string, **required**, max length 12000, The story or brief, in prose. This is the source everything else is derived from.
- `scene_count` — integer, min 1, max 20, default 6, How many scenes to produce. This is what the price depends on.
- `duration_seconds` — integer, min 3, max 600, default 30, Target length of the finished piece. Scenes are paced to fit it.
- `aspect_ratio` — string, one of `16:9`, `9:16`, `1:1`, `4:3`, `3:4`, `21:9`, default 16:9, Shape the scenes are written for; it changes framing advice, not the file.
- `style` — string, max length 500, Visual or narrative style to aim for, in your own words.
- `audience` — string, max length 300, Who the piece is for.
- `language` — string, one of `vi`, `en`, default vi, Language the prompts are written in.

Output: `prompt_package` (object), `master_prompt` (string)

Contract hash: `c55834222a3c4a0c`

### `video.generate`

Generate video from a text prompt, optionally guided by reference media. Valid resolution, duration and aspect ratio depend on the model — see each model's `constraints` in GET /api/v1/models.

Execution mode: `ASYNC_JOB`

Scopes: `jobs:create`

Input:

- `prompt` — string, **required**, max length 10000, What the video should show. Write it in any language; longer and more specific prompts give steadier results than short ones.
- `model` — string, one of `seedance-2.0`, `seedance-2.0-fast`, `seedance-2.0-mini`, Which model renders the video. Each one accepts a different set of resolutions and durations — see GET /api/v1/models.
- `resolution` — string, one of `480p`, `720p`, `1080p`, `4k`, Output resolution. Valid values depend on the model — read `constraints.resolutions` for the model you picked. Higher costs more.
- `duration` — integer, one of `4`, `5`, `6`, `8`, `10`, `12`, `15`, Video length in **seconds**, not frames. Valid values depend on the model — read `constraints.durations`. Price scales with it.
- `aspect_ratio` — string, one of `16:9`, `9:16`, `1:1`, `4:3`, `3:4`, `21:9`, Frame shape. Valid values depend on the model — read `constraints.aspect_ratios`.
- `generate_audio` — boolean, default True, Whether the model also generates a soundtrack. Leave it on unless you are supplying your own.
- `camera` — string, one of ``, `static`, `dolly_in`, `tracking`, `orbit`, `aerial`, `handheld`, default , Camera movement. Empty means the model decides.
- `motion` — string, one of ``, `subtle`, `dynamic`, `cinematic`, default , How much the subject moves. Empty means default.
- `visual_style` — string, one of ``, `realistic`, `cinematic`, `anime`, `product`, default , Overall look. Empty means the model follows the prompt alone.
- `seed` — number, min 0, max 2147483647, Repeat a previous result. The same seed with the same input gives the same video; omit it for a new one each time.
- `image_key` — string, Upload id of one reference image to guide the first frame. Optional.
- `image_keys` — array, Upload or artifact ids.
- `video_key` — string, Upload or artifact id.
- `audio_key` — string, Upload or artifact id.

Output: `video_key` (artifact)

Contract hash: `862ceb0dd1589af9`

### `video.subtitle`

Burn a transcript you already have into a video as styled subtitles. Costs 5 credits per minute at standard quality; draft costs 0.6x and high costs 1.5x. The duration is measured from the file you upload, not from anything you send.

Execution mode: `ASYNC_JOB`

Scopes: `jobs:create`

Input:

- `video_key` — string, **required**, The video to subtitle, given as the id of an upload you confirmed or of an artifact from an earlier job.
- `transcript` — array, **required**, The words to burn in, as a list of segments with `start`, `end` and `text`. This tool does not transcribe for you.
- `style_id` — string, one of `default`, `tiktok_bold`, `reels_clean`, `cinematic`, `meme_punch`, `kids_color`, `punchline`, `word_emphasis`, default default, Look of the subtitles: font, colour and outline. Does not change the price.
- `segment_mode` — string, one of `sentence`, `phrase`, `short_form`, `punchline`, `word_emphasis`, default sentence, How the transcript is cut into on-screen lines — whole sentences, shorter phrases, or one emphasised word at a time.
- `quality` — string, one of `draft`, `standard`, `high`, default standard, Encoding quality of the finished video. `draft` costs 0.6 times the standard price and `high` costs 1.5 times.
- `output_format` — string, one of `mp4`, `mkv`, `webm`, default mp4, Container of the finished video file.
- `export_srt` — boolean, default True, Also return the subtitles as a separate .srt file alongside the video.

Output: `video_key` (artifact), `srt_key` (string), `ass_key` (string)

Contract hash: `27bcb797d051e2a0`

### `video.upscale`

Upscale a video to 1080p, 1440p or 4K. Costs 30 credits per minute at 1080p on the fast preset; 1440p costs 1.8x, 4K costs 4x, and the quality preset costs 2.5x. The duration is measured from the file you upload, not from anything you send.

Execution mode: `ASYNC_JOB`

Scopes: `jobs:create`

Input:

- `video_key` — string, **required**, The video to enlarge, given as the id of an upload you confirmed or of an artifact from an earlier job.
- `preset` — string, one of `fast`, `quality`, default fast, How hard to work on the result. `quality` costs 2.5 times as much as `fast` and takes longer.
- `target_height` — integer, one of `1080`, `1440`, `2160`, default 1080, Height of the finished video in pixels. 1440 costs 1.8 times the 1080 price and 2160 costs 4 times.
- `codec` — string, one of `h264`, `hevc`, default h264, Video codec of the finished file. `hevc` makes a smaller file that fewer players open.
- `preview` — boolean, default False, Render only the first 8 seconds, and charge only for them. Use it to check the settings before paying for the whole video.
- `preserve_fps` — boolean, default True, Keep the original frame rate instead of letting the encoder choose one.
- `preserve_audio` — boolean, default True, Copy the original audio track across.
- `stabilize` — boolean, default False, Reduce camera shake. Costs 1.2 times the price without it.
- `smooth_motion` — boolean, default False, Interpolate frames for smoother motion. Costs 2.2 times the price without it, and combines with `stabilize`.

Output: `video_key` (artifact)

Contract hash: `cb03d863f7074888`

### Models

Aliases, not vendor model ids. What a call *costs* comes from `POST /quotes`: price depends on the whole input, so a number printed against a model would be wrong often enough to matter.

| Alias | Capability | Stability | Tools | Notes |
|---|---|---|---|---|
| `ltt-3.5` | text | stable | `text.chat` | Faster and much cheaper, 209K usable input context. Same message format, and it reads images — send them as OpenAI image_url parts. |
| `ltt-3.8` | text | stable | `text.chat` | 171K usable input context. Deepest model: coding, chat, agentic tool use, summarisation. It reads images too — send them as OpenAI image_url parts. |
| `seedance-2.0` | video | stable | `video.generate` | Seedance 2.0 |
| `seedance-2.0-fast` | video | stable | `video.generate` | Seedance 2.0 Fast |
| `seedance-2.0-mini` | video | stable | `video.generate` | Seedance 2.0 Mini |

<!-- END GENERATED TOOLS -->
