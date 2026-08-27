# Audit + kế hoạch thử thật: tool .exe cắm Codex (VS Code) → API LTT

**2026-08-27** · mục tiêu: dùng **chính tool .exe đã phát hành** để cắm **tiện
ích Codex trong VS Code** vào `/api/v1` của ta, chạy như người dùng thật, rồi
**chứng minh Codex đi qua API của ta**.

---

## Phần A — Audit (đã kiểm, không đoán)

### A1. Phiên bản trên web = bản cao nhất ✅
| Kiểm | Kết quả |
|---|---|
| Hằng số tool | `PHIEN_BAN = 1.1.0` (`tools/cam_cli.py:91`) |
| `/tai/cong-cu-cam` phục vụ | `LTTStudios-CamCLI-Setup-**1.1.0**.exe` (25.953.944 byte) |
| Thư mục phát hành production | `C:\LTTPlatform\data\api_dist\` có 1.0.0 **và** 1.1.0 + BAT-1.1.0.zip; route chọn **cao nhất** (`_goi_moi_nhat` so theo số phiên bản) |
| **SHA-256 phục vụ = công bố** | `853c1e1e3a325767d0cfcbf2387b16ebf52faf1660d74d220cdda4293863d576` — **khớp** giữa tệp thật và trang `/huong-dan/cong-cu` |

⇒ "Đảm bảo bản cao nhất": **ĐẠT**. Chuỗi toàn vẹn còn nguyên (không ký số, nhưng
hash đối chiếu được — đúng thiết kế: chủ sản phẩm chốt không mua chứng chỉ ký,
24/08).

### A2. Kiến trúc tool
- **GUI EXE** (`cam_cli_gui.py`): pywebview — **không mở cổng HTTP cục bộ**, gọi
  Python qua `window.pywebview.api`. Bốn method: `xem()` · `cam(khoa, lua_chon)`
  · `kiem()` · `go()`. → điều khiển được bằng computer-use (cửa sổ native tier "full").
- **Console EXE** (trong ZIP+BAT): stdout/mã thoát thật cho đường CLI.
- **Một nguồn cấu hình**: cả tool, trang `/developers/cli`, và `/huong-dan` đều
  lấy đoạn cấu hình từ `platform_core/public_api/examples.py` → ba nơi không lệch.

### A3. Codex trong VS Code — điểm mấu chốt (guide §2.2)
🔴 Tiện ích Codex **không truyền được `--profile`**, và Codex 0.145 **từ chối**
`[profiles.ltt]` trong `config.toml`. ⇒ **bắt buộc dạng GỐC** ở `~/.codex/config.toml`:
```toml
model = "ltt_llm"
model_provider = "ltt"
model_reasoning_effort = "low"
model_context_window = 65536

