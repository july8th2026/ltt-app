# Hướng dẫn cho Claude

Đọc file này trước khi làm bất cứ việc gì trong thư mục này.

## Đây là gì

Nền tảng SaaS đa người dùng bán công cụ AI theo credit, chạy trên Windows.
Mỗi công cụ là một **app** ở một đường dẫn dưới `app.lttstudios.com`. Vào
Internet qua **Cloudflare Tunnel** (không mở cổng, không cần IP tĩnh).

**Nguồn chân lý là `docs/QUYET_DINH_NEN_TANG.md`** — đọc nó trước, rồi
`docs/KE_HOACH_TRIEN_KHAI.md`, `docs/NHAT_KY.md` và `ho_so_he_thong.txt` để
định vị code. Hồ sơ gồm bản đồ + snapshot source text sinh tự động, không cao
hơn quyết định/code/test.
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

**4. Chạy test — ba lệnh, và ĐỪNG gọi `pytest` trực tiếp.**
```powershell
python tools	est_nhanh.py         # vong lap lam viec — MAC DINH  (~4 phut)
python tools	est_nhanh.py --lf    # ngay sau khi sua mot loi      (giay)
python tools\gate.py               # TRUOC KHI BAO XONG            (~8 phut)
```

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
| App socialbot (FB+TikTok) | 🗑️ **ĐÃ GỠ HẲN 2026-08-25 (Q108, thay Q10)** — xoá `apps/socialbot/`, `core/` (15.046 dòng), `utils/`, `server/services/`, 7 module route (43 route = 62% bề mặt công khai cũ), 10 template, 44 tệp test (~1.017 test). Đo trước khi xoá: **0** job, **0** `app_access`, **0** `app_projects`, và **không có** `tokens.enc` — chưa khách nào từng kết nối. Mã còn trong lịch sử git. ⚠️ Đăng ký Meta App + TikTok app là tài sản **ngoài kho**, chủ sản phẩm quyết |
| App demo · kichban · mediatools | 🗑️ **ĐÃ GỠ HẲN 2026-08-25 (Q109)** — danh mục app **19 → 14**. `demo` được thay bằng **app THỬ tổng hợp** trong `tests/conftest.py::app_thu` (sống trong bộ nhớ một test, không thư mục, không route, không lên catalog). ⚠️ Cái giá đã đo và chủ sản phẩm đã chấp nhận: **4–7 trong 10 workflow Agent đang lưu mất node** — 4 tool `asset.*` của `mediatools` là node **đầu vào** của workflow |
| **Củng cố MVP (Hardening)** — Wave 0+1+2 | ✅ xong 2026-07-31 (H7) |
| Bộ máy APIKEYS (provider + 4 category, mã hoá, allocator) — Pha 1 | ✅ xong 2026-07-31 (H8) |
| APIKEYS Pha 2: telemetry rpm/tpm/token + cascade đa-provider + làm mới model | ✅ xong 2026-08-01 (H8) |
| Giao diện: hệ thống thiết kế + header/avatar + catalog | ✅ xong 2026-07-31 (UX Pha 1+2) |
| Thanh toán / nạp credit (PayOS agnostic, gói bonus %, webhook idempotent) | ✅ xong 2026-08-01 (H9) |
| Lưu file lớn qua R2 + `Storage.url_for()` (presigned, serve thẳng CDN) | ✅ xong 2026-08-01 (H10) |
| Di trú app từ BOT GEMINI: thumbnail(parity)+taoanh+kichban+taovideo(video async) | ✅ đang (A1+A2 P1) |
| **Rà soát hệ điều hành** — bố cục mã nguồn + tầng nghiệp vụ | ✅ 9/12 xong 2026-08-06 (H22) |
| Hồ sơ hệ thống tự sinh (`ho_so_he_thong.txt`) | ✅ xong 2026-08-12 (H34, Q91) |
| **Public API `/api/v1`** cho khách lập trình — 5 tool, cổng dev + admin, chế độ thử | ✅ xong 2026-08-15 (H35, Q92); **ĐÃ DEPLOY 2026-08-17**, tool chưa mở |
| **LTT Nexus** (điều khiển máy từ xa) — nền tảng + wiring + billing | ✅ LIVE; Windows + Android chạy thật, thu credit thật. Vòng sửa lỗi 2026-08-22 đóng hết mục A+B của `docs/nexus/N7_DANH_SACH_VIEC.md`. ⏸️ **Một đợt đã commit nhưng CHƯA DEPLOY — đọc `docs/nexus/N8_CHO_DEPLOY.md` trước khi chạy deploy.** Còn hạ tầng C1–C4, macOS, iOS |
| Củng cố phần thi hành của API — lease, đội hình worker, metrics, vòng đời file | ✅ code xong 2026-08-16 (H36); **còn nợ 4 việc chứng minh** — xem H36.9–12 |
| **Model tạo ảnh NỘI BỘ trên máy B (RTX 3090)** — provider `ltt_image`, không phải app | 🔨 giai đoạn A xong 2026-08-22 (H37, Q102); cổng render đã là dịch vụ trên B; bán ra `/api/v1` qua app `anhnoibo` + tool `image.ltt` — **chưa mở cho khách** (4 cổng còn khoá, D-034). 🔴 **So mù G6b 23/08: Gemini 24 – nhà 4 – hoà 2** (phần có ý nghĩa: **14 – 4**, vì chữ tiếng Việt **ngoài phạm vi** — D-048). Nhà thua vì **giải phẫu, hình học, chất chụp thật**. ⇒ **Đừng định vị nó là "đẹp hơn"; ảnh có chữ thì trả lời Gemini và đó là câu cuối.** ⛔ **Bỏ hẳn đối chứng ngoài** (D-046) — đo từ đây là **HiDream đấu HiDream, một lô một biến**. 🔒 **GIỮ 50 BƯỚC — G4 ĐÓNG 24/08 (D-054), câu cuối.** Lô B2c (seed thứ ba) nâng tổng lên **60 cặp**: 50 bước **33 – 18**, điểm 0,625, KTC [0,507; 0,744] **không chứa 0,5**. 36 bước đã thua **hai lô độc lập** ⇒ không nhận. ⚠️ Nhưng khác biệt **nhỏ hơn khác biệt giữa hai seed** (sàn nhiễu 91% > quyết đoán 85%) — đừng đọc thành "36 bước tệ rõ". Muốn mở lại thì phải là **phép kiểm tương đương**, không phải chạy lại phép cũ. 🔨 **Tiếp quản 24/08 (D-050, D-051):** chấm theo `docs/KHUON_BAN_MODEL_NHA.md` được **18/31**; đã sửa **lỗi tiền đang sống** — xin 4 ảnh, máy B trả 2, khách vẫn bị thu tiền 4 vì handler không báo `credit_cost` (cùng gốc với lỗi H38 đã sửa 23/08). Thêm `/live` + chốt GPU/CPU cho cổng render, giá về `apps/anhnoibo/gia.py` và công bố ở `/gia-api`. 🔓 **24/08 (D-052, D-053): giá hạ một phần ba** (5 → 3 credit/ảnh, tham chiếu 15 → 9), **bốn cổng MỞ trong mã**, **G5 đóng** (trần token 7.506 → 11.412, đo thật 20,1 GB · 239 s). **Máy chấm thay người** (D-052) — đổi lại mỗi phiếu quyết đoán phải viết lý do, `cham_mu.py` từ chối tính nếu thiếu. ⚠️ `render_gateway/deploy/deploy.ps1` có **hai lỗi khiến nó chưa từng deploy thành công lần nào** (đích sai một cấp + `Join-Path` giải ổ đĩa của máy A); đã sửa, nay 29/29 khớp hash. ✅ **G4 + G5 + G9 đều ĐÓNG 24/08.** G9: **100/100 lượt, 0 hỏng**, VRAM dao động 163 MB (0,9 %), nhiệt 69–74 °C, **không trôi gì** qua hơn ba giờ (D-056). ⏳ Còn **hai việc cần chủ sản phẩm**: bật cờ bằng `setup\cong_tac_tool_api.ps1` **rồi mới** deploy — sai thứ tự thì cờ không có tác dụng. ⛔ **D-057 (24/08): DỪNG kế hoạch dùng máy A sinh ảnh.** Không hạ độ chính xác model; `bf16` đỉnh 18.450 MB không vừa card 16.311 MB, và riêng Llama-3.1-8B trong bộ mã hoá đã lấp kín một card. Mở lại cần **phần cứng ≥ 24 GB**, không phải một cách xếp encoder khác. ⇒ Hệ quả: **trọng tài VRAM ở `docs/ANH_NOI_BO/CHIA_GPU_HAI_MODEL.md` nay BẮT BUỘC** — hai model vẫn dùng chung 3090 (18.450 + 19.237 = 37.687 MB / 24.576). **KẾ HOẠCH TIẾP: `docs/KE_HOACH_TIEP_2026-08-24.md`** (một danh sách duy nhất, có thứ tự). Xem D-045…D-057 + `docs/ANH_NOI_BO/` |
| **LLM NỘI BỘ bán qua API** (H38, Q106+Q107) — Qwen3.8-27B trên máy B, bán qua `/api/v1` | ✅ **ĐANG BÁN 2026-08-24.** Ba cửa: `/jobs` · `/chat/completions` (`SYNC_BILLED`) · `/messages` + `/responses` (`STREAM`, cho Codex/Claude Code/Claude Desktop). Đã đo thật qua Cloudflare: luồng **119 giây không bị 524**, Codex CLI chạy đầu-tới-cuối, tiền khớp từng credit. Còn: phiên thật Claude Code/Desktop, xoay khoá, công cụ tự ghi cấu hình. Xem `docs/VLM_NOI_BO/` |
| **Bán VPS (máy chủ ảo Windows)** — app `apps/vps/`, Proxmox chạy LỒNG trong VMware trên máy B | 🔨 **~95% — G1→G10 xong 2026-08-25** (H39, Q103–Q105). App vẫn **TẮT** (`LTT_VPS` chưa đặt) — đó là việc của chủ sản phẩm, không phải của một phiên Claude. Chuỗi đã đo thật đầu-tới-cuối: tạo máy **17 giây** → boot thẳng vào trình cài Windows → console trong trình duyệt → DHCP theo MAC → RDP từ Internet qua **IP riêng của từng máy** → thu tiền → treo → xoá → **trả IP về Vultr**. 🔴 **Cụm không chạy được virtio** — máy phải `sata0`+`e1000`, `agent:0`, `balloon:0` (xem `MO_HINH_CARD` trong `apps/vps/services/mang.py`). 🔴 **Khách TỰ CÀI Windows** (chốt 24/08): nền tảng **không bao giờ biết mật khẩu của khách**, không có template, không sysprep. Danh mục dừng ở **Server 2016, Server 2022, Windows 10 LTSC** — **KHÔNG bán Windows 11** (nhánh UEFI/vTPM đã gỡ khỏi `jobs.py`). ⚠️ Hợp đồng app có thêm `AppManifest.bao_tri` — app khai việc định kỳ, nền tảng chạy nó **dưới lease**; app tự dựng vòng lặp sẽ trừ tiền khách N lần mỗi chu kỳ. ✅ **G8 + G10 xong 25/08**: trang tạo máy hai bước, **trang bán công khai** (`/vps` phục vụ cả khách chưa đăng nhập — thẻ app trong catalog trỏ tới đó, nên đòi đăng nhập là ngõ cụt ngay bước đầu phễu), điều khoản riêng + clickwrap, sao kê thanh toán. `test_298` đối chiếu **từng con số** trong điều khoản với hằng số thật — đổi giá mà quên sửa điều khoản là gate đỏ. ✅ Đã **dọn sạch dấu vết diễn tập**: 0 VM lạ, **0 Reserved IP** bên Vultr, 4 bảng `vps_*` về 0 dòng; tài khoản thử bị **vô hiệu hoá chứ không xoá** (bút toán credit là append-only). ⚠️ Còn **G7b** (cpulimit + cảnh báo CPU) và **G9b** (diễn tập dựng lại cổng vào — **KHÔNG cần mua thêm VPS**: Reserved IP sống sót khi instance chết, nên có đường dựng lại $0; hoãn vì nó là hành động không đảo được trên một máy đang trả tiền). ⚠️ Trước khi mở bán phải chạy `setup\cong_tac_tool_api.ps1` **rồi mới** deploy. ✅ Đã xoá **3 template + 7 ISO chết**; đường `clone` gỡ hẳn, `os_images` chỉ còn Windows. Kho `local` còn **5,1 GB**, đủ cho ba ISO đang dùng. ⚠️ **Có shell root trên node** qua `tools/vps_node_shell.py` (termproxy = shell root; token cũng có `Sys.Modify`) — đừng lặp lại kết luận cũ rằng không có. ⚠️ Hạn ngạch Reserved IP của Vultr tính **cả IP vừa xoá**, nên tạo/xoá liên tục lúc thử sẽ làm lượt sau hỏng ở mốc 92%. Xem `docs/VPS/PHAN_TICH_VPS_PROXMOX.md` và mục G ở `docs/KE_HOACH_TRIEN_KHAI.md` |

