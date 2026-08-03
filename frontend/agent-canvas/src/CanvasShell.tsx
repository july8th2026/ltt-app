import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from 'react'
import { addEdge, applyEdgeChanges, applyNodeChanges, Background, Controls, MiniMap,
  ReactFlow, ReactFlowProvider, useReactFlow, type Connection, type EdgeChange,
  type NodeChange } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import './canvas.css'
import { connectionAllowed, editorReducer, emptyDocument, nextNode,
  type PaletteTool } from './editorState'
import { Inspector } from './Inspector'
import { ToolNode } from './ToolNode'
import { approveRun, cancelRun, cloneWorkflow, createRun, exportWorkflow, importWorkflow,
  loadOrCreateWorkflow, loadPalette, loadRun, loadRunHistory, planWorkflow, saveWorkflow,
  restoreRunAsWorkflow, runAgain, tickRun, WorkflowConflictError, validateWorkflow, type AgentRun, type AgentRunSummary, type CanvasDocument,
  type CanvasEdge, type CanvasNode, type Workflow } from './workflowApi'

const nodeTypes = { tool: ToolNode }

function Editor() {
  const [state, dispatch] = useReducer(editorReducer, { document: emptyDocument(), past: [], future: [] })
  const [workflow, setWorkflow] = useState<Workflow>()
  const [palette, setPalette] = useState<PaletteTool[]>([])
  const [phase, setPhase] = useState<'loading' | 'ready' | 'saving' | 'saved' | 'conflict' | 'error'>('loading')
  const [offline, setOffline] = useState(!navigator.onLine)
  const [selected, setSelected] = useState<string[]>([])
  const [selectedEdges, setSelectedEdges] = useState<string[]>([])
  const [readOnly, setReadOnly] = useState(window.innerWidth <= 640)
  const [mobilePanel,setMobilePanel]=useState<'canvas'|'palette'|'inspector'>('canvas')
  const [costs, setCosts] = useState<Record<string, number>>({})
  const [retryNonce, setRetryNonce] = useState(0)
  const [validationIssues, setValidationIssues] = useState<{ step_id: string; message: string }[]>([])
  const [run, setRun] = useState<AgentRun>()
  const [runHistory,setRunHistory]=useState<AgentRunSummary[]>([])
  const [runError, setRunError] = useState('')
  const [scheduledAt,setScheduledAt]=useState('')
  const copied = useRef<CanvasNode[]>([])
  const autosaveTimer = useRef<number | undefined>(undefined)
  const dragBefore = useRef<CanvasDocument | undefined>(undefined)
  const csrf = document.querySelector<HTMLElement>('#agent-canvas-root')?.dataset.csrfToken ?? ''
  const reactFlow = useReactFlow()
  const byName = useMemo(() => new Map(palette.map(tool => [tool.name, tool])), [palette])
  const selectedNode = state.document.nodes.find(node => node.id === state.selectedId)
  const selectedEdge = state.document.edges.find(edge=>selectedEdges.includes(edge.id))
  const refreshRunHistory=useCallback(()=>loadRunHistory().then(setRunHistory).catch(()=>setRunHistory([])),[])

  useEffect(() => {
    let active = true
    Promise.all([loadPalette(), loadOrCreateWorkflow(csrf)]).then(([result, loaded]) => {
      if (!active) return
      setPalette(result.tools); setWorkflow(loaded); dispatch({ type: 'replace', document: loaded.canvas }); setPhase('ready')
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

  const addTool = useCallback((tool: PaletteTool, position?: { x: number; y: number }) => {
    if (readOnly) return
    const node = nextNode(tool, state.document.nodes.length)
    if (position) node.position = position
    dispatch({ type: 'graph', nodes: [...state.document.nodes, node], edges: state.document.edges })
    dispatch({ type: 'select', id: node.id })
  }, [readOnly, state.document])

  const onConnect = useCallback((connection: Connection) => {
    const sourceNode = state.document.nodes.find(node => node.id === connection.source)
    const targetNode = state.document.nodes.find(node => node.id === connection.target)
    const sourceTool = byName.get(String(sourceNode?.data.tool)); const targetTool = byName.get(String(targetNode?.data.tool))
    if (!connectionAllowed(sourceTool, connection.sourceHandle, targetTool, connection.targetHandle)) return
    const edges = addEdge({ ...connection, id: `${connection.source}-${connection.sourceHandle}-${connection.target}-${connection.targetHandle}` }, state.document.edges) as CanvasEdge[]
    const nodes = state.document.nodes.map(node => node.id === connection.target
      ? { ...node, data: { ...node.data, params: { ...(node.data.params as object ?? {}),
        [connection.targetHandle!]: `$${connection.source}.${connection.sourceHandle}` } } } : node)
    dispatch({ type: 'graph', nodes, edges })
  }, [byName, state.document])

  const duplicate = useCallback(() => {
    if (readOnly) return
    const source = selected.length ? state.document.nodes.filter(node => selected.includes(node.id)) : copied.current
    const clones = source.map((node, index) => ({ ...structuredClone(node), id: `${node.id}-copy-${Date.now()}-${index}`,
      position: { x: node.position.x + 32, y: node.position.y + 32 } }))
    if (clones.length) dispatch({ type: 'graph', nodes: [...state.document.nodes, ...clones], edges: state.document.edges })
  }, [readOnly, selected, state.document])
  const toggleErrorBranch=()=>{if(!selectedEdge||readOnly)return;const condition=selectedEdge.data?.condition==='error'?'success':'error';dispatch({type:'graph',nodes:state.document.nodes,edges:state.document.edges.map(edge=>edge.id===selectedEdge.id?{...edge,data:{...edge.data,condition}}:edge)})}
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
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'z') { event.preventDefault(); dispatch({ type: event.shiftKey ? 'redo' : 'undo' }); return }
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'y') { event.preventDefault(); dispatch({ type: 'redo' }); return }
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'd') { event.preventDefault(); duplicate(); return }
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'c') copied.current = state.document.nodes.filter(node => selected.includes(node.id)).map(node => structuredClone(node))
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'v') { event.preventDefault(); duplicate() }
    if (!readOnly && ['Delete', 'Backspace'].includes(event.key) && (selected.length || selectedEdges.length)) {
      event.preventDefault()
      dispatch(selectedEdges.length ? { type: 'deleteEdges', ids: selectedEdges } : { type: 'delete', ids: selected })
    }
  }

  const displayNodes = useMemo(() => state.document.nodes.map(node => ({ ...node,
    selected: node.id === state.selectedId || selected.includes(node.id),
    data: { ...node.data, __tool: byName.get(String(node.data.tool)), __cost: costs[node.id],
      __status: String(run?.checkpoint[node.id]?.status ??
        (validationIssues.some(issue => issue.step_id === node.id) ? 'invalid'
        : costs[node.id] === undefined ? 'draft' : 'validated')),
      __artifacts: (run?.artifacts ?? []).filter(item => item.step_id === node.id) } })),
  [state.document.nodes, state.selectedId, selected, byName, costs, validationIssues, run])
  const displayEdges = useMemo(() => state.document.edges.map(edge => {
    const isError = edge.data?.condition === 'error'
    return { ...edge, selected: selectedEdges.includes(edge.id), label: isError ? 'Lỗi' : undefined,
      animated: isError, className: isError ? 'error-branch' : undefined }
  }), [state.document.edges, selectedEdges])
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
      state.document.nodes.flatMap(source => {
        if (source.id === selectedNode.id) return []
        const sourceTool = byName.get(String(source.data.tool))
        return Object.keys(sourceTool?.returns ?? {}).filter(output =>
          connectionAllowed(sourceTool, output, byName.get(String(selectedNode.data.tool)), field))
          .map(output => ({ value: `${source.id}|${output}`, label: `${source.id} · ${output}` }))
      })])) : {}
  return <section className="canvas-shell" aria-label="LTT Agent Canvas" tabIndex={0} onKeyDown={onKeyDown}>
    <header className="canvas-toolbar"><div><strong>Canvas</strong><span>{readOnly ? 'Mobile · chỉ xem' : 'Plan v1 · server validated'}</span></div>
      <nav aria-label="Lệnh Canvas"><button disabled={!state.past.length || readOnly} onClick={() => dispatch({ type: 'undo' })}>Hoàn tác</button>
        <button disabled={!state.future.length || readOnly} onClick={() => dispatch({ type: 'redo' })}>Làm lại</button>
        <button disabled={!selected.length || readOnly} onClick={duplicate}>Nhân bản</button>
        <button disabled={(!selected.length && !selectedEdges.length) || readOnly}
          onClick={() => dispatch(selectedEdges.length ? { type: 'deleteEdges', ids: selectedEdges } : { type: 'delete', ids: selected })}>Xóa</button>
        {selectedEdges.length===1&&<button disabled={readOnly} onClick={toggleErrorBranch}>Nhánh: {selectedEdge?.data?.condition==='error'?'Lỗi':'Thành công'}</button>}
        <button disabled={readOnly} onClick={() => dispatch({ type: 'layout' })}>Tự xếp</button>
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
        <button disabled={readOnly || !workflow || !Object.keys(costs).length || !!run}
          onClick={async () => { if (!workflow) return; try { setRun(await createRun(workflow, csrf));void refreshRunHistory() }
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
      <aside className="canvas-palette" aria-label="Palette công cụ"><h2>Công cụ</h2>
        <div className="workflow-settings"><label>Mục tiêu workflow<textarea disabled={readOnly}
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
        <ReactFlow nodes={displayNodes} edges={displayEdges} nodeTypes={nodeTypes}
          onNodesChange={(changes: NodeChange[]) => { const persisted = changes.filter(change => ['position', 'add', 'remove', 'replace'].includes(change.type));
            if (persisted.length) dispatch({ type: persisted.every(change => change.type === 'position') ? 'sync' : 'graph', nodes: applyNodeChanges(persisted, state.document.nodes) as CanvasNode[], edges: state.document.edges }) }}
          onEdgesChange={(changes: EdgeChange[]) => { const persisted = changes.filter(change => ['add', 'remove', 'replace'].includes(change.type));
            if (persisted.length) dispatch({ type: 'graph', nodes: state.document.nodes, edges: applyEdgeChanges(persisted, state.document.edges) as CanvasEdge[] }) }}
          onConnect={onConnect} onNodeClick={(_event, node) => { setSelectedEdges([]); dispatch({ type: 'select', id: node.id }) }}
          onEdgeClick={(_event, edge) => { setSelected([]); setSelectedEdges([edge.id]); dispatch({ type: 'select' }) }}
          onNodeDragStart={() => { dragBefore.current = structuredClone(state.document) }}
          onNodeDragStop={() => { if (dragBefore.current) dispatch({ type: 'commit', before: dragBefore.current }); dragBefore.current = undefined }}
          onPaneClick={() => { setSelected([]); setSelectedEdges([]); dispatch({ type: 'select' }) }} onSelectionChange={onSelectionChange}
          onMoveEnd={(_event, viewport) => dispatch({ type: 'viewport', viewport })}
          nodesDraggable={!readOnly} nodesConnectable={!readOnly} elementsSelectable
          defaultViewport={state.document.viewport} minZoom={0.1} maxZoom={2}
          fitView={!state.document.nodes.length} deleteKeyCode={null}>
          <Background color="#334155" gap={20} /><MiniMap pannable zoomable /><Controls showInteractive={!readOnly} />
        </ReactFlow>
        {!state.document.nodes.length && <div className="canvas-empty"><strong>Bắt đầu workflow</strong><span>Chọn công cụ ở Palette hoặc dùng bàn phím Tab → Enter.</span></div>}
        {!!validationIssues.length && <div className="validation-banner" role="alert"><strong>Workflow chưa hợp lệ</strong>
          <span>{validationIssues.slice(0, 3).map(issue => issue.message).join(' · ')}</span></div>}
      </main>
      <Inspector node={selectedNode} tool={selectedNode ? byName.get(String(selectedNode.data.tool)) : undefined} run={run}
        runHistory={runHistory} onSelectRun={id=>void loadRun(id).then(setRun).catch(()=>setRunError('Không tải được run.'))}
        onReplay={source=>void runAgain(source,csrf).then(next=>{setRun(next);void refreshRunHistory()}).catch(error=>setRunError(error instanceof Error?error.message:'Không thể replay.'))}
        onRestore={source=>void restoreRunAsWorkflow(source,csrf).then(activateWorkflow).catch(error=>setRunError(error instanceof Error?error.message:'Không thể khôi phục workflow.'))}
        readOnly={readOnly} connections={connectionOptions}
        onConnect={(field, value) => { if (!selectedNode) return; const [source, sourceHandle] = value.split('|')
          onConnect({ source, sourceHandle, target: selectedNode.id, targetHandle: field }) }}
        onChange={data => selectedNode && dispatch({ type: 'update', id: selectedNode.id, data })} />
    </div>
  </section>
}

export function CanvasShell() { return <ReactFlowProvider><Editor /></ReactFlowProvider> }
