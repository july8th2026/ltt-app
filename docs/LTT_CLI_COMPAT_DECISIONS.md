# LTT CLI compatibility — audit và quyết định 2026-09-14

Phạm vi: Codex CLI/VS Code, Claude Code/VS Code/Desktop, `cam_cli` và hai cửa
streaming `/api/v1/responses`, `/api/v1/messages`. Backend model, GPU, admission
và queue giữ nguyên.

## Audit chốt trên client đang cài

| Client | Trước bản vá | Upstream/client thật cần | Kết luận và rủi ro |
|---|---|---|---|
| Codex CLI 0.145.0 | provider Responses, context, catalog, idle 600 s; profile luôn rơi về `ltt-3.8` | model đã chọn, auto compact, retry, catalog modality, subagent | **Sai/thiếu:** chọn 3.5 nhưng ghi 3.8; 3.8 bị khai text-only; retry mặc định 4/5; subagent chưa ghim |
| Codex VS Code 0.154.0-alpha.6.2 | cùng provider nhưng phải đặt ở config gốc | cùng contract với CLI vì extension gọi binary Codex | **Thiếu:** docs config gốc chưa có compact/retry/subagent; smoke thật gửi đúng `ltt-3.5` sau vá |
| Claude Code 2.1.270 | base URL/token/model, context, compact, output/MCP; chỉ ghim Haiku | alias Opus/Sonnet/Haiku, subagent model, retry/concurrency hữu hạn | **Thiếu:** Opus/Sonnet/subagent có thể thoát LTT; retry mặc định 10; đồng thời mặc định 20 |
| Claude VS Code 2.1.270 | settings User độc lập với CLI, nhưng cùng các thiếu sót routing | `claudeCode.environmentVariables`, tắt login prompt, terminal mode | **Thiếu:** chọn riêng extension chưa được bảo vệ khỏi alias/subagent và retry amplification |
| Claude Desktop 1.52386.6 | Windows policy gateway, nhưng chỉ phát một route và ghi boolean thành `REG_SZ` | gateway base `/api`, bearer, hai route có tên Claude, boolean/number `REG_DWORD`, ép 3p, restart toàn bộ ứng dụng | **Sai/thiếu:** kiểu registry sai; deployment mode 1p cũ làm app bỏ qua gateway; HTTP loopback bị từ chối; model thứ hai không có trong picker |
| Bộ cài GUI/console + SDK một tệp | hai nhánh ghi cấu hình độc lập | cùng model/context/compact/retry/subagent và cùng catalog modality | **Đã đồng bộ:** cả hai nhánh phát cùng contract; test đối chiếu từng model và từng khóa bắt buộc |
| LTT streaming API | Messages/Responses stream, tools, 413, `Retry-After`; test Responses stream tối giản | vòng đời SSE đầy đủ; 429 có code/scope/reason; 413 trước create-rate | **Sai/thiếu:** test stream làm Codex thật lỗi parse; 413 từng tiêu `create_rpm`; rate 429 thiếu scope/reason |

Nguồn upstream chính: OpenAI Codex config schema và provider source; OpenAI
Responses API event schema; Claude Code `env-vars` và `model-config`. Hành vi cuối
cùng được đối chiếu lại bằng chính ba binary ghi trong bảng, qua HOME tạm và mock
API local không gọi model.

## Quyết định đã khóa

1. ~~**Retry theo công suất cố định:** Codex `request_max_retries=1`,
   `stream_max_retries=0`; Claude `CLAUDE_CODE_MAX_RETRIES=1`.~~ **ĐÃ THAY bởi
   Q128 ngày 15/09/2026** sau khi hai phiên dài lộ ra lỗi capacity tạm thời và
   phép giữ chỗ lệch giữa hai máy. Codex vẫn giữ retry stream như cũ; Claude trở
   về mặc định chính thức 10 lần với exponential backoff.
2. **Ghim mọi đường model và chỉ một subagent:** model chính, Opus, Sonnet,
   Haiku và subagent đều dùng model LTT khách đã chọn; Codex và Claude mỗi phiên
   chỉ mở tối đa một subagent đồng thời. Owner chọn rõ
   “Ghim model; một subagent (khuyến nghị)” ngày 14/09/2026. Việc ghim vẫn giữ
   nguyên sau Q124: người dùng đổi model có chủ ý qua connector; không alias hay
   subagent nào tự thoát sang model ngoài LTT.