**Admin hiện tại là tài khoản trong CSDL** (`tools\create_admin.py`), đăng nhập
bằng email; đường admin-từ-biến-môi-trường đã vô hiệu ở production (Q29).

**H7 (Củng cố MVP) — Wave 0+1+2 ĐÃ XONG 2026-07-31** theo audit
`docs/AUDIT_MVP_2026-07-31.md`: đã bịt các lỗ P0 (double-spend, dedupe, IP thật
sau Tunnel, restore DB, băm token phiên, migration trong update) và P1/P2
(billing thumbnail theo ảnh, handler 500, CSRF admin/logout, khoá theo tài khoản,
ACL backup, validate hợp đồng sớm, log rotation, smoke test). Việc **cố ý hoãn**
sang H9/H10 ghi trong file audit + KE_HOACH (url_for/R2, FK constraints).
Cửa mở khách trả tiền giờ phụ thuộc **H9 (Thanh toán)**.

**H22 (Rà soát hệ điều hành) — 9/12 XONG 2026-08-06** theo audit
`docs/APP_AUDIT/control-plane/2026-08-06/`: chốt nơi đặt logic nghiệp vụ
(`AGENTS.md` mục 8), tách hai file route 1.799 và 1.308 dòng, gom việc dùng
chung về `platform_core`, và **cắt hết phụ thuộc của app vào `core/`**.

