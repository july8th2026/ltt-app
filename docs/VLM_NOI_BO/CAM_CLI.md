# Cắm Codex CLI và Claude Code vào model nhà

**2026-08-23.** Nghiên cứu từ tài liệu chính thức + **đo thật trên máy B**, không phỏng đoán.

---

## 0. Hai con đường, và chúng khác nhau nhiều hơn vẻ ngoài

| | **Đường A — LAN, tới thẳng máy B** | **Đường B — qua API công khai** |
|---|---|---|
| Địa chỉ | `http://192.168.2.66:8299` | `https://app.lttstudios.com/api/v1` |
| Khoá | bearer token của cổng VLM | khoá khách `ltt_sk_…` |
| Ai dùng được | máy trong nhà — **hôm nay tường lửa chỉ mở cho 192.168.2.17**; mở thêm ở §8.0 | bất kỳ ai có khoá |
| Tính tiền | **không** | có |
| `/v1/responses` (Codex) | ✅ **đang chạy** | ❌ chưa có |
| `/v1/messages` (Claude Code) | ✅ **đang chạy** | ❌ chưa có |
| Luồng SSE | ✅ | ❌ chế độ `STREAM` chưa mở |
| Dùng được hôm nay | **có** *(sau khi sửa CUDA — xem §5)* | không |

Phần lớn tài liệu này nói về **đường A**, vì đó là đường chạy được. §6 nói cần
gì để mở đường B.

---

## 1. Sự thật đã ĐO, không phải đọc được

Đo ngày 23/08/2026 trên cổng VLM máy B (`llm_gateway` 0.1.0, `llama-server` b10580):

| Đo cái gì | Kết quả |
|---|---|
| `POST /v1/responses` (Codex) | ✅ `200` — llama-server tự dịch Responses → Chat |
| `POST /v1/messages` (Claude Code) | ✅ `200` |
| SSE trên `/v1/messages` | ✅ đúng chuẩn Anthropic: `message_start` · `content_block_start` · 61 × `content_block_delta` · `content_block_stop` · `message_delta` · `message_stop` |
| Đường Codex thật sự gọi | `base_url` + **`/responses`** — xác nhận trong log cổng |
| **Prompt hệ thống của Codex** | **~21.936 token MỖI LƯỢT** |
| `GET /v1/models` | ✅ `200` |
| `POST /v1/messages/count_tokens` | ❌ `404` — Claude Code **tự lùi** về đếm qua endpoint suy luận, không hỏng |
| `GET /api/hello` (thăm dò khởi động của Claude Code) | ❌ `404` — vô hại, tài liệu cho phép từ chối |

### Đo lại **sau khi sửa CUDA** (16:0x, máy B đã khởi động lại sạch)

| Đo cái gì | Trên CPU (hỏng) | **Trên GPU (đã sửa)** |
|---|---|---|
| `llama-server --list-devices` | `(none)` | **`CUDA0: RTX 3090, 23.335 MiB free`** |
| Tốc độ sinh | — | **67,6 tok/s** |
| VRAM khi nạp | 1.153 MiB | **19.838 MiB** |
| **Thời gian tới token đầu tiên, prompt 22k** | **> 10 phút, không ra chữ** | **15,7 giây** |
| Nghiệm thu cổng (`kiem_tra.ps1`) | — | **19/19 ĐẠT** |
| Chốt P6 (card bẩn 23.713 MiB) | — | **69,6 tok/s — không tụt** |

**Codex chạy thật, đầu-tới-cuối:** `codex exec` trả lời đúng trong **14 giây**,
12.592 token. Cùng câu lệnh đó trước khi sửa CUDA thì **treo tới hết 7 phút**.

**Claude Code — thử đúng hình dạng nó gửi** (mảng `system`, hai `tools`, header
`anthropic-version` + `anthropic-beta` + `x-claude-code-session-id`, streaming):

