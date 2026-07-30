# Kế hoạch đạt 100% chức năng trên web và loại bỏ desktop

> Lập sau đợt audit trực tiếp trên `https://app.lttstudios.com` (đăng nhập
> thật bằng trình duyệt) cộng đối soát code ngày 2026-07-30.
> Không có giá trị bí mật nào trong file này.

## 1. Hiện trạng đo được, không phỏng đoán

> **Bảng dưới là số đo GỐC lúc lập kế hoạch (2026-07-30, trước W3–W6).**
> Giữ lại để đối chiếu. Trạng thái hiện tại xem mục 6 ở cuối file.

Đo bằng cách đăng nhập và đọc nội dung thật từng trang:

| Trang | Ký tự | Form | Bảng | Trạng thái |
|---|---|---|---|---|
| Cài đặt | 8.635 | 2 | 0 | ✅ đầy đủ 120 trường |
| Sheet FB / Sheet TikTok | ~510 | 5 | 1 | ✅ có worker CRUD + hàng đợi |
| Tài khoản FB | 703 | 2 | 0 | ⚠️ chạy được, thiếu bảng Pages khi chưa có account |
| Tài khoản TikTok | 485 | 1 | 0 | ⚠️ chỉ xem + refresh/ngắt |
| Manual FB | 582 | 1 | 0 | ✅ đã port (W3) |
| Manual TikTok | 679 | 1 | 0 | ✅ đã port (W3) |
| Monitor | 437 | 1 | 0 | ✅ đã port (W4) |
| TT Audit | 425 | 1 | 0 | ✅ đã port (W4) |
| Bảng điều khiển / Tình trạng | ~600 | 1-2 | 0 | ⚠️ mỏng |

Desktop có **9.757 dòng** giao diện. Lúc đo, web phủ khoảng **35%** chức năng.

## 2. Blocker thật — phát hiện khi đối soát code

### B-1 (chặn mọi thứ) — Google Sheets không kết nối được trên VPS

`utils/sheet_client.py:136` dùng `flow.run_local_server(port=0)` — mở trình
duyệt trên chính máy chạy code. Credentials hiện tại
(`secrets/oauth/client.json`) thuộc loại **`installed`** (OAuth desktop
client), nên trên VPS **không thể xác thực được**.

**May mắn: code đã hỗ trợ sẵn Service Account** (`sheet_client.py:107`,
nhánh `if data.get("type") == "service_account"`) — luồng này **không cần
trình duyệt**. Không phải sửa code, chỉ cần đổi loại credentials.

### B-2 (chặn mọi thứ) — Config trên VPS vẫn là bản mẫu

```
google_credentials_path = 'REPLACE_ME_google_credentials_path'
sheet_id                = 'REPLACE_ME_sheet_id'
```
Thư mục `C:\LTTPlatform\secrets\` chỉ có `app.env`, chưa có file credentials.

### B-3 — Không có cách nào tải credentials lên qua web

Desktop dùng `filedialog` chọn file trên máy. Web chưa có ô upload, nên
dù có Service Account cũng không đưa được lên VPS qua giao diện.

### B-4 — TikTok bắt buộc phải có OAuth trên web

Facebook có đường thoát: **token System User** (dán chuỗi, không cần trình
duyệt) — đã làm xong. **TikTok không có tương đương** — bắt buộc PKCE qua
trình duyệt. Nên TikTok chỉ chạy được sau khi làm OAuth web.

Ngoài ra spec chỉ ra một lỗi thật: callback handler TikTok chỉ có `do_GET`
nhưng `callback.html` lại POST → với redirect URI HTTPS, **đường local
không bao giờ nhận được code**, chỉ relay hoạt động. Khi chuyển sang web
phải sửa, không nhân bản.

### B-5 — Code chết

`core/tiktok/auth_manager.py.bak` (22 KB) còn trong repo, cùng nội dung
localhost OAuth. Xoá.

## 3. Thứ tự triển khai — theo chuỗi phụ thuộc, không theo cảm tính

```
W1 Service Account + upload credentials  ← không có bước này thì Sheet chết
        │
        ├─► W2 Publishing Facebook (token System User đã xong)
        │
W3 Manual FB / Manual TikTok
        │
W4 Monitor + TT Audit
        │
