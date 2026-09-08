import { afterEach, describe, expect, it, vi } from 'vitest'
import { approveRun, cloneWorkflow, createAutosave, createRun, exportWorkflow, importWorkflow,
  fromV3, loadRun, loadRunHistory, restoreRunAsWorkflow, saveWorkflow, toV3,
  WorkflowConflictError,
  type AgentRun, type Workflow } from '../src/workflowApi'

const workflow = { id: 'w1', name: 'A', revision: 3, status: 'draft', estimated: 0,
  canvas: { version: 2, goal: 'g', budget_max_credit: 10, active_page_id: 'page-1',
    pages: [{ id: 'page-1', name: 'Page 1', nodes: [], edges: [],
      viewport: { x: 0, y: 0, zoom: 1 }, frames: [], notes: [], comments: [] }] } } satisfies Workflow

afterEach(() => { vi.restoreAllMocks(); vi.useRealTimers() })

describe('workflow API', () => {
  it('uses CSRF and If-Match without sending client price', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(workflow), { status: 200,
        headers: { 'Content-Type': 'application/json' } }))
    await saveWorkflow(workflow, 'csrf-test')
    const init = fetchMock.mock.calls[0][1]!
    expect(new Headers(init.headers).get('If-Match')).toBe('"3"')
    expect(new Headers(init.headers).get('X-CSRF-Token')).toBe('csrf-test')
    expect(init.body).not.toContain('estimated')
  })

  it('surfaces revision conflicts', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('{}', { status: 409 }))
    await expect(saveWorkflow(workflow, 'csrf-test')).rejects.toBeInstanceOf(WorkflowConflictError)
  })

  it('binds run creation to workflow revision and approval to quote hash', async () => {
    const run = { id: 'r1', version: 1, status: 'awaiting_approval', plan: { steps: [] },
      checkpoint: {}, estimated: 5, actual: 0, quote_hash: 'abc', decisions: [], artifacts: [] } satisfies AgentRun
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async () => new Response(
      JSON.stringify(run), { status: 200, headers: { 'Content-Type': 'application/json' } }))
    await createRun(workflow, 'csrf-test', { mode: 'selection', node_ids: ['n1'] })
    expect(new Headers(fetchMock.mock.calls[0][1]?.headers).get('If-Match')).toBe('"3"')
    expect(fetchMock.mock.calls[0][1]?.body).toBe(JSON.stringify({ scope: { mode: 'selection', node_ids: ['n1'] }, use_cache: true }))
    await approveRun(run, 'csrf-test')
    expect(fetchMock.mock.calls[1][1]?.body).toBe(JSON.stringify({ version: 1, quote_hash: 'abc' }))
    await approveRun(run, 'csrf-test', '2026-08-04T02:00:00.000Z')
    expect(fetchMock.mock.calls[2][1]?.body).toContain('2026-08-04T02:00:00.000Z')
  })

  it('loads owner run history/detail and reuses workflow template contracts', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async input => {
      const url = String(input)
      const body = url.endsWith('/runs') ? { items: [{ id: 'r1' }] }
        : url.endsWith('/runs/r1') ? { id: 'r1' }
        : url.endsWith('/export') ? { schema: 'ltt.agent.workflow' } : workflow
      return new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } })
    })
    await expect(loadRunHistory()).resolves.toEqual([{ id: 'r1' }])
    await expect(loadRun('r1')).resolves.toMatchObject({ id: 'r1' })
    await cloneWorkflow(workflow, 'csrf-test')
    await exportWorkflow(workflow)
    await importWorkflow({ schema: 'ltt.agent.workflow' }, 'csrf-test')
    await restoreRunAsWorkflow({id:'r1'} as AgentRun,'csrf-test')
    expect(fetchMock.mock.calls.map(call => String(call[0]))).toEqual([
      '/agent/api/runs', '/agent/api/runs/r1', '/agent/api/workflows/w1/clone',
      '/agent/api/workflows/w1/export', '/agent/api/workflows/import',
      '/agent/api/runs/r1/restore-workflow'])
    expect(new Headers(fetchMock.mock.calls[2][1]?.headers).get('X-CSRF-Token')).toBe('csrf-test')
    expect(fetchMock.mock.calls[4][1]?.body).toBe(JSON.stringify({ schema: 'ltt.agent.workflow' }))
    expect(new Headers(fetchMock.mock.calls[5][1]?.headers).get('X-CSRF-Token')).toBe('csrf-test')
  })

  it('debounces autosave and persists only latest value', async () => {
    vi.useFakeTimers()
    const save = vi.fn(async (_value: number) => {})
    const autosave = createAutosave(save, 500)
    autosave.schedule(1); autosave.schedule(2)
    await vi.advanceTimersByTimeAsync(500)
    expect(save).toHaveBeenCalledTimes(1)
    expect(save).toHaveBeenCalledWith(2)
  })
})

// ── Canvas v3 (Dot 5.2) ────────────────────────────────────────────────────
describe('canvas v3', () => {
  // ⚠️ CO Y dung cong KHAC mac dinh. Bo du lieu dung 'out'/'in' se KHONG phan
  //    biet duoc "giu cong that" voi "hard-code gia tri du phong" — hai duong
  //    cho ra cung ket qua. Bai hoc nay da tra gia o Dot 4 va o `M-1`.
  const v2 = { version: 2 as const, goal: 'g', budget_max_credit: 10,
    active_page_id: 'p1', pages: [{ id: 'p1', name: 'P', nodes: [],
      edges: [{ id: 'e1', source: 'a', target: 'b',
        sourceHandle: 'anh_ra', targetHandle: 'van_ban_vao' }],
      viewport: { x: 0, y: 0, zoom: 1 }, frames: [], notes: [], comments: [] }] }

  it('giu cong khi len v3, va dung DUNG ten truong cua may chu', () => {
    const e = toV3(v2).pages[0].edges[0]
    expect(e).toEqual({ id: 'e1', source_node: 'a', target_node: 'b',
      source_port: 'anh_ra', target_port: 'van_ban_vao', kind: 'DATA' })
    // Khong con ten cu sot lai — mot truong thua se di thang vao CSDL.
    expect(Object.keys(e).sort()).toEqual(
      ['id', 'kind', 'source_node', 'source_port', 'target_node', 'target_port'])
  })

  it('canh KHONG khai cong thi roi ve mac dinh cua may chu', () => {
    const tran = { ...v2, pages: [{ ...v2.pages[0],
      edges: [{ id: 'e2', source: 'a', target: 'b' }] }] }
    const e = toV3(tran).pages[0].edges[0]
    expect([e.source_port, e.target_port]).toEqual(['out', 'in'])
  })

  it('vong tron v2 -> v3 -> v2 khong danh roi cong', () => {
    const lai = fromV3(toV3(v2))
    expect(lai.version).toBe(2)
    expect(lai.pages[0].edges[0].sourceHandle).toBe('anh_ra')
    expect(lai.pages[0].edges[0].targetHandle).toBe('van_ban_vao')
  })

  it('toV3 tren mot tai lieu DA la v3 tra ve nguyen (luy dang)', () => {
    const ba = toV3(v2)
    expect(toV3(ba)).toBe(ba)
  })

  it('nang v1 thang len v3', () => {
    const v1 = { version: 1 as const, goal: 'g', budget_max_credit: 5,
      nodes: [], edges: [{ id: 'e', source: 'a', target: 'b' }],
      viewport: { x: 0, y: 0, zoom: 1 } }
    const ra = toV3(v1)
    expect(ra.version).toBe(3)
    expect(ra.pages[0].edges[0].source_node).toBe('a')
  })
})
