# A7–A8 — Phương án và quyết định

| Phương án | Value | Risk | Reuse | Kết luận |
|---|---:|---:|---:|---|
| A — shell canonical + mode fragment qua HTTP contract | 5 | 2 | 5 | **CHỌN** |
| B — giữ hai trang, chỉ restyle giống nhau | 2 | 1 | 5 | không đóng IMG-H26-01/02 |
| C — gộp executor/schema/job ngay | 3 | 5 | 1 | REJECT, rủi ro dữ liệu/credit |

Quyết định đã khóa bởi lựa chọn “toàn bộ khuyến nghị A”, Q54/Q55/Q70 và roadmap
H26.9: `/taoanh` là entry; General render trực tiếp; Thumbnail là mode trong
cùng shell, lấy fragment từ API/route của app `thumbnail`; hai app không import
ruột nhau. Route queue/file/remix/job cũ tiếp tục là compatibility surface.
