# H37 — Dựng bộ máy từ tài liệu, rồi mới chạy GPU

**22/08/2026 · bản 3 · thay cách làm của bản 2**

Bản 2 làm ngược: **chạy GPU để phát hiện**, rồi mới ghi lại. Bản này làm đúng thứ
tự: **đọc tài liệu để biết, dựng xong bộ máy, rồi mới chạy GPU để xác nhận**.

Cái giá của cách cũ, đếm được: tám lượt đo, hàng nghìn giây GPU, và **ba phát hiện
mà tài liệu đã có sẵn** — thông số khuyến nghị, giới hạn ngôn ngữ, khuôn dây API.

⛔ **Chỉ làm HiDream-O1. Bỏ hẳn Qwen-Image** (chủ dự án chốt 22/08).

---

## 1. Những gì ĐÃ BIẾT từ tài liệu — không cần thực nghiệm

### 1.1 Kiến trúc

| | |
|---|---|
| Loại | Pixel-level Unified Transformer (UiT) — **không VAE, không bộ mã hoá văn bản ngoài** |
| Tham số | 8B (bản Pro 200B+, không dùng) |
| Giấy phép | **MIT** |
| Ba việc, một bộ trọng số | sinh ảnh · sửa theo lệnh · nhất quán chủ thể |

⚠️ **`CLIPTextEncodeHiDream` KHÔNG dành cho model này.** Nó nhận `clip_l`, `clip_g`,
`t5xxl`, `llama` — bốn bộ mã hoá của **HiDream-I1**, đời trước. Dùng `CLIPTextEncode`
thường là đúng.

### 1.2 Thông số khuyến nghị

| | Full *(ta dùng)* | Dev |
|---|---|---|
| Bước | **50** | 28 (lịch cố định) |
| CFG / guidance | **5,0** | 0,0 |
| **Shift** | **3,0** | 1,0 |
| Sampler | **`uni_pc`** | `euler` |
| Dùng cho sửa ảnh | ✅ *"use the Full model for editing tasks"* | ✗ |

**Ba thứ ta đang đặt sai hoặc thiếu:** sampler `euler` thay vì `uni_pc` · **không có
node shift** · chưa dùng `HiDreamO1PatchSeamSmoothing`.

### 1.3 Chất lượng theo số bước — đã có người benchmark

20 · 28 · 36 · 50 bước ở 2048², guidance 5,0:

| Bước | So với 50 bước | Nhận xét của người đo |
|---|---|---|
| 20 | nhanh 2,55× | "hơi thô" |
| 28 | nhanh 1,81× | "nhìn thoáng thì ổn, chi tiết mỏng đi khi soi kỹ" |
| **36** | nhanh 1,40× | **"dùng tốt cho hầu hết trường hợp"** |
| 50 | mốc | chuẩn chính thức |

**Chất lượng giảm lộ ra đúng ở:** mặt người lớn tuổi · **bàn tay** · hoạ tiết vải ·
**chữ**.

⇒ **Bỏ cuộc so mù s30 ↔ s90.** Câu hỏi đã có câu trả lời: 30 bước nằm ở vùng thấp,
vùng dùng được là **36–50**. Không bắt chủ dự án chấm 36 cặp cho việc này nữa.

### 1.4 Nhất quán nhân vật — điểm mạnh nhất, có số

**UniSubject** (300 ca, 1.800 chủ thể):

| Số chủ thể | HiDream-O1 **8B** | Qwen-Image-Edit **27B** |
|---|---|---|
| 2–3 | **7,95** | 7,50 |
| 4–8 | **7,47** | 5,34 |
| 9–11 | **7,65** | **2,71** |

Sửa theo lệnh: **GEdit 7,60** (Qwen 7,41) · **ImgEdit 4,14** (FLUX.1 Kontext 4,00).

Chữ trong ảnh: **CVTG-2K 0,9085** · LongText **EN 0,979 / ZH 0,978**.

### 1.5 Ngôn ngữ — vì sao tiếng Việt hỏng

Mọi benchmark ngôn ngữ chỉ có **EN** và **ZH**. Không có tiếng Việt. D-027 đo đúng
nhưng **lẽ ra đọc là biết**. Lớp `platform_core/image_gen/prompt_dich.py` là cách xử
lý tiêu chuẩn, không phải sáng kiến riêng.

### 1.6 VRAM — số cộng đồng KHỚP số ta đo

| | Cộng đồng | Ta đo (máy B, `--reserve-vram 3`) |
|---|---|---|
| Full BF16 | **18–20 GB** | t2i **17,6 GB** · tham chiếu **20,0 GB** ✅ |
| FP8 | 10–11 GB | ta đo **24,0 GB** ⚠️ *(xem D-021 — fp8 trên máy này ngược)* |

