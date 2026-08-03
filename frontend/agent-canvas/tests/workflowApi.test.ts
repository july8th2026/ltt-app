import { afterEach, describe, expect, it, vi } from 'vitest'
import { approveRun, cloneWorkflow, createAutosave, createRun, exportWorkflow, importWorkflow,
  loadRun, loadRunHistory, restoreRunAsWorkflow, saveWorkflow, WorkflowConflictError,
  type AgentRun, type Workflow } from '../src/workflowApi'

const workflow = { id: 'w1', name: 'A', revision: 3, status: 'draft', estimated: 0,
  canvas: { version: 1, goal: 'g', budget_max_credit: 10, nodes: [], edges: [],
    viewport: { x: 0, y: 0, zoom: 1 } } } satisfies Workflow

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
    await createRun(workflow, 'csrf-test')
    expect(new Headers(fetchMock.mock.calls[0][1]?.headers).get('If-Match')).toBe('"3"')
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
