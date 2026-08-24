# Dây chuyền đã lắp đủ chưa? — phân tích khoảng trống

**2026-08-22.** Trả lời thẳng câu hỏi: *"đã tối ưu chưa, còn thiếu gì để cắm API vào
`app.lttstudios.com` là gọi được làm việc"*.

Mọi khẳng định dưới đây **đọc từ mã thật trong repo**, không suy đoán. Chỗ nào là
"chưa có" đều kèm bằng chứng đã grep ở đâu.

---

## 1. Trả lời thẳng: **CHƯA**. Còn bảy mảnh.

```
[Codex / Claude Code]  ──LAN──► llm_gateway :8299  ✅ CODE XONG, 26/26 test xanh
                                      │
                                llama-swap :8280   ✅ CẤU HÌNH XONG, hợp schema
                                      │
                                llama-server       ✅ BINARY + TRỌNG SỐ + TEMPLATE SẴN
                                                   ⏸️ CHƯA CHẠY LẦN NÀO (chờ GPU)

[app.lttstudios.com] ──► apps/<slug>
                            │
                            ├─ platform_core/llm/        ❌ KHÔNG TỒN TẠI  ← mảnh lớn nhất
                            ├─ providers REGISTRY        ❌ chưa có ltt_local_llm
                            ├─ api_keys (bearer trong DB) ❌ chưa có bản ghi
                            ├─ token → credit             ❌ chưa có công thức
                            └─ credit.giu_cho/quyet_toan  ✅ CÓ SẴN, dùng lại được
```

**Nhánh trên (Codex/Claude Code) gần xong.** Nhánh dưới (`app.lttstudios.com`) **mới
là phần chưa có**, và nó không phải "cắm dây" — nó là một mảnh kiến trúc chưa ai xây.

---

## 2. Bảy mảnh còn thiếu, xếp theo thứ tự chặn

### 🔴 A. `platform_core/llm/` — client chat dùng chung. **KHÔNG TỒN TẠI.**

Đây là phát hiện quan trọng nhất của phiên này. Grep toàn repo cho
`APIKEY_CAT_CHAT` ra **ba nơi tự gọi nhà cung cấp, mỗi nơi một kiểu**:

| Nơi | Nó làm gì |
|---|---|
| `platform_core/agent/planner.py:41` | `chon_key(category=CHAT, thu_tu_provider=["gemini"])` rồi **tự viết HTTP tới `generativelanguage.googleapis.com`** |
| `apps/autosubvideo/ai_workflows.py` | tự gọi |
| `apps/kichban/jobs.py` | tự gọi |

**Hệ quả phải hiểu cho đúng:** thêm `ltt_local_llm` vào `REGISTRY` **sẽ không làm
app nào dùng nó cả.** Mỗi chỗ gọi đang ghi cứng `thu_tu_provider=["gemini"]` **và**
ghi cứng luôn định dạng dây của Gemini. Cascade đa-provider của H8 có tồn tại,
nhưng ở tầng *cấp key* — không ai bắc cầu nó sang tầng *gọi model*.

⇒ Phải viết `platform_core/llm/cong_vlm.py`, **soi gương `platform_core/image_gen/
cong_render.py`** (đã có sẵn và đã học đủ ba bài học):

- `BanError` là **lớp ngoại lệ RIÊNG**, không phải lỗi provider — 429 ≠ hỏng;
- **không tự chuyển sang đám mây** sau lưng khách (D-010);
- `job_id` của máy A làm khoá idempotency.

Rồi **chuyển ba chỗ gọi kia sang adapter**. Không chuyển thì mảnh A vô nghĩa.

### 🔴 B. Provider `ltt_local_llm` trong `REGISTRY`. **Chưa có.**

`ltt_local` **đã có** (dòng 154 của `providers.py`) nhưng nó là **cổng ảnh**:
`categories=(APIKEY_CAT_IMAGE,)`, `base_url` đọc từ `LTT_RENDER_BASE_URL` (cổng
8199), `async_poll=True`, model `hidream-o1` với `is_active=False`.

VLM là **cổng khác, cổng 8299, đồng bộ, category `chat`** ⇒ provider riêng, đừng
nhồi vào `ltt_local`. Và giữ đúng khuôn fail-closed đang có ở đó: `is_active=False`
cho tới khi qua cổng đo.

Tin tốt: **category `chat` đã tồn tại sẵn** (`APIKEY_CAT_CHAT = "chat"`,
`platform_core/models.py:596`) và đã có người dùng — không phải mở loại mới.

### 🟠 C. Bản ghi API key trong CSDL. **Chưa có.**

`api_pool.chon_key` cấp phát từ bảng `api_keys` (đã mã hoá). Bearer token của
`llm_gateway` phải nằm ở đó thì cascade mới chọn được nó. Việc nhỏ, nhưng **không
có nó thì không có gì chạy**.

