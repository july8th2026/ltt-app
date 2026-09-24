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

/** Lỗi biên dịch/báo giá do máy chủ trả ở `422 {ma,node_id,thong_diep}`.
 *  Giữ `ma`/`nodeId` để giao diện tô đúng node — một chuỗi thuần thì không. */
export class WorkflowCompileError extends Error {
  ma: string
  nodeId: string
  constructor(message: string, ma: string, nodeId: string) {
    super(message)
    this.name = 'WorkflowCompileError'
    this.ma = ma
    this.nodeId = nodeId
  }
}

async function decode(response: Response) {
  if (response.ok) return response.json()
  let detail: unknown
  try {
    detail = (await response.json()).detail
  } catch { /* non-JSON error */ }
  // Object co cau truc {ma?, node_id?, thong_diep?} — dung TRUOC nhanh 409
  // mac dinh, vi cua v3 huy run (`runs_v3.py::v3_huy_run`) cung tra 409 kem
  // detail nay ("da_ket_thuc"), khong phai xung dot revision. Doc dung
  // truong con nguoi doc duoc thay vi de `new Error({...})` bien no thanh
  // "[object Object]".
  const obj = (detail && typeof detail === 'object' && !Array.isArray(detail))
    ? detail as { ma?: string; node_id?: string; thong_diep?: string }
    : null
  if (response.status === 409) {
    // 409 CO detail cau truc (huy run da ket thuc) -> loi doc duoc tu may
    // chu. 409 KHONG co detail (luu draft, `If-Match` lech) -> xung dot
    // revision chung, giu nguyen thong diep cu.
    if (obj) throw new Error(obj.thong_diep ?? obj.ma ?? JSON.stringify(obj))
    throw new WorkflowConflictError('Workflow was updated elsewhere')
  }
  if (obj) {
    const message = obj.thong_diep ?? obj.ma ?? JSON.stringify(obj)
    // ⭐ CHI 422 KEM `node_id` la loi bien dich do thi. Rieng `ma` thi khong
    //    du: `402 thieu_credit`, `429 qua_han_muc`, `503 dong_co_chua_san_sang`
    //    va `422 chua_publish`/`inputs_qua_lon` deu mang `ma` (runs_v3.py) va
    //    KHONG chi duoc node nao. Nem WorkflowCompileError cho chung se lam
    //    `CanvasShell` xu ly "het credit" nhu loi bien dich, voi `nodeId` rong
    //    — dung kieu gop nham vua go cho 409 o ngay tren.
    if (response.status === 422 && obj.node_id)
      throw new WorkflowCompileError(message, obj.ma ?? '', obj.node_id)
    throw new Error(message)
  }
  // `detail` con lai co the la MANG: `/agent/**` khong di qua bo viet lai cua
  // `server/api/errors.py` (chi nhan `/api/v1`), nen loi validate cua FastAPI
  // giu nguyen hinh `[{loc,msg,type}]`. `new Error(mang)` in ra "[object
  // Object]" tren man hinh nguoi dung.
  if (detail != null)
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  throw new Error(`Request failed (${response.status})`)
}

// `Accept: application/json` tuong minh cho MOI loi goi API — khong phu
// thuoc Sec-Fetch-Mode co song sot qua Cloudflare hay khong. Ban sua
// `da7fce81` phan biet "goi API" voi "dieu huong HTML" bang Sec-Fetch-Mode,
// lui ve Accept khi header do vang mat. Neu Cloudflare lot ca hai thi vong
// poll (Accept: */* mac dinh cua ham fetch toan cuc) se bi may chu coi la dieu huong va
// quay lai 302 — mat ban sua ma phep do loopback (khong qua Cloudflare) van
// xanh. Nen client tu gui Accept, khong cho no phu thuoc mot header co the
// bi CDN lot.
function withAcceptHeader(init?: RequestInit): HeadersInit {
  return { Accept: 'application/json', ...(init?.headers ?? {}) }
}

// Diem goi ham fetch toan cuc THO DUY NHAT cua module — moi ham API phai di
// qua day. tests/workflowApi.test.ts khang dinh dieu nay bang cach dem so
// loi goi fetch tho (chu thuong) trong tep nguon: phai la 1. Them mot loi
// goi fetch moi ma khong qua `apiFetch()` se lam phep kiem do do ngay, khong
// can sua tay.
function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  return fetch(path, { credentials: 'same-origin', ...init, headers: withAcceptHeader(init) })
}

