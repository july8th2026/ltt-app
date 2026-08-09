# A7–A8 — Options và Decision Gate

## Ba phương án

| Phương án | Giá trị | Coverage | Rủi ro | Time-to-value | Điểm khuyến nghị |
|---|---:|---:|---:|---:|---:|
| A — REPAIR | 5 | 4 | 2 | 5 | 88/100 |
| B — PARITY ngay | 4 | 5 | 4 | 2 | 67/100 |
| C — DIFFERENTIATED/full publish | 5 | 5 | 5 | 1 | 59/100 |

**Khuyến nghị:** A → parity chọn lọc → differentiation. Không xây scheduler/editor nặng trước khi input, tiền, cancel, recovery và package đúng.

## Decision Gate đề xuất để Dev khóa

| Câu hỏi | A — khuyến nghị | B | Hệ quả chọn A |
|---|---|---|---|
| Phạm vi release kế tiếp? | Repair correctness/credit/lifecycle | Build feature thị trường trước | giảm tranh chấp và rework |
| Editor mức nào? | text + trim/reframe/caption style tối thiểu | multi-track đầy đủ | customer-first, effort hữu hạn |
| Source phase parity? | local + YouTube/public URL + Asset nội bộ | mọi cloud connector | phủ nhu cầu lớn trước |
| Publish? | package đúng + handoff Publish Bot | scheduler native ngay | tái dùng nội tại, tránh runtime thứ hai |
| Score? | giữ nhưng giải thích/calibrate | ẩn hoàn toàn | giữ differentiator có điều kiện |
| Partial render? | trạng thái PARTIAL + chỉ tính output thành công | fail toàn job | tận dụng output, minh bạch tiền |
| Retention? | policy chung + delete/export/self-service | giữ vô hạn | giảm privacy/storage risk |
| Rollout? | internal canary → beta có quota → public | public ngay | thu quality/SLO evidence |

Logic chỉ được chuyển sang BUILD sau khi các lựa chọn trên được ghi vào nguồn quyết định/kế hoạch; audit này chưa cấp quyền sửa/deploy.
