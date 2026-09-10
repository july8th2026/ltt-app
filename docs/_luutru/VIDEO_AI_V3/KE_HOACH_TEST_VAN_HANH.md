# KẾ HOẠCH TEST VẬN HÀNH — mượn cơ chế của cộng đồng, không tự nghĩ ra

> Chủ dự án 05/09/2026: *"Bạn nên xây plan test vận hành kỹ càng. Nghiên cứu công
> thức từ cộng đồng để xây logic cũng như cơ chế test phương án cộng đồng triển
> khai để ta áp dụng tránh mất nhiều time test lãng phí."*

Tệp này được viết **sau ba lượt đo hỏng**, tổng **$1,51**, mỗi lượt hỏng vì một
lý do khác nhau. Ba lý do đó là xương sống của tài liệu này.

---

## 0. Ba lượt đã mất tiền, và mỗi lượt dạy một luật

| # | Lượt | Mất | Hỏng vì | Luật rút ra |
|---|---|---|---|---|
| ① | Lượt khói đầu | **$0,22** | ComfyUI chết, `Popen` không hứng `stderr` ⇒ chỉ còn `exit 1` | **L1** |
| ② | Build 13 | **$0,00**¹ | `SaveVideo` thiếu `format` — hỏng ở giây cuối sau khi khuếch tán xong | **L2** |
| ③ | P07 lượt 1 | **$1,29** | Chạy cùng đồ thị hai lần ⇒ ComfyUI **trả cache**, lượt 2 = 0 giây | **L3** |

¹ Lượt ② rẻ vì nó hỏng ở validate, nhưng cùng lỗi ở vị trí khác đã tốn 208 giây.

**L1 — Không đo cái gì mà chưa mở được đường chẩn đoán của nó.**
Trước khi trả tiền cho một phép đo, phải chắc rằng **khi nó hỏng, ta biết vì
sao**. Năm lần trong hai ngày tôi trả tiền cho một lượt chạy rồi nhận về một con
số vô nghĩa, và cả năm lần chẩn đoán **đã tồn tại** ở đâu đó tôi không đọc.

**L2 — Phép kiểm offline phải chạy hết trước khi bật GPU.**
Mọi câu hỏi đọc-mã-là-biết phải được hỏi trên máy A. `tools/video_ra_soat.py cham`
là cổng chặn; nó **exit != 0** thì không được bắn job.

**L3 — Một phép đo phải được kiểm rằng nó ĐO ĐƯỢC THỨ NÓ ĐỊNH ĐO.**
Đây là luật đắt nhất và khó nhất. Lượt ③ chạy đúng, trả về đúng định dạng,
`status_str="success"` — và **hoàn toàn vô nghĩa**, vì hai lượt giống hệt nhau
thì cái sau bị cache. Không có phép kiểm nào của tôi hỏi *"phép trừ này có nghĩa
không"*.

---

## 1. Cơ chế mượn từ đâu — bốn nguồn, có dẫn chứng

### 1.1 `torch.utils.benchmark` — chính chủ PyTorch

Đọc `torch/utils/benchmark/utils/common.py` (05/09):

```python
_IQR_WARN_THRESHOLD       = 0.1     # IQR/median > 10%  -> "system fluctuation"
_IQR_GROSS_WARN_THRESHOLD = 0.25    # > 25% -> "significant environmental influence"
_MAX_SIGNIFICANT_FIGURES  = 4
```

Ba điều mượn:

| Mượn | Vì sao |
|---|---|
| **median, không mean** | `Measurement.median` dùng phân vị 0,5; mean chỉ để tham khảo. Đuôi dài của một lượt chậm bất thường không được kéo con số. |
| **IQR/median làm thước tin cậy** | Nó trả lời *"số này có dùng được không"*, thứ mà bản thân con số không nói. |
| **Warmup bắt buộc** | `Timer` docstring nói rõ: *"Timer will perform warmups (important as some elements of PyTorch are lazily initialized)"*. |

### 1.2 `ComfyUI-Attention-Optimizer` (MIT, cập nhật 26/08/2026)

