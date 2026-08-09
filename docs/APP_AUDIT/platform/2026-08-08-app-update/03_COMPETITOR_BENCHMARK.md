# 03 - Benchmark thị trường

**Chốt lại:** 2026-08-09

**Phạm vi:** marketplace/control plane và khả năng vận hành xuyên app; không
chấm chất lượng output của từng model AI.

**Evidence:** tài liệu chính thức E1, đối chiếu với browser/evidence H26 của LTT.

## Nguồn chuẩn đã dùng

- [Canva Apps Marketplace](https://www.canva.com/apps/) và
  [Editing & designing](https://www.canva.com/help/editing-designing/): một điểm
  khám phá app, nhóm chức năng và công cụ tạo/chỉnh sửa thống nhất.
- [Adobe Firefly generation history](https://helpx.adobe.com/in/firefly/view-history/view-generation-history/view-generation-history.html)
  và [organize generations](https://helpx.adobe.com/ca/firefly/web/access-your-files/organize-your-generations.html):
  lịch sử media dùng chung, lọc, favorite, download, project/file.
- [Magnific/Freepik Projects](https://www.magnific.com/ai/docs/projects),
  [quickstart](https://www.magnific.com/ai/docs/quickstart) và
  [Spaces](https://www.magnific.com/ai/docs/spaces-overview): project gom history,
  upload, download, folder và canvas node.
- [Krea creative suite](https://www.krea.ai/),
  [video generation](https://www.krea.ai/features/ai-video-generator) và
  [enhancer](https://www.krea.ai/features/ai-enhancer): nhiều model trong một
  workspace, chạy song song, so sánh, asset manager và batch enhancement.
- [Runway navigation](https://help.runwayml.com/hc/en-us/articles/24298206897043-Navigating-Runway),
  [asset organization](https://help.runwayml.com/hc/en-us/articles/23998498329107-How-to-organize-assets)
  và [Workflows](https://help.runwayml.com/hc/en-us/articles/45763528999699-Introduction-to-Workflows):
  session/project/asset, workflow có input-output typed và lịch sử output.

Các nguồn trên được dùng để đo **table stakes**, không dùng số người dùng hay
claim marketing làm bằng chứng chất lượng.

## Đối chiếu năng lực

Thang 0-3: `0 không có · 1 sơ khai · 2 đạt phần lớn · 3 hoàn chỉnh/khác biệt`.

### Table stakes — 70% M

| Năng lực | LTT /3 | Nhận định có bằng chứng |
|---|---:|---|
| Catalog, search, taxonomy, lifecycle | 2 | customer catalog/search/category hoạt động và không lộ tool nội bộ; hệ sinh thái nhỏ hơn Canva/Freepik |
| Tạo và lịch sử xuyên media | 2 | mọi app async có History/job timeline; history vẫn thiên theo app, chưa thành asset library hợp nhất như Firefly/Runway |
| Project và tổ chức asset | 1 | Prompt AI có project/asset; chưa có folder/project xuyên toàn portfolio và cộng tác như Freepik/Runway |
| Lifecycle, lỗi, retry, cancel, download | 3 | structured JobEvent, trạng thái trung thực, retry/cancel/recovery/download đã được test và browser kiểm tra |
| Responsive và accessibility lõi | 2 | desktop/mobile và keyboard control đã qua matrix; chưa tuyên bố chứng nhận WCAG toàn site |
| Tài khoản, credit và minh bạch chi phí | 3 | quote/confirm/hold/settle/refund và ledger owner-scoped có regression |
| **Kết quả table stakes** | **13/18 = 72** | |

### Differentiator — 30% M

| Năng lực | LTT /3 | Nhận định có bằng chứng |
|---|---:|---|
| Job lineage, event timeline, support export | 3 | durable, role-aware, redacted và có metrics/support path dùng chung |
| Credit transaction an toàn | 3 | quote trước chạy, hold/settle/refund idempotent; không chỉ trừ số dư ở UI |
| Agent DAG + hạ tầng GPU nội bộ | 2 | typed graph/run scope và lease hai GPU hoạt động; độ rộng node/model chưa bằng nền tảng dẫn đầu |
| Ecosystem, template, collaboration | 1 | có catalog/template theo app nhưng chưa có marketplace/collaboration/project xuyên app |
| **Kết quả differentiator** | **9/12 = 75** | |

`M = 70% × 72,2 + 30% × 75,0 = 73,1 → M73`.

## Kết luận giữ/bổ sung

- **Giữ và coi là khác biệt:** lifecycle job trung thực, event log bền, credit
  transaction, support export, rollback/recovery và điều phối GPU hai card.
- **Ưu tiên sau release:** asset library/project dùng chung xuyên app, folder,
  favorite/version, dùng output app trước làm input app sau và collaboration có
  ownership rõ.
- **Không sao chép:** độ rộng tool/model chỉ để tăng số lượng; control nâng cao
  dành cho dev trên màn hình customer; claim output tốt hơn nếu chưa có blind
  evaluation.
- **Nợ benchmark:** chưa trial có trả phí toàn bộ năm đối thủ và chưa blind-test
  output AI. Vì vậy M73 chỉ áp dụng cho platform/control plane, không phải model
  quality hay vị thế thương mại tổng thể.

## Tập benchmark theo app cho vòng chuyên sâu kế tiếp

| App/phạm vi | Tập benchmark | Hành vi cần đo |
|---|---|---|
| Upscale Video | Topaz Video AI, TensorPix, AVCLabs, HitPaw, CapCut | preset, queue, before/after, download, GPU expectation |
| Tạo Video Seedance | Kling, Runway, Luma, Pika, Veo surfaces | composer density, reference media, history, retry/remix |
| Prompt AI | LTX Studio, Katalist, Flora, PlenX | project IA, asset library, scene/storyboard/version/history |
| Auto Sub | CapCut, VEED, Descript, Submagic, Captions | upload/transcribe/style/timeline/render/recovery |
| Tạo ảnh hợp nhất | Midjourney, Firefly, Ideogram, Leonardo, Krea | references, variants, history, edit handoff |
| Tạo Clip ngắn | OpusClip, Vizard, Munch, Captions, Klap | ingest, highlight, edit, batch, aspect, export |
| Chat AI | ChatGPT, Claude, Gemini, Perplexity | thread, attachment, streaming, retry, source/error states |
| Agent AI | Flora, PlenX, Runway Workflows, Make, n8n | block grammar, run scope, history, recovery, customer UX |
| Social publishing | Buffer, Hootsuite, Metricool, Later, Sprout | maintenance/status; không mở feature mới |