```
event: message_start · content_block_start ×2 · content_block_delta ×34
     · content_block_stop ×2 · message_delta · message_stop
"type":"tool_use"  "name":"Read"     "stop_reason":"tool_use"
```

Model gọi đúng tool và dừng bằng `stop_reason: "tool_use"` — đúng thứ vòng lặp
agent của Claude Code cần để đi tiếp. Header `anthropic-beta` qua nguyên xi.

⚠️ **Codex có cảnh báo, không chặn:** *"Model metadata for `qwen38-api` not found.
Defaulting to fallback metadata; this can degrade performance and cause issues."*
Codex không biết năng lực của một model lạ nên dùng số mặc định. Chạy vẫn tốt;
chỉ nghĩa là các con số nó tự suy (nén ngữ cảnh, ước chi phí) sẽ không chính xác.

---

## 2. 🔴 Cái bẫy lớn nhất: cả hai CLI đặt đồng hồ trên KHOẢNG LẶNG

Đây là thứ làm hỏng việc cắm CLI, và nó không hiện ra trong bất kỳ phép thử
`curl` ngắn nào.

| CLI | Đồng hồ | Mặc định |
|---|---|---|
| Codex | `stream_idle_timeout_ms` | **300.000 ms** |
| Claude Code | đếm **từng byte** cổng chuyển tiếp, kể cả sự kiện `ping` **và dòng chú thích** | bỏ luồng sau **300 giây** im lặng |

Mà `llama-server` **không phát gì trong lúc prefill**. Với prompt hệ thống
~22.000 token, cộng một lần `llama-swap` đổi model, khoảng lặng đó rất dễ chạm
trần.

**Đã thấy tận mắt, không phải lo xa:**

```
14:18:25  cong nhan  /v1/responses  token_vao~21936
   (im lang)
14:23:27  cong nhan  /v1/responses  token_vao~21936     <- cach dung 300 giay
```

Codex không hỏng. Nó làm đúng thứ nó nói sẽ làm.

**Đã sửa** — `llm_gateway/nhip_tim.py` chèn một **dòng chú thích SSE** mỗi 15
giây khi luồng lặng (`LTT_LLM_NHIP_TIM_S`, mặc định 15, đặt 0 để tắt).

> ⭐ **Vì sao chú thích chứ không phải sự kiện `ping`.** Chú thích (`: keep-alive`)
> được **đặc tả SSE bảo đảm là bỏ qua**, nên nó an toàn cho cả ba giao thức cổng
> phục vụ. Sự kiện `ping` chỉ hợp lệ ở giao thức Anthropic, và gửi nó **trước**
> `message_start` là đặt cược vào việc client dễ tính. Chú thích mang đủ byte để
> giữ đồng hồ mà không giả vờ là một sự kiện giao thức.

---

## 3. Codex CLI

### 3.1 Cấu hình

🔴 **TỪ CODEX 0.145, PROFILE PHẢI Ở FILE RIÊNG.** Viết `[profiles.ltt]` vào
`config.toml` sẽ bị **từ chối thẳng**:

```
Error loading config.toml: --profile `ltt` cannot be used while
...\.codex\config.toml contains legacy `profile = "ltt"` or `[profiles.ltt]`
config; move those settings into ...\.codex\ltt.config.toml
```

Khối `[model_providers.ltt]` thì **vẫn ở `config.toml`** — nó không phải profile.
Hai file, hai việc:

**`~/.codex/config.toml`** — thêm vào, **không đổi gì ở trên**. `model` mặc định
của bạn giữ nguyên, nên `codex` trần vẫn dùng model cũ:

```toml
[model_providers.ltt]
name = "LTT Studios (may B)"
base_url = "http://192.168.2.66:8299/v1"   # PHAI co /v1 - Codex ghep them /responses
env_key = "LTT_LLM_TOKEN"
wire_api = "responses"                      # gia tri DUY NHAT tu 02/2026
stream_idle_timeout_ms = 600000
```

