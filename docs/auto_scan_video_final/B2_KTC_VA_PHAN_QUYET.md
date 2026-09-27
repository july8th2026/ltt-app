# Khoảng tin cậy cho mọi kết luận đã ra — và bốn kết luận đổ

> Ngày 24/09/2026 · làn `phien/do-chuan` · công cụ: `tools/do_luong.py`
> (`quyet-dinh`, `doi-chung`, `kappa`, `phan-doan`)
>
> ⛔ Tệp này **không định nghĩa lại quy trình**. Nó ghi **phán quyết về từng
> kết luận** ta đã ra, cùng con số đỡ nó.

## 0. Luật đọc tệp này — ⛔ đừng lẫn hai câu

```
"KHÔNG ĐỦ ĐỠ"   =  ta CHƯA BIẾT   ->  bắt ĐO THÊM
"SAI"           =  ta biết là sai ->  bắt ĐỔI HƯỚNG
```

⛔ Một kết luận *"không đủ đỡ"* ⛔ **không** bị rút lại. Nó bị **treo**.

---

## 1. Ba kết luận tôi (điều phối) tự sửa

### 1.1 🔴 Tuyên "V3 trượt cổng 15 %" từ `n = 30`

| | |
|---|---|
| số lúc tuyên | 7/30 = **23,3 %** |
| KTC 95 % (Wilson) | **[11,8 % ; 40,9 %]** — **cắt** ngưỡng 15 % |
| phán quyết lúc ấy | ⛔ **KHÔNG ĐỦ ĐỠ** |
| số về sau (soi mù, `n = 100`) | 33/100 = **33,0 %**, KTC **[24,6 % ; 42,7 %]** — ⛔ không cắt 15 % |
| phán quyết hiện nay | ✅ **ĐỨNG** |

⭐ **Kết luận đúng, nhưng nó chỉ đứng nhờ phép đo `n = 100` về sau.** Lúc tuyên,
ta ⛔ **chưa có quyền** tuyên.

> 🔑 **Đúng ⛔ không có nghĩa là đã được chứng minh lúc ta nói.**

Hai phép đo tương thích với nhau (Fisher `p = 0,37`), nên ⛔ không có mâu thuẫn
cần giải — chỉ có một lời tuyên đi trước bằng chứng của nó.

### 1.2 🔴 Suy TƯƠNG ĐƯƠNG từ `p = 1,0`

Tôi viết *"V1 y hệt ở hai nhiệt độ"* ⇒ *"mốc ta so là mốc sạch"*.

| | |
|---|---|
| số | 13/30 vs 13/30 — y hệt |
| Fisher | `p = 1,0` |
| phán quyết | ⛔ **KHÔNG ĐỦ ĐỠ** |
| mỗi nhánh còn rộng | **33 điểm** (KTC [27,4 % ; 60,8 %]) |

> 🔴 **⛔ Không có bằng chứng KHÁC NHAU ≠ có bằng chứng GIỐNG NHAU.**
>
> Đây là lỗi kinh điển, và nó **ngược chiều** với bài học
> `khong-doi-chung-thi-so-khong-khong-phai-phat-hien`: ở đó một con số 0 không
> phải phát hiện; ở đây một `p` lớn không phải kết luận.

Muốn tuyên tương đương thì phải chốt **biên tương đương** trước rồi chạy phép
kiểm nghịch thế (TOST). Ta ⛔ chưa hề chốt biên ấy. `do_luong.py` nay bắt mọi
khẳng định tương đương (`tuong_duong=True`) luôn trả **KHÔNG ĐỦ ĐỠ**.

### 1.3 🔴 "V3 đổi +6,6 điểm BĐG lấy +47 điểm độ nhạy"

| vế | số | phán quyết |
|---|---|---|
| **giá** (BĐG V2→V3) | 16,7 % vs 23,3 % — Fisher `p = **0,75**` | ⛔ **KHÔNG ĐỦ ĐỠ** |
| **lợi** (thực thể V2→V3) | 5/15 vs 13/15 — Fisher `p = **0,0078**` | ✅ **ĐỨNG** |

> ⭐ **Lập luận đánh đổi MẠNH LÊN, ⛔ không yếu đi.** Ta ⛔ **không đo được cái
> giá**, trong khi **cái lợi thì đo được chắc**.

⛔ ⛔ Đừng viết *"đánh đổi không còn đứng"* — đó là đọc ngược.

---

## 2. Hai kết luận tôi lo, hoá ra vững — ⛔ không mở lại

| kết luận | số | phán quyết |
|---|---|---|
| **V2 loại dứt khoát** (mù thực thể) | 5/15 vs 13/15, `p = 0,0078`, hai KTC **tách** | ✅ **ĐỨNG** — ⛔ **không mở lại** |
| V2 so V1 thực thể | 5/15 vs 15/15, `p = 0,0002` | ✅ ĐỨNG |
| **V3 trượt cổng 15 %** (`n = 100`) | 33/100, KTC [24,6 ; 42,7] | ✅ ĐỨNG |

