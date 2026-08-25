# Bán VPS trên `app.lttstudios.com` — phân tích, khảo sát, và logic đã khoá

> Trạng thái: **LOGIC ĐÃ KHOÁ** sau bốn vòng hỏi đáp ngày 2026-08-22 (V1–V13).
> Còn hai thứ chặn: kiểu kho lưu trữ trong Proxmox (8.1) và dữ liệu cổng
> đang chạy sẵn (8.2). Chưa viết dòng code nào.
> Quyết định nền tảng: **Q103** trong `docs/QUYET_DINH_NEN_TANG.md`.
> Kế hoạch thi hành: **H39** trong `docs/KE_HOACH_TRIEN_KHAI.md`.

---

## 0. Kiểm chứng trước, kết luận sau

Mọi con số dưới đây là **đo thật trên cụm ngày 2026-08-22**, không phải trích tài liệu.

| Điều | Kết quả đo | Cách đo |
|---|---|---|
| Proxmox nằm ở đâu | **`192.168.2.168:8006`**, node `pve`, **Proxmox VE 9.2** | quét TCP 8006 toàn dải `192.168.2.0/24` → `<title>pve - Proxmox Virtual Environment</title>` |
| Proxmox chạy trên gì | **Một máy ảo VMware Workstation, nằm trên MÁY B**, `H:\PVE-Nested\VMware\PVE-NESTED-VMWARE\` | Nexus File API đọc `H:\` của node `f8b24d88…` |
| Cấu hình máy ảo đó | **32 vCPU** (16 core/socket), **RAM 45.056 MB = 44 GB**, nested virt bật (`vhv.enable=TRUE`), NIC **bridged** vmxnet3 (vì thế nó lấy IP LAN thật) | đọc `PVE-NESTED-VMWARE.vmx` |
| Ổ đĩa của Proxmox | `PVE-System.vmdk` **15,7 GB** + `PVE-Data.vmdk` **217,3 GB**, đều nằm trên ổ `H:` của máy B | liệt kê thư mục VM |
| Lần tắt gần nhất | **`cleanShutdown = "FALSE"`** — Proxmox lần trước **không được tắt sạch** | `.vmx` |
| Máy B đang làm gì | Windows, RTX 3090, ComfyUI giữ **17,4 / 24 GB VRAM**; cũng là máy chạy dự án video | Nexus `/metrics/gpu` |
| Đường ra Internet | **VNPT, AS45899, IPv4 công cộng `14.232.231.35`** (động), Hà Nội | `api.ipify.org` + `ip-api.com` |
| IPv6 | **KHÔNG CÓ** | `api6.ipify.org` không phân giải được |
| Thuê bao định kỳ trong nền tảng | **Chỉ một chỗ**: `platform_core/nexus/billing.py` (Q98) | `grep -rn "subscription\|recurring\|dinh_ky"` |
| Repo có gì về Proxmox chưa | **0 dòng** | `grep -rln "proxmox"` |

> ⚠️ **Việc phải làm ngay, không liên quan VPS:** `.vmx` chứa **mật khẩu VNC dạng
> chữ thường đọc được**. Ai đọc được ổ `H:` là vào được console Proxmox. Tôi
> **không** chép giá trị đó đi đâu (AGENTS §3). Đề nghị đổi nó, hoặc tắt hẳn
> `RemoteDisplay.vnc.enabled` — Proxmox đã có console riêng.

---

## 0.1 ĐO THẬT QUA API PROXMOX — 2026-08-22, và nó lật ngược mục 2

Token `vpsapp@pve!ltt` (chỉ đọc, privilege separation) đã chạy. `python tools/vps_doctor.py`:

| Thứ | Số thật | Điều tôi đã đoán sai trước đó |
|---|---|---|
| Kho `vmdata` | **LVM-thin**, **475 GB**, đã dùng 173,6 GB (36,5 %) | Tưởng 217 GB. `PVE-Data.vmdk` 217 GB là **phần đã cấp phát trên `H:`**, còn LVM bên trong đã là 475 GB |
| RAM node | **43,2 GB** tổng | Khớp (45.056 MB trừ overhead) |
| VM đang có | **8 máy của chủ nhà**, cam kết **35,9 GB RAM** và **640 GB đĩa** | **Tôi không hề tính tới.** Đây là lỗi thật trong `capacity.py`, đã sửa |
| Template | **2 bản Windows 10 đã có sẵn**: `WIN10-GOLD-SYSPREP` (9000), `WIN10-LTSC-GOLD` (9001) | Tưởng chưa có template nào |
| Kho `local` | 20,3 GB, đã dùng **70,8 %** | — |

### Kết luận không thể tránh: **node đang ĐẦY, bán được 0 máy**

```
RAM  43 GB tổng | chừa 5 GB cho Proxmox | 8 máy chủ nhà cam kết 35 GB  -> CÒN 2 GB
Đĩa 474 GB tổng | chừa 45 GB template   | 8 máy chủ nhà cam kết 640 GB -> CÒN 0 GB
     !! đĩa đang bán chồng 1,49x
```

Ba hệ quả:

1. **V11 và V13 không còn là tối ưu hoá — chúng là ĐIỀU KIỆN.** Chưa nới thì
   không bán được máy nào. Và ngay cả sau khi nới RAM lên 64 GB thì cũng chỉ còn
   `64 − 5 − 35 = 24 GB` ⇒ **6 máy** ở mức 4 GB, không phải 10–14.
2. **Cách diễn đạt "nới 217 → 600 GB" là sai.** Pool đã là 475 GB. Việc thật là
   nới **vượt 475 GB**, và trước đó `PVE-Data.vmdk` còn phải phình từ 217 lên
   ~475 GB trên `H:` khi khách dùng — tức là **~258 GB của 800 GB trống đã bị
   hứa trước rồi**.
3. **Đĩa đã bán chồng 1,49× TRƯỚC KHI app bán máy nào.** Đây chính là kịch bản
   `capacity.py` sinh ra để phòng: kho đầy thì **mọi VM cùng hỏng một lượt**,
   không chỉ máy gây đầy. 8 máy đó là của chủ nhà, nên rủi ro này đã tồn tại
   sẵn — app chỉ đang **làm nó hiện ra**, và từ chối làm nó tệ hơn.

### Lỗi thật trong `capacity.py`, chỉ lộ ra khi đo cụm thật

Bản đầu chỉ cộng phần **app tự bán**. Với một node đã có 8 máy chiếm 35,9/43,2 GB,
nó vẫn báo "còn 38 GB, bán tiếp đi" — bán tiếp ở đó là **bán chỗ của chính chủ
nhà**, và khách trả tiền cho một máy không bao giờ khởi động nổi.

Đã sửa: `capacity.cam_ket_tu_vm()` đọc `maxmem`/`maxdisk` của **mọi** VM trên
node từ Proxmox, còn CSDL của app chỉ bù thêm những máy đã bán mà job provision
**chưa kịp tạo VM** (đếm đúng một lần mỗi máy). Ba test chốt, gồm một test dựng
lại đúng trạng thái node ngày 2026-08-22 và đòi app **từ chối bán**.

### Tin tốt: hai template Windows 10 đã có sẵn

`WIN10-GOLD-SYSPREP` và `WIN10-LTSC-GOLD` — tức là phần khó nhất của P6
(sysprep + gold image) chủ sản phẩm đã làm rồi. Còn phải kiểm hai thứ trước khi
dùng: template có **Cloudbase-Init** cấu hình `metadata_services` sang **NoCloud**
chưa, và có gắn sẵn **ổ Cloud-Init** chưa. Thiếu một trong hai thì clone vẫn ra
máy chạy được, nhưng **tên máy và mật khẩu sẽ không được áp dụng** — hỏng im lặng.

---

## 1. Hình dạng thật của hạ tầng: ảo hoá LỒNG BA LỚP

```
Windows (MÁY B, RTX 3090, đang chạy ComfyUI + dự án video)
  └─ VMware Workstation
       └─ Proxmox VE 9.2   (32 vCPU ảo, 44 GB RAM, 233 GB đĩa trên H:)
            └─ VPS của khách   ← lớp thứ BA
