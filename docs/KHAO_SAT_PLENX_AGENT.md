# Khảo sát PLENX — canvas workflow + "Workflow Assistant" (agent) — 2026-08-01

> Quan sát **trực tiếp** qua trình duyệt điều khiển bằng Playwright, tài khoản
> người dùng thật đã đăng nhập. Mọi JSON/con số dưới đây **bắt được từ mạng hoặc
> từ localStorage của trang** — không suy đoán. Chỗ nào suy đoán đều ghi rõ.
>
> Mục tiêu: tư liệu để **xây agent của ta**, không sao chép sản phẩm của họ.
> **Không ghi bất kỳ giá trị bí mật nào** (token phiên của họ không chép vào đây).
>
> Bổ sung cho `PHAN_TICH_PLENX.md` (bài đó chỉ khảo sát bố cục/điều hướng).
>
> **Chi phí khảo sát thật:** 2 lượt agent (4 credit/lượt) + 1 lần sinh ảnh (2 credit)
> = **10 credit**.

---

## 0. Kết luận trong một trang

| Phát hiện | Ý nghĩa với ta |
|---|---|
| Agent = **chat session gắn workflow**, có **5 tool**, trả về **SSE** | mô hình tham chiếu trực tiếp cho ta |
| Canvas được **làm phẳng thành VĂN BẢN** rồi nhét vào prompt | rẻ, dễ soi log, không cần schema phía LLM |
| Agent **ghi thẳng vào canvas, KHÔNG có cổng duyệt** | khác FLORA (có Assist mode); ta nên theo FLORA |
| **Mỗi lượt agent = 4 credit**, 1 ảnh 1K = 2 credit | **suy luận đắt gấp đôi sinh ảnh** — phải tính tiền |
| Có **`rag_search` + `get_workflow_patterns`** | agent được **grounding bằng RAG trên kho pattern** |
| Job: **POST run → poll status mỗi 2 giây** | y hệt mô hình HTMX-poll của ta |
| Kết quả job ghi **`api_key_id`** đã dùng | truy vết khoá — `api_pool` của ta chưa làm |
| `retry_count` trong status, quan sát được **= 1** | họ retry ngầm, người dùng không thấy |
| Giá do máy chủ tính, hiện **trước** khi chạy (`💎 2 Generate`) | mô hình "báo giá trước khi tiêu" |
| **KHÔNG có verifier, KHÔNG có vòng tự-chấm-tự-sửa** | **đây là chỗ ta vượt được** |

---

## 1. Kiến trúc trang canvas

Đường dẫn `/apps/pics-workflows/<uuid>`. Trước khi lưu lần đầu, id tạm phía trình
duyệt là `local-wf-<timestamp>-<random>`; workflow chỉ được `POST` tạo thật khi có
thay đổi đầu tiên, không phải lúc bấm "Tạo mới".

### 1.1 Vỏ giao diện
- **Thanh trên:** Back · tên workflow (sửa tại chỗ) · **✓ Saved** (tự lưu, không có nút
  Save) · Generation Logs · Lịch sử phiên bản · Độ sáng · **Export page (JSON)** ·
  **Import vào page hiện tại (JSON)** · Share · avatar.
- **Thanh công cụ trái:** Cursor mode · Add node · Add frame · Layers · Grid · Comment ·
  Sticky Note · Undo/Redo.
- **Trái dưới:** badge `💎 <credit>` · **Pages** (canvas nhiều trang).
- **Phải dưới:** nút **Logs** · nút **Workflow Assistant**.
- **Composer đáy** (hiện khi chọn node): model · tỉ lệ · chất lượng · `💎 <giá> Generate`.
- Tiện ích: Ẩn connection lines · **Tự động sắp xếp nodes** · Keyboard Shortcuts.

### 1.2 Danh mục node

| Nhóm | Node | Trạng thái |
|---|---|---|
| **Content** | Image · Batch Images · Video · Social Video · Text · Audio | bật |
| | Upload | **tắt** |
| **Transformation** | Upscale · Video Upscale · Extract Frames · Merge Video · Merge Image | bật |
| | Enhance · Remove Background · Animation | **tắt** |

