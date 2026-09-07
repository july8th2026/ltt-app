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

Tải bản mới nhất ở **<https://app.lttstudios.com/tai/cong-cu-cam>** — đường dẫn
**cố định**, luôn trả bản mới nhất, và SHA-256 công bố ngay cạnh nút tải được
tính từ chính tệp đang phục vụ. Cài không cần Administrator, rồi chọn từng bề
mặt ngay trong cửa sổ. Công cụ không tin cờ trạng thái do chính nó ghi: sau mỗi
lần cắm nó đọc lại file + registry và chỉ tô xanh thứ **thật sự** có mặt.

🔴 **Một ngoại lệ về quyền — và nó là lý do một mục hay báo hỏng.**

Mục **Claude Desktop** ghi vào `HKCU\SOFTWARE\Policies\Claude`, tức nhánh Group
Policy. ACL đo trên máy thật:

```
DESKTOP-…\<ban>          Allow  ReadKey        <- chi DOC
BUILTIN\Administrators   Allow  FullControl    <- ghi duoc
```

⇒ Với riêng mục đó phải mở công cụ bằng lối tắt **"(Administrator — chỉ cần cho
Claude Desktop)"** trong Start Menu. **Bốn mục còn lại không cần quyền quản
trị** — đừng chạy cả công cụ bằng admin nếu không cần.

Từ **1.3.0** công cụ hỏi quyền **trước khi ghi**, và nếu thiếu thì nói thẳng lý
do (`WinError 5: Access is denied`) rồi **không ghi gì cả**. Bản trước đó thất
bại bảy lần liên tiếp và in ra những dòng trông y hệt dòng thành công.

### 1.2 ZIP + BAT — không GUI, chạy Administrator

Tải ở **<https://app.lttstudios.com/tai/cong-cu-cam-bat>**, giải nén
**toàn bộ**, rồi bấm
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

### 2.0 Năm con số, và cái nào đi vào tệp nào

Mọi thứ dưới đây quay quanh **năm** con số. Chúng khác nhau, và mỗi lần dự án
này gộp hai trong số chúng thì kết quả là một lời hứa sai.

| Con số | Giá trị | Ai cần biết |
|---|---:|---|
| Cửa sổ **engine** | 204.800 | không ai — nó chỉ giải thích các số dưới |
| **Trần đầu vào** | 169.984 | máy chủ. Vượt là `413`, không bao giờ cắt lặng lẽ |
| **Cửa sổ công bố** | 156.385 | `model_context_window`, `CLAUDE_CODE_MAX_CONTEXT_TOKENS` |
| **Ngưỡng nén** | 123.617 | `auto_compact_token_limit` trong catalog Codex |
| **Token ra tối đa** | 32.768 | `CLAUDE_CODE_MAX_OUTPUT_TOKENS` |

🔴 **Ngưỡng nén không phải một tỉ lệ tròn, và chỗ này đã trả giá thật.**

Cho tới 03/09 bộ cài đặt ngưỡng nén ở `0,8 × cửa sổ`. Nghe hợp lý, và sai: client
chỉ kiểm ngưỡng **giữa hai lượt**, nên sau khi nó quyết định "chưa cần nén", lượt
kế tiếp vẫn được phép lớn thêm **trọn một lượt trả lời nữa** trước lần kiểm sau.

Với `0,8` thì khoảng trống từ ngưỡng nén lên cửa sổ công bố nhỏ hơn một lượt trả
lời dài nhất — nên cấu hình ấy **không thể** giữ lời hứa. Đo được trên
production: một lượt `POST /api/v1/responses` ăn `413` ở **101.938** token vào
trên trần **96.256** khi đó.

