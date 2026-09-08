export type CanvasNode = {
  id: string
  type: 'tool'
  position: { x: number; y: number }
  label?: string
  data: Record<string, unknown>
}

export type CanvasEdge = { id: string; source: string; target: string;
  sourceHandle?: string | null; targetHandle?: string | null;
  data?: { condition?: 'success'|'error'; modality?:string; running?:boolean;
    onInsert?:(client:{x:number;y:number})=>void } }

export type CanvasFrame = { id: string; name: string; node_ids: string[]; color?: string }
export type CanvasAnnotation = { id: string; text: string; x?: number; y?: number }
export type CanvasPage = { id: string; name: string; nodes: CanvasNode[]; edges: CanvasEdge[];
  viewport: { x: number; y: number; zoom: number }; frames: CanvasFrame[];
  notes: CanvasAnnotation[]; comments: CanvasAnnotation[];
  view?: { grid: boolean; connections: boolean; minimap: boolean } }
export type CanvasDocument = {
  version: 2
  goal: string
  budget_max_credit: number
  active_page_id: string
  pages: CanvasPage[]
}

type LegacyCanvasDocument = { version: 1; goal: string; budget_max_credit: number;
  nodes: CanvasNode[]; edges: CanvasEdge[]; viewport: CanvasPage['viewport'] }

export type Workflow = {
  id: string
  name: string
  status: 'draft' | 'validated' | 'approved' | 'archived'
  revision: number
  estimated: number
  canvas: CanvasDocument
}

export type AgentRun = {
  id: string
  version: number
  status: string
  plan: { steps: { id: string }[] }
  checkpoint: Record<string, Record<string, unknown>>
  estimated: number
  actual: number
  quote_hash: string
  decisions: Record<string, unknown>[]
  artifacts?: { step_id: string; name: string; url: string }[]
  scheduled_at?: string
}
export type AgentRunSummary=Pick<AgentRun,'id'|'version'|'status'|'estimated'|'actual'>&{
  created_at:string;finished_at:string}

export class WorkflowConflictError extends Error {}

async function decode(response: Response) {
  if (response.ok) return response.json()
  if (response.status === 409) throw new WorkflowConflictError('Workflow was updated elsewhere')
  let message = `Request failed (${response.status})`
  try { message = (await response.json()).detail ?? message } catch { /* non-JSON error */ }
  throw new Error(message)
}

async function request(path: string, init?: RequestInit) {
  return decode(await fetch(path, { credentials: 'same-origin', ...init }))
}

export function normalizeCanvas(canvas: CanvasDocument | LegacyCanvasDocument): CanvasDocument {
  if (canvas.version === 2) return canvas
  return { version: 2, goal: canvas.goal, budget_max_credit: canvas.budget_max_credit,
    active_page_id: 'page-1', pages: [{ id: 'page-1', name: 'Page 1',
      nodes: canvas.nodes, edges: canvas.edges, viewport: canvas.viewport,
      frames: [], notes: [], comments: [], view: { grid: true, connections: true, minimap: true } }] }
}

// ── Canvas v3 (LTT WORKFLOW V2, Dot 5.2) ────────────────────────────────────
//
// Canh v3 mang KIEU va CONG. Canh v2 co `sourceHandle`/`targetHandle` nhung
// `canvas_to_plan()` cua duong cu VUT chung di — do la chinh xac thu `M-1`
// duoc viet de cuu (`27_29 §27.2`).
//
// 🔴 SAU TEN TRUONG DUOI DAY PHAI KHOP TUNG CHU voi thu may chu sinh ra o
//    `platform_core/workflow/di_tru_m1.py::_canh_v3` va doc o
//    `dinh_nghia.py::_sinh_chi_muc`. Mot chu khac nhau khong gay loi bien dich
//    o ben nao ca — no chi lam cong bien mat trong im lang, dung nhu duong cu.
//    `tests/test_967` khong kiem duoc dieu do (no chi doc frontend), nen
//    `tests/test_968` doc CA HAI bo va so.
export type CanvasEdgeKind = 'DATA' | 'CONTROL'
export type CanvasEdgeV3 = {
  id: string
  source_node: string
  target_node: string
  source_port: string
  target_port: string
  kind: CanvasEdgeKind
}
export type CanvasPageV3 = Omit<CanvasPage, 'edges'> & { edges: CanvasEdgeV3[] }
export type CanvasDocumentV3 = Omit<CanvasDocument, 'version' | 'pages'> & {
  version: 3
  pages: CanvasPageV3[]
}

