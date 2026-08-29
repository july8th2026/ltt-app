# 18 — Cổng An toàn / Tiền / Audit

MODE: RELEASE GATE. Không làm tính năng.
Bằng chứng máy chạy: `tests/test_322_admin_cong_an_toan.py` (8 phép kiểm).

---

## 1. Quyền truy cập

| Vai | Kết quả | Bằng chứng |
|---|---|---|
| ẩn danh | 302/303 → `/login` cho **mọi** trang admin | `test_205::test_a_signed_out_visitor_reaches_no_admin_page` |
| khách đã đăng nhập (role=user) | bị chặn | `test_205::test_an_ordinary_customer_reaches_no_admin_page`; `test_70::test_admin_chi_cho_role_admin` |
| admin (role trong CSDL) | vào được | các test lô |

Cổng quyền **không đổi** trong đợt này: `AdminAuth.authenticate` vẫn uỷ quyền cho
`server.deps.is_operator` (`server/admin.py:83–97`). Không nới, không thêm đường
vào thứ hai.

---

## 2. CSRF — **12/12**

Mọi handler `POST` trong `server/admin.py` + `server/admin_api.py` gọi
`verify_csrf_token` trước khi làm bất cứ việc gì.

| Route | CSRF |
|---|---|
| `/nguoi-dung/thu-hoi-phien` *(mới)* | ✅ |
| `/grant-credit` | ✅ |
| `/api-key-them` · `/api-key-sua` · `/api-key-action` | ✅ |
| `/goi` · `/goi/action` | ✅ |
| `/don/action` | ✅ |
| `/api-khoa-action` · `/api-chinh-sach-action` · `/api-kill-switch-action` · `/api-gia-action` | ✅ |

`test_322::test_moi_thao_tac_ghi_deu_kiem_csrf` quét **tự động** — thêm một POST
mới mà quên CSRF là gate đỏ, không phải là một lần rà bằng mắt.

---

## 3. Nhật ký admin — **12/12** (trước đợt: 5/11)

| Route | Trước | Sau |
|---|---|---|
| `/grant-credit` | ✅ | ✅ |
| `/api-khoa-action` · `/api-chinh-sach-action` · `/api-kill-switch-action` · `/api-gia-action` | ✅ | ✅ |
| **`/don/action`** (mark-paid — TIỀN) | ❌ | ✅ `xac_nhan_don_da_tra` |
| `/goi` · `/goi/action` (giá bán) | ❌ | ✅ `them_goi_nap` · `goi_nap_bat_tat` · `xoa_goi_nap` |
| `/api-key-them` · `/api-key-sua` · `/api-key-action` | ❌ | ✅ `them_provider_credential` · `sua_provider_credential` · `provider_key_<op>` |
| `/nguoi-dung/thu-hoi-phien` *(mới)* | – | ✅ `thu_hoi_phien` |

⛔ **Không bao giờ ghi giá trị credential**, chỉ ghi **việc** có xoay hay không
(`sua_provider_credential` → `"gemini | credential DA XOAY"`).

Việc này vượt ra ngoài `05` Phần III (xếp là PROPOSAL). Lý do và giao thức sửa
hợp đồng ghi ở `08_LO_C1_C10.md` §"Sửa hợp đồng".

---

## 4. Bất biến tiền

| Bất biến | Trạng thái | Bằng chứng |
|---|---|---|
| Sổ credit **append-only** | ✅ giữ nguyên `can_create/edit/delete = False` | `test_322::test_so_credit_van_append_only_o_tang_model_view` |
| Sổ credit không có nút tạo/sửa/xoá trên UI | ✅ | `test_320::test_so_credit_van_la_chi_doc` |
| Mark-paid **idempotent** | ✅ bấm hai lần cộng đúng một lần | `test_320::test_gj5_mark_paid_cong_credit_dung_mot_lan_va_noi_ro_ket_qua` |
| Mark-paid đi qua **đúng một đường** | ✅ handler gọi `billing.ghi_nhan_tra`, **không** gọi `credit.nap`/`cap_tay` | `test_322::test_mark_paid_van_di_qua_duong_idempotent` |
| Cấp credit ghi bút toán mới, không sửa lịch sử | ✅ `credit.cap_tay` | `test_162` |
| Lịch sử đơn không bị viết lại | ✅ `price_vnd`/`credits`/`bonus_percent` chốt lúc tạo đơn | `models.py:753` |
| **Đơn vị tiền không trộn** | ✅ VND ghi `đ`, credit ghi `credit`, hai cột riêng | `test_318::test_danh_sach_khach_hang_...`; ma trận ở `05` P4 |

⭐ Điểm cuối là một thay đổi so với ảnh mockup, không phải so với mã: ảnh ghi
"Số dư credit **512.600 đ**" và cột "Credits +179.000" cạnh "Số tiền 179.000 đ".
Tỉ giá nền tảng là 1 credit = 100 đ, nên bê nhãn của ảnh vào là **sai số hiển thị
100 lần**.

