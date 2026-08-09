# 03 — Competitor Benchmark: Tạo ảnh AI + Thumbnail

## Nguồn chính thức snapshot 2026-08-09

1. Adobe Firefly dùng style/structure references, strength, effects, color,
   lighting và camera; Style Kits lưu/khóa setting để tái sử dụng on-brand:
   https://helpx.adobe.com/uk/firefly/web/generate-images-with-text-to-image/customize-generated-images/reference-images-for-styling.html
   và https://helpx.adobe.com/uk/firefly/web/work-with-enterprise-features/collaborate-using-style-kits/style-kits-overview.html
2. Midjourney Web tổ chức upload library, image/style/omni reference, rerun,
   subtle/strong variation, reuse prompt/reference và trash/organize:
   https://docs.midjourney.com/hc/en-us/articles/33390732264589-Creating-on-Web
3. Gemini Image API phân biệt Flash/Lite/Pro về giá, độ phân giải và workload;
   model mới hỗ trợ nhiều reference và ratio hơn:
   https://ai.google.dev/gemini-api/docs/pricing và
   https://ai.google.dev/gemini-api/docs/generate-content/image-generation
4. YouTube Studio Test & Compare dùng tối đa 3 thumbnail và watch-time share;
   thumbnail chuẩn ưu tiên 16:9/high resolution:
   https://support.google.com/youtube/answer/13861714?hl=en và
   https://support.google.com/youtube/answer/72431

## Gap matrix

| Năng lực | Chuẩn tham chiếu | LTT hiện tại | Gap |
|---|---|---|---|
| Model/cost/resolution | capability + giá theo model/resolution | model có, resolution không lộ; Thumbnail flat price | Rất lớn |
| Reference control | role, multiple, strength, reusable library | 1–2 file cục bộ | Lớn |
| Editor | mask/canvas/generative fill/expand | semantic text edit, nói rõ không mask | Lớn nhưng có thể staged |
| Variation workflow | rerun/vary/reuse/organize/trash | edit/remix + compare cơ bản | Lớn |
| Asset lifecycle | library/search/folder/delete/retention | 12-card recent history | Rất lớn |
| Brand consistency | versioned/shared style kit | một form Brand Kit | Lớn |
| Thumbnail quality | text/safe-zone/policy/real A/B signal | technical pixels score | Rất lớn |
| Mobile simplicity | progressive controls/sticky action | 7 section dài | Trung bình-lớn |

## Kết luận

Không nên xây Photoshop clone. Ưu tiên financial/data safety, asset library và
progressive generation surface; sau đó thêm reference roles/strength, variation
và thumbnail quality checks. “Technical score” không được quảng bá như khả năng
dự đoán CTR/watch-time.
