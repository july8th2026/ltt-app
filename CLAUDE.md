# Hướng dẫn cho Claude

Đọc file này trước khi làm bất cứ việc gì trong thư mục này.

## Đây là gì

Nền tảng SaaS đa người dùng bán công cụ AI theo credit, chạy trên Windows.
Mỗi công cụ là một **app** ở một đường dẫn dưới `app.lttstudios.com`. Vào
Internet qua **Cloudflare Tunnel** (không mở cổng, không cần IP tĩnh).

**Nguồn chân lý là `docs/QUYET_DINH_NEN_TANG.md`** — đọc nó trước, rồi
`docs/KE_HOACH_TRIEN_KHAI.md` và `docs/NHAT_KY.md`. Quy tắc làm việc đầy đủ
(kể cả quy tắc cập nhật memory và giao thức đổi quyết định) ở `AGENTS.md`.

⚠️ **`D:\BOT GEMINI` là kho tham chiếu CHỈ ĐỌC.** Nó đang phục vụ người dùng
thật trên cổng 8000. Không sửa, không tạo, không xoá gì bên đó. Nền tảng này
dùng cổng **8100**.

Thư mục này vừa là **mã nguồn** vừa là **bộ cài**. Người dùng chép nguyên nó
sang máy chủ, rồi mở Claude Code **ngay trên máy đó**.

## Kiểm tra đầu tiên: đang ở máy nào?

```powershell
Test-Path C:\LTTPlatform
```

- **Có** → đây là máy chủ, đã cài. Làm việc bình thường, cẩn thận vì đang chạy thật.
- **Không** → hoặc là máy phát triển, hoặc là máy chủ chưa cài. Hỏi người dùng.

## Cài lần đầu trên máy chủ

Chạy đúng thứ tự. **Đừng bỏ qua bước 1.**

```powershell
powershell -ExecutionPolicy Bypass -File .\setup\1-kiem-tra-may.ps1   # chỉ đọc
powershell -ExecutionPolicy Bypass -File .\setup\2-cai-dat.ps1        # cần Administrator
powershell -ExecutionPolicy Bypass -File .\setup\3-cloudflare.ps1     # DỪNG chờ người dùng
powershell -ExecutionPolicy Bypass -File .\setup\4-nghiem-thu.ps1     # chỉ đọc
```

**Bước 2 in mật khẩu admin đúng MỘT LẦN.** Nhắc người dùng lưu lại ngay. Mật
khẩu không lưu ở đâu cả, chỉ lưu dạng hash.

**Bước 3 sẽ dừng ở phần đăng nhập Cloudflare.** `cloudflared tunnel login` in
ra một đường link rồi **đợi**. Đưa link đó cho người dùng, họ mở trên trình
duyệt máy nào cũng được, đăng nhập và chọn tên miền `lttstudios.com`. Xong thì
script tự chạy tiếp. Đừng ngắt lệnh vì tưởng nó treo.

Giữa bước 2 và 3, người dùng cần sửa `C:\LTTPlatform\data\config.json`
(Sheet ID, tên cột, thông tin app).

## Bố cục trên máy chủ sau khi cài

```
C:\LTTPlatform\
├── app\            MÃ NGUỒN — bị xoá và thay TOÀN BỘ mỗi lần cập nhật
├── app.previous\   bản trước, dùng để rollback
├── data\           dữ liệu vận hành — cập nhật KHÔNG chạm tới
├── secrets\        app.env: khoá phiên, khoá mã hoá token, hash mật khẩu
├── venv\           Python + thư viện
├── cloudflare\     config.yml + credentials tunnel
├── logs\
└── tools\          nssm.exe, cloudflared.exe
```

