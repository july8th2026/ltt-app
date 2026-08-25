# Câu lệnh đưa cho Claude

Chép nguyên câu, thay phần trong `<...>`. Mỗi lệnh viết sao cho Claude tự biết
phải kiểm tra và nghiệm thu thế nào, không phải đoán.

Mở Claude Code **ngay tại thư mục chứa mã nguồn** — trên máy phát triển là
`d:\LTTSTUDIOSAPP`, trên máy chủ là chỗ bạn vừa chép sang. Claude đọc
`CLAUDE.md` ở gốc để biết đang ở máy nào và phải làm gì.

---

## Mở đầu phiên làm việc

```
Đọc docs/QUYET_DINH_NEN_TANG.md, docs/KE_HOACH_TRIEN_KHAI.md và docs/NHAT_KY.md.
Chạy python -m pytest -q để biết trạng thái hiện tại.
Tóm tắt: đang ở đâu, còn gì dở, việc tiếp theo nên làm là gì.
```

---

## Thêm một app mới

```
Thêm app mới tên <tên app>, slug <slug>, đường dẫn app.lttstudios.com/<slug>.

App làm việc này: <mô tả cụ thể — nhận gì, xử lý gì, trả ra gì>.
Chạy bằng: <API bên ngoài / ffmpeg cục bộ / model GPU cục bộ>.
Giá credit tính theo: <ví dụ: số giây video × độ phân giải>.

Làm theo docs/03_THEM_APP_MOI.md. Không sửa file nào trong platform_core/
hay server/ — nếu buộc phải sửa thì dừng lại và giải thích vì sao, vì đó là
dấu hiệu hợp đồng app còn thiếu.

Xong thì chạy pytest và cho tôi xem app mới đã hiện trên trang chủ.
```

Câu **"không sửa platform_core/ hay server/"** là quan trọng nhất. Nó biến
hợp đồng app thành thứ được kiểm chứng thật, thay vì chỉ là ý định.

---

## Nghiệm thu hạ tầng sau khi sửa

```
Chạy nghiệm thu hạ tầng (⚠️ app `demo` đã gỡ 2026-08-25 — dùng một app thật và
chấp nhận nó tiêu credit, hoặc chạy `pytest tests/test_67 tests/test_68` là bộ
kiểm cùng chuỗi mà không tốn gì):
1. python -m pytest -q  → phải xanh hết
2. python tools/scan_source_secrets.py  → phải 0 finding
3. chạy uvicorn cục bộ, mở /, xác nhận trang chủ liệt kê đủ app
4. mở một app bất kỳ, chạy một job, xác nhận có kết quả và có số credit
Báo lại từng bước kèm kết quả thật.
```

---

## Cài lần đầu trên máy chủ (chạy Claude NGAY TRÊN máy đó)

```
Đọc CLAUDE.md.
Cài đặt hệ thống này lên máy chủ, chạy setup/ theo đúng thứ tự 1 → 2 → 3 → 4.

Ở bước 3 (Cloudflare), lệnh `cloudflared tunnel login` sẽ in ra một đường
link rồi đợi — đưa link đó cho tôi, tôi đăng nhập bằng trình duyệt rồi bạn
chạy tiếp. Đừng ngắt lệnh vì tưởng nó treo.

Ở bước 2, mật khẩu admin chỉ hiện một lần — nhắc tôi lưu lại.
Báo lại kết quả từng bước.
```

---

## Cập nhật code lên máy chủ

```
Cập nhật máy chủ theo docs/01_COPY_LEN_SERVER.md phần 2.
Chạy lại setup/2-cai-dat.ps1 rồi setup/4-nghiem-thu.ps1.
Sau đó mở https://app.lttstudios.com kiểm tra thật từng trang và báo lại
nội dung đọc được. Không chỉ dựa vào health check.
```

---

## Khi có sự cố

```
https://app.lttstudios.com đang <mô tả triệu chứng>.
Vào VPS xem log dịch vụ và log Caddy, tìm nguyên nhân thật.
Nếu do bản cập nhật vừa rồi thì rollback trước, rồi mới tìm hiểu.
Đừng đoán — lấy bằng chứng từ log.
```

---

## Kiểm tra bảo mật trước khi mở cho khách ngoài

```
Rà soát bảo mật trước khi có người dùng ngoài công ty:
- mọi route trả dữ liệu có kiểm tra quyền sở hữu chưa
- route tải file có chặn path traversal chưa
- có chỗ nào lộ đường dẫn file hay stack trace ra trình duyệt không
- bí mật có bao giờ đi xuống HTML/JS không
Báo cáo từng mục kèm file:dòng, và mức nghiêm trọng. Chưa sửa vội.
```

---

## Bàn giao cuối phiên

```
Cập nhật docs/_luutru/PROJECT_MEMORY.md theo mẫu ở cuối file đó:
đã làm gì, lệnh test nào chạy và kết quả thật, quyết định gì và vì sao,
còn tồn đọng gì, việc tiếp theo.
```

---

## Cách viết lệnh cho hiệu quả

**Nên:**
- Nói rõ **nghiệm thu bằng gì** ("chạy pytest", "mở trình duyệt xem thật")
- Nêu **ràng buộc** ("không sửa platform_core/")
- Yêu cầu **dừng lại và hỏi** khi phải phá ràng buộc

**Không nên:**
- "làm cho nó chạy" — không có tiêu chí nào để biết đã xong
- "sửa nhanh giúp" — bỏ qua test là cách tạo ra lỗi ở production
- Gộp nhiều việc lớn vào một lệnh — hỏng thì không biết hỏng ở đâu

**Một câu nên thêm vào mọi lệnh lớn:**

```
Nếu phát hiện tôi hiểu sai điều gì, hoặc cách làm này có vấn đề, hãy nói
thẳng trước khi làm.
```
