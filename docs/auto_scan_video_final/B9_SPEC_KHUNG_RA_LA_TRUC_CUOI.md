# B9 — KHUNG RA là trục cuối: phụ đề, lớp phủ, dịch, và QC

**Ngày:** 2026-09-28 · **Nguồn:** phân tích frame thật của T1a
(`asvr_d0960e7dd7da40398a4320f2d52f82d`) trên production `fd565a474551`.
**Chủ dự án chốt 4 hướng** (mục §7). **Spec này là bản chốt**; kế hoạch thi công
ở `B9_PLAN.md`.

---

## 1. Một câu

B6 chốt *"trục THỜI GIAN đổi ở cuối"*. B8 chốt *"trục DỌC của khung đổi ở cuối"*.
B9 đóng nốt vế còn thiếu: **trục NGANG của khung cũng đổi ở cuối**, và **mọi
phép đo phải hỏi khung RA, ⛔ không hỏi khung mà GĐ1 từng thấy.**

## 2. Bằng chứng — frame thật, ⛔ không phải suy luận

T1a bật cả 9 trục: `toc_do 1,25` · `khung 9:16 cắt` · `lật gương` · `làm mờ
y 0,82–0,96` · `cắt đầu/cuối 5–95 %` · lớp phủ chữ · phụ đề đốt · logo.

### 2.1 ĐÚNG — xác nhận trên frame (⛔ đừng sửa)

| trục | phép đo | kết quả |
|---|---|---|
| làm mờ chữ cũ | năng lượng cạnh (`sobel`+`signalstats`) trên **bản ra GĐ1** | **9,64** trong vùng · **69,57** ngay trên · **92,03** bên phải ⇒ giảm **7–10 lần** |
| lật gương | GĐ1 vs bản giao, cùng mốc nguồn | lính trái→phải, bóng bay `x≈0,36`→`x≈0,85` |
| khung 9:16 | `ffprobe` | `324×576` = `576 × 9/16` |
| tốc độ 1,25× | `r = avg = 2997/80` | `37,46` = `29,97 × 1,25` |
| cửa sổ cắt | thời lượng | `275,029 × 0,90 ÷ 1,25 = 198,02` ↔ đo **198,002** |
| **phụ đề đúng giờ** | frame `t=2,56` · `t=23,50` | khớp **chính xác** dòng mà `doi_moc_su_kien` dự đoán |
| **hết phụ đề đúng chỗ** | frame `t=190` · `t=197,5` | sạch — ⛔ không có dòng treo |
| độ to | `ebur128` | `−14,4 LUFS` · đỉnh `−2,0 dBTP` |

⭐ **Bản đồ thời gian GĐ2 ĐÚNG.** 78 sự kiện vào → **71 ra**, 7 bị cắt đúng, dòng
cuối ở **181,3 s** < 198,002 s.

### 2.2 🔴 SAI — bốn lỗi

| mã | lỗi | phép đo |
|---|---|---|
| **B9-1** | phụ đề **tràn khung** khi GĐ2 đổi tỉ lệ | `97/98` dòng (99 %) vượt bề rộng; dòng rộng nhất **6,1 lần** khung |
| **B9-2** | lớp phủ chữ bị **cắt mất đuôi** | `x=W*0,5` neo **mép trái** ⇒ *"LTT STUDIOS"* hiện ra *"LTT STUD"* trên mọi frame |
| **B9-3** | **chữ Hán** còn trong bản dịch | `5/78` đoạn (6,4 %): `吃鸡` ×1, `狙击` ×4 |
| **B9-4** | **T2/T15** báo hỏng trên bản giao ĐÚNG | `mong_doi 220,007` = `275,008 ÷ 1,25`, thiếu cửa sổ khách |

---

## 3. B9-1 — phụ đề tràn khung

### 3.1 Cơ chế

Sinh lại `.ass` bằng **chính** `viet_tep_ass`, hai khung:

```
NGUON  16:9 (1024x576)   Style: Default,Arial,48,...   PlayResX: 1024
BANGIAO 9:16 ( 324x576)  Style: Default,Arial,48,...   PlayResX:  324
SO_DONG_TOI_DA = 2 | KY_TU_MOI_DONG = 42
```

Hai hằng số **⛔ không đổi** khi khung hẹp đi 3,16 lần:

1. `cau_hinh_kieu(ho_so, cao=cao_ass)` — cỡ chữ chỉ nhận **chiều cao**.
2. `KY_TU_MOI_DONG = 42` (`phu_de.py:734`) — hằng số, ⛔ không đọc bề rộng.

`PlayResX` khai đúng `324`, nên **libass tự ngắt lại**: mỗi dòng 42 ký tự vỡ
thành ~4 dòng ⇒ **8 dòng che ~75 % hình** (frame `t=70`).

### 3.2 Vì sao chưa ai bắt được

Quyết định ngắt dòng (`display_text` nướng sẵn `\N`) chốt ở **COMPOSE**, trên
khung 16:9. Khung đổi ở **GĐ2**. ⭐ **Cùng hình dạng B8** — B8 sửa `margin_v`
(trục DỌC), ⛔ không ai sửa trục NGANG. Một họ lỗi, hai nửa, sửa một nửa.

### 3.3 Chốt (chủ dự án chọn A)

**GĐ2 ngắt lại + co chữ theo khung RA.**

- Cỡ chữ dẫn từ `min` của hai ràng buộc — chiều cao **và** bề rộng khung RA.
- Số ký tự mỗi dòng dẫn từ bề rộng RA thật, ⛔ không phải hằng `42`.
- GĐ2 ngắt lại câu bằng **chính** `wrap_lines` (⛔ không viết bộ ngắt thứ hai).
- Đặt cạnh `doi_truc_dai_phu_de` (B8) — **nơi duy nhất biết cả hai khung**.
- Khung ⛔ không đổi (16:9 → 16:9) ⇒ kết quả **y hệt trước**, byte-identical.

### 3.4 Bất biến

> **BB-1** — Với mọi khung ra, mọi dòng phụ đề sau khi ngắt phải **vừa** bề rộng
> khung ra ở cỡ chữ đã chọn.
>
> **BB-2** — Hai khung ra **ngược tỉ lệ nhau** (16:9 và 9:16, cùng chiều cao)
> phải cho **hai** cỡ chữ khác nhau. (Cùng hình dạng phép kiểm B8 đã dùng cho
> `margin_v`: một phép kiểm chỉ chốt *một* khung thì xanh cả khi công thức bỏ
> qua bề rộng.)

---

## 4. B9-2 — neo lớp phủ chữ

### 4.1 Cơ chế

`che_do_render.py:597` → `x=W*{l['x']}`. `drawtext` hiểu `x` là **mép trái** hộp
chữ. Khách kéo con trượt tới `0,5` nghĩ *"giữa"*, nhận mép trái ở giữa.

⚠️ Chú thích tại chỗ bảo vệ việc **⛔ không kẹp về biên** (luật L3). Lý lẽ ấy
**đúng** và **giữ nguyên** — nhưng nó trả lời câu **khác**. Vấn đề ⛔ không phải
kẹp; là **`x` nghĩa là gì**.

⭐ Đây là một ca *"đọc thứ đại diện"*: chú thích trả lời đúng một câu hỏi lân
cận, nên người đọc tưởng chỗ ấy đã có ai canh.

### 4.2 Chốt (chủ dự án chọn A)

**`x` là TÂM chữ.** `x = W*x - text_w/2`.

- ⛔ **Không** kẹp về biên — luật L3 giữ nguyên, tràn thì tràn.
- Trục **`y` ⛔ KHÔNG đổi** trong đợt này: `drawtext` neo `y` ở **đỉnh** hộp chữ,
  và một lớp phủ ở `y=0,06` trông đúng như khách chờ đợi. Đổi cả hai trục cùng
  lúc là đổi hai thứ rồi ⛔ không biết thứ nào gây ra khác biệt.

### 4.3 Bán kính

`lop_phu` là hợp đồng khách **đang dùng**. Run cũ có `lop_phu` sẽ ra khác —
đó là **ý định**, vì kết quả cũ sai. Cần:

- đếm run đã dùng `lop_phu` trước khi đổi (ghi số vào nhật ký);
- vì `x` đổi nghĩa, **vân tay** của `image_finish` phải đổi (⛔ không được để một
  run cũ tái dùng artifact cũ mà tưởng là bản mới).

### 4.4 Bất biến

