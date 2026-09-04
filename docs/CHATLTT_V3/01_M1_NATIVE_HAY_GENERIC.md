# M-1 — NATIVE HAY GENERIC: phân tích và phán quyết

*H44 · 2026-09-04 · trả lời bằng **mã và dữ liệu thật**, không bằng suy đoán.*

## Kết luận trước, bằng chứng sau

> **NATIVE — bộ phân tích `Qwen3-Coder` (PEG), không phải `Generic`.**
> Cấu hình hiện tại **nhất quán**: template dạy model viết XML, parser đọc XML.
>
> 🔴 **Nhưng V3 đang đứng cạnh một cái bẫy một dòng.** Đặt
> `chat_template_kwargs: {"tool_call_format": "json"}` — một tuỳ chọn *có thật*,
> template *có đọc* — sẽ làm **mọi lời gọi tool biến thành văn bản thường**,
> im lặng, không lỗi. Chi tiết ở §5.

---

## 1. Vì sao câu hỏi này quan trọng hơn nó trông

`platform_core/runtime_noi_bo/luong.py:475` chỉ phát `tool_call.delta` khi máy B
trả `delta.tool_calls` trong chunk. Máy B **chỉ điền trường đó** khi bộ phân tích
của `llama-server` nhận ra được lời gọi tool trong dòng chữ model sinh ra.

Parser không nhận ra ⇒ lời gọi rơi vào `delta.content` như văn bản thường ⇒
`luong.py` phát `response.delta` ⇒ ChatLTT thấy **một câu trả lời bằng chữ**, và
vòng lặp tool của V3 **không bao giờ chạy một vòng nào**.

⛔ Đây là hỏng **im lặng và toàn phần**: không lỗi, không cảnh báo, model vẫn
"trả lời", khách vẫn bị tính tiền. Khác hẳn KV lượng hoá — thứ làm **giảm dần**
độ chính xác. Một cái là 0 %, một cái là 85 % thay vì 95 %.

⭐ Nên trật tự ưu tiên của P01 phải đổi: **đo khớp định dạng TRƯỚC, A/B KV SAU.**
Đo KV trên một đường ống đứt là đo nhiễu.

## 2. Phương pháp — hai nguồn, cả hai kiểm chứng được

| Nguồn | Lấy thế nào | Định danh |
|---|---|---|
| Template đang chạy | `files/read` qua Nexus tới máy B, `H:/LTT_LLM/models/chat_template.jinja` | **421/421 dòng, `truncated=False`, 26.681 byte khớp chính xác**, SHA256 `6e1439c913ad7df4a966493ad70de7e7fc5a548d41bbe417c1571f766603629b` |
| Logic phát hiện | `curl` `raw.githubusercontent.com/ggml-org/llama.cpp/master/common/chat.cpp` | HTTP 200, 174.542 byte |

⚠️ Bộ nhớ vận hành ghi *"`files/read` cắt âm thầm"*. Đã kiểm: `total_lines` =
`returned_lines` = 421, `truncated=False`, và số byte cục bộ **khớp từng byte**
với `size_bytes` máy B báo. Không dính.

## 3. Chuỗi phát hiện của llama.cpp — nó quyết định bằng gì

`common/chat.cpp` chọn bộ phân tích bằng **tìm chuỗi con trong MÃ NGUỒN
template**, chạy qua một chuỗi `if` theo thứ tự. Nhánh cuối cùng trước khi rơi
xuống `Generic` (`return std::nullopt`):

```cpp
// dòng 3596-3602
// Qwen3-Coder XML tool calls, also used by Nemotron Nano 3, Qwen3.5 và StepFun-3.5-Flash
if (src.find("<tool_call>")  != std::string::npos &&
    src.find("<function=")   != std::string::npos &&
    src.find("<parameter=")  != std::string::npos) {
    LOG_DBG("Using specialized template: Qwen3-Coder\n");
    return common_chat_params_init_qwen3_coder(tmpl, params);
}
return std::nullopt;          // <- Generic bat dau tu day
```

Đếm trên template thật:

| Dấu mốc | Số lần | Điều kiện |
|---|---|---|
| `<tool_call>` | **6** | ✅ |
| `<function=` | **4** | ✅ |
| `<parameter=` | **2** | ✅ |

⇒ **Cả ba đều có. Rơi vào nhánh Qwen3-Coder, không tới được `nullopt`.**

Và không nhánh nào **trước** nó bắt trước — đã đối chiếu từng cái: LFM2.5
(`"List of tools: ["`), GigaChatV3 (`<|role_sep|>`), MiniMax-M3 (`]<]minimax[>[`),
DeepSeek V3.2/V4 (`dsml_token` + `DSML`), Gemma4 (`'<|tool_call>call:'`),
MiniCPM5 (`Tool usage guidelines:` + `<function name="` + `<param name="`).
Template của ta **không chứa** dấu mốc nào trong số đó.

