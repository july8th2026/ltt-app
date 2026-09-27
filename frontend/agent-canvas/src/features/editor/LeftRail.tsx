import type { EditorAction } from '../../editorState'
import type { NganDesktop } from './kieu'

type Props = {
  desktopPanel: NganDesktop
  moNgan: (ngan: NganDesktop) => void
  batNgan: (ngan: Exclude<NganDesktop, null>) => void
  hasAnyNodes: boolean
  showLayers: boolean
  batLayers: () => void
  readOnly: boolean
  coQuaKhu: boolean
  coTuongLai: boolean
  boChon: () => void
  dispatch: (action: EditorAction) => void
}

/** Thanh dọc bên trái: chọn · thêm node · mẫu · chi tiết · lớp · ghi chú · undo.
 *
 *  🔴 Nút "Chi tiết node" ở đây là ĐƯỜNG VÀO DUY NHẤT của inspector trên
 *     desktop: `.canvas-mobile-tabs` (nút "Chi tiết") là `display:none` trên
 *     màn rộng. Trước task 15, tham số còn ở `ContextComposer` nổi lên cạnh
 *     node nên thiếu nó không ai thấy; giờ MỌI tham số ở inspector.
 */
export function LeftRail(p: Props) {
  return <nav className="canvas-rail" aria-label="Công cụ Canvas">
    <button title="Chọn" aria-label="Công cụ chọn" aria-pressed={!p.desktopPanel}>↖</button>
    <button title="Thêm node" aria-label="Mở công cụ" aria-pressed={p.desktopPanel==='tools'} onClick={()=>{const open=p.desktopPanel!=='tools';p.moNgan(open?'tools':null);if(open){p.boChon()}}}>＋</button>
    <button title="Mẫu & thiết lập" aria-label="Mở mẫu và thiết lập" aria-pressed={p.desktopPanel==='workspace'} onClick={()=>p.batNgan('workspace')}>▦</button>
    <button title="Chi tiết node" aria-label="Mở chi tiết node" aria-pressed={p.desktopPanel==='inspector'} onClick={()=>p.batNgan('inspector')}>☰</button>
    {p.hasAnyNodes&&<><button title="Lớp" aria-label="Mở danh sách lớp" aria-pressed={p.showLayers} onClick={p.batLayers}>☷</button>
      <button title="Sticky note" aria-label="Tạo sticky note" disabled={p.readOnly} onClick={()=>p.dispatch({type:'noteAdd',text:'Ghi chú mới'})}>□</button>
      <button title="Bình luận" aria-label="Tạo comment" disabled={p.readOnly} onClick={()=>p.dispatch({type:'commentAdd',text:'Bình luận mới'})}>◌</button></>}
    <span />
    <button title="Hoàn tác" aria-label="Hoàn tác" disabled={!p.coQuaKhu||p.readOnly} onClick={()=>p.dispatch({type:'undo'})}>↶</button>
    <button title="Làm lại" aria-label="Làm lại" disabled={!p.coTuongLai||p.readOnly} onClick={()=>p.dispatch({type:'redo'})}>↷</button>
  </nav>
}