**Đừng bao giờ sửa file trực tiếp trong `app\`.** Lần cập nhật sau là mất
trắng, mất âm thầm, không báo lỗi. Sửa trong thư mục nguồn rồi chạy lại
`setup\2-cai-dat.ps1`.

## Quy tắc bắt buộc

**1. Ghi file cấu hình phải KHÔNG BOM.**
```powershell
[IO.File]::WriteAllText($path, $text, (New-Object Text.UTF8Encoding($false)))
```
Đừng dùng `Out-File -Encoding utf8` hay `Set-Content -Encoding utf8` —
PowerShell 5.1 chèn BOM, `json.load()` vỡ, và `/health/ready` trả 503 trong
khi dịch vụ vẫn chạy bình thường. Lỗi này **đã thực sự làm sập production** ở
dự án này. Có test chốt (`tests/test_61_setup_scripts.py`).

**2. File `.ps1` phải thuần ASCII.** PowerShell 5.1 đọc `.ps1` không BOM theo
bảng mã ANSI; một dấu tiếng Việt làm hỏng cả câu lệnh và báo lỗi ở dòng khác.

**3. Đừng viết Python inline qua PowerShell.** PowerShell nuốt dấu ngoặc kép
khi truyền cho `.exe`. Ghi ra file `.py` rồi chạy.

**4. Chạy test trước khi báo xong.** Một lệnh, chạy hết:
```powershell
python tools\gate.py            # pytest + 3 bộ test frontend + 2 scanner
python tools\gate.py --quick    # bỏ full pytest, dùng cho vòng lặp ngắn
```
Đừng chỉ chạy `python -m pytest -q` rồi báo xong: nó **không** chạy 77 test
frontend ở `frontend/*`, nên "full regression xanh" sẽ là một câu nói sai.

**5. Kiểm tra thật bằng trình duyệt sau mỗi thay đổi giao diện.** Test xanh
không chứng minh trang hiển thị đúng. Việc này đã hai lần bắt được lỗi mà test
không thấy.

**5b. Kiểm trên URL CÔNG KHAI thật (`https://app.lttstudios.com`), KHÔNG chỉ
loopback `127.0.0.1:8100`.** Loopback **bỏ qua Cloudflare** (cache, CSP biên, minify)
nên trang có thể đẹp ở loopback mà VỠ với người dùng thật. Đã dính: sau khi sửa
`ltt.css`, CF phục vụ bản CSS **cũ** (TTL 4h) → chip hiện thành radio thô, dù
origin đã đúng. Quy trình: loopback để soi nhanh → **URL công khai để chốt**.

**6. Đổi static (CSS/JS) PHẢI cache-bust.** Static đi qua Cloudflare có TTL; đổi
file mà URL không đổi thì người dùng nhận bản cũ tới khi hết TTL. Link `ltt.css`
đính `?v={{ asset_ver }}` (hash nội dung, `server/templating.py:ASSET_VER`) — đổi
CSS = đổi hash = đổi URL = tải mới ngay. Thêm asset tĩnh MỚI hay dùng ở nơi build
HTML bằng chuỗi (vd `server/admin.py`) thì cũng phải đính version. Trang HTML đã
`Cache-Control: no-store` (CF không cache) nên link version tới người dùng ngay
sau deploy.

## Thêm app mới

Thêm **một thư mục** vào `apps/`. **Không sửa** `platform_core/` hay `server/`.

Nếu thấy buộc phải sửa nền tảng thì **dừng lại và nói rõ vì sao** — đó là dấu
hiệu hợp đồng app còn thiếu, phải bổ sung vào hợp đồng chứ không đi vòng.

Xem `docs/03_THEM_APP_MOI.md`. Copy `apps/demo/` làm khuôn.

## Giới hạn Cloudflare quyết định cách viết app

| Giới hạn | Free/Pro | Hệ quả |
|---|---|---|
| Upload mỗi request | **100 MB** | Lớn hơn bị HTTP 413 trước khi tới máy chủ |
| Chờ phản hồi | **100 giây** | Lâu hơn bị 524 dù bot vẫn chạy tốt |
| Serve video lớn ngoài Cloudflare | hạn chế ToS | Phải chuyển sang R2 |

**Việc dài hơn vài giây bắt buộc đi qua hàng đợi job**, không được làm đồng bộ
trong một request. `apps/demo` chạy thẳng trong request chỉ vì nó mất vài
mili-giây — **đừng lấy đó làm mẫu cho app thật**.

Khi chạm trần: thêm backend R2 vào `platform_core/storage.py`, **không sửa app
nào**.

## Việc còn dở

| Hạng mục | Trạng thái |
|---|---|
| Vỏ nền tảng + hợp đồng app | ✅ xong, có test |
| Mã nguồn trong git | ✅ từ 2026-07-31 |
| PostgreSQL + nhiều người dùng (đăng ký, xác thực email, phân quyền) | ✅ xong (H1) |
| Hàng đợi job + worker tiến trình riêng | ✅ xong (H2) |
| Sổ credit (giữ chỗ → quyết toán → hoàn) | ✅ xong (H3) |
| Trang admin (sqladmin) + tài khoản admin trong CSDL | ✅ xong (H3-admin, Q29) |
| Cloudflare Tunnel LIVE + Turnstile + Resend | ✅ xong (H0.1) |
| Cốt lõi vận hành: catalog công khai + SSO + launcher | ✅ xong (H6/H6.6) |
| Tool thật đầu tiên — thumbnail (Gemini, tính credit) | ✅ xong (H5) |
| App socialbot (FB+TikTok) | ⏸️ đóng băng — không phát triển thêm |
| App demo | ✅ dùng để nghiệm thu, tốn 0 đồng |
| **Củng cố MVP (Hardening)** — Wave 0+1+2 | ✅ xong 2026-07-31 (H7) |
| Bộ máy APIKEYS (provider + 4 category, mã hoá, allocator) — Pha 1 | ✅ xong 2026-07-31 (H8) |
| APIKEYS Pha 2: telemetry rpm/tpm/token + cascade đa-provider + làm mới model | ✅ xong 2026-08-01 (H8) |
| Giao diện: hệ thống thiết kế + header/avatar + catalog | ✅ xong 2026-07-31 (UX Pha 1+2) |
| Thanh toán / nạp credit (PayOS agnostic, gói bonus %, webhook idempotent) | ✅ xong 2026-08-01 (H9) |
| Lưu file lớn qua R2 + `Storage.url_for()` (presigned, serve thẳng CDN) | ✅ xong 2026-08-01 (H10) |
| Di trú app từ BOT GEMINI: thumbnail(parity)+taoanh+kichban+taovideo(video async) | ✅ đang (A1+A2 P1) |

**Admin hiện tại là tài khoản trong CSDL** (`tools\create_admin.py`), đăng nhập
bằng email; đường admin-từ-biến-môi-trường đã vô hiệu ở production (Q29).

**H7 (Củng cố MVP) — Wave 0+1+2 ĐÃ XONG 2026-07-31** theo audit
`docs/AUDIT_MVP_2026-07-31.md`: đã bịt các lỗ P0 (double-spend, dedupe, IP thật
sau Tunnel, restore DB, băm token phiên, migration trong update) và P1/P2
(billing thumbnail theo ảnh, handler 500, CSRF admin/logout, khoá theo tài khoản,
ACL backup, validate hợp đồng sớm, log rotation, smoke test). Việc **cố ý hoãn**
sang H9/H10 ghi trong file audit + KE_HOACH (url_for/R2, FK constraints).
Cửa mở khách trả tiền giờ phụ thuộc **H9 (Thanh toán)**.

## Không bao giờ commit hay copy đi

```
data/config.json      data/*.enc      secrets/
cloudflare/config.yml cloudflare/*.json
```

## Tài liệu

| File | Nội dung |
|---|---|
| `docs/00_BAT_DAU_TU_DAY.md` | bố cục, nguyên tắc |
| `docs/01_COPY_LEN_SERVER.md` | chuyển sang máy chủ + cập nhật |
| `docs/02_LENH_CHO_CLAUDE.md` | câu lệnh mẫu người dùng đưa cho bạn |
| `docs/03_THEM_APP_MOI.md` | thêm app |
| `docs/04_CLOUDFLARE_TUNNEL.md` | Tunnel chi tiết + xử lý sự cố |
| `docs/_luutru/PROJECT_MEMORY.md` | nhật ký — **cập nhật cuối mỗi phiên** |
| `AGENTS.md` | quy ước kỹ thuật chi tiết |