⚠️ **Số fp8 của ta trái với cộng đồng và đó là một dấu hỏi chưa giải.** D-021 đo fp8
tốn **nhiều hơn** bf16 (23,99 GB so với 16,86 GB). Cộng đồng nói fp8 chỉ 10–11 GB.
Khác biệt có thể do ta nạp checkpoint `fp8_scaled` qua `CheckpointLoaderSimple` thay
vì đường nạp riêng. **Chưa cần giải** — bf16 vừa máy và tốt hơn.

### 1.7 Số ảnh tham chiếu

Native ComfyUI: **`image_1`…`image_10`**. Bộ node cộng đồng: tới **12**.
Catalog của ta đang giới hạn **2** — con số đó là **lựa chọn sản phẩm** (chất lượng
trên hết, D-010), không phải giới hạn kỹ thuật. Giữ, nhưng ghi rõ vì sao.

### 1.8 Chế độ giữ bố cục — D-017 SAI, có đường đi

D-017 ghi *"HiDream-O1 không hỗ trợ ControlNet ⇒ chế độ `structure` không có đường"*.
Model card ghi ngược lại: pipeline hỗ trợ **`--layout_bboxes`** và **"layout and
skeleton conditioning"**.

Nhưng: **ComfyUI native KHÔNG phơi ra** — chỉ có 4 node
(`EmptyHiDreamO1LatentImage`, `HiDreamO1ReferenceImages`,
`HiDreamO1PatchSeamSmoothing`, và `CLIPTextEncodeHiDream` của đời I1).
Layout bbox nằm ở **bộ node cộng đồng** `Saganaki22/HiDream_O1-ComfyUI`.

⇒ Ba đường, chọn ở G-2 dưới đây.

---

## 2. Những gì PHẢI đo trên máy ta — và chỉ những thứ này

Ba loại, không hơn:

| Loại | Vì sao không ai đo hộ được |
|---|---|
| **Riêng máy này** | 3090 chia GPU với dự án video; VRAM/nhiệt/thời gian tuỳ cấu hình cụ thể |
| **Thứ hỏng im lặng** | issue #15667: input autogrow qua API có thể **được chấp nhận mà không có tác dụng** |
| **Chất lượng chủ đề Việt Nam** | không benchmark nào đo |

**Đã đo xong, không đo lại:** VRAM/thời gian t2i và tham chiếu · tái lập theo seed ·
rò rỉ RAM · ngưỡng token 7.506 · tác dụng thật của ảnh tham chiếu *(ảnh ra chứa cả
hai chủ thể — không thể ngẫu nhiên)*.

---

## 3. Các giai đoạn — bộ máy trước, GPU sau

### Giai đoạn A — DỰNG BỘ MÁY *(không chạm GPU)*

| # | Việc | Trạng thái |
|---|---|---|
| A1 | Cổng render trên máy B (`render_gateway/`) | ✅ xong, 121 test |
| A2 | Chốt ngân sách token, dò bận, công tắc dừng | ✅ xong |
| A3 | Lớp dịch prompt (`prompt_dich.py`) | ✅ xong, 16 test |
| A4 | Client nền tảng (`cong_render.py`) + provider `ltt_image` | ✅ xong, 19 test |
| **A5** | **Bản mẫu đúng thông số tài liệu**: `uni_pc` · `ModelSamplingSD3` shift 3,0 · `HiDreamO1PatchSeamSmoothing` | 🔨 **làm ngay** |
| **A6** | **Nối lớp dịch vào đường gọi thật** (Gemini qua `api_pool`) | 🔨 |
| **A7** | Ghép ảnh → R2 → job nền tảng, hàng đợi, credit | ⏳ |
| **A8** | Deploy cổng render thành dịch vụ trên B + tường lửa + tự khởi động | ✅ xong 2026-08-22 — đã xác minh từ máy A: TCP 8199 mở + trả **401**, TCP 8188 **đóng** |
| **A9** | **Bán ra `/api/v1`**: app `apps/anhnoibo`, tool `image.ltt` (D-034) | ✅ xong 2026-08-22, 19 test |

### Giai đoạn B — MỘT PHIÊN GPU DUY NHẤT, gộp mọi thứ cần đo

Chỉ chạy **sau khi A5–A6 xong**, và gộp thành **một lần**:

