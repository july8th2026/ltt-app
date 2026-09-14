# LTTCODE — MASTER_IMPLEMENTATION_PLAN

> Chỉ mở sau `DECISION_LOCK.md` + `MASTER_ARCHITECTURE.md`. Mỗi phase theo nhịp:
> **PLAN → IMPLEMENT → TEST → LIVE VERIFY → REPORT → COMMIT.** Không gộp một
> commit khổng lồ. Không `reset --hard`/`clean -fd`/force-push/blind `add -A`.
> Nền: `RESEARCH_BASELINE.md`. ID `Dxx` trỏ `DECISION_LOCK.md`.

## 0. Ghi chú vị trí code
Theo **D01**, phần lớn code desktop nằm ở **kho riêng `LTTCODE`** (chưa tạo).
`docs/LTTCODE/` trong LTTSTUDIOSAPP giữ nghiên cứu/quyết định/hợp đồng + snapshot
API để kiểm lệch. Adapter `llm-ltt` là plugin DSH (ở kho LTTCODE, dùng hợp đồng
LTT). Việc backend LTT (device flow OAuth, `/client/bootstrap`, release server)
theo quy trình nền tảng (`docs/00_LTT_OPERATING_CONTRACT.md`, gate).

## Blockers cần trước khi bắt tay
- **B1:** tạo kho `LTTCODE` — cần chốt tên/visibility/org (mục "Việc kế tiếp").
- **B2:** mua **cert EV** ký Authenticode (logistics, D13).
- **B3:** hạ tầng release: bucket R2 + domain CDN do LTT kiểm soát (D14).
- **B4 (nợ, không chặn MVP desktop):** backend device flow OAuth (D03).

---

## P00 — Research & Baseline ✅ ĐÃ XONG
RESEARCH_BASELINE + ma trận tương thích + DECISION_LOCK + MASTER_ARCHITECTURE.

## P01 — Decision Lock & Architecture Freeze ✅ ĐÃ XONG
Vòng 1+2 Superpower đã chốt (D01–D08); D09–D19 ghi bằng bằng chứng.

## P02 — Harness Pin & Reproducible Baseline
- **Plan:** khởi tạo kho LTTCODE; pin DSH `fb2c4b9e` (D10); dựng script build
  tái lập; `UPSTREAM_DIVERGENCE.md` (rỗng lúc đầu — mục tiêu giữ rỗng).
- **Test/Verify:** `npx dsh web` chạy được với DSH pinned; ghi lại commit + hash.
- **Commit:** scaffold kho + pin.

## P03 — LTT Compatibility Harness (test-first)
- **Plan:** bộ test tự động chạy ma trận `RESEARCH_BASELINE §4` với **key test
  `ltt_tk_`** trên `/api/v1/messages`: text, streaming, vision, 4 mức reasoning,
  single/multi-turn/parallel tool, tool-result replay, long context, cancel,
  error mapping, queue-wait(503+Retry-After), credit-exhausted.
- **TDD:** viết test kỳ vọng trước, để đỏ, rồi làm adapter (P04) cho xanh.
- ⛔ Không coi "200 OK" là PASS — phải chạy multi-turn tool thật.
- **Verify:** LIVE_TEST điền cột Evidence trong ma trận (đổi VERIFY→PASS/GAP thật).

## P04 — LTT Provider Adapter `llm-ltt`
- **Plan:** implement `stream()` (D11, ARCH §5). Auth Bearer + attributionHeaders
  + X-LTT-Request-Id; map lỗi RFC-9457; retry honor Retry-After.
- **Test:** P03 xanh cho cả ltt-3.8 và ltt-3.5.
- **Live verify:** một phiên agent multi-turn (đọc file → gọi tool → tiếp) chạy
  thật qua adapter.
- **Commit:** adapter + đăng ký `registerAdapter(['ltt'])` qua plugin.

