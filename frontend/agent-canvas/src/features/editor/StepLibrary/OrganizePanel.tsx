import type { EditorAction } from '../../../editorState'
import type { CanvasPage } from '../../../workflowApi'

type Props = {
  page: CanvasPage
  selected: string[]
  readOnly: boolean
  dispatch: (action: EditorAction) => void
}

/** Tổ chức: Frame từ lựa chọn · sticky note · comment, và danh sách của cả ba.
 *
 *  ⚠️ Frame/note/comment là TRANG TRÍ — chúng không có cổng, không tham số, và
 *     `bien_dich.py` không thấy chúng. Sửa ở đây không bao giờ đổi thứ chạy.
 */
export function OrganizePanel(p: Props) {
  return <section className="organize-panel"><h3>Tổ chức</h3><button disabled={p.readOnly||!p.selected.length}
    onClick={()=>p.dispatch({type:'frameAdd',nodeIds:p.selected})}>Tạo Frame từ lựa chọn</button>
    <button disabled={p.readOnly} onClick={()=>p.dispatch({type:'noteAdd',text:'Ghi chú mới'})}>+ Sticky note</button>
    <button disabled={p.readOnly} onClick={()=>p.dispatch({type:'commentAdd',text:'Bình luận mới'})}>+ Comment</button>
    {!!p.page.frames.length&&<ul>{p.page.frames.map(frame=><li key={frame.id}><input aria-label={`Đổi tên ${frame.name}`}
      value={frame.name} disabled={p.readOnly} onChange={event=>p.dispatch({type:'frameRename',id:frame.id,name:event.target.value})}/>
      <small>{frame.node_ids.length} node</small><button aria-label={`Xóa ${frame.name}`} disabled={p.readOnly}
        onClick={()=>p.dispatch({type:'frameDelete',id:frame.id})}>×</button></li>)}</ul>}
    {!!p.page.notes.length&&<ul>{p.page.notes.map(note=><li key={note.id}><label>NOTE<input aria-label="Nội dung sticky note"
      value={note.text} disabled={p.readOnly} onChange={event=>p.dispatch({type:'annotationUpdate',kind:'notes',id:note.id,text:event.target.value})}/></label>
      <button aria-label="Xóa sticky note" disabled={p.readOnly} onClick={()=>p.dispatch({type:'annotationDelete',kind:'notes',id:note.id})}>×</button></li>)}</ul>}
    {!!p.page.comments.length&&<ul>{p.page.comments.map(comment=><li key={comment.id}><label>COMMENT<input aria-label="Nội dung comment"
      value={comment.text} disabled={p.readOnly} onChange={event=>p.dispatch({type:'annotationUpdate',kind:'comments',id:comment.id,text:event.target.value})}/></label>
      <button aria-label="Xóa comment" disabled={p.readOnly} onClick={()=>p.dispatch({type:'annotationDelete',kind:'comments',id:comment.id})}>×</button></li>)}</ul>}
  </section>
}
