# B2 — Bộ đo dịch: xác thực **trước**, rồi cho MetricX **đấu** với bộ chấm tự nặn

> Làn `do-dich`, 24–25/09/2026. Bằng chứng thô:
> `bang_chung/b2_do_dich_tho.json` (điểm từng cặp) ·
> `bang_chung/b2_do_dich_cuoc_dau.json` (cả đường cong ngưỡng).
> Dựng lại: `tools/bench_b2_dich_tham_chieu.py` (`cham-tho` → `xac-thuc` → `doi`).

⛔ **Chưa đo bản dịch của ta.** Đường dịch đang được sửa (ghim nhiệt độ + chuyển
`ltt-3.5`) ⇒ đo bây giờ là đo một cấu hình sắp biến mất. Lệnh `bench` đã dựng sẵn,
chạy một lệnh khi điều phối gọi.

## §0. Bộ đo nào, nguồn, giấy phép

| Lớp | Công cụ | Nguồn | Giấy phép | Trạng thái |
|---|---|---|---|---|
| Điểm dịch (QE **và** tham chiếu) | **MetricX-24-Hybrid-Large** `v2p6-bfloat16` | `google-research/metricx` @ `fc4978eb` · HF `google/metricx-24-hybrid-large-v2p6-bfloat16` @ `febb720e` | **Apache-2.0** (mã **và** weights) | ⭐ **đã có trong kho**, chạy trong `qc-venv`, đã khai `THIRD_PARTY_METRICS.md` §1 #6 |
| Khoảng tin cậy | `scipy.stats.bootstrap` (BCa, 10 000 lượt) | PyPI | BSD-3-Clause | đã cài |
| Đếm 2×2 · KTC tỉ lệ · kappa | `tools/do_luong.py` (`sklearn` + `scipy`) | trong kho, trên `main` | — | ⭐ **cùng một thước cho cả hai bên** |
| chrF / chrF++ / BLEU | `sacrebleu` | `mjpost/sacrebleu` | **Apache-2.0** | ⛔ **CHƯA CÀI — chờ chủ dự án duyệt** (xem §5) |
| COMET / xCOMET / CometKiwi | — | — | **CC BY-NC-SA 4.0** | ⛔ **LOẠI** (`THIRD_PARTY_METRICS.md` §2) |

⭐ **Không tự viết lớp TÍNH.** Thứ làn này viết chỉ là lớp **NỐI**: chọn câu, làm
hỏng "nhẹ", ghép mức "sàn", gọi runner, xếp bảng.

⭐ **Hai chế độ, một checkpoint.** `metricx-24-**hybrid**` được huấn luyện cho cả hai:

```
QE          : "source: {zh} candidate: {vi}"
tham chiếu  : "source: {zh} candidate: {vi} reference: {vi_người}"
```

Định dạng lấy **y nguyên** từ `metricx24/predict.py::get_dataset._make_input` ở đúng
commit đã ghim — ⛔ không tự bịa. Đường QC sản phẩm (`apps/asv_gpu/do_luong/metricx.py`)
chạy **QE** và ⛔ **không bị tệp này đụng vào**; runner tham chiếu là tệp riêng
(`tools/_metricx_tham_chieu_runner.py`) dùng lại `ban_ghim.py` + `mt5_regression.py`.

⭐ **Chế độ dùng được thật là QE.** Phim khách ⛔ không có bản dịch đối chiếu. Chế độ
tham chiếu chỉ chạy được ở nơi đã có bản dịch người (FLORES) ⇒ nó là công cụ **đo
bộ đo**, không phải công cụ vận hành.

---

## §1. Bước A — XÁC THỰC bộ đo (bảng bốn mức)

100 dòng FLORES-200 dev (zh→vi), mỗi dòng đủ cả bốn mức, hạt giống `20260924`.
Điểm MQM `[0,25]`, **thấp là tốt**. KTC95 bootstrap BCa.

### MetricX — chế độ **QE** (không tham chiếu)

| mức | n | trung bình | trung vị | KTC95 |
|---|---|---|---|---|
| `trần` (bản dịch người) | 100 | **1,922** | 1,422 | [1,649 ; 2,276] |
| `nhẹ` (hoán vị / bỏ một từ) | 100 | 2,556 | 2,148 | [2,222 ; 2,978] |
| `nặng` (lật nghĩa / sai thực thể) | 100 | 4,627 | 4,328 | [4,153 ; 5,110] |
| `sàn` (bản dịch của dòng KHÁC) | 100 | **17,215** | 17,312 | [16,193 ; 18,210] |

### MetricX — chế độ **tham chiếu**

