# Cắm Codex / Claude Code / Claude Desktop vào API của LTT Studios

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
| **Claude Desktop** | form **Configure Third-Party Inference**; tool dùng policy Windows cho cùng thông số | ✅ 1.52386.6, hai model trả lời thật ngày 14/09/2026 |

🔴 **Claude Desktop có HAI rào chắn riêng, và chúng cho CÙNG một triệu chứng:**
bấm gửi — không có gì xảy ra, không log, không toast, không banner.

| Rào chắn | Phải làm gì | Chi tiết |
|---|---|---|
| Bộ lọc tên model | mã tuyến phải chứa `claude`; picker hiện **LTT 3.8 (Mạnh)** / **LTT 3.5 (Nhanh)** bằng `labelOverride` | §2.5b |
| Giữ chế độ Claude.ai cũ | Workspace → **Disable Claude.ai sign-in** bật | §2.5 |
| Chỉ mở tab **Code** | Workspace → **Allow Chat** bật | §2.5 |

⚠️ Sửa xong cái thứ nhất mà vẫn im là chỗ rất dễ kết luận nhầm rằng bản sửa không
ăn thua. Đo thật 25/08: đã `healthy`, picker đã đúng, mà vẫn **0 request** tới máy
chủ. Công cụ `cam` đặt sẵn cả hai.

⛔ **"Cấu hình xong cho CLI" KHÔNG có nghĩa là tiện ích chạy được.** Hai tiện ích
VS Code đi đường xác thực khác hẳn CLI. Đây là chỗ mất nhiều thời gian nhất khi
thử thật, và nó không hiển nhiên từ tài liệu của nhà nào cả.

---

## 0b. HAI model: chọn mặc định cho CLI, chọn trực tiếp trong Desktop

| | `ltt-3.8` | `ltt-3.5` |
|---|---|---|
| Cửa sổ ngữ cảnh công bố | **124.245** token | **151.552** token |
| Ngưỡng client phải nén (Codex `auto_compact_token_limit`) | 91.477 | 118.784 |
| `CLAUDE_CODE_AUTO_COMPACT_WINDOW` (Claude tự trừ 33.000 ⇒ nén ở 91.245 / 118.552) | 124.245 | 151.552 |
| Trần token **ra** một lượt | 32.768 | 32.768 |
| Trần đầu vào thật ở cổng | 186.368 | 227.328 |
| Đọc ảnh | có | có |
| Vai trò khuyến nghị | **Mạnh** — phân tích/refactor dài | **Nhanh · tiết kiệm** — hỏi code/sửa nhỏ/tác vụ phụ |
| Tên trong picker Claude Desktop | **LTT 3.8 (Mạnh)** | **LTT 3.5 (Nhanh)** |
| Mã tuyến Desktop gửi | `ltt-llm-claude-compat` | `ltt-llm-claude-compat-35` |
| Giá | bảng riêng | bảng riêng |

🔴 **Hai cửa sổ này KHÔNG dùng chung được.** Khai số của model này cho model kia
là nói dối client về chỗ nó phải nén, và client **tin**: nó nén muộn, rồi bạn ăn
một `413` giữa phiên — im lặng, không manh mối nào chỉ về phía nguyên nhân.

⭐ Công cụ `cam` cài **cả hai profile và catalog Codex trong một lượt**; mỗi
profile giữ đúng cặp số của model đó. Lựa chọn `--model ltt-3.5` hoặc ô
**Model mặc định cho Claude Code** chỉ ghim Claude Code, alias và subagent.
Claude Desktop nhận **cả hai** tuyến trong `inferenceModels`, nên đổi ngay ở
picker mà không phải cắm lại. Codex CLI đổi bằng `--profile ltt` hoặc
`--profile ltt-fast`; Codex Desktop/VS Code đọc catalog hai model nhưng khả năng
hiện custom model trong picker phụ thuộc phiên bản client.

⚠️ Mọi đoạn cấu hình dưới đây viết cho `ltt-3.8` (mặc định). Dùng `ltt-3.5` thì đổi
**cả hai** thứ: tên model **và** con số cửa sổ ở cùng khối.

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
| Cửa sổ **engine** | 221.184 / 262.144 | LTT 3.8 / LTT 3.5; giải thích các số dưới |
| **Trần đầu vào** | 186.368 / 227.328 | máy chủ. Vượt là `413`, không bao giờ cắt lặng lẽ |
| **Cửa sổ công bố** | 124.245 / 151.552 | `model_context_window`, `CLAUDE_CODE_MAX_CONTEXT_TOKENS` |
| **Ngưỡng nén** | 91.477 / 118.784 | `auto_compact_token_limit` trong catalog Codex |
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
request_max_retries = 1
stream_max_retries = 0
stream_idle_timeout_ms = 600000
```

`~/.codex/ltt.config.toml` — **tệp riêng**, Codex 0.145+ từ chối `[profiles.ltt]`
nằm trong `config.toml`:
```toml
model = "ltt-3.8"
model_provider = "ltt"
model_reasoning_effort = "medium"
model_reasoning_summary = "none"
model_context_window = 124245
model_auto_compact_token_limit = 91477
model_catalog_json = 'C:\Users\<ban>\.codex\ltt_model_catalog.json'

