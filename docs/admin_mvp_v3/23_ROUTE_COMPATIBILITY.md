# 23 — Tương thích route sau `admin_mvp_v3`

Tài liệu một-trang cho câu hỏi *"URL cũ của tôi còn chạy không?"*

## Câu trả lời ngắn

**Có. Tất cả.**

| | |
|---|---|
| Route bị xoá | **0** |
| URL bị đổi | **0** |
| Redirect thêm vào | **0** |
| URL mới | **3** + `/admin/` lấy lại từ trang index của gói SQLAdmin |

Chốt bằng `tests/test_322_admin_cong_an_toan.py::test_khong_route_admin_nao_bi_xoa`
— danh sách 31 route là **dữ liệu trong test**, không phải một lời hứa trong tài
liệu.

---

## Bảng đầy đủ

Cột **Nav**: `cha` = mục cha ở thanh bên · `con` = mục con · `tab` = tab cấp ba ·
`ctx` = hành động theo ngữ cảnh, không có mục nav · `expl` = khu Data Explorer.

| URL | Còn? | Nav | Mục cha sáng |
|---|---|---|---|
| `/admin/` | ✅ **mới là trang của nền tảng** | cha | Tổng quan |
| `/admin/khach-hang` | 🆕 | cha | Khách hàng |
| `/admin/nguoi-dung` | ✅ | con | Khách hàng |
| `/admin/nguoi-dung/thu-hoi-phien` | 🆕 POST | ctx | Khách hàng |
| `/admin/doanh-thu` | ✅ *(nhãn đổi, URL giữ)* | cha | Tài chính |
| `/admin/don` · `/admin/don/action` | ✅ | con · ctx | Tài chính |
| `/admin/goi` · `/admin/goi/action` | ✅ | con · ctx | Tài chính |
| `/admin/grant-credit` | ✅ | **ctx** *(rời thanh bên)* | Tài chính |
| `/admin/credit-entry/*` | ✅ | con | Tài chính |
| `/admin/api-tong-quan` | ✅ | cha | API Platform |
| `/admin/api-tai-khoan` | ✅ | con | API Platform |
| `/admin/api-khoa` · `-action` | ✅ | tab · ctx | API Platform |
| `/admin/api-cong-cu` | ✅ | con | API Platform |
| `/admin/api-chinh-sach` · `-action` | ✅ | tab · ctx | API Platform |
| `/admin/api-kill-switch` · `-action` | ✅ | **tab** *(rời thanh bên)* · ctx | API Platform |
| `/admin/api-request` | ✅ | con | API Platform |
| `/admin/api-job` · `/admin/api-bao-mat` | ✅ | tab | API Platform |
| `/admin/api-trace` · `-export` | ✅ | ctx | API Platform |
| `/admin/api-gia` · `-action` | ✅ | con · ctx | API Platform |
| `/admin/api-margin` | ✅ | tab | API Platform |
| `/admin/apikeys` | ✅ *(nhãn → Provider Credentials)* | cha | Vận hành |
| `/admin/api-key-them` · `-sua` · `-test` · `-action` | ✅ | ctx | Vận hành |
| `/admin/api-models` · `-refresh` | ✅ | con · ctx | Vận hành |
| `/admin/job/*` | ✅ | con | Vận hành |
| `/admin/he-thong` | 🆕 | cha | Hệ thống |
| `/admin/nhat-ky-admin/*` | ✅ | con | Hệ thống |
| `/admin/nang-cao` | 🆕 | con | Hệ thống |
| `/status` | ✅ | con | Hệ thống |
| `/admin/user/*` | ✅ | expl | Hệ thống |
| `/admin/session/*` | ✅ | expl | Hệ thống |
| `/admin/app-access/*` | ✅ | expl | Hệ thống |
| `/admin/api-key/*` | ✅ | expl | Hệ thống |
| `/admin/platform-info/*` | ✅ | expl | Hệ thống |

---

## Ba thay đổi có thể gây bất ngờ (không phải lỗi)

1. **`/admin/` không còn là trang index của SQLAdmin.** Nó là trang Tổng quan của
   nền tảng, dùng điểm mở rộng chính thức của gói (`Admin.index` — docstring của
   chính gói nói *"can be overridden to create dashboards"*).

2. **`/admin/grant-credit` và `/admin/api-kill-switch` rời thanh bên.** URL vẫn
   mở được. Chúng là **hành động**, không phải nơi chốn — vào từ ngữ cảnh của
   đối tượng bị tác động (Hồ sơ 360, tab Governance).

3. **Thanh bên của SQLAdmin còn 8 mục thay vì 31.** 22 trang nghiệp vụ đặt
   `is_visible = False` — **chỉ ẩn khỏi menu**, route sống nguyên. Thanh bên đó
   nay đúng vai của nó: mục lục khu dữ liệu thô.

---

## Nếu một URL 404 sau deploy

Nó **không** nằm trong kế hoạch. Kiểm theo thứ tự:

1. `grep '@expose("<duong-dan>"' server/admin.py server/admin_api.py server/routes/admin/`
2. Trang mới có được đăng ký chưa: `server/routes/admin/__init__.py:VIEWS`
3. `python -m pytest tests/test_322_admin_cong_an_toan.py -q`