// Cong mac dinh khi canh cu khong khai. Trung voi `_canh_v3` phia may chu.
export const DEFAULT_SOURCE_PORT = 'out'
export const DEFAULT_TARGET_PORT = 'in'

export function edgeToV3(edge: CanvasEdge): CanvasEdgeV3 {
  return {
    id: edge.id,
    source_node: edge.source,
    target_node: edge.target,
    source_port: edge.sourceHandle || DEFAULT_SOURCE_PORT,
    target_port: edge.targetHandle || DEFAULT_TARGET_PORT,
    kind: 'DATA',
  }
}

export function edgeFromV3(edge: CanvasEdgeV3): CanvasEdge {
  return {
    id: edge.id,
    source: edge.source_node,
    target: edge.target_node,
    sourceHandle: edge.source_port,
    targetHandle: edge.target_port,
  }
}

/** v1/v2 -> v3. Mot tai lieu da la v3 thi tra ve nguyen. */
export function toV3(canvas: CanvasDocument | LegacyCanvasDocument | CanvasDocumentV3): CanvasDocumentV3 {
  if ((canvas as CanvasDocumentV3).version === 3) return canvas as CanvasDocumentV3
  const v2 = normalizeCanvas(canvas as CanvasDocument | LegacyCanvasDocument)
  return { ...v2, version: 3,
    pages: v2.pages.map(page => ({ ...page, edges: page.edges.map(edgeToV3) })) }
}

/**
 * v3 -> v2, de con GUI duoc cho `/agent/api/workflows` khi no chua nhan v3.
 *
 * ⚠️ Day KHONG phai mot lop tuong thich vinh vien. No ton tai dung mot ly do:
 *    `WorkflowDraft` (v3) va `AgentWorkflow.document` (v2) hien la HAI bang
 *    khac nhau, va cua noi bo cho bang moi chua duoc dung. Go no cung luc go
 *    Plan v1.
 */
export function fromV3(canvas: CanvasDocumentV3): CanvasDocument {
  return { ...canvas, version: 2,
    pages: canvas.pages.map(page => ({ ...page, edges: page.edges.map(edgeFromV3) })) }
}

function normalizeWorkflow(workflow: Workflow): Workflow {
  return { ...workflow, canvas: normalizeCanvas(workflow.canvas as CanvasDocument | LegacyCanvasDocument) }
}

export const loadPalette = () => request('/agent/api/palette')

export type AgentPreferences = { theme: 'light'|'dark'; catalog_mode: 'simple'|'advanced';
  presentation_version: 'creative-v1'; revision: number }
export const loadPreferences = (): Promise<AgentPreferences> => request('/agent/api/preferences')
export const savePreferences = (preferences: Omit<AgentPreferences,'revision'>, csrfToken: string): Promise<AgentPreferences> =>
  request('/agent/api/preferences', { method: 'PUT', headers: {
    'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
    body: JSON.stringify(preferences) })

export type AssistantResult = { analysis?: { nodes: number; valid: boolean; issues: string[];
  roots: number; patterns_considered: number }; proposal?: { token: string; canvas: CanvasDocument;
  diff: { before_nodes: number; after_nodes: number; estimated_max_credit: number } }; error?: string }

export async function previewAssistant(workflow: Workflow, mode: 'analyze'|'improve', prompt: string,
                                       csrfToken: string): Promise<AssistantResult> {
  const response = await fetch(`/agent/api/workflows/${workflow.id}/assistant/preview`, { method: 'POST',
    credentials: 'same-origin', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken,
      'If-Match': `"${workflow.revision}"` }, body: JSON.stringify({ mode, prompt }) })
  if (!response.ok || !response.body) return decode(response)
  const result: AssistantResult = {}; const reader = response.body.getReader(); const decoder = new TextDecoder()
  let buffer = ''
  while (true) { const { value, done } = await reader.read(); buffer += decoder.decode(value, { stream: !done })
    const packets = buffer.split('\n\n'); buffer = packets.pop() ?? ''
    for (const packet of packets) { const event = packet.match(/^event: (.+)$/m)?.[1]
      const data = packet.match(/^data: (.+)$/m)?.[1]; if (!event || !data) continue
      const parsed = JSON.parse(data)
      if (event === 'analysis') result.analysis = parsed
      if (event === 'proposal') result.proposal = { ...parsed, canvas: normalizeCanvas(parsed.canvas) }
      if (event === 'error') result.error = parsed.detail }
    if (done) break }
  return result
}

