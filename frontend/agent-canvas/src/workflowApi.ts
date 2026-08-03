export type CanvasNode = {
  id: string
  type: 'tool'
  position: { x: number; y: number }
  data: Record<string, unknown>
}

export type CanvasEdge = { id: string; source: string; target: string;
  sourceHandle?: string | null; targetHandle?: string | null;
  data?: { condition?: 'success'|'error' } }

export type CanvasDocument = {
  version: 1
  goal: string
  budget_max_credit: number
  nodes: CanvasNode[]
  edges: CanvasEdge[]
  viewport: { x: number; y: number; zoom: number }
}

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

export const loadPalette = () => request('/agent/api/palette')

export async function planWorkflow(goal: string, budgetMax: number,
                                   csrfToken: string): Promise<Workflow> {
  return request('/agent/api/workflows/plan', { method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
    body: JSON.stringify({ goal, budget_max_credit: budgetMax }) })
}

export async function loadOrCreateWorkflow(csrfToken: string): Promise<Workflow> {
  const listing = await request('/agent/api/workflows')
  if (listing.items.length) return request(`/agent/api/workflows/${listing.items[0].id}`)
  return request('/agent/api/workflows', { method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
    body: JSON.stringify({ name: 'Workflow mới', canvas: {
      version: 1, goal: '', budget_max_credit: 50, nodes: [], edges: [],
      viewport: { x: 0, y: 0, zoom: 1 },
    } }) })
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
  return decode(response)
}

export async function validateWorkflow(workflow: Workflow, csrfToken: string) {
  return request(`/agent/api/workflows/${workflow.id}/validate`, { method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken,
      'If-Match': `"${workflow.revision}"` }, body: '{}' })
}

export async function createRun(workflow: Workflow, csrfToken: string): Promise<AgentRun> {
  return request(`/agent/api/workflows/${workflow.id}/runs`, { method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken,
      'If-Match': `"${workflow.revision}"` }, body: '{}' })
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
  return request(`/agent/api/runs/${run.id}/restore-workflow`,{method:'POST',
    headers:{'Content-Type':'application/json','X-CSRF-Token':csrfToken},body:'{}'})
}

export async function loadRunHistory():Promise<AgentRunSummary[]>{
  return (await request('/agent/api/runs')).items
}

export async function loadRun(id:string):Promise<AgentRun>{
  return request(`/agent/api/runs/${id}`)
}

export async function cloneWorkflow(workflow:Workflow,csrfToken:string):Promise<Workflow>{
  return request(`/agent/api/workflows/${workflow.id}/clone`,{method:'POST',
    headers:{'Content-Type':'application/json','X-CSRF-Token':csrfToken},body:'{}'})
}

export async function exportWorkflow(workflow:Workflow){
  return request(`/agent/api/workflows/${workflow.id}/export`)
}

export async function importWorkflow(payload:unknown,csrfToken:string):Promise<Workflow>{
  return request('/agent/api/workflows/import',{method:'POST',
    headers:{'Content-Type':'application/json','X-CSRF-Token':csrfToken},body:JSON.stringify(payload)})
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