---

## 3. Bảng đầy đủ

| kết luận | số | KTC 95 % / `p` | phán quyết |
|---|---|---|---|
| V3 trượt cổng 15 % (soi mù) | 33/100 = 33,0 % | [24,6 ; 42,7] không cắt | ✅ ĐỨNG |
| V3 trượt cổng 15 % (dải giữ riêng) | 7/30 = 23,3 % | [11,8 ; 40,9] **cắt** | ⛔ KHÔNG ĐỦ ĐỠ |
| V2 loại dứt khoát | 5/15 vs 13/15 | `p = 0,0078` | ✅ ĐỨNG |
| V2 vs V1 thực thể | 5/15 vs 15/15 | `p = 0,0002` | ✅ ĐỨNG |
| V1 vs V2 báo động giả | 13/30 vs 5/30 | `p = 0,047` | ✅ ĐỨNG |
| V1 vs V3 báo động giả | 13/30 vs 7/30 | `p = 0,17` | ⛔ KHÔNG ĐỦ ĐỠ |
| V2 vs V3 báo động giả | 5/30 vs 7/30 | `p = 0,75` | ⛔ KHÔNG ĐỦ ĐỠ |
| "V1 y hệt ở hai nhiệt độ" | 13/30 vs 13/30 | `p = 1,0` — khẳng định **tương đương** | ⛔ KHÔNG ĐỦ ĐỠ |

⭐ **"Hai KTC chồng nhau" ⛔ KHÔNG phải một phép kiểm.** Dòng *V1 vs V2* có hai
KTC **chồng** nhau mà Fisher vẫn `p = 0,047` ⇒ **ĐỨNG**. Lấy chồng-KTC làm phép
kiểm là vứt đi một khác biệt có thật.

---

## 4. Đồng thuận hai người đọc — sàn lỗi FLORES

| | |
|---|---|
| khớp thô | 28/30 = **93,3 %** ← con số đã báo lúc đầu |
| **Cohen's κ** | **0,714** — *"khá mạnh"* (Landis & Koch) |
| KTC 95 % (bootstrap) | **[0,000 ; 1,000]** |
| tứ phân vị | [0,595 ; 0,839] |
| lượt bootstrap **suy biến** | **3,8 %** |
| lỗi rõ | người 1 = **3**, người 2 = **5**; bất đồng ở dòng **514, 614** |

> 🔑 **Sàn lỗi kém chắc hơn ta tưởng — ⛔ KHÔNG phải vì hai người bất đồng, mà
> vì KHÔNG ĐỦ MỤC DƯƠNG TÍNH.**

⭐ Ngờ ban đầu (*"khớp thô thổi phồng ⇒ kappa sẽ thấp"*) là **sai**: hai người
đọc **có** đồng thuận thật. Tin xấu nằm ở chỗ khác và nặng hơn — với 3 và 5 mục
dương tính trên 30 dòng, kappa ⛔ **không ghim được**.

⚠️ Cận dưới 0,000 đến từ các lượt bootstrap **suy biến** (bốc trúng 0 mục dương
tính), ⛔ **không** phải *"hai người đọc có thể hoàn toàn bất đồng"*. Báo κ trần
một mình ở đây là **nói dối bằng cách im lặng** — luôn kèm tứ phân vị và tỉ lệ
suy biến.

---

## 5. Đối chứng: mọi con số đã báo **sống sót**

`do_luong.py doi-chung` tính lại bằng đường độc lập (`sklearn` + `scipy`): sàn
lỗi 10/2/11/77 · gắn cờ 43/100 · ba định nghĩa × ba tập (9 khối) TP/FP/FN/TN
khớp **từng số**. ⇒ ⛔ **không có lỗi thứ tư.**

> ⚠️ ⛔ ⛔ Đừng đọc thành *"bộ đo của ta ổn"*. Nó nói bộ đo cũ **không sai ở
> những chỗ ta đã nhìn**. Ba lỗi ngày 24/09 đều nằm ở chỗ **chưa ai nhìn**.

KTC mà cách tính cũ ⛔ không hề có: sàn lỗi 10,0 % **[5,5 ; 17,4]** · BĐG
76,7 % **[62,3 ; 86,8]** · trên tập con `n = 30`: **[49,7 ; 91,8]** — rộng tới
mức ⛔ không phân biệt được V2 với V3.

---

## 6. 🔴 Thước phân đoạn B1 — một ngưỡng KHÔNG AI VỚI TỚI ĐƯỢC

Ba số báo **cạnh nhau**, ⛔ không một điểm tổng hợp
(`do_luong.py phan-doan`). Ngưỡng ghi trong `NGUONG_PHAN_DOAN`, commit
`233ea56a` — **trước** lượt đo đầu tiên, tra `git log` để đối chứng.