**`~/.codex/ltt.config.toml`** — hồ sơ, file riêng:

```toml
model = "qwen38-api"
model_provider = "ltt"
model_reasoning_effort = "low"
model_reasoning_summary = "none"
model_context_window = 65536
```

Đặt khoá **một lần, ở cấp người dùng** (không phải `$env:` trong một terminal —
tiện ích VS Code sẽ không thấy):

```powershell
setx LTT_LLM_TOKEN "<bearer token cong VLM>"
```

Rồi **mở lại** VS Code / terminal, và chạy:

```powershell
codex --profile ltt
```

### 3.2 Vì sao từng dòng có ở đó

| Dòng | Lý do |
|---|---|
| `base_url` kết thúc bằng `/v1` | Codex ghép thêm **`/responses`**. Đã xác nhận trong log cổng, tài liệu chính thức **không** nói rõ chỗ này. |
| `wire_api = "responses"` | Từ 02/2026 đây là **giá trị duy nhất** Codex hỗ trợ. Một backend chỉ nói Chat Completions thì phải có bộ dịch đứng giữa — `llama-server` **tự làm** việc đó, nên ta không cần. |
| `env_key` | Codex đọc **biến môi trường**, không đọc khoá đặt thẳng trong file. Thế là đúng: khoá không đi theo file cấu hình vào git. |
| `model_reasoning_effort = "low"` | 🔴 Đo thật: ở mức mặc định, model tiêu **gần hết `max_tokens` vào phần `thinking`** trước khi kịp trả lời. Một câu hỏi "thủ đô Việt Nam?" hết 40 token mà chưa ra chữ nào. |
| `model_context_window = 65536` | Hồ sơ `qwen38-api` mở 64K. Khai đúng để Codex tự nén hội thoại **trước khi** đâm vào trần, thay vì ăn `400`. |

### 3.3 Ngân sách ngữ cảnh — con số quyết định mọi thứ

```
cua so                      65.536 token
− prompt he thong cua Codex ~21.936        <- MOI LUOT, khong the bo
= con lai cho viec that     ~43.600 token
```

**Hai phần ba cửa sổ còn lại cho mã và hội thoại.** Với một dự án nhỏ thì đủ; với
một phiên agent dài thì không. Đó chính là lý do hồ sơ **`qwen38-ops` (200K)**
tồn tại — nhưng nó **chưa được mở** (`LTT_LLM_MODELS` hiện chỉ có
`qwen38-api, qwen38-vision`), và mở nó sẽ nuốt thêm VRAM. Xem §5.

---

### 3.4 Tiện ích Codex trong VS Code

Tiện ích **dùng chung đúng `config.toml`** với CLI: bánh răng → *Codex Settings*
→ *Open config.toml*. Cấu hình ở §3.1 phục vụ cả hai, không phải làm hai lần.

