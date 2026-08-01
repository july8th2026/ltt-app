# Bổ sung ToolSpec vào công thức di trú

> ⚠️ **File này KHÔNG phải chuẩn di trú.** Chuẩn di trú chính thức là
> **[`../CONG_THUC_DI_TRU_APP.md`](../CONG_THUC_DI_TRU_APP.md)** (bản đồ 7 lớp,
> quy tắc 4 rổ, công thức 8 bước B0→B7). Backlog và thứ tự đợt ở
> **[`../KE_HOACH_DI_TRU_MODULE.md`](../KE_HOACH_DI_TRU_MODULE.md)**.
>
> File này **chỉ thêm đúng một thứ** mà hai file kia chưa có: **hợp đồng `ToolSpec`**
> — thứ làm cho app đã port **dùng được bởi AI Agent** ở chặng D mà không phải mở
> lại từng app.
>
> Nguyên tắc `AGENTS.md`: mỗi câu hỏi chỉ có **đúng một câu trả lời đang hiệu lực**.
> Câu hỏi "di trú thế nào" → `CONG_THUC_DI_TRU_APP.md`. Câu hỏi "khai năng lực cho
> agent thế nào" → file này.

---

## 1. Vì sao cần thêm bước này

`ToolSpec` chỉ là **metadata mô tả** quanh handler hiện có. Nó không được tạo
executor, queue, storage, allocator hay cơ chế tính tiền mới. `job_type` phải nối
thẳng tới `jobs.py::handle` và `credit_cost` đang chạy thật.

### Cổng tái sử dụng bắt buộc trước B0

Trước khi đọc module nguồn, tra bảng mục 3.6 của `00_AGENT_BAT_DAU.md` và tìm code
trong `D:\LTTSTUDIOSAPP`. Phân từng nhu cầu vào một trong bốn loại:

- **Reuse:** gọi primitive hiện có, không viết lại.
- **Extend additive:** primitive chung gần đủ; xin duyệt bổ sung hợp đồng + test.
- **App-local:** logic riêng nằm trong `apps/<slug>/`.
- **External L1/L2:** LTT thật sự chưa có; mới được tham chiếu/copy từ nguồn chỉ đọc.

`D:\BOT GEMINI` không còn là điểm xuất phát mặc định. Nó là nguồn bù khoảng trống
nghiệp vụ/tài nguyên sau kiểm kê, không phải nguồn kiến trúc.

Công thức 8 bước hiện tại cho ra một app **người dùng bấm được**. Nhưng agent
(chặng D) không bấm nút — nó cần đọc được:

- app này **làm được gì** (tên năng lực),
- **tham số nào hợp lệ** (kiểu, khoảng, giá trị cho phép, mặc định),
- **trả ra kiểu gì** (để nối bước sau),
- **verifier nào áp được** lên kết quả.

Không khai những thứ đó thì đến chặng D phải **mở lại từng app đã port để bổ sung**.
Với ~10 app thì đó là việc làm lại có thể tránh được hoàn toàn bằng ~15 dòng khai
mỗi app, **ngay lúc đang port**.

---

## 2. Chèn vào đâu trong công thức 8 bước

```
B0 Phân loại
B1 Kiểm kê parity
B2 Copy tài nguyên (L1)
B3 Port lõi nghiệp vụ (L2) → jobs.py
B3.5  ★ KHAI ToolSpec  ← BƯỚC MỚI, chèn ở đây
B4 Thay hạ tầng (L6)
B5 Dựng lại UI (L4)
B6 Nối route (L5)
B7 Nghiệm thu parity
```

**Đặt ở B3.5** vì lúc đó đã biết chính xác lõi nghiệp vụ nhận gì / trả gì, và
**trước** khi dựng UI — nhờ vậy UI và ToolSpec dùng chung một bộ tham số, không lệch.

**Bổ sung vào tiêu chí B7:** app di trú chỉ "xong" khi **`tools=` khai đủ** mọi tham
số mà giao diện cho người dùng chọn. Nếu UI có ô mà ToolSpec không có → agent sẽ
không bao giờ dùng được năng lực đó.

---

## 3. Lược đồ ToolSpec

```python
ToolSpec(
    name="image.thumbnail",           # DUY NHẤT toàn hệ thống: <miền>.<hành động>
    job_type="thumbnail.generate",    # phải nằm trong job_types của CHÍNH app này
    description="Sinh ảnh thumbnail YouTube từ chủ đề + tiêu đề.",
    params_schema={
        "topic":        {"type": "string", "required": True, "desc": "chủ đề/mô tả"},
        "title":        {"type": "string", "required": False},
        "aspect_ratio": {"type": "enum", "values": ["16:9","1:1","9:16","4:3"],
                         "default": "16:9"},
        "count":        {"type": "int", "min": 1, "max": 4, "default": 1},
        "model":        {"type": "model_ref", "category": "image"},
    },
    returns={"image_keys": "image[]", "prompt": "text"},
    verifiable=("vlm_judge",),
)
```

### Kiểu cổng hợp lệ

```
text · image · image[] · video · video[] · audio · json · model_ref
```

Validator của agent dùng bộ này để **từ chối nối output `video` vào input chỉ nhận
`text`**.

### Quy ước đặt `name` — theo MIỀN, không theo tên app

| Miền | Ví dụ |
|---|---|
| `image.` | `image.generate` · `image.thumbnail` · `image.remove_bg` · `image.upscale` · `image.analyze` |
| `video.` | `video.generate` · `video.merge` · `video.subtitle` · `video.upscale` · `video.extract_frames` |
| `text.` | `text.script` · `text.enhance_prompt` · `text.translate` |
| `audio.` | `audio.tts` · `audio.music` |

