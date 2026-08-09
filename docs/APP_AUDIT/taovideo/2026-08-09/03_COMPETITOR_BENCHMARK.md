# 03 — Competitor Benchmark: Tạo Video Seedance

Snapshot 2026-08-09. Chỉ dùng tài liệu chính thức; không coi marketing claim là
blind evidence về chất lượng output.

## Competitor set

| Sản phẩm | Vai trò | Nguồn chính thức | Giới hạn evidence |
|---|---|---|---|
| Runway | Direct leader/creative suite | [Reference media](https://help.runwayml.com/hc/en-us/articles/52963720640275-Using-reference-media-to-guide-your-generations), [Edit Studio](https://help.runwayml.com/hc/en-us/articles/51683104370451-Creating-with-Edit-Studio) | E1 docs, không chạy plan trả phí |
| Google Flow/Veo | Direct leader/story workflow | [Model/feature matrix](https://support.google.com/flow/answer/16352836?hl=en), [Scenebuilder](https://support.google.com/flow/answer/16935718?hl=en) | E1 docs, capability tùy region/plan |
| Adobe Firefly Video | Direct/commercial workflow | [Generate video](https://helpx.adobe.com/firefly/web/work-with-audio-and-video/work-with-video/generate-videos-using-images.html), [Editor panels](https://helpx.adobe.com/firefly/web/firefly-video-editor/set-up-your-project/change-view-of-panels.html) | E1 docs, không xác thực commercial-safety claim |
| Luma Dream Machine | Direct innovator | [Modify guide](https://lumalabs.ai/learning-hub/ray3-modify-user-guide), [Keyframes](https://lumalabs.ai/learning-hub/how-to-use-keyframes) | E1 docs |
| Kling AI Video | Direct leader | [Video 3.0 guide](https://app.klingai.com/cn/quickstart/klingai-video-3-model-user-guide) | E1 docs; một số trang robots-blocked |
| Pika | Low-friction adjacent | [FAQ/features](https://pika.art/faq), [Pricing/capability](https://pika.art/pricing) | E1 docs; không chạy UI |
| BytePlus ModelArk | Provider truth | [Pricing](https://docs.byteplus.com/docs/ModelArk/1099320), [Seedance tutorial](https://docs.byteplus.com/api/docs/ModelArk/2291680), [Video API](https://docs.byteplus.com/en/docs/modelark/1520757) | E1 official; trang JS hạn chế trích xuất |

## Capability matrix

Điểm `0` không có/không chứng minh; `1` tối thiểu; `2` dùng được; `3` mạnh.

| Capability/JTBD | Loại | Trọng số | LTT | Runway | Flow | Firefly | Luma | Kling | Pika | Gap/quyết định |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Text/image→video cơ bản | TABLE_STAKES | 8 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | KEEP |
| Ảnh/video/audio reference + @handle | DIFFERENTIATOR | 8 | 3 | 3 | 3 | 2 | 3 | 3 | 2 | KEEP, làm lifecycle trực quan |
| First/last frame rõ ràng | TABLE_STAKES | 5 | 2 | 2 | 3 | 3 | 3 | 3 | 3 | FIX role/capability UX |
| Model/capability tự thích nghi | TABLE_STAKES | 6 | 3 | 3 | 3 | 3 | 2 | 3 | 2 | KEEP |
| Camera/motion/style customer controls | TABLE_STAKES | 6 | 2 | 2 | 2 | 3 | 2 | 3 | 2 | RESTYLE, không giả native param |
| Prompt enhance/translate/history | TABLE_STAKES | 5 | 2 | 2 | 3 | 3 | 2 | 2 | 1 | FIX preserve/i18n |
| Variants/seed/reuse settings | TABLE_STAKES | 5 | 2 | 3 | 3 | 3 | 3 | 3 | 2 | FIX recovery/idempotency |
| Live progress/cancel/retry | TABLE_STAKES | 7 | 1 | 3 | 3 | 3 | 3 | 3 | 2 | BUILD trong app |
| Assets/project/history/delete | TABLE_STAKES | 7 | 1 | 3 | 3 | 3 | 3 | 3 | 2 | BUILD lifecycle/pagination |
| Video-to-video edit/modify | TABLE_STAKES | 7 | 1 | 3 | 3 | 2 | 3 | 3 | 3 | Provider có thể hỗ trợ; UI chưa có |
| Extend video | TABLE_STAKES | 4 | 0 | 2 | 3 | 1 | 2 | 2 | 2 | DEFER sau core safety |
| Multi-shot/storyboard/scene builder | DIFFERENTIATOR | 7 | 0 | 2 | 3 | 3 | 1 | 3 | 1 | BUILD chọn lọc, không nhồi editor |
| Native audio/voice control | TABLE_STAKES | 6 | 2 | 3 | 3 | 2 | 1 | 3 | 1 | EXTEND theo provider capability |
| Handoff Upscale một bước | DIFFERENTIATOR | 6 | 3 | 2 | 1 | 2 | 1 | 1 | 1 | Lợi thế LTT, KEEP |
| Quote/hold/refund minh bạch | DIFFERENTIATOR | 7 | 2 | 2 | 3 | 2 | 2 | 3 | 2 | FIX settlement/quote mismatch |
| Customer-first responsive/a11y | TABLE_STAKES | 6 | 1 | 2 | 3 | 3 | 2 | 2 | 3 | FIX mobile/i18n/recovery |
| Nhiều engine/model dev-facing | ANTI_FEATURE | 0 | 0 | 2 | 2 | 2 | 1 | 2 | 1 | REJECT nếu làm người dùng rối |

## Kết luận thị trường

- **Market Score: 64/100.** LTT có độ phủ input/reference, model capability và
  cầu nối Upscale tốt; đây là nội tại đáng giữ.
- Khoảng cách lớn không nằm ở việc thêm hàng chục model. Nó nằm ở workflow sau
  generate: project/asset lifecycle, edit/extend, scene assembly, retry/cancel,
  lịch sử và khả năng khôi phục input.
- BytePlus mô tả Seedance 2.0 series hỗ trợ multimodal generation, editing và
  extension; UI hiện tại mới khai thác phần generation. Đây là capability gap,
  không phải lý do mở ngay tính năng trước khi G2/G3/G5 pass.
- Google Flow công khai matrix theo model và cảnh báo khi feature không tương
  thích; LTT nên học cách giải thích constraint tại control, không chỉ lọc option
  âm thầm.
- Runway phân biệt reference tạm và saved/shared reference; Firefly cho xóa/sửa
  từng keyframe và lưu generation history. LTT hiện không có lifecycle tương tự.
- Kling 3.0 và Flow đã đưa multi-shot/scene builder thành creator workflow.
  Với MVP LTT, chỉ nên thêm shot plan/sequence sau khi generation đơn đã an toàn.

