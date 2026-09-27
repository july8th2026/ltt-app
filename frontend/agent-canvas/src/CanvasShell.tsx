/** Điểm vào của trình soạn. Thân đã tách sang `features/editor/` (làn UI-3).
 *
 *  ⭐ VÌ SAO GIỮ TỆP NÀY thay vì đổi mọi lời gọi: `main.tsx` và toàn bộ phép
 *     kiểm hiện có nhập `./CanvasShell`. Giữ MỘT dòng ở đây làm lần tách này
 *     đọc được trong `git diff` như một lần DI CHUYỂN — nếu cùng lúc đổi cả
 *     đường nhập thì không ai phân biệt được "đã dời" với "đã sửa".
 *
 *  Bản đồ: `features/editor/EditorShell.tsx` là bố cục; trạng thái ở
 *  `features/editor/hooks/`; phép biến đổi đồ thị thuần ở
 *  `features/editor/graph.ts`.
 */
export { CanvasShell } from './features/editor/EditorShell'
