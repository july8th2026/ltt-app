# AI_CLEAN_REBUILD — CẦN XEM (chiến dịch dọn legacy, PHA09 đã đóng nhiều phần)

Loại: CẦN XEM. Tệp chủ: `CAMPAIGN_STATE.md` (trạng thái chiến dịch) +
`LEGACY_SURFACE_MATRIX.csv` (ma trận từng tệp, cột cuối `DONE_09` = đã xử lý ở
PHA09). Các tệp tự gắn `HISTORY_ONLY` trong CSV là **sổ ghi lịch sử** — sửa nó
là viết lại lịch sử (nguyên văn CSV), nên các CHET/THAY trong đó (tên app/tool
đã đổi từ lúc scan) KHÔNG được sửa ở lượt 19/09 — xem `docs/_luutru/NGOAI_LE_QUET.md`.

Có 2 blocking là test gate thật (`test_1005_history_only`,
`test_190_public_api_coverage`) — cần lượt sau xác định phạm vi còn sống trước
khi quyết định giữ/lưu trữ toàn cụm hay từng tệp.

Không lưu trữ ở lượt 19/09 (chưa đủ 3 bằng chứng để quyết định toàn cụm).