### 6.1 Kết quả

| dung sai | (a) ranh giới F1 | (b) vi phạm > 7 s | (c) **onset** độ nhạy |
|---|---|---|---|
| **0,3 s** | 0,645 | 0/31 | **0,636** [0,47 ; 0,78] |
| **0,5 s** | 0,903 | 0/31 | **0,909** [0,76 ; 0,97] |

### 6.2 🔴 Vì sao con số 0,3 s ⛔ KHÔNG đọc được

Chân lý nền (`l_ocr_gt_v2.json`) ghi mốc trên **lưới 0,5 s**, và ghi bằng mốc
lưới đầu tiên **tại hoặc sau** lúc phụ đề hiện ⇒ mốc nền **muộn hơn** mốc thật
một lượng `≈ U[0 ; 0,5]` s. Đo xác nhận đúng chiều ấy: **74 %** lệch là ÂM,
trung vị **−0,148 s**.

⇒ Chạy một **hệ hoàn hảo** (mốc thật, sai số 0) qua chính thước này:

```
dung sai 0,3 s :  hệ HOÀN HẢO đạt độ nhạy  0,606  [0,424 ; 0,758]
dung sai 0,5 s :  hệ HOÀN HẢO đạt độ nhạy  1,000  [1,000 ; 1,000]
```

| | |
|---|---|
| ngưỡng đã viết | **0,80** |
| trần của thước ở 0,3 s | **0,758** |
| ⇒ | 🔴 **NGƯỠNG KHÔNG VỚI TỚI ĐƯỢC** |

Bản của ta đạt **0,636**; hệ hoàn hảo đạt **0,606**. Fisher `p = 1,0`
⇒ ⛔ **không phân biệt được ta với một hệ không sai một mili giây nào.**

> 🔑 Con số 0,3 s ⛔ không đo hệ thống — nó đo **lưới của chân lý nền**.
> Sửa **chân lý nền** (ghi mốc mịn hơn) hoặc **nới dung sai**,
> ⛔ **đừng đi sửa hệ thống.**

⭐ Nếu ta đã phát hành cổng ±0,3 s, ta sẽ đuổi theo một khuyết tật ⛔ **không
tồn tại** — mãi mãi. `tests/test_3602::test_3602_nguong_03s_KHONG_VOI_TOI_DUOC_
tren_luoi_05s` khoá kết luận này lại.

### 6.3 B1 có mất trạng thái ĐẠT không?

| mức | phán quyết |
|---|---|
| **±0,3 s** | ⛔ **KHÔNG ĐO ĐƯỢC** — ngưỡng trên trần thước. ⛔ Không phải trượt, không phải đạt. |
| **±0,5 s** | ✅ **ĐẠT cả ba số** (0,903 · 0/31 · 0,909 ≥ 0,80) |

⇒ B1 ⛔ **không mất** ĐẠT. Nhưng nó chỉ ĐẠT ở **mức 0,5 s**, và trước hôm nay
⛔ không ai nói rõ điều đó.

### 6.4 Bốn đối chứng — thước có răng

| bản | (a) F1 @0,5 s | (c) onset @0,5 s |
|---|---|---|
| **bản của ta** | **0,903** | **0,909** |
| ĐC gộp tất | 0,000 | 0,030 |
| ĐC băm 2 s | 0,413 | 0,455 |
| ĐC khối 30 s | 0,000 | 0,030 |

⭐ *ĐC gộp tất* đạt **độ chính xác 1,000** ở 0,5 s (một onset, khớp đúng) —
⛔ **độ chính xác một mình là thước bịp.** Độ nhạy mới hạ nó. Đó là lý do ba số
đi **cạnh nhau**.

---

## 7. ⚠️ Giới hạn phải nói ra

- **Một phim, một chân lý nền.** Chỉ v2 `暴雨露营` có chân lý nền phân đoạn, và
  chỉ **33 dòng** trong cửa sổ **0,5–61 s** của một phim **190 s**.
- 🔴 **v4 `气枪` ⛔ KHÔNG có bằng chứng phân đoạn ở bất kỳ cây nào** trong ~120
  worktree (quét 24/09). ⇒ mọi câu *"bốn phim"* về phân đoạn là **SAI** —
  **ba phim**, và chân lý nền thì **một**. ⛔ Đừng đi tìm nữa.
- `pyannote.metrics` đếm ranh giới bằng `[segment.end for segment in
  reference][:-1]` — **chỉ mốc KẾT, và BỎ mốc cuối**. Trên ba phim của ta nó
  hụt **11–19 %** và lệch về phía **bi quan**, nên số dùng được; nhưng nó **im
  lặng bỏ** ~5–10 **onset sau khoảng lặng** mỗi phim. Đó là **lỗ độ phủ**,
  ⛔ không phải số sai — và là lý do phép (c) tồn tại cạnh phép (a).

