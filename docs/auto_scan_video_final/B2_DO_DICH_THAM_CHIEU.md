# B2 — Bộ đo dịch: xác thực **trước**, rồi cho MetricX **đấu** với bộ chấm tự nặn

> Làn `do-dich`, 24–25/09/2026. Bằng chứng thô: `bang_chung/b2_do_dich_tho.json` ·
> `bang_chung/b2_do_dich_cuoc_dau.json` · `bang_chung/b2_do_dich_ghep.json`.
> Dựng lại: `tools/bench_b2_dich_tham_chieu.py`.

---

# 🔴 ĐỌC TRƯỚC — hai giới hạn treo trên **MỌI** con số dưới đây

⛔ **Không ai được trích một bảng nào trong tài liệu này mà bỏ mục này.**
Hai giới hạn **cộng dồn**, ⛔ không thay thế nhau.

## 🔴 (1) Vòng tròn LLM — sân đấu có thể đang đo **độ giống nhau giữa hai LLM**

Chân lý nền của sân đấu là phán quyết của **hai người soi — và cả hai đều là LLM**
(chính hai tệp bằng chứng tự khai vậy). Bộ chấm **V3 cũng là một LLM** chấm bằng
lời nhắc. MetricX là một model **hồi quy tinh chỉnh**, khác họ. ⇒ Nếu vòng tròn này
là thật thì:

- V3 thắng ⛔ **không** chứng minh V3 **tốt hơn** — chỉ chứng minh V3 **giống người chấm hơn**;
- MetricX thua ⛔ **không** chứng minh MetricX **kém** — có thể nó **bất đồng với một chân lý nền sai**.

⚠️ Và đồng thuận giữa hai người soi (30 dòng chung, bất đồng 2/30) cho
**kappa 0,714 nhưng KTC95 [0,00 ; 1,00]** ⇒ ⭐ **chân lý nền của ta chưa bao giờ được ghim.**

⛔ Làn này ⛔ **không** tự giải vòng tròn — điều phối đang mang câu hỏi *"phá vòng
tròn bằng cách nào"* tới chủ dự án.

## 🔴 (2) HAI CÁCH đo báo động giả — ⛔ hai ĐƠN VỊ, ⛔ không so trực tiếp

```
cách CŨ  — giả định "FLORES luôn đúng": mọi cờ trên FLORES = báo động giả
           ⇒ mang sẵn sàn lỗi FLORES bên trong. Một bộ chấm HOÀN HẢO cũng
             trượt: trần 23 % > ngưỡng 15 % ở định nghĩa rộng nhất.
           V1 43,3 %  ·  V2 16,7 %  ·  V3 23,3 %

cách MỚI — đối chiếu phán quyết NGƯỜI SOI MÙ (ghi trước, mù, đã commit)
           V3 33 %  ·  MetricX QE 39 %  (cùng ngân sách 43 cờ)
```

⭐ **Mọi bảng trong tài liệu này dùng CÁCH MỚI**, và mỗi bảng đều được **dán nhãn**.
⛔ Câu kiểu *"V3 tăng từ 23,3 % lên 33 %"* là **SAI** — hai số khác thước, và
V3 ⛔ **không hề tệ đi**.

---

## §0. Bộ đo nào, nguồn, giấy phép

| Lớp | Công cụ | Nguồn | Giấy phép | Trạng thái |
|---|---|---|---|---|
| Điểm dịch (QE **và** tham chiếu) | **MetricX-24-Hybrid-Large** `v2p6-bfloat16` | `google-research/metricx` @ `fc4978eb` · HF @ `febb720e` | **Apache-2.0** (mã + weights) | ⭐ đã có sẵn trong kho, `qc-venv` |
| chrF / chrF++ / BLEU | **`sacrebleu` 2.6.0** | `mjpost/sacrebleu` | **Apache-2.0** | ✅ **đã cài + đã khai** (§5) |
| Khoảng tin cậy | `scipy.stats.bootstrap` (BCa, 10 000 lượt) | PyPI | BSD-3-Clause | đã có |
| Đếm 2×2 · KTC tỉ lệ · kappa | `tools/do_luong.py` | trong kho, `main` | — | ⭐ **cùng một thước cho cả hai bên** |
| COMET / xCOMET / CometKiwi | — | — | **CC BY-NC-SA 4.0** | ⛔ **LOẠI** |

⭐ **Không tự viết lớp TÍNH.** Phần làn này viết chỉ là lớp **NỐI**.

⭐ **Hai chế độ, một checkpoint.** `metricx-24-**hybrid**` huấn luyện cho cả hai:
`QE = "source: {zh} candidate: {vi}"` · `tham chiếu = … + " reference: {vi_người}"`.
Định dạng lấy **y nguyên** từ `metricx24/predict.py` ở đúng commit đã ghim.
Đường QC sản phẩm (QE) ⛔ **không bị đụng**; runner tham chiếu là tệp riêng.

⭐ **Chế độ dùng được thật là QE** — phim khách ⛔ không có bản dịch đối chiếu.

---

## §1. Bước A — XÁC THỰC bộ đo

> 🏷️ **Phép TIÊM LỖI.** ⛔ Không thuộc cách cũ hay cách mới: ở đây ⛔ không có mẫu
> số báo động giả nào cả — ta **biết** dòng nào bị làm hỏng vì **chính ta làm hỏng**.

100 dòng FLORES-200 dev (zh→vi), hạt giống `20260924`. MQM `[0,25]`, **thấp là tốt**.

