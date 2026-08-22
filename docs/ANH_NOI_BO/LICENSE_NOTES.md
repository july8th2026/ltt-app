# LICENSE NOTES — G2, xác minh giấy phép model

**Đọc và xác minh 2026-08-21.** Đây là **cổng chặn** của H37
([`KE_HOACH_THI_HANH.md`](KE_HOACH_THI_HANH.md) §5): chưa xác minh được quyền bán
ảnh thì không tải model, không đo, không xây tiếp.

> **Quy tắc dẫn đường, lấy từ bước 13 của bộ build pack:**
> *"kiểm tra lại license model tại thời điểm triển khai · không kết luận
> commercial-use nếu chưa xác minh."*

---

## 1. Kết luận một câu

> **FLUX.2 Klein 9B — model mà cả bộ build pack được đặt tên theo — KHÔNG dùng
> được để bán ảnh.** Nó mang **FLUX Non-Commercial License v2.1**.
> Chỉ bản **4B** là Apache 2.0.

**Đây chính là lý do G2 được đặt TRƯỚC việc tải ~45 GB.** Nếu làm theo thứ tự của
bộ build pack (bước 13 nằm gần cuối), ta đã tải model, đo đạc, dựng workflow, viết
cổng render — rồi mới phát hiện không được phép bán.

---

## 2. Bảng giấy phép — dòng FLUX.2

| Model | Giấy phép | Bán ảnh được? |
|---|---|---|
| `FLUX.2-klein-4B` | **Apache 2.0** | ✅ **được** |
| `FLUX.2-klein-base-4B` | **Apache 2.0** | ✅ **được** |
| `FLUX.2-klein-9B` | FLUX Non-Commercial **v2.1** | ❌ **không** |
| `FLUX.2-klein-base-9B` | FLUX Non-Commercial **v2.1** | ❌ **không** |
| `FLUX.2-dev` (32B) | FLUX.2-dev Non-Commercial v2.0 | ❌ **không** |

**Trích dẫn từ model card chính thức của nhà phát hành:**

- `FLUX.2-klein-4B`: *"Fully open under Apache 2.0"*, ghi rõ cho **commercial use**;
  4 tỉ tham số.
- `FLUX.2-klein-9B`: *"Available for non-commercial use"* — bản 9B phát hành *"under
  a non-commercial license"* để hỗ trợ *"third-party research and development"*.

**Điều khoản của giấy phép Non-Commercial** hạn chế *"commercial use, production
deployments, revenue-generating activity"*, và định nghĩa mục đích phi thương mại là
*"personal research, testing in non-production, charitable use (no payment received)"*.

Nền tảng này bán credit. **Cả ba vế đều rơi vào phần bị cấm.**

---

## 3. Chỗ mơ hồ — và vì sao nó không cứu được Klein 9B

Có một cách đọc khác đáng xem xét nghiêm túc, nên tôi đã đi tìm nó thay vì kết luận
sớm. Trong thảo luận công khai trên model card của Klein 9B, cộng đồng chỉ ra rằng
**chính văn bản giấy phép tự mâu thuẫn**:

- **Mục 2(d)** nói đầu ra (outputs) **có thể** dùng *"for commercial purposes"*;
- **Mục 4(a)** lại hạn chế *"commercial activity"* nói chung.

Hai cách đọc cùng tồn tại: (i) đọc chặt — không được bán ảnh; (ii) đọc dung hoà —
**bán ảnh thì được, nhưng phục vụ model trong sản phẩm thương mại thì không**.

Ba lý do vẫn phải loại Klein 9B:

1. **Chính FAQ của nhà phát hành khép cửa đó lại:** *"If you're generating images for
   products you charge for, creating assets for clients, or incorporating model
   weights into software you distribute, you need a commercial license."*
   Nền tảng này sinh ảnh cho một sản phẩm có thu tiền — đúng vế đầu.
2. **Ngay cả theo cách đọc dung hoà (ii), ta vẫn vi phạm.** Ta không chỉ bán ảnh —
   ta **tự vận hành model trong một dịch vụ có thu tiền**. Đó chính xác là vế mà
   cách đọc (ii) cấm.
3. **Không có ai từ nhà phát hành trả lời để gỡ mâu thuẫn.** Cả thảo luận trên model
   card lẫn issue trên kho mã chính thức đều **không có phản hồi của maintainer**.

Và một lý do về kinh doanh, độc lập với pháp lý: **xây một sản phẩm có thu tiền
trên một mâu thuẫn chưa được giải trong giấy phép của người khác là rủi ro không có
mặt lợi** — trong khi đã có **hai** phương án Apache 2.0 tốt ngang hoặc hơn.