---

# 8. ⭐ LUẬT MỚI — trước khi tin một cổng, chạy một HỆ HOÀN HẢO qua nó

> ⭐ **Hệ hoàn hảo ⛔ không đạt ⇒ cổng đang đo CHÂN LÝ NỀN của ta, ⛔ không đo
> sản phẩm. Sửa **chân lý nền** hoặc **dung sai**, ⛔ ĐỬhNG sửa hệ thống.**

`tools/do_luong.py::tran_cua_cong` — dùng được cho **mọi** cổng.

## 8.1 Vì sao nó bắt được thứ đối chứng tiêm-lỗi ⛔ không bắt được

```
tiêm lỗi      chứng minh cổng biết nói  ĐỎ
hệ hoàn hảo   chứng minh cổng biết nói  XANH
```

⭐ Ta đã làm vế một **suốt**, ⛔ chưa bao giờ làm vế hai. Một cổng chỉ biết nói
ĐỎ là một cổng **luôn đúng** theo nghĩa vô dụng nhất. Rẻ tới mức ⛔ không có cớ
bỏ qua: ⛔ không cần chạy sản phẩm, chỉ cần hàm cổng + một bộ sinh dữ liệu hoàn hảo.

## 8.2 🔴 Hai ca, HAI câu trả lới ngược nhau — phải ĐO, ⛔ đừng suy

| cổng | chân lý nền | lưới | dung sai | **trần của thước** | ngưỡng | phán quyết |
|---|---|---|---|---|---|---|
| onset (mới) | `l_ocr_gt_v2.json` đọc tay | **0,5 s** | 0,3 s | **0,606** [0,424 ; 0,758] | 0,80 | 🔴 **KHÔNG VỚI TỚI ĐƯỢC** |
| onset (mới) | như trên | 0,5 s | **0,5 s** | **1,000** | 0,80 | ✅ với tới được |
| **B1 vế 1** `chinh_xac_cho_ngat` | **OCR 4 fps** | **0,25 s** | 0,3 s | **1,0000** [1,0000 ; 1,0000] | 0,90 | ✅ **ĐỨNG** |

⭐ **Lưới mịn hơn dung sai ⇒ lượng tử hoá ⛔ không bao giờ làm mất một lần khớp.**
`0,25 < 0,3` ⇒ vế 1 an toàn. `0,5 > 0,3` ⇒ thước onset sụp. Đó là toàn bộ khác
biệt giữa hai dòng, và nó ⛔ không đoán được nếu ⛔ không tra lưới thật.

---

# 9. 🔴 B1 có mất ĐẠT không? — **KHÔNG.** Và tôi sửa một câu tôi đã viết

## 9.1 Kết quả

Chạy **hàm thật** `bench_b1_chep_loi.chinh_xac_cho_ngat` (nạp đọc từ làn
`asvf-nghiem-thu-v2`, ⛔ không sửa) với một hệ hoàn hảo:

| phim | trần @ ±0,3 s | trần @ ±0,5 s | sàn may rủi (mốc ngẫu nhiên) | đã báo cho bản của ta |
|---|---|---|---|---|
| v1 | **1,0000** | 1,0000 | 0,1915 | 0,9255 ✅ |
| v2 | **1,0000** | 1,0000 | 0,2439 | 1,0000 ✅ |
| v3 | **1,0000** | 1,0000 | 0,1892 | 0,9730 ✅ |

⇒ **Vế 1 ĐỨNG.** Ngưỡng 0,90 nằm **dưới** trần 1,0000 ⇒ cổng biết nói XANH.
Và sàn may rủi 0,19–0,24 ⇒ nó ⛔ **không** qua được bằng may.

## 9.2 ⚠️ TÔI SỬA CÂU CỦA CHÍNH TÔI

Tôi đã viết *"**B1 ĐẠT** phải đọc là **ĐẠT ở mức ±0,5 s**"*. 🔴 **Câu đó SAI.**

Nó đúng cho **thước onset MỚI** của tôi — thứ dùng tệp đọc tay lưới **0,5 s**.
Nó ⛔ **không** đúng cho **cổng B1 thật**, vì vế 1 đối chiếu với **OCR 4 fps
(lưới 0,25 s)**, mịn **hơn** dung sai 0,3 s.

> ⭐ **"B1 ĐẠT" đọc nguyên như cũ: đạt ở ±0,3 s, và phép ấy đo được.**
> ⛔ Không phải một phạm vi bị bỏ sót. ⛔ Không cần viết lại phán quyết B1.

⭐ Tôi suýt chuồn một cảnh báo từ **thước này** sang **thước khác** chỉ vì chúng
cùng con số "0,3 s". Hai thước cùng dung sai mà **khác chân lý nền** là hai thước
**khác nhau**. ⇒ Luật §8 phải chạy **trên từng cổng**, ⛔ không suy sang ngang.

