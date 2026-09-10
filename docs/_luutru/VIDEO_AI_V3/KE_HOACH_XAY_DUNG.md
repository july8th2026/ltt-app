# CHUỖI XÂY DỰNG — bản lập lại, một nguồn duy nhất

> Chủ dự án 05/09/2026: *"Bạn cần lập kỹ lại chuỗi phase chuẩn logic xây dựng,
> không nên test nhiều workflow mà chỉ chọn của 1 nguồn chuẩn và có xác thực tối
> ưu để xây dựng."*
>
> ⭐ **Tệp này là kế hoạch đang sống.** Tám tệp kế hoạch cũ mang banner
> *"HỒ SƠ ĐƯỜNG ĐI"* — chỗ nào chúng nói khác tệp này, **tệp này đúng**.

---

## 1. Nguồn — **một**, đã chốt ở `V-014`, không mở lại giữa chuỗi

```
pipeline    Comfy-Org/workflow_templates      v0.11.55 / bffc534e    MIT
runtime     comfyanonymous/ComfyUI            v0.34.0  / 12d52794    GPL-3.0
trong so    Comfy-Org/Wan_2.2_..._Repackaged  c4f60d30               Apache-2.0
tang toc    --use-sage-attention              co san trong ComfyUI   Apache-2.0
```

🔑 `--use-sage-attention` là **một cờ**, không phải một nhánh: không custom node,
không đổi workflow, không đổi trọng số, không đổi mode nào. Nên nó **không** tạo
ra đường thứ hai. Chạy được trên Ampere, Ada **và** Hopper.

Tham số sản xuất: ⚙️ `platform_core/video_gen/cau_hinh_san_xuat.py` (`test_712` canh).

---

## 2. Bốn luật của chuỗi

**① Mỗi pha trả lời ĐÚNG MỘT câu hỏi, và cổng ra phải ĐO ĐƯỢC.**
*"Xong rồi"* không phải cổng. *"`BANG_KE.json` khớp `MODEL_BOM_V1.csv` từng
sha256"* mới là cổng.

**② Kiểm ở NƠI NÓ SẼ CHẠY.** Một image "chạy được ở máy A" không là bằng chứng
cho cloud: khác hệ điều hành, khác kiến trúc GPU, khác kernel SageAttention biên
dịch ra. ⇒ Không dựng bậc kiểm trung gian ở máy A; đưa thẳng lên cloud và để
**lượt khói** làm cổng. Phần validate đồ thị của ComfyUI chạy **trước** GPU nên
nó gần như miễn phí.

**③ ⛔ KHÔNG pha nào so sánh nhiều lựa chọn.** Nguồn đã chốt. Pha nào phát hiện
nguồn sai thì **dừng và trình chủ dự án**, không tự mở nhánh thứ hai.

> 🔴 Luật này có giá của nó: `P08` đã được lập rồi giết **ba lần** trong hai
> ngày, mỗi lần vì tôi đặt lại câu hỏi so sánh dưới một cái tên khác —
> *bf16 vs fp8* → *ba bậc chất lượng* → *chưng cất hay không*. Nay nó **không
> còn trong chuỗi**, và luật ③ là thứ ngăn nó quay lại lần thứ tư.

**④ Pha sau không mượn envelope của pha trước.** `test_710` cưỡng chế tổng bảng
`ENVELOPE_PHA_GIO` ≤ envelope thật, **và** `P06 + P07` ≤ số giờ mua được bằng số
dư hiện có.

---

## 3. Chuỗi

