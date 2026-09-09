# THAM SỐ THẬT VÀ THỜI GIAN THẬT — đọc từ code cộng đồng, không tự suy

> ⛔ **HỒ SƠ ĐƯỜNG ĐI — KHÔNG PHẢI CHỈ DẪN (đóng băng 2026-09-05).**
> Cấu hình sản xuất sống ở **`platform_core/video_gen/cau_hinh_san_xuat.py`**;
> kế hoạch sống ở **`KE_HOACH_XAY_DUNG.md`**. `V-012` chốt **một đường duy nhất**
> (fp16 · 1280×720 · 40 bước · không LoRA · A100 cố định), nên mọi thứ tệp này
> gọi là "bậc" hay "tuỳ chọn" đều **đã bị gỡ**.
>
> 🔴 **ĐÍNH CHÍNH 05/09/2026 — đọc `V-010` trước khi dùng tệp này.**
>
> Bản đầu của tệp kết luận *"đi đúng đường cộng đồng ⇒ dùng fp8_scaled 4 bước"*.
> **Dữ kiện đúng, bước suy sai.** Template mặc định fp8 + 640×640 vì nó nhắm
> **card 24GB phổ thông** — tài liệu ComfyUI nói thẳng điều đó. Ta thuê **80GB**,
> ràng buộc ấy không áp lên ta.
>
> ⇒ **Sản xuất chạy fp16/bf16.** LoRA 4 bước giữ lại làm **bậc nháp**, áp lên
> chính nền fp16 (không cần tải bản fp8). Bảng bậc + giá ở `V-010`.
>
> Mọi bảng dưới đây vẫn đúng **như một mô tả template**; chỉ đừng đọc chúng như
> một khuyến nghị cấu hình sản xuất.

> Chủ dự án, 04/09/2026: *"workflow cộng đồng đưa vốn code vận hành thông rồi,
> những gì có lời giải sẵn thì không cần đo lại cho tối ưu thời gian"* — và hỏi
> ba câu: **model tạo được video dài tối đa bao nhiêu giây**, **mỗi mode mất bao
> lâu trên GPU của ta**, và **hạng mục nào thật sự cần đo bằng GPU thật**.
>
> Tệp này trả lời cả ba bằng số **trích từ nguồn**, và nói rõ chỗ nào là số **đo
> được** còn chỗ nào là số **suy ra** — hai thứ đó không được để lẫn.

---

## 1. Tham số thật của bốn workflow — trích từ tệp đã ghim

Nguồn: `Comfy-Org/workflow_templates` tag **`v0.11.55`** (`bffc534e`), đọc bằng
cách làm phẳng subgraph rồi lấy `widgets_values`. Không có số nào ở bảng này do
tôi chọn.

| | **T2V** | **I2V** | **V2V** (fun_control) | **Character** (animate) |
|---|---|---|---|---|
| Kích thước | 640×640 | 640×640 | 640×640 | 640×640 → **1280×1280** |
| Số khung | **81** | **81** | **81** | **77** × 3 đoạn |
| fps | 16 | 16 | 16 | 16 |
| **Độ dài ra** | **5,06 s** | **5,06 s** | **5,06 s** | 4,81 s/đoạn → **~14,4 s** |
| Bước lấy mẫu | **4** (2 cao + 2 thấp) | **4** (2+2) | **4** nhanh · **20** chất lượng | **6** |
| cfg | **1** | **1** | 1 · 3,5 | **1** |
| shift (`ModelSamplingSD3`) | **5,0** | **5,0** | **8,0** | **8,0** |
| sampler / scheduler | euler / simple | euler / simple | euler / simple | euler / simple |
| Trọng số | `..._fp8_scaled` | `..._fp8_scaled` | `..._fp8_scaled` | `..._fp8_e4m3fn_scaled_KJ` |
| LoRA tăng tốc | `lightx2v_4steps_v1.1` | `lightx2v_4steps_v1` | `lightx2v_4steps_v1` | `relight` + `lightx2v` |
| Custom node | **0** | **0** | **0** | ≥ 3 gói |

🔴 **Điều bảng này nói:** template chính chủ **mặc định fp8_scaled + 4 bước**.

