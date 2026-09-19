# auto_scan_video_v6/ — TRA CỨU (V6, lớp ADR mới nhất, 18/09/2026)

Tệp chủ: **`TRANG_THAI_V6.md`** — trạng thái hiện hành của chương trình ASV V6
(98+), nhánh `phien/asv-v6`. `MA_TRAN_TINH_NANG_V6.md`, `MA_TRAN_KHOANG_TRONG.md`
là bảng tra năng lực/khoảng trống. Các `PHAxx_*.md` là hồ sơ từng pha (00 → 32),
đọc theo số thứ tự khi cần chi tiết một pha cụ thể.

⛔ `PHA06_KIEN_TRUC_GUI.md` tự ghi là **một pha nền bị bỏ qua** — các pha 08–12
xây thẳng lên trên, không đi qua nó; đọc để hiểu bối cảnh, không thi hành.

Ứng dụng sống: `apps/auto_scan_video/` + `server/static/asv/` (đã tách thành
tám module từ một IIFE `asv.js` cũ — mô tả trong `PHA06`). `CHAN_DOAN_TEST_448.md`
liên quan `tests/test_448_*` (xem thêm memory `test-448-doc-tep-tinh-khong-goi-may-b.md`).
