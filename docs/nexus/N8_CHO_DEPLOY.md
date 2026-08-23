# LTT Nexus — trạng thái sau đợt deploy 2026-08-23

Trước đây file này tên là "chờ deploy". **Đã deploy xong** lúc 13:22 và 14:50
ngày 23/08 (`deploy exit rc=0`). Giữ tên file để link cũ không gãy, nhưng nội
dung nay là **trạng thái thật**, không phải hàng đợi.

---

## Đang sống trên production

Xác minh trên **URL công khai** (không phải loopback — Cloudflare có cache và CSP
biên riêng, quy tắc 5b của `CLAUDE.md`):

| Kiểm | Kết quả |
|---|---|
| `/nexus` | **200 khi chưa đăng nhập** — trang giới thiệu 9 khối |
| `/en/nexus` | 200, **không rò một chữ tiếng Việt nào** |
| `/nexus/tai`, `/nexus/nhat-ky` | **404** — luồng web-broker đã đóng sau cờ `LTT_NEXUS_WEB_BROKER` |
| `/tai-xuong` | **5 nền tảng**, Windows mời file cài trước, zip là lối phụ |
| `/may-cua-toi` | 303 login; có bảng **Nhật ký truy cập** |
| `/nexus-sso?ma=x` | 303 — vé bịa bị từ chối |
| Máy đang chạy | **`online=True`** — lỗi "máy luôn hiện tắt" đã chết, đo bằng dữ liệu thật |

Bố cục đo trên bản đang chạy (1440px): mọi khối bắt đầu ở **x=146**, kết thúc
**1278** — kể cả hàng nền tảng vốn thụt vào 70px. 5 thẻ × 217px, một hàng, không
tràn ngang, không vùng chạm nào dưới 24px.

---

## Phiên bản đang phát hành

```
windows  1.4.0    macos  1.4.0    macos_intel  1.4.0    android  1.4.0
ios    → 1.1.0
```

**Android đã lên 1.4.0** (23/08, build trong WSL — xem `BUILD_ANDROID.md`). Kho
trong WSL từng đứng ở **1.1.0 suốt nhiều ngày mà không ai biết**, vì APK cũ vẫn
chạy bình thường; nên trước khi phát hành phải `git reset --hard origin/ltt-nexus`
rồi **chứng minh** APK chứa mã mới, đừng tin "build xong là đúng bản":

```bash
strings -a .../librustdesk.so | grep -c ltt_tab_tip_lan   # nhãn tab 1.4.0
unzip -p app-release.apk lib/arm64-v8a/libapp.so | strings | grep -c nexusClientWebLoginUrl
```

**iOS còn ở 1.1.0** — tức người dùng iOS vẫn có tab "Đã tìm thấy" bày máy ngoài
tài khoản, vẫn tự khai ID ra mạng LAN, mục Giới thiệu vẫn mang thương hiệu
RustDesk. Build được bằng workflow `ltt-ios.yml`; file `.ipa` chưa ký nên chỉ cài
qua SideStore/Sideloadly. Ký Ad Hoc cần tài khoản Apple Developer 99 USD/năm
(dùng chung cho cả macOS).

---

## Hai cái bẫy đã trả giá, đừng dẫm lại

**1. Tên file cài quyết định hành vi.** Bộ đóng gói của RustDesk:

```rust
let click_setup = args.is_empty() && arg_exe.ends_with("install.exe");
if click_setup { args = vec!["--install"]; }
```

Bản 1.2.0/1.3.0 phát hành nhầm tên `-setup.exe` → bấm đúp **chỉ chạy một bản tạm**
trong `%LOCALAPPDATA%`, không cài gì, mà vẫn mở lên bình thường nên không ai biết.

**2. Chốt chặn phải kiểm KẾT QUẢ, không kiểm biến vừa gán.** Bản vá đầu cho lỗi
trên viết `if (-not $setup.EndsWith("install.exe"))` ngay sau dòng gán `$setup`
kết thúc bằng đúng chuỗi đó — một câu hỏi không bao giờ sai được. Trong khi đó URL
trong bản kê vẫn viết cứng `-setup.exe`, nên 1.4.0 phát hành với bản kê trỏ vào
**file 404**. Nay URL dẫn xuất từ tên file, và chốt chặn đọc lại bản kê từ đĩa rồi
đối chiếu với file có thật.

---

## Còn nợ

* **🔴 iOS 1.4.0** — xem mục trên.
* **163 mục `#, fuzzy`** còn lại trong `locale/en/LC_MESSAGES/messages.po`. Đã rà
  và sửa **47 mục dịch sai** (23/08), trong đó ba mục nói ngược sự thật:
  `"Bắt buộc"→"Optional"`, `"đang khỏe"→"Pending"`, `"đang tắt"→"Finishing"`.
  163 mục còn lại chưa thấy dấu hiệu gán nhầm — kiểm bằng
  `python tools\check_fuzzy_dich.py`. **Đừng chạy `msgattrib --clear-fuzzy` cho cả
  tệp**: nó bật nguyên các bản đoán bừa của Babel lên production.
* **Ảnh chụp sản phẩm** cho trang giới thiệu. Hero đang dùng **khung app mô phỏng
  bằng HTML/CSS** — cố ý, vì ảnh chụp thật chứa ID máy và mật khẩu một lần. Muốn
  dùng ảnh thật thì phải che hai thứ đó trước.
* **Hạ tầng C1–C4** (`N7_DANH_SACH_VIEC.md`): relay còn trên **Windows Server 2016
  Eval hết hạn 15/12/2026** (hết hạn → máy tự tắt mỗi giờ), chưa có relay thứ hai,
  `LTT_NEXUS_RELAY_HOST` chưa đặt nên cảnh báo relay im lặng chưa chạy, và mật khẩu
  relay cần đổi.

---

## Deploy trên máy này cần gì

`deploy-self.ps1` **cần quyền Administrator** (nó `Stop-Service`/`Start-Service`
ba dịch vụ nssm). Shell của Claude không nằm trên phiên desktop tương tác nên
`Start-Process -Verb RunAs` **không dựng nổi hộp thoại UAC** (đã đo: `consent.exe`
= 0, màn hình không có gì), và `schtasks /rl HIGHEST` thì chính nó cũng cần admin.

Cách chạy được: dùng lối tắt đã bật cờ RunAs ở
`C:\Users\Thang Tuong\Downloads\DEPLOY LTT (Run as admin).lnk` — bấm đúp rồi bấm
**Yes** ở UAC. Dán lệnh vào một cửa sổ PowerShell thường sẽ chết ở dòng kiểm quyền
của `2-cai-dat.ps1` (dòng 39) — nhưng chết **an toàn**, trước khi dừng dịch vụ nào.

⚠️ `2-cai-dat.ps1` chép **toàn bộ cây làm việc** và chạy `alembic upgrade head`.
Máy này thường có nhiều phiên Claude làm song song — kiểm `git status` và
`alembic/versions/` trước mỗi lần deploy.
