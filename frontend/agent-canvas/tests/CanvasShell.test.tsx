import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { CanvasShell } from '../src/CanvasShell'

const palette = { version: 1, tools: [{ name: 'text.script', description: 'Viết kịch bản',
  app_slug: 'kichban', app_name: 'Kịch bản', requires: ['api'], verifiable: [],
  params_schema: { topic: { type: 'text', required: true } }, returns: { script: 'text' } }] }
const workflow = { id: 'w1', name: 'Workflow mới', status: 'draft', revision: 1, estimated: 0,
  canvas: { version: 1, goal: '', budget_max_credit: 50, nodes: [], edges: [],
    viewport: { x: 0, y: 0, zoom: 1 } } }

beforeEach(() => {
  document.body.innerHTML = '<div id="agent-canvas-root" data-csrf-token="test-csrf"></div>'
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input)
    if (url.endsWith('/palette')) return new Response(JSON.stringify(palette), { status: 200 })
    if (url.endsWith('/workflows') && !init?.method) return new Response(JSON.stringify({ items: [] }), { status: 200 })
    if (url.includes('/workflows/w1')) return new Response(JSON.stringify({ ...workflow, revision: 2 }), { status: 200 })
    return new Response(JSON.stringify(workflow), { status: 201 })
  })
})
afterEach(() => vi.restoreAllMocks())

describe('CanvasShell', () => {
  it('loads dynamic palette and adds/configures a tool node', async () => {
    render(<CanvasShell />)
    const add = await screen.findByRole('button', { name: 'Thêm text.script' })
    fireEvent.click(add)
    expect(await screen.findByLabelText('Node text.script')).toBeInTheDocument()
    fireEvent.click(screen.getByLabelText('Node text.script'))
    const topic = screen.getByRole('textbox', { name: /topic/ })
    fireEvent.change(topic, { target: { value: 'Chủ đề mới' } })
    expect(topic).toHaveValue('Chủ đề mới')
  })

  it('provides undo/redo and accessible regions', async () => {
    render(<CanvasShell />)
    const add = await screen.findByRole('button', { name: 'Thêm text.script' })
    expect(screen.getByRole('region', { name: 'LTT Agent Canvas' })).toBeInTheDocument()
    fireEvent.click(add)
    const undo = screen.getByRole('button', { name: 'Hoàn tác' })
    await waitFor(() => expect(undo).toBeEnabled())
    fireEvent.click(undo)
    expect(screen.queryByLabelText('Node text.script')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Làm lại' }))
    expect(screen.getByLabelText('Node text.script')).toBeInTheDocument()
  })
})
