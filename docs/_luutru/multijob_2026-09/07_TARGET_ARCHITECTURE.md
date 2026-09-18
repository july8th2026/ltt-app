# 07 — Kiến trúc đích

Nguồn chân lý của kiến trúc đích là **design spec đã khoá**:
`docs/superpowers/specs/2026-09-11-ltt-llm-multijob-design.md` (chủ dự án duyệt 2026-09-11).
Tệp này chỉ trỏ tới đó để không có hai bản mô tả trôi khỏi nhau.

Tóm tắt một đoạn: một mặt phẳng admission ở máy A (sổ ngân sách = `ExecutionLease` mở rộng + phòng
chờ `llm_waiters` cho cửa tương tác + hàng `jobs` cho việc nền, cùng một hàm luật nhận trong advisory
lock) → gateway máy B là chốt fail-closed đếm đúng token, không xếp hàng → llama-swap **một** hồ sơ gộp
text+vision → llama-server `-np 4 -kvu -c 204800 --mmproj`, draft-mtp, ghim UUID 3090. Hai lớp ưu tiên
(tương tác > nền, nền ≤ N−1 slot), ≤1 whale, trần tài khoản khi có người chờ, cửa stream chờ trong SSE,
giữ tiền sau khi được nhận, hủy cứng, quan sát theo mã lý do.
