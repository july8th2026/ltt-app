import type { CanvasDocument, CanvasEdge, CanvasNode } from './workflowApi'

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
  | { type: 'viewport'; viewport: CanvasDocument['viewport'] }
  | { type: 'document'; goal?: string; budget_max_credit?: number }
  | { type: 'delete'; ids: string[] }
  | { type: 'deleteEdges'; ids: string[] }
  | { type: 'undo' | 'redo' | 'layout' }

const clone = (document: CanvasDocument): CanvasDocument => structuredClone(document)

export const emptyDocument = (): CanvasDocument => ({
  version: 1, goal: '', budget_max_credit: 50, nodes: [], edges: [],
  viewport: { x: 0, y: 0, zoom: 1 },
})

function changed(state: EditorState, document: CanvasDocument): EditorState {
  return { ...state, document, past: [...state.past.slice(-49), clone(state.document)], future: [] }
}

export function editorReducer(state: EditorState, action: EditorAction): EditorState {
  switch (action.type) {
    case 'replace': return { document: clone(action.document), past: [], future: [] }
    case 'select': return { ...state, selectedId: action.id }
    case 'graph': return changed(state, { ...state.document, nodes: action.nodes, edges: action.edges })
    case 'sync': return { ...state, document: { ...state.document, nodes: action.nodes, edges: action.edges } }
    case 'commit': return { ...state, past: [...state.past.slice(-49), clone(action.before)], future: [] }
    case 'update': return changed(state, { ...state.document, nodes: state.document.nodes.map(node =>
      node.id === action.id ? { ...node, data: { ...node.data, ...action.data } } : node) })
    case 'viewport': return changed(state, { ...state.document, viewport: action.viewport })
    case 'document': return changed(state, { ...state.document,
      goal: action.goal ?? state.document.goal,
      budget_max_credit: action.budget_max_credit ?? state.document.budget_max_credit })
    case 'delete': {
      const ids = new Set(action.ids)
      return changed({ ...state, selectedId: ids.has(state.selectedId ?? '') ? undefined : state.selectedId },
        { ...state.document, nodes: state.document.nodes.filter(node => !ids.has(node.id)),
          edges: state.document.edges.filter(edge => !ids.has(edge.source) && !ids.has(edge.target)) })
    }
    case 'deleteEdges': {
      const ids = new Set(action.ids)
      return changed(state, { ...state.document,
        edges: state.document.edges.filter(edge => !ids.has(edge.id)) })
    }
    case 'layout': return changed(state, { ...state.document,
      nodes: state.document.nodes.map((node, index) => ({ ...node,
        position: { x: (index % 4) * 280, y: Math.floor(index / 4) * 190 } })) })
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

const inputPort = (type: string) => ['string', 'text', 'enum'].includes(type) ? 'text'
  : ['int', 'number', 'bool'].includes(type) ? 'json' : type

export function connectionAllowed(source: PaletteTool | undefined, sourceHandle: string | null,
                                  target: PaletteTool | undefined, targetHandle: string | null) {
  if (!source || !target || !sourceHandle || !targetHandle) return false
  const output = source.returns[sourceHandle]
  const input = target.params_schema[targetHandle]
  return Boolean(output && input && output === inputPort(input.type))
}

export function nextNode(tool: PaletteTool, count: number): CanvasNode {
  const params = Object.fromEntries(Object.entries(tool.params_schema)
    .filter(([, rule]) => rule.default !== undefined)
    .map(([name, rule]) => [name, structuredClone(rule.default)]))
  return { id: `n${Date.now().toString(36)}-${count}`, type: 'tool',
    position: { x: 80 + (count % 3) * 260, y: 80 + Math.floor(count / 3) * 180 },
    data: { tool: tool.name, params, fanout: 1, max_retry: 0,
      on_fail: 'retry_same', verify: null } }
}
