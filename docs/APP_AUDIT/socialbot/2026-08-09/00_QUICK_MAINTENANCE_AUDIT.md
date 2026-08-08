# Socialbot — QUICK maintenance audit H26.10C

## Charter và current truth

- Snapshot 2026-08-09, local; không dùng production data, không gọi Meta/TikTok.
- Q10/Q52/Q78: frozen, lifecycle `maintenance`; chỉ nhận shell/observability
  chung. Runtime lịch sử và OAuth route không được refactor trong H26.
- `public=False` đang đúng hợp đồng hiện hành: không hiện cho người chưa đăng
  nhập; sau đăng nhập vẫn theo AppAccess. Đây không phải cờ khai tử app.

## Kết quả

`Q 68 · M 55 · E 78 · INTERNAL/MAINTENANCE`

- E1: manifest khai `maintenance`, browser requirement và blocker OAuth.
- E2: targeted Socialbot/registry/access tests đã chạy trong H26.10C.
- E3: tài khoản customer đăng nhập thấy card ghi trạng thái bảo trì; anonymous
  vẫn bị ẩn theo contract đã có. Không chạy posting/OAuth end-to-end.
- Không có sửa đổi trong `apps/socialbot` hay route/runner đóng băng.

## Gate và control

G0/G2/G4 PASS trong phạm vi presentation. G1/G3/G5/G7/G8 không được tái chứng
minh cho posting thật ở vòng QUICK, nên app không được nâng khỏi maintenance.
Raw log vẫn chỉ dành operator/support theo Q76; customer chỉ nhận timeline đã
làm sạch. Retention/log dùng policy chung Q75 trong H26.11.

## Quyết định

1. REPAIR runtime Socialbot: REJECT trong H26 vì trái Q10.
2. Xóa/ẩn hoàn toàn sau đăng nhập: REJECT vì người dùng không yêu cầu khai tử và
   `public=False` không có nghĩa đó.
3. Giữ frozen + maintenance, chỉ nhận observability chung: CHỌN, đúng Q78.

## Roadmap

- H26.10C: khóa trạng thái/ranh giới, targeted test — PASS.
- H26.11: áp dụng retention, log redaction và SLO chung, không đổi nghiệp vụ.
- Muốn phát triển lại phải có quyết định mới thay Q10, audit DEEP riêng và canary
  OAuth/provider; không được nhập lẫn vào phase giao diện hiện tại.