| # | Pha | Câu hỏi **duy nhất** | Cổng ra (đo được) | GPU thuê |
|---|---|---|---|---|
| 1 | ✅ **P05** Nạp model — **XONG 05/09** | volume có **đúng** 170,51 GB **đúng tệp** không? | **8/8 tệp, 0 lỗi**; sha256 khớp `lfs.sha256` thượng nguồn; `doi-chieu` từ máy A xanh | **0** · thật **$0,20** |
| 2 | **P06** Image + endpoint + lượt khói | worker có dựng được và chạy thông **trên cloud** không? | job trả về một tệp thật, và trước đó ComfyUI **không** báo lỗi validate node | ~$0,05 |
| 3 | **P07** Đo **một lần** | một video tốn bao lâu · bao nhiêu tiền · chất lượng nào? | `DO_LUONG_KET_QUA.csv`: tiền từ **hoá đơn** và 7 chiều **VBench**, **cùng một dòng** | ~0,5 h |
| 4 | **P14a** 🔴 Cổng thương mại | **bán được không?** | giá vốn **đo được** × 2 so với giá thị trường | **0** |
| 5 | **P09** Provider | `ltt_video` vào registry | **G-B** xanh | **0** |
| 6 | **P10** App | `apps/lttvideo/` | gate + `lint_app_contract` xanh | **0** |
| 7 | **P15** Công khai | | gate đầy đủ · G-A/G-B · `api_prod_canary` | **0** |

### ⭐ Lượt khói bắt luôn bẫy subgraph — **miễn phí, ngay trên cloud**

`V-009` đo được: template T2V có **4** node ở cấp 1 nhưng **30** node thật nằm
trong `definitions.subgraphs`. Mã nào duyệt `workflow["nodes"]` sẽ thấy bốn node,
không thấy cái nó cần, rồi **thất bại im lặng** — JSON vẫn hợp lệ, chỉ là không
đổi tham số nào. Video ra sai tham số, không lỗi, không cảnh báo.

⭐ **Không cần một pha riêng để bắt nó, và không cần chạy thử ở máy A.**
ComfyUI validate đồ thị ở `POST /prompt` **trước khi** đụng tới GPU: node không
tồn tại, đầu vào thiếu, kiểu sai — đều trả lỗi ngay. Nên lượt khói trên cloud
vừa chứng minh worker dựng được, vừa chứng minh workflow giải được, mà phần
validate **không tốn một giây GPU nào**.

⛔ **Không kiểm ở máy A.** Máy A chạy Windows + WSL2 với hai RTX 5060 Ti
(Blackwell); worker chạy Linux trên Hopper/Ampere. Một image "chạy được ở A"
**không** là bằng chứng cho cloud — khác kiến trúc GPU, khác driver, khác
CUDA kernel mà SageAttention biên dịch ra. Kiểm ở nơi nó sẽ chạy.

**Lượt khói dùng tham số nhỏ nhất chạy thông** — không phải 720P/20 bước. Nó trả
lời *"đường ống có thông không"*, không phải *"nhanh chậm thế nào"*; câu sau là
của `P07`.

### 🔴 P14a đứng TRƯỚC P09/P10 — thay đổi thứ tự quan trọng nhất của bản này

Bản trước để việc chốt giá ở `P14`, tức **sau khi** đã dựng xong provider và app.
Sai thứ tự: nếu giá vốn đo được không bán nổi thì ta đã xây một app cho một sản
phẩm không bán được.

Chủ dự án đã nói thẳng điều đó: *"Với giá thành như vậy ngang giá tạo video từ
seedance rồi."*

⇒ **`P14a` là một cổng DỪNG.** Giá vốn × 2 không cạnh tranh được ⇒ **dừng chuỗi,
trình chủ dự án**, không đi tiếp sang `P09`.

---

## 4. Đã xong

| | |
|---|---|
| **P00–P03** | rà pack, bản đồ hệ thống, ADR, catalog OSS, kế hoạch chi phí |
| **P04-a** | chọn DC bằng phép đo 11 DC × 8 GPU ⇒ **US-KS-2** |
| **P04-b** | network volume `uizchbiet5` · 300 GB · US-KS-2 |
| **P04-c** | cầu dao ngân sách + sàn credit + kiểm kê mồ côi — **39 phép kiểm xanh, $0** |
| **P04-d** | ghim upstream đầy đủ; `V-009` … `V-014` |

Chi phí cloud tới lúc này: **$21/tháng cố định, $0 compute.**

