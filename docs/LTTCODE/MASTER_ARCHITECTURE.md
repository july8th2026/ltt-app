# LTTCODE — MASTER_ARCHITECTURE (FROZEN)

> Đóng băng sau `DECISION_LOCK.md` (2026-09-14). Đổi kiến trúc = ADR mới.
> Nền: `RESEARCH_BASELINE.md`. Mọi ID `Dxx` trỏ về `DECISION_LOCK.md`.

## 1. Sơ đồ runtime — một lượt chat/agent

```
USER
 │
 ▼
LTTCODE.exe  (Tauri 2 shell — Rust host + WebView2 UI)              [D02]
 │  • quản vòng đời sidecar (start/health/crash-recovery/shutdown)  [D12]
 │  • IPC hẹp (capability allow-list, shell:allow-execute)          [D19]
 │  • credential store: Windows Credential Manager/DPAPI            [D18]
 ▼
DSH Sidecar  (binaries/lttcode-sidecar-*.exe, @yao-pkg/pkg)        [D12]
 │  http://127.0.0.1:<PORT NGẪU NHIÊN>   (không bind public)
 │  DeepSeek Harness pin dsh-v0.1.5-rc.2  fb2c4b9e                  [D10]
 │  ┌──────────────────────────────────────────────┐
 │  │ Agent loop · tool lifecycle · session log     │  (plugin Cordis)
 │  │ ctx.llm (LlmRuntime, provider-neutral)        │
 │  │   └── registerAdapter(['ltt'], LttAdapter)    │  ← LTT gắn ở đây [D11]
 │  │ Profile + bundle + cordis.yml LTT             │  (không sửa core)
 │  └──────────────────────────────────────────────┘
 ▼
LttAdapter.stream()   dịch wire LTT ↔ StreamChunk trung tính        [D11]
 │  • Bearer ltt_sk_  + attributionHeaders() + X-LTT-Request-Id
 │  • map lỗi RFC-9457 → mã trung tính · tôn trọng Retry-After(503)
 ▼
LTT Public API   POST /api/v1/messages  (Anthropic Messages SSE)   [D11]
 │  (streaming CHỈ ở /messages | /responses; /chat/completions sync)
 ▼
LTT Platform
 ├─ Auth (Bearer, scope jobs:create)      ├─ Credits (giữ trần→quyết toán)
 ├─ Policy / kill-switch                   ├─ Model Catalog (GET /models)
 ├─ Admission / hàng đợi (503+Retry-After) └─ Usage (x_ltt)
 ▼
LTT LLM  →  ltt-3.8 (RTX 3090) · ltt-3.5 (RTX 5060 Ti)
```

⛔ Desktop **không** gọi máy B trực tiếp — luôn qua LTT Public API.

## 2. Sơ đồ release — source → máy user

```
SOURCE (kho riêng LTTCODE)                                          [D01]
 │  shell(Tauri) + UI + DSH pinned + adapter llm-ltt + plugin LTT
 ▼
CI/CD  (build x64 → pkg sidecar → gate compat DSH↔LTT → sec/dep)   [D07,D10]
 ▼
SIGNED RELEASE  (1 artifact atomic)                                 [D15]
 │  Authenticode EV (installer) + minisign (updater)                [D13]
 │  + SHA256 + SBOM + manifest
 ▼
LTT RELEASE CONTROL  (server do LTT kiểm soát)                      [D14]
 │  kênh dev/beta/stable · % rollout ladder · kill switch           [D06]
 │  minimum_supported_version · release notes · health ingest
 ▼
R2 / CDN  (lttcode/{dev,beta,stable}/ · versions/)
 ▼
LTTCODE UPDATER  (notify-only; ép chỉ khi < min-supported)          [D04]
 │  hỏi {{current_version}}/{{target}}/{{arch}} → server ra lệnh
 ▼
POST-UPDATE HEALTH GATE  (boot·sidecar·profile·DB·handshake)        [D16]
 ▼
MARK HEALTHY  → telemetry ẩn danh opt-out                           [D05]
```

