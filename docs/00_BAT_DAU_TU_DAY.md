# Bắt đầu từ đây

Thư mục này vừa là **mã nguồn** vừa là **bộ cài**. Chép nguyên nó sang máy chủ
rồi chạy `setup/` — không cần chuẩn bị gì thêm.

Mọi app nằm trong đây, mỗi app một đường dẫn dưới `app.lttstudios.com`.

> **Quan trọng:** thư mục cũ `BOT UP FB + TikTok\BOT UP Facebook\` giờ chỉ là
> bản chụp dự phòng. **Từ giờ chỉ làm việc trong `LTTSTUDIOSAPP`.** Sửa ở hai
> nơi là chắc chắn sẽ lệch nhau, và lỗi đó rất khó phát hiện. Khi bạn thấy yên
> tâm thì xoá hẳn thư mục cũ đi.

## Chép sang máy chủ rồi cài — 4 lệnh

Chép **nguyên thư mục** sang máy chủ (USB, ổ mạng, Remote Desktop — cách nào
cũng được). Thư mục này **không chứa bí mật nào**, bí mật sẽ được sinh trên
máy chủ ở bước 2.

Mở PowerShell bằng **Run as administrator**, vào thư mục vừa chép:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup\1-kiem-tra-may.ps1   # chỉ đọc
powershell -ExecutionPolicy Bypass -File .\setup\2-cai-dat.ps1        # cài + sinh bí mật
powershell -ExecutionPolicy Bypass -File .\setup\3-cloudflare.ps1     # DỪNG chờ bạn đăng nhập
powershell -ExecutionPolicy Bypass -File .\setup\4-nghiem-thu.ps1     # chỉ đọc
```

Hoặc mở Claude Code ngay tại thư mục đó và bảo: *"Đọc CLAUDE.md rồi cài đặt hệ
thống này lên máy chủ."*

⚠️ **Bước 2 in mật khẩu admin đúng MỘT LẦN** — lưu lại ngay, không lưu ở đâu khác.

⚠️ **Bước 3 sẽ dừng lại** và in một đường link. Mở link trên trình duyệt máy nào
cũng được, đăng nhập Cloudflare, chọn `lttstudios.com`. Script tự chạy tiếp —
đừng ngắt vì tưởng nó treo.