Ba việc còn lại, **hai trong đó chờ chủ sản phẩm quyết**:
- **H22.10** ✅ → **VƯỢT QUA 2026-08-25**: 43 route đó không còn nằm sau cờ
  nữa, chúng **đã bị xoá** cùng app socialbot (Q108). Cờ `LTT_SOCIALBOT_ROUTES`
  không còn được đọc ở đâu; để lại trong `secrets/app.env` là một dòng vô nghĩa,
  không phải một lỗi. Bề mặt route công khai giảm đúng 62% như đã dự tính.
- **H22.11** ✅ — đã xoá 2 module `core/` không ai gọi (533 dòng). Ba file
  `__init__.py` giữ lại vì là dấu hiệu package.
- **H22.12** ✅ — `platform_core` sạch hết chỗ nuốt lỗi; 90 chỗ còn lại trong mã
  sống nằm sau **bánh cóc** `tools/check_silent_except.py` (trong gate): không
  cho tăng thêm. `core/` (78 chỗ) loại khỏi phép đo vì đã đóng băng.

**H35 (Public API) — XONG 2026-08-15**, nhánh `public-api-v2`, quyết định nền
Q92. Nó là **adapter/policy layer**, không phải một app trong `apps/`: domain ở
`platform_core/public_api/`, HTTP ở `server/api/`. Dùng lại nguyên
`jobs`/`credit`/`upload_sessions`/`storage` — **đừng dựng hàng đợi, sổ tiền hay
pool thứ hai**.

