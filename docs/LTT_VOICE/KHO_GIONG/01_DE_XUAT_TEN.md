# 01 — ĐỀ XUẤT ĐẶT LẠI TÊN 25 GIỌNG DÙNG CHUNG (2026-09-05)

> ✅ **ĐÃ DUYỆT 05/09/2026** (chủ sản phẩm). Áp bằng
> `setup\doi_ten_giong_chung.ps1 -Ap` (cần Administrator).

## Vì sao đổi

Chủ sản phẩm: *"Các tên đó đều là tên tôi đặt theo kênh hoặc tên nhân viên."*

Hai lý do, và lý do thứ hai nặng hơn:

1. **Rò thông tin kinh doanh.** `kinhte_nam`, `lichsu_nam`, `phatgiao_nu`,
   `tamlyhoc_men`, `hoathinh_female`, `bietdoi_girl`, `lego_nu`, `cg_huong_nam`,
   `ht3d_men`, `qtrungg` — mỗi cái tên là tên một **kênh**. Khách của nền tảng
   đọc được danh mục kênh nội bộ từ bộ chọn giọng.
2. **Tên nhân viên thật.** `Khánh`, `Lâm`, `Quân`, `Hương KT`, `Ninh Đôn`,
   `Nguyệt Nga`, `Kỳ An`. ⛔ Một giọng nhân bản là **dữ liệu sinh trắc của một
   con người**; gắn tên thật của họ lên một sản phẩm bán cho công chúng là hai
   thứ khác nhau chồng lên nhau. Tên sản phẩm phải là **bí danh**.

## Quy tắc đặt tên

Giữ nguyên khuôn đang chạy — nó đã deploy và đọc lướt được:

    Tên — giới, thể loại          vd:  "Hạ Vy — nữ, tự nhiên"

| quyết định | vì sao |
|---|---|
| Làn **VI** → tên Việt; làn **EN** → tên quốc tế | làn đã là một chip riêng cạnh tên; tên **hợp** với làn thì khách đọc một lần là hiểu |
| Bí danh, không mô tả | *"Nữ Bắc · Tự nhiên 01"* không đọc được thành lời, và số thứ tự trôi khi thêm giọng |
| **KHÔNG** có vùng miền trong tên | xem mục dưới — ta không biết |
| Không nhắc "EN"/"VI" trong tên | làn đã hiện thành nhãn riêng; viết vào tên là nói hai lần |
| Không trùng 20 preset engine | `uq_voice_owner_ten` + khách sẽ lẫn |

### ⛔ VÌ SAO KHÔNG CÓ VÙNG MIỀN

Yêu cầu là *"đúng thể loại, giới tính, vùng miền"*. Hai cái đầu làm được. Cái
thứ ba **không có dữ liệu**:

  · `voice_profiles.yaml` của kho cũ có 12 trường — `description`, `gender`,
    `engine`, `lang`, `prosody`, … — và **không trường nào** nói về vùng miền;
  · `VoiceProfile` của hệ mới cũng **không có cột vùng**;
  · 17/25 giọng thuộc làn EN, nơi "miền Bắc/Trung/Nam" không có nghĩa.

⭐ Và 20 giọng preset engine **có** vùng miền — nhưng vì engine tự khai nó trong
`description`, chứ không phải vì ai đó nghe rồi đoán.

⇒ Bịa vùng miền vào 8 giọng Việt là thêm một bộ lọc **lọc sai**, và khách sẽ tin
nó. Ba lối, chọn lối nào là quyết định của bạn:

| | cách làm | chi phí |
|---|---|---|
| **A** | không có vùng (đề xuất này) | 0 — bộ lọc vùng chỉ áp cho 20 preset |
| B | bạn nghe 8 giọng Việt rồi nói vùng | ~5 phút nghe |
| C | tìm bộ phân loại giọng vùng miền | vài giờ, và phải đo lại độ chính xác |

---

## Bảng đề xuất

Cột `F0` là **trung vị đo được** (Hz) — nó là cơ sở của chữ *trầm/vừa/cao*, không
phải cảm nhận. `Chất` là DNSMOS OVRL.

### Làn VI — 8 giọng, tên Việt