```

Bốn hệ quả, không cái nào sửa được bằng code:

1. **Máy B tự khởi động lại vì Windows Update sau 01:00.** `CLAUDE.md` ghi rõ
   Active Hours 07:00→01:00, và việc này **đã xảy ra thật 22/08 lúc 01:29**
   (sự kiện `1074`, `MoUsoCoreWorker`). Với VPS đó là **toàn bộ khách mất máy
   cùng lúc**, và `cleanShutdown = "FALSE"` cho thấy Proxmox đã từng bị cắt đột
   ngột — đường ngắn nhất tới hỏng hệ thống tệp của khách.
2. **Máy B đồng thời chạy ComfyUI + video** (một lượt từng chạy 72,5 phút, ăn
   98,7 % VRAM). VPS khách sẽ tranh CPU, RAM và ổ `H:` với việc đó.
3. **Nested virt chậm nhất ở đúng chỗ khách cảm nhận**: I/O đĩa qua ba lớp hệ
   thống tệp chồng nhau. **Không được ghi "NVMe" trên trang bán.**
4. **Không RAID, không UPS, không backup ra máy khác.** Ổ `H:` chết = mất toàn bộ khách.

Chủ sản phẩm đã nghe đủ bốn điều này và **quyết định mở bán trên hiện trạng**
(Q103/D1, D5). Ghi lại ở đây để sau này không phải tranh luận lại, và để biết
quyết định đến từ đâu.

---

## 2. Trần công suất — sau khi nới đĩa và RAM (V11, V13)

Chủ sản phẩm chốt **nới `PVE-Data.vmdk` lên ~600 GB** (ổ `H:` còn ~800 GB trống) và
**nới RAM máy ảo Proxmox từ 44 GB lên 64 GB**. Điều đó đổi hẳn bài toán so với vòng
khảo sát đầu.

| Tài nguyên | Trước | **Sau khi nới** | Trừ hao | Bán được |
|---|---|---|---|---|
| vCPU | 32 | 32 | Proxmox ~2 | ~30, **bán chồng 3–4×** |
| RAM | 44 GB | **64 GB** | Proxmox + ARC ~5 GB | **~59 GB**, không bán chồng |
| Đĩa | 217 GB | **~600 GB** | template Win Server ~20 + Win 10/11 ~25 | **~555 GB** |

Yêu cầu tối thiểu của Microsoft, không thương lượng được:

| OS | RAM tối thiểu | Đĩa tối thiểu | Thực tế cần |
|---|---|---|---|
| Windows Server 2016 / 2022 **Core** (không giao diện) | 512 MB | 32 GB | **2 GB / 40 GB** |
| Windows Server 2016 / 2022 **Desktop Experience** | 2 GB | 32 GB | **4 GB / 50 GB** |
| Windows 10 LTSC 2021 | 2 GB | 32 GB | **4 GB / 50 GB** |

> ⛔ **Windows 11 KHÔNG bán — chốt 2026-08-24.** Nó đòi UEFI/OVMF + vTPM 2.0 +
> Secure Boot, tức một **nhánh cấu hình máy riêng** mà không bản nào khác đi qua.
> Một nhánh chỉ phục vụ một thứ là nhánh không lần chạy nào thử tới, và nó hỏng
> lặng lẽ. Nhánh đó đã gỡ khỏi `jobs.py`; danh mục dừng ở **Server 2016, Server
> 2022, Windows 10 LTSC**. Muốn mở lại thì dựng lại nhánh theo mục 11 rồi mới
> thêm mục vào `os_images.py` — thêm mục trước sẽ tạo ra máy BIOS thường và
> khách ngồi nhìn *"This PC can't run Windows 11"*.

Ghép lại:

| Nếu bán toàn gói | RAM cho phép | Đĩa cho phép | **Thực tế** |
|---|---|---|---|
| `vps-nho` — 2 GB / 40 GB | 29 máy | 13 máy | **13 máy** |
| `vps-vua` — 4 GB / 60 GB | 14 máy | 9 máy | **9 máy** |
| `vps-lon` — 8 GB / 80 GB | 7 máy | 6 máy | **6 máy** |

Bán hỗn hợp thực tế: **khoảng 10–14 máy**. **Trần doanh thu: ~2 – 2,5 triệu đ/tháng.**

> ✅ **Điều tốt nhất của việc nới đĩa, quan trọng hơn cả con số doanh thu:** ở cấu
> hình 217 GB, cách duy nhất bán được 6–8 máy là **bán chồng đĩa 2,5–3,5 lần** — và
> khi kho đầy thì **mọi VM cùng hỏng một lượt**. Với 555 GB, RAM và đĩa xấp xỉ cân
> nhau nên **cấp thật 1:1 được**, bỏ hẳn lớp rủi ro đó. `capacity.py` vẫn cần (chặn
> bán khi kho vượt 80 %), nhưng nó thành lưới an toàn chứ không còn là thứ duy nhất
> đứng giữa ta và hỏng dữ liệu hàng loạt.

⚠️ Đi kèm: nhiều khách hơn trên **cùng một ổ đĩa vật lý không RAID** nghĩa là một lần
ổ `H:` chết mất nhiều hơn. Nới đĩa làm tăng doanh thu **và** tăng thiệt hại cùng lúc.

### 2.1 Nới `PVE-Data.vmdk` — quy trình an toàn (V11)

Chủ sản phẩm chọn nới đĩa hiện có thay vì thêm đĩa thứ hai. Đường này gọn hơn về sau
nhưng **đụng thẳng vào dữ liệu đang chạy**, nên thứ tự dưới đây là bắt buộc:

1. **Kiểm snapshot — đã làm 2026-08-22: KHÔNG có snapshot nào đang mở.**
   `.vmsd` chỉ còn `snapshot.lastUID = "2"`, không có mục `snapshot0.*`. VMware
   **từ chối nới** đĩa còn snapshot, nên đây là điều kiện cửa.
2. **Tắt sạch máy ảo Proxmox từ BÊN TRONG** (`shutdown -h now` trong Proxmox), không
   bấm Power Off của VMware. Lần trước `.vmx` ghi `cleanShutdown = "FALSE"` — đừng lặp lại.
3. **Chép `PVE-System.vmdk` (15,7 GB) sang chỗ khác trước.** Nếu bước nới hỏng phân
   vùng, đây là thứ cứu được cấu hình Proxmox. `H:` còn ~800 GB nên chỗ có sẵn.
4. Nới: `vmware-vdiskmanager -x 600GB "PVE-Data.vmdk"` (đĩa là **một file duy nhất**,
   không tách `-s001`, nên lệnh này chạy được).
5. **Bật Proxmox lên rồi nới tiếp BÊN TRONG.** Đây là bước dễ sai nhất, và **cách làm
   phụ thuộc kiểu lưu trữ mà ta CHƯA biết**: LVM-thin thì `pvresize` + `lvextend`;
   ZFS thì `zpool online -e`. **Xác định kiểu lưu trữ là việc của P0** (`/nodes/pve/storage`).
6. Kiểm bằng `pvesm status` — kho phải hiện dung lượng mới.

### 2.2 Nới RAM lên 64 GB (V13)

Sửa `memsize = "65536"` trong `.vmx` khi máy ảo đã tắt (làm cùng lúc với bước 2–4 ở
trên, một lần tắt máy cho cả hai việc). Lấy thêm 20 GB từ 192 GB của máy B — đủ nhẹ
để không đụng ComfyUI và dự án video.

## 3. Logic đã khoá — quyết định của chủ sản phẩm

Ba vòng hỏi đáp ngày 2026-08-22. Cột cuối là ghi chú kỹ thuật của tôi, không phải
tranh luận lại.

| Mã | Vấn đề | **Đã chốt** | Hệ quả kỹ thuật |
|---|---|---|---|
| **V1** | Hạ tầng | **Mở bán bình thường trên hiện trạng** (nested VMware trên máy B) | Ghi "best effort, không SLA" trên trang bán. Trần công suất mục 2 phải cưỡng chế bằng code |
| **V2** | Chống máy B tự reboot | **Không làm gì, chấp nhận mất máy** | Không tắt Windows Update, không auto-start. Một lần reboot = mọi khách mất máy tới khi có người bật tay. **Nên ít nhất bật auto-start của guest trong Proxmox** — miễn phí, và nó cứu được nửa vấn đề |
| **V3** | Đường vào của khách | **NAT 1 IP + dải cổng.** Chưa bán IP riêng | Cần bảng `vps_port_map`; cần DDNS vì IP VNPT là IP động; trang bán phải nói rõ khách nhận `IP:port`, **không host được web/mail/game** |
| **V4** | Bản quyền Windows | **Cài như các nhà VPS giá rẻ VN đang làm** | Tôi đã nêu rõ: đây là Windows **không có giấy phép hosting** (SPLA là đường hợp lệ duy nhất). Rủi ro là **pháp lý và thương hiệu**, không phải kỹ thuật. Về thi hành: cần một cách kích hoạt (KMS host nội bộ hoặc tiêm key) — xem 6.2 |
| **V5** | Gốc tính giá | **Bỏ neo Vultr, neo vào đối thủ VN** | Xem mục 5 |
| **V6** | Bảng giá | **89.000đ / 179.000đ / 329.000đ** | ⚠️ Cấu hình đi kèm phải sửa lại cho chạy được Windows — xem 5.2 |
| **V7** | Bán cho ai | **Cả hai**: khách LTT hiện có + người mua VPS phổ thông | Một bảng giá chung, một giao diện chung |
| **V8** | Hết credit | **Treo ngay → xoá sau 7 ngày** | Ngày 0: shutdown, dữ liệu còn nguyên, vẫn nạp được. Ngày +7: xoá vĩnh viễn. Khắt khe là đúng vì đĩa là nút thắt |
| **V9** | Template OS | **Windows Server 2022 + Windows 10/11.** Không Linux | Đây là đường khó nhất (Cloudbase-Init + sysprep) và tốn đĩa nhất. Xem 6.1 |
| **V10** | Backup | **Snapshot tuần, giữ 1 bản, đẩy sang ổ KHÁC của máy B** | Không ăn vào 155 GB. Không cứu được nếu cả máy B hỏng — đã chấp nhận |
| **V11** | Mở 800 GB trống của ổ `H:` | **Nới `PVE-Data.vmdk` hiện có** (217 GB → ~600 GB), không thêm đĩa thứ hai | Phải tắt sạch máy ảo, chép `PVE-System.vmdk` ra trước, và nới tiếp bên trong Proxmox. Quy trình ở 2.1 |
| **V12** | Cổng vào — nhiều lựa chọn cho khách | **Khách tự chọn khi tạo máy: IP Việt Nam · IP Singapore · hoặc chỉ cổng (port)**. Chuỗi cổng xây sau; **trước mắt lấy dải IP/cổng đang chạy sẵn làm gốc** | Thay `vps_port_map` đơn lẻ bằng **`vps_gateway` nhiều bản ghi** + chọn vùng lúc tạo. Xem mục 4 |
| **V13** | RAM của máy ảo Proxmox | **Nới 44 GB → 64 GB** | Sửa `memsize = "65536"` trong `.vmx`. Lấy 20 GB từ 192 GB của máy B — không đụng ComfyUI/video |

### 3.1 Một đề nghị kỹ thuật, không phải câu hỏi

**Nên dựng thêm một template Ubuntu 24.04 dùng NỘI BỘ, không bán.**
Lý do thuần kỹ thuật: pha P1 phải chứng minh cả chuỗi *trang web → job → clone →
cấp cổng → khách vào được*. Làm việc đó bằng Linux + `cloud-init` mất ~30 giây mỗi
lần thử và tất định. Làm bằng Windows + sysprep mất 10–20 phút mỗi lần và có bốn
cái bẫy (6.1). Dựng chuỗi bằng Ubuntu trước rồi mới cắm Windows vào **tiết kiệm
vài ngày** và tách được "lỗi ở đường ống" khỏi "lỗi ở template Windows".

Giá phải trả: ~5 GB đĩa, và `public=False` cho gói đó nên khách không thấy.
Tôi sẽ làm theo cách này trừ khi anh nói không.

---

## 4. Thiết kế đường vào — nhiều cổng, khách tự chọn (V12)

V3 (NAT một IP) được **V12 mở rộng**: khách chọn ngay lúc tạo máy — **IP Việt Nam**,
**IP Singapore**, hay **chỉ cổng**. Trước mắt lấy **dải IP/cổng đang chạy sẵn** làm
gốc; chuỗi cổng nhiều tầng xây sau.

```
Khách chọn "IP Việt Nam"   -->  gateway VN   (IP VN, độ trễ ~5-20 ms)
Khách chọn "IP Singapore"  -->  gateway SGP  (Vultr, độ trễ +~90 ms khứ hồi cho khách VN)
Khách chọn "chỉ cổng"      -->  gateway mặc định, cấp một cổng trong dải chung
                                   |
                          WireGuard về nhà
                                   |
                    Proxmox pve (192.168.2.168)
                       SDN: mỗi khách một VNet + SNAT
                                   |
                        VPS của khách  10.10.<id>.2:3389
