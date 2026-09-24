# VPS V4 — Blockers and Gates

## Active blockers

### Cập nhật 2026-09-24 — dây chuyền bán đã thông; năm khuyết tật đã sửa

Máy khách thật đầu tiên kể từ sự cố: `MayTram02`, vmid 208, IP 51.79.215.194,
sổ sách giữ 1.490 → thu 1.490 (`variance 0`). Chi tiết: `docs/NHAT_KY.md` 24/09.

**Còn mở sau lượt này:**

- **Cổng vào chỉ mở 3389 cho khách.** Chủ dự án chốt 24/09: giữ nguyên, nhưng đã
  **khai rõ trong điều khoản** (`dieu_khoan.py`, mục 1). Muốn cho khách tự mở
  cổng thì đó là một plan riêng (giới hạn, nhật ký, giá).
- **Luật chặn SSH mang một con số gõ tay.** `ip daddr != 51.79.166.36` nằm trong
  `/etc/nftables.conf` của gateway — ngoài kho. `tools/vps_doi_soat_cong.py` so
  nó với `vps_gateway.ip_cong_khai` nên IP đổi sẽ đỏ, **nhưng chỉ khi có người
  chạy công cụ**. Nối vào vòng bảo trì là việc còn lại.
- **Deploy lấy HEAD lúc chạy, không nhận SHA tường minh** — xem
  `docs/VPS/DOI_SOAT_DAY_CHUYEN.md` mục F.

### Việc mở cho phiên sau (ghi 17/09 cuối ngày)

- **R26 — đo băng thông VPS OVH chưa chạy**: bộ đếm/hãm tốc nằm trên router VM199,
  nhưng lưu lượng VPS OVH không đi qua VM199 (gateway `10.50.0.1` là host Proxmox, NAT
  ở gateway OVH) ⇒ `d96b66f3` luôn "0 KB / 300 GB", vượt hạn mức không bị giảm tốc.
  Cần chọn điểm đo (gateway OVH hoặc host Proxmox) rồi mới sửa.
- **Dọn Vultr khi chủ dự án ngừng tài khoản**: app — Disable profile 0401 (bảo trì đang
  ghi `reconciliation unavailable` mỗi lượt), đóng gateway `sgp-1` (10.51,
  `dang_nhan_may_moi=true`), gỡ `LTT_VULTR_API_KEY`/`LTT_VPS_GATEWAY_*`/`LTT_VPS_ROUTER_*`;
  VM199 — tắt `wg0`, bỏ dải `10.51` khỏi dnsmasq, **giữ** `10.50.0.2` + DHCP OVH.
- **Admin chưa sửa được chính sách mua IP** (`auto_acquire`, trần giá, fingerprint hợp
  đồng) — hiện chỉ sửa qua CSDL. Trang `/vps/admin/cong-ha-tang` chỉ nhận tên biến, không
  nhận bí mật (cố ý).
- **Reboot host Proxmox** để dùng kernel 7.0.14 — chờ cửa sổ bảo trì.

### Tổng kết phiên 2026-09-17 — không còn blocker phần mềm

- OVH 0402 là mặc định (ACTIVE, default); Vultr 0401 STANDBY. Chủ dự án: **Vultr sắp
  ngừng**, không đầu tư thêm (không thử đổi default, không preflight Vultr).
- Còn mở, **ngoài phạm vi phần mềm** (cần mua/dựng hoặc cửa sổ bảo trì): Backup V2
  CAPACITY_BLOCKED, diễn tập khôi phục, dual-WAN; cập nhật PVE đã CÀI 17/09 (9.2.20), còn **reboot host** để dùng kernel 7.0.14 — chờ cửa sổ bảo trì.

### Cập nhật 2026-09-17 (chiều) — bán VPS MỞ LẠI

- R22 và R23 đã sửa và chạy trên production/Máy B; profile OVH 0402 `auto_acquire=true`,
  health 6/6 HEALTHY. Mục "tạm dừng" bên dưới chỉ còn giá trị lịch sử.

### Cập nhật 2026-09-17 — bán VPS mới TẠM DỪNG (chủ dự án chốt)

- Deploy `ee5a5ef9` đạt; E2E console/vòng đời đạt trên `d96b66f3`.
- **Chặn mở bán lại**: R22 (tự mua IP OVH chỉ dùng giỏ adopt đã hết hạn — cần quyết
  định chi tiêu + probe catalog chỉ đọc), R23 (collector Máy B coi mapping
  `LTTMANAGED` là thừa ⇒ `network` CRITICAL; sửa qua cổng thay đổi Máy B).
- Profile OVH 0402: ACTIVE/default, `auto_acquire=false`, không còn `adopt_ip_cart_id`.

### Cập nhật 2026-09-16 (tối)

- B04 **đóng**: mua một IP qua web job thật (đơn 22703620), nhập kho, mapping.
- B08 **đóng cho r1**: deploy 16:29–16:31 sau khi kiểm 0 job/0 lease.
- Còn chặn phát hành cuối: L3 phiên (một lần) → gộp `main` (cây chính còn 6
  docs chưa commit của phiên LTTCODE) → deploy từ `main`. Production đang chạy
  dòng `codex/cli-compat-final-audit` chưa có ở `main`, nên nhánh VPS phải hoà
  cả dòng đó trước L3 để deploy từ `main` không lùi mã.
- Gate sản xuất không phải blocker phần mềm: Backup V2 / restore / dual-WAN.

### Cập nhật 2026-09-14, sau lựa chọn PO mới nhất

