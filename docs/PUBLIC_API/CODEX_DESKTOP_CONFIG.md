# Ma trận cấu hình Codex Desktop qua LTT API

**Chốt ngày:** 2026-09-15  
**Bản đã đo trên máy:** Codex Desktop `26.721.11231.0`, app-server
`0.146.0-alpha.3.1`; Codex CLI `0.145.0`; extension Codex
`26.908.40401`, binary `0.154.0-alpha.6.2`.

Trang khách `/huong-dan`, bề mặt **Codex Desktop**, là hướng dẫn thao tác. Tệp
này ghi nguồn, lý do chọn giá trị và giới hạn đã biết để lần sau không suy lại.

## 1. Hợp đồng cấu hình

Codex Desktop không có form Gateway tương đương Claude Desktop. Nó khởi động
app-server và đọc cấu hình cấp người dùng từ `%USERPROFILE%\.codex\config.toml`.
Provider phải nằm ở `[model_providers.ltt]`; model Desktop phải nằm ở gốc vì
Desktop không truyền `--profile`.

| Khóa | Giá trị LTT | Lý do |
|---|---|---|
| `model_provider` | `ltt` | ID ổn định được lưu với thread; không đổi tên |
| `base_url` | `https://app.lttstudios.com/api/v1` | Codex tự nối `/responses` |
| `env_key` | `LTT_API_KEY` | Bí mật sống ngoài TOML; provider gửi Bearer |
| `wire_api` | `responses` | Giá trị wire duy nhất Codex hỗ trợ cho custom provider |
| `requires_openai_auth` | `false` | Không buộc đăng nhập OpenAI khi dùng LTT |
| `supports_websockets` | `false` | Cổng LTT stream Responses bằng SSE |
| `request_max_retries` | `1` | Một retry trước stream, không khuếch đại tải |
| `stream_max_retries` | `0` | Không phát lại stream đã mở |
| `stream_idle_timeout_ms` | `600000` | Dành 10 phút cho lượt dài |
| `model_reasoning_effort` | `low` | Mặc định đã đo: còn ngân sách cho câu trả lời |
| `model_reasoning_summary` | `none` | Cổng không công bố reasoning summary riêng |
| `model_auto_compact_token_limit_scope` | `total` | Tính trên toàn context |
| `tool_output_token_limit` | `16384` | Một tool result không ăn hết khoảng dự phòng |
| `max_concurrent_threads_per_session` | `1` | Một subagent đồng thời theo lane đã chốt |
| `default_subagent_reasoning_effort` | `low` | Cùng ngân sách đầu ra với lượt chính |

`supports_standalone_web_search = false` có trong schema web mới và mặc định là
false, nhưng Codex CLI 0.145 trên máy từ chối khóa này ở `--strict-config`.
Vì vậy cấu hình copy không ghi khóa đó: hành vi vẫn false và cùng một tệp chạy
được trên cả ba bộ đọc.

## 2. Hai model

| Tên hiển thị | Wire model | Context | Compact | Max output | Một tool result |
|---|---:|---:|---:|---:|---:|
| LTT 3.8 (Strong) | `ltt-3.8` | 171,458 | 138,690 | 32,768 | 16,384 |
| LTT 3.5 (Fast) | `ltt-3.5` | 209,141 | 176,373 | 32,768 | 16,384 |

Context và compact lấy từ `apps/ltt_llm/ngan_sach.py`. Catalog và hai cấu hình
được sinh bởi `platform_core/public_api/examples.py`; test đối chiếu từng dòng
với nguồn ngân sách, không duy trì một bảng số thứ hai trong code.

`model_catalog_json` là đường dẫn tuyệt đối và chỉ được đọc khi khởi động. Tệp
catalog thay danh mục tích hợp trong lúc cấu hình LTT hoạt động. Hai model nhận
đúng metadata, context, compact, modalities và tool contract; Codex không đoán
metadata của model OpenAI khác.

## 3. Chọn model và thread

