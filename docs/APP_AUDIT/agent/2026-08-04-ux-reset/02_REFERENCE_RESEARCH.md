# Reference research — nguyên tắc lấy, không sao chép giao diện

Chỉ dùng tài liệu chính thức và thao tác render thật. Không coi số lượng tính
năng của đối thủ là mục tiêu; chỉ lấy pattern giúp người dùng dự đoán hành vi.

## FLORA

- Canvas: double-click để tạo block; kéo tay nắm `+` để nối. Tài liệu minh họa
  trực tiếp Text→Image và Image→Video.
- Toolbar: action tạo block ban đầu chỉ Text/Image/Video; Assets và Generation
  History là vùng riêng, không phải node kỹ thuật ngang cấp.
- Node Overview: ba core creative unit; toolbar node chỉ xuất hiện theo ngữ cảnh.
- Text→Image: gõ prompt trực tiếp hoặc nối Text output để điền prompt.
- Image→Text và Video→Text: media nối vào Text có nghĩa phân tích/trích xuất.
- Text→Text: cho phép hợp nhất nhiều ý hoặc branch thành nhiều hướng.
- Images→Video: upload trong node hoặc nối ảnh; ảnh đã nối có thể reorder/delete.
- FAUNA: Assist mode mặc định cho xem node sẽ chạy và estimated credit trước
  khi duyệt; selection và `@node` cung cấp context; Plan mode không chạy.

Nguồn:

- https://docs.flora.ai/editor/canvas
- https://docs.flora.ai/editor/toolbar
- https://docs.flora.ai/blocks/editor
- https://docs.flora.ai/blocks/image-block/text-to-image
- https://docs.flora.ai/blocks/text-block/image-to-text
- https://docs.flora.ai/blocks/text-block/video-to-text
- https://docs.flora.ai/blocks/text-block/text-to-text
- https://docs.flora.ai/blocks/video-block/image-s-to-video
- https://docs.flora.ai/editor/fauna

## React Flow

LTT đã dùng React Flow nên không cần thư viện graph mới. Tài liệu chính thức có
sẵn pattern: add node khi thả edge ra khoảng trống, node toolbar không scale theo
zoom, edge toolbar/inline button, validation, prevent cycle và reconnect edge.
Đây là cơ sở kỹ thuật để đổi UX dây mà không viết runtime mới.

- https://reactflow.dev/examples
- https://reactflow.dev/examples/nodes/node-toolbar
- https://reactflow.dev/examples/edges/edge-toolbar
- https://reactflow.dev/learn/concepts/adding-interactivity
- https://reactflow.dev/learn/customization/handles

## ComfyUI, Langflow và n8n

- ComfyUI chứng minh màu/type link giúp debug và type safety, nhưng UI của nó là
  chuẩn power-user, không phải default cho khách sáng tạo phổ thông.
- Langflow tách workspace build và Playground test; cho chạy từng component để
  cô lập dependency. Pattern nên lấy là “test tại chỗ”, không lấy form dev dày.
- n8n cho map dữ liệu bằng tên node và drag-drop từ INPUT pane, tránh bắt người
  dùng viết expression. Với LTT, `@node` nên hiển thị nhãn người dùng và tự tạo
  edge typed ở dưới.

Nguồn:

- https://docs.comfy.org/development/core-concepts/links
- https://docs.comfy.org/interface/overview
- https://docs.langflow.org/concepts-overview
- https://docs.langflow.org/concepts-playground
- https://docs.n8n.io/data/data-mapping/data-mapping-ui/

## Tinh túy phải đưa vào LTT

1. Creative modality trước, executor/tool sau.
2. Box là nơi chứa nội dung và kết quả, không phải form cấu hình provider.
3. Một `+` tạo hành động kế tiếp tương thích theo ngôn ngữ con người.
4. Chỉ node được chọn có composer; advanced không chiếm Canvas mặc định.
5. Run độc lập, run từ đây và run flow có phạm vi/giá/trạng thái rõ.
6. Mọi generation có quote và confirm; không làm yếu safety để giống đối thủ.