- B04: credit guard, exact delivery attribution, durable checkout/claim, worker
  defer 60 phút và bounded read-only quote readiness đã triển khai. Acquisition
  regression mới **39 PASS**; normal-user pending GUI owner/outsider PASS.
  Còn cấu hình activation thực tế, checkout đúng một IP, gateway persistence
  read-back trên IP mới và create E2E. Không mua giỏ thứ hai.
- B07: baseline riêng đã reconcile `37839edf`; PO xác nhận canonical đã ngừng
  và giao phiên VPS tự triển khai trên worktree này, gộp main cuối phiên. Không
  sửa năm tài liệu dirty trong main. Không còn chờ canonical deploy; đường
  release immutable và rollback đang được chuẩn bị trong `13_WORKTREE_RELEASE.md`.
- Hiện gate PID 10984 của phiên khác giữ CPU/Postgres; chưa được chạy build,
  batch nặng hay deploy chồng lên. Đây là chờ tài nguyên, không phải gate của VPS.
  **Sau đó khóa đã nhả:** release builder và batch hẹp 49 PASS đã chạy.
- B08 — Cửa sổ deploy production: preflight read-only đo 3 rồi 4 LTT LLM job
  running, lần cuối 4 heartbeat còn fresh và 1 queued. Không tự restart/hủy
  việc của app khác. Release đã đóng gói; cần drain/cửa sổ vận hành trước
  installer restart dịch vụ. Không nhầm việc này với phase-stop hay OVH admin approval.

Bảng discovery dưới đây giữ bằng chứng thời điểm trước; cập nhật trên thay thế
trạng thái triển khai B04/B07 cũ, không phải chứng cứ live đã hoàn thành.

| ID | Scope | Evidence | Blocks | Unblock action |
|---|---|---|---|---|
| B01 | Exact Admin IA | **RESOLVED 2026-09-13**: PO approved generic admin contract; local browser verified exact menu | No longer an authority blocker | Offline certification still required |
| B02 | Live runtime | **PARTIAL 2026-09-14**: Machine B access, coherent collector generation and app-owned mirror passed; machine health remains CRITICAL for data protection. A later manual refresh hung and was cleanly terminated | Activation requires a newly fresh generation, not the earlier success | Repeat canonical collector immediately before activation; exit 3/hang blocks |
| B03 | PVE TLS | **RESOLVED IN CODE/EVIDENCE 2026-09-14**: private root CA exported outside Git; management-IP transport validates exact cert name `pve`; dummy-token probe reached 401 | Production still needs the two env references installed at deploy | Configure `LTT_VPS_PROXMOX_CA` and `LTT_VPS_PROXMOX_TLS_NAME`; never disable verify |
| B04 | Live free IP | **AUTOMATION IMPLEMENTATION OPEN (Q130)**: eight protected IPv4, zero free; one unpaid cart `efae624e-6114-46b9-ace5-3063f9fc1580`, one SG/SGP `ip-failover-arin`, USD 2.39 including tax, expiry `2026-09-15T08:53:23Z`. Signed driver/coordinator targeted tests pass; no checkout performed | One-IP/one-VM live acceptance | Finish credit guard, exact delivery attribution, persistent gateway address and worker/UI integration. Revalidate/adopt the existing cart without creating a second live purchase. Normal quoted checkout needs no per-order admin approval; unexpected billing or ambiguous recovery still fails closed |
| B05 | Owner canonical ID | **RESOLVED 2026-09-14**: read-only exact-email lookup returned exactly one canonical user ID | No longer blocks live create | Recheck owner active/allowlisted at create-time preflight |
| B06 | OVH mapping driver | **RESOLVED LIVE 2026-09-14**: `ltt-gwnat` installed on gateway and health returned `ok`; protected removal RC 5 and conflicting ensure RC 4. Mapping/protected files kept the identical pre/post SHA-256 `5ebaf20b44b74fc7a3379e2d2a7dca2357f70b85f6b33f281fd75ad813241766`; no mapping was mutated | No longer blocks the first new mapping | Re-run health and exact read-back immediately around the one authorized new mapping |
| B07 | Canonical reconciliation | **REOPENED 2026-09-14**: `main...HEAD` measured 1 behind/9 ahead; current `main` is `b80f837c`. Its worktree also contains unrelated uncommitted CMC/decision/plan edits owned by other sessions | Deploy/final frozen-candidate gate | Wait for the owning session to finish, then reconcile once and rerun only affected targeted checks before the single final gate |

## Production-readiness gates, not blockers for multi-profile code

| Gate | State at discovery | Rule |
|---|---|---|
| Backup V2 | CAPACITY_BLOCKED; destination shortage measured | Do not delete old backup; solve capacity under Machine B change gate |
| Restore drill | NOT VERIFIED | Only after verified V2 backup; isolated network; approval for restore boot/downtime |
| Dual WAN | NOT VERIFIED | Backlog unless required; WAN cut needs approval; no UDP load balancing |
| PVE upgrades | 146 pending in stale snapshot | Simulate first; no service/host restart without maintenance approval |
| VirtIO/QGA | Existing protected VMs remain untouched | Test only on new lab VM after primary path passes |
| Zero-touch Windows | DEFERRED | Manual ISO installer is MVP |

## Conditional stop points

Login/MFA/CAPTCHA, unexpected provider billing, production downtime, host reboot,
WAN cut, restore boot and ambiguous destructive ownership. All other safe offline
work continues automatically.