```

### 4.1 Mô hình dữ liệu

Không hardcode một cổng duy nhất — đó là thứ phải sửa lại ngay khi thêm vùng thứ hai.

```
vps_gateway     id · ten · vung (vn|sgp|...) · ip_cong_khai · wg_endpoint ·
                cong_dau · cong_cuoi · cho_phep_ip_rieng (bool) · trang_thai · ghi_chu
vps_port_map    instance_id · gateway_id · cong_ngoai · cong_trong (3389) · giao_thuc
vps_ip          gateway_id · dia_chi · instance_id (null = còn trống) · gia_thang
```

Cấp cổng phải **nguyên tử**: hai job cùng lúc không được nhận cùng một cổng. Dùng
đúng khuôn `IntegrityError = người khác giành trước` của `platform_core/gpu_lease.py`,
đừng viết kiểu "đọc rồi ghi".

### 4.2 Bốn thứ phải làm, mỗi thứ là một chỗ hỏng thật

1. **DDNS.** IP VNPT ở nhà là IP động — nhưng với V12 thì **IP mà khách nối tới là IP
   của gateway** (tĩnh), nên vấn đề IP động **chuyển thành**: đường WireGuard từ
   gateway về nhà phải tự nối lại khi IP nhà đổi. WireGuard làm được nếu **nhà là bên
   chủ động gọi ra** và bật `PersistentKeepalive`. Vẫn nên cấp cho mỗi khách một tên
   `may-<id>.vps.lttstudios.com` trỏ tới IP gateway — để sau này đổi gateway mà khách
   không phải đổi gì. Bản ghi **DNS-only (mây xám)**, Cloudflare không proxy RDP.
2. **Băng thông là trần cứng dùng chung.** Đo thật 2026-08-22 trên đường nhà:
   **upload ~150 Mbps** (40 MB lên hết 1,8–2,3 giây, đo hai lần). 10–14 khách RDP thì
   thoải mái; **một** khách tải file lớn là nghẽn cả cụm ⇒ **bắt buộc giới hạn tốc độ
   mỗi VM ở tầng hypervisor**, không phải tuỳ chọn.
3. **Chặn cổng ra 25/587 ngay từ đầu.** Một khách spam là IP gateway vào blacklist.
4. **Cổng dự phòng.** Nhà cung cấp gateway đình chỉ nhanh và tự động; một khách xấu là
   **mọi khách offline cùng lúc**. Phải dựng sẵn một gateway thứ hai để đổi trong vài phút.

### 4.3 Chọn nhà cung cấp gateway — số đo thật

| | Độ trễ từ Hà Nội | IP phụ | API tự động | Giá |
|---|---|---|---|---|
| **Nhà cung cấp VN** (AZDIGI/Vietnix/Vinahost) | **~5–20 ms** | thường phải mở ticket | yếu | 79–157k/tháng |
| **Vultr Singapore** | **45 ms** (đo thật; khách VN chịu **~90 ms khứ hồi thêm**) | **tối đa 2 IPv4 phụ/instance**, $2/IP/tháng; Reserved IP $3/tháng | **đầy đủ** — `POST /v2/reserved-ips` + `/attach`, cắm thẳng vào job provision | $5/tháng (~130k) + IP |

> **Hệ quả cho giá bán:** gói "IP Singapore" nên **đắt hơn** gói "IP Việt Nam" về chi
> phí vốn ($3–5 so với ~0), nhưng **tệ hơn về trải nghiệm** cho khách VN. Trang bán
> phải nói rõ: *"IP Singapore hợp khi bạn cần địa chỉ nước ngoài; nếu bạn ở Việt Nam
> và chỉ cần máy chạy nhanh, chọn IP Việt Nam."* Không nói thì khách chọn Singapore
> vì nghe sang, rồi phàn nàn máy lag.

⚠️ **Chưa xác minh:** gắn được bao nhiêu Reserved IP vào **cùng một** instance Vultr —
tài liệu không nói. Phải thử thật trước khi hứa bán bao nhiêu IP Singapore.

### 4.4 Câu phải in trên trang bán

*"Máy của bạn dùng địa chỉ dạng `may-123.vps.lttstudios.com:31001`. Bạn chạy được phần
mềm, bot, công cụ. Nếu chọn gói có IP riêng, bạn nhận một địa chỉ IP dùng riêng ở vùng
đã chọn."* — Với gói chỉ-cổng, phải nói thêm: **không host được website hay mail server**.

## 4.5 CỔNG VÀO ĐÃ TỒN TẠI — dựng 12/08/2026, phát hiện 2026-08-22

Trên máy B có `setuppromox/KIEN-TRUC-GATEWAY.md`: một hệ thống gateway **đã chạy và
đã nghiệm thu**, và nó **đúng bằng phương án (B)** ở mục 4 — chỉ khác là chủ sản phẩm
đã làm xong từ mười ngày trước khi tôi đề xuất nó.

```
VM khách → vmbr1 10.50.0.0/24 (cô lập, bridge-ports none)
         → WireGuard UDP 51820 (PVE 10.50.255.2 ↔ Vultr 10.50.255.1)
         → Vultr 45.76.185.75 (Windows Server 2016)
         → WinNAT: SNAT 10.50.0.0/16 + DNAT 33891-33895 → 10.50.0.11-15:3389
