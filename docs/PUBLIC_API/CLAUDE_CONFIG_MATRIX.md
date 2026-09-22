# Ma trận cấu hình Claude ↔ LTT Gateway

**Chốt Q126 · 2026-09-15 · Claude Desktop 1.52386.6 · Claude Code 2.1.270**

Tài liệu này là bảng chuẩn duy nhất. Trang API sinh danh sách từ
`platform_core.public_api.examples`; tool, tài liệu và test phải dùng cùng dữ
liệu đó. Không ghép thêm danh sách cũ.

## Kết luận kỹ thuật

LTT không bị hạ chất lượng vì dùng API ngoài. Model vẫn chạy với cửa sổ engine
221.184 token (LTT 3.8) hoặc 262.144 token (LTT 3.5), output tối đa 32.768.
LTT 3.8 mặc định `medium` (L-33, 19/09 — máy chủ chèn khi client bỏ trống; `xhigh` vẫn chọn được); LTT 3.5 giữ thinking bật và template tương thích dùng
`medium` khi client không gửi effort. Client phải nén sớm hơn trần engine để còn chỗ
cho output và sai khác tokenizer. Đây là phần dự trữ chống lỗi 413, không phải
cắt khả năng suy luận của model.

Claude Code không biết metadata của hai tên LTT nên cần khai cửa sổ. Claude
Desktop còn quản lý provider và model picker ở tầng host, nên biểu mẫu Gateway
và Local environment là hai lớp khác nhau: lớp đầu định tuyến/xác thực, lớp sau
điều khiển context, retry và subagent của Code.

## 1. Biểu mẫu Gateway

| Trường | Giá trị chuẩn |
|---|---|
| Connection | `Gateway` |
| Credential kind | `Static API key` |
| Gateway base URL | `https://app.lttstudios.com/api` |
| Gateway API key | khóa LTT còn hạn; không ghi vào tài liệu |
| Gateway auth scheme | `Bearer` |
| Artifact preview iframe origin | để trống |
| Custom inference headers | để trống |
| Stream idle timeout | `600` giây |
| Model discovery | `Off` |
| Default to 1M context | `Off` |
| Show estimated cost | `Off` |
| Tool Search | `Off` / không bật `toolSearchEnabled` |

`Bearer` gửi `Authorization: Bearer <key>`, đúng hợp đồng LTT. `x-api-key` gửi
header khác và đã đo trả 401. URL kết thúc ở `/api`; Desktop tự nối
`/v1/messages`.

