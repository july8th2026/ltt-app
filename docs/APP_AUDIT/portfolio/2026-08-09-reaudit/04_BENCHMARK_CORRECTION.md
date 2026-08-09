# A4 — Benchmark correction

Các nguồn dưới đây bổ sung bộ so sánh chính thức, snapshot 2026-08-09. Đây là
E1 docs, không phải hands-on và không chứng minh output quality.

| Phạm vi | Mẫu 5–7 sản phẩm/công cụ | Năng lực cần đối chiếu |
|---|---|---|
| Socialbot | Meta Business Suite, TikTok Studio, Buffer, Hootsuite, Later, Sprout Social, Metricool | role/approval, calendar, retry, analytics, multi-account |
| Demo/synthetic | Checkly, Grafana Synthetic Monitoring, Datadog Synthetics, New Relic Synthetics, Sentry monitoring | scheduled journey, browser/API checks, metrics/logs, alert |
| Kịch bản/Text runtime | FLORA, n8n, Make, Langflow, OpenAI structured output | literal/generate, typed input-output, stream/cancel, schema/fallback |
| Media runtime | FLORA, ComfyUI, Cloudinary, FFmpeg, n8n binary data, Make file modules | typed media, preview, transform, provenance, large-file lifecycle |

Nguồn chính thức tiêu biểu:

- https://www.hootsuite.com/platform
- https://sproutsocial.com/features/social-media-analytics/
- https://buffer.com/
- https://later.com/
- https://metricool.com/social-media-analytics-tool/
- https://docs.flora.ai/blocks/editor
- https://docs.flora.ai/nodes/video-node/text-to-video
- https://docs.comfy.org/development/core-concepts/workflow
- https://www.checklyhq.com/docs/detect/synthetic-monitoring/playwright-checks/overview/
- https://grafana.com/docs/grafana-cloud/testing/synthetic-monitoring/introduction/
- https://www.datadoghq.com/product/synthetic-monitoring/
- https://docs.newrelic.com/docs/synthetics/synthetic-monitoring/using-monitors/intro-synthetic-monitoring/

Vẫn thiếu plan/region/device trial cho bốn phạm vi, nên M giữ `provisional`.
Không dùng benchmark này để BUILD thêm feature trước khi đóng P0/P1.