Ba thứ cần biết trước khi đụng vào:

- **Fail-closed.** `LTT_PUBLIC_API` mặc định TẮT, và `LTT_PUBLIC_API_TOOLS` mặc
  định **rỗng** — bật cờ một mình **không** mở tool nào. `customer_visible` của
  ToolSpec **không** phải cờ public.
- **24 route đóng băng** ở `server/api/inventory.py`, so hai chiều với route
  thật và OpenAPI. Thêm route mà quên khai là gate đỏ, và ngược lại.
- **Thêm/đổi tool đang mở thì phải cập nhật `APP_API_COVERAGE_FINAL.md`** —
  `test_212` đọc bảng đó như dữ liệu và so với registry cả hai chiều.

**H36 (2026-08-16)** sửa ba lỗi P0 mà audit tìm ra, tất cả cùng một gốc: **mọi
vòng nền được viết như thể chỉ có một tiến trình chạy nó**, trong khi số tiến
trình worker mặc định bằng **số GPU**. Hệ quả: webhook gửi trùng, cảnh báo trùng,
việc dọn chạy N lần.

Ba thứ cần biết trước khi đụng vào worker:

- **Việc nền nằm sau một lease** (`platform_core/leases.py`). Thêm một việc nền
  mới thì đặt nó trong `_mot_luot_bao_tri`, đừng tự chạy trong vòng job — vòng
  đó chạy ở **mọi** tiến trình.
