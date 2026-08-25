# Bắt đầu từ đây

Nền tảng SaaS đa người dùng bán công cụ AI theo credit. Mỗi công cụ là một
**app** cắm vào nền tảng, ở một đường dẫn dưới `app.lttstudios.com`.

Thư mục này vừa là **mã nguồn** vừa là **bộ cài**.

---

## Đọc theo thứ tự này

| # | File | Khi nào cần |
|---|---|---|
| 1 | **`QUYET_DINH_NEN_TANG.md`** | **Đọc trước tiên.** Nguồn chân lý: dự án là gì, 12 quyết định đã chốt, ràng buộc bất biến. Tài liệu nào mâu thuẫn với nó thì nó đúng. |
| 2 | `KE_HOACH_TRIEN_KHAI.md` | Đang làm tới đâu, việc kế tiếp là gì |
| 3 | `NHAT_KY.md` | Phiên gần nhất đã làm gì, còn vướng gì |
| 4 | `KHAO_SAT_BOT_GEMINI.md` | Khi cần dựng một tool mới — tra module nguồn ở đâu, cần gì |
| 5 | `01_COPY_LEN_SERVER.md` | Đưa code lên máy chủ, cập nhật, rollback |
| 6 | `02_LENH_CHO_CLAUDE.md` | Câu lệnh mẫu để giao việc cho Claude |
| 7 | `03_THEM_APP_MOI.md` | Thêm một app |
| 8 | `04_CLOUDFLARE_TUNNEL.md` | Dựng Tunnel, xử lý sự cố mạng |
| 9 | **`AGENT_LTT/00_AGENT_BAT_DAU.md`** | **AI Agent LTT** — mở phiên làm việc về agent thì đọc file đó trước, nó chỉ đường tiếp. Kèm giao thức **đo trạng thái code thật** trước khi tin tài liệu. |
| 10 | `CONG_THUC_DI_TRU_APP.md` + `KE_HOACH_DI_TRU_MODULE.md` | Di trú module BOT GEMINI → app: công thức 8 bước + backlog theo đợt |
| 11 | **`quy_tac_audit.md`** | Audit toàn diện app: điểm Q/M/E, gate phát hành, control, benchmark thế giới và roadmap |
| 12 | `QUY_TRINH_THIET_KE_LAI_GIAO_DIEN_APP.md` | Thiết kế lại UI từ ảnh sau khi audit/logic đã khóa |
| — | `_luutru/` | Tài liệu đã ngừng dùng. **Đừng làm theo.** Chỉ để tra lý do lịch sử. |

---

## Trạng thái thật — cập nhật 2026-08-02

Bảng này phải đúng. Nếu bạn thấy nó sai, sửa ngay chứ đừng để đó — một bảng
trạng thái sai còn tệ hơn không có bảng nào.

### Đang chạy

| Hạng mục | Trạng thái |
|---|---|
| Vỏ nền tảng nhiều app + hợp đồng app | ✅ xong, có test chốt |
| PostgreSQL + di trú schema (Alembic) | ✅ xong (H1) |
| Nhiều người dùng: đăng ký, xác thực email (Resend), phân quyền app | ✅ xong (H1) |
| Hàng đợi job + worker tiến trình riêng | ✅ xong (H2) |
| Sổ credit (giữ chỗ → quyết toán → hoàn) | ✅ xong (H3) |
| Trang admin (sqladmin) | ✅ xong (H3-admin) |
| Cloudflare Tunnel LIVE `app.lttstudios.com` + Turnstile | ✅ xong (H0.1) |
| **Cốt lõi vận hành: catalog công khai + SSO + login return-to** | ✅ xong (H6) |
| **LTT Agent AI + React Canvas + 7 tool ảnh/text/video/GPU** | ✅ xong, production public (H12 P0–P13) |
| Tool thật đầu tiên — `thumbnail` (Gemini Image, tính credit) | ✅ xong (H5) |
| App socialbot (Facebook + TikTok) | 🗑️ **ĐÃ GỠ HẲN 2026-08-25** (Q108 thay Q10) — cùng `core/`, `utils/`, `server/services/`, 43 route |
| App demo (nghiệm thu hạ tầng) | 🗑️ **ĐÃ GỠ 2026-08-25** — bốn bộ test hạ tầng nay dùng app THỬ tổng hợp trong `tests/conftest.py`, không dựa vào một mặt hàng nữa |
| Bộ cài 4 script + cập nhật + rollback + lịch backup | ✅ xong |
| Kho mã nguồn trong git | ✅ từ 2026-07-31 |
| Bộ test | ✅ 1.849 pass, 8 skip, 23 subtest |

