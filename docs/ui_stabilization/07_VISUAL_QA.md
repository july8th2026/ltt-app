# 07 — Kiểm thị giác (đo thật, không nhìn bằng mắt)

Chrome thật qua Playwright, **URL công khai** `https://app.lttstudios.com`.
Phép đo: `scrollWidth` vs `clientWidth` trên **mọi** phần tử.

## ⚠️ Hai lớp dương tính giả phải lọc, nếu không cả bộ số vô nghĩa

1. **`sr-only`** — cố ý rộng 1px cho trình đọc màn hình, luôn hiện ra như tràn
   (vd `58/1`).
2. **input file đã ẩn** — cũng 1px, và sau đợt sửa thì **chính bản sửa** sinh ra
   dương tính giả (vd `175/1`).

⇒ Bộ lọc: bỏ qua `sr-only` và mọi phần tử `clientWidth <= 2`.

⭐ Điều này đáng nói ra: **một bộ đo không lọc sẽ báo rằng bản sửa làm mọi thứ tệ
hơn.** Ai đọc số thô mà không hiểu chúng sẽ đi sửa những thứ đang đúng.

## Trước → sau

| Trang | Viewport | Trước | Sau |
|---|---|---|---|
| `/taoanh` | 1876 · 1440 · 1280 | **6** tràn, có thanh cuộn ngang ở `.im-controls` | **0** |
| `/taoanh` | 768 | 0 | 0 |
| `/taoanh` | 390 | 1 (`.im-chips`) | **0** |
| `/taoanh/thumbnail` | 1440 | **5**, `.th-chips` **1322/391** | **0**, cả 4 hàng chip thừa **0** |
| `/taoclipngan` | 1440 | 1, input native 371px hiện | **0**, input 1px |
| `/upscalevideo` | 1440 | 1 (đường kẻ 19/3), input native 405px hiện | 0, input 1px |
| `/jobs` | 1440 | 0 | 0 |
| `/taovideo` | 1440 | 0 (đã dùng `tv-file-input`) | 0 |
| `/autosubvideo` | 1440 | 0 (React, đã ẩn sẵn) | 0 |

**Tài liệu không tràn ngang ở bất kỳ trang/viewport nào — trước lẫn sau.** Toàn bộ
là tràn **lồng bên trong**.

## Kiểm chức năng, không chỉ hình dạng

Chạy trên trang thật sau deploy:

```text
/taoanh
  label[for] tro dung input           true
  input van nhan file                 1 tep
  ten hien thi  "Chua chon tep"  ->   "anh-tham-chieu-ten-rat-dai-de-thu-cat-chu.png"
  ten BI CAT bang ellipsis            true
  o VAN khong tran                    true   <- ten 44 ky tu KHONG dung lai duoc cai tran
  panel VAN khong tran                true

/upscalevideo   nut "Chon tep tu may" VAN mo duoc hop thoai   true
/taoclipngan    bam vung drop VAN mo duoc hop thoai           true
                input van nam trong form                      true
```

⭐ Tên tệp 44 ký tự là **cố ý**: nó dựng lại đúng lớp lỗi mà primitive sinh ra để
diệt, chỉ khác là lần này phụ thuộc vào cách khách đặt tên tệp — tức nếu hỏng thì
sẽ không ai tái hiện được.

## Lỗi console

**0** từ ứng dụng, ở mọi trang đã đo, cả 1440 lẫn 390.

## Chưa đo

- 1920 và 1024: bỏ qua có chủ ý. Đo tại 1876/1440/1280 cho **số giống hệt nhau**
  (panel bị khoá `minmax(340px,430px)`), nên đây không phải lỗi phụ thuộc viewport.
- `/chataistudio`, `/prompt-ai-ommi`, `/agent`: chưa đo. Hai cái sau là bundle
  React có CSS riêng, không chịu ảnh hưởng của đợt sửa này.
