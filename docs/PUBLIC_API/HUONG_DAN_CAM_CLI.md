# Cắm Codex / Claude Code vào API của LTT Studios

**Tài liệu gộp, 2026-08-24.** Mọi con số ở đây **đã đo trên máy thật** — máy A,
máy B (GPU) và một VM Windows 10 sạch. Chỗ nào chưa đo thì nói rõ là chưa đo.

> Đây là **một nguồn duy nhất**. Trước đó hướng dẫn nằm rải ở ba tài liệu và một
> trang web, và ba chỗ trong số đó đã trôi khỏi sự thật. Sửa ở đây trước.

---

## 0. Năm bề mặt, và chúng **không** dùng chung cách cấu hình

Đây là điều gây hiểu nhầm nhất, nên nói trước:

| Bề mặt | Đọc gì | Đã chạy thật |
|---|---|---|
| **Codex CLI** | `~/.codex/config.toml` + `--profile ltt` | ✅ máy A |
| **Claude Code CLI** | biến môi trường | ✅ máy A **và máy B** |
| **Tiện ích Codex (VS Code)** | `~/.codex/config.toml` — **chỉ dạng GỐC** | ✅ VM, trả lời `144` |
| **Tiện ích Claude Code (VS Code)** | `settings.json` **cấp người dùng** | ✅ VM, trả lời `7 x 9 = 63` |
| **Claude Desktop** | **chính sách registry** (`HKCU\SOFTWARE\Policies\Claude`) + **tên model riêng** | ✅ VM, sau khi đổi tên tuyến |

🔴 **Claude Desktop có HAI rào chắn riêng, và chúng cho CÙNG một triệu chứng:**
bấm gửi — không có gì xảy ra, không log, không toast, không banner.

| Rào chắn | Phải làm gì | Chi tiết |
|---|---|---|
| Bộ lọc tên model | dùng `ltt-llm-claude-compat`, **không** phải `ltt_llm` | §2.5b |
| Chỉ mở tab **Code** | đặt `chatTabEnabled = true` | §2.5c |

⚠️ Sửa xong cái thứ nhất mà vẫn im là chỗ rất dễ kết luận nhầm rằng bản sửa không
ăn thua. Đo thật 25/08: đã `healthy`, picker đã đúng, mà vẫn **0 request** tới máy
chủ. Công cụ `cam` đặt sẵn cả hai.

⛔ **"Cấu hình xong cho CLI" KHÔNG có nghĩa là tiện ích chạy được.** Hai tiện ích
VS Code đi đường xác thực khác hẳn CLI. Đây là chỗ mất nhiều thời gian nhất khi
thử thật, và nó không hiển nhiên từ tài liệu của nhà nào cả.

---

## 1. Ba cách được hỗ trợ

### 1.1 Tool EXE — có giao diện

Tải `LTTStudios-CamCLI-Setup-1.1.0.exe`, cài không cần Administrator, rồi chọn
từng bề mặt ngay trong cửa sổ. Bản 1.1 không tin cờ trạng thái do chính nó ghi:
sau mỗi lần cắm, nó đọc lại file + registry và chỉ tô xanh thứ thật sự có mặt.

### 1.2 ZIP + BAT — không GUI, chạy Administrator

Tải `LTTStudios-CamCLI-BAT-1.1.0.zip`, giải nén **toàn bộ**, rồi bấm
`cam_cli_admin.bat`. Launcher tự xin UAC, che khoá khi nhập và cho chọn riêng:
`codex-cli`, `codex-vscode`, `claude-cli`, `claude-vscode`, `claude-desktop`.

Gói này mang console EXE thật. Đây là điểm quan trọng: GUI EXE dùng Windows GUI
subsystem nên `.bat` không nhận stdout/mã thoát đáng tin cậy; dùng nó làm CLI là
nguyên nhân bản cũ trông như chạy mãi không có kết quả.

### 1.3 Hướng dẫn thủ công

Không tải chương trình nào. Làm theo §2 dưới đây; mỗi bề mặt có base URL và tên
model riêng.

### CLI của gói ZIP

```text
LTTStudios-CamCLI-Console.exe xem
LTTStudios-CamCLI-Console.exe cam --muc codex-cli --muc claude-desktop
LTTStudios-CamCLI-Console.exe kiem
LTTStudios-CamCLI-Console.exe go
```

