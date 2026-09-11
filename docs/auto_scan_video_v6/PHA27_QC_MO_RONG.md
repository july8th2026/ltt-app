# Pha 27 — Technical QC expansion

**Trạng thái: XONG.** Ngày 11/09/2026. T1–T13 → **T1–T16**, `PHIEN_BAN_QC` 2 → 3.

---

## 0. Đo trước khi thêm — bốn dung sai đã có người canh, bốn thì không

Đề bài pha 27 liệt kê: codec · thời lượng · **sync** · âm lượng · khung đen ·
hỏng tệp · **biên phụ đề** · tác dụng của vùng · **nhất quán chính sách render**.

| đề bài gọi tên | ai đang canh |
|---|---|
| thời lượng | T2 |
| âm lượng | T4 / T5 |
| khung đen | T13 |
| codec · sync · biên phụ đề · nhất quán chính sách render | **không ai** |

⇒ Ba mục mới: **T14** (chính sách render + codec) · **T15** (biên phụ đề) ·
**T16** (lệch tiếng-hình).

*Tác dụng của vùng che* không thêm ở đây: `ban_dung.kiem` đã cưỡng chế nó ở
tầng bản dựng, và đo "vùng có thực sự mờ không" đòi so từng điểm ảnh — thuộc
pha 26 khi renderer được gộp.

---

## 1. 🔴 Mọi phép kiểm mới đều CHẶN được một lần chạy

`giai_doan_qc` đọc `muc_hong` rồi ném `QcChan`. Một mục `HONG` sai không phải
một cảnh báo — nó là **một video đã render xong bị từ chối giao**. Nên cả ba:

* trả `KHONG_AP_DUNG` khi dữ liệu không đầy đủ — **không đoán**;
* dùng ngưỡng **đã đo trên chuỗi lệnh thật**, không phải ngưỡng mượn;
* và `test_473` chốt **hai chiều** cho mỗi ngưỡng: ca trên ngưỡng phải đỏ, ca
  dưới ngưỡng phải xanh. Chỉ chốt một chiều là để ngỏ đúng cái hỏng đắt hơn
  (`phep-do-lech-chieu-phai-bo-khong-phai-sua`).

---

## 2. T14 — preset giữ hình có THỰC SỰ không mã hoá lại

T3 đã hỏi điều này bằng cách băm cả luồng hình. Nhưng T3 rơi về `KHONG_AP_DUNG`
ngay khi không băm được — và khi ấy **không ai** kiểm lời hứa của preset. T14 là
lưới thứ hai, và nó miễn phí: `codec_video`, `rong`, `cao`, `xoay` đã nằm sẵn
trong kết quả ffprobe đã chạy.

`-c:v copy` cho byte hình đi thẳng từ nguồn sang tệp ra, nên nó **không thể**
đổi bốn trường đó. Một trong bốn đổi ⇒ lời hứa đã bị phá.

### Hai lần sửa, cả hai do chính bài kiểm bắt

**① `0` không phải "thiếu dữ liệu" ở mọi trường.** Bản đầu coi `0` là thiếu cho
cả bốn. Với `rong`/`cao` đúng — một luồng hình không thể rộng 0. Với `xoay` thì
**sai**: `0` là giá trị hợp lệ và phổ biến nhất, nên trục xoay **không bao giờ
được so**. Một phép kiểm chết lặng lẽ. `test_473[doi2]` bắt nó ở lượt chạy đầu.

⭐ Đó là lý do bài kiểm liệt kê **cả ba trục** thay vì tin một ca đại diện.

**② Trục xoay một mình không đủ để tuyên bố "không mã hoá lại".** Một lần mã hoá
lại giữ nguyên góc xoay là chuyện bình thường. Sau bản sửa ①, một tệp chỉ so
được `xoay` sẽ báo **ĐẠT** — một tuyên bố rộng hơn thứ đã đo
(`pham-vi-phep-do-hep-hon-loi-tuyen-bo`). Nay T14 đòi ít nhất một trục **thực
chất** (bộ mã hoá hoặc kích thước), nếu không thì `KHONG_AP_DUNG`.

---

## 3. T15 — mỗi dòng phụ đề phải NẰM TRONG bản ra

🔴 Một dòng phụ đề đặt quá cuối bản ra là một dòng **không ai thấy**. Khách trả
tiền cho phụ đề, tệp `.ass` hợp lệ, ffmpeg không báo gì, và dòng chữ đó không
bao giờ hiện ra — đúng hình dạng *tính năng không tồn tại* mà chương trình này
liên tục gặp.

Đọc sự kiện **đã chốt trong bản dựng**, không tính lại từ kế hoạch: chỗ này hỏi
*"thứ đã giao có đúng không"*, và thứ đã giao là bản dựng.

Dung sai `0,50 s` bằng `ket_xuat.LECH_THOI_LUONG_GIAY` có chủ đích: `kiem_tep_ra`
đã cưỡng chế tệp ra không lệch quá ngưỡng đó so với bản dựng, nên một dòng nằm
trong bản dựng cũng không thể vượt bản ra quá ngưỡng đó. Đặt chặt hơn là báo hỏng
những lần chạy hoàn toàn bình thường.

⚠️ **Chồng lấn được ĐẾM, không bị đánh trượt.** `ass_builder` xếp chồng được, và
một bản karaoke có thể có hai dòng cùng lúc. Đếm để người đọc báo cáo thấy —
không để chặn lần chạy.

---

## 4. T16 — luồng hình và luồng tiếng phải dài bằng nhau

