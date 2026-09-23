# VPS bán thật — sổ nguồn lực, cổng bán hai tầng, băng thông giữ được

Ngày 2026-09-23. Chủ dự án chốt bốn quyết định trong phiên; tệp này là bản ghi.

## Vì sao có tệp này

Ngày 23/09 chủ dự án không tạo được VPS. Trang in *"Hết chỗ cho cấu hình này"*
cho cả ba gói. Đo trên production: compute còn 14/9/6 chỗ, gateway còn 150 chỗ.
**Không tài nguyên nào hết.** Câu đó là một lỗi sức khoẻ bị dịch sai thành một
lời từ chối bán hàng.

Truy ngược lộ ra bốn khuyết tật và hai trần cứng chưa ai đo.

### Bốn khuyết tật

1. **Sức khoẻ đỏ hiển thị thành "hết chỗ".** `_gioi_han_ban` bắt
   `ProfileNotReady` rồi trả `None`; `trang_chinh` đọc `None` thành
   `con_cho = False` cho mọi gói. Khách đọc một câu sai sự thật.
2. **Một bộ đếm gói rơi đóng cả cửa hàng.** `network` lấy thẳng
   `domains.network` của Máy B, mà miền đó đỏ **chỉ** vì
   `wireguard.gateway.tx_dropped`; 12/13 phép kiểm mạng còn lại đều PASS.
   Lịch sử từ 16/09: HEALTHY 608 · CRITICAL 136 · DEGRADED 94 · STALE 173 —
   cửa hàng bật tắt theo cửa sổ 10 phút.
3. **Hai chỗ tính IPv4 lệch nhau.** `preflight.py` gọi
   `effective_ipv4_slots(ip_details)`; `routes.py` gọi cùng hàm đó **có** trừ
   `promised_without_ip`. Thành phần `capacity` có thể xanh trong khi trang
   hiện 0 chỗ.
4. **Trần băng thông là hằng số của nhà cung cấp cũ.**
   `bang_thong.TRAN_CONG_VAO_GB = 2048` với chú thích *"Cổng vào Vultr có
   2 TB/tháng"*. Cổng vào nay là OVH. `tong_da_hua_gb()` viết ra để canh bán
   chồng nhưng **không chỗ nào gọi**.

### Hai trần cứng chưa ai đo

- **IPv4: 16.** Cổng vào là OVH VPS-1 2027 (`vps-1a9e4515.vps.ovh.ca`, zone
  `os-sgp2`), `maximumAdditionnalIp = 16`. Đã dùng 9 (8 cho VM100–107, 1 cho
  máy thử) ⇒ **còn 7**. Đây là ràng buộc chặt nhất — chặt hơn compute.
- **Băng thông: 1 TB/tháng.** OVH công bố: VPS ở Mumbai/Singapore/Sydney có
  hạn mức tháng 1 TB cho VPS-1 và VPS-2; vượt thì **hãm xuống 10 Mbps**
  (`ovhcloud.com/en-sg/vps/unmetered-vps/`, chân trang). Đo trên `ens3` qua
  27,75 ngày: RX 234,5 GB + TX 239,4 GB ⇒ ~512 GB/tháng nền production.
  Bảng giá đang hứa 300/600/1000 GB **mỗi máy**.

⚠️ Vạch 10 Mbps đập vào **cả VM100–107** — việc thật của chủ dự án. Bán chồng
băng thông ở đây đắt hơn bán chồng đĩa.

## Bốn quyết định của chủ dự án

| # | Câu hỏi | Chốt |
|---|---|---|
| 1 | Quy mô 3–6 tháng đầu | 5–15 máy (thử thị trường) |
| 2 | Nguồn IP | Mua theo yêu cầu, **nói trước thời gian chờ**, thu tiền sau khi có IP, tự hoàn nếu quá hạn |
| 3 | Cổng bán | **Tách** tín hiệu "không giao được" khỏi tín hiệu "chạy chưa mượt" |
| 4 | Trần cổng vào | **Hạ băng thông trong bảng giá** cho vừa 1 TB (không nâng cổng vào) |

---

## Mục 1 — Sổ nguồn lực

`apps/vps/services/nguon_luc.py` là **nguồn chân lý duy nhất** cho câu hỏi
"bán được gói này không, vì sao không".

