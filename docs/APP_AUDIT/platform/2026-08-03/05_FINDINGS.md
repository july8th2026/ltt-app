# 05 — Findings

| ID | Sev | Finding/root cause | Ảnh hưởng | Vé |
|---|---|---|---|---|
| F-001 | P1 | Website trong repo không phải website production; nhiều URL `.html` trả 404 | marketing/legal/support không đồng bộ, link contract không đáng tin | WEB-001..003 |
| F-002 | P1 | Token xanh chung và token đỏ local cùng tồn tại; base còn CSS inline override | đổi app làm người dùng có cảm giác sang sản phẩm khác | DS-001..003 |
| F-003 | P1 | Public catalog overflow 48 px ở 390; authenticated Home không overflow | khách mobile đầu tiên gặp lỗi trước đăng ký | PLAT-001 |
| F-004 | P1 | Touch target <44 px xuất hiện rộng; nhiều field thiếu accessible name | khó dùng mobile/keyboard/screen reader; G6 fail | DS-004 + vé app |
| F-005 | P1 | Public/login/register/billing dùng xanh; Home authenticated đỏ | brand bị đứt tại conversion/tiền | AUTH-001, BILL-001 |
| F-006 | P1 | App mới vẫn không chia sẻ cùng shell: Upscale khác Auto Sub/Tạo video/Home | credit/nav/help/state không ổn định | DS-002, PLAT-002 |
| F-007 | P2 | App cũ dùng form/card chung nhưng CSS inline nhiều, state/label khác nhau | khó nâng cấp và regression visual cao | APP-LEGACY series |
| F-008 | P2 | Agent mạnh về safe execution nhưng thiếu trigger/schedule/debug/replay/error branch | Market Score thấp hơn automation leaders | AG-FEAT series |
| F-009 | P2 | Upscale mới chỉ có Fast/Quality spatial upscale; AI Detail thật còn DEFER | thiếu denoise/deblur/stabilize/interpolation/HDR | UP-FEAT series |
| F-010 | P2 | Tạo video thiếu asset reuse/reference controls/remix/camera workflow | prompt-to-video đủ nhưng creative loop ngắn | TV-FEAT series |
| F-011 | P2 | Chat thiếu Project/file/search/export/branch | khó làm công việc dài hạn | CHAT-FEAT series |
| F-012 | P2 | Image/Thumbnail thiếu reference/edit/brand/variant compare | yếu so với creative suites | IMG/TH-FEAT series |
| F-013 | P2 | Clip/Kịch bản thiếu lớp editor/version/export/publish rõ | engine có giá trị nhưng workflow chưa khép kín | CLIP/SCRIPT series |
| F-014 | P3 | Emoji/icon/logo/typography khác nhau giữa shell và app | giảm polish, khó tạo nhận diện cao cấp | DS-005 |

## Root cause chung

Phát triển theo vertical slice từng app đã tối ưu tốc độ ra tính năng và giữ
contract backend, nhưng visual/product layer không có token + shell + control
contract bắt buộc. Mỗi ảnh tham khảo sinh một stylesheet riêng. Cách sửa đúng là
chuẩn hóa nền tảng trước rồi migrate tuần tự; không redesign đồng thời nhiều app.
