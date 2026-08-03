# 03 — Competitor Benchmark baseline

Snapshot 2026-08-03, nguồn chính thức. So theo JTBD, không sao chép hình ảnh/IP.

| Họ sản phẩm | Benchmark chính | Table stakes/capability nổi bật | Gap LTT đáng làm |
|---|---|---|---|
| Agent/Canvas | n8n, Make, Zapier | execution history/replay, retry từ dữ liệu cũ, error route, template, schedule, version recovery | debug/replay tốt hơn; trigger/schedule; template; error branch |
| Chat workspace | ChatGPT Projects | project context, file/source, instructions, memory, multi-tool, search/share | Project/file context, search/export, branch/version, tool UX |
| Video generation | Runway | image/video/audio reference, saved reference, camera/motion control, asset reuse | asset library thật, reference role, camera controls, variations/remix |
| Video upscale | Topaz Video | nhiều model, denoise, deblur, stabilization, frame interpolation, HDR, preview/preset | engine portfolio; quality diagnosis; preset/model recommendation |
| Auto caption | CapCut | ASR đa ngôn ngữ, timing/style edit, word captions, speaker detection tùy nền tảng | template/brand workflow, transcript QA, capability availability rõ |
| Image/thumbnail | Adobe Firefly/Canva class | style + structure reference, strength, edit/variation, brand consistency | reference/strength, edit/inpaint/outpaint, brand kit, variant compare |
| Short clip | OpusClip/CapCut class | transcript highlight, reframe, captions, brand template, edit/export | editor sau AI, rationale/score, template/brand, multi-platform output |

Nguồn:

- n8n executions/retry: https://docs.n8n.io/workflows/executions/all-executions/
- Make scenario/error/recovery: https://help.make.com/scenarios
- ChatGPT Projects: https://help.openai.com/en/articles/10169521-using-projects-in-chatgpt
- Runway references: https://help.runwayml.com/hc/en-us/articles/52963720640275-Using-reference-media-to-guide-your-generations
- Topaz Video: https://www.topazlabs.com/topaz-video
- CapCut captions: https://www.capcut.com/help/how-to-recognise-subtitles
- Adobe style reference: https://helpx.adobe.com/firefly/web/work-with-images/generate-images/reference-images-for-styling.html

## Baseline Market Score

| Bề mặt/app | M /100 | Khoảng trống chính |
|---|---:|---|
| Platform/commerce | 52 | onboarding, help, product discovery, website link |
| Agent/Canvas | 54 | trigger/schedule/debug/replay/template |
| Auto Sub | 68 | brand/template workflow và QA sâu |
| Upscale | 48 | mới chủ yếu spatial upscale; thiếu portfolio enhancement |
| Tạo video | 55 | asset/reference/camera/remix |
| Chat AI | 43 | project/file/search/branch/tool UX |
| Tạo clip ngắn | 50 | editor/rationale/brand/publishing workflow |
| Thumbnail | 44 | editor/brand/variant testing/reference |
| Tạo ảnh | 40 | reference/edit/inpaint/outpaint/version |
| Kịch bản | 46 | research/source/outline/version/export |

Market Score không yêu cầu build tất cả. Feature phải qua giá trị LTT, provider
economics, privacy, khả thi và Decision Gate; gap lớn nhưng tốn/rủi ro cao có thể
DEFER có chủ đích.
