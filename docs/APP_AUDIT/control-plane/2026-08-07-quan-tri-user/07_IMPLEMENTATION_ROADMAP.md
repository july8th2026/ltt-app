# A9 — Roadmap

⚠️ **Chỉ thực hiện sau khi A8 được chốt.** Ghi sẵn để chốt xong là chạy được ngay.

## Phase 0 — Đóng blocker tiền (F-01)

| | |
|---|---|
| Việc | `cap_tay()` kiểm người dùng tồn tại → ném lỗi rõ. Migration thêm FK `credit_entries.user_id → users.id`. |
| Dependency | Không |
| Test | Cấp cho UUID không tồn tại → từ chối, **0 bút toán được ghi**. Trồng lại bug → test đổ. |
| PASS gate | G3 và G4 chuyển PASS |
| Rollback | `git revert` + `alembic downgrade` một bậc |
| Rủi ro | FK vướng dữ liệu cũ — **đã đo E2: 0 bút toán mồ côi**, migration sạch |

## Phase 1 — Cấp credit dùng được (F-02, F-03)

| | |
|---|---|
| Việc | Ô nhập nhận **email**; thêm đường cấp **hàng loạt** (dán danh sách email, kiểm toàn bộ trước, ghi trong một transaction). |
| Dependency | Phase 0 |
| Test | Email hợp lệ → đúng người. Email sai trong danh sách → **không ai** được cấp, báo rõ email nào. CSRF sai → từ chối. |
| PASS gate | J1 phủ trọn |
| Rollback | `git revert` |

## Phase 2 — Test phủ luồng tiền (F-05)

| | |
|---|---|
| Việc | Test qua HTTP cho `/admin/grant-credit`: thành công, email sai, CSRF sai, hàng loạt nguyên tử, không phải admin thì bị chặn. |
| Dependency | Phase 1 |
| PASS gate | G8 chuyển PASS |

## Phase 3 — Nhìn thấy người dùng (F-04) · *sau đợt onboarding*

Cột số dư trong `UserAdmin` + trang `/admin/user/<id>` gom số dư, job gần nhất
kèm credit đã tiêu, đơn nạp, phiên đang mở, nút cấp credit tại chỗ.
**Ràng buộc:** không được mở đường sửa `email`/`password_hash`.

## Phase 4 — Nghiệm thu

Chạy `tools/gate.py` (9 bước) · kiểm trang admin trên **browser thật** để bù bằng
chứng E3 còn thiếu · chạy lại `tools/audit_van_hanh.py` · deploy · kiểm trên URL
công khai.

## A10 — Đo trước/sau

| Chỉ số | Trước (2026-08-07) | Mục tiêu |
|---|---|---|
| Số thao tác để cấp credit cho 10 người | 10 lần submit + 10 lần copy UUID | 1 lần submit |
| Cấp nhầm vào user không tồn tại | **không bị chặn** | bị chặn ở 2 tầng |
| Gate FAIL | G3, G4, G8 | 0 |
| Q | 61 | ≥ 75 |
| E | 55 | ≥ 70 (bù bằng E2 test + E3 browser) |
