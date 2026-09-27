import { RunDiff } from '../../../RunDiff'
import { RunInspector } from '../../../RunInspector'
import { RunV3Panel } from '../../../RunV3Panel'
import type { EditorAction } from '../../../editorState'
import type { CanvasEdge, CanvasPage, RunV3, SoSanhRunV3, Workflow } from '../../../workflowApi'
import type { NganDesktop, PhaLuu } from '../kieu'
import { RunTools } from './RunTools'

type Props = {
  moNgan: (ngan: NganDesktop) => void
  dangMo: boolean
  page: CanvasPage
  workflow: Workflow | undefined
  phase: PhaLuu
  readOnly: boolean
  run: RunV3 | null
  runError: string
  runGoc: RunV3 | null
  runDaXong: boolean
  dangGui: boolean
  soSanh: SoSanhRunV3 | null
  soSanhLoi: string
  chayWorkflow: () => void
  huyRun: () => void
  chayLaiTuNode: (nodeId: string) => void
  soSanhVoiGoc: () => void
  taoBanChayMoi: () => void
  // — hàng công cụ —
  selected: string[]
  selectedEdges: string[]
  selectedEdge: CanvasEdge | undefined
  showGrid: boolean
  showConnections: boolean
  showMinimap: boolean
  showLayers: boolean
  batLayers: () => void
  duplicate: () => void
  toggleErrorBranch: () => void
  dispatch: (action: EditorAction) => void
}

/** Ngăn kéo "Chạy workflow": phạm vi · nút Chạy ngay · bảng lượt chạy · so sánh.
 *
 *  ⛔ 01b chay CA do thi da publish: khong con chon pham vi, khong con
 *     `use_cache`, khong con buoc duyet bao gia — ba thu ay la ngu nghia cua
 *     Plan v1. May chu chot `credit_max` ngay luc publish.
 */
export function ExecutionPanel(p: Props) {
  return <nav className={`operation-drawer${p.dangMo?' is-open':''}`} aria-label="Chạy workflow"><header><strong>Chạy workflow</strong><button aria-label="Đóng bảng chạy" onClick={()=>p.moNgan(null)}>×</button></header>
    <RunTools page={p.page} selected={p.selected} selectedEdges={p.selectedEdges}
      selectedEdge={p.selectedEdge} readOnly={p.readOnly} showGrid={p.showGrid}
      showConnections={p.showConnections} showMinimap={p.showMinimap}
      showLayers={p.showLayers} batLayers={p.batLayers} duplicate={p.duplicate}
      toggleErrorBranch={p.toggleErrorBranch} dispatch={p.dispatch}/>
    <section className="run-scope-preview" aria-label="Phạm vi và chi phí"><small>PHẠM VI</small><strong>Toàn workflow</strong>
      <span>{p.page.nodes.length} block · server chốt chi phí tối đa khi publish</span></section>
    {/* Nhan doi theo `dangGui`: nuot im lang lan bam thu hai chi lam nguoi
        dung bam them nua. Ho phai THAY lang minh da di. */}
    {!p.run&&<button className="run-confirm" aria-busy={p.dangGui||undefined}
      disabled={p.readOnly||!p.workflow||!p.page.nodes.length||p.phase==='saving'||p.dangGui}
      onClick={p.chayWorkflow}>{p.dangGui?'Đang gửi…':'Chạy ngay'}</button>}
    {p.runDaXong&&<button onClick={p.taoBanChayMoi}>Tạo bản chạy mới</button>}
    <RunV3Panel run={p.run} onCancel={p.huyRun} onChayLaiTu={p.chayLaiTuNode}/>
    {p.runError && <span className="run-error" role="alert">{p.runError}</span>}
    {/* Task A2 — nguồn của cặp so sánh la (run cũ, run "chạy lại từ" nó);
        xem chú thích ở khai báo `runGoc`. */}
    {p.run&&p.runGoc&&p.runDaXong&&<button onClick={p.soSanhVoiGoc}>So sánh với lượt gốc</button>}
    {p.soSanhLoi && <span className="run-error" role="alert">{p.soSanhLoi}</span>}
    {p.soSanh && <RunDiff soSanh={p.soSanh}/>}
    {/* Task A5 — inspector thô (node + log sự kiện) cho lượt đang xem. */}
    <RunInspector run={p.run}/></nav>
}
