# 07 — Implementation Roadmap: Tạo ảnh AI + Thumbnail

| Phase | Vé | Phạm vi | Exit criteria |
|---|---|---|---|
| 0 Money/data safety | IMG-R01..R06 | price registry, quote, form recovery, body cap, lifecycle graph | Pro quote đúng; 0 draft loss; oversize chặn trước full read; 0 orphan |
| 1 Canonical product | IMG-U01..U06 | facade mode, locale, progress/history, error/partial contract | VI/EN; both modes poll/recover; partial/refund rõ |
| 2 Asset library | IMG-A01..A06 | page/search/folder/delete/download/reuse, reference roles | output cũ tìm/reuse/delete theo policy; no 60-job cutoff |
| 3 Creative parity | IMG-C01..C06 | model-aware ratio/resolution, reference strength, variations, compare diff | capability đúng model; rerun/vary/reuse A–Z |
| 4 Thumbnail studio | IMG-T01..T06 | progressive form, versioned Brand Kit, safe-zone/text QA, export preset | mobile task success ≥90%; QA không giả CTR |
| 5 Optional editor | IMG-E01..E03 | mask/canvas discovery/prototype | chỉ BUILD khi usage/interview vượt gate |

## Vé ưu tiên

- **IMG-R01:** dùng canonical `MODEL_CREDIT_PER_IMAGE`/pricing version cho cả hai mode.
- **IMG-R02:** server quote envelope chứa model/resolution/count/unit/total/version.
- **IMG-R03:** provider-cost regression Flash/Lite/Pro + reserve/settle/partial.
- **IMG-R04:** local draft/PRG/preserve form; disable edit/style run nếu thiếu ref.
- **IMG-R05:** request body cap/streaming validation trước `read()` toàn bộ.
- **IMG-R06:** reference/output staging, promote, delete, TTL và retention dependency.
- **IMG-U01:** locale-aware mode/fragment/action/redirect URLs.
- **IMG-U02:** poll/cancel/retry nhất quán cả General/Thumbnail.
- **IMG-U03:** stable customer error envelope/codes và next action.
- **IMG-U04:** explicit partial outcome, actual/requested/refund/retry missing.
- **IMG-U05:** preview đầy đủ model/price/ref/brand/resolution.
- **IMG-U06:** product-level job/asset facade không đổi executor/job legacy.
- **IMG-A01..A06:** pagination/search/project, delete/download, reuse, ownership query
  theo object thay vì recent scan, quota/retention disclosure.
- **IMG-C01..C06:** model capability registry, ratio/resolution, multiple role refs,
  strength, rerun/vary và metadata compare.
- **IMG-T01..T06:** progressive sections/sticky CTA, Brand Kit CRUD/version/logo,
  text OCR/safe-zone/policy QA, 1280×720+ export và A/B handoff guidance.

## Verification bắt buộc

1. Unit/API: pricing versions, settlement, partial/refund, ownership, storage rollback.
2. Frontend/template: draft retention, prerequisites, i18n, model capability.
3. Playwright desktop/mobile VI/EN: both modes, validation, quote, progress,
   partial, cancel/retry/download/delete/remix.
4. Provider staging smoke cho từng model active; blind output panel tách khỏi test
   kỹ thuật. Full `python tools\gate.py` trước release; deploy chỉ khi được yêu cầu.
