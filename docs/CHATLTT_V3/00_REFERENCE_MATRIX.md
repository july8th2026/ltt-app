# P00 — MA TRẬN THAM CHIẾU

*Cái gì đã **tự tay xác minh** trong phiên này, cái gì mới là **chép lại từ gói
prompt**, và cái gì **chưa ai kiểm**. Ba cột đó phải tách nhau, vì `CLAUDE.md`
đã ghi lại năm lần một bảng chép tay nói sai về phía nguy hiểm.*

---

## 1. Đã tự fetch và đọc trong phiên này — [U] hạng nhất

### `llama.cpp` · `docs/function-calling.md`
`https://raw.githubusercontent.com/ggml-org/llama.cpp/master/docs/function-calling.md`
· HTTP 200 · 21.029 byte · lấy 2026-09-04.

| # | Trích | Dòng | Hệ quả cho LTT |
|---|---|---|---|
| **U-1** | 🔴 *"Beware of extreme KV quantizations (e.g. `-ctk q4_0`), they can **substantially degrade** the model's tool calling performance."* (khối `[!CAUTION]`) | 332-333 | **Gọi đích danh `q4_0`** — đúng thiết lập của **cả hai** hồ sơ production. Đây không phải cảnh báo chung chung; nó nêu chính con số ta đang chạy |
| **U-2** | *"Multiple/parallel tool calling is supported on some models but **disabled by default**, enable it by passing `"parallel_tool_calls": true` in the completion endpoint payload."* | 24 | Bộ kiểm "gọi song song" của P01 **phải** gửi cờ này, nếu không nó đo một thứ đã tắt sẵn và kết luận "Qwen không gọi song song" — sai |
| **U-3** | *"Generic tool call is supported when the template isn't recognized by native format handlers (you'll see `Chat format: Generic` in the logs)."* + *"Generic support may consume more tokens and be less efficient than a model's native format."* | 20-22 | Ta dùng `--chat-template-file` **bản vá cộng đồng**. Handler đang hoạt động là **Native hay Generic — CHƯA AI BIẾT**. Đọc được từ log `llama-server`. Hệ quả rất khác nhau |
| **U-4** | *"…make sure it has a tools-enabled template: you can verify this by inspecting the `chat_template` or `chat_template_tool_use` properties in `http://localhost:8080/props`"* | 284 | Phương pháp cụ thể cho P01 bước 1, thay cho "kiểm bằng cách nào đó" |
| **U-5** | Bảng template→handler: họ Qwen **chia đôi** — `Qwen-Qwen2.5-0.5B.jinja`→`Hermes 2 Pro`, nhưng `Qwen-Qwen2-7B-Instruct.jinja`/`Qwen-QVQ-72B`/`Qwen1.5-7B-Chat`→**`Generic`** | 77-83 | Không suy được handler của Qwen3.8 từ "nó là Qwen". Phải đọc log |

⭐ **U-1 là phát hiện quan trọng nhất của cả P00.** Nó nâng R3 từ "rủi ro trung
bình–cao" thành **một cảnh báo chính thức trỏ thẳng vào cấu hình đang chạy**.
Và vì chủ dự án đã chốt giữ 200K (⇒ q4_0 bị khoá, `00_KE_HOACH_V3.md` §R3-QĐ),
nó không còn là thứ sửa được bằng cấu hình — nó là **cái giá phải đo và phải biết**.

⛔ U-3 mở ra một khả năng chưa ai xét: nếu template vá đang rơi vào handler
**Generic**, thì mọi con số tool-calling của ta đang bị một tầng kém hiệu quả
làm nhiễu, **độc lập với** chuyện KV. Đó là hai nguyên nhân khác nhau cho cùng
một triệu chứng — và P01 phải tách chúng ra, nếu không sẽ sửa nhầm chỗ.

---

## 2. Chép lại từ gói prompt — [C]/[U] hạng hai, **CHƯA tự xác minh**

`01_RESEARCH_BASELINE.md` và `05_QWEN_RUNTIME_REFERENCES.md` liệt kê các nguồn
dưới đây. Phiên này **chưa mở** chúng.

