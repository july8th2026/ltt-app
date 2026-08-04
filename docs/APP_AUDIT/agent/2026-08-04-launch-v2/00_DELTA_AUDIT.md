# Agent Canvas — delta audit sau nghiệm thu chủ sản phẩm

Ngày: 2026-08-04 · Quyết định hiệu lực: Q62, Q63, Q64.

## Vì sao phải mở lại audit H17

Điểm H17 đo tốt diện tích Canvas và safety nhưng đánh giá quá cao khả năng hiểu
của người mới. Nghiệm thu thực tế phát hiện ba vấn đề chưa được rubric kỹ thuật
bắt đúng: 18 ToolSpec ngang cấp, node ưu tiên tên nội bộ/asset, và nền tối mặc
định. Browser loop H18 còn tìm thấy node rộng 300 px nhưng bước đặt chỉ 260 px,
cùng rule CSS ép top action thành cột làm toolbar che drawer.

## Đối soát render thật

- PlenX được dùng làm benchmark interaction: palette phân nhóm content và
  transformation, node media mở composer có model/thông số; không sao chép
  nhận diện, IP hay lỗi validation.
- LTT giữ lợi thế typed ports, ownership, server quote, approval, credit hold/
  settle và validator; chỉ thay presentation hierarchy.
- Default mới: nền sáng; `Tạo văn bản`, `Tạo hình ảnh`, `Tạo video`. Search hoặc
  nút “Hiện công cụ nâng cao” mới mở toàn catalog. Theme và catalog lưu theo
  user ở server, không phụ thuộc localStorage/một thiết bị.

## Finding và trạng thái

| ID | Sev | Finding | Trạng thái |
|---|---:|---|---|
| H18-01 | P1 | Tool kỹ thuật/asset ngang cấp với hành động người dùng | RESOLVED |
| H18-02 | P1 | Nền tối mặc định không khớp lựa chọn sản phẩm | RESOLVED; light mặc định, dark tùy chọn |
| H18-03 | P1 | Node chồng nhau do spacing 260 < width 300 | RESOLVED; lưới 360×440, lề 80 |
| H18-04 | P1 | Toolbar bị ép dọc, che drawer | RESOLVED; khóa flex row, browser xác minh close |
| H18-05 | P2 | Port nâng cao của node video vẫn nhiều khi node được chọn | ACCEPT; mặc định ẩn label, Inspector dành cho advanced |
| H18-06 | P1 | Authenticated production smoke bản H18 | OPEN manual handoff; production login/health đã PASS |

## Điểm delta và gate

- Chất lượng kỹ thuật: **93/100**; safety/runtime không suy giảm.
- Mức trưởng thành sản phẩm: **87/100**; progressive disclosure đã đúng nhưng
  external 5-user study vẫn chưa có.
- Evidence confidence: **97/100** local trước deploy.
- Khuyến nghị hiện tại: **PASS local, chưa GA; deploy canary sau full gate và
  đóng authenticated production smoke**.

Browser local 1720×940 và 390×844: theme/catalog persistence qua reload, ba
node chính, advanced toggle, auto-layout, palette close; page overflow 0;
console 0. Frontend 21/21, targeted Python 22/22 và full suite **2.051 passed,
8 skipped, 23 subtests**; secret scan 0, npm audit 0. Production release 1.206
file/174,8 MB đã backup/migrate/deploy/health PASS; bundle hash khớp source.
Browser production login desktop/mobile overflow 0, console 0; authenticated
Canvas chưa chạy vì không có credential production.