## 9.3 ⚠️ Biên an toàn của vế 1 — mỏng hơn con số 1,0000 trông thấy

Trần 1,0000 giả định chân lý nền OCR chỉ **lượng tử hoá**. Thực tế `L_OCR.md` §3
đo ở 4 fps: lệch mốc trung bình 0,04–0,14 s nhưng **p95 tới 0,65 s** — **vượt**
dung sai 0,3 s. Độ nhạy của trần theo tỉ lệ mốc bị trôi quá 0,3 s (phim v3):

| tỉ lệ mốc trôi > 0,3 s | 0 % | 2 % | 5 % | **10 %** | 15 % | 20 % |
|---|---|---|---|---|---|---|
| trần vế 1 | 1,0000 | 1,0000 | 0,9459 | **0,9189** | 0,8649 | 0,8108 |
| ≥ 0,90 ? | ✅ | ✅ | ✅ | ✅ | ⛔ | ⛔ |

⇒ **Điểm gãy ≈ 12 %.** Vế 1 còn biên, nhưng ⛔ không dư dả. ⚠️ Ai hạ fps đọc OCR
(4 → 3 → 2) là **đang ăn vào biên này**, và ở 2 fps bảng `L_OCR` §3 cho lệch
0,18–0,25 s tb — lúc đó phải đo lại trần **trước**, ⛔ đừng giả định cổng còn đứng.

⚠️ Riêng **v3**: chân lý nền đã được khai là **NHIỄM** (13 dòng chữ UI game,
`B1_CHEP_LOI.md` dòng 173) ⇒ con số 0,9730 của nó đứng trên một nền đã biết là bẩn.

---

# 10. ⚠️ BẪY CỦA MỌI ĐỐI CHỨNG DỰNG TAY — fixture quá đặn

Fixture của tôi **xanh SAI hai lần** trước khi đúng:

| fixture | vì sao xanh sai |
|---|---|
| mốc cách đều **0,5 s** | mốc bị xê dịch **khớp nhầm sang mốc HÀNG XÓM** ⇒ độ nhạy cao giả |
| mốc cách đều **2,0 s** | đối chứng *"băm 2 s"* khớp **HOÀN HẢO** — trên một lưới đều thì băm đều chính là câu trả lời **ĐÚNG** |

> 🔑 **Một fixture quá đặn biến một đối chứng suy biến thành một bản TỐT.**

⛔ Đây ⛔ không phải bẫy riêng của thước phân đoạn — nó là bẫy chung của **mọi**
đối chứng dựng tay. Dữ liệu giả lập đều đặn mang một **cấu trúc** mà dữ liệu thật
⛔ không có, và bản suy biến có thể **ăn may** đúng cấu trúc ấy.

⭐ Thuốc: fixture phải mang **độ không đều của dữ liệu thật** (khoảng cách bốc
ngẫu nhiên, hạt ghim), và luôn kiểm *"bản suy biến có thực sự THUA bản thật không"*
— ⛔ không chỉ kiểm *"bản thật có đạt không"*.

---

# 11. 🔴 QUÉT `tran_cua_cong` QUA MỌI CỔNG ĐANG DÙNG

Lệnh: `tools/do_luong.py::tran_cua_cong`. **Hai cổng có vấn đề về trần.**

| cổng | chân lý nền | **trần** | ngưỡng | phán quyết |
|---|---|---|---|---|
| **B1 vế 1** chỗ ngắt ±0,3 s | OCR 4 fps (lưới 0,25 s) | **1,0000** | ≥ 0,90 | ✅ **ĐỨNG** |
| **B1 vế 2** đoạn ≤ 7 s | ⛔ **KHÔNG CÓ** — là **ràng buộc**, ⛔ không phải so sánh | **1,00** | = 1,00 | ✅ **ĐỨNG** (luật ⛔ không áp) |
| **B1 CER** | hardsub — **RÚT GỌN lời nói** | ⚠️ **CHƯA ĐO ĐƯỢC** | ≤ 0,12 | ⚠️ xem §11.2 |
| **B2 báo động giả — cách CŨ** | *"FLORES luôn đúng"* | **10–23 %** | ≤ 15 % | 🔴 xem §11.3 |
| **B2 báo động giả — cách MỚI** | người soi mù | **0 %** | ≤ 15 % | ✅ **ĐỨNG** |
| onset ±0,3 s (thước mới) | đọc tay (lưới 0,5 s) | **0,606** | ≥ 0,80 | 🔴 **KHÔNG VỚI TỚI** |
| onset ±0,5 s (thước mới) | như trên | **1,000** | ≥ 0,80 | ✅ ĐỨNG |

## 11.1 ⭐ Vế 2 — luật §8 ⛔ KHÔNG ÁP, và đó là một phân biệt thật

