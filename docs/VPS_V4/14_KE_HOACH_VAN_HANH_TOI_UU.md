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
| F6 | Hỏi phiên khác (đã gửi LTTCODE + Voice); chủ dự án bấm UAC chạy `D:\LTTSTUDIOSAPP-runtime\deploy-b1593e3c-wrapper.ps1`; `tools/nghiem_thu_deploy.py` ba chiều; `/health/version` | nghiệm thu 3 chiều | **CHỜ UAC** |
| F7 | E2E live qua `vps-v4-cdp.mjs`: chủ dự án đăng nhập Chrome thật; bước 1–2 (đã PASS 16/09 trên UI); **GO** trước "Tạo máy"; bước 3–9; cleanup giữ stopped | trình duyệt thật | |
| F8 | Cập nhật `05`/`08`/`09`/`10`, `NHAT_KY.md`; chấm điểm 3 chiều | — | |
| F9 | Đóng băng, **một** `python tools\gate.py`; gộp main theo `QUY_TRINH_WORKTREE.md` §5; retire worktree | L3 | |

Gate đầy đủ chỉ chạy ở F9. Giữa các phase chỉ chạy test tập trung của phần vừa
sửa, sau `python tools\cua_so_yen.py trang-thai`.

## 5. Bằng chứng E2E đã có (16/09)

- Chrome thật `C:\LTTBrowserProfiles\VPSV4Cdp`, cổng 9222; chủ dự án qua xác minh
  và đăng nhập; `navigator.webdriver=false`; `/vps` trả 200.
- Bước 1 (đọc): `/vps` hiển thị, tài khoản AK, 8.211 credit, chưa có máy.
- Bước 2: **PASS** — form `vps-tao` chỉ có `plan_id`, `os_id`, `ten`; không có
  trường provider/profile/gateway. Ảnh: `D:\LTTSTUDIOSAPP-runtime\e2e-shots\vps-page.png`.