```python
@dataclass(frozen=True)
class KetQua:
    ban_duoc: bool
    so_cho: int
    rang_buoc: str          # compute | ipv4 | gateway | bang_thong | suc_khoe
    cau_cho_khach: str      # MOT cau da dich, khong ten he thong noi bo
    cau_cho_van_hanh: str   # chi tiet ky thuat: log + trang admin

def con_ban_duoc(db, plan_id, *, dia_them_gb=0) -> KetQua
def so_nguon_luc(db, profile=None) -> SoNguonLuc   # bang day du cho admin
```

Ba nơi gọi, không nơi nào tự tính: `routes.trang_chinh`, `routes.tao_may`,
`preflight.run_profile_preflight`. Xoá `_gioi_han_ban`,
`_gioi_han_ip_va_cong`, `_so_cho_ban` khỏi `routes.py`; xoá phép tính IPv4
trùng trong `preflight.py`. Khuyết tật 1 và 3 biến mất theo cấu trúc, không
nhờ vá.

### Ràng buộc đo được (23/09/2026)

| Tài nguyên | Trần | Đã dùng | Bán được |
|---|---|---|---|
| Đĩa thin (bán chồng ≤ 3×) | 1.287 GB hứa | 690 GB | 14 Nhỏ / 9 Vừa / 7 Lớn |
| RAM | 96,6 GB | 37,0 GB | 28 / 14 / 7 |
| vCPU (≤ 3×) | 72 | 18 | 54 / 27 / 13 |
| **IPv4 cổng vào** | **16** | 9 | **7 — bất kể gói** |
| **Băng thông cổng vào** | **1.024 GB/tháng** | ~512 GB nền | xem mục 4 |
| Chỗ NAT gateway | 150 | 1 | không chặn |

---

## Mục 2 — Đặt máy: giữ chỗ trước, thu tiền sau khi có IP

### Hiện tại (hỏng thật, đo 22/09)

`POST /vps/tao` thu đủ tiền **trước** khi nộp job; job mua IP ở OVH giữa
luồng. Hai lần thử của chủ dự án đều chết ở `OVH_IP_ACQUIRE`
(`pre_checkout_failure`), mỗi lần thu 1.490 rồi hoàn 1.490 rồi xoá máy.

### Mới — dùng lại nguyên thuỷ đã có của nền tảng

`platform_core/credit.py` đã có `giu_cho(db, user, amount, job_id)` /
`quyet_toan(db, user, job_id, actual)`; `actual=0` nhả hết, quyết toán
idempotent. VPS không dùng — nó gọi `tru()` thẳng. Đổi sang:

```
POST /vps/tao   nguon_luc.con_ban_duoc -> tao VpsInstance
                -> jobs.submit(...) -> credit.giu_cho(job_id, gia) -> commit
                (khong tru credit; van khong cho khach het tien chiem cho)

job  VM_CREATE -> VM_CONFIG -> DHCP_AND_BANDWIDTH -> OVH_IP_ACQUIRE
     -> PUBLIC_MAPPING -> VM_BOOT
     -> credit.quyet_toan(job_id, gia) + billing.mo_chu_ky(may)

job hong / qua han -> credit.quyet_toan(job_id, 0)    # nha het, khong "hoan"
```

`billing.thu_mot_chu_ky` giữ nguyên cho **gia hạn định kỳ**; tạo mới đi đường
giữ chỗ. Khách không còn thấy "đã thu 1.490" rồi "đã hoàn 1.490" cho một máy
chưa từng tồn tại.

### Nói trước thời gian chờ

Trang tạo máy hiện **thời gian sẵn sàng ước tính**, tính từ đo thật chứ không
viết cứng: p50/p90 của các lần provision thành công gần đây
(`VpsExternalMutation` có `created_at`/`observed_at` cho từng bước). Chưa đủ
mẫu thì dùng khoảng đã quan sát (16/09: 3 phút 24 giây từ `tao_moi` tới
`VM_BOOT` observed).

Hạn chót cứng: quá `order_delivery_timeout_seconds` thì job tự dừng, nhả giữ
chỗ, ghi sự kiện khách đọc được, và **không** để lại máy nửa vời.

---

## Mục 3 — Sức khoẻ hai tầng

```python
CHAN_BAN = ("compute", "ip", "gateway", "capacity")
CANH_BAO = ("network", "runtime")
```

- `select_profile` chỉ đòi tầng `CHAN_BAN` xanh.
- Tầng `CANH_BAO` đỏ ⇒ ghi cảnh báo vận hành và hiện trạng thái cho khách
  **đang dùng**, **không** chặn bán.