Vế 2 (*đoạn ≤ 7,0 s*) so đoạn của ta với một **con số cố định**, ⛔ không so với
một **chân lý nền đo được**. ⇒ ⛔ Không có nhiễu chân lý nền để làm tụt trần.

> 🔑 Luật *"chạy hệ hoàn hảo"* chỉ có nghĩa khi cổng **đối chiếu với một phép đo
> khác**. Một **ràng buộc** (≤ 7 s) thì trần luôn là 1,00 theo định nghĩa.

⚠️ Kiểm phụ: chân lý nền hardsub (33 dòng v2) **tự thoả mãn** ≤ 7 s — dài nhất
**3,00 s**. ⇒ Ràng buộc ⛔ không mâu thuẫn với cách người làm phim thật sự cắt.

## 11.2 ⚠️ CER — trần ⛔ CHƯA ĐO ĐƯỢC, và tôi khai thẳng

`GIOI_HAN_CHAN_LY_NEN` đã khai: hardsub là **bản chữ người làm phim viết**, nó
**rút gọn lời nói**. ⇒ Một ASR **hoàn hảo** (chép đúng thứ người ta nói) vẫn sẽ có
CER **> 0** so với hardsub.

⛔ **Đo trần ấy cần một bản ghi LờI NÓI làm tay — ta ⛔ KHÔNG CÓ.**
`l_ocr_gt_v2.json` là hardsub đọc tay (chữ **trên màn hình**), ⛔ không phải lời nói.

⭐ **Nhưng chiều lệch cứu ta:** nhiễu này đẩy CER **LÊN**, tức làm cổng **NGHIẮM
KHẮC HƠN**, ⛔ không phải dễ hơn. ⇒ Nó gây **ĐỎ giả**, ⛔ không gây **XANH giả**.

```
CER xanh  ->  bằng chứng MẠNH   (vượt được cả phần nhiễu)
CER đỏ    ->  bằng chứng YẾU   (phải soi tay trước khi quy cho engine)
```

⛔ Đây ⛔ không phải phát hiện mới — `GIOI_HAN_CHAN_LY_NEN` đã viết đúng câu ấy từ
trước. Phép quét này **xác nhận** nó, ⛔ không lật nó. Đo được trần thật là việc
cần **một bản ghi lời nói làm tay** — chưa làm, và **ghi ra đây là chưa làm**.

## 11.3 🔴 CỔNG B2 CÁCH CŨ — bộ chấm HOÀN HẢO cũng có thể trượt

Cách đo **cũ** giả định *"FLORES luôn đúng"* ⇒ **mọi** lần gắn cờ là một báo
động giả. Nhưng FLORES **có lỗi thật**, và một bộ chấm hoàn hảo sẽ gắn cờ
đúng những dòng ấy ⇒ bị đếm là báo động giả:

| định nghĩa lỗi | sàn lỗi FLORES | KTC 95 % | so với ngưỡng 15 % |
|---|---|---|---|
| `chinh` | 10/100 = **10 %** | [5,5 ; 17,4] | KTC **cắt** ⇒ ⛔ không kết luận |
| `rong` | 12/100 = **12 %** | [7,0 ; 19,8] | KTC **cắt** ⇒ ⛔ không kết luận |
| `rong_nhat` | 23/100 = **23 %** | [15,8 ; 32,2] | 🔴 **trần > 15 %** ⇒ **bộ chấm HOÀN HẢO CŨNG TRƯỢT** |

⭐ ⇒ **Việc chuyển sang đối chiếu người soi MÙ ⛔ không phải một cải tiến cho
đẹp — nó là ĐIỀU KIỆN ĐỂ CỔNG CÓ NGHĨA.** Cách mới tính lỗi thật là gắn cờ
**ĐÚNG**, nên trần của bộ chấm hoàn hảo về **0 %** và ngưỡng 15 % lại có nghĩa.

⚠️ Hệ quả ngược phải nói rõ: mọi con số báo động giả đo bằng **cách cũ** đều
mang sẵn một phần **sàn lỗi FLORES** bên trong. ⛔ Chúng ⛔ không so sánh được
trực tiếp với con số đo bằng cách mới.

---

# 12. ⚠️ RÀNG BUỘC ẨN ĐÃ GHIM: `fps` đọc OCR ↔ hiệu lực cổng B1

`fps` đọc OCR quyết định độ phân giải mốc của **hardsub**, mà hardsub là **chân
lý nền** của cổng B1 vế 1. Trước 25/09 ⛔ **không chỗ nào trong mã nói hai thứ ấy
ràng buộc nhau** — đúng khuôn `hai-cho-khai-cung-mot-dieu-khong-ai-bat-khop`
cộng `hỏng im lặng`.

✅ **Đã làm cả hai việc:**

