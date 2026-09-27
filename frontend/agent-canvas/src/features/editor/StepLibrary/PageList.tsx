import type { EditorAction } from '../../../editorState'
import type { CanvasDocument, CanvasPage } from '../../../workflowApi'

type Props = {
  document: CanvasDocument
  page: CanvasPage
  readOnly: boolean
  xoaLuaChon: () => void
  dispatch: (action: EditorAction) => void
}

/** Danh sách Pages trong ngăn bên trái.
 *
 *  ⚠️ Trần 20 page là chốt của máy chủ, ⛔ không phải một con số cho đẹp.
 *  ⚠️ Nút xoá bị vô hiệu khi còn MỘT page: một tài liệu không page là hình
 *     dạng mà `activePage()` không có lối lui nào cho.
 */
export function PageList(p: Props) {
  return <section className="page-panel" aria-label="Pages"><header><h3>Pages</h3><button disabled={p.readOnly||p.document.pages.length>=20}
    onClick={()=>{p.dispatch({type:'pageAdd'});p.xoaLuaChon()}}>+ Page</button></header>
    {p.document.pages.map(item=><div className={`page-row${item.id===p.page.id?' active':''}`} key={item.id}>
      <button aria-label={`Mở ${item.name}`} aria-pressed={item.id===p.page.id} onClick={()=>{p.dispatch({type:'pageSelect',id:item.id});p.xoaLuaChon()}}>{item.nodes.length}</button>
      <input aria-label={`Đổi tên ${item.name}`} disabled={p.readOnly} value={item.name}
        onChange={event=>p.dispatch({type:'pageRename',id:item.id,name:event.target.value})}/>
      <button aria-label={`Xóa ${item.name}`} disabled={p.readOnly||p.document.pages.length===1}
        onClick={()=>p.dispatch({type:'pageDelete',id:item.id})}>×</button></div>)}
  </section>
}