Chia theo **Content** (sinh nội dung) vs **Transformation** (biến đổi nội dung đã có).
Node chưa mở thì **hiện mà tắt**, không ẩn.

---

## 2. Data model — lấy từ chính nút "Export page (JSON)"

```json
{
  "version": 2,
  "type": "page",
  "name": "Page 1",
  "nodes": [
    { "id": "node-tour-text-...", "type": "text", "label": "Text",
      "title": "Prompt mẫu", "desc": "Add text content",
      "hasUploadGenerate": true, "frameId": null, "pageId": "page-default",
      "position": { "x": 250, "y": 250 } }
  ],
  "connections": [ { "id": "conn-...", "fromNodeId": "<A>", "toNodeId": "<B>" } ],
  "frames": [], "nodeConfigs": {}, "annotations": [],
  "exported_at": "2026-08-01T08:07:34.611Z"
}
```

- **Đồ thị tách khỏi cấu hình.** `nodes[]` giữ *danh tính + vị trí*; tham số chạy nằm
  riêng ở **`nodeConfigs{}`**. Đổi model không đụng cấu trúc đồ thị.
- `frameId` trên node → frame là quan hệ **cha-con**.
- `pageId` → một workflow có **nhiều page**.
- `version: 2` → đã đổi lược đồ ít nhất một lần, có đánh số.
- Export/Import JSON là **tính năng chính thức** → workflow là dữ liệu di chuyển được.

---

## 3. Bản đồ API

Gốc `https://plenxai.com/api/v1`. Xác thực `Authorization: Bearer <token>` +
`x-workplace-id: <uuid>` (có khái niệm **workplace/workspace**).

### 3.1 Workflow
| Method | Đường dẫn | Việc |
|---|---|---|
| GET | `/apps/builder?page=&per_page=` | danh sách workflow |
| POST | `/apps/builder` | tạo (khi sửa lần đầu) |
| PUT | `/apps/builder/{id}` | **tự lưu** sau mỗi thay đổi |
| DELETE | `/apps/builder/{id}` | xoá |

### 3.2 Model / giá / pool
| Method | Đường dẫn | Việc |
|---|---|---|
| GET | `/models?type=image\|video\|text` | model đang hoạt động |
| GET | `/ai-models/catalog/all` | catalog đầy đủ |
| GET | `/ai-models/{provider_id}/servers` | **pool server** phục vụ model |
| GET | `/models/cost-preview?model_code=&quality=&resolution=&server_id=` | **báo giá trước** |
| GET | `/video-quotas/my` | hạn mức video |

### 3.3 Job
| Method | Đường dẫn | Việc |
|---|---|---|
| POST | `/pics-workflow/run/node/{workflow_id}/{node_id}` | **chạy một node** |
| GET | `/pics-workflow/status/{task_id}?_t=<ms>` | **poll trạng thái** |
| GET | `/queue/active` | hàng đợi đang chạy |
| GET | `/generations?limit=` | lịch sử generation |
| GET | `/folders` | thư mục tài nguyên |

### 3.4 Agent
| Method | Đường dẫn | Việc |
|---|---|---|
| POST | `/chat/sessions?workflow_id=<id>` | mở phiên chat gắn workflow |
| POST | `/chat/sessions/{id}/messages` | gửi lượt → **SSE** |
| GET | `/chat/settings/public` | `{general_bot_enabled, workflow_bot_enabled}` |

### 3.5 Khác
`/notifications/stream?token=` (SSE) · `/notifications/unread-count` ·
`/translations/{namespace}?locale=vi` — i18n **tách namespace**: header, footer,
workplace, textToImage, picsWorkflows, **plenxBot**, auth, common.

---

## 4. GIAO THỨC AGENT — phần giá trị nhất

### 4.1 Payload gửi lên