⚠️ **Một cái bẫy đã từng có, và tôi không chứng minh được nó đã hết.** Lỗi
[openai/codex#4558](https://github.com/openai/codex/issues/4558) (và bản trùng
[#6963](https://github.com/openai/codex/issues/6963)): tiện ích **không nhận**
model provider tự khai, rơi về `gpt-5` và báo *"Invalid LLM id"*. Cả hai đã đóng,
và bản cài trên máy này (`openai.chatgpt@26.818.41705`) mới hơn bản báo lỗi
(0.4.15) rất nhiều — nhưng "đã đóng" không phải là "đã đo".

**Cách kiểm trong ba mươi giây:** mở bộ chọn model của tiện ích. Thấy
`qwen38-api` là xong. Không thấy thì dùng lối vòng ghi trong chính issue đó —
**mở phiên bằng CLI rồi tiếp tục nó trong tiện ích**:

```powershell
codex --profile ltt
```

⚠️ Chạy thử 23/08 có thêm nhiễu **không liên quan tới model nhà**: các MCP plugin
đi kèm Codex (`visualize`, `documents`, `pdf`, `spreadsheets`) trả `HTTP 401
token_invalidated` vì chúng xác thực với OpenAI. Câu trả lời vẫn về đúng. Nếu
không dùng, tắt chúng cho log sạch.

## 4. Claude Code (CLI trong terminal)

> ⚠️ **KHÔNG phải Claude Desktop.** Hai thứ này cấu hình theo hai đường hoàn toàn
> khác nhau: CLI đọc **biến môi trường** `ANTHROPIC_BASE_URL`; Desktop **không
> đọc biến đó** mà dùng cửa sổ *Third-Party Inference* riêng của nó. Xem §8.2.

### 4.1 Cấu hình

```powershell
$env:ANTHROPIC_BASE_URL  = "http://192.168.2.66:8299"
$env:ANTHROPIC_AUTH_TOKEN = "<bearer token cua cong VLM>"
$env:ANTHROPIC_MODEL      = "qwen38-api"
$env:ANTHROPIC_DEFAULT_HAIKU_MODEL = "qwen38-api"
claude
```

Hoặc bền hơn, trong `~/.claude/settings.json`:

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "http://192.168.2.66:8299",
    "ANTHROPIC_AUTH_TOKEN": "<bearer token>",
    "ANTHROPIC_MODEL": "qwen38-api",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "qwen38-api"
  }
}
```

### 4.2 Vì sao từng biến có ở đó

| Biến | Lý do |
|---|---|
| `ANTHROPIC_BASE_URL` | **Không** có `/v1` ở cuối — Claude Code tự ghép `/v1/messages`. Ngược với Codex. |
| `ANTHROPIC_AUTH_TOKEN` | Gửi khoá ở `Authorization: Bearer`. Cổng ta đọc đúng header đó. `ANTHROPIC_API_KEY` gửi ở `x-api-key`, mà **cổng ta không đọc header đó** — dùng nhầm biến là `401`. |
| `ANTHROPIC_MODEL` | 🔴 **Bắt buộc.** Không đặt thì Claude Code gửi `claude-…`, và cổng ta trả `404` vì tên đó không có trong danh mục. |
| `ANTHROPIC_DEFAULT_HAIKU_MODEL` | 🔴 **Cũng bắt buộc, và rất dễ quên.** Claude Code dùng model "haiku" cho **việc nền** (tóm tắt, đặt tên phiên…). Bỏ trống thì mọi việc nền `404` âm thầm. |

### 4.3 Những chỗ Claude Code sẽ hụt, và mức độ nghiêm trọng

| Chỗ hụt | Hậu quả | Nặng? |
|---|---|---|
| `/v1/messages/count_tokens` → `404` | Claude Code **tự lùi** về đếm ngữ cảnh qua endpoint suy luận | nhẹ |
| `GET /api/hello` → `404` | thăm dò khởi động, tài liệu cho phép từ chối | không |
| **Khám phá model** (`GET /v1/models`) | Claude Code chỉ giữ những `id` **chứa chữ `claude` hoặc `anthropic`**. `qwen38-api` không khớp ⇒ danh sách rỗng | nhẹ — đã đặt `ANTHROPIC_MODEL` tay rồi |
| **Tên model trong phản hồi** | Cổng trả nguyên `H:/LTT_LLM/models/Qwen3.8-27B-UD-Q4_K_M.gguf` | nhẹ ở LAN, **chặn đường B** — xem §6 |
| **Đồng thời** | Cổng chỉ cho **2 lượt cùng lúc** (`LTT_LLM_MAX_DONG_THOI`). Claude Code chạy subagent song song ⇒ ăn `429` | ⚠️ vừa — xem dưới |
| `anthropic-beta` | Cổng chuyển tiếp **nguyên xi** vì nó không đọc thân request. Đúng thứ tài liệu đòi | không |

**Về đồng thời.**

⛔ **ĐOẠN NÀY ĐÃ LẠC HẬU — SỬA 13/09/2026.** Bản trước viết: *"`llama-server`
chạy `--parallel 1`, nên yêu cầu thứ ba không chạy song song… đó là hạng mục
**V7**, chưa làm."*

**V7 đã làm.** `--parallel 1` đã bị gỡ (`llm_gateway/deploy/llama-swap.yaml:151`
— cổng G2 bác lý lẽ *"speculative decoding tối ưu một luồng"*). Máy B nay phục
vụ hai model trên hai card, mỗi model nhiều suất, có **hàng đợi thật** ở
`platform_core/llm/phong_cho.py`: quá suất thì **xếp hàng và nhận nhịp báo chờ**,
không còn là "một kết nối treo".

🔑 Số suất hiện hành hỏi `apps/ltt_llm/ngan_sach.py`; đường đi một lượt đọc
`docs/ltt_llm_dual/BAN_DO_DUONG_DI.md`. **Đừng gõ lại số vào đây.**

---

## 5. ~~🔴 Sự cố đang chặn tất cả~~ — ✅ ĐÃ SỬA 23/08 bằng một lần khởi động lại sạch

Phát hiện trong lúc đo, 23/08 ~14:30. **Không phải lỗi của cấu hình CLI.**

```
llama-server.exe --list-devices
  ggml_cuda_init: failed to initialize CUDA: (null)
  Available devices:
    (none)
