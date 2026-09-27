/** Kiểu dùng chung giữa các mảnh của trình soạn, và hằng số hợp đồng.
 *
 *  ⭐ Chúng ở ĐÂY chứ không trong `EditorShell.tsx` để mỗi mảnh nhập được kiểu
 *     của nó mà không kéo theo cả cây layout — tức không có vòng nhập ngược
 *     (`WorkflowHeader` nhập `EditorShell` nhập `WorkflowHeader`).
 */

//: `apps/agent/routes/workspace.py` chi nhan dung gia tri nay. No khong phai
//  mot che do trinh bay nua — chi la hang so hop dong cua cua `/preferences`.
export const PHIEN_BAN_TRINH_BAY = 'creative-v1' as const

/** Pha của vòng lưu — huy hiệu "Đã lưu / Đang lưu… / Xung đột / Lỗi lưu". */
export type PhaLuu = 'loading' | 'ready' | 'saving' | 'saved' | 'conflict' | 'error'

/** Ngăn kéo đang mở trên desktop. `null` = không ngăn nào. */
export type NganDesktop = 'tools' | 'workspace' | 'run' | 'inspector' | null

/** Khu vực đang xem trên màn hẹp. */
export type KhuMobile = 'canvas' | 'palette' | 'inspector'

/** Menu ngữ cảnh đang mở: ở khoảng trống hay trên một node. */
export type MenuNguCanh = { kind: 'pane' | 'node'; x: number; y: number
  flow: { x: number; y: number }; nodeId?: string }

export type GiaoDien = 'light' | 'dark'
