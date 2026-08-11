# H32.3 — Findings

## Đã sửa trong phase

| ID | Severity | Hiện tượng → xử lý | Evidence |
|---|---|---|---|
| IMG-H32-01 | P1 | General preview giấu model/chi phí → thêm disclosure từ lựa chọn và bảng giá thật | pytest + browser E3 |
| IMG-H32-02 | P1 | Thumbnail preview giấu model/count/giá/reference/brand → bổ sung toàn bộ cấu hình khách gửi | pytest + browser E3 |

## Còn mở

| ID | Severity | Finding | Acceptance |
|---|---|---|---|
| IMG-H32-03 | P1 | Gemini 3 Pro giá General 16 nhưng Thumbnail 5 credit/ảnh | Một pricing version/capability contract, quote/hold/settle/refund test cùng model |
| IMG-H32-04 | P1 | Chưa chạy provider E4 nên chưa chứng minh chất lượng, latency, output thật và save/download | Canary staging tạo output cả hai mode, probe file, settle/refund, lưu artifact |
| IMG-H32-05 | P1 | POST validation/error không khôi phục đầy đủ brief; file input không thể tự restore | Draft server/client, field error, PRG canonical, file metadata an toàn |
| IMG-H32-06 | P1 | Upload đọc body trước cap; reference/output thiếu lifecycle self-service | Stream/body cap, staging/promote, TTL/delete disclosure và test |
| IMG-H32-07 | P2 | Thumbnail queued/running không poll/cancel/retry như General | State tự cập nhật; cancel/retry owner-only, không reload form |
| IMG-H32-08 | P2 | Partial output/refund và stable error chưa giải thích rõ | requested/actual/errors/refund + support code |
| IMG-H32-09 | P2 | History chỉ 12; owner lookup có cửa sổ 60; thiếu search/filter/delete/download | Pagination owner query trực tiếp và asset actions |
| IMG-H32-10 | P2 | Ratio/resolution/reference limit chưa model-aware | Capability registry điều khiển UI + server validation |
| IMG-H32-11 | P2 | Score 82/100 chỉ đo contrast/detail/exposure | Luôn ghi “kỹ thuật”; thêm OCR/layout score trước khi nói quality/CTR |
| IMG-H32-12 | P3 | Preset có tên nội bộ, copy VI/EN trộn | Curate tên khách hàng và locale QA |

Không có P0 tái hiện trong fixture. Release rộng vẫn bị chặn bởi 03–06.