export async function applyAssistant(workflow: Workflow, token: string,
                                     csrfToken: string): Promise<Workflow> {
  return normalizeWorkflow(await request(`/agent/api/workflows/${workflow.id}/assistant/apply`, {
    method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
    body: JSON.stringify({ token }) }))
}

export type WorkflowSnapshot = { revision: number; name: string; reason: string; created_at: string }
export const loadSnapshots = async (workflow: Workflow): Promise<WorkflowSnapshot[]> =>
  (await request(`/agent/api/workflows/${workflow.id}/snapshots`)).items
export async function restoreSnapshot(workflow: Workflow, revision: number,
                                      csrfToken: string): Promise<Workflow> {
  return normalizeWorkflow(await request(`/agent/api/workflows/${workflow.id}/snapshots/${revision}/restore`, {
    method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
    body: JSON.stringify({ revision: workflow.revision }) }))
}
export async function createShare(workflow: Workflow, permission: 'view'|'clone', csrfToken: string) {
  return request(`/agent/api/workflows/${workflow.id}/shares`, { method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
    body: JSON.stringify({ permission, expires_hours: 24 }) })
}

export async function uploadAsset(file: File, csrfToken: string): Promise<{
  key: string; kind: string; name: string; size: number; content_type: string; url: string
}> {
  const body = new FormData(); body.append('file', file)
  return decode(await fetch('/agent/api/assets', { method: 'POST', credentials: 'same-origin',
    headers: { 'X-CSRF-Token': csrfToken }, body }))
}

export async function quoteTool(tool: string, params: Record<string, unknown>, fanout: number,
                                maxRetry: number, csrfToken: string): Promise<number> {
  const result = await request(`/agent/api/tools/${encodeURIComponent(tool)}/quote`, {
    method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
    body: JSON.stringify({ params, fanout, max_retry: maxRetry }),
  })
  if (!result.valid) throw new Error(result.detail || 'Node chưa đủ dữ liệu để báo giá')
  return Number(result.maximum)
}

export async function planWorkflow(goal: string, budgetMax: number,
                                   csrfToken: string): Promise<Workflow> {
  return normalizeWorkflow(await request('/agent/api/workflows/plan', { method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
    body: JSON.stringify({ goal, budget_max_credit: budgetMax }) }))
}

export async function loadOrCreateWorkflow(csrfToken: string): Promise<Workflow> {
  const listing = await request('/agent/api/workflows')
  if (listing.items.length) return normalizeWorkflow(await request(`/agent/api/workflows/${listing.items[0].id}`))
  return normalizeWorkflow(await request('/agent/api/workflows', { method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
    body: JSON.stringify({ name: 'Workflow mới', canvas: {
      version: 2, goal: '', budget_max_credit: 50, active_page_id: 'page-1',
      pages: [{ id: 'page-1', name: 'Page 1', nodes: [], edges: [],
        viewport: { x: 0, y: 0, zoom: 1 }, frames: [], notes: [], comments: [],
        view: { grid: true, connections: true, minimap: true } }],
    } }) }))
}