⇒ Quy tắc đúng: **ngưỡng nén = cửa sổ công bố − token ra tối đa**. Nếu bạn tự
đặt con số, hãy giữ đúng khoảng cách ấy.

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
model_context_window = 156385
model_catalog_json = 'C:\Users\<ban>\.codex\ltt_model_catalog.json'
```

Chạy: `codex --profile ltt`

🔴 **`model_catalog_json` không phải tuỳ chọn.**

Thiếu nó, Codex cảnh báo *"Model metadata for `ltt_llm` not found"* rồi rơi vào
đường `compact_model_fallback`: nó **mượn tên một model của OpenAI** cho các lượt
phụ (đặt tên phiên, nén hội thoại). Cổng của chúng tôi từ chối tên lạ theo thiết
kế fail-closed, nên bạn thấy hội thoại dài **im lặng** mà không có lỗi rõ ràng.

Đo được 30/08, cùng một phiên, chỉ khác việc có khai catalog hay không:

| | cảnh báo metadata | `model_context_window` của phiên |
|---|---|---|
| không catalog | **có** | 84.127 |
| có catalog | **không** | **79.699** = 88.555 × 90 % |

79.699 đúng bằng con số **chúng tôi** khai, tức Codex đã đọc tệp và thôi phải
đoán. Số lượt 400 sau đó về **0**.

⚠️ Bảng trên là **một phép đo ngày 30/08**, không phải cấu hình hiện tại. Cửa sổ
công bố khi ấy là 88.555; từ 03/09 nó là **156.385** (cửa sổ engine lên
204.800), nên con số Codex hiển thị bây giờ là **140.746 = 156.385 × 90 %**.
Tỉ lệ 90 % là thứ không đổi, và đó mới là điều bảng này chứng minh.

Tệp catalog do công cụ `cam` ghi ra; nếu cấu hình tay thì lấy mẫu ở
**<https://app.lttstudios.com/huong-dan/cong-cu>**.

⚠️ **Khai đường dẫn tới một tệp KHÔNG tồn tại thì Codex `failed to parse
model_catalog_json` rồi TỪ CHỐI KHỞI ĐỘNG** — bạn biến một cảnh báo vô hại thành
một lỗi chặn đường. Có tệp rồi mới khai.

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
model_context_window = 156385
model_catalog_json = 'C:\Users\<ban>\.codex\ltt_model_catalog.json'

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
setx CLAUDE_CODE_MAX_CONTEXT_TOKENS "156385"
setx CLAUDE_CODE_MAX_OUTPUT_TOKENS "32768"
```

⛔ **Hai địa chỉ lệch nhau bốn ký tự.** Codex khai `…/api/v1`, Claude khai
`…/api`. Đổi chỗ là nhận 404 mà không có manh mối nào khác.

🔴 **Hai dòng cuối không phải tinh chỉnh — thiếu chúng là bạn mất tiền.**

Claude Code không biết `ltt_llm`, nên nó **giả định cửa sổ 200.000 token** và
nói thẳng ra điều đó:

```
"ltt_llm" is not a model this version of Claude Code recognizes, so
auto-compact will keep this session within 200k tokens (the context
window it assumes).
```

Trần đầu vào thật là **169.984**. Với giả định 200k, auto-compact **không bao giờ
nén kịp**: hội thoại vượt trần từ lâu mà client vẫn tưởng còn nửa đường, và bạn
ăn **413** giữa chừng. A/B đo 30/08: đặt `CLAUDE_CODE_MAX_CONTEXT_TOKENS` thì
cảnh báo trên biến mất.