Đặt theo miền vì agent chọn công cụ theo **việc cần làm**, không theo app nào cung
cấp. Hai app cùng làm được `image.generate` là chuyện bình thường — allocator chọn
theo giá/độ khả dụng, giống `api_pool.chon_key`.

---

## 4. Hợp đồng dán được — copy sang phiên chat đang port

> Dán nguyên khối dưới đây vào phiên đang nạp tài nguyên.

```markdown
### BẮT BUỘC khi port mỗi app (bước B3.5 của CONG_THUC_DI_TRU_APP.md)

Ngoài manifest/routes/jobs, MỖI app phải khai năng lực cho AI Agent.

Kiểm xem hạ tầng đã sẵn chưa (PowerShell):
    rg -n "class ToolSpec" platform_core/registry.py

• Nếu ra 0  → CHƯA có ToolSpec trong nền tảng. Khai TẠM dưới dạng biến module
              `TOOLS` trong apps/<slug>/manifest.py, ĐÚNG TÊN TRƯỜNG như dưới.
              Sau này chuyển sang dataclass chỉ là đổi cú pháp, không mất công.
• Nếu ra >0 → khai thẳng `tools=(ToolSpec(...),)` trong AppManifest.

TOOLS = (
    {
        "name": "image.thumbnail",        # DUY NHẤT toàn hệ thống: <miền>.<hành động>
        "job_type": "thumbnail.generate", # phải nằm trong job_types của chính app
        "description": "Sinh ảnh thumbnail YouTube từ chủ đề + tiêu đề.",
        "params_schema": {
            "topic":        {"type": "string", "required": True, "desc": "chủ đề"},
            "aspect_ratio": {"type": "enum", "values": ["16:9","1:1","9:16","4:3"],
                             "default": "16:9"},
            "count":        {"type": "int", "min": 1, "max": 4, "default": 1},
            "model":        {"type": "model_ref", "category": "image"},
        },
        "returns": {"image_keys": "image[]"},
        "verifiable": ("vlm_judge",),
    },
)

QUY TẮC BẮT BUỘC
1. `params_schema` phải phủ ĐỦ mọi tham số mà giao diện cho người dùng chọn.
   UI có ô mà ToolSpec thiếu = agent không bao giờ dùng được năng lực đó.
2. Kiểu cổng hợp lệ: text · image · image[] · video · video[] · audio · json · model_ref
3. `name` đặt theo MIỀN, không theo tên app:
   image.generate · image.thumbnail · image.remove_bg · image.upscale · image.analyze
   video.generate · video.merge · video.subtitle
   text.script · text.enhance_prompt
4. `job_type` phải là một phần tử của `job_types` trong chính manifest đó.
5. Model registry (supported_aspects / max_count / qualities / durations /
   supports_reference) → đưa vào `platform_core/providers.py`, KHÔNG để riêng trong app.

Phần còn lại của việc port: theo docs/CONG_THUC_DI_TRU_APP.md (B0→B7).
```

---

## 5. Bảng theo dõi khai ToolSpec

Đo trạng thái thật bằng lệnh A1 ở [`04_KIEM_CHUNG_CODE.md`](04_KIEM_CHUNG_CODE.md),
**không đọc từ bảng này**.

| App LTT | Nguồn BOT GEMINI | `tools=` khai chưa | Ghi chú |
|---|---|---|---|
| `thumbnail` | `thumbnail_api` | ⬜ | đang nâng parity (~30% → ≥90%) |
| `kichban` | `youtube_script` | ⬜ | đã có 20 file prompt |
| `taoanh` | `gemini_image` | ⬜ | |
| `taovideo` | `seedance_video` | ⬜ | đã có cost token, refs/assets, resume poll |
| `autosubvideo` | `auto_sub_video` | ⬜ | FFmpeg + transcript + upload R2 |
| `upscalevideo` | `video_upscale` | ⬜ | GPU; có service dùng lại |
| `taoclipngan` | `CUT CLIP SHORT` | ⬜ | nguồn ngoài BOT GEMINI; nhiều output |
| `chataistudio` | `codex` | quyết định riêng | SSE/sidecar, không qua job queue chuẩn |
| `demo` | — | ⬜ | app hạ tầng, khai `tools=()` rỗng là đúng |
| `socialbot` | — | ⬜ | đóng băng (Q10) — không khai |

---

## 6. Ba thứ cần đưa vào `platform_core/providers.py`, không để trong app

Đây là phần giao nhau giữa di trú và agent, dễ để nhầm chỗ:

| Tài sản nguồn | Dòng | Về đâu | Vì sao không để trong app |
|---|---:|---|---|
| `app/models/image_model_registry.py` | 193 | `platform_core/providers.py` | nhiều app dùng chung một model; để trong app là lặp và lệch |
| `app/models/video_model_registry.py` | 178 | `platform_core/providers.py` | như trên |
| `app/modules/seedance_video/face_detect.py` | 119 | `platform_core/agent/verifier.py` (chặng D3) | verifier là hạ tầng, không thuộc app nào |

Ba file này là **ngoại lệ** của quy tắc "port vào `apps/`" — chúng thuộc lớp **L6
(hạ tầng)** theo bản đồ 7 lớp, nên đi vào `platform_core/`. Việc này **cần duyệt**
theo `AGENTS.md` mục 2.3.
