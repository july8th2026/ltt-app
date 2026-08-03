# 02 — Journey & Control Registry tổng hợp

## Journey chính

| Journey | Hiện trạng | Verdict |
|---|---|---|
| Khách tìm app → đăng nhập → quay lại app | return-to hoạt động; public catalog mobile overflow | PARTIAL |
| Đăng ký/xác thực/reset | route và form có thật; style xanh tách brand mới | LIVE, RESTYLE |
| Nạp credit → order → cập nhật số dư | PayOS contract/route có thật; UI chưa cùng Studio | LIVE, RESTYLE |
| Tạo job → xem tiến độ → tải artifact | dùng chung jobs/credit/storage, hoạt động production | LIVE |
| Chuyển giữa các app | header/shell và từ vựng thị giác thay đổi mạnh | PARTIAL |
| Dùng app trên mobile | không overflow ở app đã kiểm, nhưng target nhỏ/field thiếu label | PARTIAL |
| Website marketing → product → app | website repo chưa phải site đang live; URL mismatch/404 | BROKEN |

## Control findings theo họ

| ID | Bề mặt/control | Bằng chứng | Verdict | Hành động |
|---|---|---|---|---|
| C-001 | Public catalog ở 390 px | scrollWidth-clientWidth = 48 | BROKEN | PLAT-003 |
| C-002 | Global button/link mobile | đa số target <44 px | PARTIAL | DS-004 |
| C-003 | Field không accessible name | 1–8 field trên nhiều app | BROKEN | DS-004 + vé app |
| C-004 | Login/register/reset CTA | hoạt động, xanh dương | LIVE/RESTYLE | AUTH-001 |
| C-005 | Home disabled Community/placeholder nav | disabled thật, không giả hành vi | LIVE/DEFER | HOME-002 |
| C-006 | Tạo video file input | native browser control chỏi theme | LIVE/RESTYLE | TV-UI-002 |
| C-007 | Upscale AI Detail | ghi “nghiên cứu”, disabled thật | LIVE/DEFER | UP-FEAT-001 |
| C-008 | Auto Sub capability thiếu token | disabled/giải thích thật | LIVE | AS-OPS-001 |
| C-009 | Socialbot controls | nội bộ, route legacy, Q10 đóng băng | KEEP | Không sửa |
| C-010 | Website repo links trên domain live | nhiều `.html` 404 | BROKEN | WEB-001 |

## Quy tắc registry chi tiết khi triển khai

Mỗi vé app phải tạo inventory đầy đủ theo mẫu LTT-AQA trước khi sửa. Vé nền tảng
không được tự suy rằng mọi selector cùng nghĩa; component migration phải có map
old selector → new component và regression cho action/API/credit hiện hành.
