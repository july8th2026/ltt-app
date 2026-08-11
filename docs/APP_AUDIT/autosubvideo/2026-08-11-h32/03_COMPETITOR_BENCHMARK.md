# H32.1 — Benchmark có chọn lọc

Chỉ lấy capability công bố trong tài liệu chính thức, không sao chép UI/brand.

| Nền tảng | Chuẩn tham chiếu hiện hành | Khoảng cách của AutoSub Video |
|---|---|---|
| Adobe Express | Chọn nguồn audio/video, ngôn ngữ; sửa transcript; style font/color/background/position; kéo caption trên canvas | AutoSub mạnh hơn ở multi-format/export, yếu hơn ở drag-position trực quan |
| Descript | Line height/alignment, gradient, border, active/future-word style, custom layout tái sử dụng, layer theo speaker | Thiếu line-height/alignment/gradient/layout reusable và style độc lập theo speaker |
| CapCut | Manual correction, split/re-segment, style/timing trên web/mobile | AutoSub có editor tương đương lõi nhưng mobile precision và partial re-recognize chưa đạt |

Nguồn chính thức:

- Adobe Express, “Generate captions in Adobe Express”, cập nhật 08-04-2026:
  https://helpx.adobe.com/express/web/create-and-customize-text/generate-captions-in-adobe-express.html
- Descript, “Add and style captions”:
  https://help.descript.com/hc/en-us/articles/37469585005197-Add-and-style-captions
- CapCut, “How Do I Fix Inaccurate Auto-Captions in CapCut?”:
  https://www.capcut.com/help/auto-captions-in-capcut

## Khuyến nghị chọn lọc

Ưu tiên tính năng giúp khách đạt kết quả, không biến app thành NLE tổng quát:
drag/safe-area, max-lines/caption width, alignment/line-height, reusable Brand
Preset, style theo speaker và re-transcribe đoạn lỗi. Không ưu tiên keyframe tự do,
stock media hoặc scene compositor trong app phụ đề.