1. ⛔ **HỦY 26/09 (Task 21)** — `FPS_DOC` đã biến cùng đường OCR; ràng buộc chuyển
   sang `luoi_s` của tệp chân lý nền đã đóng băng (xem `tests/test_3602_do_luong.py`,
   khối chú thích *“RÀNG BUỘC ẨN ĐÃ XÓA”*). Nguyên văn cũ:
   **Cảnh báo ngay cạnh chỗ đặt fps** — `apps/auto_scan_video/nguon_loi.py`,
   khối chú thích ngay trên `FPS_DOC = 4.0` (⛔ ⛔ không phải trong tài liệu đo).
2. **Phép kiểm đã có** — `tests/test_3602::test_3602_fps_doc_ocr_khong_duoc_ha_
   duoi_muc_da_hieu_luc` đọc **chính tệp nguồn** bằng AST (⛔ không import, module
   kéo ffmpeg/GPU) và đòi `FPS_DOC >= FPS_DOC_DA_DO_TRAN_CONG_B1`, đồng thời đòi
   `1/fps < 0,3 s`. Đã kiểm bằng đột biến: hạ 4 → 2 fps ⇒ phép kiểm **ĐỎ**.

⚠️ Ràng buộc này **không còn nằm trong lời** — nó nằm trong một phép kiểm.

---

# 13. ⚠️ v3 — 0,9730 đứng trên một nền ĐÃ KHAI LÀ NHIỄM

`B1_CHEP_LOI.md` (dòng 173) khai: chân lý nền của **phim 3 bị NHIỄM** — hardsub
chứa **13 dòng chữ UI game**, không phải lời thoại.

> ⛔ Đây ⛔ **không** phải lý do bỏ con số 0,9730.
> ⛔ Nhưng nó ⛔ **không được đứng trần**.

Mỗi lần trích 0,9730, phải trích kèm câu này. Và v3 cũng là phim có **p95 lệch
mốc OCR cao nhất** (tới 0,65 s ở 4 fps) ⇒ nó là phim **gần điểm gãy ≈ 12 % nhất**
trong ba phim. Hai yếu tố đó cộng dồn trên **cùng một phim**.

---

# 14. 🔴 ĐƠN VỊ CỦA TẪT CẢ CÁC BẢNG BÁO ĐỘNG GIẢ — ⛔ ĐỬhNG ĐẶT CẠNH NHAU

🔴 **BÁO ĐỘNG GIẢ ĐO BẰNG HAI CÁCH KHÁC NHAU LÀ HAI ĐƠN VỊ KHÁC NHAU.**

| | **cách CŨ** | **cách MỚI** |
|---|---|---|
| giả định | *"FLORES luôn đúng"* ⇒ **mọi** lần gắn cờ = một báo động giả | đối chiếu **người soi mù**; lỗi thật = gắn cờ **ĐÚNG** |
| mang sẵn | **sàn lỗi FLORES (10–23 %)** bên trong con số | ⛔ không |
| trần của bộ chấm hoàn hảo | **10 % / 12 % / 23 %** | **0 %** |
| bảng thuộc cách này | `V1 43,3 % · V2 16,7 % · V3 23,3 %` (dải giữ riêng, n = 30) | `V3 33 %` (soi mù, n = 100) |

> ⛔ **Đặt hai bảng ấy cạnh nhau là lặp lại đúng lỗi *"hai con số từ hai tập
> khác nhau"* — lần này ở cấp ĐỊNH NGHĨA CỦA CHÍNH PHÉP ĐO**, chứ ⛔ không phải
> ở cấp mẫu.

⭐ **Và đây là câu phải giữ nguyên văn:**

> ⭐ **Chuyển sang đối chiếu người soi mù ⛔ không phải một cải tiến cho đẹp —
> nó là ĐIỀU KIỆN ĐỂ CỔNG CÓ NGHĨA.**

⚠️ **Vị trí bảng gốc:** các bảng `V1/V2/V3` nằm trong
`docs/auto_scan_video_final/B2_XAC_THUC_BO_CHAM.md`, thuộc làn
`phien/asvf-xac-thuc` và **chưa có trên `main`** ⇒ làn này ⛔ **không sửa được**.
⇒ Đánh dấu đơn vị **ngay trên mỗi bảng ấy** là việc của làn sở hữu — điều phối
chuyển giúp. Mục này là **nguồn chân lý** cho việc đánh dấu đó.

---

# 15. 🔴 QUÉT TIẾP: `tools/cham_doi_chung.py` — MỘT LỖ THẬT

Cổng lớp 1 của bộ chấm ảnh: 44 cặp (gốc vs bản suy giảm), người chấm chọn bên
đẹp hơn. `DAT_TOI_THIEU = 0,90` tổng · `SAN_TUNG_KIEU = 0,80` mỗi trục.

Chân lý nền **chính xác theo kiến tạo** (suy giảm là hàm một chiều) ⇒ trần = 1,00.
Nhưng luật §8 còn một vế nữa: **sàn may rủi**. Trả lời **hằng số** (luôn chọn A)
được bao nhiêu?

