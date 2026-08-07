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


---

# Chấm lại sau khi thực hiện — 2026-08-07 15:38 (đã deploy)

```
Q 78 · M —  · E 68 · Release Gate: BETA
```

Gate cũ `INTERNAL`, bị chặn bởi G3. Ba gate đã chuyển:

| Gate | Trước | Sau | Vì sao |
|---|---|---|---|
| G3 Money/Credit | **FAIL** | **PASS** | `cap_tay()` kiểm tồn tại + FK `RESTRICT` đã vào production (`alembic head d2e3f4a5b6c7`, `FK credit_entries -> users`) |
| G4 Honest UI | **FAIL** | **PASS** | Không còn báo "Đã cấp" cho cấp phát vô hiệu; test hồi quy trực tiếp |
| G8 Operations | **FAIL** | **PASS** | 24 test qua HTTP + nhật ký thao tác admin |
| G6 Accessibility | UNKNOWN | **UNKNOWN** | vẫn chưa có E3 |

## Q 61 → 78

| Nhóm | Trọng số | Trước | Sau | Vì sao |
|---|---:|---:|---:|---|
| Tính năng và độ đầy đủ | 12 | 2 | 4 | cấp hàng loạt, trang chi tiết, nhật ký |
| Đúng chức năng và control | 16 | 2 | 4 | 4 control `MISSING` và 1 `MISLEADING` đã đóng |
| UX/workflow/IA | 12 | 2 | 4 | hết copy UUID giữa hai trang |
| Security/privacy/tenant/credit | 14 | 3 | 4 | lỗ P0 đã bịt hai tầng |
| Kiến trúc/vận hành/quan sát | 7 | 3 | 4 | 24 test phủ luồng tiền + nhật ký |

Các nhóm khác giữ nguyên. Tổng: **78/100** — "cạnh tranh nhưng còn gap" (70–79).

## E 55 → 68

Lên nhờ phần lớn kết luận giờ ở **E2** (test đã chạy) thay vì E1 (đọc mã):
`test_162` 22 mục, `test_163` 24 mục, và migration đã xác minh trên CSDL
production thật.

**Vẫn chưa tới 70 vì THIẾU E3.** Chưa render trang admin trên browser thật —
phiên trình duyệt hết hạn sau deploy và trang admin bắt đăng nhập.

## Vì sao `BETA` chứ không `COMMERCIAL`

Ba gate chặn đã mở, nhưng:
- **G6 Accessibility vẫn UNKNOWN.** Mục 4 nói gate không được bù bằng điểm.
- **E 68 < 70.** Thiếu E3 nghĩa là chưa được gọi là "đã xác minh" theo mục 5.

Nâng lên `COMMERCIAL` cần đúng một việc: **kiểm trên browser thật**. Cụ thể là
mở `/admin/nguoi-dung?q=<email>` và `/admin/user/list` khi đã đăng nhập admin,
ghi viewport, console error, failed request theo mục 5.