> **BB-3** — Một chuỗi chữ đặt `x=0,5` phải có **tâm** hộp chữ ở giữa khung, với
> **cả** khung rộng lẫn khung hẹp.
>
> **BB-4** — `x=0,0` phải vẫn cho chữ **tràn sang trái** (⛔ không kẹp), để luật
> L3 ⛔ không bị bản sửa này lặng lẽ đảo.

---

## 5. B9-3 — chữ Hán sót trong bản dịch

### 5.1 Số đo

`5/78` đoạn (6,4 %). Cả 5 là **từ lóng game**: `吃鸡` (ăn gà = thắng trận),
`狙击` (bắn tỉa). Mô hình dịch trọn câu nhưng để nguyên hai từ này.

### 5.2 Chốt (chủ dự án chọn A)

**Cổng kiểm sau dịch + dịch lại riêng đoạn sót.**

- Sau bước dịch, quét bản **đích** tìm ký tự CJK (`U+4E00–9FFF`, `U+3400–4DBF`).
- Đoạn có ký tự CJK ⇒ gửi lại **một lượt**, lời nhắc nêu **đích danh** từ chưa dịch.
- ⛔ Không lặp vô hạn: một lượt dịch lại; còn sót thì **ghi vào QC**, ⛔ không chặn
  lần chạy (khách vẫn nhận bản giao, và vẫn thấy con số).
- Thêm **một mục QC mới** đếm tỉ lệ sót, để lần sau **đo được** thay vì đoán.

⚠️ ⛔ **Không** quét bằng cách so với bản **nguồn**: nguồn là tiếng Trung, nên
mọi đoạn đều "có chữ Hán". Chỉ quét bản **đích**.

⚠️ Ngôn ngữ đích ⛔ không phải lúc nào cũng là tiếng Việt. Cổng chỉ bật khi
`ngon_ngu_dich` ⛔ không dùng chữ Hán (⇒ ⛔ không bật cho `zh`, `ja`, `ko`).

### 5.3 Bất biến

> **BB-5** — Một đoạn đích chứa ký tự CJK trong khi `ngon_ngu_dich` ⛔ không
> dùng chữ Hán phải **được gửi dịch lại đúng một lượt**, và tỉ lệ sót cuối cùng
> phải có mặt trong báo cáo QC (kể cả khi bằng 0 — xem *"số 0 cần đối chứng"*).

---

## 6. B9-4 — QC đọc sai trục

### 6.1 Rà soát cả 18 mục (chủ dự án chọn phương án rộng)

Đọc AST + kiểm tay từng mục. Phân loại theo câu hỏi: *"giữa chỗ mục này LẤY số
và chỗ sản phẩm QUYẾT số đó, có giai đoạn nào xen vào không?"*

| nhóm | mục | kết luận |
|---|---|---|
| 🔴 **phải sửa** | **T2**, **T15** | so **bản giao** với số dẫn từ **trục GĐ1**, ⛔ không qua bản đồ GĐ2 |
| ⚠️ **số gây hiểu nhầm** | **T13** | `den_s`/`dong_s` bản giao (198 s, đã tăng tốc) trừ của **nguồn** (275 s) |
| đã tắt có chủ đích | **T18** | lý do ghi sẵn **đúng họ này** |
| ✅ không ảnh hưởng | T1, T3, T4, T5, T6, T7, T11, T12, T14, T16, T17 | so **GĐ1 với GĐ1**, hoặc chỉ chạy ở preset giữ hình |

⭐ T6/T7/T11/T12 thoạt nhìn đáng ngờ nhưng **đúng**: chúng hỏi *"GĐ1 có làm đúng
việc của GĐ1 không"* — **cả hai vế cùng trục**. Một mục chỉ sai khi nó **bắc cầu**
giữa hai trục.

### 6.2 T2 — thời lượng mong đợi

`_thoi_luong_mong_doi` đọc `KeCat.ban_do().thoi_luong_ra` — kế cắt **TỰ ĐỘNG**.
Lần này `cat: []` ⇒ phép đồng nhất ⇒ `275,008`. Cửa sổ khách `[0,05 ; 0,95]` áp
**riêng** qua `cat_dau_cuoi.giao`, ⛔ không vào kế cắt.

⭐ Con số đúng **đã có sẵn**: `image_finish.thoi_luong_ra = 247,508`.
`247,508 ÷ 1,25 = 198,006` ↔ đo `198,002`.