```

### Dữ liệu để nạp `vps_gateway` — không còn phải hỏi

| Cột | Giá trị |
|---|---|
| `ip_cong_khai` | **45.76.185.75** |
| `vung` | Vultr (RTT từ trong guest **54–56 ms** ⇒ tuyến Singapore) |
| `wg_endpoint` | `45.76.185.75:51820` |
| `cong_dau`–`cong_cuoi` | 33891–33895 **đang dùng** cho VM100–104; mẫu `338xx`, còn rộng |
| `cho_phep_ip_rieng` | hiện **1 IP** duy nhất; Vultr cho thêm tối đa 2 IPv4/instance |

Thêm một máy vào gateway là **một lệnh có sẵn**, không phải việc phải viết mới:

```powershell
.\management\Add-GuestToGateway.ps1 -VmId 105 -LanIp 192.168.2.136 -GuestOctet 16 -RdpPort 33896
```

⇒ Job `vps.provision` (P1) chỉ cần **gọi lại script này**, thay vì tự dựng NAT.

### Ba con số đã đo thật, và chúng đổi vài giả định của tôi

- **Trần băng thông ~150–160 Mbps tổng.** Nút cổ chai là **CPU 1 vCPU của VPS Vultr**
  (đỉnh 83 % khi 5 VM chạy song song), **không phải** kiến trúc. Trùng khớp với upload
  đường nhà tôi đo (~150 Mbps) — nên dù đi đường nào, trần vẫn là ~150 Mbps chia cho
  **tất cả** khách. Nâng gói Vultr lên nhiều vCPU là cách gỡ.
- **RTT trong guest 54–56 ms.** Khớp với ước lượng "Vultr Singapore 45 ms + chặng về
  nhà" ở mục 4.3.
- **Tunnel chết ⇒ khách fail-closed**: mất Internet và DNS hoàn toàn, **không rơi về
  ISP**. Có `blackhole default metric 1000` làm sàn. Đã kiểm chứng bằng test thật.

### Điều làm biến mất một rủi ro tôi đã nêu

Mục 4.2 lo "IP nhà là IP động, đổi thì khách mất kết nối im lặng". Thiết kế này đã
giải: **PVE luôn là bên chủ động** (`PersistentKeepalive = 25`), Vultr học endpoint
mới từ handshake đến. Tài liệu ghi đã chứng kiến thật khi VPS reboot. ⇒ **Không cần
DDNS cho đường hầm.** DDNS chỉ còn hữu ích nếu muốn đổi nhà cung cấp gateway mà khách
không phải sửa gì.

### Hai điều cần biết trước khi dùng lại

1. **Chỉ VM100–VM104 nằm trên gateway.** VM105–107 thêm sau, chưa gắn.
2. **Tài liệu đó viết cho MÁY B CŨ** (`DESKTOP-30PHM9S`, `192.168.2.2`, RAM 27 GB).
   Máy B đã cài lại Windows và giờ là `192.168.2.66` với 43 GB cho Proxmox. Địa chỉ
   Proxmox `192.168.2.168` thì không đổi. Đọc phần RAM trong tài liệu đó như số cũ.

### ⚠️ Hai việc bảo mật thấy khi đọc

- `pve-root.cred`, `vps-admin.cred`, `windows-vm.cred` nằm trong thư mục
  `setuppromox/management/` **dưới OneDrive** — tức đang đồng bộ lên đám mây Microsoft.
  Mật khẩu root Proxmox và admin VPS nằm trong đó. **Không mở các file đó**
  (AGENTS §3); cần chuyển ra ngoài vùng OneDrive rồi xoay vòng mật khẩu.
- Chính tài liệu ghi **cổng 80/TCP mở** trên `45.76.185.75` với IIS `wwwroot` rỗng,
  kèm ghi chú "nên tắt nếu không dùng". Vẫn đang mở.

---

## 5. Bảng giá

### 5.1 Mặt bằng thị trường VN (khảo sát 22/08/2026)

| Nhà cung cấp | Cấu hình | Giá/tháng | Kèm gì |
|---|---|---|---|
| AZDIGI Pro VPS | 1 vCPU / 1 GB / 20 GB | 79.000đ (36 th) – 119.000đ (3 th) | SSD Enterprise **RAID-10**, backup tuần, **SLA 99,9%** |
| AZDIGI Pro VPS | 6 vCPU / 8 GB / 100 GB | 639.000đ (36 th) | như trên |
| Vietnix | gói thấp nhất | từ 157.000đ | |
| Vinahost | gói thấp nhất | từ 61.000đ | |
| VNPT Cloud | 1 vCPU / 2 GB / 30 GB | từ ~125.000đ | |
| Viettel IDC | 1 vCPU / 1 GB | từ 129.000đ | |
| FPT Cloud | 2 vCPU / 4 GB | từ ~300.000đ | |
| *(Vultr — chỉ tham chiếu)* | *2 vCPU / 4 GB / 80 GB / 3 TB* | *$20 ≈ 520.000đ* | *IP riêng, băng thông TB, SLA, datacenter thật* |

Đối thủ VN bán **rẻ hơn Vultr rất nhiều** và vẫn kèm RAID-10, backup tuần, SLA
99,9%. Hạ tầng của ta yếu hơn tất cả họ. Nên giá phải rẻ hơn rõ rệt **và** nói
thật về SLA.

### 5.2 Bảng giá đã chốt, cấu hình đã sửa cho chạy được Windows

Giá giữ nguyên theo V6. **Cấu hình phải sửa**: mức 89.000đ ban đầu ghi *1 vCPU /
2 GB / 25 GB* — với V9 (chỉ Windows) thì **25 GB không cài nổi Windows** (tối thiểu
của Microsoft là 32 GB, thực tế cần 40 GB). Đây là điều chỉnh bắt buộc, không phải
đổi ý về giá.

| Gói | vCPU | RAM | Đĩa | Chạy được OS nào | Giá/tháng | Credit |
|---|---|---|---|---|---|---|
| `vps-nho` | 1 | 2 GB | **40 GB** | Server 2016 / 2022 **Core** (không giao diện) | **149.000đ** | 1.490 |
| `vps-vua` | 2 | 4 GB | **60 GB** | **mọi bản trong danh mục** | **179.000đ** | 1.790 |
| `vps-lon` | 4 | 8 GB | **80 GB** | mọi bản — bán CPU/RAM, không mở thêm bản nào | **329.000đ** | 3.290 |
| *Đĩa thêm* | | | +10 GB | | **+25.000đ** | +250 |

Quy đổi **1 credit = 100đ** (Q31). Trần doanh thu nếu bán hết ~6–8 máy: **700k –
1,1 triệu đồng/tháng**.

**Ba dòng bắt buộc phải in trên trang bán:**
- *"Best effort — không cam kết uptime. Máy chủ có thể khởi động lại để bảo trì."*
- *"Bạn nhận địa chỉ dạng tên-miền:cổng, không phải IP riêng. Không host được website/mail."*
- *"Backup hằng tuần, giữ 1 bản. Dữ liệu quan trọng bạn nên tự sao lưu."*

---

## 6. Thi hành: bốn chỗ khó nhất

### 6.1 Template Windows — bốn cái bẫy cộng đồng đã ghi lại

Không cài từ ISO cho từng khách (10–30 phút, không tất định). Chuẩn: **template
một lần → clone → tiêm cấu hình lúc boot đầu**, bằng **Cloudbase-Init + Sysprep**.

1. Cloudbase-Init mặc định đọc metadata kiểu **ConfigDrive**, còn Proxmox sinh
   kiểu **NoCloud** → phải đổi `metadata_services` trong config. Không đổi thì
   cấu hình **im lặng không được áp dụng** — máy vẫn boot, chỉ là sai tên và sai IP.
2. Cài **VirtIO driver + QEMU guest agent** vào template **trước** khi sysprep.
3. **Không được khởi động lại VM sau khi chạy sysprep** — bật lên là hỏng template.
4. Gắn ổ Cloud-Init **trước khi** convert sang template.

> ⚠️ **Cả mục 6.1 này đã LỖI THỜI từ 2026-08-24** — mô hình template bị bỏ, khách
> **tự cài Windows** qua console và **tự đặt mật khẩu của chính họ**. Nền tảng
> không dựng template, không sysprep, không sinh mật khẩu, và **không biết mật
> khẩu của khách**. Giữ lại mục này vì nó ghi bốn cái bẫy của Cloudbase-Init, thứ
> sẽ cần lại nếu có ngày quay về mô hình dựng sẵn. Đường đang chạy: `os_images.py`
> + `jobs._cau_hinh_may_trong` + trang `/vps/<id>/cai-dat`.
>
> Phần Windows 11 (UEFI/OVMF + vTPM + Secure Boot) cũng bỏ theo — xem hộp ⛔ ở
> mục 4.

### 6.2 Kích hoạt Windows — hệ quả thi hành của V4

V4 chọn không mua SPLA. Về mặt kỹ thuật, máy chưa kích hoạt sẽ có hình mờ và một
số hạn chế cá nhân hoá. Hai đường thi hành, cần chọn khi tới P5:
- **KMS host nội bộ** — một máy trong LAN cấp kích hoạt 180 ngày, VM tự gia hạn.
- **Tiêm key lúc provision** — Cloudbase-Init đặt key rồi `slmgr /ato`.

Tôi ghi ra đây để khi tới P5 không phải dừng lại nghĩ. Rủi ro pháp lý đã được
chủ sản phẩm nhận, xem V4.

### 6.3 Bảo mật đường nối Proxmox

- **Không bao giờ mở cổng 8006 ra Internet.** Không cần: máy chủ nền tảng
  (`192.168.2.17`) và Proxmox (`192.168.2.168`) **cùng LAN**.
- **Không dùng `root@pam`.** Tạo user riêng + **API token bật privilege separation**,
  cấp quyền theo đường dẫn hẹp nhất (`/pool/khach`, role `PVEVMUser`). Quyền của
  token luôn là **tập con** quyền của user — hàng rào thứ hai.
- Token vào `secrets/app.env`, mã hoá bằng `platform_core/secretbox.py` nếu lưu DB.
  Không vào git (`tools/scan_source_secrets.py`).
- Khách **không bao giờ** thấy VMID, tên node, hay bất cứ thứ gì của Proxmox.
  Console qua proxy WebSocket của mình, vé `vncproxy` dùng-một-lần.

### 6.4 Chống lạm dụng

Bán VPS = bán **máy tính có cổng vào** cho người lạ. Trong tuần đầu sẽ gặp:

- **Đào coin** — ăn CPU của cỗ máy dùng chung với ComfyUI; tiền điện là của mình.
- **Spam / phishing** — IP `14.232.231.35` vào blacklist, kéo theo **cả đường VNPT
  ở nhà**, ảnh hưởng luôn `app.lttstudios.com`.
- **Nguồn DDoS** — VNPT cắt đường.
- **Nội dung vi phạm pháp luật VN** — trách nhiệm thuộc người vận hành hạ tầng.

Tối thiểu trước khi mở bán: **không cho dùng thử ẩn danh** (phải có thanh toán
thật), giới hạn CPU ở tầng hypervisor (`cpulimit`), cảnh báo khi CPU 100 % kéo
dài, và điều khoản cho phép **treo máy ngay lập tức**.

---

## 7. Chỗ đứng trong nền tảng

| Cần cho VPS | Đã có? | Ghi chú |
|---|---|---|
| Đăng nhập, tài khoản, credit, PayOS | ✅ | Q31, H9 — dùng lại nguyên |
| Hàng đợi job + worker | ✅ | **Bắt buộc dùng**: clone + sysprep mất vài phút, Cloudflare cắt request ở **100 giây** |
| Bảng CSDL riêng của app | ✅ | `table_prefix="vps"` + `apps/vps/tables.py` |
| Lease chống chạy trùng nhiều worker | ✅ | `platform_core/leases.py` — vòng thu phí và vòng đo đĩa phải nằm sau lease |
| **Thuê bao định kỳ** | ⚠️ | Chỉ `platform_core/nexus/billing.py` (Q98). VPS **theo đúng mẫu đó**, không dựng sổ tiền thứ hai |
| Driver Proxmox | ❌ | Dùng [`proxmoxer`](https://proxmoxer.github.io/docs/latest/) |
| Console noVNC | ❌ | Proxy WebSocket qua server mình |
| Cấp cổng NAT + DDNS | ❌ | Mục 4 |
| Đo đĩa + chặn bán khi đầy | ❌ | Mục 2 — **P3, không phải "làm sau"** |

```
apps/vps/
  manifest.py          slug="vps", table_prefix="vps", credit_cost=None (không tính theo job)
  routes.py            CHỈ HTTP: chọn gói, bấm tạo, bật/tắt, mở console
  jobs.py              vps.provision / vps.rebuild / vps.destroy  <- chạy trong worker
  services/
    proxmox.py         driver gọi API Proxmox (token, timeout, retry)
    provisioning.py    chọn node, cấp VMID, cấp cổng NAT, đặt quota
    lifecycle.py       treo / khôi phục / xoá theo trạng thái thanh toán
    billing.py         trừ credit theo chu kỳ 30 ngày — sao chép mẫu Q98
    capacity.py        đo đĩa/RAM còn trống, chặn bán khi vượt ngưỡng
  cost.py              bảng giá -> credit
  tables.py            vps_plan, vps_instance, vps_port_map, vps_event