- **Đội hình worker khai bằng `LTT_WORKER_POOLS`** (vd `api:8, gpu+ffmpeg:2`).
  Không khai thì giữ nguyên hành vi cũ.
- **`test_214` là bằng chứng đa tiến trình.** Từ H36.9 nó đã vào gate qua
  `tools/check_multiproc.py` (tự tìm/tạo CSDL test). Vẫn nên chạy tay sau khi
  sửa bất cứ thứ gì trong worker hoặc outbox.

Điểm audit trung thực sau H36.9–12: **9,0/10**
(`docs/PUBLIC_API/AUDIT_API_2026-08-15.md` §4c). Việc duy nhất còn nợ của H36 là
chạy `test_221` trên một bucket R2 vứt đi — chặn bởi một quyết định hạ tầng,
không phải bởi code.

**ĐÃ DEPLOY 2026-08-17**, và **TẠM DỪNG có chủ ý** để chuyển sang LTT Nexus.
Đọc `docs/PUBLIC_API/TAM_DUNG_2026-08-17.md` trước khi mở lại — nó ghi mở lại
thì bắt đầu từ đâu và ba cái bẫy đã dính.

🔴 **SỬA 2026-08-26 — ĐOẠN NÀY TRƯỚC ĐÓ NÓI SAI, VÀ NÓI SAI VỀ PHÍA NGUY HIỂM.**

Nó từng viết *"hạ tầng đã sống, **cửa hàng chưa mở**… `LTT_PUBLIC_API_TOOLS`
**rỗng**"*. Đọc production ngày 26/08:

```
LTT_PUBLIC_API=1
LTT_PUBLIC_API_TOOLS=text.chat,image.ltt
```

**Hai tool đang mở và đang thu tiền thật.** Cùng tài liệu này, hàng H38 nói LLM
*"ĐANG BÁN 2026-08-24"* — tức hai câu trong **một** tệp mâu thuẫn nhau suốt hai
ngày.

⛔ Vì sao nó nguy hiểm chứ không chỉ sai: một phiên sau đọc đoạn này sẽ tin
`/api/v1` **không phục vụ ai**, rồi sửa nó **như sửa mã chết**. Nó đang phục vụ
khách trả tiền.

⭐ Và tool đã mở **không phải** `image.thumbnail` như kế hoạch từng ghi — thứ tự
mở cửa đã đổi trên thực tế mà kế hoạch không theo kịp.

**Trạng thái đúng:** khu API bật, **hai tool mở** (`text.chat`, `image.ltt`),
fail-closed của Q92 vẫn đúng việc với mọi tool còn lại. Năm điều kiện §11 đã
đóng; còn nợ: **xoay khoá provider** và **H35.10** (tool video).

**H37 (bắt đầu 2026-08-21, Q102)** — model tạo ảnh chạy trên **máy B**
(`MAY-B` 192.168.2.66, RTX 3090 24 GB, RAM 192 GB). Nó là **một provider**
(`ltt_image`), **không phải một app**: thêm một dòng vào `platform_core/providers.py`
+ adapter dùng chung `platform_core/image_gen/`. Kế hoạch 13 phase và cổng chấm
điểm ≥ 9/10 ở `docs/ANH_NOI_BO/KE_HOACH_THI_HANH.md`.

Sáu thứ phải biết trước khi đụng vào:

- ⚠️ **Máy B có thể tự khởi động lại để cập nhật Windows** (Active Hours 07:00 →
  01:00; đã xảy ra 22/08 lúc 01:29, sự kiện `1074`, cuốn theo một lô ở ảnh 21/30).
  ✅ **KHÔNG còn là hạn chót nữa.** Lô đo nay ghi kết quả **sau mỗi ảnh** và **bỏ qua
  ảnh đã xong** khi chạy lại, nên một lần khởi động lại chỉ mất **đúng một ảnh đang
  vẽ** — vài chục giây, không phải cả lô. Bằng chứng: `tests/test_266_tiep_tuc_lo_do.py`.
  ⇒ **Đừng lên lịch quanh mốc 01:00, và đừng nhắc lại nó như một điều kiêng kỵ.**
  Cũng **không cần** đổi `AUOptions` — đó là một thiết lập bảo mật, và cái giá của nó
  (máy tích luỹ bản vá chưa áp) lớn hơn thứ nó cứu.
  *(Tôi đã chẩn đoán nhầm vụ 22/08 thành "cạn VRAM" — xem D-025 để biết vì sao nhầm.)*
