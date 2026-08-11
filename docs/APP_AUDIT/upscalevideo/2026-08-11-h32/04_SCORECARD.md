# H32.6 — Scorecard: Upscale Video

- **Quality Score: 72/100** (từ 64).
- **Market Score: 57/100** (không có capability thị trường mới).
- **Evidence Confidence: 94/100** cho technical contract; chất lượng cảm nhận
  riêng vẫn UNKNOWN.
- **Release Gate: BLOCKED** bởi upload security/artifact lifecycle và chưa có
  calibrated quality release evidence.

| Nhóm | Trọng số | 0–5 | Quy đổi | Nhận xét |
|---|---:|---:|---:|---|
| Giá trị/kết quả lõi | 15 | 3.8 | 11.4 | Full source Fast pass; visual quality unknown |
| Tính năng/độ đầy đủ | 12 | 3.2 | 7.7 | Option matrix đủ; restore/temporal thiếu |
| Chức năng/control | 12 | 4.2 | 10.1 | 17/17; FPS bug đã khóa regression |
| UX/workflow/IA | 12 | 3.6 | 8.6 | History/log/status/mobile rõ hơn |
| UI/design system | 8 | 3.9 | 6.2 | Bỏ fake Pro và jargon |
| Responsive/accessibility | 7 | 4.2 | 5.9 | inert/focus/no overflow |
| Hiệu năng/tin cậy | 9 | 3.9 | 7.0 | GPU telemetry/full source; dual GPU blocked |
| AI output/economics | 8 | 2.7 | 4.3 | Quote tốt; quality uncalibrated |
| Security/privacy/credit | 10 | 2.5 | 5.0 | Batch hold pass; upload/lifecycle P1 |
| Kiến trúc/ops/log | 7 | 4.1 | 5.7 | Runtime tools/evidence tốt; job type thô |

Tổng **71,9**, làm tròn **72**. Gate không được bù bằng điểm.

Gate: G0 PASS · G1 PASS kỹ thuật/UNKNOWN cảm nhận · G2 FAIL · G3 PASS có điều
kiện · G4 PASS phạm vi H32.6 · G5 FAIL · G6 PASS · G7 PARTIAL · G8 PARTIAL.

## Kết quả thực thi

- 56 targeted pytest pass.
- Browser desktop 1586×992 và mobile 390×844: overflow 0, console 0, failed
  application request 0; actual upload metadata/quote pass.
- GPU matrix 17/17 pass; full source GPU 1 pass; không thermal slowdown.
- Quality Lab: video contract PASS; perceived/temporal quality UNKNOWN.
