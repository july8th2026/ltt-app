# VPS V4 — Questions and Answers

Mọi câu hỏi nằm đúng một lớp: `LOCKED` (D01–D10), `A` (trả lời từ code), `B`
(trả lời từ hạ tầng/runtime/tài liệu provider), hoặc `C` (cần PO/auth/money/
downtime). `LOCKED` không được hỏi lại.

| Question | Evidence | Candidate A | Candidate B | Recommended answer | Product answer | Implementation consequence | Locked? |
|---|---|---|---|---|---|---|---|
| D01 — VPS có public API/ToolSpec không? | Yêu cầu §3 D01; hiện không có VPS ToolSpec | Web only | Public API | Web only | WEB ONLY | Test catalog/route/API-key đều không vào VPS | LOCKED |
| D02 — Giữ provider nào? | Yêu cầu §3 D02 | OVH + Vultr | Chỉ OVH | Giữ cả hai | TWO PROFILES | Vultr thành adapter, không bị xóa | LOCKED |
| D03 — Profile nhận máy production mới? | Yêu cầu §3 D03 | OVH | Vultr | OVH | `OVH-SGP-PROD` ACTIVE/default | Seed/configure OVH default sau preflight | LOCKED |
| D04 — Vai trò Vultr? | Yêu cầu §3 D04 | Standby | Xóa | Standby | `VULTR-SGP` STANDBY | Không accept new mặc định; vẫn health-checkable | LOCKED |
| D05 — Đổi default có repin máy cũ? | Yêu cầu §3 D05 | Không | Có | Không | Không migrate ngầm | Job chỉ đọc profile đã lưu trên instance | LOCKED |
| D06 — Khách chọn provider/gateway? | Yêu cầu §3 D06 | Không | Có | Không | Chỉ region/plan/OS | Bỏ mọi profile/provider field từ input công khai | LOCKED |
| D07 — Xử lý VM100–107? | Yêu cầu §3 D07; runtime xác nhận đang chạy | Bảo vệ | Đưa vào V4 | Bảo vệ | Không mutation | Scope guard VMID 200–899; test negative | LOCKED |
| D08 — Primitive Windows đầu tiên? | Yêu cầu §3 D08 | Blank VM + ISO | Clone template | Blank VM + ISO | Manual install chấp nhận | Không chờ Autounattend/QGA | LOCKED |
| D09 — Owner live test? | Yêu cầu §3 D09 | Resolve canonical user ID | Hardcode email | Resolve đúng một user | `akakenly.design@gmail.com` | ID chỉ đi qua controlled setup/config; zero/multiple thì block | LOCKED |
| D10 — Trần IP live? | Yêu cầu §3 D10 | Tối đa một | Nhiều IP | Tối đa một | 1 | Inventory trước; order tối đa một; không đụng IP protected | LOCKED |
| A01 — Vultr cấp IP thế nào? | `services/vultr.py`, `jobs.py` | Bọc adapter hiện hữu | Viết lại generic provider | Bọc tối thiểu | Trả lời từ code | Giữ label/ownership/timeout/error semantics | A — ANSWERED |
| A02 — Profile nằm ở đâu? | App tables/services sở hữu domain VPS | `apps/vps` | `platform_core` | `apps/vps` | Trả lời từ contract repo | Không sửa core cho domain model | A — ANSWERED |
| A03 — Owner-only dùng gì? | Pattern rollout app Agent Canvas; AppAccess không có deny-by-default | Env allowlist canonical user ID | Hệ auth mới | Reuse rollout pattern app | Trả lời từ code | `LTT_VPS_ROLLOUT` + ID allowlist; admin được phép | A — ANSWERED |
| A04 — Anonymous visibility? | `manifest.public=True`; `/vps` hiện là marketing công khai | Authenticated-only | Giữ catalog công khai | Authenticated-only cho MVP | Yêu cầu §37 ưu tiên trạng thái này | Manifest/private route guards và test redirect/404 theo convention | A — ANSWERED |
| A05 — Admin audit dùng gì? | `NhatKyAdmin`/`ghi_nhat_ky` là authority hiện tại | Reuse audit | Tạo bảng generic mới | Reuse | Trả lời từ code | Không log secret; actor/action/profile/before-after đã sanitize | A — ANSWERED |
| A06 — Migration record cũ? | `vultr_id` là bằng chứng mạnh; row không đủ evidence có thể tồn tại | Backfill có điều kiện | Gán tất cả | Có evidence thì VULTR, còn lại NEEDS_REVIEW | Trả lời từ dữ liệu/schema | Additive migration, không auto-delete/repin mơ hồ | A — ANSWERED |
| A07 — Ordering giảm leak? | OVH pool là pre-owned; VM mutation dài; mapping có readback | VM→network→IP→mapping→boot | IP→VM | A | Trả lời từ failure analysis | Journal trước mỗi mutation; mapping verify trước boot | A — ANSWERED |
| A08 — Default được enforce ở đâu? | UI không chống race; PostgreSQL hỗ trợ partial unique index | DB + service | UI | DB + service | Trả lời từ code/DB | Unique partial default; locked transaction; health gate | A — ANSWERED |
| A09 — Profile bị disable giữa job? | Instance đã pin; DISABLED cấm normal mutation | Dừng trước mutation kế tiếp, chỉ reconcile/compensate | Tiếp tục mọi bước | Dừng fail-closed | Semantics §11 | Journal `BLOCKED_PROFILE_DISABLED`; không đổi default/pin | A — ANSWERED |
| A10 — Có xây migration live giữa provider? | Yêu cầu §48 | Defer | Xây ngay | Defer | `MIGRATE_NETWORK_PROFILE` future | Không có repin endpoint trong V4 | A — ANSWERED |
| B01 — OVH IP là dynamic hay pool? | Machine B: Additional IP đã routed tới gateway, nft 1:1; order là checkout | Static pool cho provisioning | Order trong mỗi job | Static pool | Trả lời từ infra/provider | `OvhStaticIpPoolBackend`; order là operator change riêng | B — ANSWERED |
| B02 — Provider bind hay gateway bind? | Additional IP routed tới OVH gateway; destination VM qua nft/WG | Gateway mapping | Per-VM provider attach | Gateway mapping | Trả lời từ topology | OVH IP backend reserve state; GatewayBackend owns mapping | B — ANSWERED |
| B03 — Runtime truth được consume ra sao? | Ba JSON có thể lệch generation | Strict version/timestamp/freshness | Tin file mới nhất riêng lẻ | Strict/fail closed | Trả lời từ producer contract | unknown/stale/degraded/critical/healthy; không copy collector | B — ANSWERED |
| B04 — Có IP live rảnh không? | Snapshot 10/09 có 8 mapped/8 protected; không phải live ngày 12/09 | Inventory live | Suy từ snapshot | Inventory live | Chưa có bằng chứng | Block acquisition cho đến collector/provider read-back live | B — OPEN LIVE |
| B05 — Backup/restore sẵn sàng chưa? | STATE: capacity thiếu, chưa V2/restore | CAPACITY_BLOCKED | Xóa backup cũ | CAPACITY_BLOCKED | Trả lời từ runtime | Báo riêng, không giả full production ready | B — ANSWERED |
| C01 — Cho phép mở rộng contract `server` để app đăng ký `ADMIN > VPS > Cổng hạ tầng` chứ? | App contract thiếu generic admin extension | Patch generic app-admin extension | Trang operator-only riêng | Generic contract | Cho phép bổ sung hợp đồng admin chung, 2026-09-13 | AppManifest.admin_nav và request-scoped app context; không hardcode VPS trong server | LOCKED |
| C02 — Nếu provider checkout báo giá khác chi phí Additional IP đã dự kiến thì tiếp tục? | D10 cho phép tối đa một; provider billing thực tế chỉ biết ở cart/read-back | Dừng tại quote bất ngờ | Thanh toán bất kỳ giá nào | Dừng nếu quote/currency/chu kỳ bất ngờ | Chưa phát sinh | Không checkout trước explicit money gate khi quote bất ngờ | C — CONDITIONAL |
| C03 — Sau acceptance giữ hay xóa test VM? | §46 yêu cầu approval/agreed plan; destroy là destructive | Giữ stopped để manual Windows tiếp tục | Destroy và trả IP về FREE | Giữ stopped đến khi PO chọn cleanup, vì D08 cần manual install | Chưa có | Không tự destroy; IP vẫn BOUND nếu giữ | C — OPEN AT CLEANUP |
| C04 — Các phép reboot/restore/WAN-cut/package restart? | §51–53, §62 | Xin gate đúng lúc | Tự chạy | Xin gate đúng lúc | Chưa có | Backlog riêng; không chặn offline implementation | C — DEFERRED GATES |

## Gate hiện tại

Phần thiết kế/implementation app không bị C02–C04 chặn. C01 đã được duyệt;
generic admin contract và browser regression đã triển khai. B04, H:-mount,
PVE CA và actual OVH `gwnat`/persistence adapter chặn live preflight/acquisition,
không chặn công việc offline. Không bật adapter legacy cho actual OVH để đi vòng.
