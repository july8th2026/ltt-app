# VPS V4 — Current Architecture

## Luồng hiện tại

```text
Web route (region/plan/OS)
  -> VpsGateway selected
  -> VpsInstance (gateway_id, no profile_id)
  -> queued vps.provision
  -> jobs.py
       ProxmoxClient.create_blank_vm
       router DHCP/private network
       VultrClient.create_reserved_ip + attach
       gateway nft mapping
       boot/observe
```

## Mô hình dữ liệu

| Bảng | Vai trò hiện tại | Khoảng trống V4 |
|---|---|---|
| `vps_gateway` | vùng, endpoint, provider instance, WG/private network | Trộn gateway với infrastructure selection |
| `vps_ip` | public IP, `vultr_id`, gateway, binding | Provider coupling; thiếu generic resource/state/reservation |
| `vps_instance` | owner/plan/OS/gateway/VMID/lifecycle | Không pin profile |
| `vps_thao_tac` | operation/UPID/error | Không ghi intent/readback từng external mutation |
| `vps_event` | sự kiện instance | Không thay thế admin audit/profile health |

## Coupling inventory

| Nhóm | Ví dụ | Hướng xử lý |
|---|---|---|
| CORE COUPLING | `jobs.py` import Vultr, `VpsIp.vultr_id`, reconcile giả định Vultr | Chuyển qua contract/profile, giữ cột legacy trong migration đầu |
| VULTR ADAPTER | `services/vultr.py` | Bọc tối thiểu trong `VultrReservedIpBackend` |
| LEGACY DATA | row có `vultr_id`, instance chưa profile | Evidence-based backfill hoặc NEEDS_REVIEW |
| TEST | VPS test mock trực tiếp client/provider | Giữ regression và thêm contract/failure/concurrency |
| DOC | Q103–Q105, `docs/vps_v2` | Q129 mở rộng/thay phần provider selection; không xóa lịch sử |
| DEAD CODE | Chỉ kết luận sau coverage/call-site search | Không xóa theo suy đoán |

## Bề mặt và quyền

- VPS là app customer, manifest hiện `public=True`, lifecycle development.
- Mutation web có session/CSRF; ownership filter hiện hữu cần giữ.
- Không có public ToolSpec/API, nhưng disposition chưa được khóa bằng code test.
- Không có contract để app đóng góp admin navigation/view. Việc thêm trực tiếp
  registry VPS vào server sẽ vi phạm ranh giới app hiện hành.

## Điểm mạnh giữ nguyên

- Job queue cho thao tác dài.
- Operation lock/state/UPID và read-back lifecycle đã được VPS V2 harden.
- Compute capacity đọc cả VM ngoài app, tránh bán phần RAM/đĩa của VM chủ nhà.
- Vultr safety/ownership semantics đã có regression.
- Gateway code đã đóng gói SSH/nft; command không cần rò vào domain mới.

Theo weak-first, không refactor các phần mạnh này ngoài mức cần để cắm contract.
