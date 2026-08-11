# H32.5 — Benchmark theo ảnh giao diện

`GiaoDien.png` là ảnh tham khảo E0, không chứng minh backend. Vòng này không
browse/thử sản phẩm khác vì MoTa khóa visual-only; market benchmark chính thức
vẫn là hồ sơ 2026-08-09.

| Thành phần ảnh chuẩn | LTT hiện tại | Quyết định |
|---|---|---|
| Nav app icon-only | Có nav gọn | KEEP; không thêm Prompt/Settings giả |
| Composer trái | Có đầy đủ và real | RESTYLE hierarchy |
| 3 model cards | Có đúng 3 model | KEEP |
| Prompt + history + translation | Có | KEEP |
| Ảnh/video/audio reference | Có | KEEP; audio vẫn blocker backend |
| Asset ID/saved asset | Có owner-scoped reuse | RESTYLE collapsed |
| Duration/aspect/resolution/count/audio | Có, capability dependent | KEEP |
| Quote + Create luôn thấy | Trước sửa dưới fold | FIXED |
| History tabs + grid/list/filter | Có | RESTYLE/i18n |
| Running/done/error cards | Có | RESTYLE |
| Select all/delete/retry card | Backend chưa đủ | REJECT fake; BUILD sau contract |
| Template library | Chưa có | DEFER tới khi có value/contract |
| Global platform header | Ảnh không có | KEEP có chủ đích để nhất quán control plane |

Điểm tinh túy lấy từ ảnh là mô hình `compact composer + outcome-first library`,
không phải sao chép mọi nút. Những control không có ownership/error/credit/log
contract không được đưa lên UI.