[agents]
default_subagent_model = "ltt-3.8"
default_subagent_reasoning_effort = "medium"
max_concurrent_threads_per_session = 1
```

Chạy: `codex --profile ltt`

**Model thứ hai:** lưu thêm `~/.codex/ltt-fast.config.toml` với cùng mẫu, đổi
`model` và `default_subagent_model` thành `ltt-3.5`, đổi cả hai trường effort
thành `medium`, `model_context_window`
thành `151552`, `model_auto_compact_token_limit` thành `118784`.
Chạy `codex --profile ltt-fast`. Không chỉ đổi tên model mà giữ cửa sổ của 3.8.

**Cài lại để nhận số mới (R-13, từ 18/09):** chạy lại bộ cài (`cam` hoặc
`ltt_cai_dat_cli.py`) khi đã có `ltt.config.toml` / `ltt-fast.config.toml` thì
bộ cài **chỉ cập nhật khoá LTT sở hữu** (cửa sổ, ngưỡng nén, catalog, subagent,
…), giữ nguyên khoá, bảng, chú thích và kiểu xuống dòng của bạn; hai trường
effort là lựa chọn của bạn nên chỉ được thêm khi thiếu. Catalog
`ltt_model_catalog.json` là tệp của LTT nên được làm mới. Mọi tệp bị sửa có bản
sao lưu cạnh nó; tệp TOML hỏng thì bộ cài báo và không đụng tới.

`medium` trong profile 3.5 là **nhãn tương thích bắt buộc của Codex**, tương ứng
với **Thinking on**. Nó không có nghĩa Qwen3.5 sở hữu các mức
low/medium/high/xhigh. Catalog chỉ cho 3.5 đúng một lựa chọn này; 3.8 mới hiện
ba lựa chọn `low`, `medium`, `xhigh`. Để trống danh sách không tắt effort:
Codex 0.145.0 vẫn gửi `medium`, còn bỏ hẳn trường catalog làm Codex từ chối parse.

**Thứ tự nhập tay trên Windows, Codex CLI 0.145.0:**

1. Tạo khóa **live**, chọn `tools:read` và `jobs:create`, có credit và quyền model.
   Không chọn công cụ = mọi công cụ công khai đang mở; không chọn scope chỉ
   cấp quyền đọc mặc định. Khóa test trả mẫu, không kiểm được model thật.
2. Sao lưu cấu hình. Mở [Hướng dẫn API](https://app.lttstudios.com/huong-dan),
   chọn **Codex CLI**, mở JSON catalog và sao chép **toàn bộ** vào
   `~/.codex/ltt_model_catalog.json`. Catalog có metadata riêng cho cả hai model;
   `GET /api/v1/models` không phải định dạng catalog cục bộ này.
3. Thêm provider một lần vào `config.toml`; nếu đã có `model_providers.ltt`
   thì sửa khối hiện có. Lưu hai profile thành hai tệp riêng như trên.
4. Thay `<ban>` (trên trang là `YOUR_WINDOWS_USER`) bằng thư mục người dùng thật.
   Catalog phải tồn tại; đường dẫn **tuyệt đối**, không dùng `%USERPROFILE%`
   vì TOML không tự thay biến Windows. macOS/Linux dùng đường dẫn tuyệt đối tương ứng.
5. Nhập khóa có che trong PowerShell, rồi chạy Codex trong **cùng cửa sổ**:

```powershell
$env:LTT_API_KEY = [System.Net.NetworkCredential]::new(
    '', (Read-Host 'LTT API key' -AsSecureString)).Password
codex --profile ltt
# Or: codex --profile ltt-fast
```

Không ghi khóa vào TOML/catalog hay lệnh `setx` có thể lưu vào lịch sử. Trong
phiên mới, `/status` kiểm model/provider; hỏi
`Calculate 6 * 7. Reply with only the number.`, cần nhận `42`. Đối chiếu Logs/Usage
để biết đúng model và credit; lặp lại bằng profile còn lại.

Từ Tool 1.9.2, lệnh `kiem` gọi thật `/api/v1/responses` bằng **cả hai** slug
`ltt-3.8` và `ltt-3.5`, ngoài các lượt Claude `/messages`. Vì vậy trạng thái
"Cắm được" nay xác nhận đúng tuyến Codex; một cấu hình chỉ parse được nhưng
endpoint Responses lỗi sẽ không còn bị báo xanh.

Từ Tool 1.9.3, **một lần cắm Codex luôn ghi cả hai profile** ở trên và catalog
hai model. Ô chọn model trong Tool chỉ chọn mặc định cho Claude Code; nó không
loại model nào khỏi Codex. Chế độ Desktop/VS Code đặt LTT 3.8 làm mặc định ban
đầu, còn catalog vẫn công bố cả LTT 3.8 và LTT 3.5 cho client.

[OpenAI Docs — custom providers và profiles](https://developers.openai.com/codex/config-advanced/)
cho phép cấu hình provider Responses, `env_key` và profile. Đã đối chiếu CLI
**0.145.0** trên máy, không tự nâng phiên bản. Codex Desktop đang cài
**26.721.11231.0** chưa được xác minh có bảng Gateway như Claude; không dùng ô
**OpenAI API key** hay mục **MCP/Connectors** để nhập khóa LTT.

🔴 **`model_catalog_json` không phải tuỳ chọn.**

Thiếu nó, Codex cảnh báo *"Model metadata for `ltt-3.8` not found"* rồi rơi vào
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
công bố hiện tại là **124.245 / 151.552**, xem §0b. Codex có thể hiển thị phần
cửa sổ hiệu dụng sau khi chừa biên riêng; không dùng số hiển thị đó thay cho
metadata công bố và ngưỡng nén theo model.

Tệp catalog do công cụ `cam` ghi ra; nếu cấu hình tay thì lấy mẫu ở
**<https://app.lttstudios.com/huong-dan>**, chọn Codex CLI.

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
model = "ltt-3.8"
model_provider = "ltt"
model_reasoning_effort = "medium"
model_context_window = 124245
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
setx ANTHROPIC_MODEL "ltt-3.8"
setx ANTHROPIC_DEFAULT_MODEL "ltt-3.8"
setx ANTHROPIC_DEFAULT_HAIKU_MODEL "ltt-3.8"
setx ANTHROPIC_DEFAULT_OPUS_MODEL "ltt-3.8"
setx ANTHROPIC_DEFAULT_SONNET_MODEL "ltt-3.8"
setx ANTHROPIC_DEFAULT_FABLE_MODEL "ltt-3.8"
setx CLAUDE_CODE_SUBAGENT_MODEL "ltt-3.8"
setx CLAUDE_CODE_MAX_CONTEXT_TOKENS "124245"
setx CLAUDE_CODE_AUTO_COMPACT_WINDOW "124245"
setx CLAUDE_CODE_MAX_OUTPUT_TOKENS "32768"
setx MAX_MCP_OUTPUT_TOKENS "16384"
setx CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS "1"
setx CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH "1"
setx CLAUDE_CODE_SUBAGENT_MODEL_FORCE "1"
setx CLAUDE_CODE_MAX_RETRIES "10"
setx API_TIMEOUT_MS "600000"
setx CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK "1"
setx ENABLE_TOOL_SEARCH "false"
```

