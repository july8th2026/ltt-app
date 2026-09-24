# Task 3 — Ánh xạ lỗi engine → FAILED

**Nguồn tra:** memory `model-nha-tren-may-b.md` + `_luutru/
model-nha-tra-ve-rong-khoang-mot-nua-luot.md` (đo 10–12/09/2026): máy B trả
**HTTP 200**, job **SUCCEEDED**, `content` **RỖNG** — "vô hình với quan
trắc", `dem.ok` vẫn cộng một. `apps/ltt_llm/jobs.py:handle()` xác nhận
handler KHÔNG tự phát hiện rỗng — trả thẳng `kq.as_result()`.
`platform_core/workflow/cau_noi.py::ap_ket_qua` (đọc, không sửa) xác nhận
cầu nối chung chỉ nhìn `job.status`, không mở `result`.

**Đỏ:** `tests/test_2901_ai_loi_dien_giai.py` — `ImportError: cannot import
name 'ai_loi'`.

**Xanh:** `platform_core/workflow/nut_loi/ai_loi.py` (mới) —
`dien_giai(ket_qua, *, luoc_do=None)`. Bắt đúng ca đã đo:
`{"content": ""}` / `{"content": "   "}` / thiếu khoá / `None` → `FAILED
dau_ra_rong`. Đối chứng: `{"content": "xin chao"}` không lược đồ →
`SUCCEEDED` (không có ca này thì các phép trên xanh giả). 10/10 test xanh.

**Chưa làm được — cố ý, ngoài phạm vi tệp:** `dien_giai()` là hàm THUẦN,
CHƯA được gọi từ `cau_noi.ap_ket_qua` (nơi thật sự chốt trạng thái node) —
sửa tệp đó cần generalize cách suy `ten_cc` cho tiền tố `ai.` (xem báo cáo
Task 1, điểm 2), nằm ngoài `nut_loi/ai_*.py`. Đây là khoảng trống RUNTIME
thật: hôm nay nếu `ai.llm` chạy qua job thường, một job "thành công" với
content rỗng sẽ vẫn thành node SUCCEEDED cho tới khi ai đó nối `dien_giai()`
vào `ap_ket_qua`. Cần báo chủ dự án quyết định ai làm bước nối (Task 5 hoặc
một task riêng).