| mức | QE: t.bình (KTC95) | tham chiếu: t.bình (KTC95) |
|---|---|---|
| `trần` (bản dịch người) | **1,922** [1,649 ; 2,276] | **0,888** [0,769 ; 1,073] |
| `nhẹ` (hoán vị / bỏ một từ) | 2,556 [2,222 ; 2,978] | 1,772 [1,539 ; 2,074] |
| `nặng` (lật nghĩa / sai thực thể) | 4,627 [4,153 ; 5,110] | 4,508 [4,128 ; 4,882] |
| `sàn` (bản dịch dòng KHÁC) | **17,215** [16,193 ; 18,210] | **20,826** [20,043 ; 21,519] |

### ⭐ Trần vs nhiễu nhẹ — **tách được**

KTC của **hiệu THEO CẶP** (bốn mức trên cùng tập dòng ⇒ bốc theo cặp khử nhiễu
độ-khó-của-dòng). Tách được ⇔ KTC ⛔ không chứa 0.

| bước | QE: hiệu (KTC95) | tham chiếu: hiệu (KTC95) |
|---|---|---|
| `trần`→`nhẹ` | **0,634** [0,488 ; 0,833] ✅ | **0,884** [0,715 ; 1,160] ✅ |
| `nhẹ`→`nặng` | 2,071 [1,590 ; 2,512] ✅ | 2,737 [2,274 ; 3,148] ✅ |
| `nặng`→`sàn` | 12,588 [11,405 ; 13,731] ✅ | 16,317 [15,412 ; 17,154] ✅ |

Tỉ lệ **dòng** xếp đúng hướng ở `trần`→`nhẹ`: **90 %** (QE) · **99 %** (tham chiếu).
⇒ **Bốn mức xếp ĐÚNG thứ tự ở cả hai chế độ, và `trần` tách khỏi `nhẹ`.** ✅

### ⭐ Vế hai — chạy một **HỆ HOÀN HẢO** qua cổng

Tiêm lỗi chứng minh cổng biết nói **ĐỎ**; hệ hoàn hảo chứng minh nó biết nói **XANH**.
Ở ngưỡng **sản phẩm** `NGUONG_DO[("zh","vi")] = 6,0`, đưa chính bản dịch **người** qua:

> 🏷️ **CÁCH MỚI.** ⭐ Dòng **duy nhất** MetricX gắn cờ **LÀ một lỗi thật** (người soi mù
> gọi `ro`) ⇒ FP = **0**. Dưới **cách cũ** con số này sẽ hiện là *"1 % báo động giả"*
> — ⛔ và đó là một quy kết SAI cho một lần bắt ĐÚNG.

| | cờ | TP | FP | **BĐG (FP/n)** | độ nhạy |
|---|---|---|---|---|---|
| MetricX QE @ 6,0 | 1 | **1** | **0** | ✅ **0,0 %** [0,0 ; 3,7] | ⛔ 10 % [1,8 ; 40,4] |

✅ **Cổng biết nói XANH** — ⛔ không phải ca *"trần 0,606 dưới chính ngưỡng 0,80"*.
⚠️ Nhưng ngưỡng 6,0 mua sự sạch sẽ ấy bằng **độ nhạy**. Cùng ngưỡng, tỉ lệ bắt (tiêm lỗi):

| mức | QE | tham chiếu |
|---|---|---|
| `nhẹ` | 7/100 | 3/100 |
| `nặng` | 30/100 | 22/100 |
| `sàn` | **99/100** | **100/100** |

⇒ Ở ngưỡng sản phẩm, MetricX là **bộ bắt hỏng THÔ**: gần như chắc chắn bắt
"không dịch / dịch nhầm cả câu", ~1/4–1/3 lật nghĩa, ⛔ **gần như mù với nhiễu nhẹ**.

---

## §2. ⭐ Bước B — CUỘC ĐẤU trên 100 dòng đã SOI MÙ

> 🏷️ **CÁCH MỚI** — đối chiếu phán quyết soi mù, ghi **trước**, **mù**, **đã commit**
> (`bang_chung/b2_san_loi_flores.json`). ⛔ Không so với bảng cách cũ.

100 dòng FLORES (500–899): **10 `lỗi rõ`** · 2 `zh_lệch` · 11 `biên` · 77 `không lỗi`.
Ứng viên là **chính bản dịch người** — đúng thứ người soi đã phán quyết.
Cùng thước qua `tools/do_luong.py`. Định nghĩa "lỗi thật" = `chinh` (`ro`).

### Đối đầu ở **cùng ngân sách gắn cờ** (43 cờ — đúng bằng V3)

| | cờ | TP | FP | BĐG (FP/n) | độ nhạy |
|---|---|---|---|---|---|
| **V3 (tự nặn)** | 43 | **10** | 33 | **33,0 %** ⛔ | **10/10 = 100 %** ✅ |
| MetricX **QE** | 43 | 4 | 39 | 39,0 % ⛔ | 4/10 = 40 % ⛔ |
| MetricX **tham chiếu** | 43 | 3 | 40 | 40,0 % ⛔ | 3/10 = 30 % ⛔ |
| *đoán mù* | *43* | *~4,3* | *~38,7* | *~38,7 %* | *~43 %* |

⛔ **Không một ngưỡng nào**, ở **cả hai** chế độ, qua được đồng thời BĐG ≤ 15 % **và**
độ nhạy ≥ 50 %. Fisher cho độ nhạy: QE 4/10 vs V3 10/10 **p = 0,011**; tham chiếu **p = 0,0031**.

### ⭐ MetricX ⛔ không phân biệt được gì trên sân này

| chế độ | AUC | KTC95 |
|---|---|---|
| QE | 0,646 | **[0,424 ; 0,849]** |
| tham chiếu | 0,618 | **[0,412 ; 0,816]** |

⭐ **KTC cả hai đều CHỨA 0,5** ⇒ ⛔ không phân biệt được với **đoán mù**; TP=4 ở ngân
sách 43 đúng bằng kỳ vọng ngẫu nhiên (~4,3).