⭐ Chú ý MiniCPM5 dùng `<function name="…">` (có dấu cách và ngoặc kép) còn ta
dùng `<function=…>`. Hai hình dạng khác nhau một ký tự, và một ký tự đó là ranh
giới giữa hai bộ phân tích.

## 4. Bộ phân tích được chọn hành xử ra sao với model BIẾT SUY LUẬN

`common_chat_params_init_qwen3_coder` (dòng 1162+) tự chia hai đường:

```cpp
auto supports_reasoning = tmpl.source().find("<think>") != std::string::npos;
auto is_qwen3_coder     = !supports_reasoning;
```

Template ta có `<think>` **8 lần** ⇒ `supports_reasoning = true` ⇒
`is_qwen3_coder = false`. Hệ quả, cả hai đều **thuận lợi**:

| | Giá trị | Nghĩa |
|---|---|---|
| `format` | `COMMON_CHAT_FORMAT_PEG_NATIVE` | **native**, đúng như tên |
| `thinking_start_tag` | `<think>` | khớp `--reasoning-format deepseek` đang chạy |
| `thinking_end_tags` | `{"</think>", "<tool_call>"}` | ⭐ `<tool_call>` **cũng** kết thúc khối suy nghĩ — model nhảy thẳng từ think sang gọi tool không cần đóng thẻ, và parser không nuốt nhầm |
| mốc mở tool | chỉ `<tool_call>` | ⛔ **không** thêm `<function=name>` — đó là bản vá riêng cho Qwen3-Coder (model *không* suy luận) hay quên `<tool_call>` |

Và chính template **đã dạy đúng điều parser đòi**, bằng chữ:

> *"The `<tool_call>` and `<function>` tags MUST be at the very beginning of a
> new line, with NO spaces or indentation before them."*

⇒ **Template và parser khớp nhau. Không có khoảng hở nào ở cấu hình mặc định.**

## 5. 🔴 CÁI BẪY — và nó nằm cách V3 đúng một dòng cấu hình

Dòng **2** của template:

```jinja
{%- set _tool_format = tool_call_format if tool_call_format is defined else 'xml' %}
```

`tool_call_format` là một biến **điều khiển được từ ngoài** qua
`chat_template_kwargs` — cùng cơ chế mà `docs/VLM_NOI_BO/do_ngu_canh_2026-09-03/bench_ctx.py:170`
đã dùng cho `reasoning_effort`. Đặt nó thành `'json'` thì template chuyển sang
dạy model viết Hermes JSON:

```
<tool_call>
{"name": "…", "arguments": {…}}
</tool_call>
```

⛔ **Nhưng phép phát hiện đọc MÃ NGUỒN template, không đọc kết quả render.**
Mã nguồn chứa **cả hai nhánh** — chuỗi hướng dẫn JSON ở dòng 179 *và* chuỗi
hướng dẫn XML ở dòng 181. Nên `<function=` và `<parameter=` **luôn luôn** có mặt
trong `src`, bất kể `tool_call_format` bằng gì.

Hệ quả, viết thành một dòng:

```
tool_call_format = json
  ⇒ model duoc DAY viet   <tool_call>{"name":...}</tool_call>
  ⇒ parser van DOI doc     <tool_call><function=...><parameter=...>
  ⇒ khong khop
  ⇒ loi goi tool roi vao delta.content nhu VAN BAN THUONG
  ⇒ luong.py:475 khong bao gio chay
  ⇒ V3 thay 0 tool call, trong khi model dang co gang goi tool moi luot
```

⭐ **Đây là dạng hỏng tệ nhất có thể có**: không lỗi, không log, model vẫn nói
năng mạch lạc, sổ tiền vẫn chạy. Nó chỉ lộ ra khi có người hỏi *"sao nó không
bao giờ dùng tool?"* — và câu trả lời sẽ bị đổ nhầm cho model, hoặc cho KV.

⇒ **LUẬT cho V3, đưa vào `00_DO_NOT_REWRITE.md`:**
> `tool_call_format` **phải để mặc định** (`xml`). Không được đặt trong
> `chat_template_kwargs`. Muốn đổi thì phải đổi **template** để nhánh XML biến
> mất khỏi mã nguồn — và đó là một ADR, không phải một tham số.

Cần một **phép kiểm tĩnh** chốt điều này: quét `apps/chatltt/` và
`platform_core/` cấm chuỗi `tool_call_format`. Rẻ, và nó chặn đúng cái sai mà
một phiên sau rất dễ mắc khi thấy JSON "sạch hơn XML".

## 6. Một hệ quả thứ hai: `parallel_tool_calls`

`docs/function-calling.md:24` [U]: *"Multiple/parallel tool calling … **disabled
by default**, enable it by passing `"parallel_tool_calls": true`."*

