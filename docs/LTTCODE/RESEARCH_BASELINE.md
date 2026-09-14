# LTTCODE — RESEARCH_BASELINE

> **Trạng thái:** Phase 0 (RESEARCH) hoàn tất. Chưa có code sản phẩm.
> **Lập:** 2026-09-14 · Cây `main` @ `22841303`, hồ sơ `NORMAL`.
> **Mục đích:** nền bằng chứng cho Superpower Decision Session → `DECISION_LOCK.md`.

## Quy ước bằng chứng

Mỗi kết luận gắn một nhãn nguồn. `INFERENCE` **không** được coi là fact.
Chỗ chưa đủ bằng chứng ghi `UNVERIFIED`.

`LTT_SOURCE` · `UPSTREAM_SOURCE` · `OFFICIAL_DOC` · `GITHUB_ISSUE` ·
`GITHUB_DISCUSSION` · `COMMUNITY_IMPLEMENTATION` · `LIVE_TEST` · `INFERENCE` ·
`UNVERIFIED`

Chi tiết đầy đủ nằm ở 3 tệp nghiên cứu thô (scratchpad phiên):
`research_dsh_core.md`, `research_desktop_updater.md`, và bản audit API LTT
(nội dung đã hợp nhất vào §2 dưới đây).

---

# 1. DeepSeek Harness (DSH) — upstream

### 1.1 Danh tính & mốc pin
- Kho chính thức: `deepseek-ai/deepseek-harness` — org DeepSeek. `UPSTREAM_SOURCE`
- Giấy phép: **MIT** (Copyright 2026 DeepSeek). `UPSTREAM_SOURCE`
- Ngôn ngữ: **TypeScript ESM**, monorepo **pnpm**. Nhánh mặc định `master`.
- Cài: `npx @deepseek-ai/dsh web`. **Đã có sẵn app desktop Electron** trong
  repo (`apps/desktop`, đóng gói Windows/NSIS, `package:desktop:win:x64`).
  `UPSTREAM_SOURCE`
- ⚠️ **Developer-preview.** README ghi rõ *"THERE WILL BE
  COMPATIBILITY-BREAKING CHANGES"*; mọi release đến nay đều là prerelease;
  nhịp phát hành **~hằng ngày**. `UPSTREAM_SOURCE`
- **Mốc pin đề xuất:** commit `fb2c4b9e698e30edb738bca4cf0618587db7d203`
  = tag `dsh-v0.1.5-rc.2` (mới nhất, 2026-09-10). `UPSTREAM_SOURCE`

### 1.2 Kiến trúc — "Everything is a Plugin"
Trích `docs/architecture.md`: *"There is no privileged core to patch: you
extend dsh by mounting a plugin beside the others, and registrations are
effects that unwind when their plugin unloads."* `UPSTREAM_SOURCE`

- Nền plugin là **Cordis** (IoC/effect framework). Mọi thứ — model adapter,
  tool, session log, agent loop — là một plugin.
- Tuỳ biến = **profile + bundle + patch layer `cordis.yml`**, KHÔNG sửa core.
- Application-launch bị khoá vào các profile `dsh` (gác bởi
  `verify-application-entrypoints`) ⇒ **LTT phải ship dưới dạng profile/bundle,
  không tạo entrypoint mới.** `UPSTREAM_SOURCE`
- LLM runtime: Service Definition `@deepseek-ai/dsh-llm` mount là `ctx.llm`
  (`LlmRuntime`), **provider-neutral**, không chứa wire code.

### 1.3 Cửa gắn LTT Provider Adapter (mấu chốt)
Hai cách gắn LTT **không đụng core**: `UPSTREAM_SOURCE`
1. **Adapter plugin (thin):** `class LttAdapter extends LlmAdapter { async
   *stream(options): AsyncIterable<StreamChunk> }`, rồi
   `ctx.llm.registerAdapter(['ltt'], new LttAdapter())`. Chỉ `stream()` là bắt
   buộc; `resolveModel`/`listModels`/`providerRetryPolicy`/`prepareCall` là
   override tuỳ chọn. Một adapter một route (`DUPLICATE_ADAPTER` nếu trùng),
   đăng ký kiểu effect an toàn với HMR.