**Chống chỉnh-trên-bài-thi:** chọn ngưỡng trên một nửa (phân tầng), báo trên nửa kia,
hai chiều ⇒ ⛔ **không nửa nào có ngưỡng qua cổng để mà đem đi báo.**

---

## §3. ⭐ Phép GHÉP — **đã đo, và nó ⛔ KHÔNG trả công**

> 🏷️ **CÁCH MỚI.** Đề nghị của chính làn này ở bản trước: *MetricX @6,0 lọc trước,
> V3 xử phần dư.* ⭐ **Đo rồi: ⛔ không trả công.**

| cấu hình | cờ | TP | FP | BĐG (FP/n) | độ nhạy |
|---|---|---|---|---|---|
| MetricX QE @6,0 một mình | 1 | 1 | 0 | ✅ 0,0 % [0,0 ; 3,7] | ⛔ 10 % |
| V3 một mình | 43 | 10 | 33 | ⛔ 33,0 % [24,6 ; 42,7] | ✅ 100 % |
| **ghép `hợp`** (thác nước thật) | 43 | 10 | 33 | ⛔ 33,0 % [24,6 ; 42,7] | ✅ 100 % |
| **ghép `giao`** (MetricX phủ quyết) | 1 | 1 | 0 | ✅ 0,0 % | ⛔ 10 % |

⭐ **Ghép `hợp` giống V3 một mình ĐẾN TỪNG Ô.** Dòng duy nhất MetricX gắn cờ thì
V3 **đã gắn rồi** ⇒ MetricX ⛔ không thêm một phát hiện nào, và tiết kiệm lời gọi V3
được **1/100 = 1,0 %** — ⛔ không đáng một tầng kiến trúc.
Ghép `giao` hạ BĐG về 0 % nhưng ⛔ **vứt 9/10 lỗi** — trượt cổng độ nhạy.

⚠️ **Nhưng sân này ⛔ KHÔNG kiểm được cái lợi mà phép ghép được đề nghị vì nó.**
Sân toàn lỗi **tự nhiên, tinh vi** trong một bản dịch **người**; nó có **0 dòng**
mức `sàn` (không dịch / dịch nhầm cả câu) — tức ⛔ **không có** đúng loại hỏng mà
MetricX bắt giỏi (**99 %**, §1). ⇒ Bảng trên là một **cận dưới**, ⛔ không phải phán quyết.

⭐ **Kết luận đúng:** phép ghép ⛔ **không được biện minh bởi dữ liệu hiện có**. Muốn
biện minh nó thì phải có một sân **chứa ca thảm hoạ thật** (đoạn phim khách bị bỏ
dịch / sót chữ Hán) — ⛔ sân đó chưa tồn tại.

---

## §4. Phán quyết

⭐ **MetricX THUA cuộc đấu** — kết cục 3: *ta có bằng chứng bộ chấm tự nặn là
**cần thiết**, ⛔ không phải một lựa chọn tuỳ hứng.*

⛔ **Nhưng ⛔ không phải "V3 đạt".** V3 **cũng trượt** (33 % > 15 %).
⇒ **⛔ Chưa bên nào qua cổng**, MetricX ⛔ không phải đường tắt để bỏ V3,
và ⛔ **phép ghép cũng không** (§3).

| | MetricX QE @6,0 | V3 (tự nặn) |
|---|---|---|
| Không dịch / nhầm cả câu (`sàn`) | ✅ **99 %** | *(chưa đo)* |
| Lật nghĩa · sai thực thể (`nặng`) | ⚠️ 30 % | *(chưa đo)* |
| Nhiễu nhẹ | ⛔ 7 % | *(chưa đo)* |
| Lỗi tự nhiên tinh vi (bản người) | ⛔ **ngang đoán mù** | ✅ 10/10 ⚠️ *(có thể do cùng họ — mục 🔴 (1))* |
| Báo động giả (cách mới) | ✅ **0 %** | ⛔ **33 %** |

🔴 **Và toàn bộ bảng này treo trên mục 🔴 (1).** Nếu chân lý nền đang đo độ giống
nhau giữa hai LLM thì cột phải ⛔ không đọc được như năng lực.

---

## §4b. 🔴 KẾT LUẬN CẤP HẠNG MỤC — ⭐ đây là thứ phải sống sót khỏi tài liệu này

> # ⭐ Ta ⛔ KHÔNG có cổng chất lượng TỰ ĐỘNG ở ĐẦU TRÊN.

| bộ đo | làm được | ⛔ không làm được |
|---|---|---|
| **`chrF++`** | xếp hạng được; ⭐ **ngoài vòng tròn LLM** | ⛔ **cần bản tham chiếu** ⇒ ⛔ vô dụng với phim khách |
| **MetricX QE** | bắt **thảm hoạ**; ⛔ không cần tham chiếu | ⛔ **mù ở đầu trên** (§1 · §2 · §6, ba phép độc lập) |
| **bộ chấm V3** | **sàng** — độ nhạy 100 % (trên 2/35 họ lỗi) | ⛔ trượt cả hai cổng; **oan 33 %** |
| **điều phối chấm tay** | phân biệt được thật | ⛔ **không tự động hoá được** |

⇒ 🔴 **Với phim KHÁCH — nơi ⛔ KHÔNG có bản tham chiếu — ta chỉ phát hiện được
THẢM HOẠ, ⛔ không phân biệt được *"tốt"* với *"rất tốt"*.**

⭐ Đó là một **RÀNG BUỘC SẢN PHẨM**, ⛔ **không phải** một việc còn dang dở. Nó
quyết định **màn hình chất lượng cho khách được phép nói gì**:

- ✅ Được nói: *"⛔ không phát hiện lỗi nghiêm trọng"* (không dịch, sót chữ Hán,
  lệch hoàn toàn) — ta đo được điều đó, và đo tốt (mức `sàn`: 99–100 %).
- ⛔ **Không được nói:** *"bản dịch đạt chất lượng cao"* / một **điểm số** / một
  **xếp hạng sao** — ⛔ ta ⛔ **không có** bộ đo tự động nào chống đỡ được câu ấy.

⚠️ Và ⛔ đừng đọc §6 thành *"ta dịch ngang người"*: cả ba KTC chứa 0 vì **bộ đo mù**,
⛔ **không phải** vì **ta giỏi**. Hai câu ấy cùng dữ liệu nhưng ngược chiều —
⛔ để câu sai lọt là hỏng cả hạng mục.

---

## §5. ✅ `sacrebleu` — đã cài + đã khai

| gói | vai | giấy phép | khai ở đâu |
|---|---|---|---|
| `sacrebleu==2.6.0` | chrF/chrF++/BLEU | **Apache-2.0** | `requirements-dev.txt` + `THIRD_PARTY_METRICS.md` §1 #11 |
| `tabulate==0.10.0` | phụ thuộc | **MIT** | `requirements-dev.txt` |
| `portalocker==2.10.1` | phụ thuộc | **BSD-3-Clause** | `requirements-dev.txt` *(đã có sẵn)* |
| `pywin32>=306,<400` | ⚠️ phụ thuộc **của `portalocker`** | PSF-2.0 | `requirements.txt` *(đã có sẵn)* |

🔴 **Khai CẢ CHUỖI, không chỉ gói đầu.** `sacrebleu` → `tabulate` + `portalocker`
→ **`pywin32`** — đúng cái gói vừa làm **sập production 15 phút** vì có mặt trong
venv phát triển mà ⛔ không ai khai. Lượt này **không kéo thêm gói mới nào** (cả ba
đã có trong máy), nhưng **hai dòng chưa từng được khai** (`sacrebleu`, `tabulate`)
nay đã khai.

⭐ Đã kiểm: `THIRD_PARTY_NOTICES.md` là tệp **riêng của LTT Nexus** (nghĩa vụ AGPL khi
**phân phối**) ⇒ ⛔ không phải chỗ của một công cụ đo chỉ chạy lúc phát triển.
Sổ đúng là `THIRD_PARTY_METRICS.md` — *"mỗi câu hỏi hỏi đúng MỘT chỗ"*.

---

## §6. ⭐ BẢN DỊCH CỦA TA trên **FLORES** — chrF++ (ngoài vòng tròn LLM) + MetricX QE

Nguồn: `bang_chung/b2_flores/flores_dich_ltt-3.5_100dong_3luot.json` (làn B2 sinh).
Cấu hình **ghi trong thân tệp**: `ltt-3.5` · **t = 0,0** · ✅ **ép lược đồ** · lời nhắc v3 ·
**100 dòng** FLORES dev (0–99) · **3 lượt** · 0 ô rỗng/300.
⭐ `tham_chieu_vi` ⛔ **không** đi vào lời nhắc — chỉ cột `zh` được gửi (⛔ không rò đáp án).
Lệnh: `flores-3luot`.

### ⚠️ Ba giới hạn — đọc **cùng** số, ⛔ không để cuối

1. **FLORES có ~10 % dòng lỗi rõ** (KTC [5,5 ; 17,4]) ⇒ *"khớp FLORES"* ⛔ không bằng *"đúng"*.
2. 🔴 **Tỉ lệ độ dài 0,897** (ta / tham chiếu, theo từ; từng lượt 0,906 · 0,891 · 0,897).
   ⭐ Một điểm chrF++ ⛔ **không có tỉ lệ độ dài đi kèm là một điểm ⛔ không đọc được** —
   nó lẫn **chất lượng** với **độ dài**. Lượt sinh **đầu** của tệp này đặt ngân sách
   18 âm tiết ⇒ tỉ lệ **0,41** ⇒ chrF++ khi ấy đo **ĐỘ NÉN**. Làn B2 đã sửa (ngân sách
   suy từ **NGUỒN**) ⇒ **0,90**. ⭐ Số dưới đây là của bản **đã sửa**.
3. **MetricX** ⛔ vẫn treo trên cảnh báo 🔴 (1) **vòng tròn LLM**; ⭐ **`chrF++` thì KHÔNG**.

### ⭐ chrF++ — **tín hiệu DUY NHẤT ⛔ không dính vòng tròn LLM**

So thẳng với **bản dịch NGƯỜI** của FLORES, ⛔ không qua một LLM nào.

| lượt | chrF++ (cụm) |
|---|---|
| 1 | 44,84 |
| 2 | 45,47 |
| 3 | 45,17 |
| ⭐ **trung vị** | **45,17** · khoảng **[44,84 ; 45,47]** (biên độ **0,63**) |

**Mốc neo trên CHÍNH 100 dòng ấy** — ⛔ một điểm chrF++ trần trụi không đọc được:

| mốc | chrF++ |
|---|---|
| **trần** — tham chiếu so với chính nó | 100,00 |
| ⭐ **bản dịch của ta** | **45,17** |
| **sàn** — bản dịch của một dòng KHÁC | 14,21 |
| để nguyên tiếng Trung (⛔ không dịch) | 3,34 |

⇒ Trên dải dùng được `[14,21 ; 100]`, bản dịch của ta ở **≈ 36 %** quãng đường.

