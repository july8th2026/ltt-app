# Di trú lược đồ CSDL (Alembic)

Mọi thay đổi lược đồ đi qua đây. **Không bao giờ sửa bảng bằng tay trên máy
chủ** — lần cập nhật sau sẽ không biết ai đã sửa gì, và hai máy sẽ lệch lược đồ
mà không có cách nào phát hiện.

## Lệnh hay dùng

```powershell
# Xem dang o dau
alembic current

# Tien len ban moi nhat
alembic upgrade head

# Lui lai mot buoc
alembic downgrade -1

# Sinh migration tu thay doi trong platform_core/models.py
alembic revision --autogenerate -m "them bang users"

# Xem truoc SQL ma KHONG chay (dua cho nguoi quan tri CSDL duyet)
alembic upgrade head --sql
```

Tất cả đều cần biến môi trường `LTT_DATABASE_URL`. Trên máy chủ nó nằm trong
`secrets\app.env`.

## Ba quy tắc

**1. Luôn đọc lại file migration mà `--autogenerate` sinh ra trước khi chạy.**
Alembic dò được việc thêm/bớt bảng và cột, nhưng nó **không hiểu ý định**. Đổi
tên một cột sẽ bị nó hiểu thành "xoá cột cũ, thêm cột mới" — chạy nguyên như
vậy là mất sạch dữ liệu của cột đó.

**2. Mỗi migration phải viết được `downgrade()`.** Không phải vì hay dùng, mà
vì viết được đường lùi buộc ta nghĩ xem thay đổi này có mất dữ liệu không. Nếu
không viết nổi đường lùi thì đó là dấu hiệu thay đổi này cần một bước trung
gian.

**3. Sao lưu trước khi chạy trên máy chủ.** `deploy\windows\backup.ps1` có bước
`pg_dump`. Một migration hỏng giữa chừng trên CSDL có dữ liệu thật là tình
huống mà bản sao lưu là thứ duy nhất cứu được.

## Vì sao chuỗi kết nối không nằm trong `alembic.ini`

Vì nó chứa mật khẩu, và `alembic.ini` được theo dõi trong git. `alembic/env.py`
đọc từ `LTT_DATABASE_URL`, và mọi thông báo lỗi đi qua `che_mat_khau()` trước
khi in ra — thông báo lỗi của driver thường nhúng nguyên chuỗi kết nối, và
người ta hay dán nguyên nó vào chat để hỏi.
