import { useState } from 'react'
import type { RunV3 } from '../../../workflowApi'

/** Cửa DUYỆT/TỪ CHỐI cho một bước `core.human` đang `WAITING` (lan UI-8a).
 *
 *  ## Vì sao thành phần này TỰ ĐỨNG, không nhận `csrfToken`/`onDuyet` từ trên
 *
 *  Mọi hành động khác của ngăn kéo này (`chayWorkflow`, `huyRun`,
 *  `chayLaiTuNode`…) được `EditorShell.tsx` bọc sẵn CSRF rồi truyền xuống như
 *  một hàm không tham số. Nhưng tệp SỞ HỮU của làn này chỉ là
 *  `ExecutionPanel/**` (+ sửa `index.tsx` TỐI THIỂU) — `EditorShell.tsx` và
 *  `hooks/useWorkflowRun.ts` thuộc làn khác. Thêm một prop mới ở đó là sửa một
 *  tệp ngoài danh sách được giao.
 *
 *  ⇒ Thành phần này tự đọc CSRF từ DOM — CÙNG một chỗ mà `EditorShell.tsx`
 *     đọc (`#agent-canvas-root` `data-csrf-token`, xem `EditorShell.tsx:52`)
 *     — và tự gọi cửa HTTP của chính nó (`phe_duyet_v3.py`). Đây là MỘT cửa
 *     ngoài `workflowApi.ts` (tệp đó là sổ dùng chung **S4**, ⛔ không sửa),
 *     đổi lại cho một ranh giới sở hữu tệp rõ ràng hơn.
 *
 *  ## Vì sao KHÔNG có nút "Sửa" (modify)
 *
 *  `03_CREWAI_BENCHMARK.md §7` đề cập CrewAI AMP có `approve/modify/reject`.
 *  Bối cảnh của lan UI-8a (đọc ở đầu phiên) khai rõ CHỈ hai nhánh
 *  (`NHANH_HUMAN = ("approve", "reject")`) — thêm "modify" là mở một luồng dữ
 *  liệu mới (workflow phải hiểu "input đã sửa") mà `core.human` hôm nay không
 *  có cổng nào nhận. Ngoài phạm vi cửa này.
 */

type Props = {
  run: RunV3 | null
  /** Tên bước hiển thị — cùng hàm `nhanNode` mà toàn bộ ngăn kéo dùng. */
  tenBuoc: (nodeId: string) => string
  /** Tham số KHAI trong đồ thị (bản đang soạn) — dùng để đọc `cau_hoi` và chế
   *  độ `het_han` của CHÍNH node `core.human` đó. ⚠️ Đây là tham số của bản
   *  ĐANG SOẠN, không phải của phiên bản đã publish mà run đang chạy — nếu
   *  workflow bị sửa tiếp sau khi run bắt đầu, câu hỏi hiện ra có thể lệch
   *  một chút so với câu hỏi máy chủ đã hỏi. Xem báo cáo cuối làn UI-8a. */
  thamSo: (nodeId: string) => Record<string, unknown> | undefined
}

//: Danh sách ĐÓNG — khớp NGUYÊN `han_cho.CHE_DO_HET_HAN` phía máy chủ. Một
//  chuỗi lạ ở `het_han` không được để lọt qua thành một câu vô nghĩa.
const NHAN_HET_HAN: Record<string, string> = {
  fail: 'sẽ đánh dấu bước này LỖI',
  route: 'sẽ đi theo nhánh "hết hạn" riêng',
  approve: 'sẽ tự động DUYỆT',
  reject: 'sẽ tự động TỪ CHỐI',
}

function nhanHetHan(cheDoTho: unknown): string {
  const cheDo = typeof cheDoTho === 'string' && cheDoTho ? cheDoTho : 'reject'
  return NHAN_HET_HAN[cheDo] ?? NHAN_HET_HAN.reject
}

function docCsrf(): string {
  return document.querySelector<HTMLElement>('#agent-canvas-root')?.dataset.csrfToken ?? ''
}