| # | Đo gì | Ảnh | Vì sao cần |
|---|---|---|---|
| B1 | Bản mẫu mới (uni_pc + shift 3,0 + seam smoothing) so bản cũ | 6 | xác nhận thông số tài liệu đúng trên máy ta |
| B2 | 36 bước so 50 bước ở cấu hình mới | 12 | thu hẹp từ 4 mức xuống 2, theo benchmark cộng đồng |
| B3 | Nhất quán nhân vật: 1 ảnh tham chiếu → 4 bối cảnh | 4 | chủ đề Việt Nam, không ai đo hộ |
| B4 | Bàn tay / mặt người lớn tuổi / hoạ tiết vải | 6 | đúng chỗ tài liệu nói chất lượng giảm |
| | **tổng** | **~28 ảnh ≈ 1,5 giờ** | |

⛔ **Không chạy B trước khi A5–A6 xong.** Đo bản mẫu sai thông số là đo một thứ ta
sắp bỏ.

### Giai đoạn C — CỔNG CHẤT LƯỢNG *(cần chủ dự án)*

| # | Việc |
|---|---|
| C1a | **Nửa Gemini — KHÔNG cần GPU**, chạy được cả khi card đang bận: `py tools/doi_chung_gemini.py --ra bench/G6b_gemini --that` (~3,90 USD). Xem D-038 |
| C1b | Nửa model nhà (30 prompt) — cần GPU |
| C1c | Dựng lô so mù + chấm: `py tools/cham_mu.py tao/tinh` — không cần GPU |
| C2 | Quyết định chữ tiếng Việt (`DE_XUAT_CHU_TIENG_VIET.md`) |
| C3 | Quyết định chế độ giữ bố cục (G-2 dưới) |

### Giai đoạn D — MỞ BÁN

Hợp đồng API đã **đóng băng** từ 2026-08-22 (A9). Còn lại **bốn** việc, và ba trong
số đó không phải việc viết mã:

| # | Việc | Chặn bởi |
|---|---|---|
| D1 | `LTT_RENDER_BASE_URL` trên máy A + khoá `ltt_image` trong admin | thao tác vận hành |
| D2 | `hidream-o1` `is_active=True` | cổng chất lượng C1 (so mù với Gemini 3 Pro Image) |
| D3 | Chốt giá thật thay giá tạm 5/ảnh ×3 | cần số đo từ lượt dùng thật |
| D4 | Thêm `image.ltt` vào `LTT_PUBLIC_API_TOOLS` + điền một dòng ở mục 4 của `APP_API_COVERAGE_FINAL.md` | D1–D3 và một lượt chạy thật từ ngoài vào |

⛔ **`api_exposed=True` KHÔNG phải "đang bán".** Nó chỉ nghĩa là hợp đồng đã đóng
băng và không đổi lặng lẽ được nữa. Bốn cổng còn khoá: xem D-034.

---

## 4. Ba quyết định còn treo

**G-1 — Số bước sản phẩm.** Tài liệu nói 36–50. Đo B2 để chọn giữa hai mức đó.
*Không* quét lại từ 30.

**G-2 — Chế độ giữ bố cục.** Ba đường:
- (a) **Bỏ**, nói thẳng là không bán chế độ đó *(rẻ nhất, trung thực)*
- (b) Cài bộ node cộng đồng `Saganaki22/HiDream_O1-ComfyUI` để có layout bbox
  *(thêm phụ thuộc bên thứ ba vào máy dùng chung với dự án video — rủi ro thật)*
- (c) Dùng `edit` + lời nhắc giữ bố cục *(đã có sẵn, chưa đo hiệu quả)*
→ **Khuyến nghị: thử (c) trong B3, nếu không đạt thì (a).** Không chọn (b) khi
chưa cần: máy B đang chạy production của dự án video.

**G-3 — Chữ tiếng Việt.** Xem `DE_XUAT_CHU_TIENG_VIET.md`. Chủ dự án đã nói *"không
quá quan trọng, nghiên cứu model tốt tiếng Việt hơn sau"* ⇒ **hoãn**, không làm lớp
ghép chữ bây giờ.

---

## 5. Nguồn

- [ComfyUI — HiDream-O1 workflow](https://docs.comfy.org/tutorials/image/hidream/hidream-o1)
- [Model card HiDream-ai/HiDream-O1-Image](https://huggingface.co/HiDream-ai/HiDream-O1-Image)
- [Bài báo gốc — arXiv 2605.11061](https://arxiv.org/html/2605.11061v1)
- [Benchmark bước/CFG/độ phân giải](https://kotonia.ai/en/articles/hidream-quality-speed-bench/)
- [Bộ node cộng đồng — Saganaki22/HiDream_O1-ComfyUI](https://github.com/Saganaki22/HiDream_O1-ComfyUI)
- [Issue #15667 — autogrow qua API hỏng im lặng](https://github.com/Comfy-Org/ComfyUI/issues/15667)
