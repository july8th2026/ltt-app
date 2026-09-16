# Tài khoản THỬ dùng chung — kiểm GUI/API trên production

Chủ dự án chốt 16/09/2026: có sẵn **3 tài khoản thử** cho mọi phiên, cấp credit thoải
mái để chạy test. Công cụ: `tools/tai_khoan_thu.py`.

| Email | Dùng cho |
|---|---|
| `khach1.thu@lttstudios.local` | khách thường, luồng chính |
| `khach2.thu@lttstudios.local` | khách thứ hai (kiểm quyền giữa hai tài khoản, chia sẻ, kho chung) |
| `khach3.thu@lttstudios.local` | dự phòng / luồng phá hoại (hết credit, xoá, huỷ) |
| `thu.giongnoi@lttstudios.local` | **chủ 25 giọng kho chung LTT Voice** — chỉ dùng để kiểm góc nhìn chủ giọng |

Cả bốn là `role=user` (không admin), `is_verified`, email `.local` (không nhận thư thật).

## Mật khẩu ở đâu

`C:\LTTPlatform\secrets\tai_khoan_thu.json` (theo `LTT_SECRETS_DIR`) — **không** trong git,
**không** in ra màn hình. Đừng mở tệp để chép mật khẩu vào form: dùng `--cookie`.

## Lệnh

Chạy bằng venv production từ gốc kho (`D:\LTTSTUDIOSAPP` hoặc worktree):

```powershell
$PY  = "C:\LTTPlatform\venv\Scripts\python.exe"
$ENV = "--app-env", "C:\LTTPlatform\secrets\app.env"

& $PY tools\tai_khoan_thu.py @ENV --liet-ke          # email · credit · có trong kho không
& $PY tools\tai_khoan_thu.py @ENV --tao-bo           # đảm bảo 3 tài khoản + nạp bù tới 5000 credit
& $PY tools\tai_khoan_thu.py @ENV --tao-bo --nap-den 20000
& $PY tools\tai_khoan_thu.py @ENV --email khach2.thu@lttstudios.local --nap 1000
& $PY tools\tai_khoan_thu.py @ENV --cookie khach1.thu@lttstudios.local
#   -> session=<giá trị>
```

`--cookie` đăng nhập bằng HTTP vào `http://127.0.0.1:8100` (đổi bằng `--goc`) và chỉ in
cookie phiên. Phiên đó dùng được trên `https://app.lttstudios.com` (cùng máy chủ).

## Dùng với Playwright

```bash
COOKIE=$("C:/LTTPlatform/venv/Scripts/python.exe" tools/tai_khoan_thu.py \
  --app-env C:/LTTPlatform/secrets/app.env --cookie khach1.thu@lttstudios.local | sed 's/^session=//')
```

```js
await page.context().addCookies([{ name: 'session', value: COOKIE,
  domain: 'app.lttstudios.com', path: '/', secure: true, httpOnly: true }]);
await page.goto('https://app.lttstudios.com/ltt-voice');
```

Mỗi phiên dùng **profile trình duyệt riêng** (`playwright-cli -s=<tên>`), không dùng Chrome
thật của chủ dự án.

## Luật

- ⛔ Chỉ ghi vào tài khoản đuôi `.local`; công cụ từ chối email khác.
- ⛔ Không nâng `role=admin` cho tài khoản thử — nó phải nhìn đúng bề mặt khách.
- Credit đi bằng bút toán `grant` (`credit.cap_tay`) có ghi chú "TAI KHOAN THU" — không
  phải khoản nạp tiền của khách, không vào doanh thu.
- `--dat-lai-mat-khau` thu hồi mọi phiên cũ của tài khoản đó ⇒ phiên khác đang dùng
  cookie cũ sẽ bị đăng xuất. Chỉ đặt lại khi thật cần.
- Thiếu tài khoản hoặc kho mất ⇒ chạy lại `--tao-bo` (tạo lại hoặc đặt lại mật khẩu những
  tài khoản chưa có trong kho).
