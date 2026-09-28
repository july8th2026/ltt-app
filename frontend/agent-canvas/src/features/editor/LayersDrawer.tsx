import { useRef } from 'react'
import type { EditorAction } from '../../editorState'
import type { CanvasPage } from '../../workflowApi'
import { nhanNode, type BangDinhNghia } from './graph'
import { useFocusTrap } from './hooks/useFocusTrap'

type Props = {
  page: CanvasPage
  dinhNghia: BangDinhNghia
  dong: () => void
  dispatch: (action: EditorAction) => void
}

/** Danh sách lớp của trang: frame · khối · note · comment.
 *
 *  ⭐ Nhãn khối đi qua `nhanNode`, thứ tự nhiều node cùng tên bằng cách đánh số
 *     1/2/3 — ⛔ không phải một bảng tra tên app.
 */
export function LayersDrawer(p: Props) {
  const ngan = useRef<HTMLElement>(null)
  useFocusTrap(ngan)
  return <aside ref={ngan} className="layers-drawer" aria-label="Danh sách lớp"><header><strong>Lớp · {p.page.name}</strong>
    <button aria-label="Đóng danh sách lớp" onClick={p.dong}>×</button></header>
    <ul>{p.page.frames.map(frame=><li key={frame.id}><span>FRAME</span>{frame.name}</li>)}
      {p.page.nodes.map(node=><li key={node.id}><button onClick={()=>p.dispatch({type:'select',id:node.id})}><span>KHỐI</span>{nhanNode(node,p.page.nodes,p.dinhNghia)}</button></li>)}
      {p.page.notes.map(note=><li key={note.id}><span>NOTE</span>{note.text}</li>)}
      {p.page.comments.map(comment=><li key={comment.id}><span>COMMENT</span>{comment.text}</li>)}</ul></aside>
}
