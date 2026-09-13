# VPS V4 — Discovery

Ngày khảo sát: 2026-09-12. Đây là hồ sơ bằng chứng, không phải bằng chứng live
acceptance.

## Kho và nhánh

| Phạm vi | Nhánh/commit xuất phát | Kết luận |
|---|---|---|
| LTTSTUDIOSAPP | `main` @ `3b5adcb7ffa43c8c553ac38d457e22e3cde60e30` | VPS V2 mới nhất đã nằm trong `main`; nhánh VPS cũ `78ba1d50` là tổ tiên của `main` |
| Nhánh triển khai app | `codex/vps-v4-infrastructure-profiles` | Worktree riêng `D:\LTTSTUDIOSAPP-vps-v4`, sạch lúc bắt đầu |
| LTT-VM-Promox | `claude/machine-b-hardening-v1` @ `2d14480d170b3aa9f9dd24dc5956cadd64d0143e` | Đây là dòng mới hơn `main`; Phase 11 audit lần hai đang mở |
| Nhánh tích hợp infra | `codex/vps-v4-infrastructure-profiles` | Worktree riêng `D:\LTT-VM-Promox-v4`, sạch lúc bắt đầu |
| Nguồn vận hành `H:\PROXMOX` | Không mount trên máy làm việc | Không thể thu runtime live; mọi kết luận live bị chặn |

Không worktree VPS mới hơn được tìm thấy. Không thay đổi worktree/branch của
phiên khác.

## Năng lực làm việc

Không có bộ skill mang đúng tên Superpowers trong môi trường. Quy trình tương
đương được thực hiện thủ công: discovery → phân loại câu hỏi → decision lock →
mô hình hiện tại/đích → kế hoạch → test-first → verification/review. GUI sẽ
dùng Playwright CLI theo chính sách dự án.

## Mã ứng dụng hiện tại

- `VpsGateway` đang vừa là gateway vừa là selector hạ tầng.
- `VpsIp.vultr_id` đưa chi tiết Vultr vào domain lõi.
- `VpsInstance` chưa có `infrastructure_profile_id`.
- `jobs.py` gọi trực tiếp Proxmox, Vultr và gateway; profile/default chưa được
  ghim trước mutation ngoài.
- `VpsThaoTac` theo dõi operation/UPID nhưng chưa phải mutation journal từng
  bước có idempotency key.
- Vultr adapter hiện hữu đã có allocation/attach/detach/delete, timeout và kiểm
  ownership; phải bọc lại tối thiểu, không viết lại.
- VPS không có ToolSpec hay `/api/v1/vps`; disposition cũ vẫn ghi `DEFER`.
- Trang `/vps` hiện có bề mặt ẩn danh; mutation yêu cầu session/CSRF và query
  instance đã lọc theo owner.
- Không có extension point để app tự đăng ký một miền mới vào cây `ADMIN`.
  `server/routes/admin/_chung.py` và `server/admin.py` giữ registry trung tâm.
- `AppAccess` không biểu diễn rollout owner-only mặc định; pattern allowlist ID
  theo biến môi trường đã tồn tại ở app Agent Canvas và có thể tái dùng trong
  phạm vi app.

Chi tiết coupling inventory sẽ được giữ cùng test/patch khi implementation bắt
đầu; phân loại chuẩn là `CORE COUPLING`, `VULTR ADAPTER`, `LEGACY DATA`, `TEST`,
`DOC`, `DEAD CODE`.

## Machine B và OVH đã quan sát

Snapshot gần nhất trong nhánh hardening sinh lúc `2026-09-10T07:36:30Z`:

- PVE 9.2.2 chạy lồng, mạng riêng `10.50.0.0/24`, WireGuard và nftables hoạt
  động tại thời điểm snapshot.
- VM100–VM107 đang chạy và là tài sản được bảo vệ; VPS V4 không import, đổi số,
  reboot, đổi NIC/IP hay xóa chúng.
- Gateway là OVHcloud VPS Singapore; các Additional IP hiện hữu được định tuyến
  tới gateway rồi ánh xạ 1:1 bằng nftables.
- Tám mapping hiện hữu tương ứng tám VM được bảo vệ. Snapshot không chứng minh
  còn IP rảnh vào ngày triển khai.
- OVH dùng API endpoint khu vực CA/ASIA và cơ chế ký request bằng ba credential;
  DB chỉ được giữ `credential_ref`, không giữ giá trị.
- Luồng order Additional IP là thao tác cart/checkout có hệ quả billing. Nó
  không được nằm trong provisioning thông thường.
- Runtime publication hiện atomic theo từng file, chưa atomic theo generation.
  Consumer V4 phải fail closed nếu schema không hỗ trợ, timestamp giữa các file
  lệch, collector status không success, hoặc dữ liệu quá hạn.
- Data protection đang `CRITICAL`: chưa có Backup V2/restore đã kiểm chứng và
  dung lượng đích đã đo thiếu khoảng 146 GB. Không xóa backup cũ để làm xanh.
- Có 146 package upgrade PVE đang chờ ở snapshot; không restart dịch vụ/host
  khi chưa có maintenance approval.

Tài liệu OVH chính thức dùng để xác nhận thuật ngữ và billing flow:

- <https://docs.ovhcloud.com/en/guides/public-cloud/network-services/buy-additional-ip>
- <https://support.us.ovhcloud.com/hc/en-us/articles/360011668000-Purchasing-and-managing-Additional-IPs>
- <https://us.ovhcloud.com/network/additional-ip/>

## Production config preflight không bí mật

`python tools\vps_kiem_cau_hinh.py` đã đọc canonical production env và chỉ báo
tên/trạng thái biến:

- cấu hình Vultr/Proxmox/router/gateway cũ và năm ISO: có;
- `LTT_VPS_PROXMOX_CA`: thiếu;
- route điều khoản: sống.

Không giá trị credential nào được ghi vào hồ sơ. Thiếu CA là blocker fail-closed
cho TLS production; không được hạ xuống `verify=False`.

## Kết luận discovery

Hướng phù hợp bằng chứng là ba contract nhỏ và profile ghim vào instance. OVH
dùng pool Additional IP đã sở hữu (`OvhStaticIpPoolBackend`) cho đường cấp phát
bình thường. Dynamic order, nếu cần một IP test theo D10, là change-gated operator
operation riêng có read-back và mutation journal.
