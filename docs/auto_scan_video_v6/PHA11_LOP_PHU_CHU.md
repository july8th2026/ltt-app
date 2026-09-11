# V6 pha 11 — Lớp phủ chữ

> Trạng thái: **11a XONG** (chữ) · **11b HOÃN** (logo ảnh, chặn ở pha 08)
> Commit: `efbcfb4a` (mạch engine) · `42512fd8` (giao diện + hợp đồng + bộ kiểm)

---

## 0. Phạm vi thật, và vì sao nó hẹp hơn tên pha

Pha 11 của gói V6 đòi *"Logo, text overlay, position/size/opacity/timing"*. Cái
giao được là **text overlay**; **logo ảnh thì không**, và lý do là một phụ
thuộc có thật chứ không phải một lần cắt bớt:

ASV nhận **một** tệp video và không nhận gì khác. `platform_core.image_input.
validate_reference` tồn tại nhưng ASV chưa có route nào gọi nó — đường nhập ảnh
là phạm vi của **pha 08** (durable upload + source preview).

⛔ Nên `logo_image` được khai vào `hop_dong_v4.HAU_MVP` **trong mã**, không phải
   chỉ trong tài liệu này. Đó là điểm khác biệt đáng kể so với V5: hai mục
   *"Logo của tôi"* và *"Watermark chữ"* đã được `FEATURE_PARITY_MATRIX.md` xếp
   `DEFER` từ V5, nhưng **không dòng mã nào nói điều đó** — tức một quyết định
   sản phẩm chỉ sống trong một tệp `.md`, và chính `hop_dong_v4` đã cảnh báo về
   hình dạng ấy: một mục **vắng mặt** thì *"chưa khai"* và *"bị cấm"* trông
   giống hệt nhau.

---

## 1. Ranh giới với `subtitle_burn` — CƠ HỌC, không phải lời hứa

`CAM_TRONG_MVP` cấm `subtitle_burn` vì `apps/autosubvideo` sở hữu năng lực đó,
và `V6_OPERATING_CONTRACT` nhắc lại: *"AutoSubVideo owns subtitle rendering
capability"*. Nhưng cả hai chạy trên **cùng một bộ lọc** (`drawtext`).

Một giao ước (*"đừng dùng lớp phủ để làm phụ đề"*) sẽ bị vi phạm bởi chính
người viết ra nó — kho này đã ghi thành luật sau khi một phiên viết §4.9 rồi vi
phạm ở lượt kế. Nên ranh giới ở đây là ba phép cưỡng chế:

| Cưỡng chế | Nơi | Hệ quả |
|---|---|---|
| `chu` là **một dòng** | `lop_phu._chu_sach` | ký tự điều khiển bị **TỪ CHỐI**, không bị lọc bỏ |
| tối đa `SO_LOP_PHU_TOI_DA` = 3 lớp | `lop_phu.chuan_hoa` | một bản phụ đề 400 đoạn không lọt qua |
| giao diện dùng `<input type=text>` | `asv.js` | không có ô nhiều dòng để dán vào |

⭐ **Từ chối chứ không lọc bỏ** là nửa quan trọng nhất: một chuỗi bị lọc âm thầm
   là một chuỗi khách không gõ, và họ chỉ thấy nó trên bản đã render.

---

## 2. `textfile=` chứ không `text=` — một PHÉP ĐO, không phải một gu

Đo trên máy này (ffmpeg của kho, `testsrc2` 640x360), bảy chuỗi thử:

| chuỗi | `text=` đã thoát từng ký tự | `textfile=` |
|---|---|---|
| `Kenh cua toi - Dang ky nhe!` | OK | OK |
| `Tieng Viet co dau: Đăng ký ngay` | **HỎNG** | OK |
| `Gio: 12:30` | **HỎNG** | OK |
| `C:\Users\x` | **HỎNG** | OK |
| `It's mine` | OK | OK |
| `Mot, hai, ba` | OK | OK |
| `Giam 50% hom nay` | OK | OK |

    A hỏng 3/7      B hỏng 0/7

