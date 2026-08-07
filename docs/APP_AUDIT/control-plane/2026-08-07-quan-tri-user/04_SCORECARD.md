# A5 — Scorecard

## Kết quả

```
Q 61 · M —  · E 55 · Release Gate: INTERNAL
BLOCKED cho COMMERCIAL boi G3 Money/Credit (F-01)
```

**M không chấm.** Đây là control plane nội bộ một người dùng, không cạnh tranh
trên thị trường theo cùng JTBD. Chấm M ở đây sẽ là con số trang trí. Ghi `—` thay
vì bịa (quy tắc mục 8: unknown vẫn ghi unknown).

## Q — 61/100

Trọng số đã khoá ở A0 (8 điểm AI phân bổ lại: +4 Security/credit, +4 Control).

| Nhóm | Trọng số | Điểm /5 | Được | Ghi chú |
|---|---:|---:|---:|---|
| Giá trị sản phẩm/kết quả lõi | 15 | 3 | 9,0 | Cấp được credit, quản được user — lõi chạy |
| Tính năng và độ đầy đủ | 12 | 2 | 4,8 | Thiếu hàng loạt, thiếu trang chi tiết user |
| Đúng chức năng và control | 16 | 2 | 6,4 | 4 control `MISSING`, 1 `MISLEADING` |
| UX/workflow/IA | 12 | 2 | 4,8 | J1 bắt copy UUID giữa hai trang |
| UI/thẩm mỹ/design system | 8 | 3 | 4,8 | Dùng chung `ltt.css`, nhất quán với nền tảng |
| Responsive/accessibility | 7 | 2 | 2,8 | Chưa kiểm E3; sqladmin mặc định chấp nhận được |
| Hiệu năng/độ tin cậy | 9 | 4 | 7,2 | 10 user, không có vấn đề tải |
| Security/privacy/tenant/credit | 14 | 3 | 8,4 | CSRF đủ, append-only đúng, **nhưng thiếu FK** |
| Kiến trúc/vận hành/quan sát | 7 | 3 | 4,2 | Có test nền tảng; **không có test cho luồng cấp credit** |
| **Tổng** | **100** | | **61** | có nợ sản phẩm (60–69) |

## E — 55/100

| Cấp | Dùng cho |
|---|---|
| E2 | Ràng buộc CSDL, số bút toán, số tài khoản — đo trực tiếp production |
| E1 | Toàn bộ hành vi control — đọc `server/admin.py` |
| **E3 thiếu** | **Chưa render trang admin trên browser thật** |

E thấp vì phần lớn kết luận dừng ở E1. Theo mục 5: **E1 không được gọi là "đã
xác minh"**. Các finding dưới đây ghi rõ cấp bằng chứng của từng cái.

## Gate G0–G8

| Gate | Kết quả | Lý do |
|---|---|---|
| G0 Scope | PASS | A0 khoá rõ |
| G1 Core Outcome | PASS | Cấp credit tạo bút toán thật (E2: 12 bút toán `grant`) |
| G2 Security | PASS | CSRF có; chỉ admin; không sửa được email/mật khẩu qua form |
| **G3 Money/Credit** | **FAIL** | **F-01** — cấp credit cho user không tồn tại không bị chặn |
| G4 Honest UI | **FAIL** | **F-01** — báo "Đã cấp… Số dư mới: N" cho một cấp phát vô hiệu |
| G5 Data Recovery | PASS | Sổ append-only, thu hồi bằng bút toán âm |
| G6 Accessibility | UNKNOWN | chưa có E3 |
| G7 Performance | PASS | quy mô 10 user |
| G8 Operations | **FAIL** | không có test nào phủ luồng cấp credit của admin |

**Release Gate: `INTERNAL`.** Dùng nội bộ được — chính bạn đang dùng. Nhưng
G3/G4/G8 FAIL nên **chưa đạt `COMMERCIAL`**, và ba gate này đều do F-01/F-05.
