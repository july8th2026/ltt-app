> LƯU TRỮ 2026-09-19 — không còn đúng hệ thống hiện tại; thay bằng: docs/PUBLIC_API/. Chỉ đọc để hiểu lịch sử.

# Phase 07 — Nối chuỗi: kết quả job này làm đầu vào job kia

**Thi hành 2026-08-30.**

> **Kết luận sớm:** thứ chặn "dây chuyền" không phải thiếu công thức, mà là
> **thiếu một nửa hợp đồng**. Mã đã tự ghi điều đó và chờ đúng phase này.

---

## 1. Observed current truth

`docs/PUBLIC_API/RECIPES.md` đã có **9 mục** — cURL, PowerShell, n8n, Make,
backend thuần, xác minh webhook, phục hồi khi tiến trình chết. Nhưng cả 9 đều là
**một lệnh gọi**. Không mục nào nối job A sang job B.

Lý do không phải ai đó quên viết. `platform_core/public_api/invocation.py` ghi
thẳng, và nó gọi đúng tên phase này:

```
# Media parameters take an upload/artifact id. Resolving one to a storage key is
# Prompt 07's job; until then a tool that needs media simply cannot be called,
# which is better than inventing a half-contract now.
```

Nửa **upload** đã có. Nửa **artifact** thì chưa ai viết.

### Hệ quả đo được

`resolve_upload_reference` chỉ tra `UploadSession`, lọc theo `user_id` **và**
`app_slug`. Nên chuỗi bị chặn **hai lớp**:

| Lớp | Nghĩa |
|---|---|
| artifact id không phải upload id | `400 unknown upload id` |
| upload khoá theo **một app** | ngay cả tải lên lại cũng phải tạo vé cho app đích |

⇒ Muốn đưa video vừa sinh sang `video.upscale`, khách phải **tải về rồi tải lên
lại** — một tệp hàng trăm MB đi ra rồi đi vào, qua Cloudflare, chỉ để nằm lại
đúng chỗ nó đang nằm.

---

## 2. Chosen implementation

Tham số media nay nhận **hai** hình dạng:

| Id | Là gì | Xử lý |
|---|---|---|
| `up_…` | tệp khách gửi lên | `UploadSession` → **dời** sang khoá bền vững của job mới |
| `<job>.<field>.<index>` | đầu ra của một job trước | `ThamChieuArtifact` → **tham chiếu**, tệp không đi đâu |

### 2.1 ⛔ Artifact **không được** đối xử như upload

`promote_media` **dời** một upload. Làm thế với artifact là **lấy mất kết quả
của job trước**: khách vẫn cầm id đó, vẫn tải được nó, và lần tải sau sẽ **404**.

Nên `ThamChieuArtifact` là một kiểu riêng, và `promote_media` `continue` trước
khi chạm `upload_sessions.promote`. Có test chốt cả thứ tự đó.

### 2.2 Một ràng buộc **được nới**, và phải nói rõ

Upload khoá theo `app_slug` — một vé tạo cho app A không dùng được ở app B, để
một vé bị lộ không mở được cả nền tảng.

**Artifact cố ý không bị khoá như vậy.** Đó chính là mục đích: kết quả của
`taovideo` phải đưa được sang `upscalevideo`.

⭐ Hai cổng còn lại **không** nới, và chúng mới là thứ giữ an toàn:

| Cổng | Chặn gì |
|---|---|
| **Chủ sở hữu** — `job.user_id == principal.user_id` | ai đoán được một job id cũng không đọc được kết quả người khác |
| **Danh sách trắng hợp đồng đầu ra** — `storage_key_for(..., tool=…)` | một tệp trung gian handler tình cờ để lại trong `result` không thành đầu vào gọi được chỉ vì ai đó đoán ra id |

🔴 **Và cổng thứ hai suýt bị tôi để hở.** `storage_key_for(..., tool=None)`
**bỏ qua** danh sách trắng. Bản đầu của tôi tra ToolSpec của job sinh ra artifact,
và khi không tìm thấy thì… đi tiếp. Tức một job mà ta không tra lại được ToolSpec
sẽ biến **mọi thứ** handler để trong `result` — bản nháp, tệp trung gian, dump gỡ
lỗi — thành đầu vào gọi được. Nay không tìm thấy tool thì **từ chối**.