```

Ba nguyên tắc không được vi phạm:

1. **Mọi thao tác tạo/xoá/rebuild đi qua hàng đợi job.** Không gì chạm Proxmox
   trong một request HTTP — trần 100 giây của Cloudflare sẽ cắt giữa chừng và để
   lại VM mồ côi.
2. **Mọi thao tác phải tự lành (idempotent).** Worker chết giữa lúc clone thì lần
   chạy lại không được tạo VM thứ hai. Khoá theo `job_id`, giống `credit.quyet_toan`.
3. **Sổ tiền chỉ có một.** Không có bảng `vps_invoice`. Chỉ `credit` + một cột
   "máy này đã trả tới ngày nào", đúng như `NexusDevice.paid_until`.

**Chỗ dự đoán phải bổ sung hợp đồng nền tảng:** *"việc nền định kỳ do app khai"* —
hiện app không có đường đăng ký một việc chạy mỗi giờ; Nexus đi vòng bằng cách
sống trong `platform_core/`. Đó là **thiếu sót của hợp đồng**; nếu làm VPS thì nên
vá đúng chỗ đó thay vì đi vòng lần thứ hai (AGENTS §2.3).

---

### 7.1 Biến môi trường phải đặt trong `secrets/app.env`

App **fail-closed**: thiếu bất cứ dòng nào ở nhóm bắt buộc thì trang trả 404 hoặc
từ chối tạo máy kèm lý do, chứ không chạy nửa vời.

| Biến | Bắt buộc | Ý nghĩa |
|---|---|---|
| `LTT_VPS` | ✅ | `1` để bật app. **Thiếu = app không tồn tại** (không catalog, URL trả 404) |
| `LTT_VPS_PROXMOX_URL` | ✅ | `https://192.168.2.168:8006` |
| `LTT_VPS_PROXMOX_TOKEN_ID` | ✅ | dạng `user@realm!tenToken`, vd `vpsapp@pve!ltt`. Sai dạng bị bắt ngay lúc đọc cấu hình |
| `LTT_VPS_PROXMOX_TOKEN_SECRET` | ✅ | bí mật của token. **Không bao giờ vào git** |
| `LTT_VPS_PROXMOX_NODE` | — | mặc định `pve` |
| `LTT_VPS_PROXMOX_CA` | — | đường dẫn CA để ghim TLS. Thiếu thì bỏ qua xác minh **và ghi cảnh báo một lần** (đường gọi là LAN nội bộ) |
| `LTT_VPS_ISO_WINSRV2022_CORE` | P5 | volid đĩa cài, vd `vmdata:iso/winsrv2022.iso` |
| `LTT_VPS_ISO_WINSRV2022_GUI` | P5 | volid đĩa cài |
| `LTT_VPS_ISO_WIN10` | P6 | volid đĩa cài |
| `LTT_VPS_ISO_WIN11` | P6 | volid đĩa cài (máy dựng kèm UEFI + vTPM) |
| `LTT_VPS_KHO_DIA` | — | kho chứa đĩa máy khách, mặc định `vmdata` |
| `LTT_VPS_TEMPLATE_UBUNTU_24_04` | — | **nội bộ, không bán.** VMID template Linux để thử đường ống trong ~40 giây |

