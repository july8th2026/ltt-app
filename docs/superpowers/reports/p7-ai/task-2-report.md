# Task 2 — Nhánh `mac_dinh` của `ai.router`

**Nguồn tra:** spec §12.1 dòng `ai.router` — "chọn MỘT nhánh trong enum khai
sẵn (`ai_choice`, ADR Q8); không khớp ⇒ nhánh `mac_dinh`"; "`core.if` không
bao giờ gọi LLM; chỉ `ai.router` gọi". Không có runtime mới cần tra cộng
đồng — đây là logic THUẦN của nền tảng, viết trực tiếp theo câu spec.

**Đỏ:** `tests/test_2903_ai_router_chon_nhanh.py` — `ImportError: cannot
import name 'ai_router'`.

**Xanh:** `platform_core/workflow/nut_loi/ai_router.py` (mới) —
`chon_nhanh(dau_ra, nhanh_hop_le, *, mac_dinh=NHANH_MAC_DINH)`: so khớp
**chính xác** sau `strip()`, không phải substring. 9/9 test xanh, gồm đối
chứng cố ý:

- `test_khop_thua_chu_khac_KHONG_duoc_tinh_la_khop` — model trả
  `"spam vi co lien ket la"` phải về `mac_dinh`, không phải "khớp lỏng" ăn
  theo vì chứa chữ `spam`. Không có dòng `in set(...)` (so khớp chính xác)
  thì test này đỏ — chứng minh phép kiểm bắt được đúng loại lỗi.
- `test_danh_sach_nhanh_rong_luon_ve_mac_dinh` — tập rỗng vẫn về mặc định
  (đối chứng cho "không khớp").

**Chưa làm được:** cùng hai điểm của Task 1 (chưa nối `__init__.py`/
`cau_noi.py`, ngoài phạm vi tệp). `chon_nhanh()` là hàm thuần nên tự nó
đã kiểm đủ mà không cần chờ wiring — đây là phần thực sự dùng được ngay.
`AI_ROUTER.ma_loi = ai_loi.MA_LOI_AI` (dùng chung Task 3, không khai riêng).
