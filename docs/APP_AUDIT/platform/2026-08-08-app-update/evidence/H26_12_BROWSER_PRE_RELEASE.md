# H26.12 — Browser pre-release

Ngày kiểm: 2026-08-09. Môi trường: fixture cô lập ở cổng 8121, CSDL và storage
riêng, provider giả an toàn. Không dùng dữ liệu hay provider production.

## Ma trận hiển thị

- Desktop 1920×1080: 11 route customer hợp lệ trả 200, không tràn ngang,
  console không error/warning và không có request hỏng.
- Mobile 390×844: cùng 11 route đạt 200 và không tràn ngang sau khi sửa lưới
  thư viện Seedance về một cột dưới 640 px.
- Route `/account` không thuộc sản phẩm; profile là menu tài khoản nên không
  đưa 404 của route thử nhầm này vào ma trận phát hành.

## Luồng chức năng

- Chat AI: tạo hội thoại, gửi tin, nhận SSE, số dư 100 → 97, không lỗi giao
  diện/mạng.
- Agent Canvas: starter Text → Image, chặn đúng khi thiếu prompt; sau khi nhập
  prompt báo giá 8 credit, chạy đủ 2 bước, quyết toán 8/8 và số dư 97 → 89.
- Tạo ảnh AI: phát hiện thẻ đứng `queued 0%` dù backend xong. Đã thêm polling
  owner-scoped qua `/api/jobs/{id}` và chỉ thay vùng lịch sử, không reload/làm
  mất form. Browser thấy `queued 0%` → `Hoàn tất` + output thật sau 2 poll,
  số dư 84 → 79; compare/clear tiếp tục hoạt động.

## Lỗi đã khóa

1. Seedance mobile: rule hai cột khai sau rule mobile làm `.tv-empty` rộng hơn
   viewport. Khóa một cột ở rule cuối và giới hạn box sizing/min-width.
2. Tạo ảnh AI: thiếu live polling trong lịch sử output. Khóa data job contract,
   API polling và refresh riêng vùng history bằng regression source test.

## Kết quả kiểm cục bộ

- `tests/test_116_taoanh_ui.py` + `tests/test_158_taovideo_h26.py`: 9 PASS.
- Browser sau bản sửa cuối: console 0, request fail 0, response >=400 là 0.
- Quick gate lần đầu bắt đúng một chuỗi client chưa qua i18n; đã chuyển sang
  label do server dịch. Quick gate lần hai PASS 8/8.

Đây mới là pre-release; chưa thay cho full gate, backup/rollback, canary và
post-deploy audit còn lại của H26.12.
