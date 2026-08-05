
# 02 — Chất lượng hiển thị mobile

**Cách đo:** Chrome thật, viewport 390×844, quét 15 trang sau khi đăng nhập.
Đo bằng `getBoundingClientRect` và công thức tương phản WCAG 2.1, không chấm bằng
mắt.

## 1. Tràn ngang — PASS tuyệt đối

| Trang | `scrollWidth` |
|---|---:|
| `/`, `/jobs`, `/nap`, `/tai-khoan` | 390 |
| `/taoanh`, `/thumbnail`, `/kichban`, `/autosubvideo` | 390 |
| `/taovideo`, `/upscalevideo`, `/taoclipngan` | 390 |
| `/chataistudio`, `/mediatools` | 390 |
| `/agent`, `/prompt-ai-ommi` | 390 |

**15/15 trang không tràn ngang.** Với một nền tảng 13 app do nhiều đợt xây, đây
là kết quả tốt và cho thấy hợp đồng chiều rộng (Q61) cùng `ltt.css` đang có tác
dụng thật.

## 2. Tương phản — PASS

Đo mọi phần tử có chữ trên `/`, `/prompt-ai-ommi`, `/taoanh`, `/jobs`, `/agent`,
so với ngưỡng AA (4.5:1 chữ thường, 3:1 chữ lớn):

**0 lỗi trên cả 5 trang.**

## 3. Vùng chạm — FAIL, nhưng chỉ ở MỘT chỗ

Ngưỡng WCAG 2.2 AA mục 2.5.8: tối thiểu 24×24 CSS px.

Lần đếm đầu tiên của tôi cho ra 22–41 phần tử "quá nhỏ" mỗi trang. **Con số đó
sai.** Kiểm lại từng phần tử thì 31/39 ở `/thumbnail` là radio và checkbox
13–18px **nằm trong label 44px** — người dùng bấm vào label, hoàn toàn đạt. Nếu
tôi báo cáo con số đầu, bạn đã đi sửa 31 thứ không hỏng.

Sau khi loại dương tính giả, còn lại:

| Vị trí | Số | Kích thước | Đánh giá |
|---|---:|---|---|
| **Footer nền tảng** (`nav a`) | **8** | ~15px cao | **FAIL** — có ở **mọi trang** |
| Ô tìm kiếm header marketing | 1 | 158×21 | FAIL nhẹ |

Tám link footer: *Hệ sinh thái LTT · Ứng dụng · Hỗ trợ · Liên hệ · Credit &
thanh toán · Quyền riêng tư · Điều khoản · Xóa dữ liệu*.

**Điểm quan trọng:** đây là **một component dùng chung**. Sửa một chỗ là đạt cho
cả 15 trang. Đó là loại lỗi tốt nhất trong các loại lỗi.

Mức nghiêm trọng thật sự: **P2**, không phải P0/P1. Chúng là link phụ trợ ở cuối
trang (chính sách, liên hệ), không nằm trên luồng tạo giá trị hay luồng trả tiền.
Bấm trượt gây bực mình, không gây mất tiền hay mất dữ liệu.

## 4. Điều CHƯA đo — nói rõ để không ai tưởng đã xong

Quy tắc §5 buộc ghi unknown là unknown:

- **Bàn phím và focus order**: chưa đo.
- **Trình đọc màn hình**: chưa đo.
- **Thiết bị thật**: chưa — chỉ mô phỏng viewport trong Chrome desktop. Cảm ứng
  thật, bàn phím ảo che nội dung, và safe-area của iOS đều chưa kiểm.
- **Xoay ngang (landscape)**: chưa đo.
- **`prefers-reduced-motion`**: chưa đo.

Vì vậy điểm accessibility ở scorecard công bố kèm độ tin cậy thấp, không phải
một dấu tích xanh.
