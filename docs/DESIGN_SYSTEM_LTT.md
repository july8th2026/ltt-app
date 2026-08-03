# LTT Carbon Red — hợp đồng giao diện v1.0

Trạng thái: **đang hiệu lực** từ Q52, ngày 2026-08-03. Đây là nguồn chuẩn cho
mọi trang web và app LTT Studios. `server/static/ltt.css` là bản thực thi token;
tài liệu này mô tả ý nghĩa và điều kiện sử dụng.

## 1. Nguyên tắc

1. Một ngôn ngữ thị giác: nền carbon gần đen, điểm nhấn đỏ LTT, chữ trung tính.
2. Màu trạng thái không dùng làm màu thương hiệu: xanh lá = thành công, vàng =
   cảnh báo/chờ, đỏ sáng = lỗi. Accent đỏ LTT chỉ thể hiện hành động/selection.
3. Một control chỉ có một hành động chính. Tác vụ phá hủy phải có kiểu danger,
   xác nhận và trạng thái không thể bấm lặp.
4. Không đưa control giả hoặc tính năng chưa có backend lên giao diện production.
5. Desktop và mobile dùng cùng semantic token, component và thuật ngữ.

## 2. Token bắt buộc

| Nhóm | Token | Vai trò |
|---|---|---|
| Surface | `--surface-canvas` | nền trang thấp nhất |
| Surface | `--surface-base` | nền shell/header/sidebar |
| Surface | `--surface-raised` | card/panel |
| Surface | `--surface-overlay` | dropdown/modal/popover |
| Border | `--border-subtle`, `--border-strong` | phân cấp đường viền |
| Text | `--text-primary`, `--text-secondary`, `--text-muted` | ba cấp chữ |
| Brand | `--brand-primary`, `--brand-hover`, `--brand-soft` | CTA/active/focus |
| Status | `--status-success`, `--status-warning`, `--status-danger` và các `-soft`, `-border` | trạng thái thật |
| Focus | `--focus-ring`, `--focus-shadow` | keyboard focus nhìn rõ |
| Shape | `--radius-*` | bo góc theo cấp component |
| Motion | `--motion-fast`, `--motion-normal` | chuyển động ngắn, có reduced-motion |

Các alias cũ `--bg`, `--panel`, `--fg`, `--accent` vẫn tồn tại trong giai đoạn
chuyển đổi, nhưng component mới phải dùng token semantic.

## 3. Shell chuẩn

- Logo/brand dẫn về `/`; tên sản phẩm hiện rõ, không dùng emoji làm logo.
- Global navigation chỉ chứa nhóm app và lối vào dùng chung.
- Khu vực tài khoản luôn theo thứ tự: credit → avatar → menu tài khoản.
- App có route con dùng tab cấp hai; app một màn hình không tạo tab thừa.
- Help/status có accessible name; mọi menu đóng được bằng click ngoài và Escape.
- Header không che nội dung, không tạo horizontal overflow tại 390 px.

## 4. Component chuẩn

- Button: primary, secondary/ghost, danger; loading/disabled rõ; không chỉ phân
  biệt bằng màu. Nhãn dùng động từ: “Tạo video”, “Bắt đầu nâng cấp”, “Xuất”.
- Input: có label chương trình được; hint/error gắn qua `aria-describedby`; focus
  không làm layout nhảy. Placeholder không thay label.
- Card: surface raised + border subtle; card có thể bấm phải dùng link/button thật.
- Modal: có title, mô tả tác động/credit, focus trap, Escape và trả focus khi đóng.
- Toast: thông báo phụ; lỗi cần xử lý phải tồn tại trong luồng, không chỉ toast.
- Tabs: tab thật dùng `role=tablist/tab/tabpanel`; filter dùng button/chip.
- Job status: queued/running/succeeded/failed/cancelled; luôn có nhãn chữ.

## 5. Accessibility và responsive

- WCAG 2.2 AA là gate; keyboard focus phải nhìn thấy trên mọi control.
- Touch target hướng tới 44×44 CSS px trên thiết bị coarse pointer; khoảng cách
  không được làm hai mục dễ bấm nhầm.
- Mọi input có accessible name; icon-only control cần `aria-label`.
- Tôn trọng `prefers-reduced-motion`; không dựa riêng vào hover.
- 390 px: không overflow ngang; 1280 px: không che/cắt control quan trọng.

## 6. Icon, chữ và nội dung

- Font UI: Segoe UI/system; dữ liệu kỹ thuật: Cascadia Code/Consolas.
- Emoji hiện hữu là compatibility content, không phải bộ icon chuẩn. Control mới
  dùng SVG nội bộ với `currentColor`, nét/khung nhìn nhất quán và nhãn truy cập.
- Thuật ngữ chuẩn: **Credit**, **Việc**, **Tạo**, **Xuất**, **Thử lại**, **Hủy**,
  **Đang chờ**, **Đang chạy**, **Hoàn tất**, **Lỗi**.
- Không trộn Việt/Anh trong cùng một workflow, ngoại trừ tên model/codec/provider.

## 7. Gate cho từng phase

Mỗi page/app chỉ PASS khi behavior tests và secret scan xanh; browser desktop +
mobile không overflow, console error 0, failed app request 0; keyboard/focus/name
đạt; các state loading/empty/error/disabled/credit được kiểm. Mỗi phase là một
commit/release train riêng và phải có cách rollback trước khi deploy.
