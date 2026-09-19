# Từ điển "đã bị thay"

Một nơi duy nhất: mỗi dòng là một cụm/thuật ngữ TÀI LIỆU cũ đã không còn đúng hệ
thống hiện tại, sự thật mới thay nó, và nguồn xác nhận. `tools/quet_tai_lieu.py`
đọc bảng này để gắn cờ `THAY` khi gặp cụm cũ trong tài liệu. Thêm dòng khi có cơ
chế đổi — tài liệu cũ bị bắt ngay ở lần quét kế tiếp.

| cũ | mới | nguồn |
|---|---|---|
| canonical integrator | chính phiên tự gộp main | hợp đồng §6 |
| gate.py --doi là vòng lặp | trong phiên: test nhắm; L1/L2 khi cần; L3 một lần tổng kết | hợp đồng §4 |
| bốn bước trước lệnh nặng | hai lệnh: cua_so_yen trang-thai + tai_may | hợp đồng §4.8 |
| tối đa 3 agent | số làn = số việc độc lập | CLAUDE.md toàn cục ⭐ Chạy agent |
| chay_nang.py (khoá `cpu_nhieu`) | chay_nang.py giữ khoá `cpu_agent` | CLAUDE.md toàn cục |
| eval máy B phải khoá eval_may_b | máy B mặc định không khoá; eval_may_b chỉ đo độ trễ | CLAUDE.md toàn cục |
| admin-mvp-v3 | main | git |
| purification-v1 | main | git |
| ltt-3.8 mặc định xhigh | ltt-3.8 mặc định medium (L-33) | DECISION_LOG L-33 |
| apps/chataistudio | apps/chatltt | đổi tên app (xác nhận qua `find apps -maxdepth 1`, L-D 19/09) |