## 3. Thành phần

| Thành phần | Trách nhiệm | Quyết định |
|---|---|---|
| **Tauri host (Rust)** | vòng đời sidecar, port ngẫu nhiên, health, IPC, credential, updater, migration | D02,D12,D17,D18 |
| **WebUI (WebView2)** | giao diện coding agent; tái dùng Web UI của DSH nếu khả thi | D02 |
| **DSH sidecar** | agent loop, tool, session, ctx.llm | D10,D12 |
| **Plugin/bundle LTT** | profile + cordis.yml + đăng ký adapter + branding + UI ext | D10,D11 |
| **Adapter `llm-ltt`** | wire LTT↔StreamChunk, auth, lỗi, huỷ, retry | D11 |
| **LTT Release Server** | control plane phát hành | D06,D14 |
| **Bootstrap/handshake** | server-driven capability + min-version | D16 |

## 4. Vòng đời sidecar (Rust host)
`spawn(port ngẫu nhiên)` → poll `/health` tới khi ready (timeout) → sống cùng
app → crash thì restart có backoff, quá N lần thì báo lỗi UI → shutdown sạch khi
thoát. Log sidecar vào thư mục logs của app (không lẫn user data). Đa thực thi:
mỗi cửa sổ/instance một port riêng (chốt policy multi-instance ở P06).

## 5. Adapter `llm-ltt` — hợp đồng
- **Vào:** `GenerateOptions` (messages, tools, temperature, maxTokens, stop,
  reasoning effort, signal).
- **Ra:** `AsyncIterable<StreamChunk>`: `block-start → text|reasoning|
  tool-call-delta → block-end → usage → finish`. `usage` TRƯỚC `finish`.
- **Wire:** `POST /api/v1/messages` (Anthropic SSE), `stream:true`.
- **Auth:** `Authorization: Bearer <ltt_sk_>` + `attributionHeaders()`.
- **Huỷ:** `options.signal` abort fetch → LTT đóng socket máy B (≤1s);
  kèm `X-LTT-Request-Id` để huỷ chủ động nếu cần.
- **Lỗi → mã trung tính:** `unauthorized`→AUTH · `insufficient_credit`→(error
  billing, message rõ) · `model_not_found`→(config) · `execution_busy`/503→
  RATE_LIMIT + honor `Retry-After` qua `providerRetryPolicy` · context→
  CONTEXT_WINDOW_EXCEEDED.
- **GAP đã biết (hoãn):** response_format/top_p/seed/object-tool_choice — DSH
  chưa drive; không đưa vào `GenerateOptions` (thêm = sửa core).

## 6. Auth (MVP) [D03,D18]
User dán `ltt_sk_` → lưu Credential Manager/DPAPI → adapter đọc lúc gọi. Logout
= xoá credential. Nợ: device flow OAuth (browser → mint scoped key) khi backend
sẵn sàng.

## 7. Release control plane [D06,D14]
Server giữ trạng thái mỗi (channel, version): enabled, rollout%, min_supported,
notes, artifact URL + hash + chữ ký. Client cohort ổn định (hash id máy ẩn danh,
không dùng dữ liệu nhạy cảm) để chia % nhất quán. `release.enabled=false` = dừng
phát ngay (kill switch). DSH bump đi dev→beta→stable, không thẳng stable.

## 8. Bảo mật [D19]
Coi DSH là runtime bên thứ ba chưa audit. Phòng thủ: Tauri capability
deny-by-default; sidecar loopback-only; shell/file cần approval; workspace trust
hỏi trước; verify chữ ký khi update; verify SHA256 khi tải; không log secret;
credential ở OS secure store. Supply chain: pin DSH + audit npm/crate + SBOM mỗi
release; không auto-merge dependency vào stable.

## 9. Quan sát (About → System Information) [D16]
Hiển thị: LTTCODE version · DSH version/commit · adapter version · api_contract
hash · local schema version · OS/arch · channel · sidecar status. Không lộ secret.
