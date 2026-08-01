# Đối soát app hiện có ↔ yêu cầu của Agent

> Bản đo lịch sử lập **2026-08-01 16:40**. Từ 2026-08-02 code đã có thêm R2
> hoàn chỉnh, media helper, autosubvideo, upscalevideo, taoclipngan và chataistudio.
> **Số liệu này có hạn dùng ngắn** — phiên di trú đang chạy song song. Đo lại bằng
> [`04_KIEM_CHUNG_CODE.md`](04_KIEM_CHUNG_CODE.md) trước khi dùng.
>
> Bằng chứng: trong đúng phiên khảo sát này, app `seedance` đã bị **đổi tên thành
> `taovideo`** giữa hai lần đo cách nhau vài phút. Đó là lý do giao thức đo tồn tại.

---

## 0. Inventory code hiện hành cần đo trước

Tại lần chuẩn hóa 2026-08-02, registry có các app sau. Bảng này chỉ định tuyến
đọc code, không thay kết quả đo mới:

| App | Pattern nội tại có thể tái sử dụng cho Agent |
|---|---|
| `thumbnail` | prompt fragments động, job ảnh, gallery, R2 |
| `taoanh` | sinh ảnh tổng quát, model_ref, quyết toán theo output |
| `kichban` | text có cấu trúc, prompt catalog, result fragment HTMX |
| `taovideo` | provider async, poll/heartbeat/resume, giá token, refs/assets |
| `autosubvideo` | presigned upload, FFmpeg/libass, đo duration thật |
| `upscalevideo` | GPU/FFmpeg, service `submit_upscale_job()` dùng chéo có chủ đích |
| `taoclipngan` | pipeline GPU nhiều stage, nhiều output video |
| `chataistudio` | SSE, sidecar, conversation persistence; không phải job tool chuẩn |
| `demo` | khuôn submit/job/credit tối thiểu |
| `socialbot` | đóng băng, không đưa vào agent v1 |

Hạ tầng đã có: R2 GET/PUT presigned, `platform_core.media`, API pool cascade và
telemetry, credit ledger, payment, app contract linter. Vì vậy T0/T0b phải **bọc
những handler này**, không port lại runtime từ `D:\BOT GEMINI`.

---

## 1. Bảng đối soát tổng

| App | Nguồn | Dòng | `job_type` | Parity | `tools=` | Sẵn cho agent |
|---|---|---:|---|---|---|---|
| `thumbnail` | `thumbnail_api` | ~490+ | `thumbnail.generate` | ✅ **đủ catalog** (6·11·9·5) | ❌ | ⚠️ thiếu ToolSpec |
| `taoanh` | `gemini_image` | 341 | `taoanh.generate` | ✅ | ❌ | ⚠️ thiếu ToolSpec |
| `kichban` | `youtube_script` | 342 | `kichban.generate` | ✅ (20 prompt) | ❌ | ⚠️ thiếu ToolSpec |
| `taovideo` | `seedance_video` | 600 | `taovideo.generate` | ✅ (cost token) | ❌ | ⚠️ thiếu ToolSpec |
| `demo` | — | ~80 | `demo.reverse` | n/a | ❌ | ✅ đúng — khai `tools=()` rỗng |
| `socialbot` | — | — | (không) | n/a | ❌ | ✅ đúng — đóng băng (Q10), không khai |

**Kết luận hiện tại:** không được dùng bảng sáu app dưới đây như inventory hiện
hành. Hãy chạy `04_KIEM_CHUNG_CODE.md`. ToolSpec vẫn chưa có, nhưng runtime công
cụ đã rộng hơn nhiều; khoảng trống là **metadata + orchestration agent**, không
phải xây lại các công cụ hay hạ tầng thực thi.

### Đo được

```
ToolSpec trong platform_core/registry.py : 0     ← T0 chưa làm
parent_id trong models.py                : 0     ← D1 chưa làm
agent_runs trong models.py               : 0     ← D1 chưa làm
def url_for trong storage.py             : ĐÃ CÓ ← R2/presigned GET đã triển khai
def put_url trong storage.py             : ĐÃ CÓ ← upload thẳng browser→R2 đã triển khai
platform_core/agent/                     : CHƯA CÓ
```

---

## 2. Đối soát chi tiết từng app — kèm ToolSpec cần khai

Tham số dưới đây **lấy từ `Form(...)` thật trong `routes.py`**, không phải suy đoán.
Khai đúng bộ này thì agent dùng được **đúng bằng** những gì người dùng làm được.

### 2.1 `thumbnail` — `image.thumbnail`

Tham số thật: `topic · title · subtitle · text_style · phong_cach · kieu_trend ·
ngon_ngu · model · aspect_ratio · count`
Giá: `count × 5` credit. Tỉ lệ: `16:9 · 9:16 · 1:1 · 4:3 · 3:4`.
Catalog: `text_style` 6 · `phong_cach` 11 · `kieu_trend` 9 · `ngon_ngu` 5.

