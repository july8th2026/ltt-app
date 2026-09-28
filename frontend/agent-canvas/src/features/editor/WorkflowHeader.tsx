import type { ReactNode } from 'react'
import type { CanvasPage, Workflow } from '../../workflowApi'
import type { GiaoDien, NganDesktop, PhaLuu } from './kieu'

type Props = {
  workflow: Workflow | undefined
  setWorkflow: (w: Workflow) => void
  luuTen: () => void
  page: CanvasPage
  readOnly: boolean
  offline: boolean
  phase: PhaLuu
  theme: GiaoDien
  doiGiaoDien: (next: GiaoDien) => void
  thuLuuLai: () => void
  desktopPanel: NganDesktop
  moNgan: (ngan: NganDesktop) => void
  moBangLenh: () => void
  /** Ngăn kéo "Chạy workflow" — nó là con của `<header>` trong DOM thật, nên
   *  nó đi vào đây qua `children` chứ ⛔ không dựng thành một khu vực riêng. */
  children: ReactNode
}

/** Thanh trên: tên workflow · huy hiệu trạng thái lưu · giao diện · nút Chạy.
 *
 *  ⛔ Nhãn phiên bản phải nói "Canvas v3". Trình soạn chạy runtime v3 từ plan
 *     01b (`saveWorkflowV3` -> `publishWorkflowV3` -> `createRunV3`); nhãn
 *     "Canvas v2" là một nhãn SAI — nghiệm thu production 23/09 bắt được.
 */
export function WorkflowHeader(p: Props) {
  return <header className="canvas-toolbar"><a className="canvas-home" href="/agent" aria-label="Về Agent AI">LTT</a><div className="workflow-identity"><input aria-label="Tên workflow"
    value={p.workflow?.name ?? ''} disabled={!p.workflow || p.readOnly} onChange={event=>p.workflow&&p.setWorkflow({...p.workflow,name:event.target.value})}
    onBlur={p.luuTen}/>
    <span>{p.readOnly ? 'Mobile · chỉ xem' : `Canvas v3 · ${p.page.name} · ${p.page.nodes.length} node · ${p.page.edges.length} kết nối`}</span></div>
    <div className="canvas-top-actions"><span className={`save-state ${p.phase}`} aria-live="polite">{p.offline ? 'Ngoại tuyến' : p.phase === 'saving' ? 'Đang lưu…' : p.phase === 'conflict' ? 'Xung đột' : p.phase === 'error' ? 'Lỗi lưu' : 'Đã lưu'}</span>
      {p.phase==='conflict'&&<button className="save-recovery" onClick={()=>location.reload()}>Tải bản mới</button>}
      {p.phase==='error'&&<button className="save-recovery" onClick={p.thuLuuLai}>Thử lưu lại</button>}
      <button title="Đổi giao diện" aria-label={p.theme==='light'?'Chuyển sang nền tối':'Chuyển sang nền sáng'} onClick={()=>p.doiGiaoDien(p.theme==='light'?'dark':'light')}>{p.theme==='light'?'☾':'☀'}</button>
      <button title="Bảng lệnh" aria-label="Mở bảng lệnh" onClick={p.moBangLenh}>⌘</button>
      {/* Nut "AI" (Assistant) va "↗" (Phien ban & chia se) da bo: ca hai ngan
          keo phia sau chung chi goi cua v2, va cua v2 khong biet id v3. */}
      {/* UI-12: dat lich (cron) + cap URL webhook. Trang rieng server-render
          (`/agent/workflows/{id}/triggers`), khong phai mot panel React —
          giu bundle Canvas KHONG phinh them mot mang trang thai moi cho
          mot thao tac hiem (tao/xoa trigger), va tranh dung vao gate bundle
          (`test_95`) cho mot man hinh khong lien quan render do thi. */}
      {p.workflow&&<button title="Trigger: đặt lịch & webhook" aria-label="Mở trang trigger"
        onClick={()=>{location.href=`/agent/workflows/${p.workflow!.id}/triggers`}}>⏰</button>}
      <button className="run-primary" disabled={p.readOnly||!p.page.nodes.length} aria-pressed={p.desktopPanel==='run'} onClick={()=>p.moNgan(p.desktopPanel==='run'?null:'run')}>Chạy</button></div>
    {p.children}</header>
}
