# Pha 23 — Audio Studio

**Trạng thái: XONG ba điều khiển — hai mục đề bài gọi tên có lý do không làm.**
Ngày 11/09/2026.

Đề bài: *mức gốc/nền/giọng · giữ nhạc/SFX · nhạc nền tuỳ chọn · ducking/fade/chính
sách âm lượng · một bản phối master duy nhất.*

## 0. Hiện trạng trước khi sửa

Bản phối (`am_master`) đã là **một master duy nhất** từ V4: nền (demucs đã bỏ lời
gốc, giữ nhạc + tiếng động) + các đoạn tiếng lồng + `loudnorm` hai lượt về −14
LUFS / −1,5 dBTP. Nhưng mọi con số là hằng số: nền luôn hạ **−6 dB trên cả bài**,
kể cả giữa hai câu không ai nói. Cái đang gọi là "ducking" (`NEN_GIAM_DB`) thật ra
là một mức cố định.

## 1. 🔴 Đo trước khi dựng: giọng và nền KHÔNG phải hai bậc tự do

Đề bài gọi tên ba thanh mức. Bản phối kết thúc bằng `loudnorm`, và nó đưa **cả
bản** về −14 LUFS. Đo trên đường trộn thật (`am_master.tron_cuoi`, ffmpeg thật):

| so sánh | SNR giữa hai bản ra |
|---|---|
| (giọng 0, nền −6) với (giọng +3, nền −3) — **cùng tỉ lệ** | **69,7 dB** — trùng nhau tới sai số làm tròn |
| (giọng 0, nền −6) với (giọng 0, nền −12) — **đổi tỉ lệ** | 9,4 dB — khác hẳn |

⇒ Chỉ **tỉ lệ** nền/lời là có nghĩa. Hai thanh "giọng" và "nền" là một thanh thật
và một thanh giả: khách kéo "giọng" lên, bản ra không to hơn, và không gì cho họ
biết vì sao. Nên giao diện có **một** thanh: *"Nhạc nền so với lời thoại"*.
`test_479::test_giao_dien_chi_co_MOT_thanh_keo_am_thanh` giữ quyết định đó (đối
chứng: chèn thêm một thanh ⇒ đỏ).

## 2. Đo cấu hình hạ nền theo lời

`sidechaincompress` với khoá là **chính lời thoại đã chuẩn hoá** (khuếch đại +40 dB
rồi hãm biên 0,5): mọi câu nói đưa khoá lên cùng một mức, nên độ hạ gần như không
phụ thuộc giọng to hay nhỏ.

| giọng | cấu hình | nền giữa hai câu | nền dưới lời | độ hạ |
|---|---|---|---|---|
| −6 dB | **ratio 2,5 · thr 0,1** | −0,33 dB | −8,10 dB | **7,8 dB** |
| −24 dB | **ratio 2,5 · thr 0,1** | −0,33 dB | −6,84 dB | **6,5 dB** |
| −6 dB | ratio 4 · thr 0,1 | −0,33 dB | −10,13 dB | 9,8 dB |
| −24 dB | ratio 4 · thr 0,1 | −0,33 dB | −8,51 dB | 8,2 dB |

Giọng đổi **18 dB** ⇒ độ hạ lệch **1,3 dB**. Chốt ratio 2,5 (`THAM_SO_HA_THEO_LOI`),
giao diện nói *"khoảng 7 dB"*. ⚠️ Tín hiệu tổng hợp — lượt nghiệm thu thật sẽ cho
con số trên tiếng đọc thật.

## 3. Ba điều khiển

| trường | nghĩa | kiểm trên tệp ra thật |
|---|---|---|
| `nen_db` (−24…0, mặc định −6) | mức nền so với lời; `null` = tắt nền | nền −18 ⇒ tỉ lệ nền/lời giảm **12,85–13,52 dB** (8 seed); tắt ⇒ giữa hai câu < −60 dB |
| `giam_theo_loi` | hạ thêm ~7 dB chỉ lúc có lời | so với bản cố định CÙNG nguồn: nền dưới lời thấp thêm **6,5–8,0 dB** (8 seed) |
| `fade_vao` / `fade_ra` (0…5 s) | to dần / nhỏ dần | 0,8 s đầu và cuối thấp hơn bản không fade > 6 dB |

⭐ Nền và lời đặt ở **hai dải tần tách nhau** trong phép kiểm, nên bộ lọc thông
thấp đọc được riêng mức nền ngay trong bản phối đã trộn — không phải đo nền trước
khi trộn rồi đoán.

🔴 **Hai ngưỡng đầu tiên của tôi sai, và chạy lại thì xanh.** Tôi đặt `12 ± 1,5` và
*"bản cố định < 1,5 dB"* theo **một** lượt đo; nhiễu nền `anoisesrc` không cố định
seed, nên mỗi lượt là một tín hiệu khác và hai phép kiểm đỏ chập chờn (2 trên 3
lượt). Đo lại trên 8 seed:

| đại lượng | dải trên 8 seed | ngưỡng cũ | ngưỡng mới |
|---|---|---|---|
| nền −18 làm tỉ lệ giảm | 12,85–13,52 dB | 12 ± 1,5 ⇒ seed 6 **trượt** | 10,5–14,5 |
| bản cố định: nền dưới lời thấp hơn giữa câu | 0,68–2,65 dB, **luôn dương** | < 1,5 ⇒ 3/8 **trượt** | < 3,5 |
| hạ theo lời − bản cố định | 6,47–7,95 dB | (so tuyệt đối) | ≥ 5 |

⭐ Dòng giữa là một phát hiện, không chỉ là sai số: `loudnorm` tự nén nền dưới lời
0,7–2,7 dB ngay cả khi không bật gì. Nên phép kiểm hạ theo lời so **hiệu** với bản
cố định cùng nguồn, và seed nay cố định (`seed=4`) — ngưỡng vẫn bao cả dải 8 seed,
không chỉnh theo seed đã chọn.

* Fade đặt **trước** `loudnorm`: chuẩn âm lượng đo cả đoạn fade, bản ra vẫn đúng −14 LUFS.
* Fade bị cắt còn tối đa ⅓ độ dài bản phối (hồ sơ duyệt ở cửa khi chưa biết video
  dài bao nhiêu), và con số **đã áp** được ghi vào tóm tắt `master.am_thanh` — không
  lặng lẽ.
* Tắt nền + hạ theo lời ⇒ **từ chối** ở cửa (một lựa chọn không làm gì).

## 4. Không đổi gì cho lần chạy không chỉnh

* Hồ sơ mặc định ra **đúng từng ký tự** chuỗi lọc trước pha 23 — `test_479` gõ
  nguyên văn chuỗi cũ và so. Đối chứng: đổi một tham số `amix` ⇒ đỏ.
* Hồ sơ bằng mặc định **không được ghi** (`cai_dat.KHOA_THUA`); giao diện gửi
  chuỗi rỗng, máy chủ cũng trả `None`.
* ⇒ Không nâng `PHIEN_BAN_MASTER`; báo cáo nghiệm thu hiện hành vẫn hiệu lực.
* Vân tay bản phối (`van_tay_master`) mang hồ sơ **đầy đủ** — thiếu nó thì một bản
  trộn ở −6 dB được dùng lại cho lần chạy chọn −18 dB.
* Mặc định −6 là **chính** `am_master.NEN_GIAM_DB`, không phải bản chép.

## 5. Không làm — và vì sao

| mục đề bài | lý do |
|---|---|
| **mức lời gốc** (giữ tiếng gốc nhỏ dưới giọng lồng) | Stem lời gốc **không được giữ**: `audio_prepare` chỉ lưu bản nền. Làm được cần `audio_prepare` xuất thêm stem lời ⇒ nâng `PHIEN_BAN_TACH` ⇒ phải chạy lại nghiệm thu thật (cần UAC) |
| **nhạc nền tuỳ chọn** (thay/thêm nhạc) | `music_replace` nằm trong `CAM_TRONG_MVP` — mở cần một ADR (ma trận tính năng dòng *nhạc nền*: `CAN_ADR`) |
| **chính sách âm lượng do khách chọn** | −14 LUFS / −1,5 dBTP là trần QC T4/T5. Mở ra thì QC hoặc đọc theo từng lần chạy (khách tự nới cổng), hoặc chặn đúng bản khách vừa chọn |

## 6. Giao diện — kiểm trên trình duyệt thật

Trang dựng bằng máy chủ thật (TestClient, phiên của fixture), Playwright nạp nó
cùng tài sản tĩnh thật từ đĩa: 10 module ASV nạp, 0 yêu cầu hỏng, console 0 lỗi.

```
mặc định                    -> ô ẩn "" (không ghi hồ sơ)
←×6 bằng bàn phím           -> {"nen_db":-12}   nhãn "-12 dB", aria-valuetext "-12 dB"
+ hạ theo lời               -> {"nen_db":-12,"giam_theo_loi":true}
+ tắt nền                   -> {"nen_db":null}  thanh + ô hạ bị khoá, ô hạ bỏ chọn
fade 2 / 1,5                -> {"nen_db":-12,"fade_vao":2,"fade_ra":1.5}
trả về −6, fade 0           -> ""   (lại rỗng)
hai preset                  -> khối âm thanh HIỆN ở cả hai (không chạm điểm ảnh)
375 px                      -> không tràn ngang (scrollWidth 360 / 375)
```

⚠️ Phạm vi: trang nạp qua `route` của Playwright nên **không** mang CSP của máy
chủ; luồng gửi form được kiểm ở `test_479` (HTTP), không bằng nút Gửi trên
trình duyệt.
