# 06 — Options & Decision Gate

| Phương án | Giá trị | Risk | Effort | Điểm/5 | Kết luận |
|---|---:|---:|---:|---:|---|
| REPAIR: khóa operator, test path, audit log | 5 | 1 | 2 | **4.7** | Khuyến nghị |
| PARITY: thêm approval/calendar/history | 3 | 3 | 4 | 2.4 | DEFER vì Q10 |
| DIFFERENTIATED: Google Sheet orchestration mới | 2 | 4 | 5 | 1.5 | REJECT hiện tại |

## Decision Gate khuyến nghị A

1. **A:** Socialbot là operator-only, không phải app customer.
2. **A:** sửa security/access được coi là maintenance hợp lệ dưới Q10.
3. **A:** giữ route lịch sử để không phá OAuth; khóa policy tại middleware/
   dependency, không redesign slug.
4. **A:** không thêm feature thị trường trước khi có quyết định thay Q10.
5. **A:** rollback bằng feature flag `LTT_SOCIALBOT_ROUTES` và commit policy;
   không xóa token/state.

Audit không tự áp dụng các quyết định này thành code.

