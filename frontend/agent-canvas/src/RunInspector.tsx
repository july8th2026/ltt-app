import JsonView from '@uiw/react-json-view'
import type { RunV3 } from './workflowApi'

/** Dữ liệu THÔ của lượt chạy — cây JSON, và ⭐ GẬP LẠI.
 *
 * ## Vì sao tệp này còn sống sau khi có Node Execution Inspector
 *
 * Bản đầu (task A5) mở panel này vì `RunV3Panel` bỏ hẳn `su_kien[].du_lieu` và
 * phần lớn trường của `RunV3Node`. Cách chữa ấy đúng hướng nhưng sai mức: nó
 * đổ CẢ gói vào hai cây JSON, nên mọi trường "có trên màn hình" mà ⛔ không
 * trường nào đọc được (`01_CURRENT_UI_AUDIT.md §6.1`).
 *
 * Giờ `features/editor/ExecutionPanel/NodeExecutionInspector.tsx` trình bày 12
 * trường của `§8` CÓ NHÓM, cho từng bước. Cây thô ở đây ⛔ không còn là bề mặt
 * chính — nó là **lối thoát cho người đi gỡ lỗi**, nằm sau một `<summary>`:
 *
 *   - `du_lieu` của một sự kiện là payload TỰ DO (mỗi `loai` một hình dạng,
 *     đã qua `job_events.redact_details`). ⛔ Không có lược đồ nào để bày nó
 *     thành trường có tên, nên một cây JSON là câu trả lời đúng cho nó.
 *   - Khi một trường ở Inspector hiện "chưa có cửa dữ liệu", đây là chỗ kiểm
 *     chứng được rằng nó thật sự không có trong gói, ⛔ không phải bị giao diện
 *     đánh rơi.
 *
 * ⭐ DỮ LIỆU ĐÃ CÓ TRONG `RunV3` — không gọi thêm một cửa máy chủ nào.
 */
export function RunInspector({ run }: { run: RunV3 | null }) {
  if (!run) return null
  return (
    <details className="run-v3-inspector">
      <summary>Dữ liệu thô của lượt chạy</summary>
      <section aria-label="Inspector lượt chạy">
        <h4>Node</h4>
        <JsonView value={{ nodes: run.nodes }} collapsed={1} />
        <h4>Log sự kiện</h4>
        <JsonView value={{ su_kien: run.su_kien }} collapsed={1} />
      </section>
    </details>
  )
}