3. **Không thêm `/messages/count_tokens` khi client chưa cần:** Claude Code
   2.1.270 hoàn tất smoke Messages/stream/tool metadata mà không gọi route này.
   Server đã tiền kiểm token ở cửa Messages. Đây là giới hạn đã biết, sẽ mở lại
   khi một client được hỗ trợ phát request thật hoặc có contract chính thức bắt
   buộc; mock chỉ có route để thử tương thích khi cần.
4. **Hai model trên mọi client (Q124):** Codex catalog phát cả hai; Claude
   Code/VS Code chọn một model làm mặc định và ghim mọi tác vụ phụ vào đúng model
   đó. Claude Desktop hiển thị đồng thời **LTT 3.8 (Mạnh)** và
   **LTT 3.5 (Nhanh)** bằng `labelOverride`. Trường `name` vẫn dùng hai mã tuyến
   đã có trên production (`ltt-llm-claude-compat` và
   `ltt-llm-claude-compat-35`) vì bộ lọc client bắt tên chứa `claude`; đó là mã
   vận chuyển ẩn, không phải tên sản phẩm. Cách này không đòi thêm alias backend
   hay deploy chỉ để đổi chữ trong picker.
5. **Hàng chờ và retry là hai tầng khác nhau (Q128):** máy A chờ suất tối đa
   300 giây và phát heartbeat 15 giây; Claude dùng `API_TIMEOUT_MS=600000` và
   `CLAUDE_CODE_MAX_RETRIES=10`. Không bật retry watchdog. Máy A truyền đúng
   reservation sang máy B; máy B luôn lấy số lớn hơn giữa phép tự đo và header,
   nên bản cũ hoặc header khai thấp không thể nhận quá pool KV.

Nguồn năng lực Qwen3.5-9B: model card chính thức công bố LiveCodeBench v6 65,6,
BFCL-V4 66,1, context gốc 262.144, tool parser `qwen3_coder`, và cấu hình lấy mẫu
riêng cho precise coding:
<https://huggingface.co/Qwen/Qwen3.5-9B/blob/main/README.md>.

## Contract sau bản vá

- `ltt-3.8`: context công bố 124.245, compact 91.477, output 32.768, tool/MCP
  result 16.384; text và image. (Hạ từ 171.458/138.690 ngày 22/09/2026, L-35 —
  chia `HE_SO_UOC_TREN_THAT` thay vì bớt 8% lệch tokenizer.)
- `ltt-3.5`: context công bố 151.552, compact 118.784, output 32.768, tool/MCP
  result 16.384; text và image. (Hạ từ 209.141/176.373 cùng quyết định.)
- Claude Code 2.1.270 nhận cấu hình output 32.768 nhưng tự báo effective cap
  32.000 cho model ID không nhận diện. Server vẫn giữ contract 32.768; đây là
  giới hạn client đã quan sát, không phải lý do đổi trần server.
- 413 ngữ cảnh không tiêu `create_rpm`, credit hay suất thực thi. Request RPM vẫn
  bảo vệ chính cửa HTTP và vì thế vẫn đếm mọi request đã xác thực.
- 429 rate có `code=rate_limited`, `scope=key|account`,
  `reason=request_rate|create_rate`; 429 công suất có
  `code=concurrency_limited`, `scope=execution` và reason từ admission/upstream.
  Mọi 429 có `Retry-After`.

## Cắm tay trong Claude Desktop — đối chiếu 14/09/2026

Phạm vi hiện tại là Claude Desktop **1.52386.6 đang cài trên máy**, không tự
coi một bản phát hành khác là đã nghiệm thu. Đã đọc schema editor của chính
binary này, hai ảnh người dùng và tài liệu chính thức/community:

- <https://claude.com/docs/third-party/claude-desktop/gateway>
- <https://claude.com/docs/third-party/claude-desktop/configuration#models>