```

Bằng chứng đi kèm:

| Dấu hiệu | Số đo |
|---|---|
| `llama-server.exe` đang chạy | giữ **23 GB RAM CHỦ** |
| GPU | **1.153 MiB / 24.576**, tải **3 %** |
| `nvidia-smi` | chạy tốt, driver **610.88** — NVML không sao, hỏng ở **CUDA driver API** |
| Máy B khởi động lại | **13:16 → 13:19 hôm nay** |
| Sự kiện Windows | `1074` (13:16:37) → **`41` + `6008`** (13:19) = **tắt KHÔNG SẠCH** |

Nghĩa là: model **đang chạy trên CPU**, và llama.cpp **không báo lỗi** — nó chỉ
lặng lẽ rơi về CPU. Một lượt prefill 22k token trên CPU vượt xa mọi trần chờ;
đó là vì sao phép đo "thời gian tới token đầu tiên" chạy **10 phút không ra chữ**.

Nhả model rồi nạp lại **không sửa được** — CUDA vẫn không khởi tạo. Đây là trạng
thái dai dẳng sau lần tắt bẩn, không phải sự cố thoáng qua.

✅ **Cách sửa: khởi động lại sạch.** Sau `Restart-Computer` lúc 16:01,
`--list-devices` thấy card ngay, và cả bốn dịch vụ tự lên đúng thứ tự (kể cả
chuỗi phụ thuộc `LTTComfyUI` → `LTTRenderGateway`). Không phải cài lại driver.

⚠️ **ComfyUI chết cùng một nguyên nhân**, và đó là bằng chứng độc lập thứ hai:

```
Windows fatal exception: access violation
  torch/cuda/__init__.py line 529 in _lazy_init
