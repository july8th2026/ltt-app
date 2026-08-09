# 06 — Options & Decision Gate: Tạo Video Seedance

## Ba phương án

| Tiêu chí | REPAIR | PARITY | DIFFERENTIATED |
|---|---:|---:|---:|
| User value | 75 | 95 | 88 |
| Blocker coverage | 98 | 96 | 76 |
| Time-to-value | 95 | 72 | 40 |
| Reuse nội tại | 96 | 90 | 66 |
| Effort/cost | 92 | 66 | 30 |
| Dependency risk | 92 | 72 | 38 |
| Confidence | 96 | 84 | 58 |
| **Tổng /100** | **89** | **91** | **60** |

**Khuyến nghị: PARITY có kiểm soát** — luôn làm toàn bộ REPAIR trước, sau đó
chỉ mở edit/extend + scene sequence tối thiểu nếu capability probe và benchmark
PASS. Không thêm model/tool chỉ để tăng số lượng.

## Câu hỏi khóa logic

| ID | Câu hỏi | Lựa chọn | Khuyến nghị | Trạng thái |
|---|---|---|---|---|
| D1 | Lời hứa chính? | A Generate dễ + refs; B editor; C model playground | **A** | Chưa khóa |
| D2 | Giá customer khi actual vượt quote? | A cap ở held; B trừ thêm; C dừng settle | **A** + metric platform variance | Chưa khóa |
| D3 | Ref lifecycle? | A staging/TTL/promote; B lưu ngay; C browser-only | **A** | Chưa khóa |
| D4 | Recovery UI? | A in-app live/cancel/retry/history; B chỉ global Jobs | **A** | Chưa khóa |
| D5 | Parity Phase 2? | A edit+extend+simple sequence; B full timeline; C không thêm | **A** nếu benchmark PASS | Chưa khóa |
| D6 | Model config? | A operator registry/probe; B hardcode endpoint | **A** | Chưa khóa |
| D7 | i18n/a11y target? | A VI+EN A-Z/WCAG AA; B VI desktop | **A** | Chưa khóa |
| D8 | Release? | A fixture→gate→canary→auth prod verify; B deploy thẳng | **A** | Chưa khóa |

Không BUILD khi D1–D8 chưa khóa. Audit app kế tiếp vẫn được tiếp tục độc lập.
