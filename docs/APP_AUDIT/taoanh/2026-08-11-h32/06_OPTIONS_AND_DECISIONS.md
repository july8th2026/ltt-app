# H32.3 — Options & decisions

| Phương án | Giá trị | Rủi ro | Tốc độ | Điểm /100 |
|---|---:|---:|---:|---:|
| A — Chỉ sửa UI | 55 | 70 | 95 | 66 |
| B — Repair contract rồi parity chọn lọc | 92 | 30 | 72 | **86** |
| C — Xây editor/asset suite đầy đủ ngay | 85 | 75 | 30 | 58 |

**Khuyến nghị B:** khóa pricing/provider/data recovery trước, rồi thêm download,
polling và history. Không xây pixel editor giả; dùng output handoff như hiện tại.

Quyết định đã khóa trong H32.3:

1. Giữ hai mode trong một Image Studio shell.
2. Preview phải nói đúng model và chi phí trước CTA.
3. Không đổi giá Thumbnail âm thầm trong audit; cần quyết định economics có
   migration/version và regression tiền.
4. Fixture chỉ chứng minh UI; không được dùng làm bằng chứng output AI.
5. Không deploy riêng phase này; release plan toàn batch nằm ở H32.7.
