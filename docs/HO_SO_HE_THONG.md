# Bộ hồ sơ hệ thống

`ho_so_he_thong.txt` ở root là hồ sơ code đầy đủ dành cho AI và người mới tiếp
quản dự án. File được sinh từ code, không chỉnh tay.

## Cách dùng

```powershell
python tools\build_system_profile.py
python tools\build_system_profile.py --check
```

Lệnh đầu tạo lại hồ sơ bằng UTF-8 không BOM và ghi atomically. Lệnh thứ hai
không sửa file; nó trả mã lỗi nếu fingerprint hoặc nội dung không còn khớp.
`tools/gate.py` luôn chạy chế độ `--check`, nên thay đổi code mà quên cập nhật hồ
sơ sẽ bị phát hiện trước khi commit/deploy.

## Hồ sơ chứa gì

- kiến trúc và luồng job/credit/worker;
- manifest, job type, ToolSpec, route và file map của từng app;
- route HTTP, bảng SQLAlchemy, chuỗi migration Alembic;
- frontend/bundle, biến môi trường theo **tên**, quality gate và deploy;
- chỉ mục các file nguồn liên quan cùng fingerprint nội dung;
- snapshot nguyên văn toàn bộ source text trong phạm vi: code app, backend,
  frontend, worker/sidecar, engine vendored, migration, deploy/setup, tool và
  test. Mỗi file có path, SHA-256 byte gốc, số byte và số dòng.

Không có giới hạn dung lượng file hay tổng hồ sơ. Generator chỉ nhận source
UTF-8 từ allowlist; gặp file không giải mã được sẽ fail thay vì âm thầm bỏ code.
Hồ sơ không đọc `data/`, `secrets/`, log, browser profile, dependency/cache,
file nhị phân, file tạm hoặc dữ liệu người dùng. Nó không thay thế
`QUYET_DINH_NEN_TANG.md`, source code, test hay kiểm tra production live.

## Khi có thay đổi

1. Sửa code và test trước.
2. Chạy `python tools\build_system_profile.py`.
3. Review diff của `ho_so_he_thong.txt`; thay đổi ngoài dự kiến là tín hiệu cần
   kiểm tra lại manifest/route/migration.
4. Chạy `python tools\gate.py`.

Phạm vi và exclusions nằm trong `tools/system_profile_config.json` (schema 2).
Test khóa đủ các miền code vận hành và đối chiếu một block cho mọi source được
chọn. Mở rộng phạm vi phải có test và vẫn tuân thủ quy tắc không đưa secret/
runtime data vào hồ sơ.