```json
{
  "content": "[WORKFLOW CONTEXT]\nWorkflow \"Untitled Workflow\" có 2 nodes:\n- node-tour-text-1785571539480 (text): model=default, prompt=\"\"\n- node-tour-image-1785571539481 (image): model=default, prompt=\"\"\nConnections:\n  node-tour-text-1785571539480 → node-tour-image-1785571539481\n\n[USER REQUEST]\nPhân tích workflow hiện tại giúp tôi",
  "provider": "gemini",
  "bot_mode": "workflow"
}
```

Ba điều rút ra:

1. **Canvas làm phẳng thành văn bản có nhãn**, KHÔNG gửi JSON đồ thị. Hai khối
   `[WORKFLOW CONTEXT]` / `[USER REQUEST]`; mỗi node một dòng
   `- <id> (<type>): model=<model>, prompt="<prompt>"`; khối `Connections:` dùng `A → B`.
2. **`provider` là tham số của lượt chat** — chọn được nhà cung cấp LLM, không khoá cứng.
3. **`bot_mode`** — `/chat/settings/public` xác nhận có **hai chế độ**:
   `general_bot_enabled: false` · `workflow_bot_enabled: true`. Cùng một endpoint chat
   phục vụ nhiều loại bot.

### 4.2 Bộ công cụ — 5 tool

Lấy từ nhãn i18n trong bundle JS (`workflowBot.tool_label.*`):

| Tool | Nhãn hiển thị | Việc |
|---|---|---|
| `add_nodes_to_canvas` | ✨ Đang thêm nodes vào canvas... | **ghi node + connection vào canvas** |
| `analyze_video_for_workflow` | 🎬 Đang tải & phân tích video... | tải video về, phân tích, dựng workflow từ nó |
| `get_workflow_patterns` | 🔍 Đang tìm patterns... | tra **kho mẫu workflow** |
| `list_workflows` | 📋 Đang tải workflows... | liệt kê workflow của người dùng |
| `rag_search` | 🔎 Đang tìm kiếm... | **tìm kiếm RAG** |

Front-end còn có nhánh mặc định `⚙️ Đang xử lý ${tool}...` cho tool lạ → **backend có
thể còn tool khác** mà giao diện chưa đặt nhãn.

> **`rag_search` + `get_workflow_patterns` là phát hiện kiến trúc lớn:** agent không tự
> nghĩ ra workflow từ đầu — nó **truy hồi mẫu có sẵn** rồi mới dựng. Đây là cách rẻ và
> ổn định hơn nhiều so với để LLM bịa cấu trúc.

### 4.3 Luồng sự kiện SSE

| Sự kiện | Dữ liệu | Việc |
|---|---|---|
| `tool_call` | `{tool, status:"calling", args:{...}}` | báo agent đang gọi tool + tham số |
| `tool_result` | `{tool, result:{success, error, data}}` | kết quả tool đã **chuẩn hoá** |
| `action_card` | `{type:"add_nodes", nodes:[...], connections:[...]}` | **thẻ hành động để giao diện áp dụng** |
| `token` | `{content:"..."}` | văn bản trả lời, từng mẩu |
| `done` | `{message_id, provider, model}` | kết thúc + **model thật đã dùng** |
| `error` | `{code, message}` | vd `insufficient_credits` |

Model quan sát được: **`gemini-2.5-flash`**. Thời gian: 5,5 giây (phân tích) →
~25 giây (tạo 18 node).

### 4.4 `add_nodes_to_canvas` — tham số LLM sinh ra

```json
{
  "nodes": [
    { "id": "node-img-1", "type": "image", "title": "Lookbook Ảnh 1",
      "x": 100, "y": 100, "prompt": "Professional fashion photography of..." },
    { "id": "node-vid-1", "type": "video", "title": "Lookbook Video 1",
      "x": 500, "y": 100, "prompt": "The model slowly turns her head..." }
  ],
  "connections": [ { "id": "conn-1", "fromNodeId": "node-img-1", "toNodeId": "node-vid-1" } ]
}
```

**Chuẩn hoá phía máy chủ** — `tool_result.data` trả về dạng chuẩn khác hẳn:

```json
{ "type": "add_nodes",
  "nodes": [ { "id": "node-img-1", "type": "image", "title": "Lookbook Ảnh 1",
               "position": { "x": 100, "y": 100 },
               "config": { "prompt": "..." } } ],
  "connections": [...], "node_count": 18 }
```

> **Bài học thiết kế quan trọng:** LLM được phép sinh **lược đồ PHẲNG, dễ viết**
> (`x`, `y`, `prompt` ở cấp trên cùng); **máy chủ chuẩn hoá** sang lược đồ lưu trữ
> (`position{}`, `config{}`). Thứ tự khoá trong JSON của LLM lộn xộn tuỳ tiện — họ
> không quan tâm. Đừng bắt LLM sinh đúng lược đồ lưu trữ.

Kết quả thật đo được: yêu cầu *"Tạo quy trình lookbook 9 ảnh + video"* → **18 node
(9 ảnh + 9 video) + 9 connection**, xếp lưới `x=100` (ảnh) / `x=500` (video),
`y` cách nhau 350. Mỗi node có prompt tiếng Anh viết sẵn khá chi tiết. Sau đó
`PUT /apps/builder/{id}` tự lưu.

### 4.5 Cơ chế dự phòng khi LLM không gọi đúng tool

Trong bundle JS có nhánh: **nếu hết stream mà chưa nhận `action_card`**, front-end tự
đi tìm JSON trong phần văn bản — thử `` ```json ``, rồi tìm chuỗi `"add_nodes"`, rồi
**đếm ngoặc để cắt đúng khối JSON**, `JSON.parse`, và áp dụng.

> Đây là chi tiết thực chiến đáng giá: **họ không tin LLM luôn gọi tool đúng cách.**
> Ta cũng nên có đường lui tương tự.

### 4.6 Điều agent này KHÔNG làm

- **Không có cổng duyệt.** Node được ghi thẳng vào canvas, không hỏi, không báo giá
  trước. (FLORA có *Assist mode* bắt duyệt kèm chi phí — PLENX **không**.)
- **Không tự chạy generation.** Nó chỉ dựng canvas; người vẫn phải bấm Generate.
- **Không đặt model cho node** — node mới để `model=default`.
- **Không có verifier**, không chấm kết quả, không có vòng lặp tự sửa.

→ Đây là **trợ lý dựng workflow**, **chưa phải agent tự-kiểm-tra-tự-sửa**.

---

## 5. GIAO THỨC JOB — chạy một node

### 5.1 Nộp job

```
POST /api/v1/pics-workflow/run/node/{workflow_id}/{node_id}
```
```json
{ "node_config": { "model": "gem-pix-2", "aspectRatio": "9:16", "quality": "1k",
                   "prompt": "...", "serverId": "dd597ae5-..." },
  "input_refs": null }
```
Trả về:
```json
{ "success": true, "execution_id": "8a9b481b-94d", "node_id": "node-img-1",
  "status": "queued", "type": "image",
  "task_id": "e593b21f-b318-4857-a846-ed75e6a9f8c3", "credit_cost": 2.0 }
```

- **Hai id:** `execution_id` (lần chạy node này) và `task_id` (tác vụ sinh nội dung).
- **`credit_cost` trả về ngay khi nộp** — máy chủ xác nhận số tiền thật sẽ trừ.
- **`serverId`** đi trong `node_config` → client chọn được server/pool cụ thể.
- **`input_refs`** — chỗ truyền tài nguyên đầu vào (ảnh tham chiếu); `null` khi không có.

### 5.2 Theo dõi — POLL, không phải SSE

```
GET /api/v1/pics-workflow/status/{task_id}?_t=<epoch_ms>
```
Nhịp đo được: **~2,07 giây/lần** (`_t` là chặn cache).

```json
{ "success": true, "task_id": "...", "status": "queued",
  "task_type": "image/gem-pix-2",
  "created_at": "...", "started_at": null, "completed_at": null,
  "result": null, "error": null, "error_message": null,
  "is_nsfw": false, "generation_id": null, "retry_count": 0 }