async function guiQuyetDinh(runId: string, nodeId: string,
                            quyetDinh: 'approve' | 'reject'): Promise<string> {
  const csrf = docCsrf()
  const res = await fetch(
    `/agent/api/v3/runs/${encodeURIComponent(runId)}/nodes/${encodeURIComponent(nodeId)}/duyet`,
    { method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
      body: JSON.stringify({ quyet_dinh: quyetDinh, csrf_token: csrf }) })
  if (res.ok) return ''
  let thongDiep = `Máy chủ trả lỗi ${res.status}.`
  try {
    const than = await res.json() as { detail?: { thong_diep?: string; ma?: string } }
    if (than?.detail?.thong_diep) thongDiep = than.detail.thong_diep
    else if (than?.detail?.ma) thongDiep = `Lỗi: ${than.detail.ma}`
  } catch {
    // Thân không phải JSON — giữ câu chung ở trên.
  }
  return thongDiep
}

/** Một bước ĐANG chờ người duyệt: câu hỏi, hạn, hai nút. */
function TheDuyet({ runId, nodeId, ten, caseHoi, hetHan }: {
  runId: string; nodeId: string; ten: string; caseHoi: string; hetHan: string }) {
  const [dangGui, setDangGui] = useState<'approve' | 'reject' | ''>('')
  const [loi, setLoi] = useState('')

  const bam = async (quyetDinh: 'approve' | 'reject') => {
    setDangGui(quyetDinh)
    setLoi('')
    const thongDiepLoi = await guiQuyetDinh(runId, nodeId, quyetDinh)
    setDangGui('')
    // Không tự xoá thẻ khi thành công: `run` (prop) chỉ đổi khi vòng poll/SSE
    // của `useWorkflowRun` (làn khác, tệp ngoài sở hữu) nạp lại — thẻ tự biến
    // mất ở lần render kế tiếp khi `waiting_kind` không còn 'HUMAN'.
    if (thongDiepLoi) setLoi(thongDiepLoi)
  }

  return (
    <div className="run-cho-nguoi-duyet" data-duyet-node={nodeId}>
      <strong>{ten || nodeId}</strong>
      <p>{caseHoi || 'Bước này cần một người xem lại rồi quyết định.'}</p>
      <small data-duyet-het-han>Hết hạn chờ: {hetHan}.</small>
      <div className="run-cho-nguoi-duyet-nut">
        <button type="button" data-duyet-hanh-dong="approve"
          disabled={dangGui !== ''}
          aria-busy={dangGui === 'approve' || undefined}
          onClick={() => void bam('approve')}>
          {dangGui === 'approve' ? 'Đang gửi…' : 'Duyệt'}
        </button>
        <button type="button" data-duyet-hanh-dong="reject"
          disabled={dangGui !== ''}
          aria-busy={dangGui === 'reject' || undefined}
          onClick={() => void bam('reject')}>
          {dangGui === 'reject' ? 'Đang gửi…' : 'Từ chối'}
        </button>
      </div>
      {loi && <span className="run-error" role="alert">{loi}</span>}
    </div>
  )
}

/** `waiting_kind` là chuỗi nối dấu `,` (`runs_v3.py::_waiting_kind`) — một
 *  node có thể chờ ĐỒNG THỜI nhiều loại (N-of-M chưa đủ). Tách ra để so khớp
 *  từng phần tử, ⛔ không `=== 'HUMAN'` (sẽ bỏ sót ca `"HUMAN,WEBHOOK"`). */
function coCho(waitingKind: string, loai: string): boolean {
  return waitingKind.split(',').includes(loai)
}

/** Danh sách bước đang WAITING vì CHỜ NGƯỜI. ⛔ Một node WAITING vì
 *  `core.delay`/`core.wait` (waiting_kind là `DELAY`/`WEBHOOK`/`EVENT`, không
 *  có `HUMAN`) không được hiện ở đây — đọc `waiting_kind`, ⛔ không suy từ
 *  `status`. */
export function DuyetNguoi({ run, tenBuoc, thamSo }: Props) {
  if (!run) return null
  const choDuyet = run.nodes.filter(n => n.status === 'WAITING' && coCho(n.waiting_kind, 'HUMAN'))
  if (!choDuyet.length) return null
  return (
    <section className="run-duyet-nguoi" aria-label="Đang chờ người duyệt">
      {choDuyet.map(n => {
        const p = thamSo(n.node_id) ?? {}
        return (
          <TheDuyet key={n.node_id} runId={run.id} nodeId={n.node_id}
            ten={tenBuoc(n.node_id)}
            caseHoi={typeof p.cau_hoi === 'string' ? p.cau_hoi : ''}
            hetHan={nhanHetHan(p.het_han)} />
        )
      })}
    </section>
  )
}