- ✅ **VRAM: cảnh báo "97,5 %" ĐÃ LỖI THỜI — đừng lên kế hoạch quanh nó (D-056).**
  Con số 23,9 / 24,6 GB đo **trước** khi ComfyUI chạy với `--reserve-vram 3`. Đo
  lại 24/08 trên cùng card: t2i 50 bước **18,45 GB** (lô 100 lượt, dao động chỉ
  163 MB), `edit` 1 ảnh @4 MP **19,83 GB**, `subject` 2 ảnh @4 MP **20,11 GB** —
  cấu hình **nặng nhất từng đo** nay là 20,1 GB, biên còn **~4,5 GB**.
  ComfyUI trên B **đã** chạy với `--reserve-vram 3` (`test_245` chốt cờ đó khớp
  `VRAM_CHUA_LAI_GB`, mất nó lặng lẽ là sập giữa một lô dài).
  ⚠️ Nhưng **đừng đọc ngược thành "thoải mái"**: 4,5 GB là biên **khi chỉ có ta**.
  Ba hộ vẫn dùng chung card (D-037) — dự án video từng ăn 98,7 %, `llama-server`
  giữ 15,9 GB. Chốt bận của cổng render vẫn là thứ giữ hai hộ không đè nhau.
- 🔴 **CHƯA ĐO THÌ KHÔNG CHẠY.** `render_gateway/ngan_sach.py` từ chối mọi cấu hình
  vượt `TOKEN_DA_DO_TOI_DA` **trước khi chạm GPU**. Trần nay là **11.412** (4.096 →
  7.506 → 11.412, mỗi lần nâng đều có số đo: D-032, D-053). Cả `edit` và `subject`
  ở `ref_mp=4.0` **đã đo xong và đã mở**; bậc kế tiếp (2 ảnh @8 MP = 19.224 token)
  vẫn bị chặn, có test riêng chốt.
  Muốn mở tiếp thì **đo theo bậc, có người canh** rồi ghi số vào `DECISIONS.md`.
  **Đừng hạ `ref_mp` cho lọt chốt** — đó chỉ là chọn một con số khác cũng chưa ai đo.
  ⚠️ Và biết một điều trái trực giác trước khi đọc trần này: **token là proxy rất
  lỏng cho VRAM** — token gấp 2,1 lần mà VRAM chỉ +1,8 % (D-053). Trần vẫn đúng
  việc (từ chối cấu hình chưa đo) nhưng **đừng đọc nó như thước đo mức nguy hiểm**.
- **Máy B KHÔNG giữ bí mật nào của nền tảng.** Không mật khẩu CSDL, không khoá R2,
  không `LTT_TOKEN_ENCRYPTION_KEY`. Ảnh vào bằng presigned GET, ra bằng presigned PUT.
- ⚠️ **ComfyUI trên máy B KHÔNG có xác thực.** Nó chỉ được nghe `127.0.0.1`, vĩnh
  viễn. Chỉ cổng render (:8199, bearer token) nghe LAN, tường lửa chỉ mở cho
  192.168.2.17. **Không bao giờ** đưa ra Cloudflare.
- 🔴 **MÁY B CÓ BA HỘ DÙNG CHUNG GPU, không phải hai** *(đo 22/08 22:27)*:
  ① **video** — `E:\LTT AI`, dùng chung đúng ComfyUI đó; một lượt từng chạy 72,5
  phút và ăn 98,7 % VRAM. ② **LLM** — `H:\LTT_LLM`, dịch vụ `LTTLlamaSwap` +
  `LTTLlmGateway` (cổng 8280/8299); `llama-server.exe` nạp một model 27B giữ
  **15,9 GB** và **ngồi im ở đó**, GPU 0 % tải, tự nhả sau `ttl: 1800`. ③ ta.
  Job ảnh **không xếp hàng sau ai cả** — bận thì cascade sang Gemini.
  ⚠️ Hộ ② **không phải tiến trình python**, và điều đó từng làm chốt dò bận của
  cổng render báo *rảnh* trong khi card chỉ còn 4,6 GB — xem D-037.
- **Bận ≠ hỏng.** Khi B bận, tuyệt đối **không** gọi `api_pool.danh_dau_loi()` cho
  key `ltt_image`: cooldown rồi `disable` sau 5 lần, và một tối chạy video sẽ tự
  tắt vĩnh viễn model nhà.

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