| mức | n | trung bình | trung vị | KTC95 |
|---|---|---|---|---|
| `trần` | 100 | **0,888** | 0,699 | [0,769 ; 1,073] |
| `nhẹ` | 100 | 1,772 | 1,438 | [1,539 ; 2,074] |
| `nặng` | 100 | 4,508 | 4,625 | [4,128 ; 4,882] |
| `sàn` | 100 | **20,826** | 21,500 | [20,043 ; 21,519] |

### ⭐ Trần vs nhiễu nhẹ — **tách được**

KTC của **hiệu THEO CẶP** (bốn mức đo trên cùng tập dòng ⇒ bốc theo cặp khử được
nhiễu độ-khó-của-dòng). Tách được ⇔ KTC ⛔ không chứa 0.

| bước | QE: hiệu (KTC95) | tách? | tham chiếu: hiệu (KTC95) | tách? |
|---|---|---|---|---|
| `trần`→`nhẹ` | **0,634** [0,488 ; 0,833] | ✅ | **0,884** [0,715 ; 1,160] | ✅ |
| `nhẹ`→`nặng` | 2,071 [1,590 ; 2,512] | ✅ | 2,737 [2,274 ; 3,148] | ✅ |
| `nặng`→`sàn` | 12,588 [11,405 ; 13,731] | ✅ | 16,317 [15,412 ; 17,154] | ✅ |

Tỉ lệ **dòng** xếp đúng hướng ở bước `trần`→`nhẹ`: **90 %** (QE) · **99 %** (tham chiếu).

⇒ **Bốn mức xếp ĐÚNG thứ tự ở cả hai chế độ, và `trần` tách khỏi `nhẹ` ở cả hai.**

### ⭐ Vế hai — chạy một **HỆ HOÀN HẢO** qua cổng

Tiêm lỗi chứng minh cổng biết nói **ĐỎ**; hệ hoàn hảo chứng minh nó biết nói **XANH**.
Ở ngưỡng **sản phẩm** `NGUONG_DO[("zh","vi")] = 6,0`, đưa chính **bản dịch người**
của FLORES qua cổng:

| chế độ | bản dịch NGƯỜI bị đánh HỎNG | KTC95 |
|---|---|---|
| QE | **1/100 = 1,0 %** | [0,2 % ; 5,4 %] |
| tham chiếu | **0/100 = 0,0 %** | [0,0 % ; 3,7 %] |

✅ **Cổng biết nói XANH.** ⛔ Đây ⛔ không phải cái đã xảy ra với cổng bị bắt quả tang
hôm qua (trần 0,606 nằm dưới chính ngưỡng 0,80 của nó).

⚠️ Nhưng ngưỡng 6,0 **mua sự sạch sẽ ấy bằng độ nhạy**. Cùng ngưỡng đó, tỉ lệ bắt được:

| mức | QE | tham chiếu |
|---|---|---|
| `nhẹ` | 7/100 | 3/100 |
| `nặng` | 30/100 | 22/100 |
| `sàn` | **99/100** | **100/100** |

⇒ Ở ngưỡng sản phẩm, MetricX là **bộ bắt hỏng THÔ**: gần như chắc chắn bắt được
"không dịch / dịch nhầm cả câu", bắt được ~1/4–1/3 lật nghĩa & sai thực thể,
⛔ **gần như mù với nhiễu nhẹ**.

---

## §2. ⭐ Bước B — CUỘC ĐẤU trên 100 dòng đã SOI MÙ

**Sân đấu ⛔ không ai đổi luật giữa chừng:** phán quyết người soi ghi **trước**, **mù**,
**đã commit** (`bang_chung/b2_san_loi_flores.json`, nhánh `phien/asvf-xac-thuc`).
100 dòng FLORES (dải 500–899): **10 `lỗi rõ`** · 2 `zh_lệch` · 11 `biên` · 77 `không lỗi`.
Ứng viên là **chính bản dịch người** của FLORES — đúng thứ người soi đã phán quyết.
Định nghĩa "lỗi thật" = `chinh` (`ro`), **cùng một thước** cả hai bên qua `tools/do_luong.py`.

### Đường cong với đường cong, ⛔ không phải điểm tốt nhất với một điểm tồi

MetricX cho điểm liên tục ⇒ có cả một đường ngưỡng. Vài mốc (chế độ QE):

| ngưỡng | gắn cờ | TP | FP | BĐG (FP/n) | độ nhạy | qua cổng? |
|---|---|---|---|---|---|---|
| 0,598 | 17 | 0 | 17 | 17,0 % | 0,0 % | ⛔ |
| 0,809 | 36 | 3 | 33 | 33,0 % | 30,0 % | ⛔ |
| **0,965** | **43** | **4** | **39** | **39,0 %** | **40,0 %** | ⛔ |
| 1,648 | 66 | 5 | 61 | 61,0 % | 50,0 % | ⛔ |
| 2,938 | 89 | 7 | 82 | 82,0 % | 70,0 % | ⛔ |

