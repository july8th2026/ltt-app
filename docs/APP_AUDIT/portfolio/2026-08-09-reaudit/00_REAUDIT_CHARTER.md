# H28 — Re-audit độc lập vòng 2

- **Chuẩn:** LTT-AQA v1.0, `docs/quy_tac_audit.md`.
- **Mode:** DEEP audit-only; local fixture, dữ liệu test cô lập.
- **Snapshot:** 2026-08-09.
- **Phạm vi:** 13 manifest / 12 sản phẩm-runtime; Thumbnail là child mode của
  Tạo ảnh nhưng route và control được kiểm riêng.
- **Không thuộc phạm vi:** sửa runtime, provider production, deploy, dữ liệu
  production, quyết định thay Q10 Socialbot.

## Mục tiêu vòng 2

1. Không tin trạng thái `DONE` hoặc điểm H27 nếu chưa đối chiếu lại công thức.
2. Chạy lại mọi route trên browser desktop/mobile, ghi console/network/overflow.
3. Kiểm lại A2 Control Registry và A4 benchmark, không chỉ đếm file 00–07.
4. Kiểm lại các blocker bằng source/test mục tiêu.
5. Công bố lại Q/M/E/Gate; giữ UNKNOWN đúng nghĩa.

## Kết luận charter

H27 là baseline có giá trị về finding và roadmap, nhưng **không đạt tuyên bố
“audit triệt để”**: Evidence Confidence dùng sai taxonomy, bốn hồ sơ runtime có
A2/A4 mỏng và `DONE` được hiểu từ sự hiện diện file thay vì PASS A0–A10. H28
supersede điểm E và trạng thái completeness; không xóa lịch sử H27.

