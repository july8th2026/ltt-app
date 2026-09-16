# VPS V4 — Kế hoạch vận hành tối ưu (16/09/2026)

Tệp này thay thế thứ tự công việc còn lại của `05_IMPLEMENTATION_PLAN.md`
(P7–P9). Quy trình chung vẫn theo `docs/00_LTT_OPERATING_CONTRACT.md`; tệp này
không đẻ luật mới, chỉ sắp lại việc theo phụ thuộc và bằng chứng đo được.

## 1. Câu hỏi và trả lời của chủ dự án

### Đã khoá từ trước (không hỏi lại)

| Mã | Câu hỏi | Trả lời |
|---|---|---|
| D01 | VPS có public API? | Không — WEB ONLY |
| D02 | Giữ provider nào? | Cả OVH và Vultr |
| D03 | Profile nhận máy mới | `OVH-SGP-PROD` ACTIVE + default |
| D04 | Vai trò Vultr | STANDBY |
| D05 | Đổi default có chuyển máy cũ? | Không |
| D06 | Khách chọn provider/gateway? | Không — chỉ region/gói/OS |
| D07 | VM100–107 | Bảo vệ, không mutation |
| D08 | Windows đầu tiên | Máy trắng + ISO, cài tay |
| D09 | Chủ máy nghiệm thu | `akakenly.design@gmail.com` |
| D10 | Trần IP live | Tối đa 1 |
| C01 | Mở hợp đồng admin chung | Đồng ý (13/09) |
| Q124 | Va chạm nhãn quyết định khi gộp | Xử theo nội dung, không ours/theirs cả tệp |
| Q130 (Q125 trên nhánh VPS trước khi gộp) | Mua IP OVH | Web job tự mua, không duyệt từng đơn; báo giá bất thường thì dừng |
| Cleanup | Sau nghiệm thu | Giữ VM stopped, IP BOUND, không xoá |

### Trong phiên 16/09

| # | Câu hỏi / chỉ thị | Trả lời |
|---|---|---|
| 1 | Captcha ở `/login` | Chủ dự án tự qua. Cách đúng (ghi nhớ `kiem-gui-noi-vao-chrome-that`, 04/09): **Chrome thật + `--remote-debugging-port`**, Playwright chỉ nối qua CDP. Phiên trước để Playwright tự khởi chạy Chrome ⇒ captcha xoay vòng |
| 2 | Ai đăng nhập | Chủ dự án tự đăng nhập; agent không gõ mật khẩu |
| 3 | Có đưa 8 VPS đang chạy vào tài khoản này? | **Không** (D07). Nếu muốn là quyết định mới, hạng mục riêng |
| 4 | Có tạo 1 VPS test cho tài khoản này? | **Có** — tối đa 1 IP, 1 VM |
| 5 | Phạm vi quyền | Toàn quyền trên plan VPS V4; không đụng việc phiên khác; kiểm CPU trước lệnh nặng; tra GitHub/tài liệu trước khi tự suy; gom gate về cuối |
| 6 | Gộp vào main | Theo `docs/QUY_TRINH_WORKTREE.md`; đang chờ phiên LTTCODE commit 2 tệp docs chặn |

## 2. Rà soát lại việc đã làm — lỗi thật tìm được

Đọc lại code tại `e5b72562` (hai lượt rà độc lập, rồi tự đọc lại dòng code):

