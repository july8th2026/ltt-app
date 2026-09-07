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

### 5b. 🔴 ĐÍNH CHÍNH 04/09 — TÔI ĐÃ SAI. Bẫy **không** nổ, và lý do đáng biết

Bản đầu của §5 (commit `e0d8ac3`) kết luận chắc nịch rằng đặt
`tool_call_format=json` sẽ làm **mọi lời gọi tool thành văn bản thường**. Tôi đã
đem đi đo. **Nó không xảy ra.**

| Cấu hình | 3 lượt | Kết quả |
|---|---|---|
| mặc định (`xml`) | 3 | **3/3** `tool_calls` có cấu trúc |
| `chat_template_kwargs: {"tool_call_format":"json"}` | 3 | **3/3** `tool_calls` có cấu trúc, **0/3** lệch định dạng |

Và không phải vì kwarg bị bỏ qua — nó tới nơi thật. Hỏi `/apply-template` của
engine (cổng 8281) để đọc **prompt đã render**:

| | mặc định | `tool_call_format=json` |
|---|---|---|
| độ dài prompt | 2.173 ký tự | **2.090** |
| hướng dẫn `<function=example…>` | **có** | **không** |
| hướng dẫn `{"name": "example…"}` | không | **có** |

⇒ Template **thật sự chuyển sang dạy model viết JSON**. Vậy mà parser vẫn đọc được.

**Mắt xích tôi bỏ sót** nằm ở cuối `common_chat_params_init_qwen3_coder`:

```cpp
// dòng 1201
auto include_grammar = has_response_format ||
                       (has_tools && inputs.tool_choice != COMMON_CHAT_TOOL_CHOICE_NONE);
...
if (include_grammar) {
    data.grammar_lazy = has_tools && inputs.tool_choice == COMMON_CHAT_TOOL_CHOICE_AUTO;
    data.grammar = build_grammar(...);      // <- GBNF ep dung dinh dang XML
    if (data.grammar_lazy)
        for (const auto & start : tool_call_starts)
            data.grammar_triggers.push_back({ ..._WORD, start });   // kich hoat boi "<tool_call>"
}
```

⭐ **Khi có `tools`, llama.cpp không chỉ *phân tích* — nó *cưỡng chế sinh*.**
Một văn phạm GBNF được dựng từ chính schema của tool và ép đầu ra vào đúng khuôn
`<tool_call>\n<function=…>\n<parameter=…>`. Văn phạm ở chế độ **lazy**: nó nằm im
cho tới khi model phát ra `<tool_call>` — và nhánh JSON của template **cũng dùng
đúng thẻ `<tool_call>`** (chỉ khác phần ruột). Model gõ thẻ mở, văn phạm bật, và
từ đó bộ lấy mẫu **không còn đường sinh ra JSON** dù prompt vừa bảo nó thế.

**Văn phạm thắng prompt.** Đó là lý do bẫy không nổ.

### 5c. Luật sửa lại — vẫn giữ, nhưng vì lý do khác và với sức nặng khác

⛔ **Sức nặng cũ (sai):** *"hỏng 0 %, im lặng, thảm hoạ."*
✅ **Sức nặng đúng:** *"prompt và văn phạm mâu thuẫn nhau; đo n=3 vẫn phân tích
được; cái giá về chất lượng thì chưa ai đo."*

Luật giữ nguyên, nhưng nay nó là một luật **vệ sinh**, không phải một luật **an toàn**:

> `tool_call_format` để mặc định. Đặt `json` khiến model bị dạy một đằng và bị
> **ép** sinh một nẻo — nó không vỡ, nhưng nó bắt model làm việc chống lại chính
> chỉ dẫn nó vừa đọc. Chưa ai đo điều đó ăn vào độ chính xác đối số bao nhiêu ở
> ca khó. Không có lợi ích nào bù lại, nên đừng đặt.

Phép kiểm tĩnh vẫn đáng làm, nhưng hạ từ **chốt an toàn** xuống **chốt vệ sinh**,
và chú thích của nó phải nói đúng lý do — một chốt giải thích sai lý do là một
chốt sẽ bị gỡ bởi người đầu tiên đọc kỹ nó.

