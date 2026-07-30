"""
platform_core — phần nền tảng dùng chung cho mọi app.

Tên là `platform_core` chứ không phải `platform` là có lý do: `platform` là
module chuẩn của Python (`import platform` để lấy thông tin hệ điều hành).
Một package cùng tên ở thư mục gốc sẽ CHE MẤT stdlib, và lỗi hiện ra ở những
thư viện không liên quan gì — cực khó truy. Đừng đổi lại.

Nguyên tắc: `platform_core` không được import gì từ `apps/`. Chiều phụ thuộc
chỉ đi một hướng — app biết nền tảng, nền tảng không biết app nào tồn tại.
"""