[model_providers.ltt]
name = "LTT Studios"
base_url = "https://app.lttstudios.com/api/v1"   # có /v1 — Codex tự ghép /responses
env_key = "LTT_API_KEY"
wire_api = "responses"
stream_idle_timeout_ms = 600000
```
⚠️ **Dạng gốc THAY luôn mặc định của lệnh `codex`** trên máy — giới hạn của Codex,
không phải của ta. Đảo lại bằng `go` (trả về **bằng từng byte**).
Khoá để ở biến môi trường `LTT_API_KEY`, **không** nằm trong tệp cấu hình nào.

### A4. Hai cái bẫy sẽ gặp
1. **Bẫy re-login (guide §3):** `setx LTT_API_KEY` ghi **registry** ngay, nhưng
   phiên Windows **đang chạy** giữ môi trường cũ. Đo thật: mở lại VS Code **không
   đủ**, restart explorer **không đủ** — chỉ **đăng xuất/đăng nhập lại Windows**
   mới làm tiện ích thấy khoá. ⇒ tiện ích Codex **sẽ không thấy `LTT_API_KEY`**
   cho tới khi re-login.
2. **CF chặn User-Agent mặc định:** urllib mặc định bị Cloudflare trả 403 trước
   khi tới máy chủ. Tool đã đặt `User-Agent: ltt-cam-cli/1.0`. (Liên quan tới
   việc mình soi `/login` bằng curl cũng bị 403.)

### A5. Cách tool tự chứng minh (`kiem`)
Gọi THẬT một lượt bằng khoá đã cấu hình: `GET /tools` → `GET /credits/balance` →
`POST /messages` (stream, `ltt_llm`) → `POST /messages` (không stream,
`MODEL_DESKTOP`). Xanh = 200 ở cả bốn + **số dư credit giảm**. Đây là bằng chứng
"khoá + API chạy" — nhưng **chưa** phải bằng chứng "tiện ích VS Code đi qua API"
(xem C4).

---

## Phần B — Ranh giới (giữ chặt)

| Việc | Ai làm | Vì sao |
|---|---|---|
| **Nhập khoá API** | **NGƯỜI DÙNG**, vào ô che của tool | Không nhập credential thay người dùng; tool che khoá; mình không thấy giá trị |
| **Chạy tool .exe** | Mình (được phép) | Là tool **của chính ta**, hash đối chiếu được, user yêu cầu thử — không phải "tệp nguồn không tin" |
| **Gõ trong VS Code** | **NGƯỜI DÙNG** (hoặc bỏ qua) | computer-use xếp IDE ở tier "click": mở/bấm được, **gõ/phím thì chặn**. Prompt test phải do người dùng gõ |
| **Đăng xuất/đăng nhập Windows** | **NGƯỜI DÙNG** | Là hành động hệ thống, gián đoạn phiên; mình chuẩn bị, user bấm |
| **Deploy / cấp credit** | Không đụng | Ba ranh giới cứng của phiên |

---

## Phần C — Kế hoạch thử thật (theo pha)

### ⚠️ C0. QUYẾT ĐỊNH TRƯỚC: chạy trên máy nào?
**Máy này LÀ máy chủ production** (`C:\LTTPlatform` tồn tại). Cắm Codex ở đây:
- đổi **mặc định `codex`** của người dùng hiện tại (đảo được bằng `go`);
- cần **re-login Windows** để tiện ích thấy khoá — **gián đoạn phiên đang dùng**;
- **KHÔNG** chạm dịch vụ nền tảng (chỉ sửa cấu hình Codex của user), nên rủi ro
  với khách đang trả tiền là thấp — nhưng re-login là phiền thật.

Guide gom bằng chứng trên **VM sạch** có chủ ý: "chạy được vì đang ở nhà" là một
giả thuyết nhiễu mà chỉ máy sạch loại được. **Khuyến nghị:** chạy trên **máy dev
của bạn hoặc một VM Windows sạch**, không phải máy chủ này. Nếu bạn vẫn muốn máy
này, mình làm được — nhưng chấp nhận re-login + đổi codex default (đảo lại sau).

### C1. Tải + đối chiếu (Bash, không cần computer-use)
- `curl https://app.lttstudios.com/tai/cong-cu-cam -o LTTStudios-CamCLI-Setup-1.1.0.exe`
- Đối chiếu SHA-256 với `853c1e1e…` (đã kiểm ở A1). **Không chạy nếu lệch.**

### C2. Mở VS Code + tool (computer-use)
- `request_access` cho: VS Code, và tiến trình tool (cửa sổ pywebview).
- Mở VS Code (xác nhận tiện ích **Codex** đã cài — nếu chưa, cài từ Marketplace,
  đây là điều kiện tiên quyết cần bạn xác nhận).
- Chạy `.exe` → qua SmartScreen "Windows protected your PC" → *More info → Run anyway*
  (không ký số — đã biết). Cửa sổ tool hiện.

### C3. Cắm codex-vscode
- Trong tool: tích **đúng** bề mặt **Codex (VS Code)** = `codex-vscode`. **Bỏ** các
  bề mặt khác (không cắm thừa).
- **BÁO BẠN** → bạn nhập khoá `ltt_sk_…` vào ô che → bấm **Cắm**.
- Tool ghi **dạng gốc** `config.toml` + `setx LTT_API_KEY`. Mình đọc lại bằng
  `xem` để xác nhận: có khối `[model_providers.ltt]` ở gốc, `model_provider = "ltt"`.

### C4. Chứng minh — hai lớp
**Lớp 1 (API chạy với khoá) — làm được ngay, không cần re-login:**
- Bấm **Kiểm** trong tool (`kiem --khoa`, dùng khoá vừa nhập, không cần env). Kỳ vọng:
  `/tools` 200, `/credits/balance` 200 + số dư, `/messages` 200. **Ghi số dư trước.**

**Lớp 2 (tiện ích Codex THẬT đi qua API) — cần re-login + bạn gõ:**
- **Re-login Windows** (bạn) → mở VS Code mới (env đã có `LTT_API_KEY`).
- Bạn gõ một câu vào Codex trong VS Code, ví dụ **"12 × 12 = ?"** (guide dùng đúng
  câu này, trả `144`).
- **Bằng chứng phía máy chủ (mình kiểm, không cần đăng nhập UI):**
  - Số dư credit **giảm** so với mốc C4-Lớp1 (mỗi lượt gọi thu credit).
  - Một dòng mới trong `ApiRequestLog` / một job `text.chat` qua `/messages`
    (`request_log.list_for`) — đúng mốc thời gian, đúng khoá.