2. **Không code:** cấu hình provider có sẵn `dsh-llm-pi-ai` bằng route
   `openai-completions` / `openai-responses` / `anthropic-messages`
   (`baseURL`, `apiKeyEnv`, `models`, `compat` tuỳ biến).

**Nghĩa vụ của adapter** (`docs/cookbook/adding-an-llm-adapter.md`, `types.ts`):
DSH **không** giả định OpenAI-compat toàn cục — mỗi adapter tự dịch wire của nó
sang `StreamChunk` trung tính: `block-start → text/reasoning/tool-call-delta →
block-end → usage → finish`. Bắt buộc:
- phát `usage` **trước** `finish` (không gì sau `finish`);
- giữ `arguments` của tool-call là **chuỗi JSON thô**;
- map lỗi về **mã trung tính** (`AUTH`, `RATE_LIMIT`,
  `CONTEXT_WINDOW_EXCEEDED`, …) qua throw hoặc `finish{error}`;
- tôn trọng `options.signal` (huỷ);
- **luôn kèm `attributionHeaders()` trên mọi request.** `UPSTREAM_SOURCE`

**DSH hỗ trợ:** streaming SSE, tool calling, parallel tool calls (phía loop,
mặc định 10), reasoning-effort levels, vision input.
**DSH CHƯA hỗ trợ (thêm = sửa core):** `tool_choice`, `top_p`, penalties,
structured/JSON output — `GenerateOptions` chỉ có `temperature`/`maxTokens`/
`stop`. `UPSTREAM_SOURCE`

### 1.4 Rủi ro DSH
- GitHub Issues **không dùng** (0 open/0 closed; bug đi qua Discussions, CI ở
  GitLab) ⇒ lịch sử defect trên GH `UNVERIFIED`.
- Churn cấp preview; version session-format **forward-incompatible** nghiêm ngặt.
- pi-ai hạn chế: không `stop`, một slot system, sign-in không bền, không có HTTP
  status. `UPSTREAM_SOURCE`
- `SAFETY.md`: **chưa audit, có chạy code do model sinh**; dựa vào seam
  `sandbox`/`interaction`/`guard`, không phải bảo đảm. `UPSTREAM_SOURCE`

---

# 2. Nền tảng LTT — API tại HEAD `22841303`

### 2.1 Bề mặt API cho chat/LLM
Nguồn chân lý route: `server/api/inventory.py:5-11` (test `test_178` khoá).
`LTT_SOURCE`

| Method | Path | Chế độ | Auth |
|---|---|---|---|
| POST | `/api/v1/jobs` | ASYNC_JOB | yes |
| POST | `/api/v1/chat/completions` | SYNC (OpenAI-compat) | yes |
| POST | `/api/v1/messages` | STREAM (Anthropic Messages SSE) | yes |
| POST | `/api/v1/responses` | STREAM (OpenAI Responses SSE) | yes |
| GET | `/api/v1/tools`, `/tools/{name}` | — | yes |
| GET | `/api/v1/models`, `/models/{name}` | — | yes |
| POST | `/api/v1/quotes` | — | yes |
| POST | `/api/v1/jobs/{id}/cancel` | — | yes |

**Hình dạng:** một engine (`text.chat`, `apps/ltt_llm/features.py`) khoác 3
lớp áo tương thích. `text.chat` là hợp đồng nội bộ **có kiểm máy** (params,
giá, admission); `/chat/completions` + `/messages` + `/responses` là **facade**
để Claude Code / Claude Desktop / Codex cắm vào không cần sửa.
`server/api/streaming.py:1-24`, `apps/ltt_llm/manifest.py:19-27`. `LTT_SOURCE`

> ⭐ **Hệ quả cho LTTCODE:** streaming **KHÔNG** có ở `/chat/completions`
> (trả 400 nếu `stream:true`). Muốn stream cho agent code phải dùng
> **Anthropic Messages** (`/messages`) hoặc **OpenAI Responses** (`/responses`).
> `server/api/chat.py:171-181`, `server/api/streaming.py:1-24`. `LTT_SOURCE`

### 2.2 Models
- `ltt-3.8` (nội bộ `qwen38-api`, RTX 3090) và `ltt-3.5` (nội bộ `qwen35-api`,
  RTX 5060 Ti) — xác nhận. `manifest.py:277-279,355-406`. `LTT_SOURCE`
