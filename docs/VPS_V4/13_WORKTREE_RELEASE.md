# VPS V4 — triển khai từ nhánh được PO chỉ định

Trạng thái: IMPLEMENTATION CHECKPOINT, chưa deploy hay nghiệm thu live.

## Bằng chứng release 2026-09-14

- Commit release: `e2b118c6014492d6be53f1862ddd1aa407fa677f`; repository độc lập
  `D:\LTTSTUDIOSAPP-runtime\release-e2b118c6-lf`, HEAD đúng và status sạch.
- Clone đầu dùng autocrlf=true làm hash nguồn frontend khác; builder chặn
  đúng trước deploy. Clone lại với core.autocrlf=false giữ hash package.json
  đúng byte nguồn task; không đổi frontend hoặc core.autocrlf của cây khác.
  Tham chiếu: https://git-scm.com/docs/git-config#Documentation/git-config.txt-coreautocrlf.
- `python -m alembic heads`: đúng một head `f4a7c2d9e610`.
- `python tools/build_release.py --output D:/LTTSTUDIOSAPP-runtime/packages-e2b118c6-lf`:
  PASS, 4469 files, 146.4 MB, secret scan 0 finding. ZIP SHA-256
  `def98577f79508afb6ac5c826dea27536f681308accf859c4c51d3e2040fe191`.
- Acquisition + sellable-capacity batch: **49 PASS/2,74 giây**, không gate tổng.
- Preflight DB production chỉ SELECT trong READ ONLY transaction: head hiện
  `a3f7c214e8b9`, chưa bảng V4; thiếu CA/TLS-name/rollout references. Đọc lần
  một có 3 running LTT LLM/1 queued; lần hai có 4 running, cả 4 heartbeat fresh.
  Không restart worker/web/voice khi việc ngoài VPS đang chạy. Cần cửa sổ
  drain phù hợp, không tự hủy job hoặc tắt admission của app khác.

## Authority và nguồn bất biến

PO cập nhật 2026-09-14: canonical đã ngừng; phiên VPS tự tiếp tục trên
`D:\LTTSTUDIOSAPP-vps-v4`, nhánh `codex/vps-v4-infrastructure-profiles`.
Không sửa main và không thu gom năm tài liệu dirty của phiên khác. Merge main
chỉ cuối phiên sau nghiệm thu. BASE_SHA đã reconcile: `37839edf2c8ec0ca33b3f22e68a6df26bba696e4`.

Installer `setup/2-cai-dat.ps1` từ chối linked worktree trước mọi ghi production.
Không xóa `.git`, không sửa guard, không giả worktree thành canonical. Đường
release cần snapshot đúng commit đã kiểm thử của nhánh PO chỉ định trong một
repository release độc lập; xác minh HEAD và clean status trước installer.
Repository release không được dùng để nhập thay đổi ngoài phạm vi vào main.
Installer hiện có sẽ tự `git archive` HEAD rồi kiểm tra chuỗi Alembic trước
Stop-Service. Đây là triển khai nhánh explicit-authorized, không phải gate xanh.

## Trước mutation production

1. Kiểm tra `tools/tai_may.py` và `tools/cua_so_yen.py trang-thai`; không chồng
   deploy lên gate/CPU/Postgres đang được phiên khác giữ. Tối đa hai worker.
2. Freeze code/test mục tiêu, secret scan 0 finding, commit riêng nhánh VPS;
   lấy SHA đầy đủ, kiểm nguồn release clean và đúng SHA, đủ vendor đã khai.
3. Đọc lại đầy đủ installer, backup/rollback và service names thực tế. Chưa
   gọi installer nếu chưa có backup CSDL/config và cửa sổ service restart an toàn.
4. Ghi app SHA/schema trước deploy, migration head và backup reference; không
   in nội dung app.env/credential. Migration additive phải giải được từ snapshot.
5. Cài hai reference `LTT_VPS_PROXMOX_CA`, `LTT_VPS_PROXMOX_TLS_NAME` (`pve`);
   CA ngoài Git, không disable TLS. Secrets OVH đi qua canonical credential loader.
6. Bật bounded acquisition chỉ khi exact cart GET preview còn hợp lệ: một item
   `ip-failover-arin`, SG/SGP/P1M, USD 239 minor gồm thuế; ceiling 239,
   accepted_contract_fingerprints đúng digest read-only và timeout 3600 giây.
   Cart `efae624e-6114-46b9-ace5-3063f9fc1580` hết hạn `2026-09-15T08:53:23Z`.
   Cart hết hạn/đã dùng/quote đổi phải block, không tự tạo replacement live.
7. Refresh collector Machine B, exact active owner/allowlist, gateway health và
   protected VM100–107/IP/mapping trước activation. Không dùng snapshot stale.

## Rollback và nghiệm thu

- Nếu deploy/schema/readiness fail: giữ rollout/default OVH tắt, phục hồi app
  snapshot cũ theo installer runbook; không downgrade additive schema tùy tiện,
  không overwrite secrets, không tác động protected VM. Ghi đúng kết quả thật.
- Sau checkout: mất response chỉ exact GET recovery, không POST lại. Pending
  delivery defer worker tối đa 60 phút từ durable checkout_requested_at; không
  mua IP/trừ credit lần nữa. Quá hạn/ownership mơ hồ chuyển NEEDS_REVIEW.
- Live đúng một IP/VM mới, normal-user browser thật, network/console/lifecycle
  read-back. Cuối test giữ VM stopped, IP BOUND và mapping; không destroy.
- Full gate chỉ H46.9 cuối theo PO, không giữa phase hoặc pre-deploy. Chưa gate
  xanh không ghi HANDOFF_READY_FINAL hoặc FULL PRODUCTION READY.
- Khi gộp cuối: xử lý va chạm nhãn quyết định Q124 (canonical root GitHub so với
  VPS infrastructure) theo nội dung/lý do, không dùng cả-file ours/theirs.
  Backup CAPACITY_BLOCKED, restore và dual-WAN chưa verified phải báo riêng.