```python
ToolSpec(
    name="image.thumbnail",
    job_type="thumbnail.generate",
    description="Sinh ảnh thumbnail YouTube từ chủ đề, có tiêu đề/phụ đề trên ảnh, "
                "chọn được phong cách ảnh, kiểu trend, style chữ và ngôn ngữ.",
    params_schema={
        "topic":        {"type": "string", "required": True, "desc": "chủ đề/nội dung video"},
        "title":        {"type": "string", "required": False, "desc": "chữ lớn trên ảnh"},
        "subtitle":     {"type": "string", "required": False},
        "text_style":   {"type": "enum", "source": "prompts/text_style"},   # 6 lựa chọn
        "phong_cach":   {"type": "enum", "source": "prompts/phong_cach"},   # 11
        "kieu_trend":   {"type": "enum", "source": "prompts/kieu_trend"},   # 9
        "ngon_ngu":     {"type": "enum", "source": "prompts/ngon_ngu"},     # 5
        "aspect_ratio": {"type": "enum", "values": ["16:9","9:16","1:1","4:3","3:4"],
                         "default": "16:9"},
        "count":        {"type": "int", "min": 1, "max": 4, "default": 1},
        "model":        {"type": "model_ref", "category": "image"},
    },
    returns={"image_keys": "image[]", "prompt": "text"},
    verifiable=("vlm_judge",),
)
```

> **`"source": "prompts/<nhóm>"`** — lựa chọn đọc từ `_labels.json` trong
> `apps/thumbnail/prompts/`. Không liệt kê cứng trong ToolSpec: thêm một file `.txt`
> là agent thấy ngay, **không phải sửa manifest**. Đây là điểm cần chốt ở T0
> (xem mục 4.1).

### 2.2 `taoanh` — `image.generate`

Tham số thật: `prompt · model · aspect_ratio · count`. Giá `count × 5`.

```python
ToolSpec(
    name="image.generate",
    job_type="taoanh.generate",
    description="Sinh ảnh tự do từ mô tả bằng Gemini Image.",
    params_schema={
        "prompt":       {"type": "string", "required": True},
        "aspect_ratio": {"type": "enum", "values": ["16:9","9:16","1:1","4:3","3:4"],
                         "default": "16:9"},
        "count":        {"type": "int", "min": 1, "max": 4, "default": 1},
        "model":        {"type": "model_ref", "category": "image"},
    },
    returns={"image_keys": "image[]"},
    verifiable=("vlm_judge",),
)
```

### 2.3 `kichban` — `text.script`

Tham số thật: `topic · duration · tone · audience · language`
(4 nhóm catalog: `do_dai_video · giong_van · doi_tuong · ngon_ngu`).

```python
ToolSpec(
    name="text.script",
    job_type="kichban.generate",
    description="Viết kịch bản YouTube đầy đủ: hook, nội dung, outro, description, tags.",
    params_schema={
        "topic":    {"type": "string", "required": True},
        "duration": {"type": "enum", "source": "prompts/do_dai_video"},
        "tone":     {"type": "enum", "source": "prompts/giong_van"},
        "audience": {"type": "enum", "source": "prompts/doi_tuong"},
        "language": {"type": "enum", "source": "prompts/ngon_ngu"},
    },
    returns={"script": "text", "description": "text", "tags": "json"},
    verifiable=(),          # đầu ra văn bản — chưa có verifier phù hợp
)
```

> **Đây là công cụ agent sẽ dùng nhiều nhất** — nó sinh *đầu vào* cho các bước ảnh
> và video phía sau (`$s1.script` → prompt của `image.generate`).

### 2.4 `taovideo` — `video.generate`

Tham số thật: `prompt · model · resolution · duration · aspect_ratio · generate_audio`.
Model registry nằm **trong app** (`apps/taovideo/models.py`) với 3 model:

| Model | Độ phân giải | Thời lượng | Tỉ lệ |
|---|---|---|---|
| `seedance-2.0-mini` | 480p, 720p | 4,5,6,8,10,12,15 | 6 tỉ lệ |
| `seedance-2.0` | 480p, 720p, 1080p, 4k | như trên | như trên |
| `seedance-2.0-fast` | 480p, 720p | như trên | như trên |

```python
ToolSpec(
    name="video.generate",
    job_type="taovideo.generate",
    description="Sinh video AI từ mô tả (Seedance qua ModelArk). "
                "Chọn model, độ phân giải, thời lượng, tỉ lệ, có/không âm thanh.",
    params_schema={
        "prompt":         {"type": "string", "required": True},
        "model":          {"type": "model_ref", "category": "video"},
        "resolution":     {"type": "enum", "depends_on": "model", "field": "resolutions"},
        "duration":       {"type": "enum", "depends_on": "model", "field": "durations"},
        "aspect_ratio":   {"type": "enum", "depends_on": "model", "field": "aspects"},
        "generate_audio": {"type": "bool", "default": True},
    },
    returns={"video_key": "video"},
    verifiable=("technical", "vlm_judge"),
)
```

