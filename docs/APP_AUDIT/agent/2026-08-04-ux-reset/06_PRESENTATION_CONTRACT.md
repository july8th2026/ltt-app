# H21 Presentation Contract — creative-v1

## Ranh giới

`creative-v1` chỉ thay lớp trình bày. ToolSpec, Plan, validator, executor, hàng
đợi, credit, ownership và provenance vẫn là nguồn chân lý phía server.

## Bốn block khách hàng

| Block | ToolSpec tạo mặc định | Asset sau upload | Hành động chính |
|---|---|---|---|
| Văn bản | `text.generate` | Không có asset riêng | Viết trực tiếp / Tạo bằng AI |
| Hình ảnh | `image.generate` | `asset.image(s)` là state nội bộ | Upload / Tạo bằng AI |
| Video | `video.generate` | `asset.video` là state nội bộ | Upload / Tạo bằng AI |
| Âm thanh | `audio.generate` | `asset.audio` là state nội bộ | Upload / Tạo bằng AI |

Transform có executor thật nằm ở catalog nâng cao và menu intent tương thích.
`asset.*` không được tạo trực tiếp từ palette/context menu, nhưng node asset cũ
vẫn mở, render, nối và chạy theo ToolSpec hiện có.

## Migration

- Canvas document v1 tiếp tục được `normalizeCanvas()` nâng lên v2.
- Canvas v2 không đổi schema và không rewrite ToolSpec đã lưu.
- Preference H20 chưa có `presentation_version` được đọc như
  `creative-v1 + catalog simple`; không coi giá trị `advanced` mặc định cũ là
  lựa chọn có chủ ý của khách hàng.
- Khi người dùng tự bật nâng cao, preference được lưu cùng
  `presentation_version=creative-v1` và giữ qua reload.

## Rollback

Đặt `LTT_AGENT_CANVAS_PRESENTATION=legacy` rồi restart Web để trả data attribute
về renderer H20. Không cần migration ngược vì document/runtime không đổi. Khi
biến vắng hoặc giá trị khác `legacy`, chế độ hiệu lực là `creative`.

## Gate đã chứng minh

- Adapter unit test phủ 21/21 ToolSpec public và bốn canonical block.
- Backend test chứng minh cờ creative/legacy, palette có Audio primary và
  preference migration.
- Browser local 8118: fresh user chỉ thấy Văn bản/Hình ảnh/Video/Âm thanh,
  asset không lộ; console error 0, request API đều 200/201, overflow ngang 0.
