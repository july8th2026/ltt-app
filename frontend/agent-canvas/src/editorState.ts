import type { CanvasDocument, CanvasEdge, CanvasNode, CanvasPage } from './workflowApi'

export type EditorState = {
  document: CanvasDocument
  selectedId?: string
  past: CanvasDocument[]
  future: CanvasDocument[]
}

export type EditorAction =
  | { type: 'replace'; document: CanvasDocument }
  | { type: 'graph'; nodes: CanvasNode[]; edges: CanvasEdge[] }
  | { type: 'sync'; nodes: CanvasNode[]; edges: CanvasEdge[] }
  | { type: 'commit'; before: CanvasDocument }
  | { type: 'select'; id?: string }
  | { type: 'update'; id: string; data: Record<string, unknown> }
  | { type: 'viewport'; viewport: CanvasPage['viewport'] }
  | { type: 'pageView'; grid?: boolean; connections?: boolean; minimap?: boolean }
  | { type: 'document'; goal?: string; budget_max_credit?: number }
  | { type: 'pageAdd' }
  | { type: 'pageSelect'; id: string }
  | { type: 'pageRename'; id: string; name: string }
  | { type: 'pageDelete'; id: string }
  | { type: 'frameAdd'; nodeIds: string[] }
  | { type: 'frameRename'; id: string; name: string }
  | { type: 'frameDelete'; id: string }
  | { type: 'noteAdd'; text: string }
  | { type: 'commentAdd'; text: string }
  | { type: 'annotationUpdate'; kind: 'notes' | 'comments'; id: string; text: string }
  | { type: 'annotationDelete'; kind: 'notes' | 'comments'; id: string }
  | { type: 'delete'; ids: string[] }
  | { type: 'nodeMovePage'; id: string; pageId: string }
  | { type: 'deleteEdges'; ids: string[] }
  | { type: 'undo' | 'redo' | 'layout' }

const clone = (document: CanvasDocument): CanvasDocument => structuredClone(document)

export const emptyPage = (id = 'page-1', name = 'Page 1'): CanvasPage => ({
  id, name, nodes: [], edges: [], viewport: { x: 0, y: 0, zoom: 1 },
  frames: [], notes: [], comments: [],
  view: { grid: true, connections: true, minimap: true },
})

export const emptyDocument = (): CanvasDocument => ({ version: 2, goal: '',
  budget_max_credit: 50, active_page_id: 'page-1', pages: [emptyPage()] })

export function activePage(document: CanvasDocument): CanvasPage {
  return document.pages.find(page => page.id === document.active_page_id) ?? document.pages[0]
}

function updateActive(document: CanvasDocument, update: (page: CanvasPage) => CanvasPage): CanvasDocument {
  return { ...document, pages: document.pages.map(page =>
    page.id === document.active_page_id ? update(page) : page) }
}

function changed(state: EditorState, document: CanvasDocument): EditorState {
  return { ...state, document, past: [...state.past.slice(-49), clone(state.document)], future: [] }
}