```python
# Warmup
for _ in range(3):
    _ = attn_func(q, k, v, heads, skip_reshape=True)
torch.cuda.synchronize()

start = time.perf_counter()
for _ in range(num_iterations):        # 10
    _ = attn_func(q, k, v, heads, skip_reshape=True)
torch.cuda.synchronize()
return (time.perf_counter() - start) / num_iterations * 1000
```

⛔ **`torch.cuda.synchronize()` trước VÀ sau.** CUDA chạy bất đồng bộ; đo mà
không đồng bộ là đo thời gian **xếp lệnh**, không phải thời gian **chạy**. Đây là
lỗi kinh điển và nó cho số **nhỏ hơn thật rất nhiều** — tức sai về phía lạc quan.

Hai sự thật định lượng từ README của họ:

- **Attention chiếm 40–70% tổng thời gian sinh** với model transformer.
- SageAttention nhanh hơn SDPA **1,9×** trên RTX 4090 (head_dim=128); *"For video
  models (WAN, Hunyuan) with longer sequences, speedups can reach **2–4x**"*.
- Chi phí attention là **O(n²)** theo độ phân giải × số khung.

⭐ Ba dòng này đổi cả chiến lược đo của ta — xem §2.

### 1.3 `VBench` (Apache-2.0, CVPR 2024 Highlight)

Đo **chất lượng**, 7 chiều nội tại chạy được trên video của chính ta. Chi tiết
đã ở `KE_HOACH_DO_LUONG.md` §2. Chạy trên **máy A**, không tốn GPU thuê.

### 1.4 Bảng thời gian chính chủ `Wan-Video/Wan2.2`

Bảng `assets/comp_effic.png`, **1 GPU**, `--offload_model True
--convert_model_dtype`, **40 bước**, định dạng *thời gian (s) / đỉnh VRAM (GB)*:

| GPU | T2V **480P** | T2V **720P** |
|---|---|---|
| A100/A800 | 785,7 s / 41,3 GB | 2 735,7 s / 59,8 GB |
| **H100/H800** | 326,9 s / 41,3 GB | **1 041,5 s / 59,8 GB** |

🔴 **Tôi đã trích nhầm cột.** Ba tệp trong kho ghi `326,9 s` là số **720P** —
nó là **480P**. Số đúng cho cấu hình của ta là **1 041,5 s**.

⇒ Nghi vấn *"ta chạy 814 giây, chậm 2,5 lần so với 326,9"* **không tồn tại**:
1 041,5 s ở 40 bước ⇒ ~520 s ở 20 bước, cộng ~300 s nạp model = **~820 s**, và
đo được **814 s**. **Khớp.**

⭐ Và bảng đúng **đã nằm trong `THAM_SO_VA_THOI_GIAN.md` từ 04/09**. Tôi có bản
thật trong kho, trích sai cột, rồi suýt đốt **$2,10** để điều tra hệ quả của
việc đọc nhầm của chính mình.

⚠️ Bốn điều kiện của bảng, chính chủ ghi rõ — và điều (4) xác nhận luật warmup ở
§1.1 là chuẩn của họ luôn:
> *(2) …with **FlashAttention3** deployed on Hopper architecture GPUs*
> *(4) Reported results are the **average of multiple samples taken after the
> warm-up phase**.*

⇒ Khác biệt còn lại giữa ta và họ: **FlashAttention-3 (họ) vs SageAttention V1
(ta)**. Đó là câu hỏi tầng **T1**, không phải T3.

---

## 2. ⭐ Luật trung tâm: **đo ở tầng rẻ nhất trả lời được câu hỏi**

Đây là thứ giúp *"tránh mất nhiều time test lãng phí"* nhiều hơn mọi thứ khác.

| Tầng | Đơn vị | Giá một lượt | Trả lời được câu gì |
|---|---|---|---|
| **T0 — offline** | mili-giây | **$0** | cấu hình · đồ thị · cổng · kiểu · tham chiếu |
| **T1 — micro (GPU)** | mili-giây | ~$0,001 | backend attention nào nhanh · head_dim nào |
| **T2 — mini (GPU)** | giây | ~$0,05 | đường ống có thông · tệp có ra |
| **T3 — macro (GPU)** | phút | **$0,80–1,10** | thời gian thật một video · VRAM đỉnh · chất lượng |