**Sửa:** `_thoi_luong_mong_doi` lấy độ dài sau **giao** (kế cắt ∩ cửa sổ khách),
⛔ không lấy kế cắt đơn lẻ.

### 6.3 T15 — biên phụ đề

T15 đọc `hinh.phu_de.su_kien` (**bản dựng compose**, trục GĐ1) và chỉ áp
`moc_ban_ra` (÷ `toc_do`). ⛔ Không áp bản đồ GĐ2 ⇒ ⛔ không dịch, ⛔ không loại
sự kiện đã bị cắt.

🔴 Chú thích của chính T15 viết: *"chỗ này hỏi 'thứ đã giao có đúng không', và
thứ đã giao là bản dựng."* ⭐ **Câu ấy đúng vào ngày nó được viết và sai từ ngày
GĐ2 ra đời.** Nó khai đúng **ý định** và sai **hiện vật**.

**Sửa:** T15 đọc sự kiện **đã đổi trục GĐ2** (`su_kien_ra`), tức thứ thật sự
nằm trong `.ass` đã đốt.

### 6.4 T13 — mức thấp hơn, vẫn sửa

`vuot_den = den_s(giao) − den_s(nguồn)` so hai độ dài khác nhau. Lệch về phía
**an toàn** (bản giao ngắn hơn ⇒ hiệu âm ⇒ ĐẠT), nên ⛔ chưa từng báo động giả.
Nhưng con số in ra **gây hiểu nhầm** cho người đọc báo cáo.

**Sửa:** so **tỉ lệ** (`den_s / thoi_luong`) thay vì hiệu tuyệt đối.

### 6.5 Bất biến

> **BB-6** — Một lần chạy có `cat_dau_cuoi` **và** phụ đề **và** `toc_do` mà bản
> giao ĐÚNG phải cho `qc_muc_hong = []`. (Chính ca T1a.)
>
> **BB-7** — Tiêm một bản giao **ngắn hơn thật** phải làm T2 đỏ; tiêm một sự
> kiện phụ đề **quá cuối** phải làm T15 đỏ. (⛔ Không đối chứng thì một mục
> luôn-xanh trông y hệt một mục đúng.)

---

## 7. Bốn chốt của chủ dự án (28/09)

| câu | chốt |
|---|---|
| phụ đề tràn khung | **GĐ2 ngắt lại + co chữ theo khung RA** |
| neo `x` lớp phủ | **`x` là TÂM chữ** — đổi nghĩa |
| chữ Hán sót | **cổng kiểm sau dịch + dịch lại đoạn đó** |
| QC sai trục | **rà TẤT CẢ 18 mục**, ⛔ không chỉ T2/T15 |

## 7b. ĐÃ THI CÔNG — và bốn chỗ phép đo đổi thiết kế giữa chừng

| mã | commit | thứ đã làm |
|---|---|---|
| **B9-4** | `9f4d1957` | T2 dựng lại phép giao từ hai bản khai độc lập; T15 áp bản đồ GĐ2 |
| **B9-1** | `1c14dd60` | `co_chu_vua_khung` — 2 dòng trần cứng, cỡ chữ cơ động |
| **B9-2b** | `98279ed7` | vùng che RỘNG ở 1/3 dưới = dải phụ đề; lề *title safe* 5 % |
| **B9-2** | `7805bf40` | `x` của lớp phủ là TÂM chữ |
| **B9-3** | `4df07ab6` | chữ Hán sót lên được báo cáo + một vòng dịch lại |

### Bốn chỗ phép đo bác bỏ thiết kế ban đầu

1. **`wrap_lines` ⛔ KHÔNG cắt bớt chữ.** Hết dòng thì phần còn lại bị dồn HẾT
   vào dòng cuối, nên dòng cuối **dài ra** khi `ky_tu` nhỏ đi. Một phép giải
   thẳng theo `ky_tu` đi **sai chiều**. ⇒ phải đo dòng THẬT sau khi ngắt.

2. **⛔ Không có "khung tham chiếu".** Bản đầu tôi viết `rong_chuan = cao × 16/9`
   rồi co theo tỉ lệ. Nó cho khung dọc `1080×1920` cỡ chữ **15 px**, vì coi một
   khung dọc như một khung `3413×1920` bị cắt hẹp. **Một khung dọc ⛔ không phải
   một khung ngang bị hỏng.** Bỏ hẳn phép quy chiếu ấy.