Template hỗ trợ nhiều lời gọi — nó dạy rõ: *"To call multiple functions, output
a separate, completely closed `<tool_call></tool_call>` block for EACH function."*
Nhưng nếu ChatLTT không gửi cờ, năng lực đó **tắt ở tầng runtime**.

⇒ Bộ kiểm "gọi song song" của P01 **phải** gửi `parallel_tool_calls: true`.
Không gửi thì nó đo một thứ đã tắt sẵn rồi kết luận sai về model.

## 7. Còn một việc chưa đóng — và tôi không lấp nó bằng suy luận

Phân tích trên đọc `common/chat.cpp` ở nhánh **master**. `llama-swap.yaml` ghi
*"build 10689"*, và **chưa xác nhận được** đó có phải build đang chạy không:
`llama-server.exe --version` gọi qua Nexus **treo quá 60 giây** (xem §8).

Rủi ro thật của khoảng trống này: master đã chuyển sang **autoparser/PEG**
(`COMMON_CHAT_FORMAT_PEG_NATIVE`); một build cũ hơn có thể dùng bộ phân tích
Qwen3-Coder viết tay. **Ba dấu mốc phát hiện thì gần như chắc chắn không đổi** —
chúng có từ khi handler ra đời — nhưng "gần như chắc chắn" không phải bằng chứng.

**Đóng bằng, theo thứ tự rẻ trước:**
1. `files/read` log của llama-swap (băng-rôn khởi động in số build) — cần biết
   đường dẫn log; `files/read` đã chạy tốt.
2. `/props` của engine khi có model nạp — trả cả `chat_template` đang hoạt động.
3. Bật `--verbose` một lượt và đọc dòng `Using specialized template: Qwen3-Coder`
   — bằng chứng **trực tiếp** nhất, đúng dòng `LOG_DBG` ở §3.

⭐ Cách 3 là bằng chứng mạnh nhất vì nó không suy luận gì cả: nó **đọc chính lời
khai của runtime**. Đưa vào P01 bước 1 như một hạng mục bắt buộc.

## 8. Thu hoạch vận hành về Nexus (trả giá bằng năm lượt thử)

| Đã đo | Luật rút ra |
|---|---|
| `hostname` (exe trần) → 467 ms, exit 0 | exe đơn giản **chạy tốt** |
| `cmd /c echo` → **treo 120 s**, node không trả lời | ⛔ đừng lồng `cmd` |
| `powershell.exe -Command …` → **treo** | ⛔ đừng lồng PowerShell |
| `curl` → `Invoke-WebRequest: missing Uri` | Nexus **đã bọc sẵn** lệnh trong PowerShell ⇒ `curl` là bí danh |
| `curl.exe --version` → `curl: try 'curl --help'` | mảng `args` **không tới được** tiến trình; phải truyền cả dòng lệnh trong `command` |
| `exec` thiếu `reason` → 422 | Nexus **bắt buộc** khai lý do cho mọi thứ ghi vào sổ kiểm toán |
| `files/read?path=<thu-muc>` → 404 *"not a file"* | 404 ở đây là "sai đối tượng", **không phải** "không có route" |
| mọi đường khác (`process/list`, `jobs`, `audit`, `docs`) → 403 | bề mặt API hẹp: `exec`, `files/read`, `metrics/gpu`, `health`, `capabilities` |

⭐ Dòng thứ tư giải thích ba dòng trên nó. Ba lần treo trước đó trông như ba lỗi
khác nhau; chúng là **một** lỗi: lồng một shell vào trong một shell đã có sẵn.

## 9. Điều này đổi gì trong kế hoạch

| Mục | Trước | Sau |
|---|---|---|
| M-1 | "chưa ai biết, phải đo" | **NATIVE (Qwen3-Coder PEG)** — đã trả lời bằng mã; còn xác nhận build |
| Rủi ro #1 của P01 | KV `q4_0` | **khớp định dạng tool-call** — hỏng 0 % im lặng, nặng hơn hẳn suy giảm dần |
| Thứ tự đo | A/B KV trước | **khớp định dạng trước**, KV sau — đo KV trên ống đứt là đo nhiễu |
| Luật mới | — | cấm `tool_call_format` trong `chat_template_kwargs` + phép kiểm tĩnh chốt |
| Luật mới | — | `parallel_tool_calls: true` bắt buộc khi đo gọi song song |
| Ngân sách P01 | 2.700 credit | **giảm** — phép kiểm khớp định dạng đầu tiên chỉ tốn ~20 lượt gọi, và nếu nó đỏ thì không có lý do gì chạy 2.400 lượt còn lại |

⭐ Mục cuối là phần đáng giá nhất của cả phân tích này: một phép kiểm **20 lượt
gọi** đứng trước một lô đo **2.400 lượt**, và nó có quyền huỷ cả lô.