| Cờ | Khi nào dùng | Đánh đổi |
|---|---|---|
| `--muc codex-cli` | Codex CLI qua profile | an toàn nhất: mặc định Codex không đổi |
| `--muc codex-vscode` | tiện ích Codex VS Code | Codex khai ở **gốc** ⇒ thay luôn mặc định của lệnh `codex` |
| `--muc claude-cli` | Claude Code CLI | biến môi trường cấp người dùng |
| `--muc claude-vscode` | tiện ích Claude Code | ghi settings cấp người dùng, khoá vẫn ở biến môi trường |
| `--muc claude-desktop` | Claude Desktop | ghi chính sách HKCU, phải thoát hẳn app |
| `--toan-cuc` | tiện ích **Claude Code** | ghi `~/.claude/settings.json` ⇒ **mọi** phiên Claude Code trên máy đi qua LTT |

⚠️ **`--toan-cuc` chuyển hướng cả gói Anthropic thật của bạn.** Không phải mặc
định, và có cảnh báo ngay cạnh ô tích trong GUI. `go` trả lại đúng giá trị cũ.

---

## 2. Cấu hình tay, nếu không muốn dùng công cụ

### 2.1 Codex CLI — dạng **profile** (mặc định của bạn không đổi)

`~/.codex/config.toml`:
```toml
[model_providers.ltt]
name = "LTT Studios"
base_url = "https://app.lttstudios.com/api/v1"   # co /v1 - Codex ghep them /responses
env_key = "LTT_API_KEY"
wire_api = "responses"
stream_idle_timeout_ms = 600000
```

`~/.codex/ltt.config.toml` — **tệp riêng**, Codex 0.145+ từ chối `[profiles.ltt]`
nằm trong `config.toml`:
```toml
model = "ltt_llm"
model_provider = "ltt"
model_reasoning_effort = "low"
model_context_window = 65536
```

Chạy: `codex --profile ltt`

### 2.2 Tiện ích Codex (VS Code) — bắt buộc dạng **GỐC**

Tiện ích **không có cách truyền `--profile`**, và chọn profile từ tệp cũng không
được. Codex 0.145 từ chối thẳng:

```
Error: legacy `profile = "ltt"` config is no longer supported;
       use `--profile ltt` with `ltt.config.toml` instead
```

⇒ Phải đặt ở **gốc** `config.toml`:
```toml
model = "ltt_llm"
model_provider = "ltt"
model_reasoning_effort = "low"
model_context_window = 65536

[model_providers.ltt]
name = "LTT Studios"
base_url = "https://app.lttstudios.com/api/v1"
env_key = "LTT_API_KEY"
wire_api = "responses"
stream_idle_timeout_ms = 600000
```

⚠️ Dạng này **thay luôn mặc định** của lệnh `codex`. Không có cách nào được cả
hai — đó là giới hạn của Codex, không phải của chúng tôi.

### 2.3 Claude Code CLI — biến môi trường

```powershell
setx ANTHROPIC_BASE_URL "https://app.lttstudios.com/api"    # /api, KHONG /api/v1
setx ANTHROPIC_AUTH_TOKEN "<khoa ltt_sk_... cua ban>"
setx ANTHROPIC_MODEL "ltt_llm"
setx ANTHROPIC_DEFAULT_HAIKU_MODEL "ltt_llm"
```

⛔ **Hai địa chỉ lệch nhau bốn ký tự.** Codex khai `…/api/v1`, Claude khai
`…/api`. Đổi chỗ là nhận 404 mà không có manh mối nào khác.

### 2.4 Tiện ích Claude Code (VS Code) — `settings.json` cấp **người dùng**