Điều này khớp đúng blocker đã ghi sẵn trong `KE_HOACH_THI_HANH.md` §5:
*"⛔ Điều khoản mơ hồ về quyền với ảnh đầu ra → dùng phương án dự phòng."*

---

## 4. Đường mua giấy phép — có, nhưng chưa biết giá

Nhà phát hành có bán giấy phép thương mại cho việc tự vận hành. Bốn bậc, **không
công bố giá**, phải liên hệ bán hàng:

| Bậc | Gồm |
|---|---|
| Builder | model FLUX.2 [klein], 10K ảnh/tháng, 1 tên miền, quyền fine-tune & LoRA |
| Platform | FLUX.2 [klein] Base 9B + FLUX.2 [dev], 100K ảnh/tháng |
| Professional | FLUX.2 [dev], 100K ảnh/tháng, tới 3 tên miền |
| Enterprise | mọi model + bản mới, khối lượng tuỳ chỉnh |

Nhận xét: hai bậc đầu **có trần số ảnh/tháng**. Với mô hình bán credit thì trần đó
là một biến chi phí phải tính vào giá — và nó **triệt tiêu chính lợi thế** đã nêu ở
Q102 (*3090 là cách để rẻ đi*). Chỉ nên quay lại đường này nếu G4/G11 chứng minh
chất lượng Klein 9B hơn hẳn mọi phương án Apache 2.0 tới mức đáng trả tiền.

---

## 5. Phương án thay thế — đã xác minh, đều Apache 2.0

### 5.1 Qwen-Image (20B) — **ứng viên số một mới**

- **Giấy phép:** đọc thẳng tệp `LICENSE` trong kho model — **Apache License,
  Version 2.0** nguyên bản (*"Apache License Version 2.0, January 2004"*,
  *"Copyright 2024 Alibaba Cloud"*). **Không** phải giấy phép Tongyi/Qwen tuỳ biến,
  **không** có điều khoản hạn chế thương mại, **không** có trần người dùng hoạt động.
- Đã kiểm tận tệp giấy phép chứ không chỉ nhãn trên model card — vì nhiều model
  Qwen khác dùng giấy phép riêng, và nhãn dễ sai hơn tệp.

### 5.2 Qwen-Image-Edit-2509 — **khớp đúng ba chế độ đã chốt**

Giấy phép: `apache-2.0`. Và năng lực nó công bố khớp gần như một-một với ba chế độ
người dùng đã chọn ở đầu hạng mục:

| Chế độ đã chốt | Năng lực model công bố |
|---|---|
| `edit` — sửa theo lệnh | sửa nội dung chữ, **font, màu, chất liệu** |
| `subject` — giữ nhân vật/sản phẩm | ghép nhiều ảnh *"person + person"*, *"person + product"*, *"person + scene"*; **giữ nhân dạng khuôn mặt**, đổi tư thế; tối ưu cho 1–3 ảnh |
| `structure` — giữ bố cục/tư thế | **ControlNet gốc**: depth map, edge map, keypoint map |

Đây là điểm đáng chú ý nhất của G2 sau phần giấy phép: **phương án dự phòng hoá ra
phủ đúng yêu cầu tốt hơn phương án gốc.** Klein 9B là model sinh ảnh chung; Qwen-
Image-Edit-2509 được làm cho đúng ba việc đã được đặt hàng.

### 5.3 FLUX.2 Klein 4B — ứng viên cho bậc NHANH

Apache 2.0, 4 tỉ tham số, cùng dòng, và **ComfyUI trên máy B đã đỡ sẵn** (`class
Flux2`, `KleinTokenizer`). Nhẹ hơn nhiều nên hợp làm bậc rẻ/nhanh, và đặc biệt hợp
với việc **chia card với việc video** — chiếm ít VRAM hơn thì đổi model qua lại rẻ hơn.

---

## 6. Hệ quả cho H37

**Thay `DECISIONS.md` D-003 bằng D-008.** Hình dạng mới:

> ⚠️ **Bảng này đã LỖI THỜI cùng ngày 2026-08-21.** Nghiên cứu tiếp phát hiện
> **HiDream-O1-Image** (MIT, ~8B) hơn cả hai phương án dưới đây về chất lượng sửa
> ảnh, và **chính nó mới là model dùng Qwen3** — xem **D-009**. Giữ bảng để truy nguồn.

| Bậc | Model | Giấy phép | Ghi chú |
|---|---|---|---|
| **QUALITY** | Qwen-Image 20B | Apache 2.0 | fp8 ~20 GB sát trần 24 GB; GGUF Q5/Q6 thoải mái (node GGUF đã cài) |
| **QUALITY-EDIT** | Qwen-Image-Edit-2509 | Apache 2.0 | phủ `edit` + `subject` + `structure` |
| **FAST** | FLUX.2 Klein 4B | Apache 2.0 | nhẹ, nhanh, ít VRAM → hợp máy chia với video |

