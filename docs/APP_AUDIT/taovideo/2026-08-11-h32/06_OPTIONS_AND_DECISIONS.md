# H32.5 — Options & decisions

| Phương án | Giá trị | Rủi ro | Effort | Điểm | Kết luận |
|---|---:|---:|---:|---:|---|
| A. Sao chép ảnh 100%, dựng cả nút chưa có backend | 3 | 5 | 4 | 45 | REJECT |
| B. Visual parity trên chức năng thật + progressive disclosure | 5 | 2 | 2 | 91 | **CHỌN** |
| C. Chỉ đổi màu/spacing, giữ mọi hành vi | 2 | 2 | 1 | 64 | Không đủ |

## Logic đã khóa theo yêu cầu và LTT-AQA

- Ảnh là nguồn hierarchy/style, không là bằng chứng tính năng.
- Giữ global header của control plane; không giả Prompt Library, bulk delete,
  retry hoặc Settings cho user thường.
- Quote và CTA cùng một dock; request quote lỗi thì CTA không được bấm.
- Saved asset và creative guidance là secondary; collapsed mặc định.
- Mobile closed phải loại toàn bộ composer khỏi focus order.
- Không submit job/provider trong H32.5.

Khuyến nghị tiếp theo cho Seedance vẫn là `Repair → selective parity`, không
build-all. D2 cap charge, D9 audio, D10 asset lifecycle và D11 Remix trong hồ sơ
2026-08-09 vẫn là decision gate bắt buộc.
