# ⏸️ Nexus: xong code, CHỜ DEPLOY — 2026-08-22

**Đọc file này trước khi chạy `deploy-self.ps1`.**

Phần Nexus đã xong và đã commit. Nó **không** được deploy vì một lý do nằm ngoài
nó: thư mục làm việc đang chứa ba dự án khác đang dở, và công cụ deploy không
tách được.

---

## Đang chờ gì

| Hạng mục | Trạng thái |
|---|---|
| Nền tảng | commit `51dbb87` — 26 file, đã chốt |
| Client | 6 commit, đã đẩy `github.com/giaitritruyenthongltt-spec/LTTnexus` nhánh `ltt-nexus` (`d8b7f2de`) |
| Bản Windows 1.4.0 | đã build + đóng gói `dist/LTTNexus-1.4.0-win-x64-install.exe`, **chưa phát hành** |
| Bản macOS | workflow `ltt-macos.yml` đã chạy lần đầu trên GitHub Actions |
| Deploy | ⏸️ **treo có chủ ý** |

---

## Vì sao treo — hai điều công cụ deploy làm mà không ai chọn được

`setup/2-cai-dat.ps1` làm đúng hai việc, và cả hai đều là "tất cả hoặc không":

```powershell
robocopy $src $appDir /E ...        # chép TOÀN BỘ thư mục làm việc
& $venvPy -m alembic upgrade head   # nâng CSDL lên đầu mới nhất
```

Không có khái niệm "chỉ lấy phần của tôi". Lúc chốt file này, cây mã đang có:

| Đang dở | Của |
|---|---|
| `apps/vps`, `llm_gateway`, `docs/VPS`, `server/templates/vps.html` | app bán máy chủ ảo (Q103, Q104) |
| `apps/ltt_llm`, `platform_core/llm` | cổng LLM |
| `apps/anhnoibo`, `render_gateway`, `platform_core/image_gen`, `docs/ANH_NOI_BO` | H37 model ảnh nội bộ |
| `alembic/versions/20260822_1900_vps_tables.py` | **migration chưa áp dụng** |

Migration đó có `down_revision = "5a3a13144782"` — **đúng đầu CSDL production hiện
tại**. Deploy bây giờ = tạo bảng của app VPS trên CSDL thật, cộng đẩy cả ba dự án
dở lên production.

Chủ sản phẩm chốt: **chờ hai phiên kia xong, deploy một lần tất cả.**

---

## Điều kiện để mở khoá deploy

1. Ba dự án trên đã commit và tự nhận là xong.
2. `python tools\gate.py` **xanh trên cây chung**. Lúc chốt file này nó đỏ ở
   `apps/ltt_llm/manifest.py` (một chuỗi chưa bọc `_()`) — **không phải** phần Nexus.
3. Chỉ còn **một** lượt gate chạy. Đã có lúc ba lượt chạy song song từ ba phiên
   khác nhau; chúng dùng chung một CSDL test PostgreSQL và làm `test_214` đỏ giả.
   Kiểm bằng:
   ```powershell
   Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
     Where-Object { $_.CommandLine -like '*gate.py*' }
   ```
4. Ai đó đã xem lại migration VPS và đồng ý cho nó chạy trên CSDL thật.

---

## Deploy rồi thì làm gì

```powershell
powershell -ExecutionPolicy Bypass -File .\deploy-self.ps1
```

Xong thì kiểm trên **URL công khai**, không chỉ loopback `127.0.0.1:8100` — Cloudflare
có cache và CSP biên riêng (quy tắc 5b của `CLAUDE.md`):

| Kiểm | Mong đợi |
|---|---|
| `https://app.lttstudios.com/nexus` | trang giới thiệu, **mở được khi chưa đăng nhập** |
| `https://app.lttstudios.com/nexus/tai` | **404** (route web-broker đã đóng) |
| `https://app.lttstudios.com/tai-xuong` | nút **Tải file cài** đứng trước, zip là lối phụ |
| `/may-cua-toi` | có bảng **Nhật ký truy cập** |
| Máy đang chạy | **chấm xanh** — đây là phép thử sửa lỗi máy-luôn-hiện-tắt |

Chấm xanh chỉ đúng **sau** khi client gọi `/status` một lần (mỗi 60 giây).

---

## Phát hành client 1.4.0 — sau khi deploy

Sau, chứ không trước: 1.4.0 gọi `/nexus-agent/web-login` cho SSO. Đường đó có
rơi mềm (mở trang đăng nhập tay) nên phát hành trước cũng không vỡ, nhưng tính
năng sẽ im lặng không hoạt động.

```powershell
powershell -ExecutionPolicy Bypass -File D:\LTTnexus\phat-hanh-windows.ps1 -Version 1.4.0
```

⚠️ **Tên file phải kết thúc bằng `install.exe`.** Bộ đóng gói của RustDesk quyết
định hành vi theo tên file:

```rust
let click_setup = args.is_empty() && arg_exe.ends_with("install.exe");
if click_setup { args = vec!["--install"]; }
```

Bản 1.2.0/1.3.0 đã phát hành nhầm với tên `-setup.exe` → bấm đúp chỉ chạy một bản
tạm trong `%LOCALAPPDATA%`, **không cài gì**, mà vẫn mở lên bình thường nên không
ai biết. Script nay có `throw` chặn.

---

## Còn nợ sau khi deploy

* **macOS**: đọc kết quả `ltt-macos.yml`. Mã `#[cfg(target_os = "macos")]` **chưa
  từng được biên dịch** — máy phát triển là Windows, không có SDK macOS. CI là chỗ
  đầu tiên nó được kiểm. Xong thì ghép `.dmg` vào bản kê (`setup_url` +
  `setup_sha256`) để bật tự cập nhật cho macOS.
* **Android**: chưa soi bằng mắt bản 1.4.0. Máy này chạy emulator được — kiểm ba
  thứ: tab LAN đã biến mất chưa, mục Giới thiệu có đúng số phiên bản LTT không,
  nút *Cập nhật* có mở thẳng file `.apk` không.
* **iOS**: chờ tài khoản Apple Developer (99 USD/năm, dùng chung cho cả macOS).
* **Ảnh chụp sản phẩm** cho trang giới thiệu — phần chữ đã đủ, chưa có ảnh.
* **Hạ tầng C1–C4** (`N7_DANH_SACH_VIEC.md`): relay còn trên Windows Server 2016
  Eval **hết hạn 15/12/2026**, chưa có relay thứ hai, `LTT_NEXUS_RELAY_HOST` chưa
  đặt nên cảnh báo relay im lặng chưa chạy, và mật khẩu relay cần đổi.