| # | Tên cũ | **Tên mới** | Giới | F0 | Thể loại | Chất |
|---|---|---|---|---|---|---|
| 1 | Hương KT — nữ, kể chuyện ngôn tình | **Diễm Chi** — nữ, kể chuyện ngôn tình | nữ | 203 | ngôn tình | 3,27 |
| 2 | Kinh Tế — nam, tin tức kinh tế | **Gia Huy** — nam, bản tin kinh tế | nam | 140 | tin tức | 3,36 |
| 3 | Kỳ An — nam, kể chuyện | **Bảo Lâm** — nam, kể chuyện | nam | — | kể chuyện | — |
| 4 | Lịch Sử — nam, kể chuyện lịch sử | **Trọng Nghĩa** — nam, kể chuyện lịch sử *(trầm)* | nam | 103 | lịch sử | 3,34 |
| 5 | Lily — nữ, tự nhiên | **Hạ Vy** — nữ, tự nhiên | nữ | 197 | tự nhiên | 3,38 |
| 6 | Nguyệt Nga — nữ, tự nhiên | **Thanh Nhã** — nữ, tự nhiên | nữ | 188 | tự nhiên | 3,36 |
| 7 | Ninh Đôn — nam, tự nhiên | **Duy Khang** — nam, tự nhiên | nam | 160 | tự nhiên | 3,22 |
| 8 | Phật Giáo — nữ, kể chuyện | **An Nhiên** — nữ, kể chuyện thiền | nữ | 171 | thiền | 3,22 |

⭐ **An Nhiên** cho giọng thiền là cố ý: tên ấy vừa là một tên Việt thật, vừa
mang đúng nghĩa của thể loại — không cần chú thích thêm.

⚠️ Dòng 3 (`kyan_nam`) thiếu số đo: nó vắng mặt khỏi lượt chấm 01/09 vì ba clip
lệch tần số, và lượt ấy chạy **trước** bản sửa. Tên đề xuất dựa trên `description`
của kho cũ (*"kể chuyện tổng hợp"*), không dựa trên phép đo.

### Làn EN — 17 giọng, tên quốc tế

| # | Tên cũ | **Tên mới** | Giới | F0 | Thể loại | Chất |
|---|---|---|---|---|---|---|
| 9 | Alex — nam, giảng bài | **Ethan** — nam, giảng bài | nam | 146 | giáo dục | 3,41 |
| 10 | Bella — nữ, tự nhiên | **Clara** — nữ, thuyết minh | nữ | 240 | thuyết minh | 3,18 |
| 11 | Biệt Đội — nữ, hoạt hình | **Nova** — nữ, hoạt hình | nữ | 235 | hoạt hình | 3,26 |
| 12 | CG Hương — nam, tự nhiên | **Simon** — nam, trang nghiêm *(trầm)* | nam | 104 | tôn giáo | 3,53 |
| 13 | Giffen — nam, mạng xã hội | **Miles** — nam, mạng xã hội *(trầm)* | nam | 90 | mạng xã hội | 3,46 |
| 14 | Harry — nam, phiêu lưu | **Aaron** — nam, phiêu lưu | nam | 166 | phiêu lưu | 3,47 |
| 15 | Hoạt Hình — nữ, hoạt hình | **Lulu** — nữ, hoạt hình | nữ | 240 | hoạt hình | 3,40 |
| 16 | HT3D — nam, tự nhiên | **Victor** — nam, kể chuyện *(trầm)* | nam | 105 | kể chuyện | 3,39 |
| 17 | Khánh — nam, giải trí | **Robin** — giải trí, biến hoá giọng | *diễn* | 220 | giải trí | **2,97** |
| 18 | Lâm — nam, kể chuyện | **Owen** — nam, kể chuyện | nam | 140 | kể chuyện | 3,35 |
| 19 | Lego — nữ, tự nhiên | **Ivy** — nữ, thuyết minh *(cao)* | nữ | 276 | thuyết minh | 3,19 |
| 20 | Mèo Đang — nam, hoạt hình | **Marcus** — nam, thuyết minh *(trầm)* | nam | 91 | thuyết minh | 3,52 |
| 21 | Mèo Quàn — nam, hoạt hình | **Julian** — nam, thuyết minh | nam | 154 | thuyết minh | 3,46 |
| 22 | QTrungg — nam, thuyết minh | **Douglas** — nam, thuyết minh *(trầm)* | nam | 92 | thuyết minh | 3,51 |
| 23 | Quân — nam, hội thoại | **Nathan** — nam, hội thoại | nam | 115 | hội thoại | 3,55 |
| 24 | Roger — nam, hội thoại | **Peter** — nam, hội thoại | nam | 124 | hội thoại | 3,49 |
| 25 | Tâm Lý Học — nam, thuyết minh | **Adrian** — nam, thuyết minh *(trầm nhất)* | nam | 88 | chuyên sâu | 3,49 |