| ID | Mức | Chỗ | Lỗi | Hệ quả |
|---|---|---|---|---|
| R1 | **P1 chặn nghiệm thu** | `profiles.py:54,139`; `bao_tri.py` | Tạo máy đòi 6 health component `HEALTHY` và **≤ 300 s**; không vòng nào tự làm mới. Collector Máy B chạy **30 phút/lần** (`LTT-VM-Promox-v4/proxmox/06-HIEN-TRANG/CHANGE-JOURNAL.md:46`); bản sao production `C:\LTTPlatform\runtime\machine-b-ovh` ghi lần cuối 16/09 00:08 bằng tay, không có Scheduled Task | Mọi lượt "Tạo máy" bị từ chối "không nhận máy mới" — về cấu trúc gần như luôn luôn |
| R2 | P1 tiền | `ovh_ordering.py:128-137` | `recover_order` gọi `GET /order/cart/{id}/checkout` = **xem trước giá**, không phải tra đơn | Mất phản hồi sau checkout ⇒ không bao giờ khôi phục; job lỗi, hoàn tiền, trong khi OVH có thể vẫn giao IP |
| R3 | P1 tiền | `ovh_acquisition.py:118-129` | Rebuild tạo operation mới, dùng lại claim giỏ ⇒ có đường checkout giỏ **lần 2** | Rủi ro mua trùng |
| R4 | P1 tiền | `ovh_acquisition.py:113`; `bao_tri.py:_hoan_may_tao_hong` | Hoàn credit nhưng `paid_until` không lùi ⇒ guard "đã trả" vẫn qua | Có thể mua IP cho máy đã hoàn tiền |
| R5 | P1 | `ovh_acquisition.py:189` | Lỗi **trước** POST (preview timeout, giỏ hết hạn) cũng ghi "kết quả không rõ" | NEEDS_REVIEW giả, chặn cả instance |
| R6 | P0 khả dĩ | `tools/vps_gateway/ltt-gwnat.sh:109-148` | `ensure` không đối chiếu danh sách protected; dựng lại bảng từ `anh-xa-ip.txt` mà không khẳng định mọi dòng protected còn đó | Hôm nay hai tệp trùng SHA nên chưa nổ; lệch một lần là mất rule của VM100–107 |
| R7 | P2 | `ovh_acquisition.py:196-200` | Commit hỏng sau khi có `order_id` ⇒ `review()` trên session hỏng, mất `order_id` | Truy đơn thủ công |
| R8 | P2 | `inventory_sync.py:78-79` | IP `QUARANTINED` không mapping bị trả về `FREE` | IP mơ hồ bị bán lại |
| R9 | P2 | `profiles.py:121`; `preflight.py:131`; `admin_profiles.py:30` | Kích hoạt lại / preflight lỗi làm rơi `is_default` | Bước đổi default dễ kết thúc không có default |
| R10 | P2 | `provisioning.py:47` | Dải VMID 200–899 (D07) không được cưỡng chế, chỉ chặn 100–107 | |
| R11 | P2 | `routes.py:459`; migration | Gateway Vultr không được gắn profile ⇒ đổi default sang Vultr có thể chặn tạo | Ảnh hưởng bước E2E 8 (chỉ đổi default, không tạo — xác minh khi chạy) |
| R12 | P2 driver | `D:\LTTSTUDIOSAPP-runtime\vps-v4-e2e-drive.mjs` | Tự khởi chạy Chrome (nguyên nhân captcha); exit 3 không bao giờ tới (catch gọi exit 1 trước); rào "1 lần submit login" ghi trong đầu tệp nhưng **không có code**; `created_count` tăng SAU click | **Thay** bằng `vps-v4-cdp.mjs` (nối CDP, đánh dấu create TRƯỚC click, cần `e2e_GO.txt`) |

Hoãn có chủ đích (ghi nợ, không chặn MVP): journal cho stop/start/restart/destroy;
downgrade migration để lại dòng IP OVH; IP giao muộn sau timeout cần sync tay.

## 3. Hệ quả vận hành

- **Giỏ `f99ebe5c` hết hạn 16/09 18:54 (giờ máy).** Không mua trên code đang có
  R2–R4, và không tạo được máy vì R1. Nếu bản sửa lên production kịp trước hạn
  thì dùng chính giỏ đó. Nếu lỡ hạn: health `ip` tự CRITICAL (thiết kế chỉ mua
  qua giỏ đã chấp nhận, `public_ip.py:104-127`), nên phải chuẩn bị một giỏ mới
  chưa thanh toán rồi cập nhật `adopt_ip_cart_id` và fingerprint qua cấu hình
  admin có audit. Không tái dùng giỏ hết hạn, không tự tạo giỏ trong job.
