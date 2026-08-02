# UI-RD — Trang chủ `/`

**Trạng thái:** BUILD — logic đã khóa ngày 2026-08-02  
**Ảnh tham khảo:** `TRANGCHU.png` (1672×937)  
**Màn hình ảnh mô tả:** marketplace/workspace đã đăng nhập, desktop  
**Nguồn sự thật nghiệp vụ:** `server/routes/dashboard.py`, registry app, Q30/Q45

## Mục tiêu

Thiết kế lại trang chủ LTT AI Studio theo bố cục marketplace đậm đặc của ảnh,
nhưng chỉ hiển thị dữ liệu, quyền và trạng thái job có thật. Không thay hợp đồng
catalog công khai Q30 nếu Dev chưa chọn rõ phương án khác.

## Baseline đã kiểm

- Production public desktop 1440×1000: `/` 200, 9 app, ba cột ~383 px, console
  0 error/0 warning, 0 failed request không mong đợi.
- Production public mobile 390×844: `scrollWidth=438`, `clientWidth=390` — tràn
  ngang thật. Search rộng 340 px, filter rộng 385.8 px, grid/card 390 px.
- Browser search `video` lọc đúng 4 app video. Bộ lọc theo group hiện có, là
  client-side, không có sort/global command palette.
- Không có session authenticated hợp lệ để quan sát dữ liệu riêng; source cho thấy
  header có credit/avatar và `/jobs`, `/settings`, `/status`, nhưng `/` không có
  recent activity, running-job rail, favorites/My Apps hay entitlement Pro.

## Logic cần Dev khóa

## Decision Gate đã khóa

| Mã | Dev chọn | Logic thực thi |
|---|---|---|
| 1 | B | Catalog công khai cho khách, marketplace workspace riêng cho user đăng nhập |
| 2 | C | Dựng đủ bố cục reference; feature không có backend chỉ hiện disabled/hoãn rõ ràng |
| 3 | B → điều chỉnh thực thi | Artwork crop từ ảnh tham khảo do Dev cung cấp; không gọi ImageGen thêm |
| 4 | B | Header ngang giữ cho app khác; home authenticated dùng sidebar workspace |
| 5 | A | Recent Activity/Running Jobs lấy dữ liệu job owner-scoped thật |
| 6 | A | Chỉ credit/nạp credit, không giả Pro membership |
| 7 | B | Popular sort dùng aggregate job theo slug, không lộ/hiển thị số giả |
| 8 | B | Deploy production sau tất cả gate test/browser/release PASS |
