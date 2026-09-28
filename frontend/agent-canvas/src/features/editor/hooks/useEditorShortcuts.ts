import { useEffect } from 'react'
import type { EditorAction } from '../../../editorState'
import type { CanvasPage } from '../../../workflowApi'

type ThamSo = {
  page: CanvasPage
  readOnly: boolean
  selected: string[]
  selectedEdges: string[]
  setSelected: (ids: string[]) => void
  setSelectedEdges: (ids: string[]) => void
  moBangLenh: () => void
  dongHet: () => void
  moNgan: (ngan: 'workspace') => void
  duplicate: () => void
  copy: () => void
  paste: () => void
  dispatch: (action: EditorAction) => void
}

/** Phím tắt — TOÀN CỤC (Ctrl+K, Escape) và CỤC BỘ trên khung (mọi phím khác).
 *
 *  ⚠️ Hai tầng, ⛔ không gộp được. `Ctrl+K`/`Escape` phải chạy cả khi tiêu điểm
 *     đang ở trong một ngăn kéo, nên chúng nằm ở `window`. Còn `Delete`, mũi
 *     tên, `n`, `f`, `d` chỉ được chạy khi tiêu điểm ở KHUNG: gắn chúng vào
 *     `window` là làm người dùng xoá node trong lúc đang gõ tên workflow.
 *
 *  ⭐ Chốt của tầng cục bộ là `target.closest('input,textarea,...')` ở dòng đầu
 *     `onKeyDown` — ⛔ đừng bỏ, nó là thứ duy nhất phân biệt "gõ" với "ra lệnh".
 */
export function useEditorShortcuts(ts: ThamSo) {
  useEffect(() => {
    const shortcut = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault(); ts.moBangLenh()
      } else if (event.key === 'Escape') {
        ts.dongHet()
      }
    }
    window.addEventListener('keydown', shortcut)
    return () => window.removeEventListener('keydown', shortcut)
  }, [ts])

  const onKeyDown = (event: React.KeyboardEvent) => {
    const { page, readOnly, selected, selectedEdges, dispatch } = ts
    const target=event.target as HTMLElement
    if(target.closest('input,textarea,select,[contenteditable="true"]'))return
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault(); ts.moBangLenh(); return
    }
    if (event.key === 'Escape') { ts.dongHet();return }
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'z') { event.preventDefault(); dispatch({ type: event.shiftKey ? 'redo' : 'undo' }); return }
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'y') { event.preventDefault(); dispatch({ type: 'redo' }); return }
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'd') { event.preventDefault(); ts.duplicate(); return }
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'c') { ts.copy();return }
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'v') { event.preventDefault(); ts.paste();return }
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'a') {
      event.preventDefault();ts.setSelected(page.nodes.map(node=>node.id));ts.setSelectedEdges([]);dispatch({type:'select'});return
    }
    if(!event.ctrlKey&&!event.metaKey&&!event.altKey){
      const key=event.key.toLowerCase()
      if(key==='n'){event.preventDefault();dispatch({type:'noteAdd',text:'Ghi chú mới'});return}
      if(key==='f'&&selected.length){event.preventDefault();dispatch({type:'frameAdd',nodeIds:selected});return}
      if(key==='d'){event.preventDefault();ts.moNgan('workspace');return}
      if(['arrowup','arrowdown','arrowleft','arrowright'].includes(key)&&selected.length&&!readOnly){
        event.preventDefault();const amount=event.shiftKey?10:1
        const movement={arrowup:{x:0,y:-amount},arrowdown:{x:0,y:amount},arrowleft:{x:-amount,y:0},arrowright:{x:amount,y:0}}[key]!
        dispatch({type:'graph',nodes:page.nodes.map(node=>selected.includes(node.id)?{...node,position:{x:node.position.x+movement.x,y:node.position.y+movement.y}}:node),edges:page.edges});return
      }
    }
    if (!readOnly && ['Delete', 'Backspace'].includes(event.key) && (selected.length || selectedEdges.length)) {
      event.preventDefault()
      dispatch(selectedEdges.length ? { type: 'deleteEdges', ids: selectedEdges } : { type: 'delete', ids: selected })
    }
  }

  return onKeyDown
}