async function request(path: string, init?: RequestInit) {
  return decode(await apiFetch(path, init))
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
  // ⚠️ Trang v3 do may chu tao moi (`drafts_v3.py::_tai_lieu_rong`) chi co
  //    id/name/nodes/edges. Cac truong TRINH BAY (viewport, frames, notes,
  //    comments) la tuy chon o ranh gioi nay: thieu thi dien mac dinh, neu
  //    khong `page.frames.map` nem va ca canvas thanh man den.
  return { ...canvas, version: 2,
    pages: canvas.pages.map(page => ({
      ...page,
      nodes: page.nodes ?? [],
      viewport: page.viewport ?? { x: 0, y: 0, zoom: 1 },
      frames: page.frames ?? [], notes: page.notes ?? [], comments: page.comments ?? [],
      edges: (page.edges ?? []).map(edgeFromV3) })) }
}

function normalizeWorkflow(workflow: Workflow): Workflow {
  return { ...workflow, canvas: normalizeCanvas(workflow.canvas as CanvasDocument | LegacyCanvasDocument) }
}

// ── Cua v3: `workflow_draft` (Dot 5.2 phan D) ──────────────────────────────
//
// ⭐ TRINH SOAN GIU HINH DANG CUA REACT FLOW; v3 la hinh dang LUU TRU.
//
//    `@xyflow/react` doi `sourceHandle`/`targetHandle` — do la hop dong cua
//    thu vien, khong phai mot lua chon cua ta. CSDL doi `source_port`/
//    `target_port` mang KIEU. Ep mot ben theo ben kia se lam mot trong hai
//    phai chuyen doi NGAM o giua, va cho chuyen doi ngam ay chinh la cho cong
//    bi danh roi lan truoc (`canvas_to_plan()`).
//
// ⇒ Chuyen doi o RANH GIOI, mot lan, bang `toV3`/`fromV3` — hai ham da co
//   `tests/test_968` chot rang chung khop tung chu voi may chu.

export type WorkflowV3 = {
  id: string
  name: string
  published_version_id: string
  revision: number
  document: CanvasDocumentV3
}

/** Ban ghi v3 tho -> hinh dang trinh soan dang dung. */
function tuV3(raw: WorkflowV3): Workflow {
  return {
    id: raw.id,
    name: raw.name,
    // v3 chua co truong `status` rieng: da publish thi coi la `validated`.
    status: raw.published_version_id ? 'validated' : 'draft',
    revision: raw.revision,
    estimated: 0,
    canvas: fromV3(raw.document),
  }
}

export const listWorkflowsV3 = async (): Promise<{ id: string; name: string;
  published: boolean }[]> => (await request('/agent/api/v3/workflows')).items

export async function loadWorkflowV3(id: string): Promise<Workflow> {
  return tuV3(await request(`/agent/api/v3/workflows/${encodeURIComponent(id)}`))
}

export async function createWorkflowV3(name: string,
                                       csrfToken: string): Promise<Workflow> {
  return tuV3(await request('/agent/api/v3/workflows', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
    body: JSON.stringify({ name, csrf_token: csrfToken }),
  }))
}

/** Mo workflow v3 dau tien, tao mot cai neu chua co. */
export async function loadOrCreateWorkflowV3(csrfToken: string): Promise<Workflow> {
  const items = await listWorkflowsV3()
  if (items.length) return loadWorkflowV3(items[0].id)
  return createWorkflowV3('Workflow mới', csrfToken)
}

export async function saveWorkflowV3(workflow: Workflow, csrfToken: string,
                                     signal?: AbortSignal): Promise<Workflow> {
  const response = await apiFetch(
    `/agent/api/v3/workflows/${encodeURIComponent(workflow.id)}`, {
      method: 'PUT',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken,
        // Khoa lac quan y het cua v2 — mot nguoi dung ca hai cua khong phai
        // hoc hai luat.
        'If-Match': `"${workflow.revision}"` },
      body: JSON.stringify({ document: toV3(workflow.canvas),
                             csrf_token: csrfToken }),
      signal,
    })
  return tuV3(await decode(response))
}

/** Dong bang ban nhap. Publish LAI cung noi dung tra ve dung version cu. */
export async function publishWorkflowV3(workflow: Workflow, csrfToken: string):
    Promise<{ workflow_id: string; version_id: string; credit_max: number;
              credit_estimate: number }> {
  return request(
    `/agent/api/v3/workflows/${encodeURIComponent(workflow.id)}/publish`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
      body: JSON.stringify({ csrf_token: csrfToken }),
    })
}

export const loadPalette = () => request('/agent/api/palette')

// ── Goi y cho trinh soan bieu thuc §6 (P2 Task 8) ──────────────────────────
//
// ⛔ KHONG mot danh sach ten ham hay ten cong nao o phia trinh duyet. May chu
//    sinh chung tu `ham_bieu_thuc.NHOM_HAM` va tu do thi × registry
//    (`platform_core/workflow/goi_y.py`); mot ban sao o day se lech ngay lan
//    them ham dau tien — dung hang loi `test_967` dang dem hang chet.
// ⭐ Gui KEM tai lieu dang go: autosave cham 800 ms, nen bang da luu chua co
//    node nguoi dung vua tha xuong — dung luc ho can no nhat.
export type MucGoiY = {
  duong: string
  loai: 'goc' | 'cong' | 'mat_node'
  node?: string
  cong?: string
  node_type?: string
  /** Cong publish (`bien_dich._doi`) co nhan bieu thuc nay khong. */
  qua_publish: boolean
}
export type HamGoiY = { ten: string; nhom: string; chu_ky: string
  qua_publish: boolean }
