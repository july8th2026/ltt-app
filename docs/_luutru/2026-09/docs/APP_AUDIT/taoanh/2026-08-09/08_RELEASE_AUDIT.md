# A10 — Release audit H26.9

Trạng thái: **PASS development · chưa deploy · G8 BLOCKED đến H26.12**.

## Hành vi đã xác minh

- Catalog chỉ còn một entry Tạo ảnh AI; General và Thumbnail có URL canonical
  `/taoanh` và `/taoanh/thumbnail`.
- `/thumbnail` trả 308 để bảo toàn deep link; executor, job type, credit, output
  URL và history cũ không đổi.
- Fragment Thumbnail yêu cầu đăng nhập, dùng CSRF, submit HTMX tạo job thật rồi
  trả `HX-Redirect`; lỗi validation trả lại fragment, không nhét full document.
- Browser fixture owner-scoped có output done/error của hai mode. Đã thao tác
  quote ×2, submit 500→490 credit, history, compare, remix và General edit.
- Desktop 1920×1080 và mobile 390×844: không horizontal overflow; console cuối
  0 error/0 warning; request app liên quan 200/204.
- English catalog: 907 chuỗi, 0 thiếu, 0 fuzzy; nhãn mới đã kiểm trên browser.

## Kết quả test thật

| Lệnh/phạm vi | Kết quả |
|---|---|
| Targeted H26.9 + marketplace/image/thumbnail | PASS 32 test trong 20,17 giây |
| `python tools\\gate.py --quick` | PASS 8/8 trong 27 giây |
| Full gate lượt phát hiện test cũ | FAIL 8/9; 2.564 pass, 1 kỳ vọng alias cũ fail |
| `python tools\\gate.py` lượt cuối | PASS 9/9 trong 1.673,8 giây; pytest 1.648,3 giây |

## Rollback

Revert commit H26.9. Không có migration hay xóa dữ liệu; hai executor, bảng,
job, credit và storage độc lập vẫn còn. Presentation có thể quay lại hai trang
mà không sửa history. Không deploy/canary riêng trong phase này.
