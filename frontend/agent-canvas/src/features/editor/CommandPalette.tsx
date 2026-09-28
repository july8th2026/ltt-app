import { useRef } from 'react'
import type { EditorAction } from '../../editorState'
import type { CanvasEdge } from '../../workflowApi'
import { useFocusTrap } from './hooks/useFocusTrap'

type Props = {
  truyVan: string
  datTruyVan: (q: string) => void
  dong: () => void
  /** Đóng VÀ xoá truy vấn — đường dành cho "đã chạy một lệnh". */
  dongVaXoa: () => void
  showGrid: boolean
  showConnections: boolean
  showMinimap: boolean
  /** — bốn lệnh SỬA đã rời ngăn kéo "Chạy workflow" (làn UI-7) — */
  readOnly: boolean
  selected: string[]
  selectedEdges: string[]
  selectedEdge: CanvasEdge | undefined
  duplicate: () => void
  toggleErrorBranch: () => void
  dispatch: (action: EditorAction) => void
}

/** Bảng lệnh (Ctrl/Cmd+K).
 *
 *  ⚠️ Truy vấn sống ở `EditorShell`, ⛔ KHÔNG ở đây — và đó là bản gốc, không
 *     phải sơ suất: bản gốc chỉ gọi `setCommandQuery('')` sau khi CHẠY một
 *     lệnh, nên đóng bằng `Esc` hay bấm ra ngoài thì lần mở sau **còn nguyên**
 *     chữ đã gõ. Đưa state vào trong component là tháo nó theo mỗi lần đóng ⇒
 *     mất hành vi ấy trong im lặng. Đây là pha DI CHUYỂN; muốn đổi thì đổi
 *     riêng, có phép kiểm.
 *
 *  ## ⭐ Bốn lệnh cuối tới từ ngăn kéo "Chạy workflow" (làn UI-7)
 *
 *  Ngăn ấy chứa 7 nút xem/sửa không liên quan gì tới chạy
 *  (`01_CURRENT_UI_AUDIT.md §6`). *Tự xếp · Lưới · Đường nối · Bản đồ* đã có
 *  sẵn ở đây từ trước, *Lớp* có ở `LeftRail`; bốn lệnh dưới đây là phần còn
 *  thiếu, nên gỡ hàng nút kia ⛔ KHÔNG mất một đường vào nào.
 *
 *  ⚠️ Lệnh không dùng được thì `disabled`, ⛔ KHÔNG ẩn: một bảng lệnh mà mục
 *     xuất hiện/biến mất theo lựa chọn hiện tại thì không học được — người ta
 *     gõ "nhân" và thấy trống rỗng mà không biết vì sao.
 */
export function CommandPalette(p: Props) {
  const hopThoai = useRef<HTMLElement>(null)
  useFocusTrap(hopThoai)
  const coNode = !!p.selected.length
  const coCanh = !!p.selectedEdges.length
  const lenh: { name: string; run: () => void; disabled?: boolean }[] = [
    {name:'Tạo page mới',run:()=>p.dispatch({type:'pageAdd'})},
    {name:'Tạo sticky note',run:()=>p.dispatch({type:'noteAdd',text:'Ghi chú mới'})},
    {name:'Tạo comment',run:()=>p.dispatch({type:'commentAdd',text:'Bình luận mới'})},
    {name:'Tự động sắp xếp',run:()=>p.dispatch({type:'layout'})},
    {name:p.showGrid?'Ẩn lưới':'Hiện lưới',run:()=>p.dispatch({type:'pageView',grid:!p.showGrid})},
    {name:p.showConnections?'Ẩn đường nối':'Hiện đường nối',run:()=>p.dispatch({type:'pageView',connections:!p.showConnections})},
    {name:p.showMinimap?'Ẩn bản đồ':'Hiện bản đồ',run:()=>p.dispatch({type:'pageView',minimap:!p.showMinimap})},
    {name:'Nhân bản khối đang chọn',run:p.duplicate,disabled:p.readOnly||!coNode},
    {name:coCanh?'Xóa đường nối đang chọn':'Xóa khối đang chọn',
      run:()=>p.dispatch(coCanh?{type:'deleteEdges',ids:p.selectedEdges}:{type:'delete',ids:p.selected}),
      disabled:p.readOnly||(!coNode&&!coCanh)},
    {name:`Đổi nhánh đường nối: ${p.selectedEdge?.data?.condition==='error'?'Lỗi':'Thành công'}`,
      run:p.toggleErrorBranch,disabled:p.readOnly||p.selectedEdges.length!==1},
  ]
  return <div className="command-backdrop" role="presentation" onMouseDown={event=>event.target===event.currentTarget&&p.dong()}>
    <section ref={hopThoai} className="command-palette" role="dialog" aria-modal="true" aria-label="Bảng lệnh Canvas">
      <header><strong>Bảng lệnh</strong><kbd>Esc</kbd></header><input autoFocus aria-label="Tìm lệnh" value={p.truyVan}
        onChange={event=>p.datTruyVan(event.target.value)} placeholder="Tìm thao tác…"/>
      <div>{lenh.filter(item=>item.name.toLocaleLowerCase('vi').includes(p.truyVan.toLocaleLowerCase('vi')))
        .map(item=><button key={item.name} disabled={item.disabled}
          onClick={()=>{item.run();p.dongVaXoa()}}>{item.name}</button>)}</div>
    </section></div>
}
