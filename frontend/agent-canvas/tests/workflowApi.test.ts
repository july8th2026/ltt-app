import { afterEach, describe, expect, it, vi } from 'vitest'
import { approveRun, createAutosave, createRun, saveWorkflow, WorkflowConflictError,
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