⛔ **Không một ngưỡng nào** — ở **cả hai** chế độ — qua được đồng thời
BĐG ≤ 15 % **và** độ nhạy ≥ 50 %.

### Đối đầu ở **cùng ngân sách gắn cờ** (43 cờ — đúng bằng V3)

| | gắn cờ | TP | FP | BĐG (FP/n) | độ nhạy |
|---|---|---|---|---|---|
| **V3 (tự nặn)** | 43 | **10** | 33 | **33,0 %** ⛔ | **10/10 = 100 %** ✅ |
| MetricX **QE** | 43 | 4 | 39 | 39,0 % ⛔ | 4/10 = 40 % ⛔ |
| MetricX **tham chiếu** | 43 | 3 | 40 | 40,0 % ⛔ | 3/10 = 30 % ⛔ |
| *đoán mù* | *43* | *~4,3* | *~38,7* | *~38,7 %* | *~43 %* |

⇒ **V3 trội hơn MetricX trên CẢ HAI trục** ở cùng ngân sách. Fisher chính xác cho
độ nhạy: QE 4/10 vs V3 10/10 **p = 0,011**; tham chiếu 3/10 vs 10/10 **p = 0,0031**.

### ⭐ Và MetricX ⛔ không phân biệt được gì trên sân này

| chế độ | AUC | KTC95 |
|---|---|---|
| QE | 0,646 | **[0,424 ; 0,849]** |
| tham chiếu | 0,618 | **[0,412 ; 0,816]** |

⭐ **KTC của cả hai đều CHỨA 0,5.** Trên sân này ta ⛔ **không phân biệt được MetricX
với đoán mù** — và TP=4 ở ngân sách 43 đúng bằng kỳ vọng ngẫu nhiên (~4,3).

### Chống chỉnh-trên-bài-thi

Chọn ngưỡng trên một nửa (phân tầng theo nhãn), báo số trên nửa kia, hai chiều:
⛔ **không nửa nào có một ngưỡng qua được cổng để mà đem đi báo.** Phép này vì thế
⛔ không thêm thông tin — nó chỉ xác nhận ⛔ không có điểm vận hành nào để chỉnh.

---

## §3. ⚠️ Ba điều giữ cho cuộc đấu khỏi bị đọc quá rộng

1. ⭐ **Chế độ tham chiếu trên sân này là phép ĐỒNG NHẤT.** FLORES ⛔ không có bản
   dịch thứ hai, nên ứng viên **chính là** bản tham chiếu. Con số ấy đo một hằng số,
   ⛔ không đo năng lực — nó có mặt để **chứng minh** điều đó, ⛔ không để phán quyết.
   ⇒ Phán quyết của cuộc đấu đứng trên **chế độ QE**.
2. ⚠️ **Chân lý nền do LLM tạo ra.** Cả hai người soi đều là LLM — chính hai tệp bằng
   chứng tự khai vậy. V3 **cũng** là một LLM chấm bằng lời nhắc; MetricX là một model
   hồi quy tinh chỉnh. ⇒ Một phần ưu thế của V3 có thể là **cùng họ với người chấm
   điểm**, ⛔ không hẳn là năng lực. Đồng thuận hai người soi trên 30 dòng chung:
   bất đồng 2/30, **kappa 0,714 nhưng KTC [0,00 ; 1,00]** — ⛔ **vô nghĩa** ở cỡ mẫu này.
3. ⚠️ **Hai phép đo HỎI HAI CÂU KHÁC NHAU.** §1 hỏi *"có bắt được lỗi TIÊM vào một
   bản dịch không?"* — MetricX trả lời **có**, rõ ràng. §2 hỏi *"có phát hiện được
   lỗi TỰ NHIÊN, tinh vi, trong một bản dịch NGƯỜI không?"* — MetricX trả lời **không**.
   ⛔ Hai câu trả lời ⛔ không mâu thuẫn, và ⛔ không được thay cho nhau.
   `n = 100` với **10** dương tính ⇒ mỗi kết luận ở §2 đứng trên 10 sự kiện.

⛔ **Không nới ngưỡng 15 % / 50 % cho bên nào**, và ⛔ không kết luận rộng hơn dữ liệu.

---

## §4. Phán quyết

⭐ **MetricX THUA cuộc đấu** — kết cục 3 trong bảng của điều phối:

