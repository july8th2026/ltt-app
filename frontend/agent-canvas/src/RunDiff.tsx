import { diff } from 'jsondiffpatch'
import { format, type Op } from 'jsondiffpatch/formatters/jsonpatch'
import type { SoSanhRunV3 } from './workflowApi'

/** So sánh HAI lượt chạy (spec §14, `runs_v3.py::v3_so_sanh_run`, task A2).
 *
 * ⭐ Diff CHI TIẾT tính ở CLIENT bằng `jsondiffpatch`, ⛔ không phải máy chủ:
 *   `_nodes_so_sanh`/`v3_so_sanh_run` chỉ trả tập NODE lệch (`khac`) — "máy
 *   không tô màu, không xếp hạng; UI diff là việc của Canvas" (chú thích ở
 *   route). `format(diff(a, b))` (bộ định dạng `jsonpatch` có sẵn của thư
 *   viện, KHÔNG tự viết lại) biến khác biệt thành một danh sách
 *   {op, path, value} đọc được — đúng phần Canvas phải làm.
 */
export function RunDiff({ soSanh }: { soSanh: SoSanhRunV3 }) {
  const delta = diff(soSanh.a, soSanh.b)
  const ops: Op[] = delta ? format(delta) : []
  return (
    <section className="run-diff" aria-label="So sánh lượt chạy">
      <header>
        <strong>{soSanh.a.id} → {soSanh.b.id}</strong>
        {soSanh.khac_version && <span className="run-diff-version">Khác version</span>}
      </header>
      {!!soSanh.khac.length &&
        <p className="run-diff-nodes">Node lệch: {soSanh.khac.join(', ')}</p>}
      {!ops.length
        ? <p className="run-diff-empty">Không có khác biệt.</p>
        : <ul>{ops.map((op, i) => (
            <li key={i} data-op={op.op}>
              <code>{op.op}</code> <code>{op.path}</code>
              {op.op !== 'remove' &&
                <span> → {JSON.stringify((op as { value: unknown }).value)}</span>}
            </li>
          ))}</ul>}
    </section>
  )
}