Giữa bước 2 và 3: điền `C:\LTTPlatform\data\config.json` (Sheet ID, tên cột,
thông tin app) và chép file Service Account của Google vào
`C:\LTTPlatform\secrets\`.

---

## Đọc theo thứ tự

| File | Nội dung | Khi nào cần |
|---|---|---|
| `00_BAT_DAU_TU_DAY.md` | file này | đọc trước |
| `01_COPY_LEN_SERVER.md` | đưa code lên VPS | mỗi lần cập nhật |
| `02_LENH_CHO_CLAUDE.md` | các câu lệnh đưa cho Claude | khi cần làm việc gì đó |
| `03_THEM_APP_MOI.md` | thêm app mới | mỗi lần có app mới |
| `04_CLOUDFLARE_TUNNEL.md` | dựng Tunnel + xử lý sự cố | một lần, lúc đầu |
| `../CLAUDE.md` | ngữ cảnh cho Claude khi chạy trên máy chủ | Claude tự đọc |

---

## Bố cục thư mục

```
LTTSTUDIOSAPP/
├── platform_core/           NỀN TẢNG — dùng chung, không biết app nào tồn tại
│   ├── registry.py          ★ hợp đồng app. File quan trọng nhất.
│   └── storage.py           lớp bọc lưu file (đổi sang R2 chỉ sửa ở đây)
│
├── apps/                    MỖI APP MỘT THƯ MỤC
│   ├── socialbot/           app FB + TikTok đang chạy thật
│   └── demo/                app mẫu — dùng để nghiệm thu hạ tầng, tốn 0 đồng
│
├── server/                  vỏ web: đăng nhập, trang chủ, route dùng chung
├── core/                    nghiệp vụ bot (15.000 dòng, giữ nguyên đường import)
├── utils/                   sheet_client, logger
├── tools/                   doctor.py, build_release.py, quét bí mật
├── tests/                   1.348 test
├── deploy/windows/          install / update / rollback / backup
├── setup/                   ★ BỘ CÀI — 4 script chạy theo thứ tự
├── cloudflare/              mẫu cấu hình Tunnel
├── data/                    dữ liệu khi chạy — KHÔNG đưa lên git
└── secrets/                 khoá, token — KHÔNG đưa lên git, KHÔNG copy đi đâu
```

### Vì sao tên là `platform_core` chứ không phải `platform`

`platform` là tên module có sẵn của Python. Đặt một package trùng tên ở thư
mục gốc sẽ **che mất module chuẩn**, và lỗi hiện ra ở những thư viện chẳng
liên quan gì — rất khó truy. Đừng đổi lại.

---

## Nguyên tắc mở rộng — đọc kỹ phần này

Nền tảng **không được biết app nào tồn tại**. Nó quét `apps/*/manifest.py` rồi
tự dựng trang chủ, sidebar, gắn route và tra giá credit.

Nhờ vậy **thêm một app = thêm một thư mục**. Không sửa `server/`, không sửa
`base.html`, không sửa trang chủ.

Có test chốt điều này (`tests/test_60_app_registry.py`):

- `test_platform_never_imports_an_app` — nền tảng import app là fail
- `test_no_app_slug_is_hardcoded_in_the_platform` — viết cứng tên app là fail
- `test_route_prefixes_are_unique` — hai app cùng prefix là fail
- `test_unknown_job_type_is_refused_not_free` — job không tra được giá bị từ chối

Cái cuối cùng đáng chú ý: job không tính được giá thì **bị từ chối chạy**, chứ
không chạy miễn phí. Với API tính theo giây video thì "miễn phí ngoài ý muốn"
là mất tiền thật.

---

## Chạy thử ở máy bạn

```powershell
cd "d:\CODE AI\LTTSTUDIOSAPP"
python -m pip install -r requirements.txt -r requirements-server.txt
python -m pytest -q                    # phải xanh hết trước khi làm gì tiếp
python -m uvicorn server.run:app --host 127.0.0.1 --port 8000
```

Mở `http://127.0.0.1:8000` — trang chủ phải liệt kê **2 app**: Đăng bài
Facebook + TikTok, và Demo.

Vào `/demo`, gõ gì đó rồi bấm chạy. Nếu ra kết quả kèm số credit thì hợp đồng
app đang hoạt động đúng.

---

## Trạng thái hiện tại

| Hạng mục | Trạng thái |
|---|---|
| Vỏ nền tảng nhiều app | ✅ xong, có test |
| Hợp đồng app (manifest) | ✅ xong, 19 test |
| App socialbot (FB+TikTok) | ✅ đang chạy production |
| App demo | ✅ xong, dùng để nghiệm thu |
| Trang chủ + sidebar sinh động | ✅ xong |
| Lớp storage tách rời | ✅ xong (đang dùng đĩa cục bộ) |
| Bộ cài tự động (4 script) | ✅ xong, 59 test |
| Cloudflare Tunnel | ⏳ chạy `setup\3-cloudflare.ps1` trên máy chủ |
| Hàng đợi job dùng chung | ❌ chưa — giai đoạn sau |
| Nhiều người dùng + credit thật | ❌ chưa — giai đoạn sau |

Hai mục cuối là phần lớn nhất còn lại. Chúng chưa chặn việc chạy nội bộ với
nhân viên, nhưng **bắt buộc phải có trước khi mở cho khách ngoài**.

---

## Hai mốc thời gian cần nhớ

| Mốc | Hạn | Ảnh hưởng |
|---|---|---|
| Giấy phép Windows Server 2016 trên VPS (bản Evaluation) | **~139 ngày** kể từ 30/07/2026 | Hết hạn máy tự tắt mỗi giờ |
| Windows 10 hết bản vá bảo mật (ESU) | **13/10/2026** | Máy chạy bot không còn được vá |

Cả hai đều rơi vào lúc bạn sẽ đang xây dở. Nên quyết sớm.