```

### 5.3 Khi xong

```json
{ "status": "completed", "task_type": "image/gem-pix-2",
  "created_at":   "2026-08-01T08:21:55.727691+00:00",
  "started_at":   "2026-08-01T08:21:57.929056+00:00",
  "completed_at": "2026-08-01T08:22:33.330029+00:00",
  "result": {
    "success": true,
    "result_url": "https://images.plenxai.com/cdn-cgi/imagedelivery/<acct>/<img>/format=jpeg,quality=100",
    "image_urls": ["..."],
    "model": "gem-pix-2",
    "generation_id": "6eac80c6-...",
    "media_id": "ce9affc0-...",
    "api_key_id": "aef74ee9-...",
    "project_number": "1754ebab-...",
    "is_nsfw": false
  },
  "error": null, "error_message": null, "is_nsfw": false,
  "generation_id": "6eac80c6-...", "retry_count": 1 }
```

Đo được từ mốc thời gian: **chờ hàng đợi 2,2 giây · sinh ảnh 35,4 giây · tổng 37,6
giây** (giao diện Logs ghi 38,7 giây).

Bốn chi tiết đáng lấy:

- **`api_key_id` được ghi vào kết quả** → truy được *ảnh này do khoá nào tạo ra*.
  `api_pool.py` của ta **chưa** ghi lại điều này lên job.
- **`retry_count: 1`** → đã retry một lần rồi mới thành công, **người dùng không hề
  biết**. Retry ngầm là hành vi mặc định của họ.
- **`error` và `error_message` là hai trường tách nhau** (mã lỗi vs mô tả).
- **`is_nsfw`** xuất hiện ở **cả hai cấp** (task và result) → kiểm duyệt nội dung là
  thuộc tính hạng nhất, không phải phần phụ.

### 5.4 Phục vụ file: Cloudflare Images

`https://images.plenxai.com/cdn-cgi/imagedelivery/<account>/<image_id>/<biến_thể>`

Biến thể quan sát được:
- `format=jpeg,quality=100` — bản đầy đủ
- `w=360,h=640,fit=cover` — thumbnail dọc
- `w=400,quality=70,format=auto` — thumbnail danh sách

→ Họ **không tự phục vụ file**: đẩy hết sang Cloudflare Images, biến thể sinh theo URL.
Đây là câu trả lời của họ cho bài toán **H10 (R2) của ta**.

---

## 6. Model registry

Số model đang hoạt động: **image = 11 · video = 23 · text = 3**.

```json
{ "name": "Veo3.1 Quality", "provider_id": "flow-veo3", "pool_id": "00f758a9-...",
  "type": "video", "is_active": true, "is_uncensored": false, "is_accessible": true,
  "config": { "pool_code": "flow_veo3", "task_type": "video/flow-veo3",
              "qualities": ["720p","1080p","4K"], "aspect_ratios": ["16:9","9:16"],
              "durations": [4,6,8], "default_ratio": "9:16", "default_quality": "720p" } }
```

Biến thể `config` gặp được:
- `Kling Motion Control`: `min_duration: 3`, `max_duration: 30`,
  `duration_type: "range"`, `supports_reference: true`
- `Nano Banana Pro` (image): `gen_type: "text2image"`, `supports_reference: true`,
  `qualities: ["1k","2k","4k"]`, 6 tỉ lệ
- `Nano Banana Full` (image): `pool_code: "gemini_pro_3"`, **10** tỉ lệ

Điểm cần nhớ:
- **`config` CHÍNH LÀ schema tham số.** Composer dựng từ đây → đổi model thì tỉ lệ/
  thời lượng/chất lượng đổi theo. Không hardcode ở front-end.
- **`task_type` = `"<loại>/<provider_id>"`** — namespace job (của ta: `<app>.<hành động>`).
- **`pool_id` + `pool_code`** — mỗi model trỏ tới một pool khoá/máy chủ, đúng vai trò
  `platform_core/api_pool.py`.
