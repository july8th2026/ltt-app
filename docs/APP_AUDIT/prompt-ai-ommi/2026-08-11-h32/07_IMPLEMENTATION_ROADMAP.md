# Roadmap còn lại Prompt AI OMMI

## P1 — Trước release rộng

1. Dựng provider canary staging, chạy quote → hold → worker → apply → settle,
   lỗi → refund; xác minh token/job events/support ID.
2. Thêm model chooser customer-facing, bind model vào preview/quote/generate và
   giải thích trade-off.
3. Thêm project job timeline/recovery, retry/cancel theo nền tảng.

## P2 — Chất lượng trải nghiệm

4. i18n thật cho `/en`; keyboard/screen-reader audit và focus sau modal.
5. Onboarding template theo quảng cáo/phim ngắn/YouTube/character sheet.
6. Progressive detail cho selection; tìm kiếm khi catalog vượt 20 mục.
7. Download/probe JSON/MD/ZIP bằng browser và recovery two-tab/offline.

## P3 — Chỉ khi có nhu cầu/telemetry

8. Style inheritance, placeholder validation và profile.
9. Bulk import/export/search-replace ở operator/admin, không đưa vào brief.

Không deploy H32.2 riêng. H32.7 sẽ chạy full gate và lập release/rollback cho
toàn batch.