- **Catalog dẫn xuất** từ manifest tool (không có danh sách trung tâm);
  truy vấn qua `GET /api/v1/models` → cho phép **server-driven capabilities**.
  `catalog.py:375-416`. `LTT_SOURCE`
- Metadata công khai: `name, capability, stability, description, tools,
  constraints, replaced_by`. Constraints: `context_window`
  (3.8≈171K / 3.5≈209K, dẫn xuất runtime), `max_output_tokens` 32768,
  **`reads_images: True` cả hai** (vision). `manifest.py:386-404`,
  `DEVELOPER_GUIDE.md:614,734-735`. `LTT_SOURCE`
- **Giá KHÔNG có ở /models** (giá phụ thuộc toàn input); lấy qua `POST /quotes`.
  Bảng nội bộ: 3.8 = 50/10/400, 3.5 = 13/3/20 credit / 1M in·cache·out.
  `platform_core/llm/gia_token.py:8-21`. `LTT_SOURCE`

### 2.3 Tham số request (kiểm bởi cả `params_schema` và `features.kiem_tham_so`)
`messages`(bắt buộc) · `model` · `max_tokens`(1..32768) · `temperature`(0..2) ·
`tools` · `reasoning_effort`(`none|low|medium|xhigh`, mặc định `medium`) ·
`response_format`(`text|json_object|json_schema`) ·
`tool_choice`(**chuỗi only**: `none|auto|required`) · `parallel_tool_calls` ·
`top_p`((0..1]) · `seed` · `stop`(**mảng**, ≤4). `features.py:208-347`,
`manifest.py:275-327`. `LTT_SOURCE`
- **Không mở (cố ý):** `grammar` thô, `n` (nhiều choice), **object-form
  `tool_choice`** (hệ kiểu 6-loại của platform không có union). `LTT_SOURCE`
- `reasoning_effort='none'` tắt hẳn thinking (tách khỏi `max_tokens`).

### 2.4 Auth
- **Chỉ Bearer token** `Authorization: Bearer ltt_sk_<id>_<secret>` (live) /
  `ltt_tk_…` (test); **cookie bị từ chối**, không CSRF trên bề mặt này.
  `server/api/auth.py:1-20`. `LTT_SOURCE`
- Scope enforced ở biên (`require_scope`); chat cần `jobs:create`. Mọi lỗi auth
  → **401 đồng nhất** (chống dò key). IP allowlist + throttle + kill-switch tại
  cùng biên. `auth.py:105-258`. `LTT_SOURCE`
- ⚠️ **KHÔNG có OAuth / device flow.** Đây là **lỗ hổng** so với UX "Đăng nhập
  bằng LTT Studios" (§13 của brief). `LTT_SOURCE` + `INFERENCE` (không tìm thấy
  endpoint OAuth nào trong inventory).

### 2.5 Credits / usage
- Mô hình: kiểm số dư → nhận vào hàng đợi (không giữ tiền khi chờ) → **giữ trần**
  → chạy → **quyết toán theo token đo được**, hoàn phần dư. `chat.py:262-591`.
- Usage **có** trả về: OpenAI `usage{prompt,completion,total}` + khối riêng
  `x_ltt{credit_charged, credit_held, usage_measured, cached_prompt_tokens, …}`.
  Tiền để ngoài `usage` để không vỡ client OpenAI strict. `chat.py:616-645`.
- "Không đo được ⇒ tính 0" (`dang_tin=False`). `features.py:143-171`.
- Layer tiền LLM: `platform_core/llm/thanh_toan.py` (bọc `platform_core/credit.py`
  — sổ cái chung). `LTT_SOURCE`

### 2.6 Lỗi
Envelope **RFC 9457 `application/problem+json`**, rẽ theo `code` (không theo
`detail`). `DEVELOPER_GUIDE.md:304-329`. `LTT_SOURCE`