> **Mô hình template đã bỏ ngày 2026-08-24.** Máy bán cho khách là **máy trống +
> đĩa cài**: khách tự cài Windows và tự đặt tài khoản của chính họ, nên nền tảng
> không bao giờ biết mật khẩu của khách và không phải bảo trì template nào.
>
> Đường nhân bản còn sống cho **bản `khach_thay=False`** và chỉ bản đó —
> `_template_noi_bo` trong `jobs.py` **từ chối** mọi bản bán cho khách kể cả khi
> biến môi trường tương ứng được đặt. Đó là hàng rào, không phải quy ước: thiếu
> nó thì một biến gõ nhầm đưa mọi khách về chung một mật khẩu, lặng lẽ.
> Test chốt: `tests/test_295_vps_dinh_danh.py`.

Token Proxmox phải **bật privilege separation** và chỉ cấp quyền trên đường dẫn hẹp
nhất (`/pool/khach`, role `PVEVMUser`). Đừng dùng `root@pam`.

Ngoài ra, `vps_gateway` phải có **ít nhất một dòng** thì mới tạo được máy — không có
cổng vào nghĩa là VM chạy trên đĩa mà không ai vào được. Trang bán từ chối trước,
không tạo máy mồ côi (có test chốt).

---

## 8. Việc còn chặn

