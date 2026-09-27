import { useState } from 'react'
import type { RunV3 } from './workflowApi'
import { RUN_V3_KET_THUC } from './workflowApi'
import { dungCacBuoc, suKienCuoi } from './features/editor/ExecutionPanel/buocCuaRun'
import { NhatKyRun } from './features/editor/ExecutionPanel/NhatKyRun'
import { NodeExecutionInspector } from './features/editor/ExecutionPanel/NodeExecutionInspector'
import { Timeline } from './features/editor/ExecutionPanel/Timeline'
import { gio, thoiLuong } from './features/editor/ExecutionPanel/thoiGian'

// Nhan tieng Viet cho trang thai NODE (spec §5.3). Trang thai RUN de nguyen
// chu HOA: no la hop dong voi may chu, va bang nay chi doi ten cho nguoi doc.
// ⭐ Xuat ra: huy hieu trang thai tren NODE (`hooks/useDisplayGraph.ts`) doc
//    cung bang nay. Hai bang song song thi mot hom nao do mot trang thai co
//    hai ten.
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

const BANG_NHAN = { trangThai: NHAN_TRANG_THAI_NODE, waiting: NHAN_WAITING_KIND }

type Props = {
  run: RunV3 | null
  onCancel: () => void
  /** Task A1 (spec §14, `runs_v3.py::v3_chay_lai_tu_node`). Tuỳ chọn: panel vẫn
   *  dùng được (ví dụ trong test) mà không cần dây nối chạy-lại. */
  onChayLaiTu?: (nodeId: string) => void
  /** `node_id` -> TÊN BƯỚC, dựng từ đồ thị đang mở (`graph.ts::nhanNode`).
   *
   *  ⚠️ Tuỳ chọn, và lối lui là `Bước N` — ⛔ KHÔNG phải `node_id`. Panel này
   *     render được ngoài trình soạn (hộp thử, Storybook, phép kiểm), và ở đó
   *     không có đồ thị; lùi về `node_id` thô là quay lại đúng con bọ đang gỡ.
   */
  tenBuoc?: (nodeId: string) => string
  /** `node_id` -> tham số khai trong đồ thị — trường "Đầu vào" của Inspector. */
  thamSo?: (nodeId: string) => Record<string, unknown> | undefined
  /** `node_id` -> `output_ref`, chỉ có sau khi mở cửa "So sánh". */
  dauRa?: (nodeId: string) => Record<string, unknown> | undefined
}

/** Mặt THỰC THI của một lượt chạy: tóm tắt · dòng thời gian theo bước ·
 *  Inspector cho bước đang chọn · nhật ký có dấu thời gian.
 *
 *  ## ⭐ Ba thay đổi so với bản bảng phẳng, và vì sao
 *
 *  1. **Cột đầu là TÊN BƯỚC** (`Timeline.tsx`). `node_id` thô đi vào phần "Chi
 *     tiết kỹ thuật" của Inspector.
 *  2. **Nhật ký có giờ** (`NhatKyRun.tsx`) — `created_at` vốn đã nằm trong gói.
 *  3. **Bấm một bước mở Inspector 12 trường CÓ NHÓM**
 *     (`NodeExecutionInspector.tsx`), thay một cây JSON thô.
 *
 *  `buocCuaRun.ts` ghi rõ trường nào thật sự có cửa dữ liệu và trường nào chưa
 *  — đọc chú thích ở đó trước khi "sửa" một ô đang trống.
 */
export function RunV3Panel(p: Props) {
  const [dangChon, setDangChon] = useState('')
  if (!p.run) return null
  const run = p.run
  const xong = RUN_V3_KET_THUC.has(run.status)
  const cuoi = xong ? suKienCuoi(run) : null
  const buoc = dungCacBuoc(run, BANG_NHAN,
    { tenBuoc: p.tenBuoc, thamSo: p.thamSo, dauRa: p.dauRa })
  // ⭐ Nhat ky dung CUNG bang ten voi dong thoi gian — ke ca loi lui `Bước N`.
  //    Tra lai `p.tenBuoc` o day thi mot node khong co nhan se hien `node_id`
  //    tho trong nhat ky du dong thoi gian da goi no la `Bước 3`: hai ten cho
  //    mot buoc, trong cung mot ngan keo.
  const tenTheoId = new Map(buoc.map(b => [b.nodeId, b.ten]))
  // Lui ve `node_id` CHI cho id khong thuoc do thi nay (run con, node da xoa
  // giua hai version) — o do khong co "Bước N" nao dung.
  const tenBuoc = (nodeId: string) => tenTheoId.get(nodeId) ?? nodeId
  // Bước đang mở. Chọn rồi mà bước biến mất (đổi version, chạy lại) ⇒ quay về
  // "chưa chọn", ⛔ không giữ một Inspector rỗng treo lại.
  const buocChon = buoc.find(b => b.nodeId === dangChon) ?? null
  return (
    <section className="run-v3" aria-label="Lượt chạy">
      <header>
        <strong data-run-status={run.status}>{run.status}</strong>
        <span>{run.credit_charged}/{run.credit_max} credit</span>
        <span className="run-v3-thoi-gian">
          Bắt đầu {gio(run.created_at)}
          {cuoi && <> · Kết thúc {gio(cuoi.created_at)}</>}
          {cuoi && !!thoiLuong(run.created_at, cuoi.created_at) &&
            <> · {thoiLuong(run.created_at, cuoi.created_at)}</>}
        </span>
        {!xong && <button onClick={p.onCancel}>Hủy chạy</button>}
      </header>
      <Timeline buoc={buoc} dangChon={dangChon} xong={xong}
        onChayLaiTu={p.onChayLaiTu}
        chon={nodeId => setDangChon(truoc => truoc === nodeId ? '' : nodeId)}/>
      {buocChon && <NodeExecutionInspector buoc={buocChon}/>}
      <NhatKyRun suKien={[...run.su_kien].sort((a, b) => a.seq - b.seq)}
        tenBuoc={tenBuoc}/>
    </section>
  )
}