- Chốt: **200 + credit giảm + dòng log = tiện ích Codex đã đi qua API của ta.**
  (Guide §4: "không có tiền bị trừ thì không có gì chứng minh cả.")

### C5. Dọn / để nguyên
- Nếu chỉ để thử: bấm **Gỡ** (`go`) → `config.toml` về **bằng từng byte**, codex
  default trở lại như cũ. Xác nhận bằng `xem`.
- Nếu bạn muốn giữ Codex cắm vào LTT: để nguyên, ghi lại rằng codex default đã đổi.

---

## Phần D — Rủi ro + điều cần ở bạn

| Rủi ro | Giảm nhẹ |
|---|---|
| Máy này là production | Chỉ sửa cấu hình Codex của user, không chạm service; đảo được bằng `go`. **Nên cân nhắc chạy trên VM sạch.** |
| Re-login gián đoạn phiên | Bạn chủ động; hoặc chấp nhận Lớp-1 (API proof) mà chưa re-login |
| SmartScreen chặn | Đã biết (không ký số); đối chiếu hash trước khi chạy |
| Tiện ích Codex chưa cài | Cần bạn xác nhận đã cài, hoặc cho phép mình cài từ Marketplace |

**Mình cần ở bạn, theo thứ tự:**
1. **Chạy trên máy nào** — máy chủ này (chấp nhận caveat) hay VM/máy dev sạch?
2. Xác nhận **tiện ích Codex đã cài** trong VS Code (hoặc cho cài).
3. Cho phép mình **request_access** computer-use (VS Code + tool) và **chạy .exe**.
4. Khi mình báo "sẵn sàng nhập khoá" ở C3 → bạn nhập khoá vào ô che của tool.
5. (Cho Lớp-2) chấp nhận **re-login Windows** + gõ một prompt test vào Codex.

---

## Phần E — KẾT QUẢ THỬ THẬT 2026-08-27: GUI EXE 1.1.0 HỎNG CẦU NỐI

Chạy thật trên máy chủ này (WebView2 149.0.4022.80). Tải 1.1.0 từ web (hash
khớp `853c1e1e…`), cài im lặng (per-user, không UAC), mở GUI, chọn codex-vscode,
bỏ chọn cả ba Claude, người dùng dán khoá, bấm **Cắm vào** →

```
[LỖI] Đang cắm các hạng mục đã chọn thất bại: TypeError: Cannot read properties of null (reading 'cam')
```
Trạng thái kẹt ở **"Đang đọc…"** — cầu `window.pywebview.api` **null**.

### Chẩn đoán (đã cô lập từng lớp)
| Phép thử | Kết quả |
|---|---|
| `python cam_cli.py xem` (core CLI) | ✅ chạy hoàn hảo — logic lõi TỐT |
| pywebview 5.3 + html nội tuyến (script test) | ✅ BRIDGE_OK |
| pywebview 5.3 + file:// (như tool) | ✅ BRIDGE_OK |
| **EXE đóng băng (PyInstaller)** | ❌ cầu null |
| So `webview/js` hệ thống vs EXE | **hệ thống có `api.js`+`customize.js`+`finish.js`; EXE THIẾU cả ba** |

### Nguyên nhân gốc
**PyInstaller không thu các tệp dữ liệu JS của pywebview** (`webview/js/*.js`) —
đúng ba tệp tiêm `window.pywebview.api`. Bản dựng chỉ có DLL WebView2 (binary),
thiếu JS → WebView2 mở trang được nhưng **cầu nối không bao giờ được tiêm**. Chỉ
hiện trên EXE, không hiện khi chạy nguồn. **Không phải lỗi pywebview version,
không phải WebView2 149, không phải mã tạo cửa sổ.**

### Sửa (1.1.1)
1. `tools/dong_goi_exe.py`: thêm **`--collect-data webview`** vào lệnh PyInstaller
   của bản GUI → gói đủ `webview/js`.
2. `tools/gui/index.html`: thêm **guard cầu-nối-chết** — `coCau()` + timeout 4s:
   nếu `api()` null thì báo rõ "lỗi bản dựng" + chỉ đường CLI + khoá nút, thay vì
   ném TypeError thô và kẹt "Đang đọc…" mãi.
3. Nâng phiên bản **1.1.0 → 1.1.1** (`cam_cli.py` + `cam_cli.iss`).

