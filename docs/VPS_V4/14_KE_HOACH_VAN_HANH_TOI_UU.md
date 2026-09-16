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
| Q125 | Mua IP OVH | Web job tự mua, không duyệt từng đơn; báo giá bất thường thì dừng |
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

- **Giỏ `f99ebe5c` sẽ hết hạn 16/09 18:54 (giờ máy) trước khi bản sửa lên
  production an toàn.** Không mua trên code đang có R2–R4 và không thể tạo máy
  vì R1. Sau deploy, job tự chuẩn bị giỏ mới (chưa thanh toán, miễn phí) và
  fingerprint được xác minh lại trước khi bật; không tái dùng giỏ hết hạn.
- Production đang chạy `d9a48535` (nhánh `codex/cli-compat-final-audit`, chứa VPS
  tới `8b63fccc`). `main` chưa có cả hai nhánh. Bản release sửa lỗi phải dựng từ
  dòng mã production đang chạy, không từ `main`, để không lùi code cli-compat.

## 4. Thứ tự triển khai (theo phụ thuộc)

| Phase | Việc | Kiểm | Trạng thái |
|---|---|---|---|
| F0 | Rà soát + plan này | — | XONG |
| F1 | R1: tách nhịp làm mới health khỏi nhịp bảo trì nặng; ngưỡng tươi theo nhịp đo được (2× chu kỳ) cho health và cho generation Máy B; bảo trì tự làm mới preflight profile ACTIVE; Scheduled Task đồng bộ bản sao Máy B | test tập trung `-n ≤ 6` | ĐANG LÀM |
| F2 | R2–R5, R7: khôi phục đơn qua `/me/order` theo đúng giỏ (tra GitHub/OVH trước), chặn checkout lần 2 theo claim giỏ, guard hoàn tiền, phân loại lỗi trước POST, rollback trước review | test tập trung | |
| F3 | R6: `ensure` từ chối IP protected (RC 5) + khẳng định mọi dòng protected còn trong bảng mới; cài lại helper sau deploy, đo SHA trước/sau | test shell tĩnh + lệnh `health` live | |
| F4 | R8–R10 | test tập trung | |
| F5 | Hỏi phiên cli-compat/phiên khác; dựng release độc lập từ `d9a48535` + commit sửa; `alembic heads` một head; build + secret scan | build_release | |
| F6 | Deploy theo `docs/16_CAP_NHAT_VA_DEPLOY.md` trong cửa sổ không có job LLM dài; `/health/version` đúng SHA | nghiệm thu 3 chiều | |
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