export function editorReducer(state: EditorState, action: EditorAction): EditorState {
  switch (action.type) {
    case 'replace': return { document: clone(action.document), past: [], future: [] }
    case 'select': return { ...state, selectedId: action.id }
    case 'graph': return changed(state, updateActive(state.document, page =>
      ({ ...page, nodes: action.nodes, edges: action.edges })))
    case 'sync': return { ...state, document: updateActive(state.document, page =>
      ({ ...page, nodes: action.nodes, edges: action.edges })) }
    case 'commit': return { ...state, past: [...state.past.slice(-49), clone(action.before)], future: [] }
    case 'update': return changed(state, updateActive(state.document, page => ({ ...page,
      nodes: page.nodes.map(node => node.id === action.id
        ? { ...node, data: { ...node.data, ...action.data } } : node) })))
    case 'viewport': return { ...state, document: updateActive(state.document, page =>
      ({ ...page, viewport: action.viewport })) }
    case 'pageView': return changed(state, updateActive(state.document, page => ({ ...page,
      view: { grid: action.grid ?? page.view?.grid ?? true,
        connections: action.connections ?? page.view?.connections ?? true,
        minimap: action.minimap ?? page.view?.minimap ?? true } })))
    case 'document': return changed(state, { ...state.document,
      goal: action.goal ?? state.document.goal,
      budget_max_credit: action.budget_max_credit ?? state.document.budget_max_credit })
    case 'pageAdd': {
      const id = `page-${Date.now().toString(36)}`
      return changed({ ...state, selectedId: undefined }, { ...state.document,
        active_page_id: id, pages: [...state.document.pages,
          emptyPage(id, `Page ${state.document.pages.length + 1}`)] })
    }
    case 'pageSelect': return action.id === state.document.active_page_id ? state
      : { ...state, selectedId: undefined, document: { ...state.document, active_page_id: action.id } }
    case 'pageRename': return changed(state, { ...state.document,
      pages: state.document.pages.map(page => page.id === action.id
        ? { ...page, name: action.name.slice(0, 80) || page.name } : page) })
    case 'pageDelete': {
      if (state.document.pages.length === 1) return state
      const pages = state.document.pages.filter(page => page.id !== action.id)
      return changed({ ...state, selectedId: undefined }, { ...state.document, pages,
        active_page_id: action.id === state.document.active_page_id
          ? pages[0].id : state.document.active_page_id })
    }
    case 'frameAdd': return changed(state, updateActive(state.document, page => ({ ...page,
      frames: [...page.frames, { id: `frame-${Date.now().toString(36)}`,
        name: `Frame ${page.frames.length + 1}`, node_ids: action.nodeIds }] })))
    case 'frameRename': return changed(state, updateActive(state.document, page => ({ ...page,
      frames: page.frames.map(frame => frame.id === action.id
        ? { ...frame, name: action.name.slice(0, 80) || frame.name } : frame) })))
    case 'frameDelete': return changed(state, updateActive(state.document, page => ({ ...page,
      frames: page.frames.filter(frame => frame.id !== action.id) })))
    case 'noteAdd': return changed(state, updateActive(state.document, page => ({ ...page,
      notes: [...page.notes, { id: `note-${Date.now().toString(36)}`, text: action.text,
        x: 380 + (page.notes.length % 3) * 220, y: 100 + Math.floor(page.notes.length / 3) * 170 }] })))
    case 'commentAdd': return changed(state, updateActive(state.document, page => ({ ...page,
      comments: [...page.comments, { id: `comment-${Date.now().toString(36)}`, text: action.text,
        x: 420 + (page.comments.length % 3) * 220, y: 320 + Math.floor(page.comments.length / 3) * 120 }] })))
    case 'annotationUpdate': return changed(state, updateActive(state.document, page => ({ ...page,
      [action.kind]: page[action.kind].map(item => item.id === action.id
        ? { ...item, text: action.text.slice(0, 1000) } : item) })))
    case 'annotationDelete': return changed(state, updateActive(state.document, page => ({ ...page,
      [action.kind]: page[action.kind].filter(item => item.id !== action.id) })))
    case 'delete': {
      const ids = new Set(action.ids)
      return changed({ ...state, selectedId: ids.has(state.selectedId ?? '') ? undefined : state.selectedId },
        updateActive(state.document, page => ({ ...page,
          nodes: page.nodes.filter(node => !ids.has(node.id)),
          edges: page.edges.filter(edge => !ids.has(edge.source) && !ids.has(edge.target)),
          frames: page.frames.map(frame => ({ ...frame,
            node_ids: frame.node_ids.filter(id => !ids.has(id)) })) })))
    }
    case 'nodeMovePage': {
      if (action.pageId === state.document.active_page_id ||
          !state.document.pages.some(page => page.id === action.pageId)) return state
      const source = activePage(state.document)
      const node = source.nodes.find(item => item.id === action.id)
      if (!node) return state
      const document = { ...state.document, pages: state.document.pages.map(page => {
        if (page.id === source.id) return { ...page,
          nodes: page.nodes.filter(item => item.id !== action.id),
          edges: page.edges.filter(edge => edge.source !== action.id && edge.target !== action.id),
          frames: page.frames.map(frame => ({ ...frame,
            node_ids: frame.node_ids.filter(id => id !== action.id) })) }
        if (page.id === action.pageId) return { ...page, nodes: [...page.nodes, {
          ...node, position: { x: 90 + (page.nodes.length % 3) * 430,
            y: 90 + Math.floor(page.nodes.length / 3) * 430 } }] }
        return page
      }) }
      return changed({ ...state, selectedId: undefined }, document)
    }
    case 'deleteEdges': {
      const ids = new Set(action.ids)
      return changed(state, updateActive(state.document, page => ({ ...page,
        edges: page.edges.filter(edge => !ids.has(edge.id)) })))
    }
    case 'layout': return changed(state, updateActive(state.document, page => ({ ...page,
      nodes: page.nodes.map((node, index) => ({ ...node,
        position: { x: 90 + (index % 4) * 430, y: 90 + Math.floor(index / 4) * 430 } })) })))
    case 'undo': {
      const previous = state.past.at(-1)
      if (!previous) return state
      return { ...state, document: clone(previous), past: state.past.slice(0, -1),
        future: [clone(state.document), ...state.future].slice(0, 50) }
    }
    case 'redo': {
      const next = state.future[0]
      if (!next) return state
      return { ...state, document: clone(next), past: [...state.past, clone(state.document)].slice(-50),
        future: state.future.slice(1) }
    }
  }
}

