# H32.3 — Current truth: Tạo ảnh AI

## Bề mặt khách hàng

| Mode | Khả năng hiện có |
|---|---|
| Ảnh tổng quát | 4 model Gemini; generate/edit/inpaint mô tả/outpaint/style transfer; source/style reference; 5 tỉ lệ; 1–4 ảnh; history, error, compare, edit, open |
| YouTube Thumbnail | topic/title/subtitle; reference; Brand Kit; 6 text style; 11 image style; 9 trend; 4 model; 5 tỉ lệ; 5 ngôn ngữ; 1–4 ảnh; score kỹ thuật, compare, remix, open |

Hai mode dùng chung shell nhưng giữ app/job/manifest/storage/credit contract riêng.
Output và reference đều owner-scoped. General có polling history; Thumbnail chưa
có polling/cancel/retry tương đương.

## Contract tiền hiện tại

- General: 5/5/8/16 credit mỗi ảnh theo model.
- Thumbnail: 5 credit mỗi ảnh với mọi model.
- Cấu hình cùng Gemini 3 Pro vì vậy có giá khác giữa hai mode. Đây là finding
  P1, không tự đổi trong audit vì tác động doanh thu và quyết toán.

## Thay đổi H32.3

- Preview General nay hiện model và tổng credit dự kiến.
- Preview Thumbnail nay hiện model, số ảnh, tổng credit, reference và Brand Kit.
- Có regression test cho cả hai contract.

Không có thay đổi provider, pricing, production hay deploy trong phase này.
