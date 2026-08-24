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
| **Claude Desktop** | LevelDB nội bộ — **chỉ cấu hình tay** | ⏳ chưa |

⛔ **"Cấu hình xong cho CLI" KHÔNG có nghĩa là tiện ích chạy được.** Hai tiện ích
VS Code đi đường xác thực khác hẳn CLI. Đây là chỗ mất nhiều thời gian nhất khi
thử thật, và nó không hiển nhiên từ tài liệu của nhà nào cả.

---

## 1. Cách nhanh nhất: dùng công cụ

```
LTTStudios-CamCLI-Setup-1.0.0.exe      cai (khong can quyen admin)
LTTStudios-CamCLI.exe xem              xem dang cam gi
LTTStudios-CamCLI.exe cam --khoa ltt_sk_... --vscode --toan-cuc
LTTStudios-CamCLI.exe kiem             goi that mot luot
LTTStudios-CamCLI.exe go               go ra, tra ve nguyen trang
```

| Cờ | Khi nào dùng | Đánh đổi |
|---|---|---|
| *(không cờ)* | chỉ dùng **CLI** | an toàn nhất: mặc định của khách **không đổi** |
| `--vscode` | dùng **tiện ích VS Code** | Codex khai ở **gốc** ⇒ thay luôn mặc định của lệnh `codex` |
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

### 2.5 Claude Desktop — chỉ cấu hình tay

`Help → Troubleshooting → Enable Developer Mode`, rồi
`Developer → Configure Third-Party Inference…`

| | |
|---|---|
| Gateway base URL | `https://app.lttstudios.com/api` |
| Gateway auth scheme | `Bearer` |
| Gateway API key | khoá `ltt_sk_…` của bạn |
| inferenceModels | `ltt_llm` |

⛔ Không tự động hoá được: ứng dụng cất cấu hình trong LevelDB của Electron, sửa
tay là hỏng lặng lẽ ở lần cập nhật sau.

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

⇒ `LTTStudios-CamCLI.exe xem` có riêng một mục cho việc này:

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