| trục | n | A | B | **hằng số tốt nhất** | vượt sàn 0,80? |
|---|---|---|---|---|---|
| compression | 20 | 10 | 10 | 50,0 % | ⛔ không |
| blur | 8 | 5 | 3 | 62,5 % | ⛔ không |
| noise | 8 | 5 | 3 | 62,5 % | ⛔ không |
| **bicubic** | **8** | **7** | **1** | 🔴 **87,5 %** | 🔴 **CÓ — LỌT** |
| **tổng** | 44 | 27 | 17 | 61,4 % | (ngưỡng tổng 0,90 ⇒ ⛔ không lọt) |

## 15.1 🔴 Phát hiện

> Trên trục **`bicubic`**, một người chấm **⛔ không hề nhìn ảnh**, chỉ luôn trả
> lời *"A"*, ghi **87,5 %** và **đạt** `SAN_TUNG_KIEU = 0,80`.

⚠️ Docstring khai *"Đoán hú hoạ cho ~50 %"*. Đúng cho **tổng** (61,4 %, lệch khỏi
50/50 ⛔ không có ý nghĩa thống kê, binom `p = 0,17`), nhưng **sai cho từng trục**.

🔴 **Và nó ⛔ KHÔNG phải may rủi của một lượt.** `BI_MAT` là **hằng số**, `ma`
(`dc-001`…) và `dataset_sample_id` **tất định** ⇒ khoá trả lời là **cố định**. Chạy
lại ba lần: **7/1 cả ba lần**. Mỗi lượt chấm đều đối mặt **đúng** sàn 87,5 % ấy.

## 15.2 Phạm vi — ⛔ đừng đọc quá lên

✅ **Cổng TỔNG vẫn đứng**: 61,4 % < 90 % ⇒ người chấm hằng số vẫn **trượt** toàn cục.
🔴 **Cái hỏng là bảo đảm THEO TRỤC**, mà `SAN_TUNG_KIEU` sinh ra **chính xác để** chặn
*"một trục yếu nấp sau con số tổng"* (docstring của nó nói vậy). Trên `bicubic`,
bảo đảm ấy **vô hiệu**: nó ⛔ không phân biệt được *"chấm đúng"* với *"đoán bừa"*.

⚠️ ⛔ Điều này ⛔ **không** nói điểm `bicubic` đã có là sai. Nó nói một điểm
`bicubic` ≥ 0,80 là **bằng chứng YẾU**, vì đoán bừa cũng đạt được.

## 15.3 Thuốc (rẻ) — ⛔ làn này KHÔNG tự sửa

`tools/cham_doi_chung.py` ⛔ không thuộc làn này. Đề xuất, để điều phối giao:

1. **Cân khoá theo từng trục** — ép mỗi trục có số A/B bằng nhau (`bicubic` 4/4)
   thay vì để HMAC tự rơi. Giữ được tính mù (người chấm vẫn ⛔ không biết bên nào).
2. Hoặc **tăng số cặp** mỗi trục yếu (8 → 20 như `compression`).
3. Và **ghi sàn may rủi thực đo cạnh mỗi ngưỡng** — ⛔ đừng để *"~50 %"* trong
   lời khi khoá thật cho 87,5 %.

## 15.4 Các cổng còn lại đã xem

| cổng | loại | phán quyết |
|---|---|---|
| `cong_chat_luong_voice.py` (`3σ` + `SAN_DUNG_SAI`) | **so với baseline** ⇒ luật **ÁP** | ⚠️ **chưa đo được** — cần lặp lại nhiều lượt trên máy rảnh (GPU) ⇒ ⛔ không làm trong làn này; **khai là chưa làm** |
| `canh_bao_ttft_b.py` (`NGUONG_P95_AM_S`…) | **ràng buộc** (độ trễ ≤ ngưỡng) | ✅ luật ⛔ **không áp** — ⛔ không có chân lý nền để nhiễu |
| `gate.py` `TRAN_N_GO_TAY` · `tai_may.py` ngưỡng RAM | **ràng buộc** tài nguyên | ✅ luật ⛔ không áp |
| `bradley_terry.py` `NGUONG_HOI_TU` | **tiêu chí số học**, ⛔ không phải cổng chất lượng | ✅ luật ⛔ không áp |

⭐ **Quy tắc phân loại** (dùng lại được cho cổng mới bất kỳ):

```
cổng đối chiếu với MỘT PHÉP ĐO KHÁC   ->  luật §8 ÁP: phải đo TRẦN
cổng so với MỘT CON SỐ CỐ ĐỊNH (ràng buộc) ->  luật §8 ⛔ KHÔNG ÁP (trần = 1,00)
cổng có LỰA CHỌN RờI RẠC (A/B, đạt/trượt)  ->  phải đo thêm SÀN MAY RỦI
```