---

## 5. ⛔ Đã GỠ — ghi ra để phiên sau không dựng lại

| Gỡ | Vì | Ở đâu |
|---|---|---|
| **P08** và mọi pha so sánh | luật ③ | `V-014` |
| Ba bậc chất lượng · LoRA chưng cất · mọi fp8/int8 | một đường duy nhất | `V-012` |
| L40 48GB và mọi phép tra card VRAM **thấp hơn** | fp16/720P đỉnh 59,8 GB | `V-012` · `V-013` |
| **TurboDiffusion** | chỉ có I2V cho Wan2.2; *"not finalized"*; stack riêng | `V-014` |
| `kijai/ComfyUI-WanVideoWrapper` | 3 tháng không cập nhật; native chạy 0 custom node | `V-011` |
| `runpod-workers/worker-comfyui` | **AGPL-3.0** — điều khoản mạng | `P02` |
| Mode **Character** | cần ≥3 gói custom node + 3 model phụ | ngoài V1 |
| Prometheus / Grafana / W&B | bốn điểm dữ liệu | `KE_HOACH_DO_LUONG` §3 |

---

## 6. Ngân sách — và con số tôi cố ý **chưa** điền

⚙️ Bảng envelope sống ở `ngan_sach.ENVELOPE_PHA_GIO`. **Đừng chép nó ra đây.**

| | |
|---|---|
| Hạn mức tháng đã duyệt | 35,6 giờ GPU |
| **Mua được bằng số dư thật $50** | **6,8 giờ** (đã trừ sàn credit $31,50) |
| `P06` + `P07` cần | **1,3 giờ** ✅ |
| Thời gian và giá mỗi video | 🔴 **chưa biết — và tôi không đoán** |

Ước tính 8,7 phút / $0,60 (`V-013`) tính cho ComfyUI **không có** SageAttention.
Không nguồn nào công bố tốc độ end-to-end của Wan2.2 trên ComfyUI **có**
SageAttention — *"2–5×"* là số cho riêng phép attention, không phải cho cả lượt.

⇒ Đó là **lý do duy nhất còn lại** để đốt GPU thuê, và `P07` trả lời nó bằng
**một** lượt đo, không phải một ma trận.

---

## 7. Nguồn chân lý — bảng con trỏ, không chứa giá trị

| Hỏi gì | Hỏi ở đâu | Ai canh |
|---|---|---|
| Tham số sản xuất | `platform_core/video_gen/cau_hinh_san_xuat.py` | `test_712` |
| Danh sách tệp phải nạp | `docs/VIDEO_AI/MODEL_BOM_V1.csv` | `test_712` |
| Ngân sách, sàn credit, envelope | `platform_core/video_gen/ngan_sach.py` | `test_710` |
| Gọi nhà cung cấp, dừng endpoint | `platform_core/video_gen/cloud_api.py` | `test_711` |
| Cấu hình endpoint, giá, bẫy vận hành | `docs/VIDEO_AI/VAN_HANH_MAY_C.md` | — |
| Bộ đo chất lượng | `docs/VIDEO_AI/KE_HOACH_DO_LUONG.md` | — |
| Vì sao mọi thứ như thế | `docs/VIDEO_AI/DECISIONS.md` (`V-001`…`V-014`) | — |
| Đang có gì trên cloud | `python tools\video_cloud.py trang-thai` | — |

⛔ **Đừng gõ lại một con số nào từ các nguồn trên vào tài liệu.** Đó chính xác là
cơ chế đã hỏng ba lần trong hai ngày.

---

## 8. Việc tiếp theo

**`P06`** — dựng Docker image, đẩy lên registry riêng tư, tạo template +
endpoint, chạy **lượt khói**.

`P05` đã đóng: volume `uizchbiet5` chứa đủ 8 tệp / 170,515 GB, đối chiếu độc lập
từ máy A xanh. Pod nạp đã xoá, kiểm kê sạch, chi phí thật **$0,20**.