⚠️ Đừng dùng `modelOverrides` cho việc này. Đọc mô tả trong chính binary của
Claude Code: nó là **ánh xạ tên model**, cửa sổ vẫn lấy theo model ID của
Anthropic. Nó không giải bài này.

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
    {"name": "ANTHROPIC_MODEL", "value": "ltt_llm"},
    {"name": "ANTHROPIC_DEFAULT_HAIKU_MODEL", "value": "ltt_llm"},
    {"name": "CLAUDE_CODE_MAX_CONTEXT_TOKENS", "value": "156385"},
    {"name": "CLAUDE_CODE_MAX_OUTPUT_TOKENS", "value": "32768"}
  ]
}
```

🔴 Hai dòng `CLAUDE_CODE_MAX_*` là **bắt buộc**, vì đúng lý do đã ghi ở §2.3:
thiếu chúng thì tiện ích giả định cửa sổ 200.000, không nén kịp, và bạn ăn 413
giữa hội thoại.

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

## 2.6 Gỡ ra — trả máy về nguyên trạng

Đây là mục **hay bị bỏ qua nhất**, và bỏ qua nó thì ngày bạn muốn quay về tài
khoản ChatGPT/Anthropic của mình sẽ rất khó chịu.

### Bằng công cụ

```text
LTTStudios-CamCLI-Console.exe go          # go ra
LTTStudios-CamCLI-Console.exe go --sach   # go, va xoa luon cac ban sao luu
```

Hoặc bấm **"Gỡ ra"** trong cửa sổ công cụ.

⭐ **Nút gỡ KHÔNG cần khoá API và KHÔNG cần lần cắm trước.** Đó là chủ ý: lúc bạn
bấm gỡ chính là lúc bạn thôi dùng dịch vụ — bạn không còn cầm khoá nữa, và bắt
bạn dán lại khoá để gỡ là vô lý. Công cụ nhận diện cấu hình của chúng tôi bằng
**dấu vân tay trên máy**, không phải bằng một sổ ghi có thể mất khi bạn cài lại
máy, đổi tài khoản Windows hay đồng bộ thư mục nhà.

⭐ Gỡ xong nó **tự quét lại** và in ra còn sót gì. Sạch thì nó nói
`[OK] Da quet lai: khong con dau vet nao`. Công cụ không đánh dấu xanh giả.

### Nếu gỡ tay — **năm** nơi, không phải một

| # | Nơi | Xoá gì |
|---|---|---|
| 1 | `~/.codex/config.toml` | khối giữa `# >>> LTT Studios …` và `# <<< LTT Studios <<<`, **và** bảng `[model_providers.ltt]` nếu nó nằm ngoài khối đó |
| 2 | `~/.codex/` | xoá tệp `ltt.config.toml` và `ltt_model_catalog.json` |
| 3 | biến môi trường cấp người dùng | `ANTHROPIC_BASE_URL`, `ANTHROPIC_MODEL`, `ANTHROPIC_DEFAULT_HAIKU_MODEL`, `CLAUDE_CODE_MAX_CONTEXT_TOKENS`, `CLAUDE_CODE_MAX_OUTPUT_TOKENS`, `ANTHROPIC_AUTH_TOKEN`, `LTT_API_KEY` |
| 4 | `~/.claude/settings.json` và `%APPDATA%\Code\User\settings.json` | các khoá `ANTHROPIC_*` và các mục `claudeCode.environmentVariables` trỏ về `app.lttstudios.com` |
| 5 | `HKCU\SOFTWARE\Policies\Claude` | cả khoá — **cần quyền quản trị** |

⛔ **Chỗ số 1 là chỗ đã thực sự làm khách hỏng.** Bảng `[model_providers.ltt]`
có thể nằm **ngoài** cặp dấu mốc, nên một lần gỡ chỉ bóc phần trong mốc sẽ để
lại nó — kèm `env_key = "LTT_API_KEY"` trỏ vào một khoá đã chết. Bản 1.3.0 cắt
cả hai.

*(Nhưng nếu bảng đó do **bạn** tự khai thì công cụ giữ nguyên: nó chỉ cắt khi
mọi cặp khoá/giá trị khớp đúng bản công cụ sinh ra. "Xoá những gì trông giống
của ta" và "xoá đúng những gì ta đã thêm" là hai việc khác nhau.)*

⚠️ **`setx` không xoá được biến.** Dùng
`REG delete "HKCU\Environment" /v TEN /f` rồi **đăng xuất và đăng nhập lại
Windows**. Mở lại VS Code là **không đủ**: Explorer đang chạy vẫn trao môi
trường **cũ** cho mọi thứ bạn mở từ Start Menu.

### Các tệp `*.truoc-ltt`

Công cụ sao lưu **bản đầu tiên** của mỗi tệp nó chạm vào, đặt tên
`<ten>.truoc-ltt`. Đó là **cấu hình của bạn**, không phải của chúng tôi, nên
`go` **không tự xoá**. Muốn xoá luôn thì `go --sach`.

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