⛔ **Hai địa chỉ lệch nhau bốn ký tự.** Codex khai `…/api/v1`, Claude khai
`…/api`. Đổi chỗ là nhận 404 mà không có manh mối nào khác.

🔴 Đây là **khối đầy đủ**, không phải danh sách gợi ý. Nếu dùng `ltt-3.5`, hãy
đổi cả bảy dòng model sang `ltt-3.5`, context thành `151552` và compact thành
`151552`; chín dòng vận hành còn lại giữ nguyên. Bảng giải thích và danh sách
biến không được thêm nằm trong [ma trận cấu hình chuẩn](CLAUDE_CONFIG_MATRIX.md).

Claude Code không biết `ltt-3.8`, nên nó **giả định cửa sổ 200.000 token** và
nói thẳng ra điều đó:

```
"ltt-3.8" is not a model this version of Claude Code recognizes, so
auto-compact will keep this session within 200k tokens (the context
window it assumes).
```

Trần đầu vào thật là **186.368**. Với giả định 200k, auto-compact **không bao giờ
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
    {"name": "ANTHROPIC_MODEL", "value": "ltt-3.8"},
    {"name": "ANTHROPIC_DEFAULT_MODEL", "value": "ltt-3.8"},
    {"name": "ANTHROPIC_DEFAULT_HAIKU_MODEL", "value": "ltt-3.8"},
    {"name": "ANTHROPIC_DEFAULT_OPUS_MODEL", "value": "ltt-3.8"},
    {"name": "ANTHROPIC_DEFAULT_SONNET_MODEL", "value": "ltt-3.8"},
    {"name": "ANTHROPIC_DEFAULT_FABLE_MODEL", "value": "ltt-3.8"},
    {"name": "CLAUDE_CODE_SUBAGENT_MODEL", "value": "ltt-3.8"},
    {"name": "CLAUDE_CODE_MAX_CONTEXT_TOKENS", "value": "124245"},
    {"name": "CLAUDE_CODE_AUTO_COMPACT_WINDOW", "value": "124245"},
    {"name": "CLAUDE_CODE_MAX_OUTPUT_TOKENS", "value": "32768"},
    {"name": "MAX_MCP_OUTPUT_TOKENS", "value": "16384"},
    {"name": "CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS", "value": "1"},
    {"name": "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH", "value": "1"},
    {"name": "CLAUDE_CODE_SUBAGENT_MODEL_FORCE", "value": "1"},
    {"name": "CLAUDE_CODE_MAX_RETRIES", "value": "10"},
    {"name": "API_TIMEOUT_MS", "value": "600000"},
    {"name": "CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK", "value": "1"},
    {"name": "ENABLE_TOOL_SEARCH", "value": "false"}
  ]
}
```

🔴 Danh sách này phải đi cùng nhau. Hai biến context/compact ngăn client vượt
cửa sổ; các pin model giữ mọi alias và agent trên LTT; các giới hạn còn lại
chặn retry, fan-out và fallback non-streaming đã gây lỗi trong phiên dài.

⛔ **Phải là settings cấp NGƯỜI DÙNG.** `claudeCode.environmentVariables` khai
`scope: "machine"`; đặt trong `.vscode/settings.json` của một dự án thì VS Code
**bỏ qua, và không báo lỗi gì**.

⚠️ Tiền tố là `claudeCode.` (hoa chữ C). Nhiều bài viết trên mạng ghi
`claude-code.` — sai, và sai lặng lẽ.

⭐ **Khoá không đặt trong tệp này.** Để nó ở `ANTHROPIC_AUTH_TOKEN`;
tiến trình con của tiện ích vẫn kế thừa được. `settings.json` là tệp rất nhiều
người đồng bộ giữa máy hoặc commit vào kho dotfiles.

### 2.5 Claude Desktop — cắm tay trong ứng dụng 1.52386.6

Đối chiếu ngày **14/09/2026** với bản đang cài trên máy này, hai ảnh cấu hình của
chủ sản phẩm, [gateway reference của Claude](https://claude.com/docs/third-party/claude-desktop/gateway)
và [model configuration](https://claude.com/docs/third-party/claude-desktop/configuration#models).
Tool 1.9.2 dùng cùng cấu hình chuẩn; cắm tay là một đường được hỗ trợ thêm, dùng cùng API và cùng
mã tuyến. **Không phải tải tool, thêm proxy hay sửa registry để đi theo đường này.**

#### Chuẩn bị khóa LTT

1. Đăng nhập LTT Studios và mở **Khóa API** tại `/developers/keys`.
2. Tạo khóa **live**, còn hạn; bật `tools:read` và `jobs:create`. Hai scope này
   cho phép tra cứu và gọi inference; tài khoản cần có credit và quyền dùng model.
3. Sao chép khóa khi nó hiện một lần. Khóa thử ở chế độ sandbox không thay cho
   khóa live khi muốn model thực sinh câu trả lời.

#### Mở cấu hình và bảo toàn Gateway hiện có

1. Menu **☰ → Help → Troubleshooting → Enable Developer Mode**.
2. Mở **Developer → Configure Third-Party Inference**.
3. Bấm tên cấu hình ở góc trên phải → **New configuration**, đặt tên **LTT Studios**.
   Profile Gateway khác được giữ trong danh sách; không chép khóa của dịch vụ khác
   sang LTT. Nếu đã có profile LTT thì chọn profile đó để sửa.
4. Chọn **Connection → Gateway**. Trong **Credential kind**, chọn **Static API key**.

Nếu giao diện hiện **Organization-managed** hoặc trường bị khóa, cấu hình đang do
policy/MDM quản lý. Phải gỡ cấu hình LTT đã cắm bằng tool qua nút **Gỡ ra** trước
khi chuyển sang profile thủ công; nếu policy do tổ chức khác quản lý thì nhờ người
quản lý thay đổi. Form không thể ghi đè một policy đang có hiệu lực.

#### Bảng điền Connection

| Trường trên Claude | Giá trị cho LTT |
|---|---|
| Connection | **Gateway** |
| Credential kind | **Static API key** |
| Gateway base URL | `https://app.lttstudios.com/api` |
| Gateway API key | Khóa live LTT của bạn; dán vào ô được che |
| Gateway auth scheme | **Bearer** |
| Artifact preview iframe origin | Để trống, dùng mặc định của Claude |
| Custom inference headers | Để trống |
| Stream idle timeout | **600** giây |
| Model discovery | **Off** |
| Default to 1M context | **Off** |
| Show estimated cost | **Off** |