- **`is_accessible` tính phía máy chủ** theo gói; giao diện chỉ vẽ ổ khoá 🔒.
- `is_uncensored` — cờ chính sách nội dung ở mức model.

Model ảnh trên composer: Nano Banana Pro · Nano Banana 2 · Flux 2 Pro🔒 ·
Seedream 5 Lite🔒 · Kling 01 Image🔒 · Seedream 4.5 · Grok Image · Kling 3.0 Omni ·
GPT Image 2 · Seedream 5 Pro🔒 · Nano Banana Full  (🔒 = khoá theo gói)

---

## 7. Mô hình giá

| Trường hợp | Kết quả `cost-preview` |
|---|---|
| Ảnh `gem-pix-2` 1K | `{"credit_cost":"2.0000","cost_type":"per_gen","source":"server_pricing"}` |
| Video `flow-veo3` 1080p (duration=8) | `{"credit_cost":30,"cost_type":"per_gen","source":"model_pricing"}` |
| Một lượt chat agent | **4.0 credit** (từ thông báo lỗi `insufficient_credits`) |

Nhận xét:
- **Hai nguồn giá:** `server_pricing` (giá theo *server/pool* cụ thể) và `model_pricing`
  (giá theo *model*). Tức **cùng một model chạy trên pool khác nhau có giá khác nhau**.
- `cost_type` cả hai trường hợp đều `per_gen` — **kể cả video có `duration`**. Chưa gặp
  `per_second`; **không kết luận là không tồn tại**, chỉ là chưa quan sát được.
- Kiểu dữ liệu **không nhất quán**: ảnh trả chuỗi `"2.0000"`, video trả số `30`.
- Credit của họ là **thập phân**; của ta là **số nguyên**.
- Cache ở localStorage TTL **7.200.000 ms = 2 giờ**.
- Giá hiển thị thẳng trên nút hành động: `💎 2 Generate`.

**Tỉ lệ đáng chú ý: một lượt suy luận của agent (4) = hai lần sinh ảnh 1K (2×2).**

---

## 8. Nhật ký & lịch sử

- **Generation Logs** — bảng theo từng lần chạy node:
  `Lookbook Ảnh 1 | Thành công | 15:24:12 | gem-pix-2 | 38.7s | Hoàn thành`
  Có bộ lọc **Tất cả / Thành công / Thất bại** kèm số đếm.
- **Lịch sử phiên bản** — có nút **Khôi phục**.
- `/generations?limit=` — thư viện kết quả:

```json
{ "id": "...", "prompt": "...", "model": "gem-pix-2", "type": "app",
  "result_url": "...", "thumbnail_url": "...", "aspect_ratio": "9:16",
  "resolution": "1k", "references_urls": [], "is_nsfw": false, "is_public": false,
  "created_at": "...", "workplace_id": "...", "is_liked": false,
  "folder_ids": [], "metadata": null, "thumbnail": "..." }
```

`type` phân biệt **nguồn gốc**: `"app"` (chạy từ canvas) vs `"image"` (chạy từ tool
ảnh thường). `is_public` + `is_liked` + `folder_ids` → phần cộng đồng/thư viện.

- `/queue/active` → `{"success":true,"tasks":[],"count":0}`

---

## 9. Quy trình sử dụng — theo onboarding CỦA CHÍNH HỌ (10 bước)

1. **Tên Workflow** — click để đổi; **tự lưu**, không cần bấm Save.
2. **Text Node — prompt tái sử dụng** — viết prompt **một lần**, nối đến **nhiều** node
   Image/Video.
3. **Nội dung Text Node — 2 chế độ:** ✎ *Add manually* · ✦ *Generate* (AI tự viết).
4. **Image Node** — tạo bằng AI hoặc upload; click node để mở **thanh cấu hình dưới**.
5. **Upload hoặc Generate** — upload từ máy/Library/dán `Ctrl+V`; **nếu có Text Node nối
   vào thì prompt tự kế thừa**.
