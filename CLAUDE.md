# Hướng dẫn cho Claude

Đọc file này trước khi làm bất cứ việc gì trong thư mục này.

## Đây là gì

Nền tảng SaaS đa người dùng bán công cụ AI theo credit, chạy trên Windows.
Mỗi công cụ là một **app** ở một đường dẫn dưới `app.lttstudios.com`. Vào
Internet qua **Cloudflare Tunnel** (không mở cổng, không cần IP tĩnh).

**Nguồn chân lý là `docs/QUYET_DINH_NEN_TANG.md`** — đọc nó trước, rồi
`docs/KE_HOACH_TRIEN_KHAI.md` và `docs/NHAT_KY.md`. Định vị code thì đọc
**chính mã nguồn**: `grep`/`Glob` trên `apps/`, `platform_core/`, `server/`.

⛔ **`ho_so_he_thong.txt` đã gỡ 2026-09-04.** Nó là một ảnh chụp toàn cây,
nên nó cũ đi sau **mỗi** lần bất kỳ ai sửa bất kỳ tệp nào — và một bản đồ
cũ nguy hiểm hơn không có bản đồ, vì nó trả lời tự tin. Đọc mã.
Quy tắc làm việc đầy đủ (kể cả quy tắc cập nhật memory và giao thức đổi quyết
định) ở `AGENTS.md`.

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

**4. Chạy test — ĐỪNG gọi `pytest` trực tiếp, và đừng dùng gate để dò lỗi.**

```powershell
python tools\gate.py --vong-lap     # sau MOI lan sua              (~15 giay)
python tools\test_nhanh.py          # muon chay ca bo test         (~4 phut)
python tools\gate.py                # TRUOC KHI BAO XONG           (~5 phut)
```

🔑 **Gate là công cụ ra PHÁN QUYẾT, không phải công cụ CHẨN ĐOÁN.**

Ngày 27/08 gate đầy đủ được chạy **sáu lần** chỉ để dò lỗi, mỗi lần ~5 phút.
Bốn trong sáu lượt đỏ vì một thứ mà một bước con lẻ trả lời trong nửa giây:
baseline của phiên khác · một emoji trong stdout của một công cụ · hồ sơ hệ
thống stale · một phép kiểm lệch thứ tự. `--vong-lap` chạy **toàn bộ** nhóm
kiểm tĩnh (chính là thứ bắt bốn lỗi đó) trong ~15 giây.

⛔ Nhưng `--vong-lap` và `--quick` **không phải bằng chứng** — dòng `RESULT` của
chúng nói thẳng điều đó. Trước khi báo xong vẫn là `python tools\gate.py`.

⛔ **Đừng chạy `python -m pytest` cho toàn bộ kho.** Hai lý do, và lý do thứ hai
mới là lý do thật:

1. Nó **không** chạy 77 test frontend ở `frontend/*` ⇒ "full regression xanh" là
   một câu nói sai.
2. Nó chạy **một luồng, mất 25 phút**, trong khi `test_nhanh.py` cho **cùng tập
   pass/fail** trong 4 phút *(đo 26/08: 4096 passed / 26 skipped ở cả hai)*.

⭐ Trước 26/08 bộ test mất **2 giờ**, và điều đó đổi cách người ta làm việc:
`pytest` thôi là một vòng lặp và thành một sự kiện. Hệ quả đo được — H40 đóng mà
**chưa lượt `pytest` đầy đủ nào chạy xong**, và lượt đầy đủ đầu tiên sau đó tìm
ra **36 lỗi**, gồm một phép kiểm **chưa bao giờ xanh** trên máy này.

Chi tiết + luật cho test mới: `AGENTS.md` mục **4b**.

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

Xem `docs/03_THEM_APP_MOI.md` — khuôn đầy đủ nằm trong chính tài liệu đó.
⚠️ **Không còn app mẫu để copy**: `apps/demo/` đã gỡ 2026-08-25 (Q109). App thật
nhỏ gọn để tham khảo: `apps/anhnoibo/` (chỉ job) hoặc `apps/thumbnail/` (có route).

### Đặt file đúng chỗ ngay từ đầu

Đây là phần **hay bị làm sai nhất** khi phiên khác vào xây tiếp. Quy tắc đầy đủ
ở `AGENTS.md` mục 8; bản rút gọn:

```
apps/<slug>/
  manifest.py   bản khai — nền tảng CHỈ đọc file này
  routes.py     CHỈ lo HTTP (đọc request, quyền/CSRF, gọi service, dựng phản hồi)
  jobs.py       handler chạy trong worker
  services/     quy tắc nghiệp vụ khi app nhiều miền
  features.py   quy tắc nghiệp vụ khi app một miền
  tables.py     bảng CSDL riêng (kèm `table_prefix` trong manifest)
```

**`routes.py` không phải chỗ chứa nghiệp vụ.** Trần cứng: 900 dòng / 30 handler,
`tools/lint_app_contract.py` cảnh báo khi vượt. Hợp đồng trước đây không nói
logic nghiệp vụ nằm ở đâu, nên route thành chỗ để mọi thứ rơi vào — đã có file
route 1.799 dòng vì vậy.

**Việc dùng chung thì gọi `platform_core`, đừng chép lại:**
`image_input.validate_reference` (kiểm ảnh tải lên),
`frontend_bundle.bundle_assets` (đường dẫn bundle React).