### 8.1 Kiểu lưu trữ bên trong Proxmox — chặn bước nới đĩa (2.1 bước 5)

`H:` còn ~800 GB trống (chủ sản phẩm xác nhận) nên **dung lượng không còn là câu hỏi**.
Câu hỏi còn lại là **kho `PVE-Data` bên trong Proxmox là LVM-thin hay ZFS** — hai kiểu
này nới bằng hai lệnh khác nhau, và làm nhầm là hỏng kho.

Cách cấp cho tôi, chọn một:
- **API token Proxmox chỉ-đọc** — tôi tự lấy `/nodes/pve/storage`, `/nodes/pve/status`,
  `/nodes/pve/disks/list`. Cách tôi muốn nhất, và P0 cần token đó dù sao;
- hoặc bật `command.run` cho credential Nexus trên máy B (hiện Nexus trả `403` cho mọi
  endpoint hệ thống của B — chỉ `files` và `gpu` được cấp);
- hoặc chạy hộ trong Proxmox: `pvesm status` và `lsblk -f`.

Kèm theo, một câu về phần cứng: **`H:` là NVMe, SSD SATA, hay HDD?** Nếu là HDD thì
trang bán không được ghi "SSD", và RDP trên HDD lồng ba lớp là trải nghiệm rất tệ.

### 8.2 ~~Dữ liệu của cổng đang chạy sẵn~~ — ✅ ĐÃ TRẢ LỜI, xem mục 4.5

V12 chốt *"tạm thời lấy dải IP/cổng đang chạy làm gốc"*. Để nạp vào `vps_gateway` tôi
cần đúng bốn con số của cái cổng anh đang dùng cho các VM khác:

1. **IP công cộng** của cổng đó, và nó thuê ở đâu (nhà cung cấp, vùng).
2. **Dải cổng** đang dùng, và dải nào còn trống để cấp cho VPS khách.
3. **Cách chuyển tiếp hiện tại** — WireGuard? OpenVPN? `iptables DNAT` thẳng? SSH tunnel?
4. **Đường về nhà đang tới đâu** — về máy A (`192.168.2.17`), về router, hay về máy khác?

*(Việc kiểm router VNPT có forward được cả dải cổng không — **đã hết là vấn đề**. Với
V12, đường về nhà là **WireGuard do phía nhà chủ động gọi ra**, nên **không cần mở cổng
nào trên router VNPT**. Đây là cái được thứ hai của V12, sau việc chuyển vùng sát
thương của lạm dụng ra khỏi đường nhà.)*

### 8.3 Pháp lý — không phải việc của tôi

Có cần đăng ký kinh doanh / thủ tục gì ở VN để bán dịch vụ này không, và có xuất hoá
đơn không. Tôi **không biết** và không nên đoán; cần hỏi kế toán/luật. Nó ảnh hưởng
tới code (hoá đơn).

---

## 9. Thứ tự làm

| Pha | Việc | Chứng minh xong bằng gì |
|---|---|---|
| **P0a** | Lấy API token Proxmox privilege-separated; xác định kiểu kho lưu trữ (8.1) | `pvesm status` đọc được từ máy A qua LAN |
| **P0b** | **Một lần tắt máy, làm cả hai việc**: nới `PVE-Data.vmdk` 217→600 GB (quy trình 2.1) **và** `memsize` 44→64 GB (2.2) | `pvesm status` hiện ~600 GB; Proxmox báo 64 GB RAM; **đã chép `PVE-System.vmdk` ra trước** |
| **P0c** | ✅ **XONG 2026-08-22** — `apps/vps/` đầy đủ: manifest, 5 bảng, driver Proxmox, xếp chỗ, cấp phát nguyên tử, thu phí chu kỳ, trang bán, migration | 48 test xanh (`test_251` 39 + `test_252` 9); registry nạp app + bảng + 3 job type; lint hợp đồng app 0 ERROR |
| **P1** | Template **Ubuntu 24.04 dùng NỘI BỘ** (`public=False`, không bán) + job `vps.provision` + `vps_gateway`/`vps_port_map` nạp từ cổng đang chạy (8.2) + cấp cổng nguyên tử | **SSH thật vào được** `may-<id>.vps.lttstudios.com:31001` **từ ngoài mạng** |
| **P2** | Vòng đời bật/tắt/khởi động lại/rebuild/xoá + console noVNC (proxy WebSocket qua server mình, vé `vncproxy` dùng-một-lần) | Test tự động + kiểm trên **URL công khai** (CLAUDE.md quy tắc 5b) |
| **P3** | Tiền: 3 gói, trừ credit 30 ngày **sau lease** (khuôn Q98), treo ngay → xoá +7 ngày (V8), `capacity.py` chặn bán ở 80 % | Test đa tiến trình giống `test_214`; diễn tập một máy đi hết vòng hết-hạn → treo → xoá |
| **P4** | Chống lạm dụng: `cpulimit`, **giới hạn tốc độ mạng mỗi VM**, chặn cổng ra 25/587, cảnh báo CPU 100 %, nút treo khẩn cấp, không cho dùng thử ẩn danh | Diễn tập treo một máy chạy tải 100 % |
| **P5** | Template **Windows Server 2022** (Cloudbase-Init + sysprep, 6.1) + cách kích hoạt (6.2) | Clone ra máy mới, **RDP vào được**, mật khẩu ngẫu nhiên hiện đúng một lần |
| **P6** | Template **Windows 10/11** (UEFI/OVMF + vTPM + Secure Boot) | Như P5 |
| **P7** | **Cổng thứ hai** (vùng còn lại theo V12) + chọn vùng trên giao diện + gateway dự phòng | Tạo được máy ở cả hai vùng từ trang web; đổi gateway không phải sửa code |
| **P8** | Backup snapshot tuần, 1 bản, sang ổ khác của máy B (V10) | **Khôi phục thật một VM từ backup** |
| **P9** | Trang bán + ba dòng cảnh báo bắt buộc (5.2) + câu giải thích chọn vùng (4.4) + điều khoản sử dụng | Kiểm bằng trình duyệt trên `https://app.lttstudios.com/vps` |