⛔ **Và đây là chỗ tôi suy sai lần đầu** (`V-010`): tôi viết tiếp *"đi đúng theo
code cộng đồng nghĩa là đi đường fp8 — một đường rẻ hơn, không phải kém hơn"*.
Câu sau là một **khẳng định không có bằng chứng**, và nó mâu thuẫn với chính mục
tiêu chủ dự án đã nêu (*"chất lượng tốt nhất, dùng GPU 80GB của ta"*).

Mặc định của một dự án mã nguồn mở được chọn cho **người dùng đông nhất của nó**
— ở đây là card 24GB. ⇒ **Sản xuất dùng fp16/bf16**; template vẫn là nguồn cho
*hình dạng đồ thị*, sampler, shift, số khung — chỉ **không** là nguồn cho độ
chính xác trọng số và số bước.

### Vì sao 81 khung, và vì sao không được chọn số bất kỳ

VAE của Wan nén thời gian **4 lần**, nên số khung phải là **4n+1**:
81 = 4×20+1, 77 = 4×19+1. Chọn 80 hay 100 là sai hình dạng latent.

---

## 2. ⭐ Trả lời câu hỏi 1 — **độ dài tối đa: 5,06 giây một lượt**

Không phải giới hạn của phần cứng, mà là **giới hạn của model**:

```
wan/configs/shared_config.py:20   wan_shared_cfg.frame_num = 81
```

81 khung ở 16 fps = **5,0625 giây**. Đây là con số model được huấn luyện; đẩy
cao hơn thì chất lượng tụt và chuyển động trôi.

**Dài hơn thì làm thế nào — cộng đồng đã có lời giải sẵn:** nối đoạn. Chính
template `animate` làm việc đó, và nó nằm ngay trong tệp: hai subgraph tên
**`Video Extend(Subgraph)`**, mỗi cái nối thêm 77 khung ⇒ 3 đoạn ≈ **14,4 giây**.

⇒ Với V1: **bán theo lượt 5 giây**. Video dài hơn là **ghép nhiều lượt**, và
điều đó khớp thẳng với `V-003` (bán theo giây sản xuất) — không cần mô hình giá
thứ hai.

---

## 3. ⭐ Trả lời câu hỏi 2 — **mỗi mode mất bao lâu**

### 3.1 Số **đo được** — bảng chính chủ của Wan-Video/Wan2.2

Nguồn: `assets/comp_effic.png` trong kho chính chủ. Định dạng **thời gian (s) /
đỉnh VRAM (GB)**, **1 GPU**, cấu hình `--offload_model True --convert_model_dtype`,
**40 bước, có CFG**.

| GPU | T2V 480P | I2V 480P | T2V 720P | Đỉnh VRAM 480P | Đỉnh VRAM 720P |
|---|---|---|---|---|---|
| **A100/A800** | **785,7 s** | **810,0 s** | 2 735,7 s | **41,3 GB** | 59,8 GB |
| **H100/H800** | **326,9 s** | **327,8 s** | 1 041,5 s | 41,3 GB | 59,8 GB |
| H20 | 1 133,9 s | 1 117,4 s | 4 048,7 s | 41,3 GB | 59,8 GB |
| 4090 (TI2V-**5B**, 720P) | 534,7 s | 524,8 s | — | 22,9 GB | — |

⭐ **640×640 của template ≈ 480P về khối lượng tính**: 640×640 = 409 600 điểm ảnh
so với 480P (832×480) = 399 360 — lệch **2,6 %**. Nên hàng 480P dùng được thẳng.

🔴 **Và bảng này lật một giả định:** đỉnh VRAM ở 480P là **41,3 GB**, không phải
80 GB. Con số "≥80GB" trong README là mức **an toàn khi chạy 720P không nén**.
⇒ **48 GB đủ cho 640×640.** Xem §5.

### 3.2 Số **suy ra** cho đường của ta — và cách suy

Đường của ta khác đường đo ở hai chỗ, cả hai đều **giảm** thời gian:

| | Bảng chính chủ | Template ComfyUI của ta | Tỷ lệ |
|---|---|---|---|
| Bước | 40 | **4** | 1/10 |
| CFG | `guide_scale` 3,0–4,0 ⇒ **2 lượt truyền mỗi bước** | `cfg = 1` ⇒ **1 lượt** | 1/2 |
| **Tổng lượt truyền** | **80** | **4** | **1/20** |

