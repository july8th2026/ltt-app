# Chuyển sang máy chủ và cập nhật

## Phần 1 — Lần đầu: chép thư mục sang máy chủ

### Bước 1. Dọn trước khi chép

Trên máy bạn:

```powershell
cd d:\LTTSTUDIOSAPP
python -m pytest -q                      # phải xanh hết
python tools\scan_source_secrets.py      # phải 0 finding
```

Không xanh thì **dừng lại**. Mang lỗi sang máy chủ chỉ tốn thêm một vòng.

### Bước 2. Chép sang máy chủ

Cách nào cũng được: USB, ổ mạng, Remote Desktop kéo thả, hay nén rồi gửi.

Chép **nguyên thư mục**. Không cần lọc gì — thư mục này **không chứa bí mật
nào**: `data/config.json` chỉ là bản mẫu, `secrets/` rỗng. Bí mật thật sẽ được
sinh **trên máy chủ** ở bước cài.

Đặt ở đâu cũng được, ví dụ `C:\Temp\LTTSTUDIOSAPP`. Bộ cài sẽ tự chép vào
`C:\LTTPlatform\app\`.

### Bước 3. Cài trên máy chủ

Mở **PowerShell bằng Run as administrator**, vào đúng thư mục vừa chép:

```powershell
cd C:\Temp\LTTSTUDIOSAPP

powershell -ExecutionPolicy Bypass -File .\setup\1-kiem-tra-may.ps1
powershell -ExecutionPolicy Bypass -File .\setup\2-cai-dat.ps1
```

Hoặc mở Claude Code ngay tại thư mục đó và bảo:

```
Đọc CLAUDE.md rồi cài đặt hệ thống này lên máy chủ theo setup/.
Dừng lại hỏi tôi ở bước cần đăng nhập Cloudflare.
```

⚠️ **Bước 2 in mật khẩu admin đúng MỘT LẦN.** Lưu lại ngay. Mật khẩu không
được ghi ở đâu cả, chỉ lưu dạng hash — mất là phải tạo lại.

### Bước 4. Điền cấu hình thật

```powershell
notepad C:\LTTPlatform\data\config.json
```

Cần điền: `sheet_id`, `google_credentials_path`, tên các cột, thông tin Meta
App và TikTok App. Chỗ nào còn `REPLACE_ME` là chưa xong.

Chép file Service Account JSON của Google vào `C:\LTTPlatform\secrets\`.

### Bước 5. Dựng Cloudflare Tunnel

```powershell
powershell -ExecutionPolicy Bypass -File .\setup\3-cloudflare.ps1
```

Script sẽ **dừng ở phần đăng nhập** và in ra một đường link. Mở link đó trên
trình duyệt **máy nào cũng được**, đăng nhập Cloudflare, chọn `lttstudios.com`.
Xong thì script tự chạy tiếp.

**Đừng ngắt lệnh vì tưởng nó treo** — nó đang đợi bạn.

### Bước 6. Nghiệm thu

```powershell
powershell -ExecutionPolicy Bypass -File .\setup\4-nghiem-thu.ps1
```

Rồi mở `https://app.lttstudios.com`, đăng nhập bằng mật khẩu ở bước 3.

---

## Phần 2 — Cập nhật code về sau

Sửa code ở **thư mục nguồn trên máy phát triển**, không sửa trong
`C:\LTTPlatform\app\`.

### Cách A — chép lại thư mục (đơn giản, khuyên dùng)

1. Trên máy phát triển: `python -m pytest -q` phải xanh
2. Chép thư mục sang máy chủ, ghi đè bản cũ ở `C:\Temp\LTTSTUDIOSAPP`
3. Trên máy chủ chạy lại:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\setup\2-cai-dat.ps1
   ```

Script chạy lại được nhiều lần và **an toàn**:
- `data/config.json` — giữ nguyên, không ghi đè
- `secrets/app.env` — giữ nguyên, mật khẩu và khoá mã hoá không đổi
- `app/` cũ chuyển thành `app.previous/` để rollback
- Dịch vụ tự khởi động lại

4. `powershell -ExecutionPolicy Bypass -File .\setup\4-nghiem-thu.ps1`

### Cách B — dùng gói zip (khi cần bản có đánh số phiên bản)

```powershell
# Máy phát triển
python tools\build_release.py --output C:\Temp\ltt-release

# Máy chủ
powershell -ExecutionPolicy Bypass -File C:\LTTPlatform\app\deploy\windows\update.ps1 -SourceZip C:\Temp\ltt-release-1.0.0.zip
```

`build_release.py` tự quét bí mật **trên đúng nội dung sắp gửi đi** và **dừng
lại nếu phát hiện** — chốt chặn cuối để khoá/token không rời máy.

### Nếu hỏng

```powershell
powershell -ExecutionPolicy Bypass -File C:\LTTPlatform\app\deploy\windows\rollback.ps1
```

Đưa `app.previous\` về lại. `data\` không bị ảnh hưởng nên không mất gì.

---

## Hai vùng trên máy chủ — nhớ kỹ

```
C:\LTTPlatform\app\        CODE     → bị XOÁ và THAY TOÀN BỘ mỗi lần cập nhật
C:\LTTPlatform\data\       DỮ LIỆU  → cập nhật KHÔNG BAO GIỜ chạm tới
C:\LTTPlatform\secrets\    BÍ MẬT   → cập nhật KHÔNG BAO GIỜ chạm tới
```

Hệ quả: **sửa file trong `app\` là mất trắng ở lần cập nhật sau** — mất âm
thầm, không báo lỗi gì. Đây là loại lỗi khó truy nhất: bug quay lại mà code
trên máy phát triển vẫn đúng.

---

## Sao lưu — làm ngay sau khi cài xong

```powershell
Copy-Item C:\LTTPlatform\secrets\app.env D:\backup\app.env.txt
```

⚠️ **Mất `LTT_TOKEN_ENCRYPTION_KEY` là mất toàn bộ token Facebook/TikTok đã
lưu.** Chúng được mã hoá bằng khoá đó và **không có cách khôi phục**. Chép ra
chỗ an toàn ngoài máy chủ, ngay hôm nay.

Sao lưu định kỳ:
```powershell
powershell -ExecutionPolicy Bypass -File C:\LTTPlatform\app\deploy\windows\backup.ps1
```

---

## Không bao giờ đưa lên git hay chia sẻ

```
data/config.json          App Secret, Client Secret
data/*.enc                token Facebook/TikTok đã mã hoá
secrets/app.env           khoá phiên, khoá mã hoá token, hash mật khẩu
secrets/*.json            khoá riêng Google Service Account
cloudflare/config.yml     tunnel ID
cloudflare/*.json         credentials tunnel
```

Chạy `python tools\scan_source_secrets.py` trước khi chia sẻ bất cứ thứ gì.