### 🟠 D. Công thức **token → credit**. **Chưa có.**

`billing_math.py` mới chỉ có tỉ giá tiền: `1 credit = 100đ` (Q31). **Không có giá
token.** Và `credit.giu_cho → quyet_toan → hoan` thì **đã có sẵn**, khoá theo
`job_id` — dùng lại nguyên.

Phần dữ liệu cũng đã đủ: llama-server trả `usage {prompt_tokens, completion_tokens,
total_tokens}` **cộng** `timings.cache_n` = số token prompt lấy lại từ cache.

⇒ Thứ **thật sự thiếu là CHÍNH SÁCH GIÁ**, và đó là quyết định của chủ sản phẩm,
không phải của tôi. Ba câu cần chốt:

1. Giá một triệu token vào / ra là bao nhiêu credit?
2. Token **prompt lấy từ cache** (`cache_n`) tính rẻ hơn bao nhiêu? *(Với phiên
   agent dài, đây là phần lớn lưu lượng — tính đủ giá là tính tiền khách hai lần
   cho cùng một ngữ cảnh.)*
3. Token **reasoning** (`reasoning_content`) có tính tiền không? *(Ở `xhigh` nó có
   thể nhiều hơn cả câu trả lời.)*

### 🟡 E. Public API `/api/v1` cho khách lập trình. **Chưa mở.**

Nếu muốn khách ngoài gọi model nhà thì phải theo đúng thủ tục H35 đã chốt: thêm
ToolSpec, cập nhật `server/api/inventory.py` (24 route **đóng băng**, so hai
chiều), và cập nhật `APP_API_COVERAGE_FINAL.md` — `test_212` đọc bảng đó **như dữ
liệu** và so với registry cả hai chiều. Quên một trong ba là gate đỏ.

### 🟡 F. MCP server cho **Claude Desktop**. **Chưa có.**

Claude Desktop **không đổi được model** (không đọc biến môi trường, không có ô nhập
endpoint). Đường duy nhất là bọc model nhà thành **công cụ MCP**. Hạng mục riêng,
không nằm trong MVP.

### ⏸️ G. Chưa đo một lần nào trên GPU.

P0-4 (`/free` của ComfyUI), P2, P3, P4, P5, P6. Toàn bộ số trong `llama-swap.yaml`
hiện là **mốc khởi điểm mượn của cộng đồng**, chưa phải số của máy B.

---

## 3. Tài liệu cộng đồng: đã có gì, vừa thêm gì, còn thiếu gì

### Đã tải về `D:\LTT_VLM_REFS\`

| Nguồn | Đã dùng vào việc gì |
|---|---|
| `sudoingX/qwen38-mtp` | 7 luật · sweep RTX 3090 · `probe.py` · lệnh chạy 200K |
| `syv-ai/qwen38-27b-rtx3090` | 18 bẫy · `quality_battery.py` · `long-context.md` (số chất lượng KV) |
| `mostlygeek/llama-swap` | `config-schema.json` (đã đối chiếu cấu hình) · API unload · ttl |

### ⭐ Vừa tìm thêm hôm nay — và nó **cứu Codex**

**Template chat chính thức của Qwen3.8 có regression làm hỏng tool calling.**
Cụ thể, theo `froggeric/Qwen-Fixed-Chat-Templates`:

| Lỗi của template chính thức | Nó phá cái gì |
|---|---|
| **"tool argument crashes on JSON strings from standard OpenAI API clients"** | 🔴 **Đúng thứ Codex gửi.** Đây là lỗi giết chết mục tiêu chính |
| Crash khi `enable_thinking=false` | Không tắt được suy nghĩ |
| Hardcode `xhigh` | Đốt sạch ngân sách token vào reasoning trước khi làm việc |
| "Empty think poisoning" — chèn `<think></think>` rỗng vào lịch sử | Bẩn ngữ cảnh dần qua từng lượt |
| Agentic stalling giữa vòng tool-call | Agent treo |

**Đã tải về và đã đẩy sang máy B** (`H:\LTT_LLM\models\chat_template.jinja`,
26.681 B, `qwen3.8-froggeric-v22.3`). Đã đọc qua: **không có lời gọi mạng nào**
trong template. Đã cắm vào `llama-swap.yaml` cùng `--reasoning-format deepseek`
(tách khối `<think>` ra trường riêng, để token suy nghĩ **không chen vào giữa một
tool call**).

Xác nhận chéo: hàng 3090 nhanh nhất trong sweep cộng đồng (**b10450, 63,5 tok/s**)
dùng **đúng hai cờ này**. Không phải trùng hợp.

### ⭐ Và một khả năng cần đánh giá ở P6

