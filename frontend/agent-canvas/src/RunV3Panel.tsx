import type { RunV3 } from './workflowApi'
import { RUN_V3_KET_THUC } from './workflowApi'

// Nhan tieng Viet cho trang thai NODE (spec §5.3). Trang thai RUN de nguyen
// chu HOA: no la hop dong voi may chu, va bang nay chi doi ten cho nguoi doc.
// ⭐ Xuat ra: huy hieu trang thai tren NODE (`NodeKhung`) doc cung bang nay.
//    Hai bang song song thi mot hom nao do mot trang thai co hai ten.
export const NHAN_TRANG_THAI_NODE: Record<string, string> = {
  PENDING: 'Chờ', READY: 'Sẵn sàng', QUEUED: 'Đã xếp hàng', RUNNING: 'Đang chạy',
  WAITING: 'Đang chờ tín hiệu', RETRY_SCHEDULED: 'Sẽ thử lại',
  SUCCEEDED: 'Xong', FAILED: 'Hỏng', SKIPPED: 'Bỏ qua',
  CANCELLED: 'Đã hủy', ABANDONED: 'Bỏ dở',
  // P9 task 3 (🔴): KHÔNG dùng nhãn "Chờ" cho trạng thái này — nó KHÔNG phải
  // PENDING, nó là "ta không biết", và hai câu đó phải đọc khác nhau trên
  // Canvas (xem `runs_v3.py::TRANG_THAI_KHONG_XAC_DINH`).
  KHONG_XAC_DINH: 'Không xác định (vòng lặp lồng sâu)',
}

// `waiting_kind` (khớp nguyên `Waitpoint.kind`, `runs_v3.py::_waiting_kind`)
// -> nhãn tiếng Việt cho NGƯỜI xem. Thêm P9 task 3 mở rộng: một node WAITING
// vì đang chờ NGƯỜI DUYỆT không được hiện giống một node WAITING vì webhook
// chưa tới hay một run con chưa xong.
export const NHAN_WAITING_KIND: Record<string, string> = {
  HUMAN: 'chờ người duyệt', WEBHOOK: 'chờ webhook', DELAY: 'đang hẹn giờ',
  JOB: 'chờ job', CHILD_RUN: 'chờ run con', BARRIER: 'chờ đủ nhánh',
}

export function RunV3Panel({ run, onCancel }: {
  run: RunV3 | null; onCancel: () => void }) {
  if (!run) return null
  const xong = RUN_V3_KET_THUC.has(run.status)
  return (
    <section className="run-v3" aria-label="Lượt chạy">
      <header>
        <strong data-run-status={run.status}>{run.status}</strong>
        <span>{run.credit_charged}/{run.credit_max} credit</span>
        {!xong && <button onClick={onCancel}>Hủy chạy</button>}
      </header>
      <table>
        <tbody>
          {run.nodes.map(n => (
            <tr key={n.node_id} data-node-status={n.status}
               data-waiting-kind={n.waiting_kind || undefined}>
              <td>{n.node_id}</td>
              <td>
                {NHAN_TRANG_THAI_NODE[n.status] ?? n.status}
                {n.status === 'WAITING' && n.waiting_kind &&
                  <> ({NHAN_WAITING_KIND[n.waiting_kind] ?? n.waiting_kind})</>}
              </td>
              <td>{n.cost_credit}</td>
              <td>{n.error}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <ol className="run-v3-su-kien">
        {run.su_kien.map(e => (
          <li key={e.seq}>{e.loai}{e.node_id ? ` · ${e.node_id}` : ''}</li>
        ))}
      </ol>
    </section>
  )
}
