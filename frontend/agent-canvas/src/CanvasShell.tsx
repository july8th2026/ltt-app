import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from 'react'
import { addEdge, applyEdgeChanges, applyNodeChanges, Background, Controls, MiniMap,
  ReactFlow, ReactFlowProvider, useReactFlow, type Connection, type EdgeChange,
  type NodeChange } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import './canvas.css'
import { activePage, connectionAllowed, editorReducer, emptyDocument, nextNode,
  type PaletteTool } from './editorState'
import { Inspector } from './Inspector'
import { AnnotationNode, FrameNode, ToolNode } from './ToolNode'
import { applyAssistant, approveRun, cancelRun, cloneWorkflow, createRun, createShare, exportWorkflow, importWorkflow,
  loadOrCreateWorkflow, loadPalette, loadRun, loadRunHistory, loadSnapshots, planWorkflow, restoreSnapshot, saveWorkflow,
  previewAssistant, quoteTool, restoreRunAsWorkflow, runAgain, tickRun, WorkflowConflictError, validateWorkflow, type AgentRun, type AgentRunSummary, type AssistantResult, type CanvasDocument,
  type CanvasEdge, type CanvasNode, type Workflow, type WorkflowSnapshot } from './workflowApi'

const nodeTypes = { tool: ToolNode, frame: FrameNode, annotation: AnnotationNode }