### 5d. Bài học phương pháp, đắt hơn cả kết luận

Tôi đọc `chat.cpp` đủ để thấy **phép phát hiện** và **bộ phân tích**, rồi dừng
lại và kết luận. Nhưng đường sinh ra token có **ba** chặng, không phải hai:

```
phat hien template  ->  van pham cuong che sinh  ->  bo phan tich doc lai
        (da doc)              (BO SOT)                     (da doc)
```

Chặng giữa là chặng **quyết định hành vi**, và nó nằm ở cuối cùng một hàm mà tôi
đã mở. Một suy luận đọc hai phần ba đường ống thì khớp hoàn hảo với hai phần ba
sự thật — và `gia-thuyet-khop-qua-vua` nói đúng: khớp hoàn hảo là lúc nên nghi,
không phải lúc nên dừng.

⭐ Và đây là lý do phép đo 6 lượt gọi này đáng giá hơn cả §5 gốc: nó tốn **6
credit** và nó bác bỏ một luật mà tôi đã sắp đem đi cưỡng chế bằng một phép kiểm
tĩnh cho toàn kho.

## 6. Một hệ quả thứ hai: `parallel_tool_calls`

`docs/function-calling.md:24` [U]: *"Multiple/parallel tool calling … **disabled
by default**, enable it by passing `"parallel_tool_calls": true`."*

Template hỗ trợ nhiều lời gọi — nó dạy rõ: *"To call multiple functions, output
a separate, completely closed `<tool_call></tool_call>` block for EACH function."*
Nhưng nếu ChatLTT không gửi cờ, năng lực đó **tắt ở tầng runtime**.

⇒ Bộ kiểm "gọi song song" của P01 **phải** gửi `parallel_tool_calls: true`.
Không gửi thì nó đo một thứ đã tắt sẵn rồi kết luận sai về model.

## 7. 🟢 ĐÃ ĐÓNG — phân tích đúng trên **chính build đang chạy**

Bản đầu của mục này để ngỏ: phân tích đọc `chat.cpp` ở **master**, trong khi
production có thể chạy build khác. Đã đóng bằng đo, không bằng suy luận.

**Build thật, hỏi máy B:**

```
& 'H:/LTT_LLM/bin/llamacpp/llama-server.exe' --version
  -> version: 0.3.0-dev (build 10689, commit 57291f264)
     built with Clang 20.1.8 for Windows x86_64
```

**Lấy đúng `chat.cpp` tại commit đó** (`raw.githubusercontent.com/…/57291f264/common/chat.cpp`,
HTTP 200, **174.542 byte** — cùng kích thước với bản master đã đọc), và phép
phát hiện nằm ở **đúng dòng 3597-3601**, nguyên văn:

```cpp
if (src.find("<tool_call>")  != std::string::npos &&
    src.find("<function=")   != std::string::npos &&
    src.find("<parameter=")  != std::string::npos) {
    LOG_DBG("Using specialized template: Qwen3-Coder\n");
    return common_chat_params_init_qwen3_coder(tmpl, params);
}
return std::nullopt;
```

⇒ **Phán quyết NATIVE đúng trên build đang phục vụ**, không phải trên một nhánh
mã mà máy này chưa từng chạy.

⭐ Và một xác nhận đi kèm, đáng giá riêng: `llama-swap.yaml` **trong kho khớp
hoàn toàn** với bản đang chạy trên máy B (`H:\LTT_LLM\gateway\llama-swap.yaml`,
207/208 dòng, chỉ lệch một dòng chú thích; mọi dòng cấu hình **giống hệt**).
Trong một dự án đã năm lần bị tài liệu chép tay nói sai, một bản cấu hình
**không trôi** là điều đáng ghi lại chứ không đáng cho qua.

**Còn một hạng mục xác nhận trực tiếp** (rẻ, làm khi engine nạp lần tới): bật
`--verbose` và đọc dòng `Using specialized template: Qwen3-Coder` trong log.
Đó là runtime **tự khai**, mạnh hơn mọi suy luận từ mã. Nhưng nó nay chỉ là
**xác nhận thừa**, không còn là mắt xích chịu lực.

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
