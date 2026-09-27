import type { EditorAction } from '../../../editorState'
import type { CanvasEdge, CanvasPage } from '../../../workflowApi'

type Props = {
  page: CanvasPage
  selected: string[]
  selectedEdges: string[]
  selectedEdge: CanvasEdge | undefined
  readOnly: boolean
  showGrid: boolean
  showConnections: boolean
  showMinimap: boolean
  showLayers: boolean
  batLayers: () => void
  duplicate: () => void
  toggleErrorBranch: () => void
  dispatch: (action: EditorAction) => void
}

/** Hàng công cụ trong ngăn "Chạy workflow": nhân bản · xoá · nhánh lỗi · tự
 *  xếp · và bốn công tắc hiển thị.
 *
 *  ⚠️ Bốn công tắc cuối ghi vào `page.view` (qua `pageView`), ⛔ không phải
 *     state cục bộ: người dùng tắt lưới rồi mở lại trang phải thấy nó còn tắt.
 */
export function RunTools(p: Props) {
  return <div className="run-tools"><button disabled={!p.selected.length || p.readOnly} onClick={p.duplicate}>Nhân bản</button>
    <button disabled={(!p.selected.length && !p.selectedEdges.length) || p.readOnly}
      onClick={() => p.dispatch(p.selectedEdges.length ? { type: 'deleteEdges', ids: p.selectedEdges } : { type: 'delete', ids: p.selected })}>Xóa</button>
    {p.selectedEdges.length===1&&<button disabled={p.readOnly} onClick={p.toggleErrorBranch}>Nhánh: {p.selectedEdge?.data?.condition==='error'?'Lỗi':'Thành công'}</button>}
    <button disabled={p.readOnly} onClick={() => p.dispatch({ type: 'layout' })}>Tự xếp</button>
    <button aria-pressed={p.showLayers} onClick={p.batLayers}>Lớp</button>
    <button aria-pressed={p.showGrid} onClick={()=>p.dispatch({type:'pageView',grid:!p.showGrid})}>Lưới</button>
    <button aria-pressed={p.showConnections} onClick={()=>p.dispatch({type:'pageView',connections:!p.showConnections})}>Đường nối</button>
    <button aria-pressed={p.showMinimap} onClick={()=>p.dispatch({type:'pageView',minimap:!p.showMinimap})}>Bản đồ</button></div>
}
