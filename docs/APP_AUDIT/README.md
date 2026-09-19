# docs/APP_AUDIT — hồ sơ audit chất lượng app

**Loại:** TRA CỨU (quy trình) + LỊCH SỬ (từng hồ sơ audit theo ngày). Tệp chủ
quy trình: `docs/quy_tac_audit.md` (LTT-AQA — mode, scorecard Q/M/E, gate
G0–G8, pipeline A0–A10). Mỗi audit là snapshot một lần cho một app tại một
ngày, theo mẫu `_MAU/` — **không phải đặc tả sống**, không tự cập nhật khi
code đổi.

**Trạng thái 2026-09-19:** đã tách theo tệp — 12 audit đã đóng đủ 3 bằng
chứng (0 blocking thật, nội dung tự thân là audit chốt theo mẫu, sửa cuối
38–46 ngày) chuyển sang `docs/_luutru/2026-09/APP_AUDIT/…` (có README
đánh dấu). Các audit còn lại **giữ nguyên** vì vẫn được `docs/KE_HOACH_TRIEN_KHAI.md`,
`docs/QUYET_DINH_NEN_TANG.md`, `tests/test_147_layering.py` hoặc
`frontend/prompt-ai-ommi/src/OmmiShell.tsx` trích dẫn làm bằng chứng quyết
định/lịch sử — đừng lưu trữ tiếp nếu chưa `git grep` lại tên thư mục toàn kho.

Ngoại lệ máy quét (đường dẫn mã cũ trong audit lịch sử, cố ý không sửa):
`docs/_luutru/NGOAI_LE_QUET.md`.