6. **Kết nối node** — Text → Image nghĩa là prompt tự chèn khi generate.
7. **Thêm node mới** — Image/Video · Text · Upscale.
8. **Frame — nhóm node** — **▶ Play trên Frame chạy tất cả node bên trong cùng lúc**;
   di chuyển Frame kéo theo node con.
9. **Thanh công cụ** — Zoom · Chat · Tài khoản (credits & cài đặt).
10. **Mẹo nhanh** — `Ctrl+C/V` copy node · **`Ctrl+V` ảnh → tự tạo Image node** · giữ
    chuột giữa để pan · `Delete/Backspace` xoá node/connection.

Ba cơ chế đáng lấy:
- **Prompt là tài nguyên chia sẻ** (Text Node) + **kế thừa theo cạnh**. Sửa một chỗ,
  mọi node hưởng.
- **Frame = đơn vị chạy hàng loạt** → nguyên thuỷ **fan-out**.
- **Tự lưu + lịch sử phiên bản** → không có trạng thái "chưa lưu".

---

## 10. Đối chiếu với nền tảng ta

| Hạng mục | PLENX | LTTSTUDIOSAPP | Nhận định |
|---|---|---|---|
| Pool khoá API | `pool_id`/`pool_code` mỗi model | `api_pool.chon_key` + cascade + rpm/tpm + cooldown | **ta ngang/hơn** |
| Ghi khoá đã dùng lên kết quả | **`api_key_id` trong result** | ❌ | **ta THIẾU** (dễ thêm) |
| Provider registry | `/ai-models/catalog/all` | `providers.py` | ngang |
| **Schema tham số model** | **`config{}`** đầy đủ, UI dựng từ đó | ❌ form cứng mỗi app | **ta THIẾU** |
| Báo giá trước khi chạy | `cost-preview` + `💎 n Generate` | ❌ | **ta THIẾU** |
| Giá theo pool | `source: server_pricing` | ❌ giá theo hàm app | ta thiếu (chưa cần) |
| Đơn vị credit | thập phân | **số nguyên** | ta đơn giản hơn |
| Hàng đợi job | `/queue/active`, poll 2s | bảng `jobs` + `SKIP LOCKED` + reclaim orphan | **ta hơn** (bền, resume) |
| Retry | `retry_count`, ngầm | `attempts`/`max_attempts` + backoff luỹ thừa | **ta hơn** |
| Quyết toán / hoàn tiền | không quan sát được | giữ chỗ→quyết toán→hoàn, append-only | **ta hơn** |
| Kiểm duyệt nội dung | `is_nsfw` hai cấp + `is_uncensored` | ❌ | **ta THIẾU** |
| Phục vụ file | **Cloudflare Images**, biến thể theo URL | LocalStorage, stream qua Tunnel | **ta THIẾU** (= H10) |
| Đồ thị nhiều bước | canvas node/connection/frame/page | ❌ | **ta THIẾU** |
| Fan-out | ▶ trên Frame | ❌ `claim()` 1 job, không `parent_id` | **ta THIẾU** |
| Agent | 5 tool + SSE + RAG pattern | ❌ | **ta THIẾU** |
| Cổng duyệt trước khi tiêu | ❌ **họ không có** | ❌ | cả hai thiếu — **ta nên có** |
| Verifier / tự sửa | ❌ **họ không có** | ❌ | **chỗ ta vượt được** |
| Streaming | SSE cho chat, poll 2s cho job | HTMX poll 2s | ta thiếu SSE cho chat |
| Tính tiền lượt agent | **4.0 credit/lượt** | ❌ chưa có khái niệm | **ta THIẾU** |
| i18n | tách namespace, VI/EN/TH/JA | tiếng Việt cứng | chưa cần |
| Workspace nhiều chỗ làm | `x-workplace-id` | ❌ | chưa cần |

---

## 11. Mười hai bài học mang sang thiết kế agent của ta

1. **Làm phẳng ngữ cảnh thành văn bản có nhãn**, đừng ép LLM đọc JSON đồ thị.
   Mẫu `[WORKFLOW CONTEXT]` / `[USER REQUEST]` vừa rẻ vừa dễ soi log.