**Đừng neo đường dẫn bằng `Path(__file__).parents[n]`** — đếm cấp thư mục sai
ngay khi file đổi chỗ, và hỏng lặng lẽ (trang vẫn trả 200, chỉ là vỏ trống).

## Giới hạn Cloudflare quyết định cách viết app

| Giới hạn | Free/Pro | Hệ quả |
|---|---|---|
| Upload mỗi request | **100 MB** | Lớn hơn bị HTTP 413 trước khi tới máy chủ |
| Chờ phản hồi | **100 giây** | Lâu hơn bị 524 dù bot vẫn chạy tốt |
| Serve video lớn ngoài Cloudflare | hạn chế ToS | Phải chuyển sang R2 |

**Việc dài hơn vài giây bắt buộc đi qua hàng đợi job**, không được làm đồng bộ
trong một request. *(App cũ `apps/demo` chạy thẳng trong request được chỉ vì nó
mất vài mili-giây; nó đã bị gỡ, và cách làm đó chưa bao giờ là mẫu cho app thật.)*

Khi chạm trần: thêm backend R2 vào `platform_core/storage.py`, **không sửa app
nào**.

## Hiện giờ cái gì đang sống — HỎI MÁY CHỦ, đừng đọc ở đây

```powershell
python tools\api_prod_canary.py trang-thai
```

Một lệnh, mười giây, không cần khoá production. Nó trả lời: app nào đang công
khai, tool nào đang mở ở `/api/v1`, dịch vụ có sống không.

🔴 **Vì sao mục này không còn là một bảng.** Trước 2026-09-02 chỗ này là một
bảng 280 dòng chép tay — **56% cả tệp**. Nó đã nói sai **năm lần**, và **cả năm
đều về phía nguy hiểm**: báo một thứ đang TẮT trong khi nó đang BẬT và **đang
thu tiền thật**. Bốn lần được sửa bằng cách viết lại bảng; lần thứ năm vẫn xảy
ra.

⭐ Cái sai không nằm ở người viết. Một bảng chép tay **không có cách nào tự biết
nó đã cũ**. Nên thứ đổi là *nơi câu trả lời đến từ*.

⛔ Nếu một tệp `.md` nào nói khác lệnh trên, **tệp đó sai**. Đừng sửa máy chủ
cho khớp tài liệu.

Toàn văn bảng cũ giữ nguyên ở `docs/_luutru/CLAUDE_lich_su_2026-09.md`.

### Luật của từng hệ con nằm ở đâu

Bảng này chỉ chứa **con trỏ**, không chứa giá trị — một giá trị chép lại là một
giá trị sẽ trôi.

| Hệ con | Luật (nguồn chân lý) | Vì sao thành ra thế |
|---|---|---|
| Sổ credit · thanh toán | `platform_core/credit.py`, `billing.py` | `docs/AUDIT_MVP_2026-07-31.md` |
| Hàng đợi job · worker · lease | `platform_core/job_runner.py`, `leases.py` | `docs/PUBLIC_API/` (H36) |
| Public API `/api/v1` | `platform_core/public_api/`, `server/api/inventory.py` (24 route đóng băng) | `docs/PUBLIC_API/APP_API_COVERAGE_FINAL.md` |
| Khoá API · provider | `platform_core/api_pool.py`, `providers.py` | `docs/KHAO_SAT_APIKEYS.md` |
| Model ảnh nội bộ (máy B) | `render_gateway/ngan_sach.py`, `apps/anhnoibo/gia.py` | `docs/ANH_NOI_BO/DECISIONS.md` |
| LLM nội bộ (máy B) | `apps/ltt_llm/ngan_sach.py` | `docs/VLM_NOI_BO/` |
| LTT VOICE | `apps/ltt_voice/tham_so_cong_khai.py` | `docs/LTT_VOICE/` |
| Bán VPS | `apps/vps/services/mang.py`, `apps/vps/bao_tri.py` | `docs/VPS/` |
| LTT Nexus | `nexus_agent/`, `platform_core/nexus/` | `docs/nexus/` |
| Lưu trữ · R2 | `platform_core/storage.py` | |
| Cây riêng · cổng chất lượng | `tools/cay_rieng.py`, `tools/gate.py`, `tools/thanh_phan.py` | `docs/DEVELOPMENT_WORKFLOW.md` |

⚠️ **Đừng gõ lại một con số nào từ các tệp trên vào đây.** Đó chính xác là cơ
chế đã hỏng năm lần. Ví dụ thật: trần ký tự của `ltt_voice` được tách thành
**hai** hằng số ngày 31/08 — bảng cũ vẫn mô tả **một**, và không ai phát hiện
cho tới khi có người đối chiếu từng giá trị với mã.

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
| `docs/PUBLIC_API/APP_API_COVERAGE_FINAL.md` | app/tool/model nào mở, nào đóng, **vì sao** |
| `docs/PUBLIC_API/API_PLATFORM_FULL_RELEASE_READINESS.md` | trạng thái Public API + điều kiện còn lại |
| `docs/_luutru/PROJECT_MEMORY.md` | nhật ký — **cập nhật cuối mỗi phiên** |
| `docs/BAY_TRONG_CONG_CHAT_LUONG.md` | sáu cái bẫy trong chính cổng chất lượng — đọc trước khi tin một dòng `RESULT: PASS` |
| `AGENTS.md` | quy ước kỹ thuật chi tiết |