```

Hai stack khác nhau — PyTorch và llama.cpp — cùng một CUDA hỏng. Nếu chỉ thấy
một trong hai, rất dễ đi sửa nhầm ứng dụng.

⚠️ **Ghi lại cho lần sau:** triệu chứng của "CUDA rơi về CPU" là **chậm**, không
phải **lỗi**. `/health` xanh, `llama-swap` báo `state: ready`, mọi lượt gọi trả
`200`. Chốt duy nhất nhìn ra được là **VRAM**. Đây đúng là họ hàng của bài học P6
(card bẩn ⇒ 18 tok/s thay vì 63, không lỗi nào báo), chỉ nặng hơn một bậc.

---

## 6. Cần gì để mở đường B (bán ra ngoài)

Hôm nay `/api/v1` chỉ có `POST /chat/completions` (chế độ `SYNC_BILLED`, Q106).
Cắm được CLI qua khoá khách cần **bốn** thứ, và ba trong số đó là quyết định chứ
không phải mã:

| # | Việc | Loại |
|---|---|---|
| 1 | **Mở chế độ `STREAM`** — Claude Code *bắt buộc* streaming, Codex cũng streaming | 🔴 **quyết định hợp đồng**; `protocol.py` đòi đủ sáu ngữ nghĩa (kiểu sự kiện khai sẵn, nhịp tim, sự kiện `usage` cuối mang credit THẬT, huỷ-khi-ngắt, tiếp-nối-không-thu-hai-lần) |
| 2 | Route `POST /api/v1/responses` + `POST /api/v1/messages` | mã + khai inventory |
| 3 | **`Idempotency-Key`** — không CLI nào gửi nó | 🔴 **quyết định** (đúng vấn đề L4 đã nêu ở `RA_SOAT_VA_KE_HOACH.md` §10) |
| 4 | Che tên model thượng nguồn | mã — hôm nay phản hồi lộ nguyên `H:/LTT_LLM/models/….gguf`, vi phạm lớp đệm alias mà `test_212` chốt |

Việc 3 là chỗ thắt: cửa `SYNC_BILLED` **bắt buộc** `Idempotency-Key` vì nó không
có quote, mà **cả Codex lẫn Claude Code đều không gửi header đó**. Nói cách khác,
mở đường B cho CLI đòi giải xong câu hỏi L4 trước.

---

## 7. Thứ tự làm

1. ~~Sửa CUDA trên máy B~~ ✅ **xong** — khởi động lại sạch, 16:01.
2. ~~Đo lại~~ ✅ **xong** — VRAM 19.838 MiB, **67,6 tok/s**, nghiệm thu 19/19.
3. ~~Cắm Codex~~ ✅ **xong** — `codex exec` trả lời đúng trong 14 giây.
4. **Cắm Claude Code, chạy một việc thật có gọi tool.** Hình dạng request đã thử
   xong và model trả đúng `tool_use`; còn thiếu **một phiên thật**. Máy này không
   có Claude Code CLI (bạn dùng bản desktop), nên bước này cần bạn chạy.
5. Cân nhắc mở `qwen38-ops` (200K) nếu ~43.600 token còn lại là quá chật.
6. Chỉ sau đó mới bàn đường B (§6).

---

## 8. ~~Máy khác trong LAN~~ — ⛔ ĐƯỜNG NÀY ĐÃ BỎ (23/08)

> 🔴 **Chủ sản phẩm chốt 23/08: một cửa duy nhất, qua `app.lttstudios.com/api/v1`.**
> Không phát bearer token của cổng VLM cho từng máy nữa, không mở tường lửa máy B
> cho nhiều IP nữa. Lộ trình thay thế: **`LO_TRINH_API_CLI.md`**.
>
> Mục dưới đây **giữ lại làm tham chiếu kỹ thuật** — nó ghi đúng những gì mỗi
> client đòi hỏi, và Đợt 4 của lộ trình sẽ cần lại chính những chi tiết đó. Nhưng
> **đừng làm theo nó để cấu hình một máy mới.**
>
> ⛔ Cổng VLM máy B thì **không bỏ**: nó là động cơ, không phải một lối đi thay
> thế. Xem §0 của lộ trình.

### 8-cũ. Cấu hình LAN — tham chiếu kỹ thuật

### 8.0 🔴 Bước bắt buộc: mở tường lửa máy B

Hôm nay **chỉ máy A vào được**. Đo thật:

```
LTT LLM Gateway (chi may A) | enabled=True | dir=Inbound | port=8299 | remote=192.168.2.17
```

Cổng VLM **có** nghe `0.0.0.0:8299`, nên thứ duy nhất chặn máy khác là quy tắc
này. Chạy trên **máy B**, PowerShell **Run as administrator**, thay bằng đúng IP
các máy bạn muốn cho vào:

```powershell
Set-NetFirewallRule -DisplayName "LTT LLM Gateway (chi may A)" `
  -NewDisplayName "LTT LLM Gateway (may trong nha)" `
  -RemoteAddress 192.168.2.17,192.168.2.20,192.168.2.21