Không thêm `/v1` vào URL: Claude tự nối `/v1/messages`. Scheme Bearer tạo header
`Authorization: Bearer …`, đúng với xác thực LTT. Không cần helper script,
Organization UUID, OIDC, địa chỉ localhost hoặc header bổ sung cho cấu hình này.

**401 khi chọn x-api-key:** header này khác `Authorization: Bearer …`. Backend
LTT hiện chỉ nhận Bearer (xem `server/api/deps.py::bearer_token`). Ngày 15/09,
owner thử cùng khóa trên form: x-api-key trả 401, đổi Bearer thì Test connection
xanh. Không cần tạo lại khóa; không liên quan giới hạn công cụ hay số token.

#### Cửa sổ token khi dùng Code trên Desktop

Tắt **Default to 1M context** và **Offer 1M-context variant** cho cả hai model.
Đây là khai báo khả năng 1M, không phải nút cấp thêm bộ nhớ. **Tắt 1M không tự
đặt cửa sổ 124K:** trước khi thêm môi trường Local, UI Automation ngày 15/09
đọc được `Usage: Context 48.1k / 200k (24%)`; ảnh 24/28 sau khi thêm môi trường
hiện `46.8k / 138.7k`, rồi `99.6k / 138.7k` và tự nén ở 76% — đó là preset CŨ
(`AUTO_COMPACT_WINDOW=138690`, nén sớm 33K, R-05); preset 18/09-21/09 hiện
`/ 171.5k`; preset hiện tại (từ 22/09, L-35) hiện `/ 124.2k`.
Form `inferenceModels` bản 1.52386.6 không có trường nhập cửa sổ token tùy ý.

Nếu đang trong hội thoại Code và không thấy ô môi trường: bấm **New** ở thanh
bên trái, mở màn hình tạo phiên. UI Automation đã xác minh nút **Local** hiện
trong vùng soạn màn hình này; không hiện trong khung soạn phiên đang chạy ở ảnh 21.
Mở danh sách môi trường, rê vào **Local** rồi bấm bánh răng.

Trong **Code → Environment dropdown → Local → gear**, chép nguyên khối **11
dòng** sau rồi mở **phiên Local mới**. Đây là danh sách chuẩn đầy đủ cho Claude
Desktop 1.52386.6 / Claude Code 2.1.270 với LTT Gateway, không phải một nhóm gợi
ý để ghép thêm vào danh sách cũ:

| Biến | Giá trị dùng chung an toàn khi chuyển hai model |
|---|---:|
| `CLAUDE_CODE_MAX_CONTEXT_TOKENS` | `124245` |
| `CLAUDE_CODE_AUTO_COMPACT_WINDOW` | `124245` |
| `CLAUDE_CODE_MAX_OUTPUT_TOKENS` | `32768` |
| `MAX_MCP_OUTPUT_TOKENS` | `16384` |
| `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` | `1` |
| `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` | `1` |
| `CLAUDE_CODE_SUBAGENT_MODEL_FORCE` | `1` |
| `CLAUDE_CODE_MAX_RETRIES` | `10` |
| `API_TIMEOUT_MS` | `600000` |
| `CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK` | `1` |
| `ENABLE_TOOL_SEARCH` | `false` |

| Preset môi trường | `MAX_CONTEXT` | `AUTO_COMPACT` | Dấu hiệu đúng trong Context |
|---|---:|---:|---|
| LTT 3.8, hoặc đổi qua lại hai model | 124.245 | 124.245 | `… / 124.2k`, `Autocompact buffer 33k`, nén ở 91.245 (~73%) |
| Chỉ LTT 3.5 | 151.552 | 151.552 | `… / 151.6k`, `Autocompact buffer 33k`, nén ở 118.552 (~78%) |

Cặp dùng chung lấy model hẹp nhất là **LTT 3.8**: LTT 3.5 nén sớm hơn khả năng
của nó nhưng không bị khai dư cửa sổ. UI chuyển model không tự đổi các biến.
Không dùng preset 3.5 rồi chuyển sang 3.8. Không bật `DISABLE_COMPACT`,
`DISABLE_AUTO_COMPACT` hoặc
`CLAUDE_CODE_DISABLE_UNKNOWN_MODEL_WINDOW_ENFORCEMENT` để bỏ lớp bảo vệ.

Ba biến agent giải quyết ba việc khác nhau: `MAX_CONCURRENT_SUBAGENTS=1` chỉ cho
một agent phụ chạy đồng thời; `MAX_SUBAGENT_SPAWN_DEPTH=1` cấm agent phụ sinh
thêm tầng; `SUBAGENT_MODEL_FORCE=1` mà **không** đặt `SUBAGENT_MODEL` trong môi
trường Desktop ép agent phụ kế thừa đúng model chính đang chọn trong picker.
Đây là hành vi chính thức từ Claude Code 2.1.257; bản đang cài là 2.1.270.

Không thêm `CLAUDE_CODE_DISABLE_1M_CONTEXT`,
`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`, `MAX_THINKING_TOKENS`,
`CLAUDE_CODE_ALWAYS_ENABLE_EFFORT`, `CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY`,
hoặc `CLAUDE_STREAM_IDLE_TIMEOUT_MS`. Chúng hoặc dư với hai mã
LTT không có hậu tố `[1m]`, ghi đè ngưỡng đã tính, có thể đổi chất lượng suy
luận, hoặc trùng trường **Stream idle timeout = 600 seconds** trong Gateway.

> ⚠️ **`AUTO_COMPACT_WINDOW` là CỬA SỔ, không phải ngưỡng** (R-05, đo 18/09). Claude Code
> nén ở `min(AUTO_COMPACT_WINDOW, cửa sổ) − min(MAX_OUTPUT_TOKENS, 20.000) − 13.000`.
> Đo thật Claude Code 2.1.274 trỏ về LTT: `/context` in `Autocompact buffer 33k` ở mọi
> cửa sổ; khớp mã client và tài liệu (cửa sổ 1M nén “at about 967K” = 1M − 33K).
> Trước 18/09 ta khai 138.690 ⇒ Claude nén ở 105.690 (76 %), sớm 33.000 token so với
> Codex. Giá trị đúng = cửa sổ công bố (124.245 / 151.552, hạ 22/09 — L-35, chia
> `HE_SO_UOC_TREN_THAT`) ⇒ nén ở 91.245 / 118.552, ≤ ngưỡng Codex (91.477 / 118.784).
> Nguồn: `HoSoModel.cua_so_nen_claude` trong hai bộ cài;
> `tests/test_1440_nen_claude_tach_codex.py`.

Ảnh 28 cũ (`… / 138.7k`, `Compacts automatically at 76%`) là dấu hiệu của cấu
hình **trước 18/09**: nén sớm 33.000 token, không phải hành vi mong muốn.

Kiểm `/context` hoặc vòng Usage trong phiên mới: phải thấy cửa sổ đã điều chỉnh;
nếu còn 200K thì cấu hình chưa có hiệu lực. `/autocompact 124245` là cách chọn
ngưỡng qua lệnh nếu bản engine hỗ trợ; `/compact` chủ động trước khi đọc tệp lớn.
Biến Local theo tài liệu áp dụng cho **Code local sessions**; chưa nghiệm thu
việc chúng điều khiển Chat/Cowork trên bản này. Với Chat, dùng hội thoại mới và
chia nhỏ tài liệu; không coi kết quả Chat ngắn là chứng minh nén phiên dài.

Claude gửi ngữ cảnh đã nạp: system instructions, lịch sử, nội dung tệp/tool,
schema công cụ và ảnh — không gửi cố định 200K hoặc 1M ở mỗi lượt. Output và
reasoning còn phải có chỗ trong cửa sổ engine. Tokenizer Claude/Qwen khác nhau;
biên hiện tại và tiền kiểm của LTT vẫn cần thiết. Một kết quả tool lớn có thể
làm vượt trần trong cùng lượt, trước lần kiểm nén kế tiếp.

