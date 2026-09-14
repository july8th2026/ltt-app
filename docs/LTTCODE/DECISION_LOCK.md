# LTTCODE — DECISION_LOCK

> Quyết định đã KHÓA. Không đổi âm thầm; muốn đổi phải tạo ADR mới ở
> `docs/LTTCODE/adr/`. Nền bằng chứng: `RESEARCH_BASELINE.md`.
> Lập 2026-09-14. Chủ sản phẩm chốt Vòng 1+2 trong phiên này.

## Nhóm A — Chủ sản phẩm chốt

### D01 — Chiến lược kho
- **Status:** LOCKED
- **Question:** LTTCODE ở kho nào?
- **Selected:** **Kho riêng `LTTCODE`**, tách khỏi `LTTSTUDIOSAPP`.
- **Reason:** vòng đời phát hành desktop (installer ký số, auto-update, staged
  rollout, pin DSH) khác hẳn nền tảng Python; tách giữ gate/deploy nền tảng sạch,
  không phình kho, deploy nền tảng không kéo theo desktop.
- **Evidence:** `RESEARCH_BASELINE §6`; monorepo hiện là Python/Windows-server;
  "deploy chép cả cây" (CLAUDE.md) sẽ nuốt cả desktop nếu để chung.
- **Impact:** cần cơ chế đồng bộ hợp đồng API giữa 2 kho (snapshot có test kiểm).
- **Revisit trigger:** nếu chi phí đồng bộ hợp đồng vượt lợi ích tách kho.

### D02 — Công nghệ desktop
- **Status:** LOCKED
- **Selected:** **Tauri 2** (CLI 2.11.4, plugin-updater 2.11.0).
- **Reason:** installer ~5MB, sandbox capability deny-by-default (hợp agent chạy
  shell), updater + verify chữ ký minisign sẵn, trỏ được vào release server LTT.
- **Evidence:** `RESEARCH_BASELINE §3.2`; bản cộng đồng 5MB dùng Tauri.
- **Impact:** phải đóng gói runtime DSH (Node) thành sidecar exe (xem D12).
- **Revisit trigger:** nếu đóng gói Node-sidecar trên Windows tỏ ra bất khả thi
  ⇒ cân nhắc lại Electron (upstream ship sẵn Electron desktop).

### D03 — UX Auth
- **Status:** LOCKED (theo pha)
- **Selected:** **API-key tạm cho MVP → nâng cấp device flow OAuth sau.**
- **Reason:** LTT hiện CHỈ có Bearer `ltt_sk_` (không OAuth); ship MVP không chờ
  backend. Device flow là đích (brief §13).
- **Evidence:** `RESEARCH_BASELINE §2.4` (không có endpoint OAuth trong inventory).
- **Impact:** MVP: user dán `ltt_sk_` (lưu Windows Credential Manager/DPAPI, xem
  D18). Nợ backend: device-authorization grant ở LTT platform (campaign riêng).
- **Revisit trigger:** khi backend device flow sẵn sàng ⇒ ADR chuyển UX.

### D04 — Hành vi update
- **Status:** LOCKED
- **Selected:** **Notify-only** (báo có bản mới; user tự bấm tải + cài).
- **Reason:** ưu tiên không gián đoạn bất ngờ.
- **Evidenceः** `RESEARCH_BASELINE §3.4`.
- **Impact:** ⚠️ users có thể tụt hậu → **kill switch + minimum_supported_version
  ở server là bắt buộc** để chặn bản lỗi/cũ (bù cho notify-only). Bản dưới
  min-supported phải bị chặn dùng và ép nâng (đây KHÔNG mâu thuẫn notify-only:
  notify là mặc định, ép chỉ dành cho vá bảo mật/incompatible).
- **Revisit trigger:** nếu quá nhiều user kẹt bản cũ gây sự cố hỗ trợ.

### D05 — Telemetry / privacy
- **Status:** LOCKED
- **Selected:** **Telemetry vận hành ẩn danh, opt-out.**
- **Reason:** cần tối thiểu health để staged rollout + kill switch quyết định
  được; vẫn tôn trọng riêng tư.
- **Evidence:** brief §24-25.
- **Impact:** CHỈ gửi: installed/startup_success/startup_failure/crash, version/
  channel/OS/arch, sidecar status. **TUYỆT ĐỐI không** gửi source/prompt/file
  user. Có công tắc tắt trong Settings.
- **Revisit trigger:** yêu cầu pháp lý/riêng tư mới.

### D06 — Kênh phát hành + staged rollout
- **Status:** LOCKED
- **Selected:** **3 kênh dev/beta/stable + ladder** internal→1%→10%→25%→50%→100%
  + kill switch.
- **Reason:** khớp brief §15-17 và workflow nâng DSH §30; vùng đệm an toàn cho
  upstream churn nhanh.
- **Evidence:** `RESEARCH_BASELINE §3.4`, §1.1 (DSH ~daily preview).
- **Impact:** LTT Release Server phải quản kênh + % + kill switch (D14). DSH mới:
  upstream→compat branch→tests→dev→beta→stable (không lên thẳng stable).
- **Revisit trigger:** đội quá nhỏ để vận hành 3 kênh ⇒ rút còn beta/stable.

### D07 — Phạm vi Windows
- **Status:** LOCKED
- **Selected:** **Windows 10/11 x64 only** cho MVP.
- **Reason:** đơn giản CI/ký số/test; đại đa số máy.
- **Impact:** target `x86_64-pc-windows-msvc`. ARM64 = ADR sau nếu có nhu cầu.
- **Revisit trigger:** nhu cầu ARM64 (Surface/Snapdragon) đo được.