W5 OAuth trên web  ← mở đường cho TikTok
        │
W6 Xoá hẳn gui/ và mọi cơ chế desktop
```

### W1 — Nền tảng: Sheets chạy headless

- Thêm ô **upload file credentials** vào trang Cài đặt, ghi vào
  `secrets/`, siết quyền, không bao giờ trả nội dung về trình duyệt.
- Kiểm tra loại credentials khi upload: `service_account` → OK;
  `installed`/`web` → **từ chối kèm giải thích**, vì nó cần trình duyệt.
- Nút **"Kiểm tra kết nối Sheet"** gọi `SheetClient.test_connection()` và
  hiện số tab đọc được.
- **Việc của người dùng:** tạo Service Account trong Google Cloud, tải
  JSON, và **chia sẻ Google Sheet cho email của service account** (bước
  này rất dễ bỏ sót — không chia sẻ thì đọc sheet sẽ 403).

### W2 — Đăng bài Facebook chạy thật
Đã có token System User. Còn: kiểm tra preflight cột (`core/preflight.py`
đã có) hiển thị trên trang Sheet, và chạy thử một job thật khi có credentials.

### W3 — Manual FB / Manual TikTok
Theo spec đã trích. Điểm khác desktop bắt buộc phải xử lý:
- `filedialog` → **upload video qua web** (giới hạn 10 GB FB / 4 GB TikTok);
  Caddy đã cấu hình `max_size 2GB`, cần nâng.
- Dialog xác nhận TikTok là **yêu cầu compliance** — phải giữ nguyên:
  mức riêng tư chỉ lấy từ `creator_info.privacy_level_options`, khoá cứng
  các tuỳ chọn creator đã tắt, khai báo AI/quảng cáo, ghi
  `user_confirmed_at`.
- Sửa lỗi desktop: bộ đếm ký tự tab TikTok đang hiện giới hạn Facebook
  (100/5000) trong khi validate 2200.

### W4 — Monitor + TT Audit
Sửa 2 lỗi desktop thay vì nhân bản:
- `monitor_tab.py:388` — `NameError` bị `except` nuốt làm **cột Pages luôn
  bằng 0**.
- `_Empty` fallback thiếu 5 thuộc tính → `AttributeError` khi lỗi.

Lưu ý kiến trúc: Monitor lấy số liệu từ **biến toàn cục trong tiến trình**
(`_GLOBAL_METRICS`, `_GLOBAL_BUFFER`, circuit-breaker). Trên web một tiến
trình thì vẫn đúng; nếu sau này scale nhiều worker thì phải chuyển sang
kho chung.

Audit tab gọi 3 request HTTPS **đồng bộ** — trên web phải chạy nền + cache,
không chặn request.

**Đã xong.** `server/services/monitor_service.py`, `audit_service.py`,
`server/routes/monitor.py`, `templates/monitor.html`, `audit.html`;
29 test trong `tests/test_50_monitor_audit.py`, trong đó 2 test chốt cứng
2 lỗi desktop ở trên để không tái phát. `AuditRunner` cache 600 giây +
single-flight chạy ở thread nền; trang chỉ poll `/api/audit/status` rồi tự
tải lại, nên không bao giờ probe site của người dùng mỗi lần mở trang.

Kết quả kiểm tra thật trên `https://app.lttstudios.com`: checklist trả
**1 blocking, 1 warn, 9 pass** — blocking là *"Privacy policy không mention
tiktok"*, warn là *thiếu logo TikTok official*. Đây là việc của người dùng,
không phải lỗi code.

Đồng thời `server/routes/placeholder.py` và `templates/placeholder.html`
**đã xoá hẳn** — mọi tab desktop giờ đều có trang web thật, `BUILT_PAGES`
không còn khoá nào `False` (có test chốt điều này).

Phát sinh khi chạy suite: nhánh báo lỗi của `tools/build_release.py` đọc
`f.line_number`/`f.rule_name`, hai thuộc tính **không tồn tại** trên
`Finding` (đúng tên là `.line`/`.rule`). Nhánh này chưa từng chạy vì chưa
bao giờ có finding, nên cái chặn rò rỉ bí mật sẽ vỡ đúng lúc cần nó nhất.
Đã sửa + thêm 2 test bọc nhánh đó.