```

⛔ **LIỆT KÊ TỪNG IP, ĐỪNG MỞ CẢ DẢI.** `192.168.2.0/24` nghe có vẻ tiện, nhưng
cổng VLM dùng **một bearer token duy nhất dùng chung** — không có khái niệm
"khoá của máy này". Mở cả dải nghĩa là mọi thứ nối vào Wi-Fi nhà, kể cả điện
thoại của khách, đều **chạm tới được** cổng; chúng chỉ còn thiếu một chuỗi 43 ký
tự mà chuỗi đó nay nằm trên nhiều máy.

⚠️ Đặt IP **tĩnh** (hoặc DHCP reservation) cho các máy đó. DHCP đổi IP thì quy
tắc trỏ nhầm máy, và triệu chứng là "tự nhiên hôm nay không gọi được".

Kiểm từ máy mới (không cần token):

```powershell
Test-NetConnection 192.168.2.66 -Port 8299
curl.exe -s http://192.168.2.66:8299/live
```

`{"ok":true,...}` là thông. `TcpTestSucceeded: False` là tường lửa chưa mở.

---

### 8.1 Codex trong VS Code, trên máy khác

Giống hệt §3.1 — tiện ích và CLI **dùng chung `config.toml`**, nên làm một lần
là xong cả hai. Ba bước:

**1.** `~/.codex/config.toml` — thêm vào, **không đổi `model` mặc định ở trên**:

```toml
[model_providers.ltt]
name = "LTT Studios (may B)"
base_url = "http://192.168.2.66:8299/v1"
env_key = "LTT_LLM_TOKEN"
wire_api = "responses"
stream_idle_timeout_ms = 600000
```

**2.** `~/.codex/ltt.config.toml` — hồ sơ, **file riêng** (Codex 0.145 từ chối
`[profiles.X]` nằm trong `config.toml`):

```toml
model = "qwen38-api"
model_provider = "ltt"
model_reasoning_effort = "low"
model_reasoning_summary = "none"
model_context_window = 65536
```

**3.** Khoá, đặt ở **cấp người dùng** rồi **mở lại VS Code**:

```powershell
setx LTT_LLM_TOKEN "<bearer token cong VLM>"
```

`$env:` trong một cửa sổ terminal **không đủ** — tiện ích là tiến trình khác và
không thấy nó.

---

### 8.2 Claude Desktop

🔴 **Claude Desktop KHÔNG đọc `ANTHROPIC_BASE_URL`.** Nó có đường riêng gọi là
*Third-Party Inference*. Đặt biến môi trường ở đây là không có tác dụng gì —
khác hẳn Claude Code CLI ở §4.

**Mở cửa sổ cấu hình:**

> **Help → Troubleshooting → Enable Developer Mode**
> rồi **Developer → Configure Third-Party Inference…**
>
> (Trên Windows, menu ứng dụng là nút **☰** góc trên bên trái màn hình đăng nhập.)

**Điền phần Connection:**

| Trường | Giá trị |
|---|---|
| Inference provider | **Gateway** |
| Gateway base URL | `http://192.168.2.66:8299` |
| Gateway API key | bearer token của cổng VLM |
| Credential kind | **Static API key** |
| Gateway auth scheme | **Bearer** |

**Rồi phần Models — đừng bỏ qua bước này:**

| Trường | Giá trị |
|---|---|
| `inferenceModels` | `qwen38-api` |