- Production đang chạy `d9a48535` (nhánh `codex/cli-compat-final-audit`, chứa VPS
  tới `8b63fccc`). `main` chưa có cả hai nhánh. Bản release sửa lỗi phải dựng từ
  dòng mã production đang chạy, không từ `main`, để không lùi code cli-compat.

## 4. Thứ tự triển khai (theo phụ thuộc)

| Phase | Việc | Kiểm | Trạng thái |
|---|---|---|---|
| F0 | Rà soát + plan này | — | XONG |
| F1 | R1: ngưỡng tươi theo nhịp đo được; bảo trì làm mới health mỗi 10 phút, không hạ profile; script Scheduled Task đồng bộ Máy B (thử thật: bản sinh `09:06:29Z`, đo `09:08:53Z`) | 102 passed/5 skipped | **XONG** `030d51b5` |
| F2 | R2–R5, R7. Tra `ovh/order-cart-examples`: `GET /order/cart/{id}/checkout` là **dry-run quotation**; OVH không có liên kết giỏ → đơn ⇒ mất phản hồi = NEEDS_REVIEW trung thực, một lần mua cho mỗi máy, chặn máy lỗi/đã hoàn, lỗi trước POST trả claim, rollback trước review | 102 passed | **XONG** `448c162f` |
| F3 | R6: helper từ chối địa chỉ protected và mọi thay đổi làm rơi dòng protected. Test chạy helper thật dưới Git Bash; đối chứng bản cũ `e5b72562` trượt đúng 3 rào mới | 5 passed; đối chứng 3 failed | **XONG** `0e5adf0f`; cài lên gateway: **chờ chủ dự án** (auto mode chặn ghi máy từ xa) |
| F4 | R8, R10 (R9 gộp vào F1) | 93 passed | **XONG** `3a468834` |
| F5 | Release `codex/vps-v4-release-r1` = `d723c79d` (dòng production) + nhánh VPS; xung đột duy nhất ở `08_LIVE_ACCEPTANCE.md`, xử theo nội dung (Q130). VPS diện rộng trên cây gộp 819 passed/7 skipped; một Alembic head `f4a7c2d9e610`; repo release độc lập `release-b1593e3c-lf` sạch; build 4486 tệp/146,5 MB, SHA-256 `89aa2c41…b262`, secret scan 0 | build_release PASS | **XONG** `b1593e3c` |
| F6 | Phiên Voice "OK deploy"; kiểm chỉ đọc 0 job running/0 lease sống ngay trước khi bấm; helper gateway cài live (SHA `eb612fd8…`→`2e98dddd…`, mapping/protected giữ `5ebaf20b…`, ensure IP protected trả **RC 5** live); deploy 16:29–16:31 exit 0; `/health/version` = `b1593e3ce90e`, `/health/ready` 200; `nghiem_thu_deploy.py` **ĐẠT 0/0/0**, đường lùi `d9a48535`; worker 7 năng lực `['api','voice']` | nghiệm thu 3 chiều | **XONG** |
| F6b | Sau deploy, health tươi 13 s và profile **không bị hạ** (R1 chạy đúng) nhưng chưa bán được vì hai lỗi mới đo được: **R11** Scheduled Task đồng bộ Máy B rc=1 — script tính gốc repo bằng `..\..\..` nên bản chép ngoài repo từ chối mọi đích (sửa `e15530e4`, task rc=0); **R12** worker `LocalSystem` SSH tới gateway OVH rc=255 — `ltt_ovh_gateway` owner là người dùng, Win32-OpenSSH dưới SYSTEM báo "UNPROTECTED PRIVATE KEY… bad permissions"; các khoá chạy được (`ltt_pve`, `ltt_gateway`) owner `BUILTIN\Administrators` ⇒ đổi owner về Administrators, ACL giữ nguyên (Administrators + SYSTEM); SYSTEM xác thực được, helper `ok` rc=0. `network` DEGRADED do `wireguard.gateway.tx_dropped` delta 18 (0,01/s) từ collector — tín hiệu thật, không nới ngưỡng, chờ bản sinh kế | đo dưới SYSTEM | **XONG R11/R12; network chờ Máy B** |
| F7 | E2E live qua `vps-v4-cdp.mjs` (Chrome thật, chủ dự án đăng nhập). Bước 1–2 PASS. **Lượt 1** (GO, 16:54:16, Nhỏ + Server 2022 Core): trừ 1.490 credit, `VM_CREATE` hỏng — task PVE `qmcreate`: *volume 'local:iso/windows-server-2022-eval-en-us.iso' does not exist*; không có `OVH_IP_ACQUIRE` ⇒ **không tốn tiền OVH**; VM 203 không được tạo. **ISO:** kho chỉ còn Win10 LTSC + virtio (bản 2022 tải 23/08 đã mất khỏi `local`); nới `local` bằng thin pool `pve/data` rỗng (26→41 G, quy trình cộng đồng Proxmox), node tự tải từ CDN Microsoft, khớp byte: 2022 = 5.044.094.976, 2016 = 6.972.221.440. **Lượt 2** (17:23:45): trang từ chối "Đã hết chỗ" trước khi trừ tiền ⇒ **R14**. Chủ dự án: chỉ tạo **1** VPS và giữ lại để dùng | trình duyệt thật | **ĐANG LÀM** — chờ bảo trì hoàn tiền + xoá máy lỗi `f072f952` để trả suất IP |
| F7d | **VPS thật** (chủ dự án giữ để dùng): lượt 3 lúc 17:34:06, `d96b66f3` `v4-nghiem-thu-2`, VM 204, trừ 1.490 credit (lượt 1 đã hoàn 17:33:14, xoá 17:33:15). Checkout OVH đơn `22703620` USD 2,39, thanh toán `debtAccount`, **một** đơn. **R18** trạng thái đọc ngay sau checkout ⇒ NEEDS_REVIEW; khôi phục vận hành có 11 điều kiện đọc lại (đơn đã `delivered`) ⇒ IP `51.79.x.x` BOUND, mapping gwnat OBSERVED. **R19** `qmstart` "WARNINGS: 1" (e1000 bỏ qua mtu) bị coi là hỏng dù VM chạy (pve-common `RESTEnvironment.pm`: warnings ⇒ exitcode 0); khôi phục lần 2 ⇒ `tao_xong` 17:38:48, 7/7 bước journal OBSERVED. UI: "Đang chạy", IP, RDP, sao kê đúng. **R20** console đóng ngay — cầu WebSocket dùng kho CA hệ thống; đo bắt tay: mặc định FAIL, CA riêng + IP FAIL, CA riêng + tên `pve` OK TLSv1.3. **R21** tắt mềm VM chưa cài OS quá hạn ⇒ UI "Đã tắt" + chỉ nút "Bật" trong khi VM chạy; nút tắt cứng đã thiết kế nhưng chưa có route. Bước 6 (mạng trong máy) và bước 8 (đổi default) chờ Windows cài qua console sau khi deploy R20 | trình duyệt thật + đọc lại PVE/OVH/DB | R18–R21 code **XONG** (`48ba172e`, `e5e38edb`, `6f824652`, `e5838cba`); **r2 `7432c7de`** = r1 + R11/R14/R18/R19/R20, chờ gate chung Voice+r2; R21 vào r3 |
| F7b | **R13** health gateway chỉ đo một lần: một lượt hỏng thoáng (17:14, sau đó 5/5 HEALTHY dưới SYSTEM, 1,4–2,1 s) đóng bán 10 phút ⇒ thử lại có giới hạn trước khi ghi CRITICAL. **R14** admission đếm máy `loi` chưa từng mua IP là đang giữ suất IPv4 ⇒ một lượt tạo lỗi chặn mọi lượt bán (sửa `5b9d3d64`, 16 passed; chưa deploy vì phiên khác đang chạy gate đầy đủ) | test tập trung | R14 code **XONG**; R13 **CHƯA** |
| F7c | Gia hạn (rà `release-b1593e3c`): **R15 P0** máy `bi_treo` không có đường gia hạn lại khi nạp credit, trong khi Điều khoản hứa 7 ngày để nạp và dùng tiếp; **R16 P1** không có code nào điều khiển gia hạn/huỷ dịch vụ IP ở OVH — IP P1M tự gia hạn USD 2,39/tháng kể cả khi rỗi trong kho, không có đối soát IP rỗi; **R17 P2** `inventory_sync` ghi đè `billing_mode`/`provider_metadata` làm mất `order_id` | quyết định chủ sản phẩm cho R16 (trần IP rỗi, `deleteAtExpiration`) | **CHƯA** |
| F8 | Cập nhật `05`/`08`/`09`/`10`, `NHAT_KY.md`; chấm điểm 3 chiều | — | |
| F9 | Đóng băng, **một** `python tools\gate.py`; gộp main theo `QUY_TRINH_WORKTREE.md` §5; retire worktree | L3 | |

