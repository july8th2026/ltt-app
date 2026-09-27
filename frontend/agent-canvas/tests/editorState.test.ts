import { describe, expect, it } from 'vitest'
import { activePage, cloneGraphSelection, connectionCreatesCycle, editorReducer, emptyDocument, scopeNodeIds, type EditorState, nextNode } from '../src/editorState'
import type { NodeDefinition } from '../src/nodeDefinition'

// ⛔ Bai `typed connection guard` va bai "doi Image node sang upload" DA XOA
//    cung `connectionAllowed`/`replaceNodeTool` (plan 02 task 15). Chung do
//    mot luat noi day GO CUNG o client tren `params_schema` phang cua palette
//    v2. Luat that gio tai tu `he_kieu.xuat_luat_noi_day()`; phep kiem cua no
//    o `tests/nodeDefinition.test.ts` (`noiDuoc`) va `tests/test_1750_*.py`.

describe('editor reducer', () => {
  it('rejects self-links and links that would close a graph cycle',()=>{
    const edges=[{id:'a-b',source:'a',target:'b'},{id:'b-c',source:'b',target:'c'}]
    expect(connectionCreatesCycle(edges,'c','a')).toBe(true)
    expect(connectionCreatesCycle(edges,'b','b')).toBe(true)
    expect(connectionCreatesCycle(edges,'a','c')).toBe(false)
  })
  it('undoes, redoes and deletes nodes with their edges', () => {
    const document = emptyDocument()
    activePage(document).nodes = [
      { id: 'a', type: 'tool', position: { x: 0, y: 0 }, data: {} },
      { id: 'b', type: 'tool', position: { x: 1, y: 1 }, data: {params:{input:'$a.output'}} },
    ]
    activePage(document).edges = [{ id: 'a-b', source: 'a',sourceHandle:'output', target: 'b',targetHandle:'input' }]
    let state: EditorState = { document, past: [], future: [] }
    state = editorReducer(state, { type: 'delete', ids: ['a'] })
    expect(activePage(state.document).nodes).toHaveLength(1); expect(activePage(state.document).edges).toHaveLength(0)
    expect(activePage(state.document).nodes[0].data.params).toEqual({})
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

  it('stores a display label outside executable node data',()=>{
    const document=emptyDocument()
    activePage(document).nodes=[{id:'a',type:'tool',position:{x:0,y:0},data:{tool:'text.generate'}}]
    const state=editorReducer({document,past:[],future:[]},{type:'nodeLabel',id:'a',label:'Lời dẫn mở đầu'})
    expect(activePage(state.document).nodes[0].label).toBe('Lời dẫn mở đầu')
    expect(activePage(state.document).nodes[0].data).toEqual({tool:'text.generate'})
  })

  it('disconnects selected edges without deleting their nodes and can undo', () => {
    const document = emptyDocument()
    activePage(document).nodes = [
      { id: 'a', type: 'tool', position: { x: 0, y: 0 }, data: {} },
      { id: 'b', type: 'tool', position: { x: 1, y: 1 }, data: {params:{input:'$a.output'}} },
    ]
    activePage(document).edges = [{ id: 'a-b', source: 'a',sourceHandle:'output', target: 'b',targetHandle:'input' }]
    let state: EditorState = { document, past: [], future: [] }
    state = editorReducer(state, { type: 'deleteEdges', ids: ['a-b'] })
    expect(activePage(state.document).nodes).toHaveLength(2)
    expect(activePage(state.document).edges).toHaveLength(0)
    expect(activePage(state.document).nodes[1].data.params).toEqual({})
    state = editorReducer(state, { type: 'undo' })
    expect(activePage(state.document).edges).toHaveLength(1)
    expect(activePage(state.document).nodes[1].data.params).toEqual({input:'$a.output'})
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

  it('duplicates a graph selection with internal edges and remapped references',()=>{
    const nodes=[
      {id:'source',type:'tool' as const,position:{x:10,y:20},data:{tool:'text.generate',params:{prompt:'gốc'}}},
      {id:'target',type:'tool' as const,position:{x:50,y:60},data:{tool:'image.generate',params:{prompt:'$source.text',refs:['$source.text']}}},
    ]
    const edges=[{id:'source-target',source:'source',sourceHandle:'text',target:'target',targetHandle:'prompt'}]
    const cloned=cloneGraphSelection(nodes,edges,'fixed')
    expect(cloned.nodeIds).toEqual(['source-copy-fixed-0','target-copy-fixed-1'])
    expect(cloned.nodes[1].data.params).toEqual({prompt:'$source-copy-fixed-0.text',refs:['$source-copy-fixed-0.text']})
    expect(cloned.edges).toEqual([{id:'source-copy-fixed-0-text-target-copy-fixed-1-prompt',
      source:'source-copy-fixed-0',sourceHandle:'text',target:'target-copy-fixed-1',targetHandle:'prompt'}])
    expect(cloned.nodes[0].position).toEqual({x:42,y:52})
  })

})

describe('pham vi chay mot node', () => {
  it('limits a node run to that node and all transitive prerequisites',()=>{
    const nodes=['a','b','c','unrelated'].map((id,index)=>({id,type:'tool' as const,position:{x:index,y:0},data:{}}))
    const edges=[{id:'a-b',source:'a',target:'b'},{id:'b-c',source:'b',target:'c'}]
    expect(new Set(scopeNodeIds(nodes,edges,['c']))).toEqual(new Set(['a','b','c']))
    expect(scopeNodeIds(nodes,edges,['missing'])).toEqual([])
  })
})

// ── UI-0 Task 5 — buoc xep phai RONG HON node ─────────────────────────────
describe('nextNode — buoc xep', () => {
  const nutGia = (): NodeDefinition => ({
    type: 'app.video.generate', type_version: 1, kind: 'app', category: 'LTT_APPS',
    title: 'Tao Video', description: '', icon: '', app_name: 'Video',
    cong_vao: [], cong_ra: [],
    tham_so: { type: 'object', properties: {}, required: [] },
    thi_hanh: 'job', side_effect: '', resource: {}, timeout_expr: '',
    retry_mac_dinh: { max: 0, backoff_s: 0 },
    gia: { kieu: 'mien_phi', so: 0, job_type: '' },
    credential: [], quyen: [], cho: [], ma_loi: [],
    co_mock: false, publish_duoc: true,
  })

  it('hai node lien tiep KHONG duoc de len nhau', () => {
    // Node RONG NHAT do duoc tren trinh duyet that 27/09/2026
    // (`app.video.generate`) la 456px. Buoc xep phai LON HON con so do —
    // buoc cu la 430px, nen node thu HAI de len node thu nhat 26px va che
    // mat duoi tieu de cua no.
    const RONG_NHAT = 456
    const a = nextNode(nutGia(), 0)
    const b = nextNode(nutGia(), 1)
    expect(b.position.x - a.position.x).toBeGreaterThan(RONG_NHAT)
  })

  it('xuong hang moi khi het mot hang ba node', () => {
    const a = nextNode(nutGia(), 0)
    const d = nextNode(nutGia(), 3)
    expect(d.position.x).toBe(a.position.x)
    expect(d.position.y).toBeGreaterThan(a.position.y)
  })
})