⚠️ Hai dòng **20, 21** đổi thể loại: tên cũ ghi *"hoạt hình"* (theo tên kênh
`meodang`/`meoquan`), nhưng `description` của kho cũ ghi thẳng *"EN male
narrator"*. Thể loại đi theo **mô tả**, không theo tên kênh.

⚠️ Dòng **17** không có giới trong tên, và đó là **kết luận có đo** — xem mục ① dưới.

---

## Ba việc cần bạn quyết

### ① `Khánh` → `Robin — giải trí, biến hoá giọng` — ĐÃ CHỐT BẰNG ĐO

Nhãn kho cũ ghi **nam**; F0 trung vị đo được **220,2 Hz**, giữa dải nữ. Tôi nghi
chính phép đo của mình sai (tự tương quan nhảy quãng tám ở giọng dải rộng).

**Đo lại có đối chứng thì giả thuyết ấy bị bác:**

| giọng | khung nghi nhảy quãng tám | khung < 170 Hz (dải nam) | phân bố |
|---|---|---|---|
| **`khanh`** | **2,8%** | **24,1%** | trải khắp 110→350 |
| `lego_nu` *(nữ chắc)* | 7,3% | 0,3% | một đỉnh 240–350 |
| `hoathinh_female` *(nữ chắc)* | 4,6% | 1,5% | một đỉnh 200–290 |
| `tamlyhoc_men` *(nam chắc)* | 0,1% | 92,8% | một đỉnh 80–110 |

⭐ Nhảy quãng tám ở giọng này **thấp hơn cả hai giọng nữ chắc chắn** — nên 220 Hz
không phải lỗi đo. Nhưng **24,1%** số khung vẫn nằm trong dải nam (nữ thật:
0,3% và 1,5%), nên nó cũng không phải một giọng nữ.

⇒ Đây là **giọng diễn, biến hoá qua cả hai dải**. Khớp đúng với `entertainment`
  trong tên cũ, và giải thích luôn DNSMOS thấp nhất kho — âm thanh biểu cảm/xử lý
  nhiều thì chấm thấp, không phải "giọng hỏng".

⛔ Gán "nam" hay "nữ" đều là **bỏ đi chính đặc điểm** khiến giọng này đáng có mặt
   trong danh mục. Tên chốt: **`Robin — giải trí, biến hoá giọng`**.

⭐ Và điều đáng ghi hơn cả kết luận: **trung vị đã xoá đúng thứ cần nhìn.** Một
   phân bố trải từ 110 tới 350 Hz bị nén thành "220,2" — một con số trông như một
   giọng nữ bình thường. Histogram trả lại thứ trung vị đã bỏ.

### ② Một cặp rất giống nhau: `Clara` ↔ `Nova`

Nhúng speaker embedding (`OnnxSpeakerEncoder` — đúng bộ mã hoá `prepare_reference`
dùng, nên nó ở trong không gian model thật sự nhìn), 300 cặp:

    phan bo cosine:  p50 = 0,418    p95 = 0,722    p99 = 0,809

| cặp | cosine | |
|---|---|---|
| `bella_nu` ↔ `bietdoi_girl` | **0,9356** | 🔴 cao hơn p99 **0,13** |
| `bella_nu` ↔ `hoathinh_female` | 0,8514 | ⚠️ |
| `ht3d_men` ↔ `tamlyhoc_men` | 0,8086 | ⚠️ |
| `cg_huong_nam` ↔ `lam_male_storytelling` | 0,8201 | ⚠️ |

⛔ **Không tự gộp, không tự xoá.** Cosine cao nói *"hai clip nghe rất giống nhau
với bộ mã hoá"* — nó **không** nói cùng một người. Bốn giọng nữ làn EN, cùng kiểu
thu, cùng thể loại thuyết minh thì giống nhau là chuyện bình thường.

⇒ Đề xuất: **giữ cả hai, đặt tên cả hai**, và đánh dấu cặp 0,9356 là *cần nghe*.
  Nếu nghe ra là một người thì gộp — nhưng đó là một quyết định riêng.