Nguồn cộng đồng và liên kết tới hướng dẫn Stratoclave nằm ở
`docs/PUBLIC_API/HUONG_DAN_CAM_CLI.md` §2.5.

Gateway cần Messages streaming và tool use. LTT đã có `/api/v1/messages`,
Bearer và hai tuyến tương thích; **không cần thêm endpoint để nhập form**.
Base URL kết thúc ở `/api`, vì client tự thêm `/v1/messages`. Discovery là tùy
chọn theo tài liệu upstream: tắt discovery, nhập hai Model ID cố định và
`Display name` tương ứng. Không thay catalog sản phẩm chỉ để vượt bộ lọc Claude.
`labelOverride` là nhãn, `name` là mã gửi trên wire. Đặt tier alias `opus` cho
LTT 3.8 và `haiku` cho LTT 3.5, bật Default cho cả hai để bare alias của app
không thoát khỏi gateway. Để trống artifact origin và custom headers; tắt 1M,
Tool Search và giá USD ước tính.

Editor hỗ trợ New configuration, Save Changes và Apply Changes/relaunch.
Policy do tool quản lý có thể khóa editor: dùng chức năng Gỡ ra trước khi đổi
sang profile nhập tay. Không chỉnh LevelDB hoặc xóa policy tổ chức khác.

**Bằng chứng vận hành:** `tmp/kiem_cli_van_hanh/prod.json` báo API PASS,
connector PASS, hai model đều hiện/chọn/gửi/nhận câu trả lời trên Desktop thật;
key thử nghiệm tạo và thu hồi thành công, cấu hình Desktop được phục hồi.
Đây là phép thử qua tool. Form nhập tay đã đối chiếu schema, chưa có bằng chứng
nghiệm thu thao tác nhập tay end-to-end. Không suy rộng sang toàn bộ Cowork/Code
hoặc prompt caching Anthropic; upstream mô tả gateway cho Claude models, không
chứng nhận Qwen tương thích.

Hướng dẫn dùng chung cho `/huong-dan` và `/developers/cli`, có bản Việt/Anh,
bảng điền chính xác, scope/credit, hai câu hỏi nghiệm thu, restart và xử lý lỗi.
Playwright kiểm bốn tổ hợp ngôn ngữ/kích thước: PASS, 0 console errors,
0 failed requests, không tràn ngang. Thay đổi chỉ ở repo, chưa deploy trang live.

## Bổ sung 15/09 — cắm tay Codex, 401 và token trên Desktop

Owner xác nhận Test connection xanh khi đổi cùng khóa từ x-api-key sang Bearer.
Server chỉ đọc Authorization: Bearer; giữ nguyên hợp đồng, không thêm đường
xác thực mới. 401 không chứng minh lỗi scope hay allowed_tools. Trang khóa trước
đây không hiện trạng thái all-tools và ẩn fieldset khi catalog rỗng; đã sửa để
hiện rõ, không tự cấp thêm scope. Empty tools = mọi công cụ **công khai đang mở**;
empty scopes = tools:read/jobs:read, không có jobs:create.

Đã gỡ dấu vết tool trên máy qua EXE và CLI `go`, quét lại sạch LTT. Giữ bản sao
lưu `.truoc-ltt` ban đầu; khởi động lại Desktop sau cleanup. Profile Gateway owner
tự nhập sau đó không bị gỡ lần nữa và không đọc giá trị key từ ô được che.

Codex CLI 0.145.0: provider `/api/v1`, Responses/Bearer env_key, JSON catalog
hai model và tệp riêng `ltt.config.toml` / `ltt-fast.config.toml`. Catalog/path/
context/compact/subagent theo đúng model. Hai profile sinh từ trang hướng dẫn
đã chạy bằng binary cài thật với server mock: metadata được nhận, nhận SSE mẫu,
wire gửi đúng ltt-3.8/ltt-3.5. Báo cáo `tmp/kiem_cli_van_hanh/codex-manual.json`.
Đây không phải bằng chứng model thật trả 42. Chưa xác minh Gateway GUI trong
Codex Desktop 26.721.11231.0; không dùng ô OpenAI API key hoặc MCP để cắm LTT.