### D08 — Dạng phân phối
- **Status:** LOCKED
- **Selected:** **Chỉ installer offline self-contained** (không portable, không
  auto-start ở MVP).
- **Reason:** atomic release (§22); tránh lỗi "download lúc chạy đầu"; ký số toàn
  bộ payload.
- **Impact:** installer chứa sẵn sidecar DSH đã đóng gói (D12).
- **Revisit trigger:** user yêu cầu portable/auto-start.

## Nhóm B — Claude chốt bằng bằng chứng (ghi, không hỏi)

### D09 — Tên sản phẩm
LOCKED: **LTTCODE** (chủ sản phẩm đặt trong brief).

### D10 — Pin DSH + workflow nâng cấp
LOCKED: pin **commit `fb2c4b9e698e30edb738bca4cf0618587db7d203`** (tag
`dsh-v0.1.5-rc.2`). Nâng cấp qua compatibility branch + chạy ma trận tương thích
LTT trước khi vào dev (§30). **Cấm** bot tự đẩy DSH mới lên stable.
Evidence: `RESEARCH_BASELINE §1.1, §1.4`.

### D11 — LTT Provider Adapter
LOCKED: **thin adapter `llm-ltt`** (`extends LlmAdapter`, implement `stream()`),
KHÔNG dùng no-code pi-ai. Wire chính: **Anthropic Messages** (`POST /api/v1/
messages`, SSE) — LTT thiết kế cửa này cho coding agent (Claude Code/Desktop),
reasoning map sạch sang reasoning-chunk của DSH. Adapter lo: Bearer `ltt_sk_`,
`attributionHeaders()`, map lỗi RFC-9457→mã trung tính, huỷ qua `X-LTT-Request-Id`
+ `options.signal`, tôn trọng `Retry-After` (503). Evidence: `RESEARCH_BASELINE
§1.3, §2, §4`. **Revisit:** nếu `/messages` thiếu gì lúc tích hợp → thử
`/responses` (OpenAI Responses) — chỉ đổi wire trong adapter, không đụng nơi khác.

### D12 — Sidecar DSH
LOCKED: đóng gói runtime DSH thành **một exe** bằng `@yao-pkg/pkg` →
`binaries/lttcode-sidecar-x86_64-pc-windows-msvc.exe`, nhúng qua Tauri
`externalBin` + `shell().sidecar()`. **Port loopback ngẫu nhiên** (không cố định),
health-check, quản lý vòng đời (start/health/crash-recovery/shutdown) ở lớp Rust.
KHÔNG bind interface public. Evidence: `RESEARCH_BASELINE §3.1-3.2, §5`.

### D13 — Ký số
LOCKED: **hai chữ ký** — (1) Authenticode trên installer (**cert EV**, tránh
SmartScreen); (2) minisign cho updater Tauri. Khoá private CHỈ ở CI secret/HSM,
KHÔNG ở repo/frontend/bundle/log. Có kế hoạch rotation + gia hạn cert. Evidence:
`RESEARCH_BASELINE §3.5`. **Blocker logistics:** mua cert EV.

### D14 — LTT Release Server (control plane)
LOCKED: dịch vụ nhỏ do LTT kiểm soát trên R2/CDN, là điểm điều khiển DUY NHẤT:
kênh, % rollout, kill switch, minimum_supported_version, release notes, health
ingest, hai kênh update (shell mỏng vs runtime nặng). Client hỏi theo
`{{current_version}}/{{target}}/{{arch}}`; server "ra lệnh", client tuân.
Evidence: `RESEARCH_BASELINE §3.4`.

### D15 — Atomic release
LOCKED: một version LTTCODE = shell + UI + **DSH đã pin** + adapter `llm-ltt` +
plugin LTT, build & ký thành **một** artifact atomic. Không updater riêng cho
từng phần. Evidence: brief §22.

### D16 — Server-driven capabilities + handshake
LOCKED: models/context/feature đọc từ `GET /api/v1/models` + một handshake
`/client/bootstrap` (app gửi version/platform/arch/channel; server trả
supported/latest/min-supported/feature_flags/models). Không hardcode con số nếu
server cấp được. Evidence: `RESEARCH_BASELINE §2.2`, brief §10, §20.

### D17 — Tách dữ liệu + migration
LOCKED: **binary ≠ user data**. sessions/settings/credentials/history ở thư mục
data riêng; update không đụng. Đổi schema local: backup trước → migrate →
integrity check → mark success; fail thì KHÔNG phá dữ liệu cũ. Evidence: brief
§23. Lưu ý: session-format DSH forward-incompatible nghiêm ngặt (`§1.4`).

### D18 — Lưu credential
LOCKED: **Windows Credential Manager / DPAPI**; không plain text. Evidence:
brief §13, D03.

### D19 — Sandbox / approval
LOCKED: DSH `SAFETY.md` "chưa audit, chạy code model sinh" ⇒ LTTCODE tự chịu
trách nhiệm sandbox/approval qua seam `sandbox`/`interaction`/`guard` của DSH +
allow-list capability của Tauri (`shell:allow-execute`). Mặc định: workspace
trust hỏi trước, shell cần duyệt. Evidence: `RESEARCH_BASELINE §1.4, §3.2`.
(Chi tiết mức mặc định sẽ chốt ở P08 kèm bằng chứng cộng đồng.)