### W5 — OAuth trên web
- Route `GET /oauth/facebook/callback` và `GET /oauth/tiktok/callback`
  trong chính ứng dụng (thay `HTTPServer` localhost).
- Lưu `state` + PKCE `code_verifier` phía server có TTL, gắn với phiên
  đăng nhập — hiện chúng nằm trong closure của thread, không dùng được.
- **Việc của người dùng:** đổi Redirect URI ở Meta Developer và TikTok
  Developer Portal sang `https://app.lttstudios.com/oauth/...`.
- Bỏ relay + `tiktok_oauth_relay_*` (không cần khi app đã là endpoint công khai).
- Giữ nguyên modal disclosure trước khi redirect — bắt buộc cho audit.

**Đã xong.** `server/services/oauth_service.py`, `server/routes/oauth.py`,
`templates/oauth_result.html`, `oauth_tiktok_disclosure.html`;
34 test trong `tests/test_51_oauth_web.py`.

Cách làm — **không nhân bản logic**: `core/auth_manager.py` và
`core/tiktok/auth_manager.py` được tách thành 2 nửa không phụ thuộc vận
chuyển, `build_authorize_url()` và `complete_oauth()`. `start_oauth_flow()`
của desktop giờ **gọi lại đúng 2 hàm đó**, nên phần Graph / TikTok chỉ có
một bản duy nhất. Nhân đó sửa luôn một lỗi tiềm ẩn: URL đăng nhập Facebook
trước đây nội suy chuỗi thô, không `urlencode` — chỉ vô hại vì localhost và
danh sách scope không có ký tự cần escape; một redirect URI có query string
sẽ bị cắt âm thầm.

Ba thứ web cần mà desktop lấy không mất gì từ biến closure, nay là thật:
- **Kho `state` + `code_verifier` phía máy chủ**, TTL 600 giây, dùng một lần,
  có giới hạn số lượng. Callback phát lại không tìm thấy gì.
- **Gắn mỗi luồng với đúng phiên trình duyệt** đã khởi tạo nó, qua một nonce
  trong cookie phiên đã ký. Nếu thiếu, ai biết được `state` cũng ghi được
  token vào kho của người vận hành.
- `code_verifier` **không bao giờ ra khỏi máy chủ** — có test khẳng định nó
  không nằm trong URL mà trình duyệt/TikTok nhìn thấy.

Màn hình disclosure TikTok nằm trên đường đi bắt buộc: `/oauth/tiktok/start`
chỉ nhận POST kèm `consent=yes`; không có route GET nào đi tắt được (có test).

Redirect URI đọc từ **chính 2 khoá config bot đang dùng** —
`meta_redirect_uri` / `tiktok_redirect_uri` — không thêm khoá mới. Nếu chúng
còn trỏ vào trang bridge tĩnh của bản desktop, app **từ chối ngay và nói rõ
phải sửa gì ở đâu**, thay vì đẩy người dùng sang một lỗi mờ mịt phía Meta /
TikTok. Đã kiểm tra thật trên production: bấm cả 2 nút đều hiện đúng thông
báo đó với giá trị hiện hành (`.../auth/fb-callback.html`,
`.../legal/callback.html`).

Cố tình **chưa** tự sửa config trên VPS: sửa config mà chưa khai báo URL mới
ở Developer Portal sẽ biến thông báo rõ ràng này thành lỗi mờ mịt từ phía
nhà cung cấp. Hai việc đó phải làm cùng lúc, và phần Portal cần tài khoản
của người dùng.

### W6 — Loại bỏ desktop
**Chỉ làm sau khi W1–W5 xong.** Lý do: `gui/` đang là **nguồn spec** để
port. Xoá trước khi web đủ chức năng là tự bỏ bản tham chiếu giữa đường.

Khi làm:
- Xoá `gui/`, `main.py`, `run_debug.bat`, `build_exe.bat`,
  `tests/gui_smoke_validator.py` và các test GUI.
- Xoá `core/tiktok/auth_manager.py.bak`.
- Bỏ nhánh localhost trong `core/auth_manager.py`,
  `core/tiktok/auth_manager.py`, `utils/sheet_client.py`.