**Khối lượng thật:** đây không phải "thêm một app". Đây là một **dòng sản phẩm có cam
kết vận hành**, ngang quy mô LTT Nexus, và nặng hơn về hậu quả khi hỏng (mất dữ liệu
của khách).

---

## 10. Khảo sát cộng đồng — cái gì dùng lại được

Không dự án nào cắm thẳng vào được: tất cả đều mang **sổ tiền + cổng thanh toán
riêng**, thứ mình đã có (credit + PayOS) và không được phép có hai cái.

| Dự án | Là gì | Dùng được gì | Vì sao không lấy nguyên |
|---|---|---|---|
| [proxmox-cloudportal/cloud-platform](https://github.com/proxmox-cloudportal/cloud-platform) | Portal đa tenant cho PVE. **Python 3.12 + FastAPI + SQLAlchemy 2.0 + PostgreSQL 16** — trùng stack dự án này | **Tham chiếu tốt nhất**: mô hình quota, RBAC, vòng đời VM, cách gắn noVNC | Không có billing; ~25 sao; kéo theo K8s/Celery/RabbitMQ — ta đã có hàng đợi riêng |
| [The-Network-Crew/Proxmox-VE-for-WHMCS](https://github.com/The-Network-Crew/Proxmox-VE-for-WHMCS) | Module WHMCS, FOSS, chạy production nhiều năm | **Tham chiếu nghiệp vụ**: đúng thứ tự thao tác tạo/treo/xoá, cách map gói → cấu hình | PHP, dính WHMCS |
| [proxpanel/proxpanel](https://github.com/proxpanel/proxpanel) | Panel VPS generic (Proxmox + libvirt) | Tham chiếu giao diện khách | Ít hoạt động |
| [Panelica/pnlcs](https://github.com/Panelica/pnlcs) | Thay WHMCS, Laravel 13, MIT | Tham chiếu luồng gia hạn | PHP + sổ tiền riêng |
| [Proxmoxrobo](https://github.com/pedrosantos867/Proxmoxrobo) | Billing + quản lý VPS | Tham chiếu | Như trên |
| VirtFusion / ProxCP / HostBill / ModulesGarden | Panel thương mại | — | Trả phí, không nhúng vào `app.lttstudios.com` |
| [`proxmoxer`](https://proxmoxer.github.io/docs/latest/) | Thư viện Python bọc API Proxmox | Đã đọc kỹ rồi **quyết định KHÔNG dùng** — xem 10.1 | Giấu mất timeout/retry/thông báo lỗi, và thêm một phụ thuộc phải ghim + phải cài thì test mới chạy, cho ~200 dòng ta muốn tự kiểm |

### 10.1 Vì sao driver tự viết thay vì `proxmoxer` (đổi ý so với bản nháp đầu)

Bản nháp ghi "cài `proxmoxer` làm driver". Sau khi đọc kỹ thì đổi, và ghi lý do ở
đây để không ai phải suy diễn:

* Proxmox là **REST/JSON thuần**, phần ta cần là ~10 endpoint. `proxmoxer` chủ yếu
  bọc chúng thành cú pháp thuộc tính — tiện khi gõ tay, nhưng **giấu mất đúng ba
  thứ phải kiểm soát chặt ở đây**: timeout, có được thử lại hay không, và thông
  báo lỗi.
* Thứ hai là quan trọng nhất. **Clone một VM không idempotent**: thử lại một
  request đã tới nơi nhưng mất phản hồi sẽ tạo **hai** máy — một cái mồ côi, ăn
  đĩa trong cái kho vốn là nút thắt, và **không ai biết nó tồn tại** vì CSDL chỉ
  ghi một máy. `apps/vps/services/proxmox.py` vì thế **không tự thử lại bất cứ
  thứ gì**, kể cả `GET`; việc chạy lại là của hàng đợi job và nó phải hỏi thế
  giới thật trước.
* `requests` đã là phụ thuộc lõi. Thêm `proxmoxer` là thêm một thứ phải ghim
  phiên bản, phải cài trên máy chủ, và **phải có mặt thì bộ test mới chạy** — cho
  khoảng 200 dòng mà ta muốn tự kiểm.

Driver nhận một `session` tiêm được, nên toàn bộ tầng trên kiểm được **mà không
cần một cụm Proxmox thật** (`tests/test_251_vps_ha_tang.py`).

---

## Nguồn

- Vultr, bảng giá thật: `https://api.vultr.com/v2/plans` (API công khai, 22/08/2026)
- [Proxmox VE — Cloud-Init Support](https://pve.proxmox.com/wiki/Cloud-Init_Support)
- [Proxmox VE — User Management / API Tokens](https://pve.proxmox.com/wiki/User_Management)
- [Proxmox VE — Software-Defined Network](https://pve.proxmox.com/wiki/Software-Defined_Network)
- [proxmoxer — thư viện Python](https://proxmoxer.github.io/docs/latest/)
- [proxmox-cloudportal/cloud-platform](https://github.com/proxmox-cloudportal/cloud-platform)
- [The-Network-Crew/Proxmox-VE-for-WHMCS](https://github.com/The-Network-Crew/Proxmox-VE-for-WHMCS)
- [proxpanel/proxpanel](https://github.com/proxpanel/proxpanel) · [Panelica/pnlcs](https://github.com/Panelica/pnlcs) · [Proxmoxrobo](https://github.com/pedrosantos867/Proxmoxrobo)
- [SAMexpert — Microsoft SPLA Licensing Guide](https://samexpert.com/microsoft-spla/) · [Licensing Windows Server in SPLA and CSP Hosting](https://samexpert.com/microsoft-windows-server-spla-licensing/)
- [computingforgeeks — Windows Server 2025 template trên Proxmox VE](https://computingforgeeks.com/windows-server-template-proxmox/)
- [Proxmox forum — Windows cloud-init template (patch)](https://forum.proxmox.com/threads/how-to-create-windows-cloudinit-templates-on-proxmox-7-3-patch-included.123338/)
- Giá thị trường VN: [AZDIGI Pro VPS](https://azdigi.com/pro-vps) · [FPT Cloud](https://fptcloud.com/bang-gia-thue-vps/) · [Vietnix](https://vietnix.vn/vps/) · [VNPT Cloud](https://cloud.vnpt.vn/blog/bang-gia-thue-vps-308) · [Vinahost](https://vinahost.vn/en/cheap-vps-vietnam/)
