# H32.5 — Current truth: Tạo Video Seedance

## Năng lực có thật

| Miền | Hiện trạng | Evidence |
|---|---|---|
| Model | Mini/Standard/Fast; registry đổi duration/aspect/resolution/seed | E3 browser, E2 test |
| Prompt | 10.000 ký tự, history, dịch EN/ZH/VI, creative guidance | Source + E3 |
| Reference | Ảnh/video/audio, role/handle, preview, tối đa 4, reuse asset | Source + E3 upload |
| Thiết lập | 4–15s, 6 tỉ lệ, 480p–4K theo model, audio, 1–2 variant | E3 |
| Credit | Estimate/hold trước chạy, settle token thật ở worker | Kế thừa audit 2026-08-09 |
| History | Owner-scoped 60 job; model/aspect/status/sort; grid/list persisted | E2/E3 |
| Output | Player Range 206, download, activity log, quote/confirm Upscale | E2/E3 quote only |

## Delta UI đã triển khai

- Composer tách thành `nội dung cuộn + quote/CTA cố định`; không còn CTA dưới
  fold hoặc sticky che control.
- Asset cũ chuyển sang progressive disclosure và sidebar mở đúng panel đó.
- Status card/tab đi qua i18n; raw `progress_msg` worker không còn lộ trên card.
- Mobile composer dùng `inert` + `aria-hidden` khi đóng, có nút Close thật,
  trả focus về nút mở và tự đồng bộ khi đổi breakpoint.
- Toolbar history gọn hơn nhưng giữ accessible name; horizontal tab scrollbar
  được ẩn mà vẫn cuộn được.
- Estimate HTMX có pending/failure state; failure khóa CTA trả phí, success mở
  lại. Không còn dấu `…` hoặc báo giá cũ trông như sẵn sàng khi request lỗi.

## Sự thật không được nâng hạng bởi vòng này

- Không chạy provider/job theo MoTa nên không có evidence mới về output,
  latency, token hoặc billing.
- P0 credit actual vượt hold, orphan ref, audio AssetType/MIME và lifecycle từ
  deep audit 2026-08-09 vẫn chưa được đóng.
- Fixture done video là asset kiểm layout; không được gọi là video Seedance.