Theo [Configuration reference của Claude Desktop](https://claude.com/docs/third-party/claude-desktop/configuration#gateway),
timeout 600 nằm trong miền hợp lệ 300–1800 giây và chỉ có tác dụng khi gateway
gửi SSE ping. LTT gửi heartbeat, nên giá trị này khớp hai đầu. Tăng timeout không
tăng context hay năng lực model.

## 2. Hai model trong Model list

| Thứ tự | Model ID | Display name | 1M | Tier alias | Default for tier |
|---:|---|---|---|---|---|
| 1 | `ltt-llm-claude-compat` | `LTT 3.8 (Mạnh)` | Off | `opus` | On |
| 2 | `ltt-llm-claude-compat-35` | `LTT 3.5 (Nhanh)` | Off | `haiku` | On |

Model ID là tên tuyến LTT đã qua bộ lọc của Desktop; Display name là nhãn người
dùng thấy. `anthropicFamilyTier` chỉ ánh xạ bare alias nội bộ của app. Tài liệu
Claude nói rõ tier mapping dùng để bare alias và fallback gửi đúng model của
gateway; nó không đổi `name` mà app gửi và không đổi nhãn hiển thị
([Models configuration](https://claude.com/docs/third-party/claude-desktop/configuration#models)).

Gắn `haiku` vào LTT 3.5 đưa công việc nền về tuyến nhanh. Gắn `opus` vào LTT 3.8
đưa tier mạnh về tuyến mạnh. Các subagent được chốt theo model chính bằng biến
FORCE ở mục 3, nên agent `sonnet`/`fable` trong định nghĩa riêng không thoát ra
một model ngoài LTT.

## 3. Local environment: đúng 11 dòng

> ⚠️ **`AUTO_COMPACT_WINDOW` là CỬA SỔ, không phải ngưỡng** (R-05, đo 18/09). Claude Code
> nén ở `min(AUTO_COMPACT_WINDOW, cửa sổ) − min(MAX_OUTPUT_TOKENS, 20.000) − 13.000`.
> Đo thật Claude Code 2.1.274 trỏ về LTT: `/context` in `Autocompact buffer 33k` ở mọi
> cửa sổ; khớp mã client và tài liệu (cửa sổ 1M nén “at about 967K” = 1M − 33K).
> Trước 18/09 ta khai 138.690 ⇒ Claude nén ở 105.690 (76 %), sớm 33.000 token so với
> Codex. Giá trị đúng = cửa sổ công bố (124.245 / 151.552, hạ 22/09 — L-35, chia
> `HE_SO_UOC_TREN_THAT`) ⇒ nén ở 91.245 / 118.552, ≤ ngưỡng Codex (91.477 / 118.784).
> Nguồn: `HoSoModel.cua_so_nen_claude` trong hai bộ cài;
> `tests/test_1440_nen_claude_tach_codex.py`.

Preset dùng chung an toàn khi chuyển qua lại hai model:

```dotenv
CLAUDE_CODE_MAX_CONTEXT_TOKENS=124245
CLAUDE_CODE_AUTO_COMPACT_WINDOW=124245
CLAUDE_CODE_MAX_OUTPUT_TOKENS=32768
MAX_MCP_OUTPUT_TOKENS=16384
CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS=1
CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=1
CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1
CLAUDE_CODE_MAX_RETRIES=10
API_TIMEOUT_MS=600000
CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK=1
ENABLE_TOOL_SEARCH=false
```

Nếu môi trường **chỉ** dùng LTT 3.5, thay đúng hai dòng đầu:

```dotenv
CLAUDE_CODE_MAX_CONTEXT_TOKENS=151552
CLAUDE_CODE_AUTO_COMPACT_WINDOW=151552
```

Chín dòng còn lại giữ nguyên. Không dùng preset 3.5 rồi đổi sang LTT 3.8 vì khi
đó client tin một cửa sổ lớn hơn tuyến thật.

| Biến | Vì sao có mặt |
|---|---|
| `MAX_CONTEXT_TOKENS` | Sửa cửa sổ 200K mà Claude đoán cho model ID lạ. |
| `AUTO_COMPACT_WINDOW` | Là cửa sổ, không phải ngưỡng: Claude tự trừ 33.000 ⇒ nén ở 91.245/118.552, ≤ ngưỡng Codex 91.477/118.784 (R-05). |
| `MAX_OUTPUT_TOKENS` | Khớp trần output thật của LTT. |
| `MAX_MCP_OUTPUT_TOKENS` | Chặn một kết quả MCP nuốt hết vùng dự trữ; không giới hạn schema tool. |
| `MAX_CONCURRENT_SUBAGENTS` | Chỉ một agent phụ chạy đồng thời; LTT có ba lane chia sẻ. |
| `MAX_SUBAGENT_SPAWN_DEPTH` | Giá trị 1 tắt agent lồng nhau. |
| `SUBAGENT_MODEL_FORCE` | Khi không đặt `SUBAGENT_MODEL` trong Desktop, mọi subagent dùng model chính đang chọn. |
| `MAX_RETRIES` | `10`, đúng mặc định chính thức của Claude Code; lỗi tạm thời được thử lại với exponential backoff. Không bật retry watchdog vì chế độ đó có thể thử lại 429/529 vô hạn và chỉ phù hợp phiên không người trông. |
| `API_TIMEOUT_MS` | 600.000 ms cho mỗi API call, khớp trần chính thức mặc định và trường idle timeout 600 giây. |
| `DISABLE_NONSTREAMING_FALLBACK` | Stream lỗi đi về retry streaming, không đổi sang request JSON dài bị cửa 90 giây từ chối. |
| `ENABLE_TOOL_SEARCH=false` | LTT chưa nhận `tool_reference`; giữ schema thường để request không 400. |

Các ngữ nghĩa trên đến từ bảng [Environment variables](https://code.claude.com/docs/en/env-vars)
và [Subagents](https://code.claude.com/docs/en/sub-agents#run-every-subagent-on-one-model)
của Claude Code. FORCE cần 2.1.257+, depth/concurrency cần 2.1.217+; engine đang
cài là 2.1.270.

Ảnh vận hành ngày 15/09 xác nhận preset 3.8 hiện `46.8k / 138.7k`, sau đó
`99.6k / 138.7k`, buffer khoảng 33K và tự nén ở 76% — tức preset CŨ nén sớm 33K
(R-05, sửa 18/09: preset mới hiện `/ 171.5k`, nén ở 138.458). Lỗi đã chụp khác loại:
fallback `stream:false` mang 98.678 input token vào cửa non-streaming nên nhận
400. Đây là lý do giữ biến disable fallback.

## 4. Claude Code CLI/VS Code: thêm các khóa chọn model

CLI và extension không có picker host của Desktop. Ngoài 11 biến ở trên, mỗi
profile phải ghim toàn bộ đường chọn model về cùng `ltt-3.8` hoặc `ltt-3.5`:

```dotenv
ANTHROPIC_MODEL=ltt-3.8
ANTHROPIC_DEFAULT_MODEL=ltt-3.8
ANTHROPIC_DEFAULT_HAIKU_MODEL=ltt-3.8
ANTHROPIC_DEFAULT_OPUS_MODEL=ltt-3.8
ANTHROPIC_DEFAULT_SONNET_MODEL=ltt-3.8
ANTHROPIC_DEFAULT_FABLE_MODEL=ltt-3.8
CLAUDE_CODE_SUBAGENT_MODEL=ltt-3.8
```

Khi chọn profile 3.5, đổi cả bảy giá trị thành `ltt-3.5`. FORCE khiến model do
agent definition hoặc lời gọi riêng yêu cầu không vượt qua pin. `default` và
`fable` có trong Claude Code hiện hành; không có biến chính thức
`ANTHROPIC_DEFAULT_MYTHOS_MODEL`, nên không thêm một khóa giả. Các alias hiện
hành và thứ tự ưu tiên được mô tả trong
[Model configuration](https://code.claude.com/docs/en/model-config#model-aliases).

Hai biến xác thực/địa chỉ của CLI là:

```dotenv
ANTHROPIC_BASE_URL=https://app.lttstudios.com/api
ANTHROPIC_AUTH_TOKEN=<đọc an toàn từ LTT_API_KEY>
```

## 5. Những biến phải để unset

| Biến | Quyết định |
|---|---|
| `CLAUDE_CODE_DISABLE_1M_CONTEXT` | Bỏ. Hai ID LTT không có `[1m]`; `MAX_CONTEXT_TOKENS` áp trực tiếp. |
| `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` | Bỏ. Đã khai ngưỡng token chính xác; phần trăm sẽ ghi đè một lớp thứ hai. |
| `MAX_THINKING_TOKENS` | Bỏ. Có thể đổi/tắt thinking; LTT đã đo `none` làm output sụp từ khoảng 1.180 xuống 2 token. |
| `CLAUDE_CODE_ALWAYS_ENABLE_EFFORT` | Bỏ. Tên custom chưa khai capability effort của Claude và LTT stream chuyển body xuống engine; ép trường lạ có thể 400. |
| `CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY` | Bỏ. Nó giới hạn cả tool đọc local, không phải lane inference LTT. |
| `CLAUDE_STREAM_IDLE_TIMEOUT_MS` | Bỏ trong Desktop. Form Gateway 600 giây có ưu tiên và đã cùng giá trị. |
| `CLAUDE_CODE_DISABLE_UNKNOWN_MODEL_WINDOW_ENFORCEMENT` | Bỏ. Nó chờ API từ chối quá dài rồi mới phục hồi, trái với nén chủ động. |
| `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS` | Bỏ. Host Gateway đã suppress beta; đặt nó còn khóa Tool Search bất kể biến khác. |
| `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB` | Tùy chọn bảo mật riêng; không thuộc preset tương thích vì có thể làm MCP cần credential ngừng chạy. |

Không đặt biến reasoning/effort toàn cục để server áp đúng hồ sơ từng model:
3.8 `medium` (L-33), 3.5 thinking bật. Người dùng API trực tiếp vẫn có thể chọn
`low|medium|xhigh` theo từng request nhờ template tương thích; đây là điều khiển
tương thích ở 3.5, không phải enum do model card 3.5 công bố. Claude Desktop
không cần ép thêm trường đó. Cửa Public API `text.chat` cũng dùng cùng mặc định
theo model; schema không còn điền một `xhigh` chung cho cả hai.

## 6. Hàng chờ khi chạy nhiều phiên

Claude Code tự retry lỗi server, overload, timeout và kết nối tạm thời theo
exponential backoff; mặc định là 10 retry. Preset LTT đặt `10`. Mỗi retry có
timeout riêng, nên tăng retry lên 10 không tạo một hàng chờ tốt hơn mà có thể
kéo dài và nhân tải khi hai hội thoại rất lớn cùng gọi một model.

Hàng chờ chính nằm ở LTT: stream được chờ tối đa 300 giây, có heartbeat mỗi 15
giây, trước khi model bắt đầu trả chữ. Pool KV mới là giới hạn thật: ba slot
không có nghĩa ba phiên gần trần luôn cùng chạy được. Nếu tổng reservation của
hai phiên LTT 3.8 vượt 221.184 token, phiên sau chờ; LTT 3.5 có pool/GPU riêng.
Muốn hai phiên chạy đồng thời ngay, chọn LTT 3.8 cho một phiên và LTT 3.5 cho
phiên kia. `MAX_CONCURRENT_SUBAGENTS=1` chỉ giới hạn agent phụ trong từng phiên,
không giới hạn hai phiên chính độc lập.

Sự cố 15/09/2026 xác nhận hai reservation 148.593 + 79.848 vượt pool LTT 3.8.
Bản vá làm máy A đếm cả `tool_use`/`tool_result`, truyền reservation của lease
sang máy B và buộc máy B lấy số lớn hơn giữa header với phép đo của chính nó.
Nhờ đó yêu cầu thứ hai ở lại hàng chờ thay vì lọt qua rồi nhận 529.

## 7. Tool Search và tải token MCP

Claude Desktop 1.52386.6 bundle Claude Code 2.1.270 nên có cơ chế gateway-safe
Tool Search. Tuy nhiên bật `toolSearchEnabled` làm request chứa beta tool-search,
deferred schemas và `tool_reference`; tài liệu cảnh báo endpoint không nhận hình
dạng đó sẽ trả 400
([Desktop Tool Search](https://claude.com/docs/third-party/claude-desktop/configuration#toolsearchenabled-details)).
LTT hiện nhận tool definition/tool call/tool result thường, chưa có test
`tool_reference`, nên quyết định đúng là tắt.

Hệ quả: schema của connector/plugin đã bật được đưa vào context. Trong ảnh 28,
131 MCP tool chiếm khoảng 65K trên cửa sổ nén 138.7K. `MAX_MCP_OUTPUT_TOKENS`
chỉ chặn **kết quả** của một tool, không làm nhỏ 65K schema. Cần tắt connector và
plugin không dùng, giữ tổng MCP tools khoảng dưới 10% cửa sổ nén khi có thể.

## 8. Đối chứng cộng đồng

Các issue dưới đây là báo cáo người dùng, không phải đặc tả. Chúng được dùng để
kiểm chế độ hỏng mà tài liệu chính thức mô tả:

- [claude-code #87930](https://github.com/anthropics/claude-code/issues/87930): stream lỗi rơi sang non-streaming; biến disable fallback tránh đường này.
- [claude-code #40314](https://github.com/anthropics/claude-code/issues/40314): Tool Search từng không defer HTTP MCP và vẫn inline context lớn.
- [claude-code #83355](https://github.com/anthropics/claude-code/issues/83355): subagent khác model có thể nhận sai cửa sổ compact toàn cục.
- [claude-code #65966](https://github.com/anthropics/claude-code/issues/65966): các bản cũ từng áp context override sai cho provider ngoài; đặc tả hiện tại ghi hành vi từ 2.1.193.
- [claude-ai-mcp #829](https://github.com/anthropics/claude-ai-mcp/issues/829): tải toàn bộ connector schema trong 3P có thể làm đầy context rất nhanh.

## 9. Dấu hiệu nghiệm thu

1. `Test connection` xanh với Bearer.
2. Picker chỉ hiện LTT 3.8 (Mạnh) và LTT 3.5 (Nhanh).
3. Phiên Local mới dùng preset chung hiện khoảng `/ 124.2k` và `Autocompact buffer 33k`, không còn `/ 200k` hay `/ 171.5k`.
4. Chạy một subagent rồi xem `/tasks`: model phải là model chính đang chọn.
5. Subagent không thể sinh tầng con và không có hơn một subagent chạy đồng thời.
6. Một stream lỗi không tạo request tiếp theo với `stream:false`.
7. Logs/Usage của LTT ghi đúng model, token và credit.

Nếu một mục không đạt, giữ nguyên bảng chuẩn và chẩn lớp không đạt; không thêm
một biến mới trước khi đối chiếu bảng biến chính thức, wire request và test hồi
quy.