`llama-swap` có **`/comfyui/` — endpoint riêng cho ComfyUI, mô tả là *"for more
reliable swapping"*** (issue #1001). Tức là **chính bài toán trọng tài GPU của ta đã
được giải ở thượng nguồn**: khai ComfyUI như một "model" trong `llama-swap`, và nó
bảo đảm chỉ một thứ nằm trong VRAM.

⚠️ **Nhưng có một xung đột thật, phải kiểm trước khi mừng:** ComfyUI trên máy B
**còn phục vụ dự án video**, mà dự án đó **không đi qua `llama-swap`**. Nếu
`llama-swap` nắm vòng đời ComfyUI, nó sẽ **giết ComfyUI giữa một lượt video**.

⇒ P6 phải đánh giá hai đường: (a) `llm_gateway` tự trọng tài (thiết kế hiện tại,
không đụng ComfyUI), hay (b) giao ComfyUI cho `llama-swap` (gọn hơn, nhưng phải
giải quyết dự án video trước). **Đừng chọn (b) chỉ vì nó đẹp hơn.**

### Còn thiếu — cần nghiên cứu tiếp, đều **không cần GPU**

| # | Cần tìm | Vì sao chặn |
|---|---|---|
| 1 | **Báo cáo thực chiến Codex ↔ `llama-server /v1/responses`** | Ta mới biết endpoint **tồn tại**. Chưa thấy ai xác nhận Codex chạy trọn một việc qua nó. Nếu hỏng thì cần proxy dịch Responses↔Chat |
| 2 | **Mẫu tính tiền theo token cho cổng OpenAI-compatible** (LiteLLM hoặc tương đương) | Mảnh D. Đừng tự nghĩ ra cách đếm — lấy mẫu đã có |
| 3 | **`llama-swap` `/metrics` (Prometheus) và `/running`** | Cổng cần biết model nào đang nằm trong VRAM để trọng tài. Repo đã clone, chỉ cần đọc |
| 4 | **MCP server bọc endpoint OpenAI-compatible** | Mảnh F, cho Claude Desktop |
| 5 | **`stripParams` / `setParams` của llama-swap** | Có thể ép `reasoning_effort` theo hồ sơ ngay ở tầng swap, thay vì tin client gửi đúng |

---

## 4. Trình tự để tới được "cắm API vào `app.lttstudios.com`"

**Đợt 1 — không cần GPU, làm được ngay** *(còn lại của P7 + mảnh A/B/C)*

| # | Việc | Chặn cái gì |
|---|---|---|
| 1 | Nghiên cứu 5 mục "còn thiếu" ở §3 | mảnh A, D, F |
| 2 | Viết `platform_core/llm/cong_vlm.py` + test | 🔴 **mảnh A** — mảnh lớn nhất |
| 3 | Thêm provider `ltt_local_llm` (fail-closed, `is_active=False`) | mảnh B — ⏸️ **chờ phiên khác đóng `providers.py`** |
| 4 | Chuyển `planner.py` sang adapter (chỗ dễ nhất, có sẵn `llm_call` tiêm được) | chứng minh mảnh A dùng được |
| 5 | Chốt **chính sách giá token** với chủ sản phẩm rồi viết vào `billing_math.py` | mảnh D |
| 6 | `deploy.ps1` + `kiem_tra.ps1` | P9a |

**Đợt 2 — khi card trống**: P0-4 → P2 → P3 → P4 → P5 → P6.

**Đợt 3**: P8 (Codex + Claude Code) → bật `ltt_local_llm` → một app thật gọi được →
(tuỳ chọn) mở Public API.

---

## 5. Cái đã tối ưu, và cái chưa

**Đã tối ưu:**
- Không dựng engine mới — `llama.cpp` + `llama-swap` là phần mềm thượng nguồn, ta chỉ cấu hình.
- Không viết lại `/v1/*` — cổng là **đường ống có chính sách**, không phải bộ dịch.
- Không dựng hàng đợi/sổ tiền thứ hai — dùng `credit` và `api_pool` đang có.
- Không chép `busy.py` — `llm_gateway/trong_tai.py` gọi thẳng `render_gateway.busy`.
- Hai hồ sơ model thay vì hy sinh vision hoặc ngữ cảnh.

**Chưa tối ưu — và biết rõ vì sao:**
- **Chưa có tầng adapter chat** ⇒ nền tảng vẫn ghi cứng Gemini ở ba chỗ. Đây là nợ
  kiến trúc **có sẵn từ trước**, hạng mục này chỉ làm nó lộ ra.
- **Mọi con số hiệu năng đang là số mượn.** Chưa có một phép đo nào của máy B.
- **Trọng tài GPU chưa chọn đường** — tự làm, hay giao cho `llama-swap`.