### Mô hình vận hành (Q30 / H6)

1 host `app.lttstudios.com`, **path-based**: mỗi app ở `/<slug>`. Trang chủ `/`
là **catalog công khai** — khách chưa đăng nhập xem được các tool (manifest
`public=True`), bấm vào thì bị đưa về `/login?next=/<slug>` rồi quay lại đúng
chỗ. **1 tài khoản dùng cho mọi app** (SSO tự nhiên: cùng host, 1 cookie phiên).
App `public=False` (qualitylab) ẩn khỏi catalog khách, chỉ vào qua sidebar
sau khi đăng nhập + phân quyền.

### Chưa có — việc phía trước

| Hạng mục | Trạng thái |
|---|---|
| Thanh toán / nạp credit (cổng chưa chốt) | ❌ chưa (H9) |
| Lưu file lớn qua R2 (khi chạm trần Cloudflare) | ❌ chưa (H10) |
| Thêm tool mới | ⏭️ mở (H11) |

Chi tiết từng bước: `KE_HOACH_TRIEN_KHAI.md`.

---

## Bố cục thư mục

```
LTTSTUDIOSAPP/
├── platform_core/       NỀN TẢNG — không biết app nào tồn tại
│   ├── registry.py      ★ hợp đồng app. File quan trọng nhất của dự án.
│   └── storage.py       lớp bọc lưu file (đổi sang R2 chỉ sửa ở đây)
│
├── apps/                MỖI APP MỘT THƯ MỤC
│   ├── thumbnail/       Tạo thumbnail YouTube (Gemini Image) — tool thật
│
├── server/              vỏ web: đăng nhập, trang chủ, route dùng chung
├── tools/               doctor.py, gate.py, build_release.py, quét bí mật
├── tests/               ~1.400 test
├── deploy/windows/      install / update / rollback / backup
├── setup/               ★ BỘ CÀI — 4 script chạy theo thứ tự
├── cloudflare/          mẫu cấu hình Tunnel
├── data/                dữ liệu khi chạy — KHÔNG đưa lên git
└── secrets/             khoá, token — KHÔNG đưa lên git, KHÔNG copy đi đâu
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

## Chạy thử ở máy phát triển

```powershell
cd d:\LTTSTUDIOSAPP
python -m pip install -r requirements.txt -r requirements-server.txt
python -m pytest -q                    # phải xanh hết trước khi làm gì tiếp
python -m uvicorn server.run:app --host 127.0.0.1 --port 8100
```

Mở `http://127.0.0.1:8100` — chưa đăng nhập sẽ thấy **catalog công khai** (chỉ
app `public=True`). Đăng nhập rồi mở một app bất kỳ và nộp một job. Ra kết quả
kèm số credit nghĩa là hợp đồng app đang hoạt động đúng.

> **Cổng 8100 chứ không phải 8000.** Máy này còn chạy một hệ thống nội bộ khác
> đã chiếm 8000 từ trước (`D:\BOT GEMINI`). Dùng 8000 sẽ giành cổng với dịch vụ
> đang phục vụ người dùng thật.

---

## Ba giới hạn quyết định cách viết app

| Giới hạn | Free/Pro | Hệ quả |
|---|---|---|
| Upload mỗi request | **100 MB** | Lớn hơn bị HTTP 413 trước khi tới máy chủ |
| Chờ phản hồi | **100 giây** | Lâu hơn bị 524 dù job vẫn chạy tốt |
| Serve file lớn ngoài Cloudflare | hạn chế ToS | Phải chuyển sang R2 |

**Việc dài hơn vài giây bắt buộc đi qua hàng đợi job.** *(App cũ `apps/demo`, đã gỡ 2026-08-25, chạy thẳng
trong request chỉ vì nó mất vài mili-giây — **đừng lấy đó làm mẫu cho app thật**.

---

## Hai mốc thời gian cần nhớ

| Mốc | Hạn | Ảnh hưởng |
|---|---|---|
| Giấy phép Windows Server (bản Evaluation) trên máy chủ | ~giữa 12/2026 | Hết hạn máy tự tắt mỗi giờ |
| Windows 10 hết bản vá bảo mật (ESU) | **13/10/2026** | Máy chạy không còn được vá |