⚠️ ⛔ **Đừng đọc 45,17 thành "đúng 45 %".** chrF++ **một tham chiếu** phạt nặng mọi
**diễn đạt khác mà vẫn đúng** — và tiếng Việt có rất nhiều cách nói cùng một ý.
Con số này đọc được theo **mốc neo** và theo **so sánh giữa các cấu hình**,
⛔ không đọc được như một tỉ lệ đúng/sai.

⭐ **Một phát hiện phụ đáng giữ:** đường dịch ⛔ **không tái lập** ở mức **đoạn**
(3 lượt khác nhau ở mọi đoạn), ⭐ **nhưng** chrF++ **cụm** gần như đứng yên
(biên độ **0,63** trên thang 100). ⇒ ⭐ *"Không tái lập"* ⛔ **không** kéo theo
*"số đo không ổn định"* — cái lắc nằm ở **cách diễn đạt**, ⛔ không ở **chất lượng tổng thể**.
⚠️ Điều này ⛔ **không** miễn cho ta luật ≥ 3 lượt: ta biết được nó **vì** đã chạy 3 lượt.

### 🔴 45,17 là TỐT hay TỆ? — **MỐC CÔNG BỐ đã tra được**

⭐ ⛔ Không đoán. `chrF++` trên FLORES là thứ **cả ngành đã đo và công bố**.

**Nguồn:** `naver/nllb-pruning` @ `a8d16434`, tệp `scores/FLORES-dev-53-3B.tsv` và
`scores/FLORES-dev-53-54B.tsv`. Cột: `direction · spBLEU · chrF++ · len_ratio`.
Dòng **nguyên văn** cho `zho_Hans-vie_Latn`:

```
FLORES-dev-53-3B.tsv    zho_Hans-vie_Latn   30.49   50.25   0.992
FLORES-dev-53-54B.tsv   zho_Hans-vie_Latn   32.07   51.19   0.970
```

| hệ | chrF++ | len_ratio |
|---|---|---|
| NLLB-200 **MoE 54B** | **51,19** | 0,970 |
| NLLB-200 **dense 3,3B** | **50,25** | 0,992 |
| ⭐ **ta — `ltt-3.5`** | **45,17** *(KTC95 bootstrap trên 100 dòng: [42,70 ; 47,57])* | **0,897** |

⇒ ⭐ **Ta thấp hơn NLLB-3,3B khoảng 5,1 điểm chrF++.** KTC95 của ta (trần **48,06**
ở lượt tốt nhất) ⛔ **không chạm tới 50,25** ⇒ khoảng cách ⛔ **không** giải thích
được chỉ bằng nhiễu lấy mẫu của 100 dòng.

⭐ **Và cột `len_ratio` của chính bảng công bố là một xác nhận độc lập:** ngành
coi **tỉ lệ độ dài** là thứ **phải đi kèm** điểm chrF++ — đúng luật ta vừa chốt.
NLLB dịch ở độ dài **gần ngang** tham chiếu (0,97–0,99); ta ở **0,897**, tức
**ngắn hơn ~10 %**. ⚠️ ⇒ **Một phần** khoảng cách 5,1 điểm là **ĐỘ DÀI**, ⛔ không
phải toàn bộ là chất lượng. ⛔ Chưa tách được hai phần ấy.

### ⚠️ Ba bẫy "mượn số" — chặn từng cái, ⛔ không mượn số mà bỏ điều kiện

| bẫy | trạng thái |
|---|---|
| **`chrF` ⛔ ≠ `chrF++`** | ✅ **khớp** — cột trong tệp tên đúng là `chrF++` |
| **`dev` hay `devtest`?** | ✅ **khớp** — tệp tên `FLORES-**dev**`, ta cũng dùng `dev` |
| **cùng bộ tham số `sacrebleu`?** | ⚠️ **⛔ CHƯA xác minh** — xem dưới |

- ⚠️ **Tham số `sacrebleu` của họ ⛔ không được khai.** README của repo chỉ ghi
  `pip install … sacrebleu --upgrade`, ⛔ không nêu phiên bản, cờ, hay chữ ký.
  Cột mang tên `chrF++` nên `word_order = 2` gần như chắc, nhưng ⛔ **chưa chắc**.
  **Chữ ký CỦA TA, khai ra để ai cũng so lại được:**
  ```
  nrefs:1|case:mixed|eff:yes|nc:6|nw:2|space:no|version:2.6.0
  ```
  (`CHRF(word_order=2)` — char_order 6, word_order 2, beta 2, ⛔ không lowercase,
  ⛔ không tính khoảng trắng, `corpus_score`.)
- 🔴 **Cỡ tập ⛔ KHÁC NHAU, và tập của ta ⛔ KHÔNG phải mẫu ngẫu nhiên.** Họ chấm
  trên **toàn bộ** `dev`; ta chấm trên **100 dòng ĐẦU (0–99)**. ⛔ 100 dòng đầu
  ⛔ không phải một mẫu ngẫu nhiên của `dev` ⇒ ngoài nhiễu lấy mẫu còn có thể có
  **lệch hệ thống** mà KTC bootstrap ⛔ **không** bắt được.
  ⇒ ⭐ Muốn khớp hoàn toàn thì phải dịch **cả 997 dòng** `dev`. ⛔ Chưa làm.
- ⚠️ **Hai hệ ⛔ không cùng loại việc.** NLLB là **model dịch chuyên dụng**; `ltt-3.5`
  là **LLM đa dụng chạy qua lời nhắc + ép lược đồ**, và trong sản phẩm nó còn phải
  giữ `ma`, cảm xúc, kiểu nói. ⛔ Khoảng cách 5,1 điểm ⛔ không đọc được thành
  *"đường dịch của ta hỏng"*.

⭐ **Nghĩa (kết cục 2 trong ba kết cục):** ta **thấp hơn hẳn** mức công bố, và nay
**biết còn bao xa** — ~5 điểm chrF++, trong đó **một phần là độ dài**. Đó là một
đích đo được, ⛔ không phải một cảm giác.