```
A100, 640×640, 81 khung:
   cận dưới   785,7 s ÷ 20  ≈  39 s   (đúng tỷ lệ lượt truyền)
   cận trên   785,7 s ÷ 10  ≈  79 s   (giữ nguyên phí tổn offload của bảng)
   + cố định  T5 encode + VAE decode 81 khung + ghi tệp  ≈ 20–40 s
   ────────────────────────────────────────────────────────────────
   ƯỚC TÍNH:  60 – 120 giây cho MỘT video 5,06 giây
```

| GPU | T2V / I2V / V2V (4 bước, 640×640, 5,06 s) | V2V bậc chất lượng (20 bước) |
|---|---|---|
| **A100 80GB** | **~1–2 phút** | ~5–10 phút |
| **H100** | ~0,5–1 phút | ~2–4 phút |
| **L40 48GB** | ~2–4 phút *(ước, chưa có hàng đo)* | — |

⛔ **Đây là ƯỚC TÍNH, không phải phép đo.** Cận dưới giả định không còn phí tổn
offload (ta có đủ VRAM nên không cần `--offload_model`); cận trên giữ nguyên phí
tổn đó. Sự thật nằm giữa, và **một lượt chạy** ở P07 thay được cả khoảng này.

### 3.3 Giá vốn suy ra — nối thẳng vào `V-003`

```
A100 serverless $0,00076/giây · lấy 90 giây/video (giữa khoảng)

giá vốn 1 video 5,06 s  =  90 × $0,00076  =  $0,068
giá vốn mỗi GIÂY ra     =  $0,068 ÷ 5,06  =  $0,0135
giá bán (V-003, ×2)     =  $0,027 / giây ra  ≈  710 đ/giây
                        =>  video 5 giây  ≈  3 600 đ  ≈  36 credit
```

⚠️ Chưa gồm khởi động nguội. Xem `VAN_HANH_MAY_C.md` §3: một lần nạp model tốn
$0,13–$0,26, tức **gấp 2–4 lần chính lượt sinh**. ⇒ **Gộp lô là đòn bẩy giá vốn
lớn nhất của V1**, lớn hơn mọi thứ khác trong tệp này. Một lô 10 video chia đôi
giá vốn mỗi video.

---

## 4. ⭐ Trả lời câu hỏi 3 — hạng mục nào **thật sự** cần GPU thật

### Cộng đồng đã trả lời rồi — ⛔ **không đo lại**

| Câu hỏi | Đã có lời giải ở đâu |
|---|---|
| Bước / cfg / shift / sampler tối ưu | template chính chủ, đã ghim |
| VRAM cần bao nhiêu theo độ phân giải | bảng `comp_effic.png` |
| fp8 hay bf16 | template **mặc định fp8** — cộng đồng đã chọn |
| Mode nào cần custom node | đọc template: T2V/I2V/V2V = **0** |
| Danh sách tệp model | `MODEL_BOM_FINAL.csv` + template |
| Tỷ lệ thời gian giữa các GPU | bảng chính chủ |

🔴 **`P08` (so mù bf16 vs fp8, 9,0 giờ) mất phần lớn lý do tồn tại.** Nó được lập
khi tôi tưởng đường chính chủ là bf16. Đường chính chủ **là fp8**. So bf16 với
fp8 giờ là so đường ta không đi với đường ta đi.

### Chỉ bốn thứ này không ai trả lời hộ được

| # | Đo cái gì | Vì sao không mượn được | Chi phí |
|---|---|---|---|
| 1 | **Khởi động nguội**: nạp model từ network volume US-KS-2 | Ổ đĩa của ta, DC của ta, băng thông của ta | ~0,2 h |
| 2 | **Wall-clock mỗi mode**, đúng tham số template, **1 lượt/mode** | §3.2 là ước tính; giá bán không được đứng trên ước tính | ~0,5 h |
| 3 | **L40 48GB có đủ không** cho fp8 + 640×640 | Bảng đo là bf16+offload; fp8 chưa ai đo ở cấu hình này | ~0,3 h |
| 4 | **Giá vốn thật mỗi giây ra**, đọc từ `GET /billing/endpoints` | `V-003` bán theo giây; con số phải là hoá đơn, không phải phép nhân | gộp vào 1–3 |

