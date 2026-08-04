import { describe, expect, it } from 'vitest'
import { activePage, connectionAllowed, editorReducer, emptyDocument, scopeNodeIds, type EditorState, type PaletteTool } from '../src/editorState'

const tool = (name: string, input: string, output: string): PaletteTool => ({ name,
  description: '', app_slug: 'x', app_name: 'X', requires: [], verifiable: [],
  params_schema: { input: { type: input } }, returns: { output } })

describe('editor reducer', () => {
  it('undoes, redoes and deletes nodes with their edges', () => {
    const document = emptyDocument()
    activePage(document).nodes = [
      { id: 'a', type: 'tool', position: { x: 0, y: 0 }, data: {} },
      { id: 'b', type: 'tool', position: { x: 1, y: 1 }, data: {} },
    ]
    activePage(document).edges = [{ id: 'a-b', source: 'a', target: 'b' }]
    let state: EditorState = { document, past: [], future: [] }
    state = editorReducer(state, { type: 'delete', ids: ['a'] })
    expect(activePage(state.document).nodes).toHaveLength(1); expect(activePage(state.document).edges).toHaveLength(0)
    state = editorReducer(state, { type: 'undo' }); expect(activePage(state.document).nodes).toHaveLength(2)
    state = editorReducer(state, { type: 'redo' }); expect(activePage(state.document).nodes).toHaveLength(1)
  })

  it('auto-layout changes positions only', () => {
    const document = emptyDocument()
    activePage(document).nodes = [{ id: 'a', type: 'tool', position: { x: 99, y: 99 }, data: { tool: 'x' } }]
    const state = editorReducer({ document, past: [], future: [] }, { type: 'layout' })
    expect(activePage(state.document).nodes[0].data).toEqual({ tool: 'x' })
    expect(activePage(state.document).nodes[0].position).toEqual({ x: 90, y: 90 })
  })

  it('disconnects selected edges without deleting their nodes and can undo', () => {
    const document = emptyDocument()
    activePage(document).nodes = [
      { id: 'a', type: 'tool', position: { x: 0, y: 0 }, data: {} },
      { id: 'b', type: 'tool', position: { x: 1, y: 1 }, data: {} },
    ]
    activePage(document).edges = [{ id: 'a-b', source: 'a', target: 'b' }]
    let state: EditorState = { document, past: [], future: [] }
    state = editorReducer(state, { type: 'deleteEdges', ids: ['a-b'] })
    expect(activePage(state.document).nodes).toHaveLength(2)
    expect(activePage(state.document).edges).toHaveLength(0)
    state = editorReducer(state, { type: 'undo' })
    expect(activePage(state.document).edges).toHaveLength(1)
  })

  it('keeps 100 nodes and 150 edges editable within the local budget', () => {
    const document = emptyDocument()
    activePage(document).nodes = Array.from({ length: 100 }, (_, index) => ({ id: `n${index}`,
      type: 'tool' as const, position: { x: index, y: index }, data: { tool: 'text.script' } }))
    activePage(document).edges = Array.from({ length: 150 }, (_, index) => ({ id: `e${index}`,
      source: `n${index % 99}`, target: `n${(index % 99) + 1}` }))
    const start = performance.now()
    let state: EditorState = { document, past: [], future: [] }
    state = editorReducer(state, { type: 'layout' })
    state = editorReducer(state, { type: 'delete', ids: ['n50'] })
    state = editorReducer(state, { type: 'undo' })
    expect(performance.now() - start).toBeLessThan(250)
    expect(activePage(state.document).nodes).toHaveLength(100)
    expect(activePage(state.document).edges).toHaveLength(150)
  })

  it('creates, renames, switches and deletes pages without leaking graph state', () => {
    const document = emptyDocument()
    activePage(document).nodes = [{ id: 'a', type: 'tool', position: { x: 0, y: 0 }, data: {} }]
    let state: EditorState = { document, past: [], future: [] }
    state = editorReducer(state, { type: 'pageAdd' })
    expect(state.document.pages).toHaveLength(2)
    expect(activePage(state.document).nodes).toHaveLength(0)
    const second = state.document.active_page_id
    state = editorReducer(state, { type: 'pageRename', id: second, name: 'Biến thể' })
    expect(activePage(state.document).name).toBe('Biến thể')
    state = editorReducer(state, { type: 'frameAdd', nodeIds: [] })
    state = editorReducer(state, { type: 'noteAdd', text: 'Ghi chú' })
    state = editorReducer(state, { type: 'commentAdd', text: 'Bình luận' })
    expect(activePage(state.document).frames).toHaveLength(1)
    expect(activePage(state.document).notes).toHaveLength(1)
    expect(activePage(state.document).comments).toHaveLength(1)
    const frame = activePage(state.document).frames[0]
    const note = activePage(state.document).notes[0]
    const comment = activePage(state.document).comments[0]
    state = editorReducer(state, { type: 'frameRename', id: frame.id, name: 'Cảnh mở đầu' })
    state = editorReducer(state, { type: 'annotationUpdate', kind: 'notes', id: note.id, text: 'Duyệt màu' })
    state = editorReducer(state, { type: 'annotationDelete', kind: 'comments', id: comment.id })
    expect(activePage(state.document).frames[0].name).toBe('Cảnh mở đầu')
    expect(activePage(state.document).notes[0].text).toBe('Duyệt màu')
    expect(activePage(state.document).comments).toHaveLength(0)
    state = editorReducer(state, { type: 'frameDelete', id: frame.id })
    expect(activePage(state.document).frames).toHaveLength(0)
    state = editorReducer(state, { type: 'pageDelete', id: second })
    expect(state.document.pages).toHaveLength(1)
    expect(activePage(state.document).nodes[0].id).toBe('a')
  })

  it('moves a node to another page and removes invalid cross-page edges',()=>{
    const document=emptyDocument();const first=activePage(document)
    first.nodes=[{id:'a',type:'tool',position:{x:0,y:0},data:{}},{id:'b',type:'tool',position:{x:1,y:1},data:{}}]
    first.edges=[{id:'a-b',source:'a',target:'b'}]
    let state:EditorState={document,past:[],future:[]};state=editorReducer(state,{type:'pageAdd'})
    const target=state.document.active_page_id;state=editorReducer(state,{type:'pageSelect',id:'page-1'})
    state=editorReducer(state,{type:'nodeMovePage',id:'a',pageId:target})
    expect(activePage(state.document).nodes.map(node=>node.id)).toEqual(['b'])
    expect(activePage(state.document).edges).toHaveLength(0)
    expect(state.document.pages.find(page=>page.id===target)?.nodes[0].id).toBe('a')
  })
})

describe('typed connection guard', () => {
  it('accepts matching ports and rejects mismatches', () => {
    expect(connectionAllowed(tool('a', 'text', 'video'), 'output', tool('b', 'video', 'text'), 'input')).toBe(true)
    expect(connectionAllowed(tool('a', 'text', 'video'), 'output', tool('b', 'image', 'text'), 'input')).toBe(false)
    expect(connectionAllowed(tool('a', 'text', 'text'), 'output', tool('b', 'enum', 'text'), 'input')).toBe(false)
  })

  it('limits a node run to that node and all transitive prerequisites',()=>{
    const nodes=['a','b','c','unrelated'].map((id,index)=>({id,type:'tool' as const,position:{x:index,y:0},data:{}}))
    const edges=[{id:'a-b',source:'a',target:'b'},{id:'b-c',source:'b',target:'c'}]
    expect(new Set(scopeNodeIds(nodes,edges,['c']))).toEqual(new Set(['a','b','c']))
    expect(scopeNodeIds(nodes,edges,['missing'])).toEqual([])
  })
})