| code | status | nghĩa (chat) |
|---|---|---|
| `insufficient_credit` | 402/409 | hết credit, **không tính tiền** |
| `unauthorized` | 401 | key sai/thiếu/thu hồi (đồng nhất) |
| `forbidden` | 403 | thiếu scope / tài khoản treo |
| `model_not_found` | 404 | model lạ / không thuộc bạn |
| `execution_busy` / model busy | **503 + Retry-After** | hàng đợi đầy / model bận (KHÔNG 429) |
| `rate_limited`/`concurrency_limited`/`quota_exceeded` | 429 | vượt tần suất/đồng thời/hạn ngày |
| `invalid_request` | 400 | input xấu / quote hỏng / ảnh hỏng |
| `client_disconnected` | 499 | client rời (log, nginx) |

> ⭐ **Adapter phải coi 503 `execution_busy`/model-busy là RETRYABLE** và tôn
> trọng `Retry-After` (không nhầm với 429). `LTT_SOURCE`

### 2.7 Huỷ & hàng đợi
- **Huỷ:** (a) đứt kết nối → đóng socket sang máy B (llama.cpp giải phóng slot
  ≤1s); (b) `POST /jobs/{id}/cancel`; request-id truyền qua `X-LTT-Request-Id`,
  gateway có `POST /v1/huy`. `platform_core/llm/huy_luot.py`, `ngat.py`.
- **Hàng đợi có chờ:** `phong_cho.py` chờ slot tới hạn (dùng chung đồng hồ với
  hạn ~125s của Cloudflare). Admission theo pool: 3.8→`ltt_38_3090` 3 slot,
  3.5→`ltt_35_5060` 3 slot. `streaming.py:802-806`. `LTT_SOURCE`

### 2.8 Chiến dịch chuẩn hoá API (5 commit mới nhất, 2026-09-14)
Kết luận hướng đi: **KHÔNG** gộp về một shape OpenAI thuần, cũng không thuần
custom — làm `text.chat` thành **hợp đồng custom, tự nhất quán, có kiểm máy**,
còn OpenAI/Anthropic/Responses là **áo tương thích ở biên**. Căng thẳng lặp lại:
hệ kiểu 6-loại (`invocation.py:197-227`) không diễn đạt nổi union của OpenAI
(`tool_choice`, `stop`) ⇒ platform cắt hợp đồng công khai về đúng thứ nó **trung
thực publish được**. `LTT_SOURCE`

---

# 3. Desktop shell + Updater — ứng viên

### 3.1 Bản cộng đồng wrap DSH (học từ thực tế) `COMMUNITY_IMPLEMENTATION`
| Repo | Tech | Ghi chú |
|---|---|---|
| `dsh-tauri-desk/deepseek-harness-desktop` | **Tauri** | installer ~5MB; **tải Node v22.22.0 + DSH lần chạy đầu** vào `~/.dsh`, spawn `dsh --host 127.0.0.1 --port 3080`; **KHÔNG dùng externalBin**, **KHÔNG dùng plugin-updater** (self-update shell hand-rolled) |
| `dataelement/dsh-desktop` (6.1k★) | Electron | phổ biến nhất; port loopback **ngẫu nhiên** |
| `fufankeji/deepseek-harness-studio` | Electron | plugin manager |
| `deepseek-ai/deepseek-harness` `apps/desktop` | **Electron** | **chính upstream** ship desktop Electron, NSIS |

### 3.2 Tauri 2 (chính thức) `OFFICIAL_DOC`
- Phiên bản verify live: **Tauri CLI 2.11.4**, `@tauri-apps/plugin-updater 2.11.0`.
- Sidecar: `externalBin` + `shell().sidecar()` để ship & spawn một exe bundle.
  Vì DSH là Node/TS ⇒ đường **chính thức** là `@yao-pkg/pkg` gói runtime DSH
  thành `binaries/lttcode-sidecar-x86_64-pc-windows-msvc.exe`.
- Updater plugin: đọc manifest, **verify chữ ký minisign**, trỏ được vào
  **endpoint tự host** (server release của LTT). Hỗ trợ mẫu "dynamic update
  server": Tauri **tuân theo chỉ dẫn của server** theo
  `{{current_version}}/{{target}}/{{arch}}` + custom header + override so sánh
  version (cho rollback).
- Bảo mật: capabilities **deny-by-default** (allow-list từng lệnh, vd
  `shell:allow-execute`), IPC hẹp — hợp với agent chạy shell.

