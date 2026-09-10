# P03 — NGÂN SÁCH VÀ SỔ CHI PHÍ

> ⛔ **HỒ SƠ ĐƯỜNG ĐI — KHÔNG PHẢI CHỈ DẪN (đóng băng 2026-09-05).**
> Kế hoạch đang sống là **`KE_HOACH_XAY_DUNG.md`**; tham số sản xuất sống trong
> **`platform_core/video_gen/cau_hinh_san_xuat.py`**. Tệp này viết trước
> `V-010`/`V-012` nên nó còn mang giả định **fp8 · 4 bước · 640×640 · nhiều bậc
> chất lượng · L40**. Cả năm giả định đó **đã bị gỡ**. Đọc tệp này để hiểu
> *chương trình đã đi qua đâu*, đừng đọc để lấy con số.


> Sản phẩm của **P03**. Đây là chỗ P00 gọi là *"defect nghiêm trọng nhất của pack
> sau điểm mù `taovideo`"*: **bảy pha cần GPU trả tiền, một túi tiền, không ai
> giữ cửa** — và pha tốn nhất (P08) chạy **trước** pha chứng minh hệ thống an
> toàn (P14/P15). Tệp này đóng lỗ đó.

Giá gốc: **$2,72/giờ** (RunPod serverless A100 80GB) · **$0,07/GB/tháng** (volume).
Hỏi hai lần trong ngày 04/09/2026, kết quả trùng nhau.

---

> 🔴 **BẢN NÀY ĐÃ ĐƯỢC TÍNH LẠI 2026-09-04 (lần 2).** Hai phát hiện làm lệch con
> số của bản đầu — xem `CHUOI_MODEL_VA_VAN_HANH.md`:
> ① volume **chỉ chứa model** (ComfyUI/torch nằm trong Docker image, gộp vào giá
> giờ worker) ⇒ dung lượng **nhỏ đi**; ② phải giữ một **sàn credit**, nếu không
> số dư về $0 thì **volume bị xoá không khôi phục được** ⇒ tiền tiêu được **ít đi**.
> Con số dưới đây là bản đã sửa.

## 1. Ngân sách tháng — tách cố định khỏi biến

```
$150,00 / tháng  (D08)
  ─ cố định:   volume 300 GB × $0,07/GB/tháng      = $21,00   (tính theo GIỜ)
  ─ SÀN CREDIT: giữ lại, KHÔNG được tiêu           = $31,50
  ───────────────────────────────────────────────────────────
    còn cho compute                                = $97,50
                                         ÷ $2,72   = 35,8 giờ GPU
```

🔴 **Sàn credit không phải một khoản chi — nó là khoản KHÔNG ĐƯỢC CHI.**
`docs.runpod.io/accounts-billing/billing.md` nói thẳng: *"If your balance stays at
$0 and these charges can't be covered, the network volume **may eventually be
terminated, and its data can't be recovered**."*

Mất khả năng sinh video là **phiền**. Mất 220 GB model đã nạp là **nhiều giờ làm
lại**. ⇒ Sàn = chi phí lưu trữ 30 ngày × 1,5 = **$31,50**.

⭐ **Điều này đổi cách đọc `D08`:** $150/tháng **không phải** thứ được tiêu tới
đồng cuối. Trần tiêu thật là **$118,50**, và trần compute là **$97,50**.

🔴 **Lưu trữ tiêu ngân sách kể cả tháng không sinh một khung hình nào.** Ở 300 GB
nó ăn **14 %**; cộng sàn credit thì **35 %** của $150 bị khoá lại trước khi có bất
cứ thứ gì được tạo ra. P00 không tính khoản nào trong hai khoản này.

### ✅ Một dung lượng duy nhất: **300 GB ngay từ đầu** (chủ dự án chốt 04/09)

Bản trước đề xuất chia ba đợt 160 → 230 → 275 GB. **Bỏ.** Ba lý do, và lý do đầu
là một lỗi tính của tôi:

1. 🔴 **275 GB không đủ.** Con số đó tính trên trạng thái *tĩnh* 220,81 GB, **quên
   đỉnh của P08**: bf16 và fp8 của cùng một mode phải nằm cạnh nhau ⇒ đỉnh
   **≈ 263 GB** (`CHUOI_MODEL_VA_VAN_HANH.md` §2). Biên còn 4,4 % — quá mỏng.
2. **Lần nới rơi giữa P07.** P07 đi tuần tự qua cả 4 mode và **không xoá** mode
   trước ⇒ chạm 220 GB ngay trong P07, đúng lúc đang đốt envelope GPU.
3. Tiết kiệm thật của việc chia đợt chỉ ~$9,80/tháng, và chỉ trong vài tuần đầu.