🔑 Ba cái hỏng **không phải ba lỗi lẻ tẻ**. Chúng là ba **tầng** khác nhau của
   cùng một vấn đề: dấu `:` (bộ tách tham số của filter), dấu `\` (bộ thoát), và
   bảng mã đối số dòng lệnh trên Windows. Một bảng thoát ký tự phải đúng cả ba,
   và nó chỉ "đúng" cho tới chuỗi thử tiếp theo.

⇒ `drawtext` đọc một tệp UTF-8 (không BOM). Thứ duy nhất còn phải thoát là một
  **đường dẫn do chính ta sinh ra**: ASCII, không khoảng trắng, một dấu `:`.

⚠️ Giá phải trả: bộ lọc không còn là một hàm thuần tuý — nó cần một thư mục để
   ghi tệp chữ. Đó là lý do `viet_tep_chu()` tách khỏi `chuan_hoa()`, và
   `ket_xuat.dung_lenh` nhận `duong_chu` y như nó nhận `duong_lop` (nó **không
   ghi** tệp nào; người gọi ghi trước).

---

## 3. `fontsize` nhận biểu thức, `borderw` thì KHÔNG

```
fontsize=H*0.060000       OK
borderw=2                 OK
borderw=H*0.004           HỎNG   "Error : Invalid argument"
borderw=max(1\,H*0.004)   HỎNG   như trên
```

Nên độ dày viền **không thể** để bộ lọc tự tính theo tỉ lệ, kiểu
`_MAU_BAN_KINH` đã làm với bán kính làm mờ. Ai đó để `borderw=2` sẽ được một
viền rõ trên 480p và gần như vô hình trên 4K — đúng hình dạng lỗi mà luật *"phân
số, không bao giờ pixel"* tồn tại để tránh.

⇒ Chiều cao khung phải đi **từ ngoài** vào: `ban_dung.hinh.cao_khung`, đọc lại
  từ hồ sơ soi của `MEDIA_PREPARE` (không `ffprobe` lại — pha soi đã trả lời câu
  ấy rồi). `ban_dung.kiem` từ chối một bản dựng có lớp phủ mà thiếu nó.

---

## 4. Bằng chứng engine — và bản đo đầu tiên SAI

Nguồn 6 giây, một lớp phủ đặt giờ `[2,0 ; 4,0)`. PSNR bản **có** so bản
**không**, cùng mốc thời gian:

```
t=1,0s NGOÀI cửa sổ   PSNR = inf         (trùng khớp từng điểm ảnh)
t=3,0s TRONG cửa sổ   PSNR = 20,36 dB    (chữ đã được vẽ)
t=5,0s NGOÀI cửa sổ   PSNR = inf
đường chéo (t=3,0 so t=1,0 của CÙNG bản có lớp phủ) = 13,36 dB
```

🔴 **Lượt đầu ghi hai bản bằng `libx264 -crf 12`, và `t=5,0s` ra 53,25 dB** —
   khác, dù bộ lọc không vẽ gì ở đó. Khác biệt ấy đến từ **bộ mã hoá**: các
   khung 2–4s của bản có lớp phủ chứa chữ, nên các khung P sau đó tham chiếu một
   lịch sử khác.

⭐ Và sự **bất đối xứng** mới là thứ chỉ ra nguyên nhân: `t=1,0s` trùng khớp vì
   nó là khung I đầu chuỗi, chưa có lịch sử nào để lệch. Nếu cả hai mốc đều
   ~53 dB thì tôi đã đi tìm lỗi trong bộ lọc.

⇒ FFV1 (không mất mát). Khi đó `inf` mới có nghĩa đúng là *"từng điểm ảnh"*.

---

## 5. Một lỗ cache có thật, và nó không liên quan tới lớp phủ

`giai_doan_ket_xuat._van_tay` hứa *"đổi bản dựng HAY đổi cách dựng lệnh đều đổi
nó"*, nhưng nó băm `ban_dung` + `PHIEN_BAN_KET_XUAT` + `ffmpeg`. Chuỗi lọc thì
do `che_do_render.loc_cat_noi` dựng.

⇒ Đổi cách làm mờ, đổi thứ tự chặng, thêm một bộ lọc: **cùng một bản dựng, cùng
  một vân tay, khác tệp ra.** Nó không bao giờ nổ; nó hiện ra như một lần chạy
  lại *"nhanh bất thường"* trả về đúng tệp cũ — thứ `assets.py` gọi tên là *"sót
  tham số = serve nhầm"*.

Đã thêm `PHIEN_BAN_CHE_DO` vào vân tay tệp ra, kèm một phép kiểm đọc AST chốt
điều đó.

---

## 6. Một lỗi CHỈ trình duyệt thấy

Hàng ô điều khiển của một dòng chữ có **bốn** ô (`flex:1 1 90px`); hàng của vùng
che chỉ có hai. Ở 375px bốn ô chia nhau 234px:

```
trước:  40px mỗi cái   ← ô số không hiện nổi `100`; ô chọn không hiện nổi tên màu
sau:   113px, xếp 2x2
```

⛔ `scrollWidth == clientWidth` — **không tràn ngang** — nên một chốt *"không
   được tràn ngang"* cũng im lặng ở đúng ca này. Không phép kiểm nào thấy được.

Bản sửa gắn lớp `asv-lp-o` (JS) + `flex-wrap:wrap` kèm `min-width:100px` (CSS),
và phép kiểm chốt **cả hai nửa** — thiếu một nửa thì luật không tồn tại.

---

## 7. Đối chứng: năm phép tiêm, cả năm đều làm bộ kiểm ĐỎ

| tiêm | kết quả |
|---|---|
| bỏ `expansion=none` | ĐỎ |
| `textfile=` → `text=` | ĐỎ |
| bỏ `lop_phu` khỏi vân tay | ĐỎ |
| không gọi `_loc_chu` (không nối mạch) | ĐỎ |
| LỌC BỎ ký tự điều khiển thay vì từ chối | ĐỎ |

⭐ Đối chứng của đối chứng: bản thật phải **XANH** trước, nếu không mọi phép
   tiêm đều vô nghĩa.

---

## 8. Còn nợ

| Mục | Chặn ở | Ghi chú |
|---|---|---|
| **11b — logo ảnh** | pha 08 (đường nhập ảnh) | đã khai `logo_image` vào `HAU_MVP` |
| **Xem trước lớp phủ trên khung hình** | — | khách đang đặt toạ độ bằng số, chưa kéo thả được trên khung; `vung_che` có, lớp phủ chưa |
| **`do_mo` chưa có ô trên giao diện** | — | miền đã kiểm ở máy chủ (`DO_MO_TOI_THIEU`..1), nhưng chưa có tay cầm; mặc định 1,0 |

⚠️ Hai mục cuối là **năng lực có mà chưa có đường đi tới** — đúng hình dạng lỗi
   `nang-luc-co-nhung-khong-ai-di-tren-duong`. Viết ra đây để chúng không lặng
   lẽ thành "đã xong".