### 3.3 Electron — so sánh cho ca này `OFFICIAL_DOC` + `COMMUNITY_IMPLEMENTATION`
- Node chạy sẵn ⇒ spawn `dsh web` trực tiếp, **không cần đóng gói sidecar**.
- electron-updater trưởng thành (NSIS + blockmap differential + Authenticode).
- **Chính upstream + 2 bản phổ biến nhất đều Electron** ⇒ tương thích & bảo trì
  cao nhất, nhanh nhất tới MVP.
- Nhược: installer ~85–150MB (vs ~5MB Tauri); sandbox yếu hơn.

### 3.4 Staged rollout / kill switch `OFFICIAL_DOC`
- **Phải tự làm ở server.** Updater (Tauri hoặc Electron) chỉ hit endpoint và
  **tuân theo** — không có config % rollout hay kill-switch sẵn.
- ⇒ Cần một **LTT Release Server** nhỏ: điểm điều khiển duy nhất cho kênh,
  % rollout, kill switch, minimum_supported_version, hai kênh update (shell mỏng
  vs runtime nặng). (CrabNebula Cloud là bản quản lý sẵn nhưng là bên thứ ba,
  không do LTT kiểm soát → tính năng rollout `UNVERIFIED`.)

### 3.5 Ký số Windows `OFFICIAL_DOC`
- **Hai chữ ký tách biệt:** (1) **Authenticode** trên installer (khuyến nghị
  cert **EV** để bỏ cảnh báo SmartScreen); (2) **minisign** cho updater của
  Tauri (Electron dùng chữ ký riêng của electron-updater).
- Khoá private **không** được nằm trong repo/frontend/bundle/log/CI-public-env.

---

# 4. ⭐ MA TRẬN TƯƠNG THÍCH — Harness ↔ LTT (bắt buộc, §8 brief)

Trạng thái: **PASS** (chạy được qua adapter) · **PARTIAL** (được nhưng có điều
kiện) · **GAP** (LTT có, DSH chưa drive được / hoặc ngược lại) ·
**VERIFY** (phải kiểm lúc tích hợp — chưa có LIVE_TEST).

| Feature | ltt-3.8 | ltt-3.5 | Bằng chứng | Khoảng trống / Ghi chú |
|---|---|---|---|---|
| Text | PASS | PASS | LTT chat + DSH text chunk | — |
| Streaming | PASS* | PASS* | LTT `/messages` \| `/responses`; DSH route `anthropic-messages`\|`openai-responses` | *KHÔNG dùng được stream ở `/chat/completions` |
| Vision (ảnh vào) | VERIFY | VERIFY | `reads_images:true`; DSH vision input | Phải kiểm block ảnh qua `/messages` lúc tích hợp |
| Reasoning none/low/medium/xhigh | PASS | PASS | LTT `reasoning_effort` khớp 1-1 với 4 mức DSH | adapter map thẳng |
| Single tool | PASS | PASS | LTT `tools`+`tool_calls`; DSH tool loop | — |
| Multi-turn tool | PASS | PASS | messages mang tool result | adapter format theo Anthropic/OpenAI |
| Parallel tools | PASS | PASS | LTT `parallel_tool_calls`; DSH loop (mặc định 10) | — |
| Tool result replay | PASS | PASS | DSH giữ `arguments` chuỗi JSON thô | adapter giữ nguyên định dạng |
| Structured output (json_schema) | GAP | GAP | LTT hỗ trợ; DSH `GenerateOptions` chưa | thêm = sửa core DSH — hoãn |
| `tool_choice` (ghim hàm) | GAP | GAP | LTT chuỗi-only; DSH không gửi | không ghim được hàm; ảnh hưởng nhỏ |
| `top_p` / `seed` | GAP | GAP | LTT có; DSH sampling chỉ temp/maxTokens/stop | ảnh hưởng nhỏ |
| Long context | PASS | PASS | 171K / 209K, đọc từ `/models` | server-driven |
| Cancellation | PASS | PASS | LTT đóng socket + `X-LTT-Request-Id`; DSH `options.signal` | adapter abort fetch → LTT nhả slot |
| Error mapping | PASS | PASS | LTT RFC-9457 code ↔ DSH mã trung tính | map bảng ở adapter |
| Credit exhausted | PARTIAL | PARTIAL | LTT `insufficient_credit`; DSH không có khái niệm credit | surface qua `finish{error}` + message rõ |
| Queue wait | PASS | PASS | LTT 503+Retry-After | `providerRetryPolicy` tôn trọng Retry-After |
| Session resume | PASS | PASS | DSH session-log plugin | *rủi ro:* format session churn (preview) |
| Context compaction | VERIFY | VERIFY | DSH có seam compaction | kiểm hành vi lúc tích hợp |
| Attribution headers | PASS | PASS | DSH bắt buộc `attributionHeaders()` | adapter luôn kèm |

