# Agent Canvas UX Reset — kết luận điều hành

Ngày audit: 2026-08-04. Phạm vi: production `app.lttstudios.com/agent/canvas`,
phiên PlenX đã đăng nhập do chủ sản phẩm cho phép, source LTT và tài liệu chính
thức của FLORA/React Flow/ComfyUI/Langflow/n8n. Không chạy generation trả phí.

## Kết luận

Đánh giá 3/10 của chủ sản phẩm là có cơ sở. Canvas hiện tại **đúng kỹ thuật nhưng
chưa đúng mô hình tư duy của người dùng sáng tạo**. Điểm UX/UI thực đo là
`28/100` (2,8/10); Quality tổng hợp còn `58/100` nhờ security, credit và runtime
mạnh. Bản hiện tại không đủ điều kiện trình làng rộng.

Các scorecard `Q87/Q93` trước đây không bị xóa, nhưng không còn là baseline phát
hành: chúng thiếu bằng chứng E4 từ người dùng thật và đã đánh đồng “có control +
test xanh” với “người mới hiểu và hoàn thành việc”. Baseline hiệu lực cho vòng
nâng cấp tiếp theo là hồ sơ UX Reset này.

## Bằng chứng production

- Đã bảo đảm một canary vai trò `user`, mở production Canvas bằng phiên riêng;
  không hiển thị credential/cookie và không duyệt job trả phí.
- Canvas tải sạch: console 0 error/warning; palette/workflow/preferences/runs,
  save và quote đều 200/201. Đây là bằng chứng runtime khỏe, không phải UX tốt.
- Ở 1280×720, Text node hiển thị khoảng 660×612 px; palette 280 px và composer
  760×256 px đồng thời che phần lớn vùng làm việc.
- Ở 1920×1080 sau Fit View, ba node khoảng 515×478 px mỗi node. Khi đang chọn
  node, Palette/composer/quick-connect có thể cùng tồn tại.
- Advanced preference làm palette “Thêm node” phơi khoảng 20 ToolSpec, gồm
  `asset.*`, `prompt_package`, `short_clips` và mô tả kỹ thuật. Simple mode chỉ
  còn Text/Image/Video nhưng thiếu Audio và vẫn diễn đạt theo “generator tool”.
- `image.generate` → hai Text node cho hai lựa chọn trùng nhau
  `text.generate · image_keys`; người dùng không biết box đích nào là box nào.
- Text→Image và Image→Text chạy được ở mức typed graph, nhưng ý nghĩa nằm trong
  tên cổng/schema và dropdown, không hiện thành ý định “Tạo ảnh từ mô tả” hoặc
  “Phân tích ảnh”.

## Bằng chứng PlenX

- Add menu nhóm `Content` và `Transformation`; Content bắt đầu từ Image, Batch
  Images, Video, Social Video, Text, Audio.
- Image/Video rỗng tự nói hành động `Upload` hoặc `Generate`; chọn Generate mới
  mở composer dưới Canvas với prompt, model, tỉ lệ, độ phân giải, server và giá.
- Chuột phải khoảng trống mở add menu tại con trỏ. Chuột phải node chỉ hiện
  `Run From Here`, `Copy`, `Delete` trong lần kiểm.
- Composer mang ngữ cảnh node đang chọn, không biến node thành form kỹ thuật.
- Workflow mua sẵn được hoàn nguyên về 13 node/13 connection sau kiểm thử; không
  để lại node audit và không tiêu credit.

## Phương án

| Phương án | Mô tả | Khả thi | UX đích | Rủi ro | Điểm |
|---|---|---:|---:|---:|---:|
| A | Vá CSS/đổi nhãn trên UI hiện tại | 5/5 | 2/5 | 4/5 | 56/100 |
| **B** | **Lớp trình bày 4 modality trên runtime typed hiện có** | **4/5** | **5/5** | **2/5** | **91/100** |
| C | Viết lại Canvas và runtime | 2/5 | 5/5 | 5/5 | 62/100 |

Chọn khuyến nghị B: giữ ledger, ownership, typed validation, quote/approval và
worker; thay domain model trước mặt khách hàng bằng Text/Image/Video/Audio cùng
ngữ pháp nối theo ý định. Không xây runtime thứ hai.

## Release gate

`BLOCKED FOR PUBLIC LAUNCH`. Chỉ mở lại gate khi P0–P7 trong roadmap hoàn tất,
5 user task có tỷ lệ thành công tối thiểu 80%, median time-to-first-valid-chain
không quá 120 giây và không ai phải nhìn tên tool/field nội bộ.
