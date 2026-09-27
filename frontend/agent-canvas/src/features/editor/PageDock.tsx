import type { EditorAction } from '../../editorState'
import type { CanvasDocument } from '../../workflowApi'

/** Thanh chuyển page dưới khung vẽ. */
export function PageDock({ document, activeId, dispatch }:
    { document: CanvasDocument; activeId: string
      dispatch: (action: EditorAction) => void }) {
  return <nav className="page-dock" aria-label="Chuyển page">{document.pages.map((item,index)=><button
    key={item.id} aria-pressed={item.id===activeId} onClick={()=>dispatch({type:'pageSelect',id:item.id})}>{item.name||`Page ${index+1}`}</button>)}</nav>
}
