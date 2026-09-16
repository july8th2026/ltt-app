# VPS V4 — Decision Lock

Khóa ngày 2026-09-12, trước mọi sửa production code.

## D01–D10

1. VPS là web-only; không public API, ToolSpec, SDK hay API-key provisioning.
2. Giữ OVH và Vultr.
3. `OVH-SGP-PROD` là ACTIVE/default cho máy production mới, nhưng chỉ sau
   preflight live đạt.
4. `VULTR-SGP` là STANDBY, không nhận máy production mới mặc định.
5. Đổi default chỉ ảnh hưởng request mới; instance luôn ghim profile.
6. Khách chọn region/plan/OS, không chọn provider/profile/gateway.
7. VM100–VM107 cùng IP/mapping/WG identity là protected resources.
8. Windows MVP là blank VM + official ISO; manual installer được chấp nhận.
9. Live owner được resolve thành đúng một canonical user ID; không hardcode email.
10. Live acceptance dùng/tạo tối đa một OVH public IPv4.

## Khóa kỹ thuật rút ra từ bằng chứng

- Domain model nằm trong `apps/vps`.
- Ba contract độc lập: compute, public IP, gateway.
- Existing Proxmox/Vultr/gateway clients được bọc lại, không viết lại vì style.
- OVH provisioning ưu tiên pre-owned static pool. Theo Q130, khi pool hết IP,
  web provisioning tự chạy acquisition có journal/price guard/provider
  read-back; admin không duyệt từng order và acquisition vẫn tách khỏi thao tác
  `reserve()` thuần CSDL.
- Profile được persist trước mutation ngoài đầu tiên; mọi job/lifecycle/reconcile
  dùng profile đã pin.
- Default có partial unique constraint và service transaction; activation/default
  fail closed nếu preflight không đạt.
- Mutation journal ghi intent trước external call, rồi read-back mới đánh observed.
- Runtime Machine B phải cùng generation, supported schema, collector success và
  còn fresh; nếu không thì `UNKNOWN`/`STALE` và không activate.
- Record cũ chỉ backfill VULTR khi có evidence. Mơ hồ giữ `NEEDS_REVIEW`.
- Rollout MVP là authenticated + canonical user-ID allowlist; không hardcode email.
- Không xây live network-profile migration; giữ tên future operation
  `MIGRATE_NETWORK_PROFILE` trong tài liệu.

## Chưa khóa, không được tự suy diễn

- C01 **ĐÃ KHÓA 2026-09-13**: chủ dự án chọn “Cho phép bổ sung hợp đồng admin
  chung”. Cho phép extension generic trong registry/server cho metadata điều
  hướng, render vỏ và audit; domain/routes vẫn app-owned. Không cho phép hardcode
  tên VPS trong server hoặc bỏ gate quyền/CSRF.
- C03 **ĐÃ KHÓA 2026-09-14**: giữ đúng VM acceptance ở trạng thái tắt và giữ IP
  để kiểm tra tiếp. Không destroy VM, không unbind/release IP do test hoàn tất.
- C05 **ĐÃ KHÓA, CẬP NHẬT 2026-09-14**: ban đầu giao canonical tích hợp/deploy;
  PO xác nhận phiên canonical đã ngừng và giao phiên VPS tự tiếp tục triển khai
  từ worktree này. Main và năm tài liệu dirty của phiên khác phải giữ nguyên;
  gộp main chỉ ở cuối phiên sau nghiệm thu, không merge giữa phase.
- C06 **ĐÃ KHÓA 2026-09-14**: đơn OVH đã nhận/thanh toán được chờ tối đa
  60 phút theo timestamp durable trước checkout. Worker defer/read-back, không
  sleep giữ worker, không mua lại và không trừ credit khách lần nữa.
- Mọi downtime/reboot/WAN-cut/restore boot và billing **bất ngờ** chỉ được thực hiện
  tại gate tương ứng.

Không dùng phần chưa khóa để phá hủy live resource. Gate tổng chỉ chạy H46.9
nghiệm thu cuối theo chỉ đạo PO; không chạy full gate giữa phase hoặc pre-deploy.
