# Thả phim khách thật vào đây — đây là thứ duy nhất còn chặn G17

## Cần gì

**Hai clip.** Thả thẳng vào thư mục này, không cần đặt tên theo quy ước.

| Yêu cầu | Vì sao |
|---|---|
| 2–5 phút mỗi clip | đủ dài để có nhiều cảnh, đủ ngắn để một lượt nghiệm thu không thành một sự kiện |
| tiếng Anh | đường chạy là dịch → lồng tiếng Việt |
| **một người nói là đủ** | 🔑 Sản phẩm là **thuyết minh / lồng tiếng một giọng**. Nhiều giọng là hướng mở rộng sau. Clip nhiều người nói vẫn dùng được — chỉ là không cần |
| **≥ 1 cảnh thật sự đáng cắt** | ⛔ đây là yêu cầu hay bị bỏ qua nhất — xem dưới |
| đuôi `.mp4` `.mov` `.mkv` `.webm` `.m4v` | bài kiểm chỉ nhận phim; một tệp chỉ có tiếng sẽ hỏng ở khâu dựng hình với một thông báo không liên quan gì tới thứ đang được đo |

### 🔴 Vì sao "một cảnh đáng cắt" là bắt buộc

Preset `smart_localize` phải trả lời được câu hỏi **"nó CÓ cắt không"**. Một
clip không có gì đáng cắt cho ra `so_cat = 0` — và `so_cat = 0` đọc y hệt nhau ở
hai tình huống trái ngược: *sản phẩm không cắt được* và *không có gì để cắt*.

Đây không phải lo xa. Hằng số `BIEN_CHO_CODEC_DB` được đo ở pha 22 trên một lượt
chạy `so_cat: 0`, rồi áp cho cả hai preset — và **sai** với preset còn lại. Một
lượt đo trên bản nguồn không có gì để cắt đã một lần cho ra một con số sai.

Cảnh đáng cắt = một đoạn không có thoại và không mang thông tin: bảng hiệu kéo
dài, ảnh tĩnh, khoảng lặng chuyển cảnh, đoạn quay thừa.

## Rồi chạy gì

```
powershell -ExecutionPolicy Bypass -File .\setup\nghiem_thu_asv.ps1
```

Bài `test_G17_hai_preset_tren_PHIM_KHACH_THAT` (trong
`tests/test_448_asv_v4_e2e_nghiem_thu.py`) tự tìm thấy các tệp ở đây. Không có
tệp nào thì nó `skip` **kèm câu nói rõ thiếu gì** — không im lặng.

## Nó chốt gì, và KHÔNG chốt gì

⭐ Phim khách **không đi kèm sự thật**: ta không biết trước câu thoại nằm ở giây
nào, nên không đối chiếu `phu_song_loi` được. Bài này vì thế chốt **ít hơn**
đường chính — nhưng những gì nó chốt thì một bản tổng hợp **không thể** chứng
minh: tiếng ồn phòng, giọng chồng nhau, nhạc nền thật, cắt cảnh không sạch.

Chốt: cả hai preset chạy hết chuỗi · QC đạt · bản ra không dài hơn nguồn ·
preset giữ hình giữ nguyên độ dài · sổ kê khớp đối soát · ít nhất một clip bị
cắt một cảnh.

## ⛔ Các tệp phim không bao giờ vào git

`.gitignore` ở đây chặn tất cả trừ hai tệp mô tả. Đây là tư liệu của khách, và
một tệp đã vào lịch sử git thì còn ở đó sau khi bị xoá — kho này có bản off-site
trên GitHub riêng tư.

## 🔑 Vì sao "một giọng" chứ không phải "càng nhiều giọng càng tốt"

Chủ dự án chốt 2026-09-05: hệ thống làm **thuyết minh / lồng tiếng một giọng**
trước; cơ chế nhiều người mở rộng sau.

Điều đó **đã đúng với sản phẩm đang chạy**, không phải một thay đổi:

* `CHE_DO_GIONG_MAC_DINH = CHE_DO_GIONG_TU_CHON` — mặc định là tự chọn **một** giọng;
* `AUTO_MATCH` (gán giọng theo người nói) đã được khai với khách là *"đang được
  hoàn thiện — hiện tại hãy tự chọn giọng"*;
* `giai_doan_chep_loi.can_phan_vai()` chỉ chạy phân vai **khi** `AUTO_MATCH`, nên
  một clip một giọng **không tiêu tiền** cho việc tách người nói.

⇒ Thứ duy nhất phải sửa là **yêu cầu tư liệu ở bảng trên**: bản đầu đòi ≥2 người
  nói — một đòi hỏi cho tính năng chưa mở bán, và nó làm việc tìm tư liệu khó hơn
  mà không đổi lại được gì.