| | Volume | $/tháng | Sàn credit | Compute | Giờ GPU |
|---|---|---|---|---|---|
| **300 GB** | 300 | **$21,00** | **$31,50** | **$97,50** | **35,8** |
| *(275 GB — đã bỏ)* | 275 | $19,25 | $29,00 | $101,75 | *37,4* |

**Giá của việc chọn 300 thay vì 275: $4,25/tháng = 1,6 giờ GPU ≈ 10 lượt chạy lô.**
Đổi lại biên 12,4 % thay vì 4,4 %, và **không phải nới giữa P07**. Đáng.

⚠️ *"Volume size can be increased later but **cannot be decreased**"* — đặt hụt thì
phải tạo volume mới và chép lại toàn bộ 220 GB.

⛔ **Envelope dưới đây tính trên 35,8 giờ.**

---

## 2. Envelope theo pha — **tính bằng GIỜ, không bằng đô-la**

Vì sao bằng giờ: giá có thể đổi. Một envelope ghi bằng đô-la sẽ **âm thầm sai**
khi giá tăng; ghi bằng giờ thì nó tự đúng, và cột $ chỉ là quy đổi ở giá hiện tại.

| Pha | % | **Giờ GPU** | ≈ $ @ $2,72 |
|---|---|---|---|
| **P05** nạp model | 0 % | **0** | $0 — mục tiêu cả pha là **không** đốt GPU |
| **P06** bootstrap + dựng lại | 10 % | **3,6** | $9,75 |
| **P07** 4 mode upstream | 20 % | **7,2** | $19,50 |
| **P08** benchmark | **25 %** | **9,0** | $24,38 |
| **P09** golden | 5 % | **1,8** | $4,88 |
| **P10** E2E A↔C | 10 % | **3,6** | $9,75 |
| **P14** tiêm lỗi | 10 % | **3,6** | $9,75 — ⭐ **phải còn tiền lúc này** |
| **P15** canary | 5 % | **1,8** | $4,88 |
| **dự phòng** | 15 % | **5,4** | $14,61 |
| | **100 %** | **35,8** | **$97,50** |

**Cộng volume $21,00 + sàn $31,50 ⇒ $150,00.** Đúng trần `D08` theo thiết kế.

### Ba luật đi kèm

1. ⛔ **Pha sau không mượn trước được của pha trước.** Hết envelope ⇒ thu hẹp ma
   trận thí nghiệm theo *information gain* (chính `P08` đã viết vậy), **không**
   tiêu lấn. Vay của P14 là vay của chính phép kiểm an toàn.
2. **Mỗi lần chạy ghi một dòng sổ** (§4), kèm `envelope_remaining_h`.
3. **Cuối mỗi pha có GPU: kiểm kê tài nguyên còn đang tính tiền.** Không có dòng
   này thì pha **chưa đóng**.

---

## 3. Kiểm tra envelope có thực tế không — bằng số, không bằng cảm giác

Chuỗi model thật (`CHUOI_MODEL_VA_VAN_HANH.md` §1) cho con số **tệ hơn** bản đầu:

```
NGUỘI  T2V/I2V nạp 68,78 GB @ 200–400 MB/s  =  172–344 s     (bản đầu ước 75–150 s)
       + một lượt sinh ≤ 600 s
       ⇒ một lượt CÔ LẬP  ≈ 772–944 s ≈ 0,21–0,26 giờ ≈ $0,58–0,71

ẤM    worker còn sống (nộp liên tiếp trong `idle timeout`)
       ⇒ một lượt ≈ 600 s = 0,167 giờ ≈ $0,45
```

| Pha | Envelope | Nếu **cô lập** (0,26 h) | Nếu **gộp lô** (0,167 h) | Nhu cầu | Đủ? |
|---|---|---|---|---|---|
| P07 | 7,2 h | 27 lượt | **43 lượt** | ~24 | ✅ |
| P08 | 9,0 h | **34 lượt** | **54 lượt** | ~40+ | ⛔ cô lập **KHÔNG đủ** · ✅ gộp lô đủ |
| P14 | 3,6 h | 13 lượt | 21 lượt | bật/chạy/drain/huỷ lặp | ✅ |

> 🔑 **Gộp lô không còn là một tối ưu hoá — nó là điều kiện để P08 chạy được.**

Ở $2,72/giờ, mỗi lần khởi động nguội tốn **$0,26**. Với ~40 lượt của P08, chạy lẻ
đắt hơn chạy lô **~$10**, tức hơn một phần ba envelope của cả pha P14.

⇒ **Hai luật vận hành cho P08**, không phải gợi ý:
1. **Nộp job liên tiếp thành lô**, không nộp lẻ tay từng cái.
2. **Nâng `idle timeout` lên ~60 s trong lúc chạy lô** rồi trả về 5 s. 60 giây
   nhàn rỗi tốn $0,045; một lần khởi động nguội tốn $0,26 — lời gấp gần **6 lần**.

