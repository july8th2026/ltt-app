# LTT Studios Public API — hướng dẫn cho lập trình viên

Bản này viết cho người tích hợp. Quy tắc nội bộ ở `KERNEL_V1.md`,
`SECURITY_MATRIX_V1.md`, `DEVELOPER_KEYS_V1.md`.

Đường dẫn chuẩn: `/api/v1` trên `https://app.lttstudios.com`.
Spec máy đọc: `GET /api/v1/openapi.json`.

---

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
{"type":"/errors/conflict","title":"Conflict","status":409,"code":"conflict",
 "detail":"Not enough credit for this call.","instance":"/api/v1/jobs",
 "request_id":"9f1c…","required_credit":10,"balance":3}
```

`code` là phần **ổn định** — hãy nhánh theo nó, đừng nhánh theo `detail`.

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

`POST /api/v1/jobs` **bắt buộc** header `Idempotency-Key` (8–255 ký tự, nên là
một UUID mỗi lần gọi logic).

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

## 12. Sandbox

**Chưa có sandbox.** Mọi lời gọi chạy trên hạ tầng thật và tiêu credit thật.
Cách thử an toàn: dùng công cụ rẻ nhất, `count` nhỏ nhất, và đặt trần credit
ngày cho tài khoản thử. Chúng tôi không giả vờ có môi trường thử nghiệm khi
chưa dựng nó.

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

- `prompt` — string, **required**, max length 4000
- `image_key` — string, Upload or artifact id.
- `model` — string, one of `enhanced`, `pro`, `standard`, `standard-lite`, Model alias.
- `aspect_ratio` — string, one of `16:9`, `9:16`, `1:1`, `4:3`, `3:4`, default 16:9
- `count` — integer, min 1, max 4, default 1

Output: `image_keys` (artifact[]), `prompt` (string)

### `image.thumbnail`

Generate one to four YouTube thumbnail images from a topic, with optional title text, style and language.

Execution mode: `ASYNC_JOB`

Scopes: `jobs:create`

Input:

- `topic` — string, **required**, max length 2000
- `title` — string, max length 200
- `subtitle` — string, max length 200
- `text_style` — string, one of `bold_impact`, `clean_minimal`, `dramatic_gold`, `neon_glow`, `street_art`
- `phong_cach` — string, one of `chuyen_nghiep_toi_gian`, `hoat_hinh_cartoon`, `cinematic`, `flat_design`, `3d_render`, `collage`, `retro_vintage`
- `kieu_trend` — string, one of `khuon_mat_cam_xuc`, `so_sanh_truoc_sau`, `bi_an_gay_to_mo`, `listicle_numbered`, `huong_dan_tutorial`, `reaction_phan_ung`, `storytelling`, `mui_ten_chi_dan`, `text_heavy_chu_lon`
- `ngon_ngu` — string, one of `tieng_viet`, `english`, `japanese`, `korean`, `chinese`
- `aspect_ratio` — string, one of `16:9`, `9:16`, `1:1`, `4:3`, `3:4`, default 16:9
- `count` — integer, min 1, max 4, default 1

Output: `image_keys` (artifact[]), `prompt` (string)

### `image.upscale`

Upscale an image to four times its original size. Costs 2 credits at the fast preset and 4 at the quality preset.

Execution mode: `ASYNC_JOB`

Scopes: `jobs:create`

Input:

- `image_key` — string, **required**, Upload or artifact id.
- `preset` — string, one of `fast`, `quality`, default fast

Output: `image_key` (artifact)

### `story.storyboard`

Turn a story brief into a storyboard: one shot description per scene plus a master prompt. Priced by scene count.

Execution mode: `ASYNC_JOB`

Scopes: `jobs:create`

Input:

- `title` — string, **required**, max length 160
- `story` — string, **required**, max length 12000
- `scene_count` — integer, min 1, max 20, default 6
- `aspect_ratio` — string, one of `16:9`, `9:16`, `1:1`, `4:3`, `3:4`, `21:9`, default 16:9
- `style` — string, max length 500

Output: `storyboard` (object), `master_prompt` (string)

### `text.prompt_package`

Turn a story brief into a structured prompt package: one prompt per scene plus a master prompt. Priced by scene count.

Execution mode: `ASYNC_JOB`

Scopes: `jobs:create`

Input:

- `title` — string, **required**, max length 160
- `story` — string, **required**, max length 12000
- `scene_count` — integer, min 1, max 20, default 6
- `duration_seconds` — integer, min 3, max 600, default 30
- `aspect_ratio` — string, one of `16:9`, `9:16`, `1:1`, `4:3`, `3:4`, `21:9`, default 16:9
- `style` — string, max length 500
- `audience` — string, max length 300
- `language` — string, one of `vi`, `en`, default vi

Output: `prompt_package` (object), `master_prompt` (string)

<!-- END GENERATED TOOLS -->