### MetricX QE trên cùng tệp — ⚠️ treo trên 🔴 (1) **vòng tròn LLM**

| lượt | trung vị | trung bình | vượt ngưỡng 6,0 |
|---|---|---|---|
| 1 | 1,832 | 2,484 | 7/100 |
| 2 | 1,797 | 2,563 | 10/100 |
| 3 | 1,797 | 2,363 | 6/100 |
| ⭐ **trung vị** | **1,797** · khoảng **[1,797 ; 1,832]** (biên độ **0,035**) | | |

**Mốc neo MetricX trên CHÍNH 100 dòng ấy** (cùng một lượt chấm):

| mốc | trung vị | vượt ngưỡng 6,0 |
|---|---|---|
| ⭐ **bản dịch của ta** | **1,797** | 6–10/100 |
| **bản dịch NGƯỜI của FLORES** | **2,234** | 6/100 |
| **sàn** — bản dịch dòng KHÁC | 16,06 | 94/100 |
| để nguyên tiếng Trung | 12,56 | 99/100 |

### 🔴 MetricX QE ⛔ KHÔNG phân biệt được bản dịch của ta với bản dịch NGƯỜI

Hiệu **theo cặp** (cùng 100 dòng), KTC95 bootstrap:

| lượt | hiệu (ta − người) | KTC95 | |
|---|---|---|---|
| 1 | −0,166 | [−0,563 ; +0,176] | ⛔ **KTC chứa 0** |
| 2 | −0,087 | [−0,426 ; +0,265] | ⛔ **KTC chứa 0** |
| 3 | −0,287 | [−0,688 ; +0,068] | ⛔ **KTC chứa 0** |

⛔ **Đừng đọc thành *"ta dịch ngang/hơn người"*.** Đọc đúng là: **MetricX QE ⛔ không
có đủ độ phân giải ở ĐẦU TRÊN của thang** — nó tách **thảm hoạ** (sàn 16,06 · tiếng
Trung 12,56) khỏi **bản dịch tốt** (~2) cực giỏi, nhưng ⛔ **không xếp hạng được hai
bản dịch đều tốt**.

⭐ Điều này **ăn khớp** với hai kết quả trước, ⛔ không mâu thuẫn:
- §1: ở ngưỡng 6,0 MetricX chỉ bắt **7/100** nhiễu **nhẹ** (mù với hỏng nhẹ);
- §2: trên lỗi **tự nhiên, tinh vi** MetricX **ngang đoán mù** (AUC KTC chứa 0,5).

⇒ ⭐ **Cùng một tính chất, đo được ba lần bằng ba cách khác nhau.**

### ⭐ chrF++ và MetricX có ĐỒNG THUẬN không? — **đồng thuận YẾU**

Spearman từng dòng (âm = đồng thuận, vì chrF++ cao là tốt còn MetricX thấp là tốt):

```
luot 1 −0,357 · luot 2 −0,293 · luot 3 −0,290   ⇒ trung vị −0,293
```

⭐ Đúng chiều, nhưng **|ρ| ≈ 0,29 là YẾU**. ⇒ Hai bộ đo **nhìn hai thứ khác nhau**:
chrF++ đo **trùng khớp bề mặt** với một bản dịch người; MetricX đo **lỗi ngữ nghĩa
dự đoán** ⛔ không cần tham chiếu. ⚠️ **Bất đồng ⛔ không phải lỗi** — nó là thông tin
ta chưa có, và nó nói rằng ⛔ **không được thay bộ đo này bằng bộ đo kia**.

### ⭐ Độ ổn định CỤM — MetricX nay **tự chứng minh**

| bộ đo | biên độ qua 3 lượt | thang |
|---|---|---|
| chrF++ (cụm) | **0,63** | 0–100 |
| MetricX QE (trung vị) | **0,035** | 0–25 |

⇒ ⭐ Kết luận *"⛔ không tái lập ở mức ĐOẠN ⛔ không kéo theo số đo cụm không ổn định"*
nay đúng cho **cả hai** bộ đo — và ⭐ **mỗi bộ đo tự chứng minh phần của nó**, ⛔ không
khái quát từ bộ kia. ⚠️ Ta biết được ⇒ **vì** đã chạy 3 lượt: luật ≥ 3 lượt giữ nguyên.

---

## §6b. Đo bản dịch **đoạn phim** đã có — ⛔ không sinh bản mới

⭐ ⛔ Không đụng sổ khoá production. Đo thẳng bằng chứng **đã commit** của làn B2
(nhánh `phien/asvf-nghiem-thu-v2`, **chỉ đọc**). Lệnh: `qe-co-san`.

⚠️ **Đoạn phim ⛔ KHÔNG có bản dịch tham chiếu** ⇒ ở §6b này chỉ đo được **MetricX QE**;
chrF++ ⛔ không có gì để so. (Đó chính là lý do §6 phải chạy trên **FLORES**.)

### MetricX QE trên bản dịch đã có — **ba cấu hình, ⛔ KHÔNG gộp**

> 🏷️ Mọi số dưới đây là **MetricX QE** ⇒ **treo trên mục 🔴 (1)**. Ngưỡng sản phẩm
> `6,0`. **Thấp là tốt.**