**Tổng ≈ 1,0–1,5 giờ GPU**, thay cho **16,2 giờ** mà P07+P08 từng chiếm.

⭐ Và đây không phải cắt gọt cho vừa túi tiền. Đây là **bỏ những phép đo đi tìm
câu trả lời đã có sẵn** — đúng nguyên tắc chủ dự án nêu, và nó tình cờ cũng giải
luôn bài toán "$50 chỉ mua được 6,8 giờ".

---

## 5. ~~Hệ quả: A100 có thể không phải lựa chọn đúng nữa~~ — ⛔ **GIẢ THUYẾT ĐÃ CHẾT**

> 🔴 **Mục này sai, giữ lại vì cách nó sai đáng nhớ.** Nó đứng trên giả định
> chạy **fp8 ở 640×640**. `V-010` bỏ giả định đó: sản xuất chạy **fp16, tới
> 720P**, và đỉnh VRAM đo được ở 720P là **59,8 GB** — **không vừa 48 GB**.
>
> ⇒ **`V-008` (A100 80GB) đứng vững.** L40 không còn là ứng viên cho bậc sản
> xuất. Phép đo `Đ3` đổi câu hỏi: không còn hỏi *"L40 có đủ không"* mà hỏi
> *"fp16 ở 720P đỉnh VRAM thật là bao nhiêu trên 80GB"*.
>
> ⭐ Đáng nhớ: giả thuyết này **khớp quá vừa** — nó vừa rẻ hơn, vừa giải luôn
> bài toán thiếu tiền, vừa có một con số đo (41,3 GB) hậu thuẫn. Chính vì khớp
> quá vừa mà tôi đã ghi *"chưa đổi `V-008`, phải đo"*. Câu thận trọng đó là thứ
> duy nhất giữ cho nó không thành một quyết định sai.

### Nội dung gốc của mục (đọc như một lối rẽ đã bị loại)


`V-008` chốt A100 80GB vì README nói *"at least 80GB VRAM"*. Nhưng bảng đo của
chính họ nói đỉnh VRAM ở 480P là **41,3 GB** — và đó là bản **bf16**. Bản
**fp8_scaled** của ta còn nhỏ hơn.

Kho US-KS-2 lúc 04/09/2026 (đo qua GraphQL):

| GPU | VRAM | $/giờ Pod | Hạng serverless | $/giờ serverless |
|---|---|---|---|---|
| H100 NVL | 94 GB | 2,59 | H100 PRO | 4,176 |
| A100-SXM4 | 80 GB | 1,39 | A100 | **2,736** |
| **L40** | **48 GB** | **0,69** | L40/L40S/6000 Ada | **1,908** |

**L40 rẻ hơn A100 1,43 lần.** 6,8 giờ khả dụng thành **9,7 giờ**.

⛔ **Chưa đổi `V-008`.** Đây là một giả thuyết có căn cứ, không phải một quyết
định — và nó đúng loại giả thuyết "khớp quá vừa" mà `docs` đã cảnh báo. Cách giải
đúng: **thêm L40 vào `gpuTypeIds` làm ưu tiên thứ hai và đo một lượt ở phép đo
số 3**. Vừa đủ hàng, vừa đủ rẻ, và nếu OOM thì rơi về A100 tự động.

⚠️ Kho **thay đổi theo giờ**: lượt quét đầu tối nay thấy `A100 80GB PCIe` ở
US-KS-2, lượt sau thấy `A100-SXM4-80GB` và `L40`. ⇒ `gpuTypeIds` phải liệt kê
**cả ba**, không được cắm một loại.

---

## 6. Những chỗ tệp này **chưa** trả lời

| Chỗ trống | Đóng ở đâu |
|---|---|
| Thời gian thật (mọi số §3.2 là ước tính) | P07, một lượt/mode |
| L40 48GB có OOM không | P07, phép đo số 3 |
| Cold start thật từ US-KS-2 | P07, phép đo số 1 |
| Bản API format làm phẳng có giữ đủ 30 node không | P06, theo `V-009` |
| Character mode: 3 gói custom node + tự tải lúc chạy | để **sau** V1 — ba mode kia cần **0** custom node, đó là ưu thế phải giữ |