Gate đầy đủ chỉ chạy ở F9. Giữa các phase chỉ chạy test tập trung của phần vừa
sửa, sau `python tools\cua_so_yen.py trang-thai`.

## 6. Kế hoạch lại theo luật vận hành 17/09 (thay thứ tự F-phase ở §4)

Luật (`docs/00_LTT_OPERATING_CONTRACT.md` §4, tóm tắt ở `~/.claude/CLAUDE.md`):

```
TRONG PHIÊN   test nhắm cụm vừa sửa; cần gate thì CHỈ L1 (gate.py --doi) / L2 (--pham-vi <tp>)
L3            python tools\gate.py MỘT lần ở tổng kết phiên; một L3 mỗi nhánh
L3 ĐỎ         sửa tại chỗ -> chạy lại đúng phép đỏ -> khép gate.py --doi --tu <sha L3>
DEPLOY        bất cứ lúc nào việc xây dựng cần, khi có gate XANH trên đúng SHA deploy:
              giữa phiên L1 (gate.py --doi --tu <sha bản production đang chạy>) / L2;
              không bấm L3 để deploy; test nhắm một mình không đủ
GỘP main      main đi tiếp thì hoà + test nhắm (+ L1/L2); chính phiên gộp, deploy, báo
```

Deploy xuất `HEAD` của cây chính `D:\LTTSTUDIOSAPP` (`setup\deploy_nang_quyen.ps1`
qua `tools
ang_quyen.py`, gọi từ **PowerShell** — Git Bash lấy nhầm GNU tar);
bản production đang chạy phải là tổ tiên của SHA deploy.

