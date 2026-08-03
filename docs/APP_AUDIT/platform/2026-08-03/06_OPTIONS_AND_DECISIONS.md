# 06 — Options & Decisions

## Phương án

| Tiêu chí | A. Chỉ đổi màu | B. Redesign app trước | C. System-first tuần tự |
|---|---:|---:|---:|
| Nhất quán | 55 | 70 | 95 |
| Không phá chức năng | 85 | 60 | 88 |
| Time-to-value | 90 | 55 | 78 |
| Khả năng mở rộng | 45 | 62 | 94 |
| Bao phủ accessibility | 40 | 65 | 91 |
| Tổng /100 | 65 | 63 | **90** |

**Khóa phương án C:** xây contract LTT Carbon Red + shell/component/a11y trước;
sau đó migrate từng page/app hoàn chỉnh từ audit → code → browser → regression
→ commit → phase kế. Không mở hai app song song.

## Quyết định mặc định theo ủy quyền của Dev

| ID | Quyết định đã khóa | Hệ quả |
|---|---|---|
| D1 | LTT Carbon Red là style chuẩn | đổi token xanh toàn cục; giữ status semantic xanh/vàng/đỏ |
| D2 | Home/Upscale/Auto Sub là nguồn tham chiếu, không phải ba stylesheet chuẩn | chiết token/component; bỏ hardcode trùng khi migrate |
| D3 | Platform/Auth/Billing làm trước app | conversion và tiền không còn chỏi brand |
| D4 | App triển khai tuần tự | mỗi app có audit riêng, PASS rồi mới app kế |
| D5 | Không build toàn bộ gap thị trường | ưu tiên table stakes và differentiator có ROI/provider thật |
| D6 | Socialbot chỉ audit, không redesign | tuân Q10; shared shell chỉ thay nếu không đổi hành vi và được test |
| D7 | Production chỉ sau full gate mỗi release train | backup/rollback/canary/browser bắt buộc |

Không cần thêm câu hỏi xác nhận: người dùng đã yêu cầu Codex chọn khuyến nghị tối
ưu và triển khai tuần tự. Nếu phát sinh thay đổi tiền, provider mới có phí lớn,
dữ liệu hoặc ranh giới Q10/core thì vẫn phải dừng theo AGENTS.md.