### 2.3 Mọi lỗi trả **cùng một câu**

```
400  <param>: unknown media id.
```

Một artifact của tài khoản khác và một id bịa phải **không phân biệt được** —
nếu khác nhau, chính thông điệp lỗi thành một cổng dò id. Có test đếm số nhánh
dùng cùng chuỗi đó.

---

## 3. Công thức

### Recipe A — sinh video → nâng cấp

```
POST /api/v1/quotes   {"tool":"video.generate", "input":{...}}
POST /api/v1/jobs     {"tool":"video.generate", "quote":…, "input":{...}}
                      Idempotency-Key: <moi lan mot khoa>
GET  /api/v1/jobs/{id}          -> doi status = succeeded
                                -> outputs[0].id = "job_abc.video_key.0"

POST /api/v1/quotes   {"tool":"video.upscale",
                       "input":{"video_key":"job_abc.video_key.0", ...}}
POST /api/v1/jobs     ...
GET  /api/v1/artifacts/{id}/content        -> tai ban cuoi
```

**Không tải về giữa chừng.** Đó là cả điểm của phase này.

### Recipe B — ảnh tham chiếu → video

`image.ltt` hoặc `image.generate` sinh ảnh → lấy `outputs[0].id` → đưa thẳng vào
`video.generate` ở tham số `image_key`.

⚠️ `video.generate` hiện **chỉ mở** `image_key` (một ảnh). Bốn đường tham chiếu
còn lại (`image_keys`, `video_key`, `audio_key`, `refs`) **hoãn có ghi** — xem
`04_SEEDANCE_API.md` §2.4.

### Recipe C — video → phụ đề

`video.subtitle` nhận `video_key` là artifact id, **và** `transcript` bạn tự
mang tới. ⛔ Tool này **không phiên âm hộ**.

### Recipe D — chuỗi đầy đủ

```
brief -> text.chat -> image.ltt -> video.generate -> video.upscale -> video.subtitle
```

⚠️ Prompt 07 đề nghị bước đầu dùng **Codex**. Tôi dùng **`text.chat`** (model
nhà) thay thế — `DEVIATION_WITH_EVIDENCE`: Codex đang `BLOCKED_POLICY`
(`05_CODEX_AUTH_BRIDGE.md` §6), còn `text.chat` **đang mở và đang phục vụ**.
Chính Prompt 07 cho phép: *"Không bắt buộc tất cả capability phải từ Codex."*

---

## 4. Độ tin cậy — thứ công thức phải xử

| Tình huống | Cách xử |
|---|---|
| `429` | đọc `Retry-After`, **đừng** thử lại ngay |
| job `failed`/`cancelled` | trạng thái cuối, không thử lại — đọc `error` |
| quote hết hạn | xin quote mới; **không** dùng lại quote cũ |
| thiếu credit | `402`, nạp rồi gọi lại |
| tiến trình bạn chết | `Idempotency-Key` → gọi lại **cùng khoá** trả về job cũ |

⛔ **Đừng thử lại mù một thao tác có tác dụng phụ** khi không giữ đúng khoá
idempotency — đó là đường thu tiền hai lần.

---

## 5. Deviations

**`DEVIATION_WITH_EVIDENCE`** ×2:

1. Bước đầu Recipe D dùng `text.chat` thay Codex (Codex `BLOCKED_POLICY`).
2. Prompt 07 nói *"tạo recipes + helper client"*; SDK đã có, `RECIPES.md` đã có 9
   mục. Việc thật không phải viết thêm công thức mà là **mở khoá nửa hợp đồng
   còn thiếu** — không có nó thì mọi công thức chuỗi đều là văn tả một thứ không
   gọi được.

**`BLOCKED_EXTERNAL`** — chưa chạy chuỗi thật đầu-tới-cuối bằng credential thật;
`video.generate` cũng chưa được operator bật. Không giả PASS.

---

## 6. Còn lại

| # | Việc |
|---|---|
| 1 | Chạy Recipe A đầu-tới-cuối ở test-mode qua toàn bộ bề mặt công khai |
| 2 | Link `RECIPES.md` → mục nối chuỗi |
| 3 | Mở dần bốn ref còn hoãn của `video.generate` khi chứng minh được ownership |