export async function saveWorkflow(
  workflow: Workflow,
  csrfToken: string,
  signal?: AbortSignal,
): Promise<Workflow> {
  const response = await fetch(`/agent/api/workflows/${workflow.id}`, {
    method: 'PUT',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken,
      'If-Match': `"${workflow.revision}"` },
    body: JSON.stringify({ name: workflow.name, canvas: workflow.canvas }),
    signal,
  })
  return normalizeWorkflow(await decode(response))
}

export async function validateWorkflow(workflow: Workflow, csrfToken: string) {
  return request(`/agent/api/workflows/${workflow.id}/validate`, { method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken,
      'If-Match': `"${workflow.revision}"` }, body: '{}' })
}

export type RunScope = { mode: 'full'|'node'|'selection'|'frame'; node_id?: string;
  node_ids?: string[]; frame_id?: string }

export async function createRun(workflow: Workflow, csrfToken: string,
                                scope: RunScope = { mode: 'full' }, useCache = true): Promise<AgentRun> {
  return request(`/agent/api/workflows/${workflow.id}/runs`, { method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken,
      'If-Match': `"${workflow.revision}"` }, body: JSON.stringify({ scope, use_cache: useCache }) })
}

export async function approveRun(run: AgentRun, csrfToken: string,
                                 scheduledAt = ''): Promise<AgentRun> {
  return request(`/agent/api/runs/${run.id}/approve`, { method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
    body: JSON.stringify({ version: run.version, quote_hash: run.quote_hash,
      scheduled_at: scheduledAt || undefined }) })
}

export async function tickRun(run: AgentRun, csrfToken: string): Promise<AgentRun> {
  return request(`/agent/api/runs/${run.id}/tick`, { method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken }, body: '{}' })
}

export async function cancelRun(run: AgentRun, csrfToken: string): Promise<AgentRun> {
  return request(`/agent/api/runs/${run.id}/cancel`, { method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken }, body: '{}' })
}

export async function runAgain(run: AgentRun, csrfToken: string): Promise<AgentRun> {
  return request(`/agent/api/runs/${run.id}/again`, { method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken }, body: '{}' })
}

export async function restoreRunAsWorkflow(run:AgentRun,csrfToken:string):Promise<Workflow>{
  return normalizeWorkflow(await request(`/agent/api/runs/${run.id}/restore-workflow`,{method:'POST',
    headers:{'Content-Type':'application/json','X-CSRF-Token':csrfToken},body:'{}'}))
}

export async function loadRunHistory():Promise<AgentRunSummary[]>{
  return (await request('/agent/api/runs')).items
}

export async function loadRun(id:string):Promise<AgentRun>{
  return request(`/agent/api/runs/${id}`)
}

export async function cloneWorkflow(workflow:Workflow,csrfToken:string):Promise<Workflow>{
  return normalizeWorkflow(await request(`/agent/api/workflows/${workflow.id}/clone`,{method:'POST',
    headers:{'Content-Type':'application/json','X-CSRF-Token':csrfToken},body:'{}'}))
}

export async function exportWorkflow(workflow:Workflow){
  return request(`/agent/api/workflows/${workflow.id}/export`)
}

export async function importWorkflow(payload:unknown,csrfToken:string):Promise<Workflow>{
  return normalizeWorkflow(await request('/agent/api/workflows/import',{method:'POST',
    headers:{'Content-Type':'application/json','X-CSRF-Token':csrfToken},body:JSON.stringify(payload)}))
}

export function createAutosave<T>(
  save: (value: T) => Promise<void>,
  delayMs = 800,
) {
  let timer: ReturnType<typeof setTimeout> | undefined
  let latest: T | undefined
  const flush = async () => {
    if (timer) clearTimeout(timer)
    timer = undefined
    if (latest === undefined) return
    const value = latest
    latest = undefined
    await save(value)
  }
  return {
    schedule(value: T) {
      latest = value
      if (timer) clearTimeout(timer)
      timer = setTimeout(() => { void flush() }, delayMs)
    },
    flush,
    cancel() {
      if (timer) clearTimeout(timer)
      timer = undefined
      latest = undefined
    },
  }
}
