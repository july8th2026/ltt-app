# DEEPY — LẤP HAI KHOẢNG TRỐNG CỦA BÁO CÁO TRÍCH XUẤT

`WANGP_ARCHITECTURE_EXTRACTION.md` mục 10 để hai ô ⚠️ *chưa đủ bằng chứng*. Lượt
này đọc `wangp-agent/` để đóng chúng. **Không đoán bù.**

Cây agent tại SHA ghim chỉ có hai tệp: `wangp-agent/SKILL.md` (16.303 byte) và
`wangp-agent/agents/openai.yaml` (237 byte).

---

## UNKNOWN 1 — Deepy có tự suy/gán vai media không?

### → **SOLVED_BY_WANGP**

**FILE:** `wangp-agent/SKILL.md`
**SYMBOL:** mục `## Media Input Rules` (dòng 55–68)
**BEHAVIOR:** Bản hướng dẫn cho agent chứa **bảng ánh xạ vai → tham số → cờ**
đầy đủ, và bảng đó **do chính model khai** qua `metadata.media_inputs.image`:

> *"Use the entries in `metadata.media_inputs.image` to decide which image
> attachments can be supplied"*

| Vai | Tham số | Cờ |
|---|---|---|
| `start` | `image_start` | `S` trong `image_prompt_type` |
| `end` | `image_end` | `E`, ghép được thành `SE` |
| `reference` | `image_refs` | `video_prompt_type` chứa `I` |
| `single_reference` / `multiple_references` | `image_refs` (1 hoặc N) | `I` |
| `background` | `image_refs` | `K`, thường là `KI` |
| `injected_frames` | `image_refs` + `frames_positions` | `F` |
| `control` | `image_guide` | `V`, **giữ nguyên cờ tiền xử lý đi kèm** |
| `mask` | `image_mask` | `A`, giữ nguyên cờ mask/control đi kèm |

Video: `metadata.media_inputs.video` cho `video_source` · `video_guide` ·
`video_mask`. Âm thanh: `media_inputs.audio` chứa `prompt`; **đầu ra** âm thanh
là `metadata.outputs` chứa `audio` hoặc `capabilities.audio_output` — tài liệu
nói thẳng *"never treat that as audio output"*.

**LIMIT:** Đây là **hướng dẫn cho agent**, không phải bộ suy luận tất định. Agent
vẫn phải quyết *"ảnh này người dùng muốn dùng làm vai gì"*. Nhưng vế **"vai đó
ánh xạ ra tham số nào"** thì đã đóng hoàn toàn — và còn có một lớp lưới an toàn ở
tầng dưới: `apply_media_flag_defaults()` tự điền cờ khi tham số media được cấp mà
thiếu cờ.

**EVIDENCE:** `wangp-agent/SKILL.md:40,55–68`; `shared/api.py:74`;
`docs/API.md` §*Model Metadata* · **confidence: CHẮC CHẮN**

---

## UNKNOWN 2 — Deepy xử lý "ảnh nhân vật + video chuyển động + prompt" thế nào?

### → **PARTIALLY_SOLVED_BY_WANGP**

**FILE:** `wangp-agent/SKILL.md`
**SYMBOL:** `## Media Input Rules`, các mục `reference` và `control`
**BEHAVIOR:** Tổ hợp này **biểu diễn được** bằng đúng hai dòng của bảng trên:

```
anh nhan vat  ->  image_refs   + video_prompt_type chua I
video dan     ->  video_guide  (media_inputs.video.control)
prompt        ->  prompt
```

Và các model làm đúng việc này **có thật, được khai theo tên**: `SCAIL-2`,
`Wan 2.2 Animate` — *"Animate or replace performers using reference images,
pose/control video, and masks"*; `Bernini-R` — *"can edit a video or generate
from multiple reference images"*.

**LIMIT — và đây là phần chưa đóng:** có bằng chứng **cơ chế tồn tại** và
**agent có luật để dùng nó**. **Không** có bằng chứng agent *chọn đúng* tổ hợp ấy
từ một câu tiếng Việt tự nhiên. Đó là câu hỏi về **chất lượng suy luận**, và
`docs/` không trả lời được — chỉ chạy thật mới trả lời được.

⇒ Xếp loại: **NEEDS_LIVE_TEST**, không phải *thiếu năng lực*.

**EVIDENCE:** `wangp-agent/SKILL.md:62,66`; `docs/MODELS.md` §*Wan 2.1 và Wan 2.2*
· **confidence: CAO** cho phần cơ chế; **THẤP** cho phần chất lượng suy luận —
và tôi ghi rõ là thấp thay vì lấp bằng suy đoán.

---

## Ba thứ tìm thêm được trong lượt này

### a) Deepy có luật cho video dài — LTT không cần tự nối đoạn

> *"A long video is any requested sequence that exceeds what the selected model
> should generate in one window… The model must create it as multiple
> conditioned segments rather than one uninterrupted generation."*

Kèm hướng dẫn **master-image workflow**: sinh một ảnh tham chiếu chất lượng cao,
rồi mỗi keyframe là một lượt sửa **độc lập từ cùng ảnh gốc** (không phải từ ảnh
đã sửa trước đó) để tránh trôi nhận dạng.

**EVIDENCE:** `wangp-agent/SKILL.md:76,92` · **confidence: CAO**

### b) Không phải tính khung hình bằng tay

> *"The MCP/API frontier accepts `video_length` as a seconds string such as
> `"10s"`, so do not calculate frames manually."* WanGP **snap** thời lượng về số
> khung hợp lệ gần nhất của model đã chọn.

**EVIDENCE:** `wangp-agent/SKILL.md:80` · **confidence: CHẮC CHẮN**

### c) Gallery có bộ nhớ bền hơn giao diện

> *"Media IDs already observed by the MCP session remain resolvable while their
> files exist even if WanGP has trimmed their rows from the visible Gallery;
> remembered records have `in_gallery: false`."*

**EVIDENCE:** `wangp-agent/SKILL.md:72` · **confidence: CHẮC CHẮN**

---

## Ba thứ Deepy **KHÔNG** làm — tìm bằng cách tìm symbol, không thấy

| Thiếu | Kiểm thế nào |
|---|---|
| khái niệm **người dùng / quyền** | không có symbol nào về user/auth trong `SKILL.md`, `mcp_server.py`, `shared/api.py` |
| khái niệm **tiền / credit / ngân sách** | không có |
| **lưu trữ bền ngoài Gallery cục bộ** | Gallery nằm trên máy sẽ bị xoá; `wangp_create_gallery_download` chỉ trả URL ngắn hạn |

→ **NOT_SOLVED_BY_WANGP** cho cả ba. Đây đúng là phần `D-V2-004` giao cho
A-CONTROL.

**EVIDENCE:** `grep` trên `shared/api.py`, `shared/mcp_server.py`,
`wangp-agent/SKILL.md` cho `user|auth|credit|budget|owner` — không có định nghĩa
nào · **confidence: CAO** (chứng minh phủ định bằng tìm kiếm, nên ghi CAO chứ
không CHẮC CHẮN).