### ③ Bốn giọng chất lượng thấp đang bày ra cho khách

`Robin` (2,97) · `Ivy` (3,19) · `Clara` (3,18) · và `Thanh Nhã` **hơn nửa clip là
im lặng** (tỉ lệ im 0,562).

Hôm nay **không có tầng chất lượng**: `dung_chung` là một cột `bool`, bật là hiện.
Muốn ẩn một giọng yếu thì phải tắt hẳn nó.

⚠️ "Thấp" ở đây là thấp **so với chính kho này** (2,97–3,55 — dải rất hẹp), không
phải thấp tuyệt đối. Đừng đọc 3,18 thành "giọng hỏng".

---

## 🔴 MỘT PHỎNG ĐOÁN CỦA TÔI ĐÃ BỊ CHÍNH PHÉP ĐO BÁC BỎ

Trước khi nhúng, tôi thấy **bốn giọng nam làn EN có F0 nằm trong 3,6 Hz của
nhau** (88,2 · 89,9 · 91,3 · 91,5) và nghi chúng là bản sao của nhau.

Nhúng nói ngược lại:

    giffen  <-> qtrungg    0,7611
    qtrungg <-> tamlyhoc   0,6735
    meodang <-> tamlyhoc   0,5770
    giffen  <-> tamlyhoc   0,5429
    meodang <-> qtrungg    0,5311
    meodang <-> giffen     0,4340   <- gan trung vi cua CA kho (0,418)

Cặp thấp nhất trong nhóm ấy còn **dưới** phân vị 50 của toàn kho. **Cùng cao độ
không phải cùng người** — cao độ là một chiều, âm sắc là 192 chiều.

⭐ Đây là lần thứ năm trong hai phiên gần đây một suy luận nghe rất chắc bị một
phép đo bác bỏ trong vài phút. Xem `docs/LTT_VOICE/NGUON_CHAN_LY.md`.

---

## 🔴 MỘT RỦI RO TÌM RA KHI VIẾT CÔNG CỤ ÁP

Bản đầu của `tools/doi_ten_giong_chung.py` khoá bảng đổi theo **tên hiển thị**,
với một lý do nghe rất hợp lý: *"tên là thứ đọc được trực tiếp từ hàng, nên nó
khớp hay không khớp một cách nhìn thấy được."*

⛔ Lý do ấy sai vì một dữ kiện tôi chưa kiểm khi viết nó: lượt nhập 01/09 chỉ
**vá xuất xứ** cho bốn giọng đã có từ trước (`_va_xuat_xu`) — nó **KHÔNG đổi
tên** chúng. Nên bốn giọng ấy vẫn mang tên do đợt nhập đầu đặt.

⚠️ Và lỗi ấy sẽ **không trông như lỗi**: công cụ báo *"khong thay trong kho
chung"* cho đúng bốn dòng, và người đọc rất dễ kết luận *"kho thiếu bốn giọng"*
thay vì *"bảng của tôi khoá sai thứ"*.

⇒ Nay khoá theo **`ma_cu`** (khoá kho cũ, nằm trong `ghi_chu`) — nó không trôi
  theo tên hiển thị. Tên đang chờ vẫn giữ trong bảng làm **đối chứng**: lệch thì
  công cụ nói ra rồi **vẫn đổi**, vì `ma_cu` mới là danh tính còn tên chỉ là thứ
  ta tưởng nó đang mang.

`test_399::test_khop_theo_ma_cu_chu_KHONG_theo_ten` dựng đúng ca ấy: đổi tên một
giọng ra thứ hoàn toàn khác rồi đòi công cụ vẫn nhận ra nó.

## Nếu duyệt thì áp dụng thế nào

⭐ **Không đụng vào `public_id`.** `VoiceProfile` đã tách sẵn `public_id`
(`vc_<32 hex>`) khỏi `ten_hien_thi` từ đầu — nên đổi tên hiển thị **không đổi một
chữ nào** của hợp đồng API. Khách đang gọi `voice_id="vc_…"` không bị ảnh hưởng.

⚠️ Việc duy nhất phải cẩn thận là `uq_voice_owner_ten`: 25 tên mới phải đôi một
khác nhau **và** khác 20 tên preset. Đã kiểm: không trùng.

Cần một lệnh có quyền Administrator (đọc `app.env`), như mọi lượt chạm CSDL
production.