### Đã xong (17/09)

| # | Việc | Bằng chứng |
|---|---|---|
| R1–R21 | sửa + test nhắm (R16 theo chốt giữ tối đa 1 IP rỗi) | test tập trung + đối chứng |
| G1–G2 | R16, tài liệu 05/08/09/10, NHAT_KY, memory | commit nhánh |
| G3 | hoà `main` 1df18b17, origin/main 40ac2848, ASV a0532a6c, prod 80319d0a, main 228f91cf (Voice V2, prod d5bd7b07), main 17759a7b; Q124 GitHub đổi số Q135; test VPS 1029/1030 | tổ tiên đã kiểm |
| G4 | L3 `d8b02cd7` ĐỎ (12 test + 2 bánh cóc) ⇒ sửa tại chỗ `5abe2ace`; khép `--doi --tu d8b02cd7` trên `de331f8a` **PASS** (test_1259 cần token Máy B trong env) | `test-results/gates/`, `D:\LTTSTUDIOSAPP-runtime\l3-vps-v4-doi2.log` |
| G5 | L2 xanh trên SHA deploy (`--doi --tu` bị gate từ chối vì delta chạm tệp dùng chung): `app:vps`, `app:auto_scan_video`, `cong_cu` PASS trên `ee5a5ef9`; ff `main` + `origin/main` | `test-results/gates/`, `l2-vps-v4-*.log` |
| G6 | Deploy `ee5a5ef9` 17/09 03:28 (0 job/0 lease, EXITCODE 0, 83 s); `nghiem_thu_deploy` 0 lệch/0 thiếu/0 thừa; `/health/ready` 200 loopback + công khai; env Voice giữ nguyên; task đồng bộ Máy B đăng ký lại, chạy rc 0 | `C:\LTTPlatform\logs\deploy-20260917-032810.ket.txt` |
| G7 | E2E live trên `d96b66f3` (Chrome thật qua CDP, chủ dự án đăng nhập): console **ĐẠT** (WS mở ≥30 s, thấy trình cài Windows Server, 0 lỗi console/request); bật trên VM đang chạy đồng bộ lại UI; khởi động lại + tắt mềm khi guest không nhận ACPI ⇒ PVE timeout, UI giữ **Đang chạy** khớp PVE, hiện nút Tắt cứng (R21 **ĐẠT**); tắt cứng có xác nhận ⇒ `qmstop` OK, UI Đã tắt; bật lại `WARNINGS: 1` coi là thành công (R19 **ĐẠT**) | `D:\LTTSTUDIOSAPP-runtime\e2e-shots\g7-*` |