3. **Bộ dò chữ Hán ⛔ KHÔNG hỏng** — `78/78` đoạn được dò, `5` dính, kèm trích.
   Thứ hỏng là **đường báo cáo**: `content_process.outputs` ⛔ không có khoá nào
   nhắc tới chữ Hán. ⇒ B9-3 ⛔ không phải "viết bộ dò", mà là "nối con số lên".

4. **`dich_thuat.dich_ban_ghi` là ĐƯỜNG CHẾT** (`thi_hanh.py:167` ghi rõ). Suýt
   cài cổng vào một module ⛔ không ai gọi. Đường sống: `giai_doan_noi_dung`.

### Và một giả định chính sách hết hạn

Chú thích ở vòng lô chọn *"ĐÁNH DẤU, ⛔ KHÔNG HUỶ"* với lý do **"0,3 % là hiếm"**.
T1a đo **6,4 %** — gấp **21 lần**. Tiền đề ấy ⛔ không ai kiểm lại được **vì
chính con số kiểm nó ⛔ không lên tới nơi có người đọc.**

### ⛔ Đã cân nhắc và KHÔNG làm

- **Mục QC `T19`** đếm chữ Hán: con số đã ở đúng tầng của nó (giai đoạn nội
  dung). Khai thêm ở tầng QC là *"hai chỗ khai cùng một điều"* giữa hai module.
- **BBC 68 % bề rộng**: chặt hơn SMPTE, nhưng sang đó làm **mọi** khách 16:9
  đang chạy thấy phụ đề nhỏ hẳn. Con số ghi ở §6b để lần sau ai muốn siết.

## 6b. Nguồn cộng đồng — chủ dự án yêu cầu tra, ⛔ không tự suy

| nguồn | luật |
|---|---|
| **BBC** | **tối đa 2 dòng** (3 chỉ khi chắc ⛔ không che thông tin hình) |
| **BBC** | 16:9: trong **90 % dọc**, **75 % ngang**; dài dòng ≤ **68 %** bề rộng; **37** ký tự |
| **Netflix** | căn giữa, đáy màn; nâng lên đỉnh **chỉ khi** đụng chữ có sẵn; **42** ký tự |
| **Netflix/SMPTE** | title-safe **90 %** (lề 5 %) |
| **Nimdzi 2023** | ⛔ **CHƯA có chuẩn** cho 9:16 — khuyến nghị đo với người dùng thật |

⭐ **`KY_TU_MOI_DONG = 42` chính là con số Netflix** — hằng số ấy có xuất xứ.
⭐ **"Tối đa 2 dòng" là chuẩn ngành**, ⛔ không phải lựa chọn riêng của ta.
⚠️ **Mọi con số ta đặt cho 9:16 là LỰA CHỌN CỦA TA** và phải ghi rõ là lựa chọn.

⚠️ Và một chỗ suýt chép sai: bản tóm tắt tìm kiếm đầu nói BBC có số cho 9:16
(*"central 75 % vertically"*). Đọc thẳng tài liệu: *"does not specify safe area
percentages for 9:16 video format"*. **Con số ấy ⛔ không có trong nguồn.**

## 8. Ngoài phạm vi đợt này

- **Đoạn phụ đề ngắn dưới ngưỡng đọc** — sự kiện 12–15 dài `0,222–0,296 s` trên
  trục biên tập ⇒ `0,18–0,24 s` trên màn. Máy đọc được, người thì ⛔ không.
  Là quyết định **sản phẩm** (gộp đoạn? kéo dài tối thiểu? bỏ bớt?), cần một
  câu hỏi riêng cho chủ dự án. **⛔ Chưa hỏi.**
- **T18 / VMAF** — đang tắt có chủ đích, lý do đã ghi.
- **Watermark gốc ngoài vùng khách vẽ** — góc dưới-phải phim nguồn còn một dấu
  ⛔ không bị che vì nằm ngoài `x 0,10–0,90`. Là lựa chọn của **khách**, ⛔ không
  phải lỗi.

## 9. Nợ công cụ (đã biết, ⛔ chưa làm)

- `[WinError 206]` — `gate.py --doi` và `test_nhanh.py` truyền 972–1001 đường dẫn
  vào một dòng lệnh. Thuốc: `pytest @tệp`.
- `test_2011` còn nhạy tải.