function Editor() {
  const [state, dispatch] = useReducer(editorReducer, { document: emptyDocument(), past: [], future: [] })
  const [workflow, setWorkflow] = useState<Workflow>()
  const [palette, setPalette] = useState<PaletteTool[]>([])
  const [catalogMeta,setCatalogMeta]=useState({models:0,routing:''})
  const [phase, setPhase] = useState<'loading' | 'ready' | 'saving' | 'saved' | 'conflict' | 'error'>('loading')
  const [offline, setOffline] = useState(!navigator.onLine)
  const [selected, setSelected] = useState<string[]>([])
  const [selectedEdges, setSelectedEdges] = useState<string[]>([])
  const [readOnly, setReadOnly] = useState(window.innerWidth <= 640)
  const [mobilePanel,setMobilePanel]=useState<'canvas'|'palette'|'inspector'>('canvas')
  const [showLayers,setShowLayers]=useState(false)
  const [commandOpen,setCommandOpen]=useState(false)
  const [commandQuery,setCommandQuery]=useState('')
  const [costs, setCosts] = useState<Record<string, number>>({})
  const [liveQuotes,setLiveQuotes]=useState<Record<string,number>>({})
  const [retryNonce, setRetryNonce] = useState(0)
  const [validationIssues, setValidationIssues] = useState<{ step_id: string; message: string }[]>([])
  const [run, setRun] = useState<AgentRun>()
  const [runHistory,setRunHistory]=useState<AgentRunSummary[]>([])
  const [runError, setRunError] = useState('')
  const [scheduledAt,setScheduledAt]=useState('')
  const [runScope,setRunScope]=useState('full')
  const [useCache,setUseCache]=useState(true)
  const [assistantOpen,setAssistantOpen]=useState(false)
  const [assistantMode,setAssistantMode]=useState<'analyze'|'improve'>('analyze')
  const [assistantPrompt,setAssistantPrompt]=useState('')
  const [assistantResult,setAssistantResult]=useState<AssistantResult>({})
  const [assistantBusy,setAssistantBusy]=useState(false)
  const [historyOpen,setHistoryOpen]=useState(false)
  const [snapshots,setSnapshots]=useState<WorkflowSnapshot[]>([])
  const [sharePermission,setSharePermission]=useState<'view'|'clone'>('view')
  const [sharePath,setSharePath]=useState('')
  const copied = useRef<CanvasNode[]>([])
  const autosaveTimer = useRef<number | undefined>(undefined)
  const dragBefore = useRef<CanvasDocument | undefined>(undefined)
  const csrf = document.querySelector<HTMLElement>('#agent-canvas-root')?.dataset.csrfToken ?? ''
  const reactFlow = useReactFlow()
  const page = activePage(state.document)
  const showGrid=page.view?.grid??true
  const showConnections=page.view?.connections??true
  const showMinimap=page.view?.minimap??true
  const byName = useMemo(() => new Map(palette.map(tool => [tool.name, tool])), [palette])
  const selectedNode = page.nodes.find(node => node.id === state.selectedId)
  const selectedEdge = page.edges.find(edge=>selectedEdges.includes(edge.id))
  const refreshRunHistory=useCallback(()=>loadRunHistory().then(setRunHistory).catch(()=>setRunHistory([])),[])

  useEffect(() => {
    let active = true
    Promise.all([loadPalette(), loadOrCreateWorkflow(csrf)]).then(([result, loaded]) => {
      if (!active) return
      setPalette(result.tools); setCatalogMeta({models:result.models?.length??0,
        routing:result.routing?.mode??''}); setWorkflow(loaded); dispatch({ type: 'replace', document: loaded.canvas }); setPhase('ready')
    }).catch(() => active && setPhase('error'))
    return () => { active = false }
  }, [csrf])
  useEffect(()=>{void refreshRunHistory()},[refreshRunHistory])

  useEffect(() => {
    const online = () => setOffline(false); const offlineNow = () => setOffline(true)
    const resize = () => setReadOnly(window.innerWidth <= 640)
    window.addEventListener('online', online); window.addEventListener('offline', offlineNow); window.addEventListener('resize', resize)
    return () => { window.removeEventListener('online', online); window.removeEventListener('offline', offlineNow); window.removeEventListener('resize', resize) }
  }, [])

  useEffect(() => {
    const shortcut = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault(); setCommandOpen(true)
      } else if (event.key === 'Escape') { setCommandOpen(false); setShowLayers(false) }
    }
    window.addEventListener('keydown', shortcut)
    return () => window.removeEventListener('keydown', shortcut)
  }, [])

  useEffect(() => {
    if (!run || run.status !== 'running') return
    const scheduledDelay=run.scheduled_at?new Date(run.scheduled_at).getTime()-Date.now():0
    const delay=scheduledDelay>0?Math.min(60_000,Math.max(1200,scheduledDelay)):1200
    const timer = window.setTimeout(() => { void tickRun(run, csrf).then(next=>{setRun(next);void refreshRunHistory()})
      .catch(() => setPhase('error')) }, delay)
    return () => window.clearTimeout(timer)
  }, [run, csrf])

  useEffect(() => {
    if (!workflow || phase === 'loading' || offline) return
    if (JSON.stringify(workflow.canvas) === JSON.stringify(state.document)) return
    setValidationIssues([])
    autosaveTimer.current = window.setTimeout(async () => {
      setPhase('saving')
      try {
        const saved = await saveWorkflow({ ...workflow, canvas: state.document }, csrf)
        setWorkflow(saved); setPhase('saved')
      } catch (error) { setPhase(error instanceof WorkflowConflictError ? 'conflict' : 'error') }
    }, 800)
    return () => { if (autosaveTimer.current) window.clearTimeout(autosaveTimer.current) }
  }, [state.document, csrf, offline, retryNonce]) // workflow intentionally excluded: revision update is not an edit

  useEffect(()=>{
    if (!page.nodes.length || offline) { setLiveQuotes({}); return }
    const timer=window.setTimeout(()=>{void Promise.all(page.nodes.map(async node=>{
      try { return [node.id,await quoteTool(String(node.data.tool),(node.data.params??{}) as Record<string,unknown>,
        Number(node.data.fanout??1),Number(node.data.max_retry??0),csrf)] as const }
      catch { return undefined }
    })).then(rows=>setLiveQuotes(Object.fromEntries(rows.filter(Boolean) as readonly (readonly [string,number])[])))},450)
    return()=>window.clearTimeout(timer)
  },[page.nodes,csrf,offline])

  const addTool = useCallback((tool: PaletteTool, position?: { x: number; y: number }) => {
    if (readOnly) return
    const node = nextNode(tool, page.nodes.length)
    if (position) node.position = position
    dispatch({ type: 'graph', nodes: [...page.nodes, node], edges: page.edges })
    dispatch({ type: 'select', id: node.id })
  }, [readOnly, page])

  const onConnect = useCallback((connection: Connection) => {
    const sourceNode = page.nodes.find(node => node.id === connection.source)
    const targetNode = page.nodes.find(node => node.id === connection.target)
    const sourceTool = byName.get(String(sourceNode?.data.tool)); const targetTool = byName.get(String(targetNode?.data.tool))
    if (!connectionAllowed(sourceTool, connection.sourceHandle, targetTool, connection.targetHandle)) return
    const edges = addEdge({ ...connection, id: `${connection.source}-${connection.sourceHandle}-${connection.target}-${connection.targetHandle}` }, page.edges) as CanvasEdge[]
    const nodes = page.nodes.map(node => node.id === connection.target
      ? { ...node, data: { ...node.data, params: { ...(node.data.params as object ?? {}),
        [connection.targetHandle!]: `$${connection.source}.${connection.sourceHandle}` } } } : node)
    dispatch({ type: 'graph', nodes, edges })
  }, [byName, page])

  const duplicate = useCallback(() => {
    if (readOnly) return
    const source = selected.length ? page.nodes.filter(node => selected.includes(node.id)) : copied.current
    const clones = source.map((node, index) => ({ ...structuredClone(node), id: `${node.id}-copy-${Date.now()}-${index}`,
      position: { x: node.position.x + 32, y: node.position.y + 32 } }))
    if (clones.length) dispatch({ type: 'graph', nodes: [...page.nodes, ...clones], edges: page.edges })
  }, [readOnly, selected, page])
  const toggleErrorBranch=()=>{if(!selectedEdge||readOnly)return;const condition=selectedEdge.data?.condition==='error'?'success':'error';dispatch({type:'graph',nodes:page.nodes,edges:page.edges.map(edge=>edge.id===selectedEdge.id?{...edge,data:{...edge.data,condition}}:edge)})}
  const activateWorkflow=(next:Workflow)=>{setWorkflow(next);dispatch({type:'replace',document:next.canvas});setRun(undefined);setCosts({});setValidationIssues([]);setPhase('ready')}
  const cloneCurrent=async()=>{if(!workflow)return;try{activateWorkflow(await cloneWorkflow(workflow,csrf))}catch{setPhase('error')}}
  const downloadTemplate=async()=>{if(!workflow)return;try{const payload=await exportWorkflow(workflow);const url=URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}));const link=document.createElement('a');link.href=url;link.download=`workflow-${workflow.id}.json`;link.click();URL.revokeObjectURL(url)}catch{setPhase('error')}}
  const importTemplate=async(event:React.ChangeEvent<HTMLInputElement>)=>{const file=event.target.files?.[0];if(!file)return;try{activateWorkflow(await importWorkflow(JSON.parse(await file.text()),csrf))}catch{setPhase('error')}finally{event.target.value=''}}
  const onSelectionChange = useCallback(({ nodes, edges }: { nodes: { id: string }[]; edges: { id: string }[] }) => {
    const next = nodes.map(node => node.id).sort()
    const nextEdges = edges.map(edge => edge.id).sort()
    if (nextEdges.length) dispatch({ type: 'select' })
    else if (next.length === 1) dispatch({ type: 'select', id: next[0] })
    setSelected(previous => previous.length === next.length && previous.every((id, index) => id === next[index])
      ? previous : next)
    setSelectedEdges(previous => previous.length === nextEdges.length && previous.every((id, index) => id === nextEdges[index])
      ? previous : nextEdges)
  }, [])

  const onKeyDown = (event: React.KeyboardEvent) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault(); setCommandOpen(true); return
    }
    if (event.key === 'Escape') { setCommandOpen(false); setShowLayers(false); return }
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'z') { event.preventDefault(); dispatch({ type: event.shiftKey ? 'redo' : 'undo' }); return }
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'y') { event.preventDefault(); dispatch({ type: 'redo' }); return }
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'd') { event.preventDefault(); duplicate(); return }
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'c') copied.current = page.nodes.filter(node => selected.includes(node.id)).map(node => structuredClone(node))
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'v') { event.preventDefault(); duplicate() }
    if (!readOnly && ['Delete', 'Backspace'].includes(event.key) && (selected.length || selectedEdges.length)) {
      event.preventDefault()
      dispatch(selectedEdges.length ? { type: 'deleteEdges', ids: selectedEdges } : { type: 'delete', ids: selected })
    }
  }

  const displayNodes = useMemo(() => {
    const tools = page.nodes.map(node => ({ ...node,
    selected: node.id === state.selectedId || selected.includes(node.id),
    data: { ...node.data, __tool: byName.get(String(node.data.tool)), __cost: liveQuotes[node.id]??costs[node.id],
      __readOnly: readOnly,
      __onParamChange: (name:string,value:unknown) => dispatch({type:'update',id:node.id,data:{
        params:{...((node.data.params??{}) as Record<string,unknown>),[name]:value}}}),
      __status: String(run?.checkpoint[node.id]?.status ??
        (validationIssues.some(issue => issue.step_id === node.id) ? 'invalid'
        : costs[node.id] === undefined ? 'draft' : 'validated')),
      __artifacts: (run?.artifacts ?? []).filter(item => item.step_id === node.id) } }))
    const frames = page.frames.map(frame => {
      const members = page.nodes.filter(node => frame.node_ids.includes(node.id))
      const minX = Math.min(...members.map(node => node.position.x), 80)
      const minY = Math.min(...members.map(node => node.position.y), 80)
      const maxX = Math.max(...members.map(node => node.position.x + 230), 310)
      const maxY = Math.max(...members.map(node => node.position.y + 150), 230)
      return { id: `decoration-frame-${frame.id}`, type: 'frame',
        position: { x: minX - 34, y: minY - 52 }, draggable: false, selectable: false,
        connectable: false, zIndex: -1, style: { width: maxX - minX + 68, height: maxY - minY + 86 },
        data: { name: frame.name, count: frame.node_ids.length } }
    })
    const notes = page.notes.map((note, index) => ({ id: `decoration-note-${note.id}`,
      type: 'annotation', position: { x: note.x ?? 380 + index * 220, y: note.y ?? 100 },
      draggable: false, selectable: false, connectable: false, zIndex: 2,
      data: { kind: 'note', text: note.text } }))
    const comments = page.comments.map((comment, index) => ({ id: `decoration-comment-${comment.id}`,
      type: 'annotation', position: { x: comment.x ?? 420 + index * 220, y: comment.y ?? 320 },
      draggable: false, selectable: false, connectable: false, zIndex: 3,
      data: { kind: 'comment', text: comment.text } }))
    return [...frames, ...tools, ...notes, ...comments]
  }, [page, state.selectedId, selected, byName, costs, liveQuotes, validationIssues, run, readOnly])
  const displayEdges = useMemo(() => (showConnections ? page.edges : []).map(edge => {
    const isError = edge.data?.condition === 'error'
    return { ...edge, selected: selectedEdges.includes(edge.id), label: isError ? 'Lỗi' : undefined,
      animated: isError, className: isError ? 'error-branch' : undefined }
  }), [page.edges, selectedEdges, showConnections])
  if (phase === 'loading') return <section className="canvas-state" aria-live="polite">Đang tải workflow…</section>
  if (phase === 'error' && !workflow) return <section className="canvas-state error" role="alert">Không tải được Canvas. <button onClick={() => location.reload()}>Thử lại</button></section>
  const groups = palette.reduce<Record<string, PaletteTool[]>>((result, tool) => {
    const group = tool.requires.includes('gpu') ? 'GPU' : tool.name.startsWith('video.')
      ? 'Video' : tool.name.startsWith('image.') ? 'Ảnh' : 'Text'
    ;(result[group] ??= []).push(tool)
    return result
  }, {})
  const connectionOptions = selectedNode && byName.get(String(selectedNode.data.tool))
    ? Object.fromEntries(Object.keys(byName.get(String(selectedNode.data.tool))!.params_schema).map(field => [field,
      page.nodes.flatMap(source => {
        if (source.id === selectedNode.id) return []
        const sourceTool = byName.get(String(source.data.tool))
        return Object.keys(sourceTool?.returns ?? {}).filter(output =>
          connectionAllowed(sourceTool, output, byName.get(String(selectedNode.data.tool)), field))
          .map(output => ({ value: `${source.id}|${output}`, label: `${source.id} · ${output}` }))
      })])) : {}
  return <section className="canvas-shell" aria-label="LTT Agent Canvas" tabIndex={0} onKeyDown={onKeyDown}>
    <header className="canvas-toolbar"><div className="workflow-identity"><input aria-label="Tên workflow"
      value={workflow?.name ?? ''} disabled={!workflow || readOnly} onChange={event=>workflow&&setWorkflow({...workflow,name:event.target.value})}
      onBlur={()=>workflow&&saveWorkflow({...workflow,canvas:state.document},csrf).then(setWorkflow).catch(()=>setPhase('error'))}/>
      <span>{readOnly ? 'Mobile · chỉ xem' : `Canvas v2 · ${page.name} · server validated`}</span></div>
      <nav aria-label="Lệnh Canvas"><button disabled={!state.past.length || readOnly} onClick={() => dispatch({ type: 'undo' })}>Hoàn tác</button>
        <button disabled={!state.future.length || readOnly} onClick={() => dispatch({ type: 'redo' })}>Làm lại</button>
        <button disabled={!selected.length || readOnly} onClick={duplicate}>Nhân bản</button>
        <button disabled={(!selected.length && !selectedEdges.length) || readOnly}
          onClick={() => dispatch(selectedEdges.length ? { type: 'deleteEdges', ids: selectedEdges } : { type: 'delete', ids: selected })}>Xóa</button>
        {selectedEdges.length===1&&<button disabled={readOnly} onClick={toggleErrorBranch}>Nhánh: {selectedEdge?.data?.condition==='error'?'Lỗi':'Thành công'}</button>}
        <button disabled={readOnly} onClick={() => dispatch({ type: 'layout' })}>Tự xếp</button>
        <button aria-pressed={showLayers} onClick={()=>setShowLayers(value=>!value)}>Lớp</button>
        <button aria-pressed={showGrid} onClick={()=>dispatch({type:'pageView',grid:!showGrid})}>Lưới</button>
        <button aria-pressed={showConnections} onClick={()=>dispatch({type:'pageView',connections:!showConnections})}>Đường nối</button>
        <button aria-pressed={showMinimap} onClick={()=>dispatch({type:'pageView',minimap:!showMinimap})}>Bản đồ</button>
        <button aria-label="Mở bảng lệnh" onClick={()=>setCommandOpen(true)}>⌘ K</button>
        <button aria-pressed={assistantOpen} onClick={()=>setAssistantOpen(value=>!value)}>Assistant</button>
        <button aria-pressed={historyOpen} onClick={()=>{const open=!historyOpen;setHistoryOpen(open);if(open&&workflow)void loadSnapshots(workflow).then(setSnapshots)}}>Phiên bản & share</button>
        <button disabled={readOnly || phase === 'saving'} onClick={async () => {
          if (!workflow) return
          if (autosaveTimer.current) window.clearTimeout(autosaveTimer.current)
          setPhase('saving')
          try { const saved = await saveWorkflow({ ...workflow, canvas: state.document }, csrf)
            const result = await validateWorkflow(saved, csrf)
            setWorkflow(result); setCosts(Object.fromEntries(result.validation.step_costs.map((item: { step_id: string; maximum: number }) => [item.step_id, item.maximum])))
            setValidationIssues(result.validation.issues); setPhase('saved')
          } catch (error) { setPhase(error instanceof WorkflowConflictError ? 'conflict' : 'error') }
        }}>Kiểm tra & báo giá</button>
        <select aria-label="Phạm vi chạy" value={runScope} onChange={event=>setRunScope(event.target.value)}>
          <option value="full">Toàn workflow</option>
          <option value="selection" disabled={!selected.length}>Lựa chọn ({selected.length})</option>
          {selectedNode&&<option value="node">Node đang chọn</option>}
          {page.frames.map(frame=><option key={frame.id} value={`frame:${frame.id}`}>Frame · {frame.name}</option>)}
        </select>
        <label className="cache-control"><input type="checkbox" checked={useCache} onChange={event=>setUseCache(event.target.checked)}/>Dùng cache</label>
        <button disabled={readOnly || !workflow || !Object.keys(costs).length || !!run || (runScope==='selection'&&!selected.length)}
          onClick={async () => { if (!workflow) return; const scope=runScope.startsWith('frame:')
            ? {mode:'frame' as const,frame_id:runScope.slice(6)} : runScope==='selection'
            ? {mode:'selection' as const,node_ids:selected} : runScope==='node'&&selectedNode
            ? {mode:'node' as const,node_id:selectedNode.id} : {mode:'full' as const}
            try { setRun(await createRun(workflow, csrf,scope,useCache));void refreshRunHistory() }
            catch (error) { setPhase(error instanceof WorkflowConflictError ? 'conflict' : 'error') } }}>Tạo bản chạy</button>
        {run?.status === 'awaiting_approval' && <label className="schedule-control">Chạy lúc<input type="datetime-local" value={scheduledAt} min={new Date().toISOString().slice(0,16)} onChange={event=>setScheduledAt(event.target.value)}/></label>}
        {run?.status === 'awaiting_approval' && <button onClick={async () => {
          try { setRunError(''); const when=scheduledAt?new Date(scheduledAt).toISOString():'';setRun(await approveRun(run, csrf,when));void refreshRunHistory() }
          catch (error) { setRunError(error instanceof Error ? error.message : 'Không thể phê duyệt.') }
        }}>Phê duyệt {run.estimated} credit</button>}
        {run?.status === 'running' && <button onClick={async () => {setRun(await cancelRun(run, csrf));void refreshRunHistory()}}>Hủy chạy</button>}
        {run && <span className={`run-state ${run.status}`} aria-live="polite">Run: {run.status} · thực tế {run.actual}</span>}
        {runError && <span className="run-error" role="alert">{runError}</span>}</nav>
      <div className={`save-state ${phase}`} aria-live="polite">{offline ? 'Ngoại tuyến · chờ thử lại' : phase === 'saving' ? 'Đang lưu…' : phase === 'conflict'
        ? <>Xung đột <button onClick={() => location.reload()}>Tải bản mới</button></>
        : phase === 'error' ? <>Lưu lỗi <button onClick={() => setRetryNonce(value => value + 1)}>Thử lại</button></> : 'Đã lưu'}</div></header>
    <nav className="canvas-mobile-tabs" aria-label="Khu vực Canvas">{(['canvas','palette','inspector'] as const).map(item=><button key={item} className={mobilePanel===item?'active':''} aria-pressed={mobilePanel===item} onClick={()=>setMobilePanel(item)}>{item==='canvas'?'Canvas':item==='palette'?'Công cụ':'Inspector'}</button>)}</nav>
    <div className={`canvas-body panel-${mobilePanel}`}>
      <aside className="canvas-palette" aria-label="Palette công cụ"><h2>Workspace</h2>
        <section className="page-panel" aria-label="Pages"><header><h3>Pages</h3><button disabled={readOnly||state.document.pages.length>=20}
          onClick={()=>{dispatch({type:'pageAdd'});setSelected([]);setSelectedEdges([])}}>+ Page</button></header>
          {state.document.pages.map(item=><div className={`page-row${item.id===page.id?' active':''}`} key={item.id}>
            <button aria-label={`Mở ${item.name}`} aria-pressed={item.id===page.id} onClick={()=>{dispatch({type:'pageSelect',id:item.id});setSelected([]);setSelectedEdges([])}}>{item.nodes.length}</button>
            <input aria-label={`Đổi tên ${item.name}`} disabled={readOnly} value={item.name}
              onChange={event=>dispatch({type:'pageRename',id:item.id,name:event.target.value})}/>
            <button aria-label={`Xóa ${item.name}`} disabled={readOnly||state.document.pages.length===1}
              onClick={()=>dispatch({type:'pageDelete',id:item.id})}>×</button></div>)}
        </section>
        <section className="organize-panel"><h3>Tổ chức</h3><button disabled={readOnly||!selected.length}
          onClick={()=>dispatch({type:'frameAdd',nodeIds:selected})}>Tạo Frame từ lựa chọn</button>
          <button disabled={readOnly} onClick={()=>dispatch({type:'noteAdd',text:'Ghi chú mới'})}>+ Sticky note</button>
          <button disabled={readOnly} onClick={()=>dispatch({type:'commentAdd',text:'Bình luận mới'})}>+ Comment</button>
          {!!page.frames.length&&<ul>{page.frames.map(frame=><li key={frame.id}><input aria-label={`Đổi tên ${frame.name}`}
            value={frame.name} disabled={readOnly} onChange={event=>dispatch({type:'frameRename',id:frame.id,name:event.target.value})}/>
            <small>{frame.node_ids.length} node</small>{workflow&&<a aria-label={`Xuất ${frame.name}`}
              href={`/agent/api/workflows/${workflow.id}/frames/${frame.id}/export`}>↓</a>}<button aria-label={`Xóa ${frame.name}`} disabled={readOnly}
              onClick={()=>dispatch({type:'frameDelete',id:frame.id})}>×</button></li>)}</ul>}
          {!!page.notes.length&&<ul>{page.notes.map(note=><li key={note.id}><label>NOTE<input aria-label="Nội dung sticky note"
            value={note.text} disabled={readOnly} onChange={event=>dispatch({type:'annotationUpdate',kind:'notes',id:note.id,text:event.target.value})}/></label>
            <button aria-label="Xóa sticky note" disabled={readOnly} onClick={()=>dispatch({type:'annotationDelete',kind:'notes',id:note.id})}>×</button></li>)}</ul>}
          {!!page.comments.length&&<ul>{page.comments.map(comment=><li key={comment.id}><label>COMMENT<input aria-label="Nội dung comment"
            value={comment.text} disabled={readOnly} onChange={event=>dispatch({type:'annotationUpdate',kind:'comments',id:comment.id,text:event.target.value})}/></label>
            <button aria-label="Xóa comment" disabled={readOnly} onClick={()=>dispatch({type:'annotationDelete',kind:'comments',id:comment.id})}>×</button></li>)}</ul>}
        </section><h2>Công cụ</h2>
        <div className="workflow-settings"><p className="routing-note">AUTO ROUTING · {catalogMeta.models} model · {catalogMeta.routing||'managed'}</p><label>Mục tiêu workflow<textarea disabled={readOnly}
          value={state.document.goal} onChange={event => dispatch({ type: 'document', goal: event.target.value })} /></label>
          <label>Ngân sách tối đa<input type="number" min="5" disabled={readOnly}
            value={state.document.budget_max_credit} onChange={event => dispatch({ type: 'document', budget_max_credit: Number(event.target.value) })} /></label>
          <button disabled={readOnly || state.document.goal.trim().length < 10} onClick={async () => {
            try { setPhase('loading'); const planned = await planWorkflow(state.document.goal,
              state.document.budget_max_credit, csrf); setWorkflow(planned)
              dispatch({ type: 'replace', document: planned.canvas }); setRun(undefined); setCosts({}); setPhase('ready')
            } catch { setPhase('error') }
          }}>AI dựng Canvas</button><div className="template-actions"><button disabled={readOnly||!workflow} onClick={cloneCurrent}>Nhân workflow</button><button disabled={!workflow} onClick={downloadTemplate}>Xuất mẫu</button><label>Nhập mẫu<input type="file" accept="application/json,.json" onChange={importTemplate}/></label></div></div>
        {Object.entries(groups).map(([group, tools]) => <section key={group}><h3>{group}</h3>
        {tools?.map(tool => <button key={tool.name} draggable={!readOnly} disabled={readOnly}
          onDragStart={event => event.dataTransfer.setData('application/ltt-tool', tool.name)} onClick={() => addTool(tool)}
          aria-label={`Thêm ${tool.name}`}><strong>{tool.name}</strong><small>{tool.app_name}</small></button>)}</section>)}</aside>
      <main className="canvas-stage" data-testid="canvas-stage" onDragOver={event => event.preventDefault()}
        onDrop={event => { const tool = byName.get(event.dataTransfer.getData('application/ltt-tool')); if (tool) addTool(tool, reactFlow.screenToFlowPosition({ x: event.clientX, y: event.clientY })) }}>
        <ReactFlow key={page.id} nodes={displayNodes as CanvasNode[]} edges={displayEdges} nodeTypes={nodeTypes}
          onNodesChange={(changes: NodeChange[]) => { const persisted = changes.filter(change => ['position', 'add', 'remove', 'replace'].includes(change.type));
            if (persisted.length) dispatch({ type: persisted.every(change => change.type === 'position') ? 'sync' : 'graph', nodes: applyNodeChanges(persisted, page.nodes) as CanvasNode[], edges: page.edges }) }}
          onEdgesChange={(changes: EdgeChange[]) => { const persisted = changes.filter(change => ['add', 'remove', 'replace'].includes(change.type));
            if (persisted.length) dispatch({ type: 'graph', nodes: page.nodes, edges: applyEdgeChanges(persisted, page.edges) as CanvasEdge[] }) }}
          onConnect={onConnect} onNodeClick={(_event, node) => { setSelectedEdges([]); dispatch({ type: 'select', id: node.id }) }}
          onEdgeClick={(_event, edge) => { setSelected([]); setSelectedEdges([edge.id]); dispatch({ type: 'select' }) }}
          onNodeDragStart={() => { dragBefore.current = structuredClone(state.document) }}
          onNodeDragStop={() => { if (dragBefore.current) dispatch({ type: 'commit', before: dragBefore.current }); dragBefore.current = undefined }}
          onPaneClick={() => { setSelected([]); setSelectedEdges([]); dispatch({ type: 'select' }) }} onSelectionChange={onSelectionChange}
          onMoveEnd={(_event, viewport) => dispatch({ type: 'viewport', viewport })}
          nodesDraggable={!readOnly} nodesConnectable={!readOnly} elementsSelectable
          defaultViewport={page.viewport} minZoom={0.1} maxZoom={2}
          fitView={!page.nodes.length} deleteKeyCode={null}>
          {showGrid&&<Background color="#5b2c29" gap={20} />}{showMinimap&&<MiniMap pannable zoomable />}<Controls showInteractive={!readOnly} />
        </ReactFlow>
        {!page.nodes.length && <div className="canvas-empty"><strong>Bắt đầu {page.name}</strong><span>Chọn công cụ ở Palette hoặc tạo page mới để tách quy trình.</span></div>}
        {!!validationIssues.length && <div className="validation-banner" role="alert"><strong>Workflow chưa hợp lệ</strong>
          <span>{validationIssues.slice(0, 3).map(issue => issue.message).join(' · ')}</span></div>}
        {showLayers&&<aside className="layers-drawer" aria-label="Danh sách lớp"><header><strong>Lớp · {page.name}</strong>
          <button aria-label="Đóng danh sách lớp" onClick={()=>setShowLayers(false)}>×</button></header>
          <ul>{page.frames.map(frame=><li key={frame.id}><span>FRAME</span>{frame.name}</li>)}
            {page.nodes.map(node=><li key={node.id}><button onClick={()=>dispatch({type:'select',id:node.id})}><span>NODE</span>{String(node.data.tool)}</button></li>)}
            {page.notes.map(note=><li key={note.id}><span>NOTE</span>{note.text}</li>)}
            {page.comments.map(comment=><li key={comment.id}><span>COMMENT</span>{comment.text}</li>)}</ul></aside>}
      </main>
      <nav className="page-dock" aria-label="Chuyển page">{state.document.pages.map(item=><button
        key={item.id} aria-pressed={item.id===page.id} onClick={()=>dispatch({type:'pageSelect',id:item.id})}>{item.name}</button>)}</nav>
      <Inspector node={selectedNode} tool={selectedNode ? byName.get(String(selectedNode.data.tool)) : undefined} run={run} csrfToken={csrf}
        runHistory={runHistory} onSelectRun={id=>void loadRun(id).then(setRun).catch(()=>setRunError('Không tải được run.'))}
        onReplay={source=>void runAgain(source,csrf).then(next=>{setRun(next);void refreshRunHistory()}).catch(error=>setRunError(error instanceof Error?error.message:'Không thể replay.'))}
        onRestore={source=>void restoreRunAsWorkflow(source,csrf).then(activateWorkflow).catch(error=>setRunError(error instanceof Error?error.message:'Không thể khôi phục workflow.'))}
        readOnly={readOnly} connections={connectionOptions}
        onConnect={(field, value) => { if (!selectedNode) return; const [source, sourceHandle] = value.split('|')
          onConnect({ source, sourceHandle, target: selectedNode.id, targetHandle: field }) }}
        onChange={data => selectedNode && dispatch({ type: 'update', id: selectedNode.id, data })} />
    </div>
    {assistantOpen&&<aside className="assistant-drawer" aria-label="Workflow Assistant"><header><strong>Workflow Assistant</strong><button aria-label="Đóng Assistant" onClick={()=>setAssistantOpen(false)}>×</button></header>
      <div className="assistant-modes"><button aria-pressed={assistantMode==='analyze'} onClick={()=>setAssistantMode('analyze')}>Phân tích</button><button aria-pressed={assistantMode==='improve'} onClick={()=>setAssistantMode('improve')}>Đề xuất cải tiến</button></div>
      <textarea aria-label="Yêu cầu Assistant" value={assistantPrompt} onChange={event=>setAssistantPrompt(event.target.value)} placeholder="Ví dụ: thêm nhánh tạo giọng đọc và ghép video…"/>
      <button disabled={!workflow||assistantBusy||(assistantMode==='improve'&&assistantPrompt.trim().length<3)} onClick={async()=>{if(!workflow)return;setAssistantBusy(true);setAssistantResult({});try{setAssistantResult(await previewAssistant(workflow,assistantMode,assistantPrompt,csrf))}catch(error){setAssistantResult({error:error instanceof Error?error.message:'Assistant lỗi'})}finally{setAssistantBusy(false)}}}>{assistantBusy?'Đang phân tích…':'Tạo bản xem trước'}</button>
      {assistantResult.analysis&&<section><h3>Phân tích</h3><p>{assistantResult.analysis.nodes} node · {assistantResult.analysis.roots} đầu vào · {assistantResult.analysis.valid?'Hợp lệ':'Cần sửa'}</p>{assistantResult.analysis.issues.map(issue=><small key={issue}>{issue}</small>)}</section>}
      {assistantResult.proposal&&<section className="assistant-diff"><h3>Bản diff</h3><p>{assistantResult.proposal.diff.before_nodes} → {assistantResult.proposal.diff.after_nodes} node · tối đa {assistantResult.proposal.diff.estimated_max_credit} credit</p><button onClick={async()=>{if(!workflow||!assistantResult.proposal)return;try{activateWorkflow(await applyAssistant(workflow,assistantResult.proposal.token,csrf));setAssistantOpen(false)}catch(error){setAssistantResult(current=>({...current,error:error instanceof Error?error.message:'Không áp dụng được'}))}}}>Áp dụng bản đã xem trước</button></section>}
      {assistantResult.error&&<p className="assistant-error" role="alert">{assistantResult.error}</p>}</aside>}
    {historyOpen&&<aside className="history-drawer" aria-label="Phiên bản và chia sẻ"><header><strong>Phiên bản & chia sẻ</strong><button aria-label="Đóng phiên bản" onClick={()=>setHistoryOpen(false)}>×</button></header>
      <section><h3>Snapshot</h3>{snapshots.map(item=><div key={item.revision}><span>v{item.revision} · {item.reason}</span><button disabled={!workflow||item.revision===workflow.revision} onClick={()=>workflow&&void restoreSnapshot(workflow,item.revision,csrf).then(next=>{activateWorkflow(next);return loadSnapshots(next)}).then(setSnapshots)}>Khôi phục</button></div>)}</section>
      <section><h3>Share riêng tư · 24 giờ</h3><select aria-label="Quyền share" value={sharePermission} onChange={event=>setSharePermission(event.target.value as 'view'|'clone')}><option value="view">Chỉ xem</option><option value="clone">Xem & clone</option></select><button onClick={()=>workflow&&void createShare(workflow,sharePermission,csrf).then(result=>setSharePath(`${location.origin}${result.path}`))}>Tạo link</button>{sharePath&&<input readOnly aria-label="Link share" value={sharePath}/>}</section>
    </aside>}
    {commandOpen&&<div className="command-backdrop" role="presentation" onMouseDown={event=>event.target===event.currentTarget&&setCommandOpen(false)}>
      <section className="command-palette" role="dialog" aria-modal="true" aria-label="Bảng lệnh Canvas">
        <header><strong>Bảng lệnh</strong><kbd>Esc</kbd></header><input autoFocus aria-label="Tìm lệnh" value={commandQuery}
          onChange={event=>setCommandQuery(event.target.value)} placeholder="Tìm thao tác…"/>
        <div>{[
          {name:'Tạo page mới',run:()=>dispatch({type:'pageAdd'})},
          {name:'Tạo sticky note',run:()=>dispatch({type:'noteAdd',text:'Ghi chú mới'})},
          {name:'Tạo comment',run:()=>dispatch({type:'commentAdd',text:'Bình luận mới'})},
          {name:'Tự động sắp xếp',run:()=>dispatch({type:'layout'})},
          {name:showGrid?'Ẩn lưới':'Hiện lưới',run:()=>dispatch({type:'pageView',grid:!showGrid})},
          {name:showConnections?'Ẩn đường nối':'Hiện đường nối',run:()=>dispatch({type:'pageView',connections:!showConnections})},
          {name:showMinimap?'Ẩn bản đồ':'Hiện bản đồ',run:()=>dispatch({type:'pageView',minimap:!showMinimap})},
        ].filter(item=>item.name.toLocaleLowerCase('vi').includes(commandQuery.toLocaleLowerCase('vi')))
          .map(item=><button key={item.name} onClick={()=>{item.run();setCommandOpen(false);setCommandQuery('')}}>{item.name}</button>)}</div>
      </section></div>}
  </section>
}

export function CanvasShell() { return <ReactFlowProvider><Editor /></ReactFlowProvider> }