export type PaletteTool = {
  name: string
  label?: string
  category?: 'content'|'input'|'transform'|'specialized'|'advanced'
  primary?: boolean
  description: string
  app_slug: string
  app_name: string
  requires: string[]
  params_schema: Record<string, { type: string; required?: boolean; default?: unknown;
    values?: unknown[]; options?: { value: unknown; label: string }[]; min?: number; max?: number;
    depends_on?: string }>
  schema_variants?: Record<string, Record<string, PaletteTool['params_schema']>>
  returns: Record<string, string>
  verifiable: string[]
}

const inputPort = (type: string) => ['string', 'text'].includes(type) ? 'text'
  : ['int', 'number', 'bool'].includes(type) ? 'json' : type

export function connectionAllowed(source: PaletteTool | undefined, sourceHandle: string | null,
                                  target: PaletteTool | undefined, targetHandle: string | null) {
  if (!source || !target || !sourceHandle || !targetHandle) return false
  const output = source.returns[sourceHandle]
  const input = target.params_schema[targetHandle]
  return Boolean(output && input && output === inputPort(input.type))
}

export function scopeNodeIds(nodes:CanvasNode[],edges:CanvasEdge[],targets:string[]){
  const available=new Set(nodes.map(node=>node.id))
  const included=new Set(targets.filter(id=>available.has(id)))
  let expanded=true
  while(expanded){
    expanded=false
    for(const edge of edges)if(included.has(edge.target)&&available.has(edge.source)&&!included.has(edge.source)){
      included.add(edge.source);expanded=true
    }
  }
  return [...included]
}

export function nextNode(tool: PaletteTool, count: number): CanvasNode {
  const params = Object.fromEntries(Object.entries(tool.params_schema)
    .filter(([, rule]) => rule.default !== undefined)
    .map(([name, rule]) => [name, structuredClone(rule.default)]))
  return { id: `n${Date.now().toString(36)}-${count}`, type: 'tool',
    position: { x: 90 + (count % 3) * 430, y: 90 + Math.floor(count / 3) * 430 },
    data: { tool: tool.name, params, fanout: 1, max_retry: 0,
      on_fail: 'retry_same', verify: null } }
}
