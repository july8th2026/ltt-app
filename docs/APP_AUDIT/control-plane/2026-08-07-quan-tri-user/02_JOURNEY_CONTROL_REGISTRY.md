# A2 — Journey & Control Registry

Chỉ đăng ký control **trong phạm vi J1–J3**. Trạng thái theo mục 6 LTT-AQA.

## J1 — Cấp credit cho một nhóm nhân viên

| Control | Hành động | Credit | Verdict | Bằng chứng |
|---|---|---|---|---|
| `/admin/user/list` → cột | xem danh sách người dùng | — | `PARTIAL` | E1 `admin.py:249` — `column_list` **không có số dư** |
| ô tìm kiếm | tìm theo email/tên | — | `LIVE` | E1 `column_searchable_list` |
| copy UUID | *(không có nút)* | — | `MISSING` | E1 — phải bôi đen chuỗi UUID bằng tay |
| `/admin/grant-credit` ô User ID | nhận UUID gõ tay | ghi sổ | `MISLEADING` | E1 `admin.py:399` + E2 không có FK — xem F-01 |
| ô Số credit | dương cộng, âm trừ | ghi sổ | `LIVE` | E1 |
| nút Cấp credit | ghi bút toán `grant` | ghi sổ | `LIVE` | E1 `cap_tay()` |
| cấp cho nhiều người | *(không có)* | — | `MISSING` | E1 — không có đường hàng loạt |

## J2 — Biết một người dùng đang thế nào

| Control | Verdict | Bằng chứng |
|---|---|---|
| trang chi tiết một user | `MISSING` | E1 — sqladmin có trang detail mặc định nhưng **không** gom số dư/job/đơn |
| số dư của user | `MISSING` (ở nơi cần) | E1 — chỉ suy ra được bằng cách lọc Sổ credit theo UUID |
| job của user | `PARTIAL` | E1 — có `/admin/job/list`, lọc bằng UUID copy tay |
| đơn nạp của user | `PARTIAL` | E1 — `/admin/don`, cũng bằng UUID |

## J3 — Xử lý sự cố tiền

| Control | Verdict | Bằng chứng |
|---|---|---|
| thu hồi credit (số âm) | `LIVE` | E1 |
| xem lịch sử bút toán một user | `PARTIAL` | E1 — lọc thủ công |
| nhật ký thao tác admin | `PARTIAL` | E1 — `cap_tay(by=)` ghi `admin=` vào ghi chú bút toán; **chỉ có với credit**, không có với đổi vai trò / vô hiệu hoá tài khoản |
| xác nhận trước khi cấp | `MISSING` | E1 — submit là ghi ngay, không có bước xem lại |

**PASS A2:** mọi control trong phạm vi đã có verdict.

⚠️ Chưa có bằng chứng E3 (render browser thật). Ảnh hưởng tới điểm E, ghi ở 04.