> *"MetricX thua ⇒ ⭐ **kết quả đáng giá** — ta có bằng chứng bộ chấm tự nặn là
> **cần thiết**, ⛔ không phải một lựa chọn tuỳ hứng."*

⛔ **Nhưng ⛔ không phải "V3 đạt".** V3 **cũng trượt** cổng (BĐG 33 % > 15 %). Kết quả
đúng là: **⛔ chưa bên nào qua cổng**, và MetricX ⛔ không phải đường tắt để bỏ V3.

**Đọc đúng:** hai thứ này ⛔ không thay thế nhau, chúng **bắt hai loại hỏng khác nhau**.

| | MetricX QE @ 6,0 | V3 (tự nặn) |
|---|---|---|
| Không dịch / dịch nhầm cả câu (`sàn`) | ✅ **99 %** | *(chưa đo trên mức này)* |
| Lật nghĩa · sai thực thể (`nặng`) | ⚠️ 30 % | *(chưa đo)* |
| Nhiễu nhẹ | ⛔ 7 % | *(chưa đo)* |
| Lỗi tự nhiên tinh vi trong bản người | ⛔ **ngang đoán mù** | ✅ 10/10 (⚠️ có thể do cùng họ) |
| Báo động giả trên bản dịch người | ✅ **1 %** | ⛔ **33 %** |

⇒ **Đề nghị = kết cục 2 (ghép), theo đúng thứ tự chi phí:**
**MetricX QE ở ngưỡng 6,0 lọc trước** (gần như miễn phí, 1 % báo động giả, tóm
99 % ca thảm hoạ) **→ V3 chỉ xử phần dư.** Việc còn lại của làn V3 vì thế hẹp hơn:
⛔ không phải "bắt mọi thứ" mà là "hạ 33 % báo động giả trên phần MetricX bỏ qua".

## §5. ⛔ Việc đang CHỜ chủ dự án duyệt — `sacrebleu`

⛔ **Chưa cài.** Xin duyệt, kèm đủ thông tin để quyết:

- **Giấy phép: Apache-2.0** (`pyproject.toml`, `mjpost/sacrebleu`) — thương mại ✅, phân phối lại ✅.
- **Phụ thuộc kéo theo:** `portalocker` · `regex` · `tabulate>=0.8.9` · `numpy>=1.17` ·
  `colorama` · `lxml`. Trong `C:\LTTPlatform\venv` **đã có** `regex`, `numpy`, `colorama`,
  `lxml` ⇒ thực tế chỉ thêm **`portalocker`** (BSD-3-Clause) và **`tabulate`** (MIT).
  ⛔ Không kéo theo model, không tải gì lúc chạy cho chrF.
- **Được gì:** chrF++ là bộ đo **ký tự**, hợp tiếng Việt hơn BLEU, rẻ (không GPU), và là
  bản tham chiếu của cộng đồng WMT ⇒ số của ta so được với số công bố bên ngoài.
- **Rủi ro nếu bỏ qua:** ⛔ không có — MetricX đã gánh xong phần xác thực ở §1.
  chrF++ chỉ là **đối chứng thứ hai, độc lập** cho bảng bốn mức.

⚠️ **Cài rồi thì PHẢI khai vào `requirements`.** Một giờ trước phiên này, production
**sập 15 phút** vì `pywintypes` có mặt trong venv phát triển mà ⛔ không ai khai.
⛔ Đừng dựng lại ca ấy.

## §6. Chạy lại

```powershell
# 1. bước TÍNH (nặng — GPU/CPU) — giữ khoá đúng lệnh tính, nhả ngay khi xong
python "C:\Users\Thang Tuong\.claude\ltt\chay_nang.py" --phien do-dich -- ^
  python -X utf8 tools\bench_b2_dich_tham_chieu.py cham-tho ^
  --n 100 --nhan <...>\b2_san_loi_flores.json --ra tho.json

# 2. phân tích (nhẹ — NGOÀI khoá)
python tools\bench_b2_dich_tham_chieu.py xac-thuc --tho tho.json
python tools\bench_b2_dich_tham_chieu.py doi --tho tho.json --nhan <...>\b2_san_loi_flores.json
```

⚠️ `doc_flores()` và hai phép làm hỏng "nặng" nằm ở `tools/bench_b2_xac_thuc_bo_cham.py`
(**làn khác sở hữu**, chưa lên `main`). Khi chưa có, trỏ `LTT_XAC_THUC_DIR` vào thư mục
chứa tệp đó. ⛔ Đừng viết bộ đọc FLORES mới.

Lượt đã chạy: **cuda**, bf16, lô 16 — 1 000 cặp trong **58 giây**, khoá giữ **1,0 phút**.