🔴 Đây là hỏng **đúng thứ sản phẩm này bán**. Một bản lồng tiếng mà tiếng và hình
lệch nhau thì mọi thứ khác đều vô nghĩa — và trước pha 27 không chốt nào hỏi: T2
đo độ dài **container**, một con số vẫn đúng khi hai luồng bên trong lệch nhau.

`soi()` nay báo thêm `thoi_luong_video` / `thoi_luong_tieng`.

⚠️ `None` khi luồng không tự khai `duration` (MP4 được phép). Đó **không phải**
`0`, và đoán bằng `0` sẽ biến một tệp bình thường thành báo cáo hỏng.

### Ngưỡng: đo, không mượn

Bản đo **đầu tiên** của tôi dùng một lệnh ffmpeg tự viết → 0,0234 s. Nó đo một
thứ khác: chuỗi thật còn `trim`+`concat` trên hình, `amix`+`loudnorm` trên tiếng
và `-shortest`, mỗi mắt xích đều đổi được độ dài một luồng.

Đo lại bằng **chính `ket_xuat.dung_lenh`**, cả hai đường render:

| đường render | nhịp | container | video | tiếng | lệch video↔tiếng |
|---|---|---|---|---|---|
| giữ hình | 30 | 6,000 | 6,000 | 6,000 | **0,0000** |
| cắt | 30 | 6,000 | 6,000 | 6,000 | **0,0000** |
| cắt | 30000/1001 | 5,973 | 5,973 | 5,952 | **0,0206** |

⇒ `LECH_TIENG_HINH_S = 0,50` — dư địa **24×** mức tệ nhất đã đo. Rộng thế là có
ý: sai số phải đẩy về phía **không hành động**, và 0,5 giây lệch tiếng-hình thì
tai người nghe được.

⭐ `test_473::test_T16_nguong_du_dia_it_nhat_MUOI_LAN_muc_da_do` chốt chính con
số, không chỉ chốt hành vi: một bản sửa sau siết ngưỡng xuống 0,05 s vẫn làm mọi
bài khác xanh, nhưng nó đưa ngưỡng tới sát vùng nhiễu thật.

---

## 5. `PHIEN_BAN_QC` 2 → 3, và vì sao nó bắt buộc

Chú thích của chính hằng số đó đã ghi lý do: không nâng thì một lần chạy lại
**dùng lại báo cáo QC cũ từ cache** — báo cáo do một bộ luật *chưa biết ba mục
này tồn tại* làm ra, và nó sẽ báo "đạt".

`test_420::test_bao_cao_liet_ke_DU_cac_dung_sai` mở tập hợp T1–T13 → T1–T16 và
**chốt luôn** `PHIEN_BAN_QC >= 3` ở cùng chỗ, để hai việc không thể tách rời.

---

## 6. Bằng chứng

* `tests/test_473_asv_v6_qc_mo_rong.py` — **23 bài**.
* Đối chứng: tiêm ba lỗi, cả ba làm bộ kiểm **đỏ** — coi `0` là thiếu ở mọi
  trường (lỗi tôi **đã thực sự viết**) · siết ngưỡng xuống dưới vùng nhiễu đã đo
  · quên truyền `ban_hinh` cho `qc.kiem`. Rồi `qc.py` và `giai_doan_qc.py` được
  trả lại nguyên vẹn.
* Ngưỡng T16 đo bằng chính `ket_xuat.dung_lenh` — bảng ở §4.

## 6b. Lần đầu ba mục mới chạy trên RENDER THẬT

Nâng `PHIEN_BAN_QC` làm `nghiem_thu_hien_hanh.json` thành cũ (`qc/2` vs `qc/3`),
và `test_448` đỏ đúng như docstring của nó nói phải đỏ. Báo cáo được **tái sinh ở
độ trung thực đầy đủ** ngày 11/09 (lượt nâng quyền qua Scheduled Task, bốn khoá
`cua_so_yen` fail-closed, `chen_khong_khoa=false`): `model_that=True`,
`giong_that=True`, `thay_the=[]`, **26 passed / 1 skipped, 22:19**.

| cánh | T14 | T15 | T16 |
|---|---|---|---|
| `giu_hinh` | **đạt** — so đủ 4 trường, không lệch | không áp dụng | **đạt** — lệch **0,0177 s** (32,167 / 32,149) |
| `cat_thong_minh` | không áp dụng (đường cắt) | không áp dụng | **đạt** — lệch **0,0003 s** |

⭐ T16 trên render thật (0,0177 s) nằm **dưới** mức tệ nhất đã đo ở §4 (0,0206 s)
   — ngưỡng 0,50 s còn dư địa 28× trên dữ liệu thật, không chỉ trên dữ liệu đo.

⭐ T14 lần đầu chứng minh trên đầu ra thật rằng preset giữ hình **không** mã hoá
   lại: bộ mã hoá, rộng, cao, xoay đều khớp nguồn.

⚠️ **T15 chưa từng chạy trên một render thật.** Nghiệm thu E2E không bật phụ đề,
   nên cả hai cánh trả `khong_ap_dung`. Đó là một khoảng trống, không phải một
   lần đạt — nó cần một cánh nghiệm thu bật phụ đề (việc của pha 33).

## 7. Còn nợ

* **Hỏng tệp** (`corruption`) chưa có chốt: cần giải mã toàn bộ luồng để phát
  hiện, và chi phí đó phải đo trước khi đưa vào một cổng chạy mỗi lần render.
* **Tác dụng thật của vùng che / lớp phủ** cần so từng điểm ảnh — thuộc pha 26.
* **T15 chưa chạy trên render thật** — xem §6b.
* T15 mới kiểm biên **thời gian**. Biên **không gian** (phụ đề tràn ra ngoài
  khung) cần dựng thử khung — thuộc pha 32 cùng ô xem trước.