#### Lỗi `Invalid request` sau nhiều tool call

Ngày 15/09, ảnh 27 ghi đủ lỗi thật: Claude gửi một request `stream=false` ước
98.678 token đầu vào; cửa JSON của LTT không còn chỗ sinh output trong ngân sách
90 giây nên trả 400 trước khi gọi model. Đây không phải 413 và không phải cửa sổ
138.7K sai.

[Tài liệu biến môi trường của Claude](https://code.claude.com/docs/en/env-vars)
định nghĩa `CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK=1` cho đúng trường hợp
gateway/proxy: nếu stream hỏng, lỗi đi về tầng retry thay vì đổi sang request
non-streaming. Báo cáo cộng đồng
[#88110](https://github.com/anthropics/claude-code/issues/88110) mô tả cùng đường
stream lỗi → retry `stream:false`; [#40316](https://github.com/anthropics/claude-code/issues/40316)
ghi nhận retry có thể làm phiên dài phình thêm.

Ảnh 28 đồng thời đo 131 MCP tools chiếm khoảng 65K token. Claude giải thích rằng
[Tool Search](https://code.claude.com/docs/en/mcp#scale-with-mcp-tool-search) tự
tắt khi `ANTHROPIC_BASE_URL` trỏ tới host ngoài, vì nhiều proxy không chuyển được
`tool_reference`. LTT hiện chưa triển khai khối đó, nên giữ
`ENABLE_TOOL_SEARCH=false`, tắt Connector/Plugin không dùng và cố giữ dòng MCP
tools dưới khoảng 10% cửa sổ nén (khoảng 13,9K với preset 3.8).
`MAX_MCP_OUTPUT_TOKENS` chỉ giới hạn **kết quả một tool**; nó không làm nhỏ schema
của 131 tool.

#### Chế độ quyền trên Claude Desktop

| Mode | Hành vi với LTT Gateway |
|---|---|
| Ask permissions | Hỏi trước khi sửa tệp hoặc chạy lệnh. |
| Accept edits | Tự nhận sửa tệp và vài thao tác filesystem; vẫn hỏi lệnh terminal khác. |
| Auto | Không khả dụng với third-party provider; vắng mục này không phải lỗi LTT. |
| Bypass permissions | Không hỏi quyền. Bật **Settings → Claude Code → Allow bypass permissions mode**, rồi chọn Bypass trước câu đầu của phiên Local mới. |

Nếu đổi Bypass trong phiên đã chạy và gặp *Permission mode couldn't be changed*,
tạo phiên Local mới. Nếu phiên mới vẫn không có Bypass, kiểm
`permissions.disableBypassPermissionsMode` có giá trị `"disable"` ở user,
project hoặc managed settings. `settings.json` cấp quyền tool không tự làm hiện
Bypass khi công tắc Desktop chưa bật.

Hệ thống đã có tiền kiểm theo model, trần body/input/output, admission theo
suất **và pool token**, phòng chờ hữu hạn, SSE heartbeat và nhả giữ chỗ khi
client ngắt. 413 là request quá dài; 429 là hạn mức/công suất. Ba suất không có
nghĩa ba request 170K cùng chạy: các suất chia sẻ pool KV của mỗi model, lượt
dài có thể làm lượt khác phải chờ. Không tăng context, concurrency hoặc retry
chỉ để làm hết thông báo lỗi.

**Tài liệu đọc ngày 15/09/2026:**
[Claude Code — context và custom gateway window](https://code.claude.com/docs/en/model-config#correct-the-window-for-a-gateway-or-custom-model-id),
[Environment variables và non-streaming fallback](https://code.claude.com/docs/en/env-vars),
[MCP Tool Search](https://code.claude.com/docs/en/mcp#scale-with-mcp-tool-search),
[Desktop — Local environment editor](https://code.claude.com/docs/en/desktop#local-sessions),
[Desktop — permission modes](https://code.claude.com/docs/en/desktop#choose-a-permission-mode),
[Desktop configuration — Models](https://claude.com/docs/third-party/claude-desktop/configuration#models).
Các báo cáo cộng đồng [#68522](https://github.com/anthropics/claude-code/issues/68522),
[#16033](https://github.com/anthropics/claude-code/issues/16033),
[#88110](https://github.com/anthropics/claude-code/issues/88110) và
[#40316](https://github.com/anthropics/claude-code/issues/40316) là bằng chứng
người dùng báo cáo, không thay thế phép thử phiên dài của LTT trên đúng bản cài.

#### Thêm hai model

Ở **Model list**, bấm **Add** hai lần. Mở mũi tên ở đầu mỗi dòng để điền:

| Thứ tự | Model ID | Display name |
|---|---|---|
| 1 — mặc định | `ltt-llm-claude-compat` | **LTT 3.8 (Mạnh)** |
| 2 | `ltt-llm-claude-compat-35` | **LTT 3.5 (Nhanh)** |

Trong từng dòng, để **Offer 1M-context variant** tắt. Đặt **Tier alias** của
LTT 3.8 là `opus`, của LTT 3.5 là `haiku`, rồi bật **Default for tier** ở cả hai.
Đây là ánh xạ nội bộ mà Claude Desktop dùng để chuyển alias và tác vụ nền về
đúng tuyến gateway; nó không đổi Display name và không tuyên bố model LTT là
model Anthropic. Hai mã Model ID vẫn là tuyến tương thích của backend LTT.

**Tắt discovery là có chủ ý:** `/api/v1/models` công bố tên sản phẩm `ltt-3.8` và
`ltt-3.5`; bộ lọc Desktop hiện không nhận các tên đó. Danh sách cố định giữ đúng
hai tuyến tương thích và đúng nhãn. Vì thế không cần bổ sung catalog giả mang tên
Claude vào hệ thống chỉ để cắm tay.

#### Bật Chat, lưu và khởi động lại

1. Mở **Workspace**: bật **Allow Chat** và **Disable Claude.ai sign-in**.
   Chúng tương ứng `chatTabEnabled=true` và `disableDeploymentModeChooser=true`,
   giúp app mở Chat và dùng Gateway thay cho lựa chọn Claude.ai đã lưu trước đó.
2. Quay về **Connection**, bấm **Test connection**. Đợi kết quả đạt; nếu báo lỗi,
   xử lý theo bảng dưới trước khi gửi câu hỏi thật.
3. Bấm **Apply Changes → Relaunch now** (hoặc **Save & Restart** nếu app hỏi).
   **Save Changes** riêng chỉ lưu profile, chưa áp nó vào phiên đang mở.
4. Nếu model cũ còn hiện, **thoát hẳn Claude**, kể cả tiến trình ở khay hệ thống,
   rồi mở lại. Chọn **Chat** trong ô soạn.

#### Kiểm vận hành từng model

| Model chọn trong picker | Câu hỏi | Kết quả cần thấy |
|---|---|---|
| LTT 3.8 (Mạnh) | `Calculate 8 * 7. Reply with only the number.` | `56` |
| LTT 3.5 (Nhanh) | `Calculate 12 * 12. Reply with only the number.` | `144` |

Mở cuộc trò chuyện mới cho mỗi phép thử; kiểm tên ở picker trước khi bấm gửi.
Sau đó mở **Logs/Usage** trong cổng API LTT để đối chiếu lượt gọi và credit.
**Test connection** xanh là kiểm kết nối; hai câu trả lời là kiểm inference.

Ngày 14/09/2026, tài khoản thường thử nghiệm đã gọi thực tế Messages, Responses,
tool call và tool result cho **cả hai** tuyến, rồi Claude Desktop 1.52386.6 đã chọn
và trả lời đúng `56`/`144` sau khi tắt/mở hoàn toàn. Khóa tạm đã thu hồi. Lượt này
cắm bằng tool; hướng dẫn cắm tay được đối chiếu với schema form cùng phiên bản,
không được ghi nhận thành một lượt nhập form thủ công đã chạy.

#### Lỗi thường gặp và giới hạn

| Hiện tượng | Việc kiểm tra |
|---|---|
| 404 | URL phải kết thúc ở `/api`; không dùng `/api/v1` trong form Desktop |
| 401 | Bearer, khóa LTT còn hạn/chưa thu hồi, không dán khóa Gateway khác |
| 403 | Khóa có `jobs:create`, tài khoản có quyền model; `tools:read` cho tra cứu |
| 402 | Credit hoặc hạn mức chi tiêu của khóa/tài khoản |
| Không có model | Discovery tắt; khai đúng hai Model ID và Display name |
| Vẫn hiện model cũ | Apply Changes, thoát hẳn và mở lại; kiểm profile đang áp |
| Bấm gửi không có request | Allow Chat bật, chọn Chat, Gateway đang có hiệu lực |
| 429/công suất đang bận | Đợi theo Retry-After; không gửi lặp nhiều cửa sổ |
| 400 `context_window_exceeded` / "prompt is too long" (ngữ cảnh quá dài) | Cuộc trò chuyện mới hoặc giảm nội dung; không bật 1M |
| 413 `request_body_too_large` (thân request quá lớn) | Bớt tệp/ảnh đính kèm; đây không phải lỗi ngữ cảnh |
| Chỉ có suy nghĩ, thiếu câu trả lời | Không giảm ngân sách đầu ra quá nhỏ; suy nghĩ cũng tiêu token |

Không công bố hỗ trợ prompt caching Anthropic, USD theo bảng giá Anthropic, 1M
context hay toàn bộ chức năng Cowork/Code chỉ từ lượt smoke Chat. LTT thu credit
theo token sinh thực tế; giá chuẩn nằm ở `/gia-api`. Artifact preview để trống dùng
renderer mặc định của Claude, không phải một endpoint cần xây trên LTT.

Tài liệu cộng đồng của chính gateway
[Stratoclave](https://github.com/littlemex/stratoclave/blob/main/docs/COWORK_INTEGRATION.md)
cũng mô tả đường nhập form và lỗi URL có `/v1`.
[Issue model picker](https://github.com/anthropics/claude-code/issues/52526)
cho thấy tên hiển thị từng lệch trên phiên bản cũ; hướng dẫn này dùng **Display name**
từ schema 1.52386.6. Các nguồn cộng đồng là đối chiếu kinh nghiệm, không thay bằng
bằng chứng vận hành LTT. Claude mô tả gateway cho model Claude; tương thích giao
thức LTT không đồng nghĩa Anthropic chứng nhận model Qwen.

#### Quay về Gateway khác hoặc Claude.ai

Mở lại cửa sổ cấu hình, chọn profile trước đó và **Apply Changes**, rồi mở lại app.
Muốn Claude.ai thì tắt **Disable Claude.ai sign-in** và chọn đăng nhập Claude.ai.
Thu hồi khóa LTT khi thôi dùng. Nút **Gỡ ra** của tool chỉ quản lý policy do tool
cắm; profile nhập tay được quản lý trong Claude Desktop.

### 2.5d Chính sách registry — tùy chọn tự động hóa Windows

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
"inferenceModels"="[{\"name\":\"ltt-llm-claude-compat\",\"labelOverride\":\"LTT 3.8 (Mạnh)\"},{\"name\":\"ltt-llm-claude-compat-35\",\"labelOverride\":\"LTT 3.5 (Nhanh)\"}]"
"modelDiscoveryEnabled"=dword:00000000
"chatTabEnabled"=dword:00000001
"disableDeploymentModeChooser"=dword:00000001
"inferenceStreamIdleTimeoutSec"=dword:00000258
```

Hoặc để EXE/ZIP + BAT làm; cả hai đã bao gồm bước này.

---

### 2.5b 🔴 Vì sao tên hiển thị và mã tuyến là hai trường khác nhau

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

`ltt-3.8` không chứa chuỗi nào trong `qe` ⇒ bị **loại khỏi mảng** ⇒ picker rỗng.
(`qwen` còn nằm trong danh sách **cấm**, nên cả tên trung thực nhất cũng bị chặn.)

⚠️ **Mỗi model có tên tuyến riêng.** `ltt-3.8` đi qua
`ltt-llm-claude-compat`; `ltt-3.5` đi qua `ltt-llm-claude-compat-35`. Cấu hình
phát **cả hai**, đồng thời dùng `labelOverride` để picker hiện đúng hai tên sản
phẩm dễ hiểu: **LTT 3.8 (Mạnh)** và **LTT 3.5 (Nhanh)**. Mã tuyến chỉ là trường
giao thức gửi về gateway và không cần xuất hiện như tên sản phẩm.

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

**Vì sao giữ mã tuyến `ltt-llm-claude-compat*`:** luật chỉ đòi trường `name`
**chứa** chuỗi `claude`; nó không đòi một model Anthropic có thật. Hai mã này đã
được production nhận và nói rõ đây là cổng tương thích, không mượn tên sản phẩm
của hãng khác. Desktop 1.52386.6 có trường `labelOverride` dành riêng cho chữ
hiện trong picker, nên không cần thêm alias backend chỉ để có nhãn đẹp.

Chốt bằng test: `tests/test_290_ten_tuyen_claude_desktop.py` chép nguyên luật lọc
từ bản cài và bắt lỗi nếu ai đó "dọn cho gọn" tên tuyến về tên sản phẩm.

---

### 2.5c 🔴 Hai rào chế độ: `disableDeploymentModeChooser` và `chatTabEnabled`

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
| Picker | hiện đủ **LTT 3.8 (Mạnh)** và **LTT 3.5 (Nhanh)** |
| `claude` / `node` trên PATH | **không có** |
| Số request tới máy chủ sau khi bấm Enter | **0** |
| Dòng log của ứng dụng khi bấm Enter | **không có dòng nào** |

Bản 1.52386.6 còn giữ lựa chọn `deploymentMode=1p` của lần dùng Claude.ai trước.
Khi đó registry gateway có đủ mà app vẫn ở model Anthropic. Đặt
`disableDeploymentModeChooser=1` buộc chế độ 3p; bật `chatTabEnabled=1` thì hiện
công tắc **Chat / Cowork** ngay trong ô soạn,
và lần gửi đầu tiên đi ngay: `8 × 7 = 56`, rồi `12 × 12 = 144`.

⭐ Vì sao đáng ghi lại: hai rào chắn này **cho cùng một triệu chứng** — bấm gửi,
không có gì xảy ra, không lời giải thích. Sửa xong cái thứ nhất mà vẫn im thì rất
dễ kết luận nhầm rằng bản sửa không ăn thua.

**Bốn chốt của tài liệu chính thức, đừng đoán lại:**

| | |
|---|---|
| `inferenceGatewayBaseUrl` | là **gốc**, ứng dụng tự ghép `/v1/messages`. Kèm sẵn `/v1` là thành `/v1/v1/messages` ⇒ 404 không manh mối |
| HTTPS | **bắt buộc**, kể cả loopback theo schema 1.52386.6; dùng URL HTTPS công khai của LTT |
| Khởi động lại | cấu hình đọc **một lần lúc khởi động** ⇒ phải **thoát hẳn**, không phải chỉ đóng cửa sổ |
| `HKLM` đè `HKCU` | máy đã có chính sách ở `HKEY_LOCAL_MACHINE` thì ứng dụng **bỏ qua hoàn toàn** bản người dùng — cắm sẽ **vô tác dụng và không báo lỗi** |

Đường nhập tay trên phiên bản đang dùng được mô tả đầy đủ ở §2.5. Phần policy
này dành cho tool và triển khai được quản lý, không cần chép `.reg` khi nhập form.

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
| 2 | `~/.codex/` | xoá `ltt.config.toml`, `ltt-fast.config.toml` và `ltt_model_catalog.json` |
| 3 | biến môi trường cấp người dùng | Toàn bộ biến trong khối §2.3: `ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`, bảy pin model `ANTHROPIC_*`/`CLAUDE_CODE_SUBAGENT_MODEL`, mười biến vận hành `CLAUDE_CODE_*`/`MAX_MCP_OUTPUT_TOKENS`/`ENABLE_TOOL_SEARCH`, và `LTT_API_KEY` của Codex |
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