2. **Cho LLM sinh lược đồ PHẲNG, máy chủ chuẩn hoá.** Đừng bắt LLM sinh đúng lược đồ
   lưu trữ — nó sẽ sai thứ tự khoá, thiếu tầng lồng nhau.
3. **Luôn có đường lui phân tích JSON từ văn bản** khi LLM không gọi tool đúng cách.
   Họ có, và đó là kinh nghiệm thực chiến.
4. **RAG trên kho mẫu workflow** (`get_workflow_patterns` + `rag_search`) — agent truy
   hồi mẫu rồi mới dựng, thay vì bịa từ đầu. Rẻ hơn và ổn định hơn nhiều.
5. **Tính tiền cho chính lượt suy luận.** 4 credit/lượt, gấp đôi một lần sinh ảnh. Agent
   nhiều bước → **chi phí suy luận có thể vượt chi phí sinh nội dung**.
6. **Báo giá trước khi tiêu**, hiện ngay trên nút hành động.
7. **Giá do máy chủ tính** (`source: server_pricing`) — khớp nguyên tắc "mọi logic ở máy
   chủ" (Q18) của ta.
8. **Tách đồ thị khỏi cấu hình** (`nodes[]` vs `nodeConfigs{}`). Kế hoạch agent sinh ra
   cũng nên tách *bước* khỏi *tham số bước*.
9. **`config` của model là schema tham số** — nên thêm vào `platform_core/providers.py`
   (`qualities`, `aspect_ratios`, `durations`, `supports_reference`, mặc định). Đây là
   điều kiện để agent **tự chọn tham số hợp lệ** thay vì đoán.
10. **Ghi `api_key_id` vào kết quả job** — truy vết khoá nào tạo ra sản phẩm nào. Rẻ,
    làm được ngay, giá trị cao khi gỡ rối và kế toán.
11. **`is_nsfw` là công dân hạng nhất**, không phải phần phụ. Bán cho khách ngoài thì
    kiểm duyệt phải nằm trong lược đồ job từ đầu.
12. **Điều PLENX CHƯA có, và là chỗ ta vượt:** không cổng duyệt, không verifier, không
    vòng tự-chấm-tự-sửa. Đúng yêu cầu "mặt sai thì tự tạo lại" thì **họ chưa làm**.

---

## 12. Khoảng trống còn lại của khảo sát

- ❌ Chưa gặp `cost_type` nào ngoài `per_gen` (đoán có `per_second`, **chưa xác minh**).
- ❌ Chưa quan sát chế độ `general` bot (đang tắt: `general_bot_enabled: false`).
- ❌ Chưa thử `analyze_video_for_workflow`, `get_workflow_patterns`, `rag_search`,
   `list_workflows` — mới chỉ thấy tên và nhãn.
- ❌ Chưa mở tham số node **Batch Images** và **Social Video**.
- ❌ Chưa chạy **Frame ▶** để xem giao thức fan-out (chạy nhiều node cùng lúc).
- ❌ Chưa biết họ có giữ chỗ credit trước khi chạy hay trừ sau khi xong.

---

## 13. Cách tái lập

```bash
playwright-cli -s=plenx open --headed --persistent --browser=chrome "https://plenxai.com"
playwright-cli -s=plenx resize 1920 1080
```

Profile lưu ở `%LOCALAPPDATA%\ms-playwright\daemon\<hash>\ud-plenx-chrome`, đã đăng
nhập sẵn. Sau đó:

```bash
playwright-cli -s=plenx requests            # bản đồ API
playwright-cli -s=plenx request-body <n>    # payload gửi lên
playwright-cli -s=plenx response-body <n>   # SSE / JSON trả về
```

Trên Git Bash phải `export MSYS_NO_PATHCONV=1` trước khi dùng `--regex`, nếu không MSYS
biến regex thành đường dẫn.

**Cảnh báo chi phí:** lượt chat agent **4 credit**, sinh ảnh 1K **2 credit**, video
Veo3 1080p **30 credit**. Đừng gọi thử lung tung.
