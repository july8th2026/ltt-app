import type { EditorAction } from '../../editorState'

type Props = {
  truyVan: string
  datTruyVan: (q: string) => void
  dong: () => void
  /** Đóng VÀ xoá truy vấn — đường dành cho "đã chạy một lệnh". */
  dongVaXoa: () => void
  showGrid: boolean
  showConnections: boolean
  showMinimap: boolean
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
 */
export function CommandPalette(p: Props) {
  const lenh = [
    {name:'Tạo page mới',run:()=>p.dispatch({type:'pageAdd'})},
    {name:'Tạo sticky note',run:()=>p.dispatch({type:'noteAdd',text:'Ghi chú mới'})},
    {name:'Tạo comment',run:()=>p.dispatch({type:'commentAdd',text:'Bình luận mới'})},
    {name:'Tự động sắp xếp',run:()=>p.dispatch({type:'layout'})},
    {name:p.showGrid?'Ẩn lưới':'Hiện lưới',run:()=>p.dispatch({type:'pageView',grid:!p.showGrid})},
    {name:p.showConnections?'Ẩn đường nối':'Hiện đường nối',run:()=>p.dispatch({type:'pageView',connections:!p.showConnections})},
    {name:p.showMinimap?'Ẩn bản đồ':'Hiện bản đồ',run:()=>p.dispatch({type:'pageView',minimap:!p.showMinimap})},
  ]
  return <div className="command-backdrop" role="presentation" onMouseDown={event=>event.target===event.currentTarget&&p.dong()}>
    <section className="command-palette" role="dialog" aria-modal="true" aria-label="Bảng lệnh Canvas">
      <header><strong>Bảng lệnh</strong><kbd>Esc</kbd></header><input autoFocus aria-label="Tìm lệnh" value={p.truyVan}
        onChange={event=>p.datTruyVan(event.target.value)} placeholder="Tìm thao tác…"/>
      <div>{lenh.filter(item=>item.name.toLocaleLowerCase('vi').includes(p.truyVan.toLocaleLowerCase('vi')))
        .map(item=><button key={item.name} onClick={()=>{item.run();p.dongVaXoa()}}>{item.name}</button>)}</div>
    </section></div>
}
