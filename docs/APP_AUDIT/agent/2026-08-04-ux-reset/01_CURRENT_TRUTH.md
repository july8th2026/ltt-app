# Current Truth — cái gì đang có, giữ, ẩn và thay

## Inventory hành vi

| Vùng | Hiện trạng | Đánh giá | Hành động |
|---|---|---|---|
| Shell | Full viewport, rail 48 px, top bar | Nền tốt | Giữ, giảm CTA top bar |
| Palette | Simple 3 tool; Advanced khoảng 20 ToolSpec | IA dựa trên code | Thay bằng 4 modality + nhóm Transform |
| Text node | Manual text, Generate, nhận text/image[]/video | Runtime mạnh, trình bày khó hiểu | Giữ contract; đổi UI theo intent |
| Image node | Upload/Generate, preview, nhận text/image[] | Đúng hướng nhưng node/tool bị trộn | Hợp nhất thành Image block |
| Video node | Upload/Generate, nhận text/image/video/audio | Quá nhiều khả năng không giải thích | Hợp nhất thành Video block, mode theo input |
| Audio | Executor có thật nhưng bị ẩn khỏi simple | Core modality bị thiếu | Đưa vào core khi acceptance đủ |
| Asset nodes | Owner/provenance an toàn | Không phải mental model khách | Ẩn; asset là trạng thái của media block |
| Transform | Upscale/merge/extract có executor | Có giá trị nhưng lấn core | Secondary menu/context action |
| Ports | Typed, server validate | An toàn nhưng lộ field/type | Giữ nội bộ, đổi thành một `+` theo modality |
| Quick connect | Picker tương thích | Đích trùng nhãn, không theo ý định | Hiện label node + verb nghiệp vụ |
| Composer | Contextual bottom panel | Đúng hướng, quá cao và chồng nội dung | Thu gọn, một composer duy nhất |
| Inspector | Schema/model/dev controls | Cần cho power user | Ẩn dưới Advanced/Dev mode |
| Run | Header, footer, composer, context menu | Bốn điểm chạy gây mơ hồ | Chuẩn hóa Run node/Run from here/Run flow |
| Credit | Server quote + approval | Lợi thế LTT | Giữ tuyệt đối; giá hiện ngay CTA |
| Assistant | Có selection context | Chưa là đường chính | Để phase sau core UX |
| Pages/frame/layers/note/comment | Có | Hỗ trợ, không phải first-run | Secondary, không hiện trong onboarding đầu |

## Findings ưu tiên

| ID | Sev | Finding | Hậu quả |
|---|---:|---|---|
| UXR-01 | P0 | UI phản chiếu ToolSpec thay vì mục tiêu sáng tạo | Người dùng phải học kiến trúc nội bộ |
| UXR-02 | P0 | Asset và generator là hai node dù cùng một media concept | Không hiểu Upload/Generate là hai trạng thái của một box |
| UXR-03 | P0 | Kết nối nói bằng field/type, không nói bằng kết quả | Dây có chạy nhưng không thể dự đoán |
| UXR-04 | P0 | Nhiều surface cùng mở và chồng Canvas | Mất ngữ cảnh, cảm giác bí bách |
| UXR-05 | P1 | Node được scale quá lớn khi Fit View | Ba box đã chiếm gần hết chiều ngang |
| UXR-06 | P1 | Simple mode thiếu Audio | Mental model 4 modality không hoàn chỉnh |
| UXR-07 | P1 | Nhãn đích quick-connect trùng nhau | Có thể nối nhầm box |
| UXR-08 | P1 | Bốn cách Run/Báo giá chưa có thứ bậc | Không biết thao tác nào chạy phạm vi nào |
| UXR-09 | P1 | Không có guided happy path đầu tiên | Empty state chỉ bảo mở Palette |
| UXR-10 | P2 | Quote tự gọi nhiều lần khi cấu hình/selection đổi | Tăng churn và làm trạng thái khó hiểu |
| UXR-11 | P2 | Toolbar có icon AI/↗/Workspace/Layers sớm | Nhiễu trước khi người dùng tạo được kết quả |
| UXR-12 | P2 | Default theme trong quyết định cũ không khớp yêu cầu gần đen mới | Cần đổi quyết định đúng giao thức khi code |

## Không được phá

1. ToolSpec, executor, queue và worker vẫn là source of truth.
2. Typed compatibility vẫn tồn tại trong adapter; UI không được nối tùy tiện.
3. Quote, approval, credit hold/settle/refund vẫn server-authoritative.
4. Asset ownership/provenance vẫn kiểm ở backend dù node asset biến mất khỏi UX.
5. Snapshot/conflict/undo/redo, tenant isolation và secret boundary được giữ.