- `activate_profile` (thao tác của người vận hành) vẫn đòi **cả sáu** xanh:
  bật bán lần đầu là một quyết định có người, khác với giữ cửa hàng mở.

Lý do tách: `tx_dropped` là chỉ số chất lượng đường hầm. Gói rơi trong hầm
không ngăn `qm clone` chạy. Đo 30 giây lúc 15:40 ngày 23/09: 1.786 gói TX,
**0 gói rơi**, 0,12 Mbit/s — các cụm rơi là từng đợt, không liên tục.

### Thông điệp cho khách

Không bao giờ in "hết chỗ" cho một nguyên nhân không phải hết chỗ. Bảng câu
sinh từ `KetQua.rang_buoc`:

| `rang_buoc` | Câu cho khách |
|---|---|
| `compute` | "Gói này tạm hết chỗ." (kèm gói còn bán được, như hiện nay) |
| `ipv4` | "Tạm hết địa chỉ IP. Chúng tôi đang bổ sung." |
| `bang_thong` | "Tạm ngưng nhận máy mới trong tháng này." |
| `gateway` | "Tạm ngưng nhận máy mới." |
| `suc_khoe` | "Hệ thống đang bảo trì, tạm chưa nhận máy mới." |

---

## Mục 4 — Băng thông giữ được

### Số học

```
Tran OVH VPS-1 SGP                          1.024 GB/thang
- Nen production (VM100-107), do that          512 GB
- Du tru an toan 15%                           154 GB
-----------------------------------------------------
= Ngan sach THAT cho khach                     358 GB/thang
x He so ban chong 2,5 (cong khai, giam sat)
-----------------------------------------------------
= Ngan sach HUA cho khach                      895 GB/thang
```

Nền 512 GB lấy **tổng hai chiều** — OVH không nói rõ đếm chiều nào, nên giả
định thận trọng. Cờ `LTT_VPS_DEM_HAI_CHIEU=false` đổi sang chỉ chiều ra nếu
sau này xác định được; ngân sách tự gấp đôi, không sửa mã.

### Bảng giá

| Gói | Cũ | **Mới** | Giá (giữ nguyên) |
|---|---|---|---|
| Nhỏ | 300 GB | **100 GB** | 149.000đ |
| Vừa | 600 GB | **150 GB** | 179.000đ |
| Lớn | 1000 GB | **250 GB** | 329.000đ |

Vượt hạn mức vẫn là **hãm tốc, không cắt, không tính thêm tiền** — câu đang
viết trên trang vẫn đúng sau khi hạ số.

### Hai lớp bảo vệ

1. **Theo khách** (đã có): `bao_tri.py` đọc counter nft theo IP nội bộ; vượt
   hạn mức riêng thì vào set `giam_toc`.
2. **Theo tổng** (mới): mỗi vòng bảo trì đọc `ens3` của cổng vào, cộng dồn
   bằng đúng `bang_thong.cong_don` (đã xử lý reset). Tháng-tới-giờ ≥ 80% của
   1.024 GB ⇒ hãm khách theo thứ tự dùng nhiều nhất trước, cho tới khi dự
   phóng cuối tháng lọt trần. **VM100–107 không bao giờ bị hãm.**

Lớp 2 phải vào `dieu_khoan.py`: *"khi tổng lưu lượng nền tảng chạm ngưỡng,
máy dùng nhiều nhất có thể bị hãm tốc trước khi chạm hạn mức riêng."*
Không viết vào là bán một thứ khác với thứ giao.

---

## Mục 5 — Quan sát

`tx_dropped` không còn chặn bán, nên nó phải **được nhìn**, không phải bị bỏ:

- `nguon_luc.so_nguon_luc()` trả cả sáu tài nguyên kèm % đã dùng → trang admin.
- Băng thông cổng vào tháng-tới-giờ và dự phóng cuối tháng hiện cạnh trần.
- `tx_dropped` giữ trong health ở tầng `CANH_BAO`, kèm bộ đếm tổng và tỉ lệ
  trên tổng gói TX (hiện 6.523.625 / 245.827.848 = 2,65% tích luỹ 27 ngày) để
  phân biệt cụm nhất thời với suy giảm thật.

## Không làm (YAGNI)

- Hàng đợi đặt hàng trước: quá lớn cho 5–15 máy.
- Kho IP mua sẵn: chủ dự án chọn mua theo yêu cầu.
- Nâng cổng vào lên VPS-3: để dành; ba con số băng thông đọc từ một hằng số
  nên nâng sau không phải sửa mã.