| cấu hình | nguồn | đơn vị | n | trung vị | khoảng | qua ngưỡng 6,0 |
|---|---|---|---|---|---|---|
| **A** — lời nhắc v4, **t = 0,2**, ⛔ **không ép** | `b2_dich_nen/v{1,2,3}_nen` | 🔴 **3 PHIM khác nhau**, ⛔ không phải lượt lặp | 83 / 74 / 31 | 1,727 · 1,699 · 2,328 | ⛔ *không áp dụng* | 3/83 · 4/74 · 1/31 |
| **B** — **t = 0,0**, ⛔ không ép | `b2_lap_lai/…_lan3` | ✅ **3 lượt lặp** (phim v3) | 11 / 11 / 10 | **2,930** | [2,578 ; 3,125] | 2 · 1 · 0 |
| **C** — **t = 0,0**, ✅ **ÉP LƯỢC ĐỒ** *(cấu hình đã ghim)* | `b2_lap_lai/…_lan3_ep_seed20260925` | ✅ **3 lượt lặp** (phim v3) | 12 / 12 / 11 | **4,219** | [2,898 ; 4,297] | 3 · 1 · 5 |

🔴 **A ⛔ không có "trung vị + khoảng".** Ba tệp của A là **ba phim khác nhau**, mỗi
phim **một lượt** ⇒ khoảng giữa chúng đo **độ khó của phim**, ⛔ **không** đo độ
không tái lập. Gộp lại là dựng lại đúng lỗi *"hai con số từ hai tập khác nhau"*.
Công cụ nay **tự phát hiện và từ chối** in khoảng cho trường hợp này.

⛔ **KHÔNG được đọc bảng này thành "C tệ hơn B".** Ba lý do:
1. **n = 10–12** mỗi lượt, và KTC của các lượt **chồng lên nhau rất nhiều**
   (C lượt 3: [3,967 ; 10,767]). ⛔ Không tách được.
2. ⚠️ **Tập của B và C bị THIÊN LỆCH theo cùng một kiểu nhưng ⛔ không giống nhau:**
   cả hai lấy từ `chi_tiet_doan_DOI` — tức **chỉ những đoạn ĐÃ ĐỔI giữa các lượt**,
   ⛔ bỏ các đoạn ổn định. B: 11/12 đoạn đổi; C: 12/12. ⇒ Đây là **tập các đoạn khó
   nhất**, ⛔ không phải tập đại diện.
3. B và C ⛔ **không cùng tập đoạn** (11 vs 12, chọn khác nhau) ⇒ ⛔ không so cặp được.

⭐ **Thứ bảng này NÓI ĐƯỢC:** ở cả ba cấu hình, **trung vị nằm sâu dưới ngưỡng 6,0**
(1,7–4,2) và tỉ lệ vượt ngưỡng thấp (0–5 trên 10–83 đoạn) ⇒ ⛔ **không thấy dấu hiệu
sụp** của đường dịch theo thước MetricX QE. **Thứ nó ⛔ KHÔNG nói được:** cấu hình
nào tốt hơn cấu hình nào.

### ⚠️ Nhắc lại giới hạn đã đo

- **FLORES có ~10 % dòng lỗi rõ** (KTC [5,5 ; 17,4]) ⇒ *"khớp FLORES"* ⛔ **không** bằng *"đúng"*.
- Đường dịch **⛔ không tái lập được** (t 0,0 + ép lược đồ + seed vẫn cho ba bản
  khác nhau) ⇒ ⛔ **một lượt ⛔ không phải một con số** — đó là lý do bảng trên báo
  **trung vị + khoảng** ở đúng hai dòng có lượt lặp thật.

---

## §6b. (lịch sử) Hai nút chặn của bản trước — **đã gỡ**

Lệnh `bench` đã dựng xong và **đã kiểm chạy** (chrF++ qua 3 lượt giả, xếp hạng đúng
chiều; chặn `< 3 lượt` có hiệu lực):

```powershell
# chrF NHE => ⛔ khong can khoa
python tools\bench_b2_dich_tham_chieu.py bench --dich luot1.json luot2.json luot3.json --bo-metricx
# kem MetricX QE (NANG) => qua chay_nang.py, nha khoa ngay khi xong
python "C:\Users\Thang Tuong\.claude\ltt\chay_nang.py" --phien do-dich -- ^
  python tools\bench_b2_dich_tham_chieu.py bench --dich luot1.json luot2.json luot3.json
```

Bench **ép ≥ 3 lượt** và báo **trung vị + khoảng** cho **chrF++** và **MetricX QE**
**riêng rẽ** (⛔ không gộp thành một điểm), vì **đường dịch ⛔ không tái lập được**
(temp 0,0 + ép lược đồ + seed vẫn cho ba bản khác nhau ở **mọi** đoạn).

Bản trước nêu hai nút chặn; ⭐ **cả hai đã gỡ bằng cách RẺ hơn — ⛔ không xin quyền:**

1. ~~Ghim nhiệt độ chưa lên nhánh này~~ ⇒ ⛔ **không cần**: ta ⛔ không sinh bản dịch
   nữa, ta **đo bản đã sinh**, và bản ấy **đã** sinh dưới cấu hình đã ghim (cấu hình
   **C**). Thứ cần ⛔ không phải mã mà là **NHÃN cấu hình** — nhãn ấy nằm ngay trong
   **tên tệp + trường JSON** của bằng chứng (`temperature`, `ep_luoc_do`,
   `phien_ban_loi_nhac`), ⛔ nên không phải suy từ ngày giờ.
2. ~~Sinh bản dịch cần sổ khoá production~~ ⇒ ⛔ **không đụng tới**. ⭐ Bản dịch
   **đã tồn tại và đã commit** ⇒ ⛔ không mở một bề mặt quyền mới nào trên CSDL
   production.

⇒ Nút chặn **còn lại đúng một**, và nó ⛔ không phải quyền mà là **dữ liệu**:
⛔ chưa ai dịch **FLORES** dưới cấu hình đã ghim ⇒ ⛔ chưa có chrF++ (xem §6).

---