### Phát hiện G7 và quyết định (17/09)

| # | Phát hiện | Xử lý |
|---|---|---|
| R22 | Tự mua IP chỉ bật khi có `adopt_ip_cart_id`; giỏ đã checkout ⇒ `404 Cart expired` ⇒ probe `OvhError` mỗi lượt, `ip`/`capacity` CRITICAL | **Chủ dự án chốt: tạm dừng bán VPS mới.** `provider_config.auto_acquire=false`, bỏ `adopt_ip_cart_id` (config v4, bản lùi ở runtime). Mở bán lại cần quyết định mua IP tự động + probe catalog `GET /order/catalog/formatted/ip` (chỉ đọc) |
| R23 | Collector Máy B coi mapping `LTTMANAGED` là thừa, đòi IP gateway = 8+1 ⇒ `network` CRITICAL sau máy bán đầu tiên | Chặn mở bán lại; bản chạy ở `H:\PROXMOX` không phải git — sửa theo cổng thay đổi Máy B |
| R24 | Trang `/vps` "còn chỗ" chỉ theo RAM/đĩa, lúc tạo mới kiểm IPv4/cổng | Sửa `75e1e0a5` + `test_1031` (đối chứng mã cũ 7 đỏ); chờ L2 + deploy |
| — | Đổi default OVH→Vultr→OVH | Không chạy live: tài khoản thử là khách (403 admin) và Vultr 0401 chưa từng có health; đã có test tự động giữ ghim profile |

### Còn lại

| # | Việc | Chặn bởi |
|---|---|---|
| G7b | Deploy R24 sau L2 `app:vps` trên SHA đã hoà `main`; kiểm `/vps` báo hết chỗ trên URL công khai | phiên Voice deploy xong |
| G7c | **NỢ — chủ dự án nhận 17/09, phiên này bỏ qua**: mạng trong máy (RDP `51.79.202.1:3389` từ Internet, egress đúng IP OVH, đường `10.50.0.x`) sau khi chủ dự án cài Windows qua console tài khoản sở hữu | chủ dự án |
| G8 | **Xong 17/09**: gỡ worktree `wt-vps-release`, xoá nhánh `codex/vps-v4-release-r1..r4`, xoá 6 clone/gói release của phiên. Worktree `D:\LTTSTUDIOSAPP-vps-v4` giữ tới khi R24 lên production | G7b |

Tiến độ phần mềm ≈ 95%. Mở bán lại cần R22 + R23. Sẵn sàng production đầy đủ vẫn
chặn bởi Backup V2 CAPACITY_BLOCKED, restore drill và dual-WAN chưa kiểm.

## 5. Bằng chứng E2E đã có (16/09)

- Chrome thật `C:\LTTBrowserProfiles\VPSV4Cdp`, cổng 9222; chủ dự án qua xác minh
  và đăng nhập; `navigator.webdriver=false`; `/vps` trả 200.
- Bước 1 (đọc): `/vps` hiển thị, tài khoản AK, 8.211 credit, chưa có máy.
- Bước 2: **PASS** — form `vps-tao` chỉ có `plan_id`, `os_id`, `ten`; không có
  trường provider/profile/gateway. Ảnh: `D:\LTTSTUDIOSAPP-runtime\e2e-shots\vps-page.png`.
