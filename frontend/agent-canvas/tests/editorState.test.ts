import { describe, expect, it } from 'vitest'
import { activePage, cloneGraphSelection, connectionAllowed, connectionCreatesCycle, editorReducer, emptyDocument, replaceNodeTool, scopeNodeIds, type EditorState, type PaletteTool } from '../src/editorState'

const tool = (name: string, input: string, output: string): PaletteTool => ({ name,
  description: '', app_slug: 'x', app_name: 'X', requires: [], verifiable: [],
  params_schema: { input: { type: input } }, returns: { output } })

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

  it('switches an Image node from generated collection to owned upload without leaving a broken graph',()=>{
    const generated={...tool('image.generate','text','image[]'),params_schema:{prompt:{type:'text',required:true}},
      returns:{image_keys:'image[]'}}
    const uploaded={...tool('asset.image','string','image'),params_schema:{image_key:{type:'string',required:true}},
      returns:{image_key:'image'}}
    const text={...tool('text.generate','text','text'),params_schema:{prompt:{type:'string',required:true},
      image_key:{type:'image'},image_keys:{type:'image[]'}},returns:{text:'text'}}
    const page=activePage(emptyDocument())
    page.nodes=[
      {id:'source',type:'tool',position:{x:0,y:0},data:{tool:'text.generate',params:{prompt:'nguồn'}}},
      {id:'image',type:'tool',label:'Ảnh sản phẩm',position:{x:1,y:0},data:{tool:'image.generate',params:{prompt:'$source.text'}}},
      {id:'analysis',type:'tool',position:{x:2,y:0},data:{tool:'text.generate',params:{prompt:'phân tích',image_keys:'$image.image_keys'}}},
    ]
    page.edges=[
      {id:'source-image',source:'source',sourceHandle:'text',target:'image',targetHandle:'prompt'},
      {id:'image-analysis',source:'image',sourceHandle:'image_keys',target:'analysis',targetHandle:'image_keys'},
    ]
    const replaced=replaceNodeTool(page,'image',uploaded,[generated,uploaded,text],{
      params:{image_key:'agent-assets/u/owned.png'},asset_name:'owned.png',asset_url:'/preview/owned.png'})
    expect(replaced.nodes.find(node=>node.id==='image')).toMatchObject({label:'Ảnh sản phẩm',data:{
      tool:'asset.image',params:{image_key:'agent-assets/u/owned.png'},asset_name:'owned.png'}})
    expect(replaced.edges).toEqual([{id:'image-image_key-analysis-image_key',source:'image',
      sourceHandle:'image_key',target:'analysis',targetHandle:'image_key'}])
    expect(replaced.nodes.find(node=>node.id==='analysis')?.data.params).toMatchObject({
      prompt:'phân tích',image_key:'$image.image_key'})
    expect((replaced.nodes.find(node=>node.id==='analysis')?.data.params as Record<string,unknown>).image_keys).toBeUndefined()
  })
})

describe('typed connection guard', () => {
  it('accepts matching ports and rejects mismatches', () => {
    expect(connectionAllowed(tool('a', 'text', 'video'), 'output', tool('b', 'video', 'text'), 'input')).toBe(true)
    expect(connectionAllowed(tool('a', 'text', 'video'), 'output', tool('b', 'image', 'text'), 'input')).toBe(false)
    expect(connectionAllowed(tool('a', 'text', 'text'), 'output', tool('b', 'enum', 'text'), 'input')).toBe(false)
  })

  it('connects image and image collections to matching multimodal text inputs', () => {
    expect(connectionAllowed(tool('image-source', 'text', 'image'), 'output',
      tool('text-vision', 'image', 'text'), 'input')).toBe(true)
    expect(connectionAllowed(tool('batch-source', 'text', 'image[]'), 'output',
      tool('text-vision', 'image[]', 'text'), 'input')).toBe(true)
    expect(connectionAllowed(tool('batch-source', 'text', 'image[]'), 'output',
      tool('text-vision', 'image', 'text'), 'input')).toBe(false)
  })

  it('allows repeated scalar media outputs to feed collection merge inputs',()=>{
    expect(connectionAllowed(tool('video-source','text','video'),'output',
      tool('merge-video','video[]','video'),'input')).toBe(true)
    expect(connectionAllowed(tool('image-source','text','image'),'output',
      tool('merge-image','image[]','image'),'input')).toBe(true)
    expect(connectionAllowed(tool('audio-source','text','audio'),'output',
      tool('merge-video','video[]','video'),'input')).toBe(false)
  })

  it('keeps uploaded asset nodes as graph sources, never connection targets', () => {
    expect(connectionAllowed(tool('text.generate', 'text', 'text'), 'output',
      tool('asset.image', 'string', 'image'), 'input')).toBe(false)
  })

  it('keeps text context separate from the instruction prompt', () => {
    const source = tool('source-text', 'text', 'text')
    const target = {
      ...tool('text.generate', 'string', 'text'),
      params_schema: { prompt: { type: 'string' }, source_text: { type: 'text' } },
    }
    expect(connectionAllowed(source, 'output', target, 'prompt')).toBe(false)
    expect(connectionAllowed(source, 'output', target, 'source_text')).toBe(true)
    expect(connectionAllowed(source, 'output', tool('image.generate', 'string', 'image'), 'input')).toBe(true)
  })

  it('allows typed image and video references to drive a Video node',()=>{
    const videoTarget={...tool('video.generate','text','video'),params_schema:{
      prompt:{type:'text',required:true},image_key:{type:'image'},image_keys:{type:'image[]'},video_key:{type:'video'}},
      returns:{video_key:'video'}}
    expect(connectionAllowed(tool('asset.image','string','image'),'output',videoTarget,'image_key')).toBe(true)
    expect(connectionAllowed(tool('image.batch_generate','text','image[]'),'output',videoTarget,'image_keys')).toBe(true)
    expect(connectionAllowed(tool('asset.video','string','video'),'output',videoTarget,'video_key')).toBe(true)
    expect(connectionAllowed(tool('raw.json','text','json'),'output',{
      ...videoTarget,params_schema:{...videoTarget.params_schema,refs:{type:'json'}}},'refs')).toBe(false)
  })

  it('limits a node run to that node and all transitive prerequisites',()=>{
    const nodes=['a','b','c','unrelated'].map((id,index)=>({id,type:'tool' as const,position:{x:index,y:0},data:{}}))
    const edges=[{id:'a-b',source:'a',target:'b'},{id:'b-c',source:'b',target:'c'}]
    expect(new Set(scopeNodeIds(nodes,edges,['c']))).toEqual(new Set(['a','b','c']))
    expect(scopeNodeIds(nodes,edges,['missing'])).toEqual([])
  })
})
