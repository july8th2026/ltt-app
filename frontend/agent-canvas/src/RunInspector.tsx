import JsonView from '@uiw/react-json-view'
import type { RunV3 } from './workflowApi'

/** Inspector THÔ cho một lượt chạy: node + log sự kiện, qua
 *  `@uiw/react-json-view` (spec P-A task A5).
 *
 * ⭐ DỮ LIỆU ĐÃ CÓ TRONG `RunV3` — không gọi thêm một cửa máy chủ nào.
 *   `RunV3Panel` chỉ vẽ một bảng PHẲNG (node_id/trạng thái/credit/lỗi) và
 *   MỘT dòng văn bản cho mỗi sự kiện (`loai · node_id`); nó bỏ hẳn
 *   `du_lieu`/`created_at` của sự kiện và mọi trường khác của node
 *   (`job_id`, `attempt`, `waiting_kind`, `het_han`…). Panel này chỉ mở đúng
 *   phần bị bỏ đó ra — dây nối, không phải tính năng mới.
 */
export function RunInspector({ run }: { run: RunV3 | null }) {
  if (!run) return null
  return (
    <section className="run-v3-inspector" aria-label="Inspector lượt chạy">
      <h3>Node — input/output thô</h3>
      <JsonView value={{ nodes: run.nodes }} collapsed={1} />
      <h3>Log sự kiện</h3>
      <JsonView value={{ su_kien: run.su_kien }} collapsed={1} />
    </section>
  )
}