---

## 5. Bất biến secret

| Secret | Quy tắc | Trạng thái |
|---|---|---|
| Token phiên (`DbSession.id` — PK **chính là** token cookie) | không bao giờ render | ✅ giữ nguyên; bảng phiên mới ở Hồ sơ 360 cố ý chỉ có `created_at`/`expires_at`/`ip`/`user_agent` |
| `ApiKey.credential_enc` | không render, không vào `form_columns`, **không vào nhật ký** | ✅ |
| Khoá API của khách | masked, không tái tạo được | ✅ |
| `password_hash` | không có trong `column_list` | ✅ |

`test_322::test_khong_secret_nao_bi_render` quét mã: `credential_enc` và
`password_hash` không được xuất hiện trong bất kỳ chuỗi f-string nào.

---

## 6. UX nguy hiểm — thiết kế lại **không** làm loãng ràng buộc

| Kiểm | Kết quả |
|---|---|
| Kill switch vẫn là **form có ô lý do bắt buộc**, không phải toggle | ✅ `test_322::test_kill_switch_van_doi_ly_do_o_tang_service` |
| `reason` vẫn bắt buộc ở **tầng service**, không bị đẩy lên UI | ✅ `policy.py` + `public_api/tables.py` |
| Mark-paid có xác nhận nêu rõ số credit sẽ cộng | ✅ |
| Thu hồi phiên có xác nhận nêu rõ hệ quả | ✅ |
| Hành động nguy hiểm **không** dồn chung hàng với thao tác đọc | ✅ `test_319::test_hanh_dong_nguy_hiem_khong_dung_chung_hang_voi_thao_tac_doc` |
| Danh sách khách hàng **không** chứa mutation | ✅ `test_318::test_bang_danh_sach_khong_chua_mutation` |

🔴 **Ảnh mockup vẽ kill switch là ba toggle, mỗi cái kèm ba dòng meta rỗng**
("Lý do —", "Hết hiệu lực —", "Thực hiện bởi —"). Đọc ngược: ba dòng đó chính là
ba **trường bắt buộc** backend đòi. Làm theo ảnh ⇒ hành động **luôn thất bại** ở
`_require_reason`. Đây là cái bẫy prompt 14 cảnh báo, và nó có thật.

---

## 7. Tương thích route — 0 mất mát

`test_322::test_khong_route_admin_nao_bi_xoa` chốt danh sách 31 route.
Redirect thêm vào: **0**. URL đổi: **0**. URL mới: **3**
(`/admin/khach-hang`, `/admin/he-thong`, `/admin/nang-cao`) + `/admin/` được lấy
lại từ trang index của gói SQLAdmin.

---

## 8. Cổng sự thật dữ liệu (thêm mới — bộ prompt gốc không có)

`test_317_admin_nav_contract.py` đọc **bảng §2 của `06b_SO_DANG_KY_NOI_DUNG_CAM.md`
như dữ liệu** và grep mọi template admin. 30 mẫu `AUTO`.

Các lô còn kiểm trên **trang đã render** (khác với grep template — một chuỗi vẫn
có thể lọt qua f-string trong Python):
`test_319::test_khong_bia_du_lieu_ho_so_khach` ·
`test_320::test_don_khong_co_cot_goi_dich_vu` ·
`test_320::test_tong_quan_tai_chinh_khong_bia_kenh_thanh_toan` ·
`test_321::test_tong_quan_khong_bia_chi_so` ·
`test_318::test_rail_chu_y_chi_dem_tin_hieu_don_dinh`.

### Rà bằng mắt các mẫu `MẮT`

| Mẫu | Kết quả |
|---|---|
| Starter/Pro/Business làm **bậc thuê bao** | không xuất hiện |
| `còn * ngày`, `Object Storage`, `Worker */ *`, `Routing *%` | không xuất hiện |
| `Error rate` dạng % | không xuất hiện |
| nút "Xem payload" / export cURL dựng lại body | không thêm |
| chip môi trường "Production" | **không dựng** (nền tảng không có nhiều môi trường) |
| chuông thông báo có số đếm | **không dựng** (không có hàng đợi thông báo cho admin) |
| ảnh đại diện khách hàng | **không dựng** (`User` không có trường avatar) |

---

## 9. Kết luận cổng

**PASS.**

Không tìm thấy hồi quy nào về quyền, CSRF, tiền, secret hay audit. Ba chỉ số an
toàn **tốt hơn** trước đợt: audit 5/11 → 12/12, một thao tác an ninh (thu hồi
phiên) chuyển từ "xoá dòng trong bảng thô, không dấu vết" thành hành động có ngữ
cảnh + xác nhận + nhật ký, và một lỗi cache-bust P1 đã sửa.