| Nguồn | Mẫu hình gói prompt rút ra | Trạng thái |
|---|---|---|
| OpenAI Responses API · ChatGPT capabilities · Projects · Deep Research | `tools`/`tool_choice`, built-ins, MCP/custom functions, Projects, Memory, apps & approvals | **chưa xác minh** |
| Gemini Interactions · function calling · image generation | Interactions hợp nhất, steps, state phía máy chủ, thi hành nền, function call → app execution → result → model continuation, sửa ảnh hội thoại, Canvas, Gems | **chưa xác minh** |
| LibreChat · agents/tools/image_gen/mcp/skills | agent chọn tool; ảnh chat-native; **tool result trả về LLM**; MCP/Actions; Skills; Artifacts; HITL bền | **chưa xác minh** — nhưng H43 Phase 01 đã đối chiếu 12 hệ con của LibreChat @ `9e74cc0` (`docs/CHATLTT/reports/01_librechat_tham_chieu.md`) [S nội bộ] |
| Open WebUI · server-side tool calling | vòng nhiều lượt phía máy chủ; **duyệt bền trong state của chat đã lưu**; built-ins + workspace + MCP + OpenAPI dưới một vòng | **chưa xác minh** |
| `llama.cpp` #27588 · #22581 · #28287 · #27281 | message assistant cuối mang `tool_calls` bị rơi ở đường nối tiếp; tool call hỏng do tích hợp runtime/template | **chưa xác minh** — P01 phải kiểm **có/không tái hiện trên build của ta** |
| `froggeric/Qwen-Fixed-Chat-Templates` v22.3 | vá 5 regression: crash `enable_thinking=false` · *"tool argument crashes on JSON strings from standard OpenAI API clients"* · hardcode `xhigh` · *"empty think poisoning"* · **agentic stalling giữa vòng tool-call** | **đang chạy trên production** [S: yaml], nhưng **năm lời hứa chưa ai kiểm** |
| LangGraph | checkpoint / interrupt / resume / HITL | chỉ tham chiếu mẫu hình. ⛔ Không thêm phụ thuộc trừ khi P02 chứng minh nó giảm trùng lặp |

⛔ **Không được nâng bất kỳ dòng nào ở §2 thành căn cứ cho một cổng** cho tới
khi có người mở đúng nguồn đó. Gói prompt là một bản tóm tắt do người khác viết
— nó là [C], không phải [U].

---

## 3. Mẫu hình LTT **đã có sẵn** mà V3 phải dùng lại, không viết lại [S]

| Mẫu hình đối chiếu | LTT đã có ở đâu | Vì sao không viết lại |
|---|---|---|
| tool result **trả về LLM** (LibreChat/OpenWebUI) | ⛔ **chưa có** | đây là GAP thật, xây ở P03 |
| phép chiếu tool → schema công khai | `platform_core/public_api/catalog.project_tool` | đã làm đúng việc khó: bỏ id model nội bộ (test_212), ẩn tham số máy chủ tự quyết, giữ đúng kiểu enum. Bản chiếu thứ hai = hai hợp đồng lệch nhau (`danh_muc.py` đã ghi lý do) |
| báo giá → xác nhận → nộp, **báo giá lại** khi chốt | `tao_media.tao()` `"gia da doi: bao X, tinh lai Y"` | phép kiểm đã có; P04 **mở rộng** nó cho tool do model gọi |
| quyết toán không bao giờ thu quá phần đã giữ | `credit.quyet_toan` (Q84) | sổ cái là sự thật tính tiền |
| bận ≠ hỏng, không thu tiền | `luong.DangBan` · `jobs.PROVIDER_REJECTED` · `hoan_luot()` | ba lớp đã thống nhất qua H43 Phase 04/05 |
| hàng đợi job bền, có lease, có `so_lan_thu` | `job_runner` · `leases` · `job_submit.submit_with_credit` | P08 (việc nền) **dùng**, không dựng hàng đợi thứ hai |
| sự kiện canonical một hình dạng cho ba nguồn | `services/su_kien.py` LOAI + `ap_dung` fail-closed | V3 **nối thêm** loại, không đổi cơ chế |
| cây hội thoại + typed blocks | `chatltt_message.blocks` | 5 test `convoStructure.spec.ts` của LibreChat là đặc tả cho `test_617` |
| CSRF một cửa duy nhất | `_chung.kiem_csrf` | `test_628` đọc mã nguồn từng route và đòi thấy đúng tên hàm |
| kiểm sở hữu ở tầng service, route không "quên" được | `hoi_thoai.*` mọi truy vấn có `user_id` | IDOR chặn ở một chỗ |

---

## 4. Ba câu hỏi mở mà P01 **phải** trả lời, không được suy

| # | Câu hỏi | Vì sao không suy được | Trả lời bằng |
|---|---|---|---|
| **M-1** | Handler tool-call đang hoạt động là **Native hay Generic**? | U-5: họ Qwen chia đôi trong chính bảng của llama.cpp; và ta dùng template **vá**, không phải template gốc | log `llama-server`: dòng `Chat format: …` |
| **M-2** | `q4_0` **thật sự** làm hỏng tool-call trên model này bao nhiêu? | U-1 nói "substantially degrade" nhưng không nói bao nhiêu, trên model nào | A/B P01 với hồ sơ tạm `-c 65536` q8_0 vs q4_0 |
| **M-3** | Năm regression froggeric v22.3 tuyên bố vá — **đã vá thật chưa** trên build của ta? | [C] là lời hứa của một bản vá cộng đồng, không phải phép đo trên máy này | kịch bản riêng trong ma trận P01 |

⭐ M-1 và M-2 là **hai nguyên nhân độc lập** cho cùng một triệu chứng "tool call
kém". Nếu P01 chỉ đo M-2, một kết quả xấu sẽ bị quy hết cho KV trong khi thủ
phạm có thể là handler Generic. Ma trận P01 phải tách được hai cái đó.
