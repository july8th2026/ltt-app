# Chuẩn hoá danh tính VPS — máy mới tự đúng, máy cũ được kéo về chuẩn

Ngày 2026-09-25. Làn `phien/vps-chuan-hoa`, dải test **3500–3599**.

## Vì sao

Phân tích 25/09 so VPS của ta với Vultr. Ba khoảng cách **đo được**:

| Đo thật | Ta | Vultr |
|---|---|---|
| `ipfilter`/`macfilter` per-VM | **tắt** (`firewall=0`) | có ở tầng hạ tầng |
| CPU model | *không khai* → `kvm64` generic | model thật |
| PTR (rDNS) | **không IP nào có** | có mặc định |

Chủ dự án chốt ranh giới 25/09: **chuẩn mực vận hành + an ninh**. ⛔ Không làm
phần che dấu vết nhà cung cấp (giữ nguyên tiền tố `LTT-` ở serial, ⛔ không giả
`manufacturer`/`product` — `dinh_danh.smbios1` đã chốt điều này từ trước).

⚠️ Và một đính chính ghi lại để không ai đi vòng lại: lo ngại *"PTR trỏ về
`lttstudios.com` sẽ thành dấu hiệu nhóm"* là **làm quá**. Vultr dùng
`*.vultrusercontent.com`, AWS dùng `*.compute.amazonaws.com`, OVH dùng
`*.ovh.net` — mọi nhà cung cấp đều vậy. Ai muốn nhóm các IP này **đã biết**
chúng thuộc OVH qua ASN 16276 + cờ `hosting: true`; chuỗi PTR không thêm gì.

## Điều đã ĐO, không đoán

- **OVH bắt buộc forward-confirm.** Thử thật trên `51.79.202.1`:
  `POST /ip/51.79.202.1%2F32/reverse` →
  `400 {"message":"Cannot check if ip-51-79-202-1.vps.lttstudios.com. resolves to 51.79.202.1"}`
  ⇒ phải tạo A record **trước**, nên PTR cần một token DNS. Không có token thì
  hạng mục này không chạy được — và nó **không được** làm hỏng việc tạo máy.
- Cấu hình thật của hai VM khách (204, 208): MAC/UUID/serial đĩa/serial máy đều
  **khác nhau** (`dinh_danh.py` làm đúng); `machine`/`bios`/NIC/CPU thì giống.

## Các pha

### Pha 1 — Máy MỚI tự đúng (không cần secret nào)

`jobs._tao_may` đặt thêm, ngay ở bước dựng VM:
- `cpu: host` — bỏ `kvm64`. Cụm chỉ có một node nên không vướng live migration.
- firewall per-VM: `enable=1`, `policy_in=ACCEPT`, `policy_out=ACCEPT`,
  `ipfilter=1`, `macfilter=1`.
  ⚠️ **Bật firewall mà để policy mặc định DROP là cắt mạng của khách.** Mục tiêu
  ở đây **chỉ** là chống giả mạo IP/MAC, không phải lọc gói — nên hai policy
  phải ACCEPT tường minh, và có phép kiểm chốt đúng điều đó.

### Pha 2 — Máy ĐÃ CÓ được kéo về chuẩn

`tools/vps_chuan_hoa.py`, chạy được nhiều lần:
- firewall/ipfilter/macfilter: áp **ngay**, có hiệu lực không cần tắt máy.
- `cpu host`: ghi vào cấu hình; ⚠️ **chỉ có hiệu lực sau một chu kỳ tắt/bật**.
  ⛔ Công cụ **không** tự tắt máy khách. Nó ghi cấu hình, nói rõ máy nào đang
  chờ chu kỳ tắt/bật, và để chủ máy chọn thời điểm.

### Pha 3 — PTR (chặn ở token DNS)

- `ovh.OvhClient`: thêm `reverse()` / `dat_reverse()`. Rào `post()` hiện chỉ cho
  `/order/cart` — **mở đúng một đường** `/ip/*/reverse`, không mở rộng hơn.
- `dns_cloudflare.py`: tạo/sửa A record `ip-<a>-<b>-<c>-<d>.vps.lttstudios.com`.
- Nối vào job tạo máy **sau** `OVH_IP_ACQUIRE` thành công, và vào `vps_chuan_hoa`
  để backfill IP đã có.
- ⛔ **Không được ném**: PTR hỏng thì máy vẫn phải giao được. Ghi cảnh báo.

### Pha 4 — Không im lặng

Vòng bảo trì kiểm và ghi bản ghi sức khoẻ `chuan_hoa_may` (tầng
`CANH_BAO_BAO_TRI`, ⛔ **không** chặn bán): máy nào còn `kvm64`, còn `firewall=0`,
hoặc IP nào chưa có PTR thì hiện ra. Cùng khuôn `cong_quan_tri` (24/09): thiếu
bản ghi = STALE, khác hẳn "đạt".

## Không làm (YAGNI)

- VLAN per-customer: chủ dự án chỉ ra đúng rằng máy chung LAN vật lý là chuyện
  bình thường; `ipfilter`/`macfilter` xử đúng rủi ro (ARP/IP spoofing) với chi
  phí nhỏ hơn nhiều. Xem lại nếu có khách lạ thứ hai trên `vmbr1`.
- Cho khách tự đặt PTR (như Vultr): cần giao diện + chống lạm dụng tên.
- MTU 1500: hệ quả của WireGuard, không bỏ được nếu giữ kiến trúc tunnel.
