import { describe, expect, it } from 'vitest'
import { connectionAllowed, editorReducer, emptyDocument, type EditorState, type PaletteTool } from '../src/editorState'

const tool = (name: string, input: string, output: string): PaletteTool => ({ name,
  description: '', app_slug: 'x', app_name: 'X', requires: [], verifiable: [],
  params_schema: { input: { type: input } }, returns: { output } })

describe('editor reducer', () => {
  it('undoes, redoes and deletes nodes with their edges', () => {
    const document = emptyDocument()
    document.nodes = [
      { id: 'a', type: 'tool', position: { x: 0, y: 0 }, data: {} },
      { id: 'b', type: 'tool', position: { x: 1, y: 1 }, data: {} },
    ]
    document.edges = [{ id: 'a-b', source: 'a', target: 'b' }]
    let state: EditorState = { document, past: [], future: [] }
    state = editorReducer(state, { type: 'delete', ids: ['a'] })
    expect(state.document.nodes).toHaveLength(1); expect(state.document.edges).toHaveLength(0)
    state = editorReducer(state, { type: 'undo' }); expect(state.document.nodes).toHaveLength(2)
    state = editorReducer(state, { type: 'redo' }); expect(state.document.nodes).toHaveLength(1)
  })

  it('auto-layout changes positions only', () => {
    const document = emptyDocument()
    document.nodes = [{ id: 'a', type: 'tool', position: { x: 99, y: 99 }, data: { tool: 'x' } }]
    const state = editorReducer({ document, past: [], future: [] }, { type: 'layout' })
    expect(state.document.nodes[0].data).toEqual({ tool: 'x' })
    expect(state.document.nodes[0].position).toEqual({ x: 0, y: 0 })
  })

  it('disconnects selected edges without deleting their nodes and can undo', () => {
    const document = emptyDocument()
    document.nodes = [
      { id: 'a', type: 'tool', position: { x: 0, y: 0 }, data: {} },
      { id: 'b', type: 'tool', position: { x: 1, y: 1 }, data: {} },
    ]
    document.edges = [{ id: 'a-b', source: 'a', target: 'b' }]
    let state: EditorState = { document, past: [], future: [] }
    state = editorReducer(state, { type: 'deleteEdges', ids: ['a-b'] })
    expect(state.document.nodes).toHaveLength(2)
    expect(state.document.edges).toHaveLength(0)
    state = editorReducer(state, { type: 'undo' })
    expect(state.document.edges).toHaveLength(1)
  })

  it('keeps 100 nodes and 150 edges editable within the local budget', () => {
    const document = emptyDocument()
    document.nodes = Array.from({ length: 100 }, (_, index) => ({ id: `n${index}`,
      type: 'tool' as const, position: { x: index, y: index }, data: { tool: 'text.script' } }))
    document.edges = Array.from({ length: 150 }, (_, index) => ({ id: `e${index}`,
      source: `n${index % 99}`, target: `n${(index % 99) + 1}` }))
    const start = performance.now()
    let state: EditorState = { document, past: [], future: [] }
    state = editorReducer(state, { type: 'layout' })
    state = editorReducer(state, { type: 'delete', ids: ['n50'] })
    state = editorReducer(state, { type: 'undo' })
    expect(performance.now() - start).toBeLessThan(1000)
    expect(state.document.nodes).toHaveLength(100)
    expect(state.document.edges).toHaveLength(150)
  })
})

describe('typed connection guard', () => {
  it('accepts matching ports and rejects mismatches', () => {
    expect(connectionAllowed(tool('a', 'text', 'video'), 'output', tool('b', 'video', 'text'), 'input')).toBe(true)
    expect(connectionAllowed(tool('a', 'text', 'video'), 'output', tool('b', 'image', 'text'), 'input')).toBe(false)
  })
})