> **`"depends_on": "model"`** — độ phân giải hợp lệ **phụ thuộc model đã chọn**
> (`mini` không có 1080p/4k). Nếu ToolSpec không diễn đạt được ràng buộc này thì
> agent sẽ sinh kế hoạch `mini + 4k` → job hỏng → tốn tiền retry vô ích.
> **Đây là ràng buộc T0 phải hỗ trợ** (mục 4.2).

---

## 3. Ba khoảng cách phát hiện qua đối soát

### K1 — Model registry đang nằm TRONG app, không ở nền tảng ⚠️

`apps/taovideo/models.py` tự giữ `MODELS` (endpoint, provider_model_id, resolutions,
durations, aspects). Theo bản đồ 7 lớp của `CONG_THUC_DI_TRU_APP.md`, đây là **lớp
L6 (hạ tầng)** → phải ở `platform_core/providers.py`.

| Hệ quả nếu để nguyên | |
|---|---|
| App sau dùng cùng model phải chép lại | lệch phiên bản |
| Agent phải đọc từ nhiều nơi | không có nguồn duy nhất |
| Admin không đổi model tập trung được | như PLENX làm được ở `/ai-models/catalog/all` |

**Đề xuất:** gom vào `providers.py` **ở bước T0**, cùng lúc với ToolSpec — vì
`model_ref` trong `params_schema` cần trỏ tới đó.
*(Cần duyệt: sửa `platform_core/`.)*

### K2 — Chưa app nào khai năng lực ❌

Nhiều công cụ đã chạy được nhưng agent **không nhìn thấy** vì chưa có ToolSpec.
Đo lại danh sách hiện hành theo A1; đây là món nợ T0b nêu ở
[`02_LO_TRINH.md`](02_LO_TRINH.md), không phải lý do viết lại handler.

### K3 — Tài liệu lệch code trong vài phút ⚠️

`seedance` → `taovideo` đổi tên giữa hai lần đo. **Không có tài liệu nào theo kịp.**
Vì vậy mọi bảng trong bộ này đều phải kèm câu *"đo lại trước khi dùng"*.

---

## 4. Hai quyết định T0 phải giải, phát hiện nhờ đối soát

Không đối soát thì hai chỗ này sẽ lộ ra **sau khi đã khai xong ToolSpec cho 4 app** —
lúc đó sửa là sửa cả bốn.

### 4.1 Enum động từ thư mục prompt

`thumbnail` và `kichban` có lựa chọn **đọc từ `_labels.json`**, không phải hằng số.
`params_schema` phải diễn đạt được "lấy giá trị từ nguồn này".

| Phương án | Ưu | Nhược |
|---|---|---|
| **A. `{"type":"enum","source":"prompts/<nhóm>"}`** *(đề xuất)* | thêm file `.txt` là agent thấy ngay; không sửa manifest | nền tảng phải biết đọc `_labels.json` |
| B. liệt kê cứng trong manifest | đơn giản | mỗi lần thêm lựa chọn phải sửa manifest — sẽ quên |

### 4.2 Enum phụ thuộc tham số khác

`taovideo`: `resolution` hợp lệ **phụ thuộc `model`**.

| Phương án | Ưu | Nhược |
|---|---|---|
| **A. `{"type":"enum","depends_on":"model","field":"resolutions"}`** *(đề xuất)* | validator chặn được kế hoạch sai **trước khi tiêu tiền** | phức tạp hơn |
| B. để agent tự đoán rồi job hỏng | không phải làm gì | **tốn tiền thật mỗi lần đoán sai** |

Chọn A cho cả hai. Chi phí ở T0 là nhỏ; chi phí sửa sau khi đã khai 4 app là gấp bốn.

---

## 5. Việc còn lại ở tầng công cụ — đúng ba dòng

| # | Việc | Cần duyệt | Ước lượng |
|---|---|---|---|
| 1 | **T0** — `ToolSpec` + `tools=()` vào `registry.py`, hỗ trợ `source` và `depends_on` | ✅ sửa `platform_core/` | 2–4 ngày |
| 2 | **K1** — gom model registry của `taovideo` vào `providers.py` | ✅ sửa `platform_core/` | 1–2 ngày |
| 3 | **T0b** — khai `tools=` cho 4 app (dùng đúng khối ở mục 2) | không | 0,5–1 ngày |

Sau ba dòng đó, **tầng công cụ sẵn sàng hoàn toàn cho agent** — chỉ còn chờ đủ số
lượng công cụ và H10 (nếu agent chạm video).