- Bỏ config chết: `oauth_redirect_port`, `tiktok_oauth_port`,
  `oauth_browser_path`, `oauth_browser_profile`,
  `tiktok_oauth_relay_url/secret`.
- Sửa các câu chữ nay đã sai: "Token lưu trên máy này", "Mở app desktop…".
- `core/config_defaults.py` và `core/config_help.py` đã tách sẵn nên
  không mất dữ liệu khi xoá `gui/`.

**Đã xong.** Đã xoá: `gui/` (26 file), `main.py`, 5 file `.bat`, file
`.spec`, `tests/gui_smoke_validator.py`, `tests/test_30_operation_tab_split.py`
(40 test chỉ về `gui/operation_tab.py`), 2 script ghi demo, 3 thư mục
`.backup_*`, `tools/check_oauth_relay.py`, `tools/simulate_oauth_flow.py`,
`MIGRATION.md`, `docs/DESKTOP_BASELINE_RUNBOOK.md`. Bỏ khỏi
`requirements.txt`: `customtkinter`, `Pillow`, `qrcode[pil]`,
`google-auth-oauthlib`. 65 test chốt trong `tests/test_52_desktop_removed.py`.

Thứ tự bắt buộc: **chuyển hết test phụ thuộc `gui/` trước, xoá sau.** ~45 test
ở 13 file đọc `gui/` — phần lớn chỉ cần đổi nguồn (`DEFAULTS` →
`core.config_defaults`, `_FIELD_TOOLTIPS` → `core.config_help`,
`ResultTabs._pick_tag` → `ui_constants.log_colour`). Các test guard
compliance TikTok (`test_31`) được viết lại để soi bản web: yêu cầu audit vẫn
còn, chỉ chỗ hiện thực đổi.

### Ba lỗ hổng chỉ lộ ra khi xoá desktop

Đây là lý do phải đối chiếu từng test thay vì xoá cho nhanh:

1. **`MaintenanceDaemon` không còn ai khởi động.** Chỉ
   `gui/main_window.py` gọi nó. Xoá desktop là dọn dữ liệu theo retention
   (`DATA_RETENTION_POLICY.md`) và probe Meta/TikTok App status **âm thầm
   ngừng hoạt động** — mà toàn bộ unit test vẫn xanh. Đã chuyển vào lifespan
   của app web, có test khởi động thật rồi kiểm tra thread sống + được dừng
   khi shutdown.

2. **Ba tính năng Kho nội dung chưa từng được port.** Tab Cài đặt desktop có
   *Export Content History*, *Cross-target duplicates*, *Import CSV*; bản web
   không có dấu vết nào. Phần phủ *khoá config* đã 100%, và đó chính là lý do
   lỗ hổng này lọt — mấy nút đó không phải config. Đã port thành
   `server/services/content_tools.py` + 3 route + 21 test; export giờ tải file
   về máy người dùng (đường dẫn desktop chọn sẽ nằm trên VPS, vô nghĩa).
   Giữ nguyên một hạn chế của desktop **có chủ ý**: import CSV chỉ kiểm tra
   đọc được, không ghi vào Sheet — docstring desktop nói rõ phần ghi chưa từng
   được xây, giả vờ có sẽ làm mất dữ liệu người dùng.

3. **Thiếu `_severity_prefix` trên web.** Dòng log `[W3] Lỗi ...` được tô màu
   theo worker chứ không theo mức độ, nên trên web **mất hẳn dấu hiệu lỗi** —
   đúng cái desktop đã sửa (P2). Đã port; và phải tính màu *trước* khi chèn
   tiền tố, vì `✖ ` đẩy `[W3]` khỏi đầu chuỗi làm regex không khớp và mất luôn
   màu worker. Có test chốt cả hai.

### Sự cố khi triển khai: BOM hạ production

Script dọn 6 khoá chết trên VPS của tôi dùng `Out-File -Encoding utf8` —
PowerShell 5.1 ghi kèm **BOM**, và `json.load()` vỡ vì BOM. Kết quả:
`/health/ready` trả 503 trong khi service vẫn chạy bình thường. Lỗi của tôi.

