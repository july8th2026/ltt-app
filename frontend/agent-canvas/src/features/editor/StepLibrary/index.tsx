import { PaletteV2 } from '../../../palette/PaletteV2'
import type { EditorAction } from '../../../editorState'
import type { NhomPalette, NodeDefinition } from '../../../nodeDefinition'
import type { CanvasDocument, CanvasPage, Workflow } from '../../../workflowApi'
import type { NganDesktop } from '../kieu'
import { OrganizePanel } from './OrganizePanel'
import { PageList } from './PageList'
import { WorkflowSettings } from './WorkflowSettings'

type Props = {
  desktopPanel: NganDesktop
  moNgan: (ngan: NganDesktop) => void
  document: CanvasDocument
  page: CanvasPage
  selected: string[]
  readOnly: boolean
  workflow: Workflow | undefined
  nhomPalette: NhomPalette[]
  paletteQuery: string
  setPaletteQuery: (q: string) => void
  ganDay: string[]
  themNode: (nd: NodeDefinition) => void
  dangSoan: boolean
  soanLoi: string
  soanBangAI: () => void
  xoaLuaChon: () => void
  dispatch: (action: EditorAction) => void
}

/** Ngăn kéo bên trái — bọc `PaletteV2` hiện có, cộng Pages · Tổ chức · Mục tiêu.
 *
 *  ⚠️ MỘT ngăn, HAI mặt: `tools-only` (thêm block) và `workspace-only` (mẫu &
 *     thiết lập). Cùng một phần tử DOM, `canvas.css` ẩn/hiện từng khối theo
 *     lớp — nên ⛔ đừng tách nó thành hai `<aside>`: lớp CSS thuộc làn UI-2.
 */
export function StepLibrary(p: Props) {
  const moRong = p.desktopPanel==='tools'||p.desktopPanel==='workspace'
  return <aside className={`canvas-palette${moRong?' is-open':''}${p.desktopPanel==='workspace'?' workspace-only':' tools-only'}`} aria-label="Palette công cụ"><header className="drawer-heading"><h2>{p.desktopPanel==='workspace'?'Mẫu & thiết lập':'Thêm block'}</h2><button aria-label="Đóng Palette" onClick={()=>p.moNgan(null)}>×</button></header>
    <PageList document={p.document} page={p.page} readOnly={p.readOnly}
      xoaLuaChon={p.xoaLuaChon} dispatch={p.dispatch}/>
    <OrganizePanel page={p.page} selected={p.selected} readOnly={p.readOnly} dispatch={p.dispatch}/>
    <WorkflowSettings goal={p.document.goal} workflow={p.workflow} readOnly={p.readOnly}
      dangSoan={p.dangSoan} soanLoi={p.soanLoi} soanBangAI={p.soanBangAI} dispatch={p.dispatch}/>
    <PaletteV2 nhom={p.nhomPalette} truyVan={p.paletteQuery} onTruyVan={p.setPaletteQuery}
      onChon={nd=>p.themNode(nd)} ganDay={p.ganDay} /></aside>
}
