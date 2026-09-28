import { useRef } from 'react'
import type { EditorAction } from '../../editorState'
import type { CanvasDocument, CanvasPage } from '../../workflowApi'
import { useFocusTrap } from './hooks/useFocusTrap'
import type { MenuNguCanh, NganDesktop } from './kieu'

type Props = {
  menu: MenuNguCanh
  dong: () => void
  document: CanvasDocument
  page: CanvasPage
  readOnly: boolean
  showConnections: boolean
  moNgan: (ngan: NganDesktop) => void
  duplicateNode: (nodeId: string) => void
  xoaNode: (nodeId: string) => void
  dispatch: (action: EditorAction) => void
}

/** Menu ngữ cảnh — hai hình dạng: ở khoảng trống, và trên một node.
 *
 *  ⚠️ Vị trí bị KẸP vào trong khung nhìn (`Math.min`). Không kẹp thì một cú
 *     phải chuột sát mép phải mở một menu chạy ra ngoài màn hình.
 */
export function ContextMenu(p: Props) {
  const { menu } = p
  const ngan = useRef<HTMLElement>(null)
  useFocusTrap(ngan)
  return <aside ref={ngan} className={`canvas-context-menu ${menu.kind}`} aria-label={menu.kind==='pane'?'Menu khoảng trống Canvas':'Menu thao tác node'}
    style={{left:Math.min(menu.x,window.innerWidth-310),top:Math.min(menu.y,window.innerHeight-520)}}>
    <header><strong>{menu.kind==='pane'?'Thêm vào Canvas':'Thao tác node'}</strong><button aria-label="Đóng menu ngữ cảnh" onClick={p.dong}>×</button></header>
    {menu.kind==='pane'?<><button onClick={()=>{p.moNgan('tools');p.dong()}}>Mở bảng node</button>
      <hr/><button onClick={()=>{p.dispatch({type:'pageView',connections:!p.showConnections});p.dong()}}>{p.showConnections?'Ẩn đường nối':'Hiện đường nối'}</button>
      <button onClick={()=>{p.dispatch({type:'layout'});p.dong()}}>Tự động sắp xếp node</button></>:
      <>{menu.nodeId&&<><button disabled={p.readOnly} onClick={()=>{p.duplicateNode(menu.nodeId!);p.dong()}}>Sao chép node</button>
        {p.document.pages.filter(item=>item.id!==p.page.id).map(item=><button key={item.id} disabled={p.readOnly}
          onClick={()=>{p.dispatch({type:'nodeMovePage',id:menu.nodeId!,pageId:item.id});p.dong()}}>Chuyển sang {item.name}</button>)}
        <button className="danger" disabled={p.readOnly} onClick={()=>{p.xoaNode(menu.nodeId!);p.dong()}}>Xóa node</button></>}</>}
  </aside>
}