### 6b. Bảng giấy phép cuối cùng *(sau D-009, 2026-08-21)*

| Vai | Model | Giấy phép | Bán ảnh? |
|---|---|---|---|
| **Model đích** | **HiDream-O1-Image** ~8B | **MIT** | ✅ |
| Đối chứng | Qwen-Image-2512 20B | Apache 2.0 | ✅ |
| Đối chứng | Qwen-Image-Edit-2511 20B | Apache 2.0 | ✅ |
| Đối chứng | FLUX.2 Klein 4B | Apache 2.0 | ✅ |
| **Thước đo trần — CHỈ ĐỂ ĐO** | FLUX.2 Klein 9B | FLUX Non-Commercial v2.1 | ❌ |
| Đối chứng thương mại | Gemini 3 Pro Image · GPT Image 2 | dịch vụ trả tiền | ✅ (mua) |

**Ba ranh giới bắt buộc với Klein 9B**, thành blocker ở G6b: ảnh sinh ra **chỉ dùng
để chấm điểm**, không bán và không làm tài sản trong sản phẩm · **không** khai vào
`platform_core/providers.py` · **không** dùng đầu ra để train/fine-tune/distill
(giấy phép cấm riêng khoản này).

**Kiến trúc không đổi một dòng nào.** Đó là kiểm chứng thực tế cho nguyên tắc
model-agnostic đã đặt ở `KE_HOACH_H37.md` §2: đổi model = đổi file workflow JSON +
dòng `ModelInfo`, không đụng mã.

**Việc phải làm lại ở phase sau:**

- G3/G4: bộ ứng viên đo là **Qwen-Image · Qwen-Image-Edit-2509 · Klein 4B** —
  không phải Klein 9B.
- G4: tính lại VRAM. Text encoder của Qwen-Image là **Qwen2.5-VL-7B**, khác với
  Qwen3-4B của Klein → phép tính đỉnh VRAM ở `KE_HOACH_H37.md` §5 **phải đo lại**,
  không suy từ số cũ.
- G5: bộ test `subject` nên khai thác chế độ nhiều ảnh của Edit-2509 (1–3 ảnh).

---

## 7. Nguồn và ngày đọc

Tất cả đọc ngày **2026-08-21**. Giấy phép có thể đổi — **đọc lại tại thời điểm
triển khai thật**, đúng như bước 13 của build pack yêu cầu.

| Nội dung | Nguồn |
|---|---|
| Klein 4B — Apache 2.0, commercial use | [huggingface.co/black-forest-labs/FLUX.2-klein-4B](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B) |
| Klein 9B — FLUX Non-Commercial | [huggingface.co/black-forest-labs/FLUX.2-klein-9B](https://huggingface.co/black-forest-labs/FLUX.2-klein-9B) |
| Bảng biến thể + điều khoản NC | [deepwiki.com/black-forest-labs/flux2 — Licensing & Terms](https://deepwiki.com/black-forest-labs/flux2/7.4-licensing-and-terms) |
| Mâu thuẫn 2(d) vs 4(a), không có phản hồi chính thức | [Thảo luận trên model card Klein 9B](https://huggingface.co/black-forest-labs/FLUX.2-klein-9B/discussions/24) |
| Câu hỏi giấy phép chưa được trả lời | [github.com/black-forest-labs/flux2 — issue #32](https://github.com/black-forest-labs/flux2/issues/32) |
| Bốn bậc giấy phép thương mại | [bfl.ai/licensing](https://bfl.ai/licensing) |
| Qwen-Image — tệp LICENSE Apache 2.0 nguyên bản | [huggingface.co/Qwen/Qwen-Image/blob/main/LICENSE](https://huggingface.co/Qwen/Qwen-Image/blob/main/LICENSE) |
| Qwen-Image-Edit-2509 — apache-2.0 + năng lực | [huggingface.co/Qwen/Qwen-Image-Edit-2509](https://huggingface.co/Qwen/Qwen-Image-Edit-2509) |

**Không phải tư vấn pháp lý.** Đây là bản đọc kỹ thuật của tài liệu công khai, để
quyết định kỹ thuật. Nếu có tiền đặt cược lớn vào Klein 9B thì phải hỏi luật sư —
nhưng khuyến nghị ở §5 là **không cần đặt cược đó**, vì phương án Apache 2.0 phủ
yêu cầu tốt hơn.