⚠️ **Vì sao bắt buộc.** Claude Desktop tự dò model qua `GET /v1/models`, nhưng
nó **chỉ giữ những id trông giống Claude**. `qwen38-api` không khớp ⇒ bộ chọn
model **rỗng**, và không có gì nói cho bạn biết vì sao. Khai tay thì app **bỏ
qua luôn bước dò**.

> Tài liệu có nhắc một lối khác: cổng trả thêm trường `anthropic_family_tier` để
> model lọt bộ lọc. **Ta không dùng.** Trường đó nghĩa là *"đây là một model
> Claude nấp sau bí danh"* — Qwen của ta thì không phải, và dán nhãn sai lên
> chính hàng của mình là tự tạo ra một câu hỏi khó trả lời về sau.

Cuối cùng bấm **Apply locally** — ghi cấu hình cho **riêng máy này** rồi khởi
động lại app. (Nút *Export* là để phát cho cả đội qua MDM; một máy thì không cần.)

⚠️ Nếu máy đã có managed profile do tổ chức đẩy xuống, cửa sổ này mở ở chế độ
**chỉ đọc**. Lúc đó phải sửa từ phía MDM.

✅ Cổng ta **đáp ứng đủ** thứ Claude Desktop đòi: `POST /v1/messages` có
**streaming** và **tool use** — cả hai đã đo ngày 23/08 (`stop_reason: "tool_use"`).

ℹ️ Claude Desktop tắt sẵn *MCP tool search* và các beta thử nghiệm khác khi chạy
qua gateway, vì nhiều cổng khắt khe trả `400` cho header `anthropic-beta` lạ.
Cổng ta chuyển tiếp nguyên xi nên bật được — nhưng **không cần bật**, và cứ để
tắt là ít rủi ro nhất.

---

### 8.3 Bật và tắt

| | Bật | Tắt, về lại như cũ |
|---|---|---|
| **Codex CLI** | `codex --profile ltt` | `codex` trần — `model` mặc định ở đầu `config.toml` chưa hề bị đụng |
| **Codex trong VS Code** | chọn `qwen38-api` trong bộ chọn model | chọn lại model cũ |
| **Claude Desktop** | *Configure Third-Party Inference…* → provider **Gateway** → **Apply locally** | mở lại đúng cửa sổ đó, đưa **Inference provider** về mặc định → **Apply locally** → app khởi động lại |
| **Cả LAN, một nhát** | — | trên máy B: `Disable-NetFirewallRule -DisplayName "LTT LLM Gateway*"` |

⭐ **Công tắc tổng nằm ở máy B, không ở máy khách.** Tắt quy tắc tường lửa là mọi
máy mất đường ngay lập tức, không cần đụng vào từng máy. Bật lại bằng
`Enable-NetFirewallRule` cùng tên. Đây cũng là cách xử lý đúng khi token bị lộ:
**cắt đường trước, xoay khoá sau.**

---

### 8.4 Hỏng thì soi ở đâu

| Triệu chứng | Nguyên nhân hay gặp nhất |
|---|---|
| `TcpTestSucceeded: False` | tường lửa máy B chưa có IP máy đó (§8.0) |
| `401` | sai token, hoặc Claude Desktop để **auth scheme** là `x-api-key` (cổng ta đọc `Authorization: Bearer`) |
| `404` kèm tên model | tên model sai — phải đúng `qwen38-api` |
| Bộ chọn model của Claude Desktop **rỗng** | chưa khai `inferenceModels` (§8.2) |
| Codex báo *"legacy `[profiles.ltt]`"* | hồ sơ còn nằm trong `config.toml`, phải tách ra `ltt.config.toml` |
| Rất chậm, không lỗi | 🔴 model rơi về CPU. Hỏi `/health` → khối `gpu` → `dang_lo: true`. Xem §5 |
| `429` | cổng đang chạy đủ 2 lượt. Bình thường, thử lại sau |
