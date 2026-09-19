# A1 — Current Truth

Nguồn: `server/admin.py` (961 dòng), `platform_core/credit.py`,
`platform_core/models.py`, `platform_core/billing.py`. Bằng chứng E1 trừ chỗ ghi rõ.

## Trang quản trị đang có

Điều hướng khai ở `server/admin.py` dòng 70–83:

| Nhóm | Mục | Đường |
|---|---|---|
| Quản trị | Người dùng | `/admin/user/list` |
| | Sổ credit | `/admin/credit-entry/list` |
| | Cấp credit | `/admin/grant-credit` |
| | APIKEYS | `/admin/apikeys` |
| | Job | `/admin/job/list` |
| | Phiên | `/admin/session/list` |
| Thanh toán | Doanh thu | `/admin/doanh-thu` |
| | Gói nạp | `/admin/goi` |
| | Đơn hàng | `/admin/don` |
| Hệ thống | Tình trạng | `/status` |

Nền tảng là **sqladmin**; `UserAdmin`, `CreditEntryAdmin`, `JobAdmin`,
`SessionAdmin`, `AppAccessAdmin`, `ApiKeyAdmin` là `ModelView`; `GrantCreditView`,
`ApiKeysConsole`, `AddApiKeyView` và trang Doanh thu/Gói/Đơn là `BaseView` tự dựng.

## Quyết định đúng đã có sẵn (giữ nguyên, không đụng)

- `UserAdmin.can_create = False` và `form_columns` **không** chứa `email` hay
  `password_hash`. Email là danh tính; mật khẩu chỉ đổi qua luồng băm đúng cách.
- Sổ credit **append-only**; `cap_tay()` ghi một bút toán `grant`, âm để thu về.
  Không có đường sửa số dư trực tiếp.
- `GrantCreditView` có **CSRF** (`verify_csrf_token`) — đã củng cố ở W1.3.
- Admin là tài khoản trong CSDL; đường admin-từ-biến-môi-trường đã vô hiệu ở
  production (Q29).

## Sự thật đo được trên CSDL production (E2, 2026-08-07)

```
FK tren credit_entries            : KHONG CO
but toan credit tro toi user ma   : 0
   user do KHONG TON TAI
tong but toan kind='grant'        : 12
so tai khoan                      : 10  (10 da xac thuc email)
tong credit trong so              : 1.392
```

**PASS A1:** đã biết trang nào tồn tại, dựng bằng gì, và ràng buộc CSDL thật ra sao.
