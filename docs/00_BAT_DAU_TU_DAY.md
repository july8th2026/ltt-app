# Bắt đầu từ đây

Nền tảng SaaS đa người dùng bán công cụ AI theo credit. Mỗi công cụ là một
**app** cắm vào nền tảng, ở một đường dẫn dưới `app.lttstudios.com`.

Thư mục này vừa là **mã nguồn** vừa là **bộ cài**.

---

## Mở phiên ở đâu

Đừng đọc theo một danh sách ở tệp này. Thứ tự đọc khi mở phiên nằm ở **`CLAUDE.md`**
(rồi `docs/00_LTT_OPERATING_CONTRACT.md` §1) — một nguồn duy nhất.

**Cái gì đang sống trên production** thì hỏi máy chủ, đừng đọc bảng chép tay:

```powershell
python tools\api_prod_canary.py trang-thai
```

*(Tệp này từng có bảng "Trạng thái thật" ghi tay ngày 02/08/2026; nó đã cũ và bị
gỡ 16/09/2026 — lịch sử nằm trong git.)* Đã chốt gì: `QUYET_DINH_NEN_TANG.md`.
Đang làm tới đâu: `KE_HOACH_TRIEN_KHAI.md` và `NHAT_KY.md`.

### Tra theo việc

| Việc | Tệp |
|---|---|
| Dựng tool mới — module nguồn ở BOT GEMINI | `KHAO_SAT_BOT_GEMINI.md` |
| Đưa code lên máy chủ, cập nhật, rollback | `01_COPY_LEN_SERVER.md` |
| Câu lệnh mẫu để giao việc cho Claude | `02_LENH_CHO_CLAUDE.md` |
| Thêm một app | `03_THEM_APP_MOI.md` |
| Dựng Tunnel, xử lý sự cố mạng | `04_CLOUDFLARE_TUNNEL.md` |
| AI Agent LTT (app `apps/agent/`) | `AGENT_LTT/00_AGENT_BAT_DAU.md` |
| Di trú module BOT GEMINI → app | `CONG_THUC_DI_TRU_APP.md` + `KE_HOACH_DI_TRU_MODULE.md` |
| Audit toàn diện app | `quy_tac_audit.md` |
| Thiết kế lại UI từ ảnh sau audit | `QUY_TRINH_THIET_KE_LAI_GIAO_DIEN_APP.md` |
| Tài liệu đã ngừng dùng — **đừng làm theo**, chỉ tra lịch sử | `_luutru/` |

### Mô hình vận hành (Q30 / H6)

1 host `app.lttstudios.com`, **path-based**: mỗi app ở `/<slug>`. Trang chủ `/`
là **catalog công khai** — khách chưa đăng nhập xem được các tool (manifest
`public=True`), bấm vào thì bị đưa về `/login?next=/<slug>` rồi quay lại đúng
chỗ. **1 tài khoản dùng cho mọi app** (SSO tự nhiên: cùng host, 1 cookie phiên).
App `public=False` ẩn khỏi catalog khách, chỉ vào qua sidebar sau khi đăng nhập
+ phân quyền.

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
├── tests/               bộ test (chạy theo hợp đồng §4)
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
python -m uvicorn server.run:app --host 127.0.0.1 --port 8100
```

Mở `http://127.0.0.1:8100` — chưa đăng nhập sẽ thấy **catalog công khai** (chỉ
app `public=True`). Đăng nhập rồi mở một app bất kỳ và nộp một job. Ra kết quả
kèm số credit nghĩa là hợp đồng app đang hoạt động đúng.

### Node `piece.*` (connector) — một bước nữa

```powershell
cd d:\LTTSTUDIOSAPP\connector_runner
npm ci
```

`connector_runner/node_modules` **không được git theo dõi**, nên một cây mới
clone sẽ không có piece nào. Thiếu nó thì runner ném
`Cannot find module '@activepieces/piece-…'`, và ba phép kiểm chạy runner thật
trong `tests/test_3505_wf_flow_d_poll_pg.py` (`test_THAT_*`) sẽ **đỏ**.

⛔ **Đừng cho ba phép kiểm đó `skip`.** Node/npm là phụ thuộc phát triển bình
thường, luôn cài được — khác hẳn các điều kiện `check_bo_qua.py` chấp nhận bỏ
qua (không có PostgreSQL, không phải Windows). *Một test bị bỏ qua là một test
không canh gì cả.*

⭐ `npm ci` chứ không `npm install`: `package-lock.json` đã commit, và lệch
phiên bản piece làm `connector.py` ném `phien_ban_lech`. Trên máy chủ bước này
do `setup/2-cai-dat.ps1` chạy, cài vào `$Root/connector_runner` — ⛔ không phải
trong `app/`, vì robocopy của trình cài loại `node_modules` theo **tên** ở mọi
cấp và sẽ xoá mất.

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