⭐ Đây là con số thứ ba củng cố `V-001③`, và lần này nó là ràng buộc chứ không
phải lợi thế.

⚠️ Cả bảng vẫn sụp nếu một lượt thật lâu hơn 600 s. **P07 là chỗ con số đó được
thay bằng số đo thật**, và envelope phải tính lại ngay tại đó.

### Nếu phải chuyển sang H100 ($4,79/giờ)

35,8 giờ → **20,3 giờ** (−43 %). Không đủ cho ma trận P08 kể cả khi gộp lô.
⇒ Đó là lúc phải trình chủ dự án, không phải lúc tự thu hẹp phạm vi.

---

## 4. Khuôn sổ chi phí

Ghi vào `docs/VIDEO_AI/COST_LEDGER.csv` (sinh khi có dòng đầu tiên):

```csv
timestamp,resource_type,resource_id,provider,region,unit_price_usd,unit,quantity,estimated_cost_usd,actual_cost_usd,phase,phase_envelope_h,envelope_remaining_h,status,notes
```

So với khuôn của pack (`templates/COST_LEDGER_TEMPLATE.csv`), thêm **hai cột**:
`phase_envelope_h` và `envelope_remaining_h` — vì một sổ không nói còn bao nhiêu
thì không ngăn được ai tiêu quá.

**Nguồn số thật:** `actual_cost_usd` lấy từ hoá đơn RunPod, **không** từ phép nhân
của ta. Ước tính và thực tế nằm hai cột khác nhau để chênh lệch **nhìn thấy được**
— đúng khuôn `credit.SettlementResult` (`provider_credit` vs `charged_credit`) mà
nền tảng đã dùng cho tiền của khách.

---

## 5. Nối vào `V-003` — giá vốn mỗi video

`V-003` chốt **giá bán = 2 × giá vốn theo giây**. Nay có đủ mảnh để viết công thức:

```
giá vốn một video =  (giây_khởi_động_phân_bổ + giây_chạy) × $2,72/3600
                  +  chi_phí_volume_tháng / số_video_tháng
```

Với số **đã sửa** (volume 300 GB, ước 200 video/tháng):

```
                              CHẠY LẺ (nguội)        CHẠY LÔ (ấm)
compute   944 s × $0,000756  = $0,714     600 s × $0,000756 = $0,454
volume    $21,00 / 200       = $0,105                        $0,105
                              ─────────                     ─────────
giá vốn                       ≈ $0,819                       ≈ $0,559
giá bán ×2                    ≈ $1,64 ≈ 43.000 đ             ≈ $1,12 ≈ 29.000 đ
```

🔑 **Chạy lẻ đắt hơn chạy lô 47 %** ở cùng một video. Đây là con số cuối cùng
biến "gộp lô" từ vận hành thành **chính sách giá**: `giá_vốn_chuẩn` của `V-003`
phải khai rõ nó tính ở **mức sử dụng nào**, nếu không thì ×2 nhân vào một con số
không có nghĩa.

⛔ **Đây là một phép tính minh hoạ, KHÔNG phải bảng giá.** Ba đầu vào đều chưa đo:
thời gian thật một lượt · tỉ lệ khởi động nguội · số video mỗi tháng. Bảng giá
thật là sản phẩm của **P09**, sau khi P07/P08 có số.

⭐ Nhưng nó cho thấy một điều ngay bây giờ: **khoản volume chỉ là 17 % giá vốn ở
200 video/tháng, và 63 % ở 20 video/tháng.** Tức ở mức dùng thấp, **chi phí lưu
trữ mới là thứ giết biên lợi nhuận**, không phải giá giờ GPU. Điều đó củng cố
`V-001③` (gộp lô, dùng đều) bằng một con số thứ hai.

---

## 6. Cổng của P03 — đối chiếu với `NON_NEGOTIABLE_GATES`

| Yêu cầu | Trạng thái |
|---|---|
| BOM đủ (từng tệp, không lấy dung lượng cả kho) | ✅ `MODEL_BOM_FINAL.csv` |
| Giá đã hỏi **live** | ✅ hỏi **hai lần** 04/09, trùng nhau · ⛔ P04 hỏi lại |
| Dự phóng tổng ≤ $150/tháng | ✅ **$150,00** đúng trần, tính trên trường hợp xấu |
| A100 PCIe 80GB có hàng / có phương án dự phòng ghi rõ | ⚠️ **P04 kiểm live**; ba đường ở `CLOUD_RESOURCE_PLAN.md` §7 |
| Có kế hoạch chặn chi phí **trước** tài nguyên trả tiền | ✅ `CLOUD_SAFETY_PLAN.md` |