**Kết luận adapter:** viết **thin `llm-ltt` adapter** (không dùng no-code
pi-ai), route **`anthropic-messages`** (hoặc `openai-responses`) tới LTT, tự lo
Bearer auth + map lỗi RFC-9457→mã trung tính + huỷ qua `X-LTT-Request-Id` +
`attributionHeaders()`. Lý do loại pi-ai: nó **không map HTTP status/lỗi**,
**sign-in không bền**, **không `stop`** — trái đúng nhu cầu LTT. `UPSTREAM_SOURCE`

---

# 5. Bài học cộng đồng — chép & tránh
**Chép:** port loopback **ngẫu nhiên** (dataelement) thay vì cố định 3080;
**hai kênh update tách biệt** (shell mỏng vs runtime nặng); health-check +
lifecycle service cho sidecar.
**Tránh:** tải Node+DSH lúc chạy đầu (bản Tauri cộng đồng) ⇒ vỡ khi offline,
không atomic, không ký được payload → **LTTCODE nên đóng gói sidecar atomic**
(installer self-contained). Tránh self-updater hand-rolled → dùng updater chính
thức + server release của LTT.

---

# 6. Khoảng trống & rủi ro (hợp nhất)
1. ⚠️ **DSH là preview `v0.1.x`**, breaking changes ~hằng ngày → pin commit +
   compatibility-branch workflow (§30) là **bắt buộc**; đây là rủi ro chiến lược.
2. ⚠️ **LTT chưa có OAuth/device flow** → chặn UX "Đăng nhập bằng LTT" (cần
   backend làm thêm, hoặc dùng API-key tạm). → **Decision Q3.**
3. **Streaming chỉ qua `/messages` \| `/responses`** → adapter phải nói
   Anthropic-Messages/OpenAI-Responses. (Ràng buộc, không chặn.)
4. **DSH chưa drive được** `response_format`/`top_p`/`seed`/object-`tool_choice`
   → GAP nhỏ, hoãn (thêm = sửa core).
5. **Staged rollout + kill switch = phải tự dựng LTT Release Server.**
6. **Windows cần 2 chữ ký** (Authenticode + minisign) + logistics cert EV.
7. **DSH `SAFETY.md`: chưa audit, chạy code model sinh** → sandbox/approval là
   trách nhiệm của LTTCODE, không phải bảo đảm của upstream.

---

# 7. Quyết định cần chủ sản phẩm (feed Decision Session)
| # | Quyết định | Khuyến nghị của Claude |
|---|---|---|
| Q1 | Chiến lược kho (riêng / hybrid / monorepo) | Kho **riêng** `LTTCODE` |
| Q2 | Công nghệ desktop (Tauri / Electron) | **Tauri** (bảo mật+size+updater ký sẵn) — Electron là lựa chọn nhanh/khớp-upstream hợp lệ |
| Q3 | UX Auth (device flow / API-key tạm / loopback OAuth) | **Device flow** là đích; API-key tạm nếu muốn MVP trước backend |
| Q4 | Hành vi update (notify / auto-dl+cài-khi-restart / auto-silent) | **Auto-download + cài khi restart**, ép cài bản bảo mật |
| Q5 | Telemetry/privacy | (Round 2) |
| Q6 | Kênh phát hành + chính sách staged rollout | (Round 2) |
| Q7 | Phạm vi Windows (x64 / +ARM64), offline installer, portable | (Round 2) |

> Các quyết định kỹ thuật đủ bằng chứng (pin commit DSH, thin adapter,
> port ngẫu nhiên, sidecar atomic, 2 chữ ký, LTT Release Server) sẽ được ghi
> thẳng vào `DECISION_LOCK.md` mà không cần hỏi.