export type GoiYBieuThuc = {
  node_id: string
  muc: MucGoiY[]
  ham: HamGoiY[]
  loi: { ma: string; thong_diep: string } | null
}

export async function goiYBieuThuc(workflowId: string, nodeId: string,
                                   canvas: CanvasDocument, csrfToken: string):
    Promise<GoiYBieuThuc> {
  return request(
    `/agent/api/v3/workflows/${encodeURIComponent(workflowId)}/bieu-thuc/goi-y`,
    { method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
      body: JSON.stringify({ node_id: nodeId, document: toV3(canvas),
                             csrf_token: csrfToken }) }) as Promise<GoiYBieuThuc>
}

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
  const response = await apiFetch(`/agent/api/workflows/${workflow.id}/assistant/preview`, { method: 'POST',
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
  return decode(await apiFetch('/agent/api/assets', { method: 'POST', credentials: 'same-origin',
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
  const response = await apiFetch(`/agent/api/workflows/${workflow.id}`, {
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

// ── Cua v3: mot luot chay (Dot 5.2, apps/agent/routes/runs_v3.py) ─────────
export type RunV3Node = { node_id: string; status: string; attempt: number
  cost_credit: number; job_id: string; error: string
  // `WAITING` vi ly do GI (`DELAY|JOB|WEBHOOK|HUMAN|CHILD_RUN|BARRIER`,
  // khop nguyen `Waitpoint.kind`) -- rong khi node khong `WAITING`. Them P9
  // task 3 (coordinator, mo lai `main`/phase 5+6): mot node cho NGUOI DUYET
  // phai hien KHAC mot node cho webhook/loi, khong duoc gop chung nhan.
  waiting_kind: string }
export type RunV3Event = { seq: number; loai: string; node_id: string
  du_lieu: Record<string, unknown>; created_at: string }
export type RunV3 = { id: string; workflow_id: string; version_id: string
  status: string; credit_max: number; credit_charged: number; settled: boolean
  created_at: string; nodes: RunV3Node[]; su_kien: RunV3Event[]
  seq_cuoi: number }

/** Trạng thái kết thúc của run (spec §5.2). Vòng poll dừng ở đây. */
export const RUN_V3_KET_THUC: ReadonlySet<string> = new Set(
  ['SUCCEEDED', 'FAILED', 'CANCELLED', 'TIMED_OUT', 'SYSTEM_FAILURE'])

/**
 * Tạo một run v3.
 *
 * ⭐ `idempotencyKey` là **tham số bắt buộc**, và đó là cả thiết kế.
 *
 * Cửa `/agent/api/v3/workflows/{id}/runs` từ chối `400` khi thiếu header
 * `Idempotency-Key` (`runs_v3.py::_khoa_idempotency`, sửa 23/09 — đo được là
 * bấm hai lần trừ tiền hai lần).
 *
 * ⛔ Hàm này **không tự sinh** khoá. Sinh ở đây thì mỗi lời gọi là một khoá
 *    mới, kể cả hai lời gọi của **cùng một lần bấm** — trông như có chống
 *    trùng mà không chống được gì. Khoá phải sinh ở **chỗ người dùng bấm**, nơi
 *    duy nhất biết được đâu là "một lần bấm": xem `CanvasShell::chayWorkflow`.
 */
export async function createRunV3(workflowId: string, csrfToken: string,
                                  idempotencyKey: string): Promise<RunV3> {
  return request(`/agent/api/v3/workflows/${workflowId}/runs`, {
    method: 'POST', headers: { 'Content-Type': 'application/json',
      'X-CSRF-Token': csrfToken,
      'Idempotency-Key': idempotencyKey }, body: '{}' }) as Promise<RunV3>
}

/** `sau` = con trỏ sự kiện của lần poll trước (`seq_cuoi`). 0 = lấy cả lịch sử. */
export async function loadRunV3(runId: string, sau = 0): Promise<RunV3> {
  return request(`/agent/api/v3/runs/${runId}?sau=${sau}`) as Promise<RunV3>
}

export async function cancelRunV3(runId: string,
                                  csrfToken: string): Promise<RunV3> {
  return request(`/agent/api/v3/runs/${runId}/cancel`, {
    method: 'POST', headers: { 'Content-Type': 'application/json',
      'X-CSRF-Token': csrfToken }, body: '{}' }) as Promise<RunV3>
}