Đọc mới tài liệu Claude model-config/env-vars/Desktop/configuration và issue
cộng đồng, nguồn đầy đủ ở `docs/PUBLIC_API/HUONG_DAN_CAM_CLI.md` §2.5. Tắt 1M
không tự đặt 171K. UI Automation đọc vòng Usage `48.1k / 200k (24%)` rồi `58.1k
/ 200k (29%)` trong Code đang mở; owner sau đó xác nhận thấy 200K. Năm ảnh 16–20
không hiện số này: đã sửa phát biểu nhầm nguồn bằng chứng. Ảnh 21 là phiên Code
đang chạy, không có ô môi trường; nút Local đã xác minh ở màn hình **New**.
Ảnh 22 owner gửi đã xác nhận mở đúng **Edit local environment**, nhập đúng
ba giá trị 171458/138690/32768; chưa xác nhận phiên mới đã đọc giới hạn.

Hướng dẫn nhập biến qua Local environment editor, dùng cửa sổ/ngưỡng nén của
model hẹp hơn cho cả hai, output/MCP/subagent/retry giới hạn. Không tuyên bố đã
áp giới hạn vào phiên owner đang chạy hoặc nghiệm thu nén hội thoại dài. Local
Code env không được suy rộng sang tab Chat/Cowork chưa thử. Backend đã có trần
input/output/body và admission theo slot + pool KV; không tăng GPU/queue/retry.

GUI hướng dẫn PASS 4/4 Việt/Anh × 1440/390px, kể cả JSON catalog mở được và đúng
hai model. GUI khóa PASS 4/4, tạo khóa test với scope jobs:create, empty tools
hiện unrestricted và GET lại không hiện bí mật; 0 console errors/request hỏng.
Một lần harness dùng reload sau POST đã resubmit và tạo **khóa mới**; sửa phép
đo dùng GET, không quy nhầm thành backend khôi phục bí mật cũ.

L3 đầu hoàn tất **32/33 PASS**; bộ test có 3 lỗi (link GitHub bị regex coi là
file local, assertion registry cũ, Q124 thiếu heading). Cả ba đã sửa và chạy lại
PASS. Nhóm mở rộng 229 passed/4 skipped, một lỗi prose EN còn nhãn Việt đã sửa;
nhóm i18n chạy lại 13 passed/1 skipped. L3 cuối sẽ ghi riêng khi có kết quả thật.

## Bổ sung 15/09 — bằng chứng phiên dài và Q125

Ảnh 24/28 xác nhận môi trường Local đã nhận preset 3.8: `46.8k / 138.7k`, sau
đó `99.6k / 138.7k`, buffer khoảng 33k và tự nén ở 76%. Đây là bằng chứng trực
tiếp, thay cho trạng thái 200K trước khi cấu hình. Tổng công bố vẫn 171.458;
Claude dùng 138.690 để tính nén và chừa 32.768 cho output.

Ảnh 27 là lỗi khác: request retry có `stream:false`, input ước 98.678 và không
còn output trong ngân sách JSON 90 giây. Tài liệu Claude hiện hành định nghĩa
`CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK=1` để lỗi stream đi về tầng retry
thay vì đổi giao thức. Issue `anthropics/claude-code#88110` đo cùng hành vi và
`#40316` ghi nhận retry làm phiên dài phình thêm. Vì vậy Q125 giữ một retry nhưng
cấm fallback non-streaming; không nới cửa JSON hoặc bỏ đồng hồ Cloudflare.

Ảnh 28 đo thêm 131 MCP tools chiếm khoảng 65K. Tài liệu Claude nói Tool Search
tự tắt với custom `ANTHROPIC_BASE_URL`, vì proxy phải hỗ trợ `tool_reference`.
LTT hiện không có hợp đồng/kiểm thử đó. Q125 giữ `ENABLE_TOOL_SEARCH=false` và
hướng dẫn tắt Connector/Plugin không dùng; `MAX_MCP_OUTPUT_TOKENS` chỉ giới hạn
tool result, không giảm schema. Auto permission mode cũng không có trên
third-party provider. Bypass phải được bật trong Settings rồi chọn trước câu
đầu của một phiên Local mới; ảnh 25 đo việc đổi trong phiên đang chạy bị từ chối.
