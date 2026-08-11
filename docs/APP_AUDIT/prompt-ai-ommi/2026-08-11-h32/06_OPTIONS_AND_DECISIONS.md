# Phương án và quyết định

| Vấn đề | A — khuyến nghị | B | C | Chọn |
|---|---|---|---|---|
| Tích hợp catalog | Lưu ID, resolve ownership lúc dùng | Chép body vào project | Chỉ trang thư viện | A |
| Lưu brief | Explicit save + flush trước action | onBlur | autosave debounce ngầm | A |
| Preview | Deterministic/free/preflight | Gọi AI mất credit | Không preview | A |
| Tính năng module nguồn | Chắt lọc customer core | Copy toàn bộ | Giữ app cũ | A |
| Team/admin controls | Giữ ở quản trị | Đưa ra customer | Xóa backend | A |
| Provider thiếu | Gate conditional, không giả kết quả | Mock rồi báo pass | Dùng production key | A |

Quyết định không tạo Q nền tảng mới: đây là hiện thực hóa hợp đồng H26/Q81 đã
có, không đổi kiến trúc nền tảng.