🔴 **Lỗi tôi đã mắc: hỏi câu T1 bằng lượt T3.** Nghi vấn *"SageAttention V1 có
chậm hơn không"* là câu hỏi về **attention**, đo được ở tầng T1 với **vài
mili-giây** — nhưng tôi định trả lời nó bằng cách sinh cả video 814 giây.

⇒ **Quy tắc:** trước khi bắn một lượt T3, viết ra câu hỏi nó trả lời, rồi hỏi:
*"câu này có rơi xuống T0/T1/T2 được không?"* Nếu có, xuống tầng.

⛔ Và điều ngược lại cũng đúng: **đừng dùng T1 để trả lời câu T3.** Micro-benchmark
attention **không** nói được thời gian một video, vì còn VAE, text encoder, đổi
model MoE, ghi tệp. Đó là bài học *"cửa giả chỉ trả lời câu không phụ thuộc thứ
nó thay"* ở dạng khác.

---

## 3. ⭐ Số nào ĐÃ CÓ — và vì thế KHÔNG được đo lại

> Chủ dự án 05/09: *"nghiên cứu công thức từ cộng đồng và xác minh đã có sẵn để
> lắp ráp pipeline cũng như số đo và xác minh cuối từ cộng đồng lắp ráp và xác
> minh thay vì đi test thế này"*

Sau khi đọc lại bảng chính chủ **đúng cột**, phần lớn kế hoạch đo ở bản trước
**không còn lý do tồn tại**:

| Câu hỏi | Nguồn đã có | Còn phải đo? |
|---|---|---|
| Thời gian 720P/40 bước, H100, 1 GPU | **1 041,5 s** — bảng chính chủ | ❌ **KHÔNG** |
| Đỉnh VRAM 720P | **59,8 GB** — cùng bảng | ❌ **KHÔNG** |
| Đỉnh VRAM 480P | **41,3 GB** — cùng bảng | ❌ **KHÔNG** |
| Thời gian ở **20 bước** | suy tuyến tính từ 40 bước ⇒ ~520 s | ❌ đã đối chiếu, khớp |
| Thời gian nạp model từ network volume | **814 − ~520 ≈ 300 s**, từ chính lượt đã chạy | ❌ đã có |
| Đường ống có ra tệp không | ✅ `P06` — video 1,1 MB đã về máy A | ❌ **XONG** |
| Giá vốn thật | hoá đơn RunPod | ✅ **T0, $0** |
| Chất lượng 7 chiều | VBench trên video đã sinh | ✅ **máy A, $0 GPU** |

🔴 **Nghĩa là `P07` gần như đã xong, và tôi suýt đốt thêm $2,10 để đo lại thứ
Alibaba đã công bố.** Lý do duy nhất tôi nghĩ cần đo lại là một **nghi vấn sinh
ra từ việc tôi trích nhầm cột của chính bảng đó**.

### 3.1 Kiểm chứng: số của ta có khớp bảng không

| | chính chủ | của ta |
|---|---|---|
| 720P · 81 khung · 40 bước | 1 041,5 s | — |
| 720P · 81 khung · **20 bước** (suy) | ~520 s | — |
| \+ nạp model từ network volume | *(họ không có)* | ~300 s |
| **tổng một lượt đầu** | **~820 s** | **814 s** ✅ |
| đỉnh VRAM | 59,8 GB | 43,8 GB¹ |

¹ Của ta là VRAM **đang giữ lúc đo**, không phải đỉnh — nên thấp hơn là **không
mâu thuẫn**. Và vì đã có 59,8 GB từ bảng, ta **không cần** đo đỉnh nữa:
`VRAM_TOI_THIEU_GB = 80` đứng vững với biên 20 GB.

⭐ **814 s khớp ~820 s** là một kiểm chứng chéo mạnh: nó xác nhận cùng lúc rằng
đường ống dựng đúng, `SO_BUOC=20` có hiệu lực thật, và SageAttention V1 **không
chậm hơn** FlashAttention-3 tới mức nhìn thấy được ở tầng này.