## P05 — LTT Auth & Bootstrap (MVP)
- **Plan:** UI dán `ltt_sk_`; lưu Credential Manager/DPAPI (D18); handshake
  `/client/bootstrap` (D16) đọc models/min-version/flags; logout xoá key.
- **Test:** key sai → lỗi rõ; key đúng → thấy catalog; restart giữ đăng nhập.
- **Live verify:** đăng nhập → thấy ltt-3.8/ltt-3.5 từ `/models`.

## P06 — Desktop Runtime / Sidecar
- **Plan:** pkg DSH → sidecar exe (D12); Tauri externalBin + shell().sidecar();
  port ngẫu nhiên; health-check; crash-recovery backoff; shutdown sạch; policy
  multi-instance; log tách user data.
- **Test:** kill sidecar → tự phục hồi; thoát app → không tiến trình mồ côi.
- **Live verify:** boot app → sidecar healthy → UI gọi được model.

## P07 — Core Coding Agent UX
- **Plan:** mở repo thật, cây file, chat, xem tool call/kết quả, diff/approve,
  streaming + reasoning hiển thị, cancel. Tái dùng Web UI DSH nếu khả thi.
- **Live verify (trình duyệt/thật):** hỏi model → đọc file → sửa file → chạy
  lệnh shell → vòng tool → duyệt → xong task.

## P08 — Session / Sandbox / Approval
- **Plan:** session persist (D17, lưu ý format DSH forward-incompatible); sandbox
  + shell approval + workspace trust (D19) — mức mặc định chốt kèm bằng chứng
  cộng đồng (đối chiếu wrapper hiện có).
- **Test:** đóng/mở app → session còn; lệnh shell bị chặn tới khi duyệt.

## P09 — Release Control Plane
- **Plan:** LTT Release Server (D14): kênh dev/beta/stable, rollout ladder, kill
  switch, min-supported, health ingest, hai kênh update; cohort ẩn danh ổn định.
- **Test:** `enabled=false` → client ngừng thấy bản; % rollout chia đúng.

## P10 — Updater / Signing / Migration
- **Plan:** Tauri updater trỏ release server (D04 notify-only; ép khi <min);
  Authenticode EV + minisign (D13); migration backup→verify→migrate→integrity→
  mark (D17).
- **Test (failure-first §39):** chữ ký sai → từ chối; tải đứt → không hỏng bản
  đang chạy; migration lỗi → dữ liệu cũ nguyên.

## P11 — Security / Supply Chain
- **Plan:** audit Tauri capabilities/IPC/localhost/deeplink; SBOM + SHA256 +
  provenance mỗi release; audit npm/crate/license; không auto-merge dep vào stable.
- **Test:** security-review; scan phụ thuộc.

## P12 — Beta Acceptance
- **Plan:** chạy TOÀN chuỗi nghiệm thu §38 trên Windows sạch + bộ failure §39
  (sidecar crash, mất mạng, API/ model unavailable, queue full, hết credit, auth
  hết hạn, tool fail, shell denied, malformed tool call, stream đứt, cancel,
  session hỏng, migration fail, chữ ký update sai, tải đứt, release disabled,
  client < min-version).
- **Gate:** chưa PASS đủ chuỗi ⇒ chưa lên stable.

## P13 — Stable Release
- **Plan:** promote CÙNG artifact đã test qua ladder; scorecard §40; kill switch
  sẵn sàng.

---

## Acceptance chain (§38) — đích cuối
download→install→launch→sign in(ltt_sk_)→model catalog→open repo→ask model→read
files→edit→run shell→tool loop→approve→finish→close→reopen (session còn)→publish
bản mới→**notify update**→signed update→install→restart→session/workspace còn→
post-update health PASS.

## Cột mốc phụ thuộc
P02→P03→P04→P05→P06→P07→P08 (client); P09,P10 cần B2/B3; P05→(nợ B4 device flow).