## §6c. ⭐ Bao nhiêu trong 5,1 điểm là **ĐỘ DÀI**, bao nhiêu là **CHẤT LƯỢNG**?

Phép **rẻ**, ⛔ không sinh lại gì: trên **chính 300 bản dịch đã có** (100 dòng × 3 lượt),
tính chrF++ **cụm theo nhóm `len_ratio`**.

| nhóm `len_ratio` | n | **chrF++ cụm** | `len_ratio` trung vị | tham chiếu (số từ, tv) |
|---|---|---|---|---|
| **< 0,85** | 114 | **39,31** | 0,741 | 31,0 |
| **0,85–0,95** | 71 | **48,42** | 0,900 | 29,0 |
| **≥ 0,95** | 115 | **49,85** | 1,130 | 25,0 |

⭐ **Nhóm gần độ dài tham chiếu đạt 49,85 — gần như ĐÚNG mức NLLB (50,25).**
Nhóm ngắn hơn 15 % kéo tụt xuống **39,31**.

### ⚠️ Khử bớt nhiễu lẫn — cùng một bảng, nhưng **khống chế độ dài câu**

Câu **ngắn** có `len_ratio` **cao** hơn (Spearman `len_ratio` vs số từ tham chiếu
= **−0,271**) ⇒ ⚠️ nhóm `≥ 0,95` có thể chỉ đang chứa **câu dễ**. Lọc chỉ giữ câu
tham chiếu **22–32 từ** (trung vị ba nhóm bằng nhau, ~29 từ):

| nhóm `len_ratio` | n | **chrF++ cụm** | tham chiếu (số từ, tv) |
|---|---|---|---|
| < 0,85 | 43 | **42,90** | 29,0 |
| 0,85–0,95 | 18 | **45,59** | 28,5 |
| ≥ 0,95 | 62 | **50,85** | 29,0 |

⇒ ⭐ Khống chế độ dài câu rồi, **thứ bậc vẫn giữ và khoảng cách vẫn ~8 điểm**.

### 🔴 Đây là **GỢI Ý**, ⛔ KHÔNG phải phép đo nhân quả

⛔ **Không kết luận nhân quả từ tương quan.** Vẫn còn ít nhất hai lối thoát:
1. ⚠️ Một bản dịch **ngắn** có thể ngắn **vì nó bỏ mất nội dung** — khi ấy điểm thấp
   là **chất lượng thật**, ⛔ không phải hình phạt độ dài. Hai thứ ⛔ **không tách
   được** bằng phép này.
2. ⚠️ `n` của nhóm giữa chỉ **18** sau khi lọc — ⛔ mỏng.

⭐ **Phép THẬT là: nới ngân sách độ dài rồi ĐO LẠI** — và đó là việc của **làn dịch**,
⛔ không phải của làn này. Cái làn này làm được là **chỉ đúng chỗ đáng nới**.

---

## §6d. ⚠️ CĂNG THẲNG MỞ — ⛔ làn này ⛔ KHÔNG tự giải

> 🔑 **Chất lượng DỊCH và độ vừa KHE LỒNG TIẾNG kéo NGƯỢC nhau, và ta ⛔ chưa từng
> đo cái giá của việc đánh đổi.**

Ngân sách độ dài ⛔ **không tuỳ tiện** — nó tồn tại vì **khe lồng tiếng**. §6c cho
thấy **nới** nó thì chrF++ **tăng** (có thể tới ~+8 điểm ở nhóm dài). ⚠️ **Nhưng**
**73,9 % khe vốn đã ⛔ KHÔNG vừa**, và câu dài hơn sẽ làm chúng **càng chật**.

⇒ Câu hỏi **mở**, cần số từ **CẢ HAI** phía, ⛔ chưa ai có:

- Nới ngân sách thêm **x %** ⇒ chrF++ **+ bao nhiêu**?
- Cùng mức nới ấy ⇒ tỉ lệ khe ⛔ không vừa **+ bao nhiêu**?
- ⭐ Có một mức nào mà **chrF++ tăng đáng kể** trong khi **khe xấu đi không đáng kể** không?

⛔ Làn này ⛔ **không** trả lời — nó chỉ **đặt** câu hỏi và cung cấp **vế chrF++**.
Vế **khe** thuộc làn đang đo **nắn thời lượng**; điều phối sẽ nối hai làn.

---

## §7. Chạy lại

```powershell
# 1. buoc TINH (nang) — giu khoa dung lenh tinh, nha ngay khi xong
python "C:\Users\Thang Tuong\.claude\ltt\chay_nang.py" --phien do-dich -- ^
  python -X utf8 tools\bench_b2_dich_tham_chieu.py cham-tho ^
  --n 100 --nhan <...>\b2_san_loi_flores.json --ra tho.json

# 2. phan tich (nhe — NGOAI khoa)
python tools\bench_b2_dich_tham_chieu.py xac-thuc --tho tho.json
python tools\bench_b2_dich_tham_chieu.py doi  --tho tho.json --nhan <...>\b2_san_loi_flores.json
python tools\bench_b2_dich_tham_chieu.py ghep --tho tho.json --nhan <...>\b2_san_loi_flores.json ^
  --v3 <...>\b2_cham_v3_tren_100_dong_soi_mu.json
```

⚠️ `doc_flores()` + hai phép làm hỏng "nặng" nằm ở `tools/bench_b2_xac_thuc_bo_cham.py`
(**làn khác sở hữu**, chưa lên `main`) ⇒ trỏ `LTT_XAC_THUC_DIR` vào thư mục chứa nó.
⛔ Đừng viết bộ đọc FLORES mới.

Lượt đã chạy: **cuda**, bf16, lô 16 — 1 000 cặp trong **58 giây**, khoá giữ **1,0 phút**.