### 3.2 Việc còn lại — không việc nào cần GPU thuê thêm

| Đ | Việc | Tầng | Chi phí |
|---|---|---|---|
| **Đ4** | Giá vốn thật từ `GET /v1/billing/endpoints` | T0 | $0 |
| **Đ5** | VBench 7 chiều trên video 1,1 MB đã có | máy A | $0 |
| **Đ6** | Ghi bảng số vào `DO_LUONG_KET_QUA.csv` | T0 | $0 |

🔴 **Hoá đơn tính bù muộn** — đo 05/09:

```
16:2x  $1,3171 · 990 giay
16:5x  $1,6805 · 1262 giay    (KHONG chay job nao them)
17:2x  $2,0318 · 1526 giay    (van con tang)
```

⇒ Chốt giá vốn phải đọc **sau ≥ 30 phút**, đối chiếu `timeBilledMs` với tổng
`executionTime + delayTime` của các job.

### 3.3 Chỉ đo khi có câu hỏi mà cộng đồng KHÔNG trả lời được

Ba câu duy nhất còn lại thuộc loại đó, và **không câu nào cấp bách**:

1. **i2v và v2v** — bảng chính chủ có I2V-A14B 720P = **1 055,9 s / 59,7 GB**;
   v2v (fun_control) thì **không có trong bảng**. Nhưng cả hai dùng cùng backbone
   14B nên ước từ t2v là đủ cho `P14a`.
2. **Khởi động nguội thật** (cold start RunPod) — đo được **18,4 s** ở `P06` và
   **154,7 s** ở lượt `P07`. Chênh lệch là do worker ấm/nguội; cần vài mẫu để có
   median, nhưng nó **đi kèm miễn phí** với mọi lượt chạy thật sau này.
3. **SageAttention V1 vs FA3** — chỉ đáng đo nếu ta muốn *tăng tốc*, không phải
   để *vận hành*. Xếp vào việc tối ưu sau `P15`.

---

## 4. Luật chống lãng phí — tổng hợp

1. ⭐ **Đi tìm số trước khi đi đo.** Luật số một, và là luật tôi vừa vi phạm đắt
   nhất: bảng đã nằm trong kho từ 04/09.
2. **Đọc đúng cột.** Một bảng đúng bị trích sai cột thì nguy hiểm hơn không có
   bảng — vì nó sinh ra nghi vấn giả và ta đi điều tra nghi vấn giả đó.
3. **Xuống tầng trước khi bắn.** Viết câu hỏi ra, hỏi nó có rơi xuống T0/T1/T2 không.
4. **Đ0 phải xanh** (`cham` 35/35) — cổng chặn, không phải gợi ý.
5. **`--thu` trước mọi lượt thật.** `--tran` không phải phanh.
6. **Warmup không tính vào số đo** — chính chủ cũng ghi *"after the warm-up phase"*.
7. **`so_lan ≥ 3`** nếu buộc phải đo, để có median và IQR.
8. **Đổi seed mỗi lượt** — nếu không thì đo cache. Đã trả $1,29.
9. **`torch.cuda.synchronize()`** quanh mọi phép đo GPU tầng T1.
10. **Mở đường chẩn đoán trước khi trả tiền.**
11. **Đọc hoá đơn muộn**, không đọc ngay sau job.
12. **Hỏi "phép đo này có đo được thứ nó định đo không"** trước khi bắn.

---

## 5. Ngân sách sau khi sửa

| Bước | Tầng | Chi phí |
|---|---|---|
| Đ4 giá vốn | T0 | $0 |
| Đ5 VBench | máy A | $0 |
| Đ6 ghi bảng | T0 | $0 |
| | | **$0** |

Envelope `P07` là 1,0 giờ = $4,79. **Đã tiêu $2,03; phần còn lại không cần
GPU.** Bản kế hoạch trước định tiêu thêm $2,10 — toàn bộ khoản đó nay là **tiền
tiết kiệm được nhờ đọc lại một bảng đã có**.