Desktop hiện chưa có provider-aware model picker đáng tin cậy cho custom
provider. Cách được hỗ trợ trong sản phẩm LTT là chọn một trong hai khối gốc,
thoát hẳn Desktop, mở lại và tạo thread mới. CLI vẫn dùng hai file profile
`ltt.config.toml` và `ltt-fast.config.toml` với `--profile`.

Tiện ích Codex trong VS Code tự đọc cùng `$CODEX_HOME/config.toml` khi chạy dưới
cùng tài khoản Windows và cùng `CODEX_HOME`; không có một form Gateway riêng và
không cần cắm LTT dưới dạng MCP. `LTT_API_KEY` phải có trong môi trường của tiến
trình VS Code, vì vậy sau khi đặt biến môi trường người dùng cần đóng toàn bộ
cửa sổ VS Code, mở lại và tạo chat mới. Một dự án tin cậy có thể đặt
`.codex/config.toml`; khóa `model` trong đó có thể ghi đè model gốc, nhưng Codex
bỏ qua `model_provider` và `model_providers` trong cấu hình dự án. Provider LTT
và khóa xác thực vì thế phải ở cấu hình người dùng.

Giữ ID provider `ltt` cố định. Các issue upstream cho thấy đổi hoặc xóa provider
có thể làm lịch sử cũ biến mất hoặc không resume được. Không sửa SQLite/index
của Desktop để ép đổi model cho thread đã tồn tại.

`default_subagent_model` chỉ là mặc định. Một spawn có thể chỉ định model khác;
gateway mới là hàng rào fail-closed chặn tên ngoài hai model được cấp quyền.
Giới hạn một thread phụ giảm cạnh tranh lane nhưng không phải allowlist model.

## 4. Phạm vi tương thích

Chat agent chính, shell, apply_patch và tool tĩnh dùng Responses API của LTT.
Một số tính năng app-only chưa đi qua custom provider: preview selection Edit
có thể gọi endpoint OpenAI; Browser/Computer Use và dynamic tool discovery chưa
được cung cấp đầy đủ. Không mô tả các chức năng này là lỗi key hoặc hứa chúng đã
được LTT hỗ trợ.

Nguồn chính thức:

- [Configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference)
- [Configuration basics and precedence](https://learn.chatgpt.com/docs/config-file/config-basic)
- [Environment variables](https://learn.chatgpt.com/docs/config-file/environment-variables)
- [Codex on Windows](https://learn.chatgpt.com/docs/windows/windows-app)
- [Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)
- [Current JSON schema](https://learn.chatgpt.com/docs/config-schema.json)

Đối chứng cộng đồng/upstream:

- [#15364 — model switching](https://github.com/openai/codex/issues/15364)
- [#19694 — catalog loaded but picker filters it](https://github.com/openai/codex/issues/19694)
- [#29156 — provider-aware picker](https://github.com/openai/codex/issues/29156)
- [#37315 — app-only Edit](https://github.com/openai/codex/issues/37315)
- [#31750 — dynamic tools](https://github.com/openai/codex/issues/31750)
- [#35932 — custom-provider subagents](https://github.com/openai/codex/issues/35932)
- [#37122 — `/models` internal schema](https://github.com/openai/codex/issues/37122)
- [#22484 — provider ID and history](https://github.com/openai/codex/issues/22484)

## 5. Phép đo bắt buộc khi đổi schema

1. Parse TOML và đối chiếu ngân sách bằng `test_294`.
2. Chạy `python tests/test_1262_cli_operational_harness.py --codex-binary <path>`
   lần lượt với CLI ổn định, binary trong Codex Desktop và binary extension
   đang cài.
3. `config/read` phải trả đúng `model` + `model_provider=ltt`; `model/list` phải
   trả đúng hai slug, hai display name.
4. Render `/huong-dan` Việt/Anh ở 1440 px và 390 px; đổi tab, parse catalog JSON,
   kiểm console error và failed request.
5. Chỉ chạy gate đầy đủ sau cùng.