Tiện ích **không đọc biến môi trường** như CLI (lỗi đã biết từ v2.0.0:
[#9010](https://github.com/anthropics/claude-code/issues/9010),
[#38430](https://github.com/anthropics/claude-code/issues/38430)).

`Ctrl+Shift+P` → **Preferences: Open User Settings (JSON)**:
```json
{
  "claudeCode.disableLoginPrompt": true,
  "claudeCode.environmentVariables": [
    {"name": "ANTHROPIC_BASE_URL", "value": "https://app.lttstudios.com/api"},
    {"name": "ANTHROPIC_MODEL", "value": "ltt_llm"}
  ]
}
```

⛔ **Phải là settings cấp NGƯỜI DÙNG.** `claudeCode.environmentVariables` khai
`scope: "machine"`; đặt trong `.vscode/settings.json` của một dự án thì VS Code
**bỏ qua, và không báo lỗi gì**.

⚠️ Tiền tố là `claudeCode.` (hoa chữ C). Nhiều bài viết trên mạng ghi
`claude-code.` — sai, và sai lặng lẽ.

⭐ **Khoá không đặt trong tệp này.** Để nó ở `ANTHROPIC_AUTH_TOKEN`;
tiến trình con của tiện ích vẫn kế thừa được. `settings.json` là tệp rất nhiều
người đồng bộ giữa máy hoặc commit vào kho dotfiles.

### 2.5 Claude Desktop — **chính sách registry** (Windows)

⭐ **Tự động hoá được**, khác với điều tài liệu này viết ở bản trước. Thiết lập
*chạy* của ứng dụng nằm trong LevelDB của Electron và không sửa tay được — nhưng
phần **suy luận bên thứ ba** đọc từ **chính sách hệ điều hành**: `.mobileconfig`
trên macOS, **registry** trên Windows. Đó là đường dành cho triển khai doanh
nghiệp và nó ổn định.

Lưu thành tệp `.reg` rồi bấm đúp:
```
Windows Registry Editor Version 5.00

[HKEY_CURRENT_USER\SOFTWARE\Policies\Claude]
"inferenceProvider"="gateway"
"inferenceGatewayBaseUrl"="https://app.lttstudios.com/api"
"inferenceGatewayApiKey"="<khoa ltt_sk_... cua ban>"
"inferenceGatewayAuthScheme"="bearer"
"inferenceModels"="[{\"name\": \"ltt-llm-claude-compat\"}]"
"modelDiscoveryEnabled"="false"
"chatTabEnabled"="true"
```

Hoặc để EXE/ZIP + BAT làm; cả hai đã bao gồm bước này.

---

### 2.5b 🔴 Vì sao ở đây tên model là `ltt-llm-claude-compat`, không phải `ltt_llm`

Đây là chỗ **im lặng nhất** trong cả tài liệu này, nên nói kỹ.

Claude Desktop ở chế độ `gateway` **lọc danh sách model trước khi vẽ picker**.
Luật đọc từ chính bản cài (`Claude 1.34493.1.0`, tệp
`app/resources/ion-dist/assets/v1/ce459c687-CEBp0mVy.js`) — **tài liệu công khai
không nói gì về nó**:

```js
Be = /…|gpt|gemini|glm|llama|minimax|mistral|qwen|…/     // CẤM
qe = ["claude", …tên dòng Claude…, "anthropic"]          // PHẢI chứa
Ke(t) = !Be.test(t) && (Ne.test(t) || qe.some(s => t.includes(s)))
```

`ltt_llm` không chứa chuỗi nào trong `qe` ⇒ bị **loại khỏi mảng** ⇒ picker rỗng.

⛔ **Triệu chứng khi sai — và nó không chỉ về phía nguyên nhân chút nào:**

| Bạn thấy | Sự thật |
|---|---|
| Gõ xong, bấm Enter — **không có gì xảy ra** | model rỗng nên nút gửi bị vô hiệu |
| Bấm nút gửi — con trỏ chỉ nhảy vào ô nhập | nháy chuột rơi xuyên qua nút đã tắt |
| **Không** log, **không** toast, **không** banner | ứng dụng không coi đây là lỗi |
| Ứng dụng vẫn hiện `Gateway` ở góc dưới trái | phần xác thực **đã** đúng |

⭐ **Cách phân biệt nhanh với lỗi khoá:** gọi thẳng API bằng đúng khoá trong
registry. Trả `200` mà ứng dụng vẫn im ⇒ **không phải khoá**, là bộ lọc tên.

⚠️ **`qwen` nằm trong danh sách CẤM.** Nên kể cả tên trung thực nhất
(`qwen3-27b`) cũng bị chặn thẳng. Không có cách nào lách bằng "đặt tên cho đúng
sự thật hơn".

**Vì sao chọn `ltt-llm-claude-compat` chứ không phải `claude-sonnet-4-5`:** luật
chỉ đòi tên **chứa** chuỗi `claude`; nó **không** đòi một model Anthropic có
thật. Nên cái tên này qua cổng mà không mượn tên sản phẩm của hãng khác. Nó là
**tên tuyến của một cổng tương thích**, không phải tên sản phẩm — thứ bạn mua vẫn
là `ltt_llm`, catalog và bảng giá vẫn chỉ nói `ltt_llm`, và model đứng sau vẫn là
model nhà.

Chốt bằng test: `tests/test_290_ten_tuyen_claude_desktop.py` chép nguyên luật lọc
từ bản cài và bắt lỗi nếu ai đó "dọn cho gọn" tên tuyến về `ltt_llm`.

---

### 2.5c 🔴 Rào chắn thứ hai: `chatTabEnabled`

Sửa xong tên model, picker đã hiện đúng, cấu hình đã `healthy` — **và vẫn không
gửi được gì**. Đây là một rào chắn **khác**, im lặng y hệt.

Mặc định bản triển khai bên-thứ-ba chỉ mở tab **Code** (tab Cowork bị mờ). Tab
Code **không nói thẳng với gateway**: nó mở một **phiên tác tử cục bộ**, và phiên
đó cần một runtime trên máy (`claude` / `node`). Máy khách không có thì ứng dụng
**không gửi gì cả**.

⛔ Đo trên VM sạch 25/08, sau khi tên model đã đúng:

| Bằng chứng | Giá trị |
|---|---|
| `ConfigHealth` trong log ứng dụng | `state: 'healthy', provider: 'gateway'` |
| Picker | hiện đúng `ltt-llm-claude-compat` |
| `claude` / `node` trên PATH | **không có** |
| Số request tới máy chủ sau khi bấm Enter | **0** |
| Dòng log của ứng dụng khi bấm Enter | **không có dòng nào** |

Bật `chatTabEnabled` xong thì hiện công tắc **Chat / Cowork** ngay trong ô soạn,
và lần gửi đầu tiên đi ngay: `8 × 7 = 56`, rồi `12 × 12 = 144`.

⭐ Vì sao đáng ghi lại: hai rào chắn này **cho cùng một triệu chứng** — bấm gửi,
không có gì xảy ra, không lời giải thích. Sửa xong cái thứ nhất mà vẫn im thì rất
dễ kết luận nhầm rằng bản sửa không ăn thua.

**Bốn chốt của tài liệu chính thức, đừng đoán lại:**

| | |
|---|---|
| `inferenceGatewayBaseUrl` | là **gốc**, ứng dụng tự ghép `/v1/messages`. Kèm sẵn `/v1` là thành `/v1/v1/messages` ⇒ 404 không manh mối |
| HTTPS | **bắt buộc** (trừ loopback) |
| Khởi động lại | cấu hình đọc **một lần lúc khởi động** ⇒ phải **thoát hẳn**, không phải chỉ đóng cửa sổ |
| `HKLM` đè `HKCU` | máy đã có chính sách ở `HKEY_LOCAL_MACHINE` thì ứng dụng **bỏ qua hoàn toàn** bản người dùng — cắm sẽ **vô tác dụng và không báo lỗi** |

Vẫn điền tay được nếu muốn: `Help → Troubleshooting → Enable Developer Mode`, rồi
`Developer → Configure Third-Party Inference…`

---

## 3. 🔴 Cái bẫy làm mất nhiều thời gian nhất

Triệu chứng: **`Missing environment variable: LTT_API_KEY`**, dù `xem` cho thấy
biến **đã đặt**.

⭐ **Đọc đúng thông điệp đó:** nó là bằng chứng cấu hình **ĐÚNG**. Codex đã đọc
được `config.toml` của bạn và đã đi tới bước tra `env_key`. Chỉ là môi trường
của tiến trình thiếu biến.

Vì `setx` ghi vào **registry** ngay, còn một phiên Windows **đang chạy** vẫn mang
môi trường cũ. Đo thật trên VM sạch 24/08:

| Đã thử | Kết quả |
|---|---|
| `setx` rồi mở lại VS Code | ❌ vẫn thiếu |
| Thêm khởi động lại `explorer.exe` | ❌ vẫn thiếu |
| **Đăng xuất rồi đăng nhập lại Windows** | ✅ `$env:LTT_API_KEY.Length` = 83 |

⚠️ Vì sao khởi động lại explorer **không đủ**: nếu bạn giết explorer rồi khởi
động nó từ một `cmd` do explorer **cũ** sinh ra, explorer mới **kế thừa đúng môi
trường cũ**. Một vòng luẩn quẩn không nhìn thấy được.

⇒ Mục **Trạng thái đo từ máy này** trong EXE, hoặc lệnh
`LTTStudios-CamCLI-Console.exe xem` trong gói ZIP, có riêng một mục cho việc này:

```
Tien trinh HIEN TAI co nhin thay khong:
  LTT_API_KEY            REGISTRY co, TIEN TRINH KHONG  <== dang xuat roi dang nhap lai
```

---

## 4. Bằng chứng đã chạy thật

| Bề mặt | Câu hỏi | Trả lời | Nơi |
|---|---|---|---|
| Codex CLI | `2+2` | `4` | máy A |
| Claude Code CLI | `2+2` | `4` | máy A |
| Claude Code CLI | `7×6` | `42` | **máy B** |
| Tiện ích Codex | `12×12` | **`144`** | VM sạch |
| Tiện ích Claude Code | `7×9` | **`7 x 9 = 63`** | VM sạch |

⭐ **Bằng chứng nó đi qua API của chúng tôi:** số dư credit `1041 → 1034`. Không
có tiền bị trừ thì không có gì chứng minh cả.

⭐ **Vì sao chạy trên máy B và VM mới có nghĩa:** máy A **là** máy chủ nền tảng và
có sẵn mọi đồ nghề. Một phép thử chỉ ở đó không loại trừ được giả thuyết *"nó
chạy vì đang ở nhà"*.

---

## 5. Ba lời hứa của công cụ, và giới hạn của từng cái

| Lời hứa | Mức | Ghi chú |
|---|---|---|
| `~/.codex/config.toml` trả về **bằng từng byte** sau `go` | ✅ chắc | mổ một khối có dấu mốc; giữ cả chú thích, thứ tự, dòng trắng, và **ký tự xuống dòng lẫn lộn** |
| `~/.claude/settings.json` và `settings.json` của VS Code | ⚠️ **nội dung** giống hệt, tệp được **định dạng lại** | JSON không có chú thích nên buộc phải parse để biết khoá nào của bạn |
| Khoá **không nằm trong tệp nào** | ✅ chắc | có test quét mọi tệp sau khi cắm |

⛔ Chúng tôi **không** hứa bằng-từng-byte cho JSON, và không nới test cho nó
xanh. Hứa một điều không giữ được thì tệ hơn không hứa.

---

## 6. Về `.exe` — không ký số

Chủ sản phẩm quyết 24/08: **không mua chứng chỉ ký số**. Nên lần chạy đầu Windows
sẽ hiện **"Windows protected your PC"** — bấm *More info → Run anyway*.

| | |
|---|---|
| SHA-256 | công bố cạnh đường tải, **đối chiếu trước khi chạy** |
| Windows Defender | quét sạch (đo 24/08, cả bản thư mục lẫn bản cài) |

⛔ **Chúng tôi không bao giờ bảo bạn tắt phần mềm diệt virus.** Nếu máy quét nào
báo, gửi chúng tôi tên máy quét — chúng tôi nộp báo cáo dương-tính-giả.

---

## 7. Tài liệu liên quan

| Tệp | Nội dung |
|---|---|
| [`KE_HOACH_GUI_CAM_CLI.md`](KE_HOACH_GUI_CAM_CLI.md) | vì sao chọn pywebview, vì sao **không** dựng máy chủ HTTP cục bộ |
| [`KE_HOACH_TEST_VM.md`](KE_HOACH_TEST_VM.md) | chín ca thử trên VM sạch + bốn lỗi chỉ VM tìm ra |
| [`../VLM_NOI_BO/LO_TRINH_API_CLI.md`](../VLM_NOI_BO/LO_TRINH_API_CLI.md) | lộ trình sáu đợt, và bài học từ `api.nghimmo.com` |
| `/developers/cli` | bản khách nhìn thấy, sinh cấu hình theo tài khoản |