### Cảnh báo vận hành
1.1.0 đang **trên web** và **hỏng với mọi khách có WebView2 149.x**. Sau khi 1.1.1
chạy ổn trên máy này → thay tệp trong `data/api_dist` (route tự phục vụ bản cao
nhất; không cần deploy lại vỏ nền tảng).

## Phần F — LỖI THỨ HAI (nặng hơn) + cơ chế chống rác: 1.1.1 → 1.2.0 (27/08)

Sau khi 1.1.1 sửa cầu nối, mở **tiện ích Codex thật** trong VS Code mới lộ lỗi
thứ hai — và đây mới là lỗi làm chết tính năng:

### Triệu chứng
Sau `Cắm` (codex-vscode) + `Kiểm thật` **xanh hết**, tiện ích Codex vẫn hiện màn
"Sign in with ChatGPT". `~/.codex/config.toml` **không parse được**:

```
TOMLDecodeError: Cannot declare ('model_providers','ltt') twice (line 129)
```

### Gốc
`cam_codex` chế độ vscode chèn **mù** một khối chứa `[model_providers.ltt]` + các
khoá `model`/`model_provider` ở top-level, **nối vào cuối tệp**. Khi máy khách đã
có sẵn (ví dụ setup VLM H38):
1. **Trùng bảng** — hai `[model_providers.ltt]` ⇒ TOML hỏng.
2. **Sai vị trí** — khoá top-level nối sau một `[bảng]` ⇒ rơi *vào trong* bảng đó.
3. **Trùng khoá** — khách đã có `model`/`model_reasoning_effort` ở gốc ⇒ hai khoá.

### Vì sao `kiem` không bắt được
`kiem` **tự gọi HTTP** (`GET /tools`, `POST /messages`) — nó **không** nhờ Codex
đọc `config.toml`. Nên cắm ghi ra TOML hỏng mà `kiem` vẫn 200. **Chỉ mở tiện ích
thật mới lộ.** Khe hở test tương ứng: *không một test nào parse kết quả cắm*, và
fixture cũ dùng `[model_providers.cua_toi]` (tên KHÁC) nên ca trùng-`ltt` chưa
bao giờ chạy.

### Cơ chế đã xây (4 tầng, `tools/cam_cli.py`)
1. **Cổng kiểm TOML** — `_toml_hop_le()` parse thử kết quả TRƯỚC khi ghi; hỏng
   thì `raise CauHinhHong`, **không ghi**, không đặt khoá. Đây là lưới an toàn
   đáng ra đã chặn lỗi gốc.
2. **Gỡ-trước (idempotent)** — luôn `_go_khoi` + `_khoi_phuc_model_goc` trước khi
   chèn ⇒ chạy N lần = 1 lần.
3. **Không nhân đôi provider** — `_co_provider_ltt()`: đã có `[model_providers.ltt]`
   thì không chèn lại bảng.
4. **Đặt top-level đúng chỗ, đảo ngược được** — `_vo_hieu_model_goc()` chú-thích-hoá
   5 khoá gốc của khách bằng tiền tố `TAG_TAT`, đặt khối của ta ở ĐẦU tệp
   (`_chen_khoi_dau`); `go` bóc tiền tố ⇒ **trả về nguyên trạng từng byte**.

### Chứng minh đầu-tới-cuối (tiện ích thật)
Sau khi vá config sống + nạp `LTT_API_KEY` vào env rồi mở lại VS Code:
- Màn "Sign in" biến mất → ô chat sẵn sàng, model hiển thị **"Custom"** (= provider ltt).
- Hỏi "bạn là model gì?" → trả lời **"Mình là Qwen… Alibaba"** (= `ltt_llm` máy B,
  KHÔNG phải `gpt-5.6-sol`).
- Credit **1335 → 1333** ngay sau lượt chat ⇒ đi qua API của ta và **có tính tiền**.

### Test mới (đóng khe hở)
`tests/test_283_cam_cli.py`:
- `test_vscode_ket_qua_LA_TOML_HOP_LE_du_khach_da_co_provider_ltt` — **parse** kết quả.
- `test_vscode_go_tra_ve_DUNG_TUNG_BYTE_khi_da_co_provider_ltt`.
- `test_profile_KHONG_nhan_doi_provider_ltt_da_co_san`.
- `test_cong_kiem_TU_CHOI_ghi_khi_ket_qua_hong`.

### Khác
- **Hiển thị phiên bản** trong GUI: badge `v1.2.0` ở header (qua `xem()`) + tiêu đề
  cửa sổ (tĩnh, hiện cả khi cầu nối chết).
- Nâng **1.1.1 → 1.2.0** (`cam_cli.py` + `cam_cli.iss`, đồng bộ qua test).