Đã sửa gốc thay vì chỉ chữa file: `core/settings.py`,
`server/services/settings_service.py`, `core/worker_store.py` đọc bằng
`utf-8-sig`. Lý do quan trọng hơn cái sự cố: **người dùng mở `config.json`
bằng Notepad trên Windows cũng thêm BOM** và hạ cả app xuống một lỗi 503 mờ
mịt. `deploy/windows/install.ps1` cũng chuyển sang ghi không BOM.

## 4. Việc chỉ người dùng làm được

| # | Việc | Chặn cái gì |
|---|---|---|
| 1 | Tạo **Google Service Account**, tải JSON, **chia sẻ Sheet cho email đó** | Toàn bộ Sheet Runner |
| 2 | Điền Sheet ID + mapping cột thật (mapping hiện đang lệch — xem `docs/_luutru/AUDIT_REPORT.md` B3) | Sheet Runner |
| 3 | Token **System User** Facebook | Đăng bài Facebook |
| 4 | Đổi **Redirect URI** ở Meta + TikTok Portal | OAuth web (W5) |
| 5 | **Đổi mật khẩu admin** — đã lộ trong hội thoại | Bảo mật |

## 5. Nguyên tắc giữ trong suốt quá trình

1. Lấy nhãn, màu, luồng **từ code desktop**, không tự nghĩ.
2. Lỗi trong desktop thì **sửa**, không nhân bản.
3. Sau mỗi thay đổi: chạy regression + **đăng nhập bằng trình duyệt kiểm tra thật**.
4. Chức năng chưa xong thì ghi rõ "đang xây", không ẩn đi.
5. Không xoá `gui/` trước khi web đủ chức năng.

## 6. Trạng thái sau khi hoàn thành W1–W6

| Hạng mục | Trạng thái |
|---|---|
| 11/11 route trả HTTP 200 (kiểm tra thật bằng trình duyệt) | ✅ |
| `BUILT_PAGES` không còn trang nào "đang xây" | ✅ (có test) |
| `placeholder.py` / `placeholder.html` | ✅ đã xoá |
| OAuth Facebook + TikTok nhận callback trong chính app | ✅ |
| Màn hình disclosure TikTok nằm trên đường đi bắt buộc | ✅ (có test) |
| `gui/`, `main_window`, file `.bat`, `.spec` | ✅ đã xoá |
| Transport localhost + relay OAuth | ✅ đã xoá |
| 6 khoá config chết (kể cả trên VPS) | ✅ đã xoá |
| `MaintenanceDaemon` có chủ sở hữu | ✅ lifespan app web |
| Kho nội dung: export / duplicates / import CSV | ✅ đã port |
| Test | **1.344 pass**, 1 skip |
| Quét bí mật | **0 finding** |

### Còn phụ thuộc người dùng (code đã sẵn sàng)

| # | Việc | Chặn cái gì |
|---|---|---|
| 1 | Chia sẻ Google Sheet cho `bot-make-sheet@moonlit-bucksaw-482712-v1.iam.gserviceaccount.com` (quyền Editor) | Toàn bộ Sheet Runner — hiện HTTP 403 |
| 2 | Dán token **System User** Facebook ở `/facebook` | Đăng bài Facebook |
| 3 | Đổi Redirect URI ở **Meta** → `https://app.lttstudios.com/oauth/facebook/callback`, rồi sửa `meta_redirect_uri` trong Cài đặt cho khớp | OAuth Facebook |
| 4 | Đổi Redirect URI ở **TikTok Portal** → `https://app.lttstudios.com/oauth/tiktok/callback`, rồi sửa `tiktok_redirect_uri` | OAuth TikTok |
| 5 | Bổ sung đoạn nói về TikTok API vào trang Privacy Policy | 1 blocking trong TT Audit |
| 6 | Tải logo TikTok chính thức về `data/assets/tiktok_logo.png` | 1 warning trong TT Audit |
| 7 | **Đổi mật khẩu admin** — đã lộ trong hội thoại | Bảo mật |

Việc 3 và 4 phải làm **cùng lúc cả hai phía**: sửa config mà chưa khai báo ở
Portal sẽ biến thông báo hướng dẫn rõ ràng của app thành một lỗi mờ mịt từ
phía nhà cung cấp. Vì vậy app **chưa** tự sửa config, mà chỉ nói chính xác
phải đổi gì ở đâu.
