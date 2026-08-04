import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from 'react'
import { addEdge, applyEdgeChanges, applyNodeChanges, Background, Controls, MarkerType, MiniMap, Position,
  ReactFlow, ReactFlowProvider, useReactFlow, type Connection, type EdgeChange,
  useStore, useUpdateNodeInternals, type NodeChange } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import './canvas.css'
import { activePage, cloneGraphSelection, connectionAllowed, connectionCreatesCycle, editorReducer, emptyDocument, nextNode,
  scopeNodeIds, type PaletteTool } from './editorState'
import { Inspector } from './Inspector'
import { AnnotationNode, CreativeToolNode, FrameNode, ToolNode } from './ToolNode'
import { CanvasEdgeView } from './CanvasEdgeView'
import { fieldLabel, mediaKind, nodeModality, outputLabel, primaryFields } from './nodePresentation'
import { CANVAS_PRESENTATION_VERSION, customerPaletteTools, customerToolLabel,
  destinationLabel, primaryOutputHandle } from './presentationAdapter'
import { applyAssistant, approveRun, cancelRun, cloneWorkflow, createRun, createShare, exportWorkflow, importWorkflow,
  loadOrCreateWorkflow, loadPalette, loadPreferences, loadRun, loadRunHistory, loadSnapshots, planWorkflow, restoreSnapshot, savePreferences, saveWorkflow,
  previewAssistant, quoteTool, restoreRunAsWorkflow, runAgain, tickRun, uploadAsset, WorkflowConflictError, validateWorkflow, type AgentRun, type AgentRunSummary, type AssistantResult, type CanvasDocument,
  type CanvasEdge, type CanvasNode, type Workflow, type WorkflowSnapshot } from './workflowApi'

const nodeTypes = { tool: ToolNode, creativeTool: CreativeToolNode, frame: FrameNode, annotation: AnnotationNode }
const edgeTypes = { creative: CanvasEdgeView }

function removeEdgeFromGraph(nodes:CanvasNode[],edges:CanvasEdge[],edgeId:string){
  const edge=edges.find(item=>item.id===edgeId);if(!edge)return {nodes,edges}
  const cleaned=nodes.map(node=>{if(node.id!==edge.target||!edge.targetHandle)return node
    const params={...((node.data.params??{}) as Record<string,unknown>)};const reference=`$${edge.source}.${edge.sourceHandle}`
    if(params[edge.targetHandle]===reference)delete params[edge.targetHandle]
    else if(Array.isArray(params[edge.targetHandle])){
      const values=(params[edge.targetHandle] as unknown[]).filter(value=>value!==reference)
      if(values.length)params[edge.targetHandle]=values;else delete params[edge.targetHandle]
    }
    return {...node,data:{...node.data,params}}
  })
  return {nodes:cleaned,edges:edges.filter(item=>item.id!==edgeId)}
}

function connectGraph(nodes:CanvasNode[],edges:CanvasEdge[],connection:Connection,
                      byName:Map<string,PaletteTool>){
  const sourceNode=nodes.find(node=>node.id===connection.source);const targetNode=nodes.find(node=>node.id===connection.target)
  const sourceTool=byName.get(String(sourceNode?.data.tool));const targetTool=byName.get(String(targetNode?.data.tool))
  if(!connectionAllowed(sourceTool,connection.sourceHandle,targetTool,connection.targetHandle)||
      connectionCreatesCycle(edges,connection.source!,connection.target!))return undefined
  const sourceHandle=connection.sourceHandle!;const targetHandle=connection.targetHandle!
  const output=sourceTool!.returns[sourceHandle];const input=targetTool!.params_schema[targetHandle]
  const variadic=Boolean(input.type.endsWith('[]')&&output===input.type.slice(0,-2))
  const sameInput=edges.filter(edge=>edge.target===connection.target&&edge.targetHandle===targetHandle)
  const retained=variadic?sameInput.filter(edge=>{
    const tool=byName.get(String(nodes.find(node=>node.id===edge.source)?.data.tool))
    return tool?.returns[edge.sourceHandle??'']===output&&!(edge.source===connection.source&&edge.sourceHandle===sourceHandle)
  }):[]
  const available=edges.filter(edge=>!(edge.target===connection.target&&edge.targetHandle===targetHandle)).concat(retained)
  const nextEdges=addEdge({...connection,id:`${connection.source}-${sourceHandle}-${connection.target}-${targetHandle}`},available) as CanvasEdge[]
  const references=[...retained.map(edge=>`$${edge.source}.${edge.sourceHandle}`),`$${connection.source}.${sourceHandle}`]
  const nextNodes=nodes.map(node=>node.id===connection.target?{...node,data:{...node.data,params:{...(node.data.params as object??{}),
    [targetHandle]:variadic?[...new Set(references)]:`$${connection.source}.${sourceHandle}`}}}:node)
  return {nodes:nextNodes,edges:nextEdges}
}

function uniqueNodeLabel(node:CanvasNode,nodes:CanvasNode[],byName:Map<string,PaletteTool>){
  const base=node.label?.trim()||customerToolLabel(byName.get(String(node.data.tool)))
  const peers=nodes.filter(item=>(item.label?.trim()||customerToolLabel(byName.get(String(item.data.tool))))===base)
  return peers.length>1?`${base} ${peers.findIndex(item=>item.id===node.id)+1}`:base
}

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
  const [desktopPanel,setDesktopPanel]=useState<'tools'|'workspace'|'run'|'inspector'|null>(null)
  const [paletteQuery,setPaletteQuery]=useState('')
  const [theme,setTheme]=useState<'light'|'dark'>('dark')
  const [catalogMode,setCatalogMode]=useState<'simple'|'advanced'>('advanced')
  const [quickConnect,setQuickConnect]=useState<{sourceId:string;sourceHandle:string}|null>(null)
  const [quickCreate,setQuickCreate]=useState<{sourceId:string;sourceHandle:string;x:number;y:number;flow:{x:number;y:number}}|null>(null)
  const [edgeInsert,setEdgeInsert]=useState<{edgeId:string;x:number;y:number;flow:{x:number;y:number}}|null>(null)
  const [contextMenu,setContextMenu]=useState<{kind:'pane'|'node';x:number;y:number;flow:{x:number;y:number};nodeId?:string}|null>(null)
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
  const copied = useRef<{nodes:CanvasNode[];edges:CanvasEdge[]}>({nodes:[],edges:[]})
  const autosaveTimer = useRef<number | undefined>(undefined)
  const dragBefore = useRef<CanvasDocument | undefined>(undefined)
  const csrf = document.querySelector<HTMLElement>('#agent-canvas-root')?.dataset.csrfToken ?? ''
  const presentationMode=document.querySelector<HTMLElement>('#agent-canvas-root')?.dataset.presentation==='legacy'
    ?'legacy':'creative'
  const reactFlow = useReactFlow()
  const updateNodeInternals=useUpdateNodeInternals()
  const page = activePage(state.document)
  const showGrid=page.view?.grid??true
  const showConnections=page.view?.connections??true
  const showMinimap=page.view?.minimap??true
  const byName = useMemo(() => new Map(palette.map(tool => [tool.name, tool])), [palette])
  const selectedNode = page.nodes.find(node => node.id === state.selectedId)
  const selectedEdge = page.edges.find(edge=>selectedEdges.includes(edge.id))
  const referenceOptions=useMemo(()=>{
    if(!selectedNode)return []
    const targetTool=byName.get(String(selectedNode.data.tool))
    return page.nodes.filter(node=>node.id!==selectedNode.id).flatMap(node=>{
      const sourceTool=byName.get(String(node.data.tool))
      if(!sourceTool||!targetTool)return []
      for(const sourceHandle of Object.keys(sourceTool.returns))for(const targetHandle of Object.keys(targetTool.params_schema)){
        if(connectionAllowed(sourceTool,sourceHandle,targetTool,targetHandle))return [{source:node.id,sourceHandle,targetHandle,
          label:uniqueNodeLabel(node,page.nodes,byName),detail:`${outputLabel(sourceHandle,sourceTool.returns[sourceHandle])} → ${fieldLabel(targetHandle)}`}]
      }
      return []
    })
  },[selectedNode,page.nodes,byName])
  const connectedInputs=useMemo(()=>selectedNode?page.edges.filter(edge=>edge.target===selectedNode.id).map(edge=>{
    const source=page.nodes.find(node=>node.id===edge.source);const sourceTool=byName.get(String(source?.data.tool))
    return {edgeId:edge.id,label:source?uniqueNodeLabel(source,page.nodes,byName):edge.source,
      detail:`${outputLabel(edge.sourceHandle??'',String(sourceTool?.returns[edge.sourceHandle??'']??''))} → ${fieldLabel(edge.targetHandle??'đầu vào')}`}
  }):[],[selectedNode,page.edges,page.nodes,byName])
  const refreshRunHistory=useCallback(()=>loadRunHistory().then(setRunHistory).catch(()=>setRunHistory([])),[])

  useEffect(()=>{
    if(!palette.length||!page.nodes.length)return
    const frame=requestAnimationFrame(()=>updateNodeInternals(page.nodes.map(node=>node.id)))
    return()=>cancelAnimationFrame(frame)
  },[updateNodeInternals,palette.length,page.nodes.length])

  useEffect(() => {
    let active = true
    Promise.all([loadPalette(), loadOrCreateWorkflow(csrf), loadPreferences()]).then(([result, loaded, preferences]) => {
      if (!active) return
      setPalette(result.tools); setCatalogMeta({models:result.models?.length??0,
        routing:result.routing?.mode??''}); setTheme(preferences.theme); setCatalogMode(preferences.catalog_mode)
      setWorkflow(loaded); dispatch({ type: 'replace', document: loaded.canvas }); setPhase('ready')
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
      } else if (event.key === 'Escape') {
        setCommandOpen(false);setShowLayers(false);setDesktopPanel(null);setContextMenu(null);setQuickCreate(null);setQuickConnect(null)
        setSelected([]);setSelectedEdges([]);dispatch({type:'select'})
      }
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
    if(presentationMode==='creative'){setDesktopPanel(null);setQuickConnect(null);setQuickCreate(null)}
  }, [readOnly, page,presentationMode])

  const onConnect = useCallback((connection: Connection) => {
    const next=connectGraph(page.nodes,page.edges,connection,byName);if(next)dispatch({type:'graph',...next})
  }, [byName, page])

  const onReconnectEdge=useCallback((oldEdge:CanvasEdge,connection:Connection)=>{
    if(readOnly)return
    const base=removeEdgeFromGraph(page.nodes,page.edges,oldEdge.id)
    const next=connectGraph(base.nodes,base.edges,connection,byName);if(next)dispatch({type:'graph',...next})
  },[readOnly,page,byName])

  const insertToolOnEdge=useCallback((tool:PaletteTool,edgeId:string,position:{x:number;y:number})=>{
    if(readOnly)return
    const old=page.edges.find(edge=>edge.id===edgeId);if(!old||!old.sourceHandle||!old.targetHandle)return
    const sourceNode=page.nodes.find(node=>node.id===old.source);const targetNode=page.nodes.find(node=>node.id===old.target)
    const sourceTool=byName.get(String(sourceNode?.data.tool));const targetTool=byName.get(String(targetNode?.data.tool))
    const inputHandle=Object.keys(tool.params_schema).find(field=>connectionAllowed(sourceTool,old.sourceHandle!,tool,field))
    const candidateOutput=primaryOutputHandle(tool)
    const outputHandle=candidateOutput&&connectionAllowed(tool,candidateOutput,targetTool,old.targetHandle!)?candidateOutput:undefined
    if(!inputHandle||!outputHandle)return
    const node=nextNode(tool,page.nodes.length);node.position=position
    const inputRule=tool.params_schema[inputHandle];const sourceKind=sourceTool?.returns[old.sourceHandle]
    node.data.params={...((node.data.params??{}) as Record<string,unknown>),[inputHandle]:
      inputRule.type.endsWith('[]')&&sourceKind===inputRule.type.slice(0,-2)?[`$${old.source}.${old.sourceHandle}`]:`$${old.source}.${old.sourceHandle}`}
    const nodes=page.nodes.map(item=>{if(item.id!==old.target)return item
      const params={...((item.data.params??{}) as Record<string,unknown>)};const before=`$${old.source}.${old.sourceHandle}`;const after=`$${node.id}.${outputHandle}`
      if(params[old.targetHandle!]===before)params[old.targetHandle!]=after
      else if(Array.isArray(params[old.targetHandle!]))params[old.targetHandle!]=(params[old.targetHandle!] as unknown[]).map(value=>value===before?after:value)
      return {...item,data:{...item.data,params}}
    })
    const edges=page.edges.filter(edge=>edge.id!==old.id).concat([
      {id:`${old.source}-${old.sourceHandle}-${node.id}-${inputHandle}`,source:old.source,sourceHandle:old.sourceHandle,target:node.id,targetHandle:inputHandle},
      {id:`${node.id}-${outputHandle}-${old.target}-${old.targetHandle}`,source:node.id,sourceHandle:outputHandle,target:old.target,targetHandle:old.targetHandle},
    ])
    dispatch({type:'graph',nodes:[...nodes,node],edges});dispatch({type:'select',id:node.id});setSelected([node.id]);setEdgeInsert(null)
  },[readOnly,page,byName])

  const addConnectedTool=useCallback((tool:PaletteTool,sourceId:string,sourceHandle:string,position:{x:number;y:number})=>{
    if(readOnly)return
    const source=page.nodes.find(node=>node.id===sourceId);const sourceTool=byName.get(String(source?.data.tool))
    const targetHandle=Object.keys(tool.params_schema).find(field=>connectionAllowed(sourceTool,sourceHandle,tool,field))
    if(!targetHandle)return
    const node=nextNode(tool,page.nodes.length);node.position=position
    const targetRule=tool.params_schema[targetHandle];const output=sourceTool?.returns[sourceHandle]
    const value=targetRule.type.endsWith('[]')&&output===targetRule.type.slice(0,-2)
      ?[`$${sourceId}.${sourceHandle}`]:`$${sourceId}.${sourceHandle}`
    node.data.params={...((node.data.params??{}) as Record<string,unknown>),[targetHandle]:value}
    const edge={id:`${sourceId}-${sourceHandle}-${node.id}-${targetHandle}`,source:sourceId,sourceHandle,target:node.id,targetHandle}
    dispatch({type:'graph',nodes:[...page.nodes,node],edges:[...page.edges,edge]})
    dispatch({type:'select',id:node.id});setSelected([node.id]);setQuickCreate(null)
  },[readOnly,page,byName])

  const uploadToNode=useCallback(async(nodeId:string,files:File[])=>{
    const node=page.nodes.find(item=>item.id===nodeId);if(!node)return
    try{
      const current=byName.get(String(node.data.tool));const batch=nodeModality(current)==='batch'
      const selected=files.slice(0,batch?12:1);if(!selected.length)return
      const uploadedRows=await Promise.all(selected.map(file=>uploadAsset(file,csrf)))
      if(batch&&uploadedRows.some(item=>item.kind!=='image')){setRunError('Bộ ảnh chỉ nhận file hình ảnh.');return}
      const uploaded=uploadedRows[0]
      const assetTool=byName.get(batch?'asset.images':`asset.${uploaded.kind}`)
      if(!assetTool){setRunError(`Canvas chưa có node đầu vào ${uploaded.kind}.`);return}
      const keyField=batch?'image_keys':Object.entries(assetTool.params_schema).find(([,rule])=>rule.type===uploaded.kind)?.[0]
        ??`${uploaded.kind}_key`;const params=batch?{[keyField]:uploadedRows.map(item=>item.key)}:{[keyField]:uploaded.key}
      dispatch({type:'toolReplace',id:nodeId,tool:assetTool,tools:palette,data:{
        params,...(batch?{asset_names:uploadedRows.map(item=>item.name),asset_sizes:uploadedRows.map(item=>item.size),
          asset_urls:uploadedRows.map(item=>item.url)}:{asset_name:uploaded.name,asset_size:uploaded.size,
          asset_url:uploaded.url})}})
      dispatch({type:'select',id:nodeId});setSelected([nodeId]);setRunError('')
    }catch(error){setRunError(error instanceof Error?error.message:'Không tải được tệp.')}
  },[page,csrf,byName,palette])

  const generateInNode=useCallback((nodeId:string)=>{
    const node=page.nodes.find(item=>item.id===nodeId);const current=byName.get(String(node?.data.tool))
    const kind=mediaKind(current)
    if(!node||!kind)return
    const generator=current?.name==='asset.images'?byName.get('image.batch_generate'):
      palette.find(tool=>tool.primary&&tool.category==='content'&&nodeModality(tool)===kind)
      ??palette.find(tool=>tool.category==='content'&&nodeModality(tool)===kind)
    if(generator&&generator.name!==current?.name)dispatch({type:'toolReplace',id:nodeId,tool:generator,tools:palette})
    dispatch({type:'select',id:nodeId});setSelected([nodeId]);setSelectedEdges([]);setDesktopPanel('inspector')
  },[page.nodes,byName,palette])

  const prepareScope=useCallback(async(scope:{mode:'node'|'selection';node_id?:string;node_ids?:string[]})=>{
    if(!workflow||readOnly||run)return
    if(autosaveTimer.current)window.clearTimeout(autosaveTimer.current)
    setDesktopPanel('run');setPhase('saving');setRunError('')
    try{
      const saved=await saveWorkflow({...workflow,canvas:state.document},csrf)
      const checked=await validateWorkflow(saved,csrf)
      setWorkflow(checked);setCosts(Object.fromEntries(checked.validation.step_costs.map((item:{step_id:string;maximum:number})=>[item.step_id,item.maximum])))
      const requested=(scope.node_ids??[scope.node_id??'']).filter(Boolean)
      const relevantIds=new Set(scopeNodeIds(page.nodes,page.edges,requested))
      const relevantIssues=checked.validation.issues.filter((issue:{step_id:string;message:string})=>relevantIds.has(issue.step_id))
      setValidationIssues(relevantIssues);setPhase('saved')
      if(relevantIssues.length)return
      setRun(await createRun(checked,csrf,scope,useCache));void refreshRunHistory()
    }catch(error){setPhase(error instanceof WorkflowConflictError?'conflict':'error');setRunError(error instanceof Error?error.message:'Không chuẩn bị được bản chạy.')}
  },[workflow,readOnly,run,state.document,csrf,useCache,refreshRunHistory,page.nodes,page.edges])

  const downstreamIds=useCallback((nodeId:string)=>{
    const found=new Set([nodeId]);let changed=true
    while(changed){changed=false;for(const edge of page.edges)if(found.has(edge.source)&&!found.has(edge.target)){found.add(edge.target);changed=true}}
    return [...found]
  },[page.edges])

  const duplicateNode=useCallback((nodeId:string)=>{
    if(readOnly)return;const source=page.nodes.find(node=>node.id===nodeId);if(!source)return
    const clone={...structuredClone(source),id:`${source.id}-copy-${Date.now()}`,
      position:{x:source.position.x+32,y:source.position.y+32}}
    dispatch({type:'graph',nodes:[...page.nodes,clone],edges:page.edges});dispatch({type:'select',id:clone.id});setSelected([clone.id])
  },[readOnly,page])

  const duplicate = useCallback(() => {
    if (readOnly) return
    const source=page.nodes.filter(node=>selected.includes(node.id))
    if(!source.length)return
    const cloned=cloneGraphSelection(source,page.edges)
    dispatch({type:'graph',nodes:[...page.nodes,...cloned.nodes],edges:[...page.edges,...cloned.edges]})
    setSelected(cloned.nodeIds);setSelectedEdges([])
  }, [readOnly, selected, page])
  const paste=useCallback(()=>{
    if(readOnly||!copied.current.nodes.length)return
    const cloned=cloneGraphSelection(copied.current.nodes,copied.current.edges)
    dispatch({type:'graph',nodes:[...page.nodes,...cloned.nodes],edges:[...page.edges,...cloned.edges]})
    setSelected(cloned.nodeIds);setSelectedEdges([])
  },[readOnly,page])
  const disconnectInput=useCallback((edgeId:string)=>{
    if(readOnly)return
    const edge=page.edges.find(item=>item.id===edgeId);if(!edge)return
    const nodes=page.nodes.map(node=>{if(node.id!==edge.target||!edge.targetHandle)return node
      const params={...((node.data.params??{}) as Record<string,unknown>)}
      const reference=`$${edge.source}.${edge.sourceHandle}`
      if(params[edge.targetHandle]===reference)delete params[edge.targetHandle]
      else if(Array.isArray(params[edge.targetHandle])){
        const remaining=(params[edge.targetHandle] as unknown[]).filter(value=>value!==reference)
        if(remaining.length)params[edge.targetHandle]=remaining
        else delete params[edge.targetHandle]
      }
      return {...node,data:{...node.data,params}}
    })
    dispatch({type:'graph',nodes,edges:page.edges.filter(item=>item.id!==edgeId)})
  },[readOnly,page])
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
    const target=event.target as HTMLElement
    if(target.closest('input,textarea,select,[contenteditable="true"]'))return
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault(); setCommandOpen(true); return
    }
    if (event.key === 'Escape') { setCommandOpen(false);setShowLayers(false);setDesktopPanel(null);setContextMenu(null);setQuickCreate(null);setQuickConnect(null);
      setSelected([]);setSelectedEdges([]);dispatch({type:'select'});return }
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'z') { event.preventDefault(); dispatch({ type: event.shiftKey ? 'redo' : 'undo' }); return }
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'y') { event.preventDefault(); dispatch({ type: 'redo' }); return }
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'd') { event.preventDefault(); duplicate(); return }
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'c') {
      const ids=new Set(selected);copied.current={nodes:page.nodes.filter(node=>ids.has(node.id)).map(node=>structuredClone(node)),
        edges:page.edges.filter(edge=>ids.has(edge.source)&&ids.has(edge.target)).map(edge=>structuredClone(edge))};return
    }
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'v') { event.preventDefault(); paste();return }
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'a') {
      event.preventDefault();setSelected(page.nodes.map(node=>node.id));setSelectedEdges([]);dispatch({type:'select'});return
    }
    if(!event.ctrlKey&&!event.metaKey&&!event.altKey){
      const key=event.key.toLowerCase();const mode=({i:'image',v:'video',t:'text',a:'audio'} as Record<string,string>)[key]
      const tool=mode&&palette.find(item=>nodeModality(item)===mode&&item.primary)
        ||mode&&palette.find(item=>nodeModality(item)===mode)
      if(tool){event.preventDefault();addTool(tool);return}
      if(key==='n'){event.preventDefault();dispatch({type:'noteAdd',text:'Ghi chú mới'});return}
      if(key==='f'&&selected.length){event.preventDefault();dispatch({type:'frameAdd',nodeIds:selected});return}
      if(key==='d'){event.preventDefault();setDesktopPanel('workspace');return}
      if(['arrowup','arrowdown','arrowleft','arrowright'].includes(key)&&selected.length&&!readOnly){
        event.preventDefault();const amount=event.shiftKey?10:1
        const movement={arrowup:{x:0,y:-amount},arrowdown:{x:0,y:amount},arrowleft:{x:-amount,y:0},arrowright:{x:amount,y:0}}[key]!
        dispatch({type:'graph',nodes:page.nodes.map(node=>selected.includes(node.id)?{...node,position:{x:node.position.x+movement.x,y:node.position.y+movement.y}}:node),edges:page.edges});return
      }
    }
    if (!readOnly && ['Delete', 'Backspace'].includes(event.key) && (selected.length || selectedEdges.length)) {
      event.preventDefault()
      dispatch(selectedEdges.length ? { type: 'deleteEdges', ids: selectedEdges } : { type: 'delete', ids: selected })
    }
  }

  const displayNodes = useMemo(() => {
    const tools = page.nodes.map(node => {const tool=byName.get(String(node.data.tool));
    const creative=presentationMode==='creative';const width=readOnly?280:creative?300:360
    const inputFields=tool?.name.startsWith('asset.')?[]:Object.keys(tool?.params_schema??{}).filter(field=>palette.some(source=>Object.keys(source.returns).some(handle=>connectionAllowed(source,handle,tool,field))))
    const outputHandles=creative?[primaryOutputHandle(tool)].filter(Boolean) as string[]:Object.keys(tool?.returns??{})
    return ({ ...node,type:creative?'creativeTool':'tool',
    measured:{width,height:readOnly?244:creative?258:334},handles:[
      ...inputFields.map((id,index)=>({id,type:'target' as const,position:Position.Left,x:-22,y:34+index*34,width:44,height:44})),
      ...outputHandles.map((id,index)=>({id,type:'source' as const,position:Position.Right,x:width-22,y:46+index*42,width:44,height:44}))],
    selected: node.id === state.selectedId || selected.includes(node.id),
    data: { ...node.data, __tool: tool, __cost: liveQuotes[node.id]??costs[node.id],
      __readOnly: readOnly,__inputFields:inputFields,__label:node.label,
      __onParamChange: (name:string,value:unknown) => dispatch({type:'update',id:node.id,data:{
        params:{...((node.data.params??{}) as Record<string,unknown>),[name]:value}}}),
      __onRename:(label:string)=>dispatch({type:'nodeLabel',id:node.id,label}),
      __onDuplicate:()=>duplicateNode(node.id),
      __onQuickConnect: (sourceHandle:string)=>setQuickConnect({sourceId:node.id,sourceHandle}),
      __onOpen:()=>{setSelected([node.id]);setSelectedEdges([]);dispatch({type:'select',id:node.id})},
      __onRun:()=>{setSelected([node.id]);dispatch({type:'select',id:node.id});void prepareScope({mode:'node',node_id:node.id})},
      __onUpload:(files:File[])=>void uploadToNode(node.id,files),
      __onGenerate:()=>generateInNode(node.id),
      __status: String(run?.checkpoint[node.id]?.status ??
        (validationIssues.some(issue => issue.step_id === node.id) ? 'invalid'
        : costs[node.id] === undefined ? 'draft' : 'validated')),
      __artifacts: (run?.artifacts ?? []).filter(item => item.step_id === node.id) } })})
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
  }, [page, state.selectedId, selected, byName, palette, costs, liveQuotes, validationIssues, run, readOnly,presentationMode,prepareScope,uploadToNode,generateInNode,duplicateNode])
  const displayEdges = useMemo(() => (showConnections ? page.edges : []).map(edge => {
    const isError = edge.data?.condition === 'error'
    const sourceTool=byName.get(String(page.nodes.find(node=>node.id===edge.source)?.data.tool))
    const kind=String(sourceTool?.returns[edge.sourceHandle??'']??'data').replace('[]','')
    const running=run?.status==='running'&&run.checkpoint[edge.source]?.status==='done'&&run.checkpoint[edge.target]?.status!=='done'
    return { ...edge,type:presentationMode==='creative'?'creative':undefined,
      selected:selectedEdges.includes(edge.id),label:isError?'Lỗi':undefined,
      markerEnd:{type:MarkerType.ArrowClosed,width:16,height:16},animated:isError||running,
      className:`edge-${kind}${isError?' error-branch':''}${running?' is-running':''}`,
      data:{...edge.data,modality:kind,running,onInsert:({x,y}:{x:number;y:number})=>setEdgeInsert({edgeId:edge.id,x,y,
        flow:reactFlow.screenToFlowPosition({x,y})})} }
  }), [page.edges,page.nodes,selectedEdges,showConnections,byName,run,presentationMode,reactFlow])
  if (phase === 'loading') return <section className="canvas-state" aria-live="polite">Đang tải workflow…</section>
  if (phase === 'error' && !workflow) return <section className="canvas-state error" role="alert">Không tải được Canvas. <button onClick={() => location.reload()}>Thử lại</button></section>
  const query=paletteQuery.trim().toLocaleLowerCase('vi')
  const creativePalette=presentationMode==='creative'
    ?customerPaletteTools(palette,catalogMode==='advanced'):palette
  const hasPrimary=creativePalette.some(tool=>tool.primary)
  const categoryLabels:Record<string,string>={content:'Tạo nội dung',input:'Đầu vào',transform:'Xử lý',specialized:'Chuyên biệt',advanced:'Khác'}
  const groups = creativePalette.filter(tool=>(catalogMode==='advanced'||!!query||!hasPrimary||tool.primary)
    &&`${tool.label??''} ${tool.name} ${tool.app_name} ${tool.description}`.toLocaleLowerCase('vi').includes(query))
    .reduce<Record<string, PaletteTool[]>>((result, tool) => {
    const group = catalogMode==='simple'&&!query ? 'Công cụ chính' : categoryLabels[tool.category??'advanced']
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
  const quickOptions=quickConnect?page.nodes.flatMap(target=>{
    if(target.id===quickConnect.sourceId)return []
    const source=page.nodes.find(node=>node.id===quickConnect.sourceId)
    const sourceTool=byName.get(String(source?.data.tool));const targetTool=byName.get(String(target.data.tool))
    if(connectionCreatesCycle(page.edges,quickConnect.sourceId,target.id))return []
    const targetHandle=Object.keys(targetTool?.params_schema??{}).find(field=>
      connectionAllowed(sourceTool,quickConnect.sourceHandle,targetTool,field))
    return targetHandle?[{targetId:target.id,targetHandle,
      label:destinationLabel(sourceTool,quickConnect.sourceHandle,targetTool,uniqueNodeLabel(target,page.nodes,byName))}]:[]
  }):[]
  const quickCreateOptions=quickCreate?customerPaletteTools(palette,true).filter(tool=>{
    const source=page.nodes.find(node=>node.id===quickCreate.sourceId);const sourceTool=byName.get(String(source?.data.tool))
    return Object.keys(tool.params_schema).some(field=>connectionAllowed(sourceTool,quickCreate.sourceHandle,tool,field))
  }):[]
  const insertEdge=edgeInsert?page.edges.find(edge=>edge.id===edgeInsert.edgeId):undefined
  const insertOptions=insertEdge&&insertEdge.sourceHandle&&insertEdge.targetHandle?customerPaletteTools(palette,true).filter(tool=>{
    const sourceTool=byName.get(String(page.nodes.find(node=>node.id===insertEdge.source)?.data.tool))
    const targetTool=byName.get(String(page.nodes.find(node=>node.id===insertEdge.target)?.data.tool))
    return Object.keys(tool.params_schema).some(field=>connectionAllowed(sourceTool,insertEdge.sourceHandle!,tool,field))&&
      Boolean(primaryOutputHandle(tool)&&connectionAllowed(tool,primaryOutputHandle(tool)!,targetTool,insertEdge.targetHandle!))
  }):[]
  const persistPreferences=(nextTheme:'light'|'dark',nextCatalog:'simple'|'advanced')=>{
    setTheme(nextTheme);setCatalogMode(nextCatalog)
    void savePreferences({theme:nextTheme,catalog_mode:nextCatalog,
      presentation_version:CANVAS_PRESENTATION_VERSION},csrf).catch(()=>setPhase('error'))
  }
  return <section className={`canvas-shell theme-${theme}`} data-presentation={presentationMode}
    aria-label="LTT Agent Canvas" tabIndex={0} onKeyDown={onKeyDown}>
    <header className="canvas-toolbar"><a className="canvas-home" href="/agent" aria-label="Về Agent AI">LTT</a><div className="workflow-identity"><input aria-label="Tên workflow"
      value={workflow?.name ?? ''} disabled={!workflow || readOnly} onChange={event=>workflow&&setWorkflow({...workflow,name:event.target.value})}
      onBlur={()=>workflow&&saveWorkflow({...workflow,canvas:state.document},csrf).then(setWorkflow).catch(()=>setPhase('error'))}/>
      <span>{readOnly ? 'Mobile · chỉ xem' : `Canvas v2 · ${page.name} · ${page.nodes.length} node · ${page.edges.length} kết nối`}</span></div>
      <div className="canvas-top-actions"><span className={`save-state ${phase}`} aria-live="polite">{offline ? 'Ngoại tuyến' : phase === 'saving' ? 'Đang lưu…' : phase === 'conflict' ? 'Xung đột' : phase === 'error' ? 'Lỗi lưu' : 'Đã lưu'}</span>
        <button title="Đổi giao diện" aria-label={theme==='light'?'Chuyển sang nền tối':'Chuyển sang nền sáng'} onClick={()=>persistPreferences(theme==='light'?'dark':'light',catalogMode)}>{theme==='light'?'☾':'☀'}</button>
        <button title="Bảng lệnh" aria-label="Mở bảng lệnh" onClick={()=>setCommandOpen(true)}>⌘</button>
        <button title="Assistant" aria-pressed={assistantOpen} onClick={()=>setAssistantOpen(value=>!value)}>AI</button>
        <button title="Phiên bản và chia sẻ" aria-pressed={historyOpen} onClick={()=>{const open=!historyOpen;setHistoryOpen(open);if(open&&workflow)void loadSnapshots(workflow).then(setSnapshots)}}>↗</button>
        <button className="run-primary" aria-pressed={desktopPanel==='run'} onClick={()=>setDesktopPanel(value=>value==='run'?null:'run')}>Chạy</button></div>
      <nav className={`operation-drawer${desktopPanel==='run'?' is-open':''}`} aria-label="Lệnh Canvas"><header><strong>Kiểm tra & chạy</strong><button aria-label="Đóng bảng chạy" onClick={()=>setDesktopPanel(null)}>×</button></header><button disabled={!selected.length || readOnly} onClick={duplicate}>Nhân bản</button>
        <button disabled={(!selected.length && !selectedEdges.length) || readOnly}
          onClick={() => dispatch(selectedEdges.length ? { type: 'deleteEdges', ids: selectedEdges } : { type: 'delete', ids: selected })}>Xóa</button>
        {selectedEdges.length===1&&<button disabled={readOnly} onClick={toggleErrorBranch}>Nhánh: {selectedEdge?.data?.condition==='error'?'Lỗi':'Thành công'}</button>}
        <button disabled={readOnly} onClick={() => dispatch({ type: 'layout' })}>Tự xếp</button>
        <button aria-pressed={showLayers} onClick={()=>setShowLayers(value=>!value)}>Lớp</button>
        <button aria-pressed={showGrid} onClick={()=>dispatch({type:'pageView',grid:!showGrid})}>Lưới</button>
        <button aria-pressed={showConnections} onClick={()=>dispatch({type:'pageView',connections:!showConnections})}>Đường nối</button>
        <button aria-pressed={showMinimap} onClick={()=>dispatch({type:'pageView',minimap:!showMinimap})}>Bản đồ</button>
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
      <div className={`legacy-save-state save-state ${phase}`} aria-live="polite">{offline ? 'Ngoại tuyến · chờ thử lại' : phase === 'saving' ? 'Đang lưu…' : phase === 'conflict'
        ? <>Xung đột <button onClick={() => location.reload()}>Tải bản mới</button></>
        : phase === 'error' ? <>Lưu lỗi <button onClick={() => setRetryNonce(value => value + 1)}>Thử lại</button></> : 'Đã lưu'}</div></header>
    <nav className="canvas-mobile-tabs" aria-label="Khu vực Canvas">{(['canvas','palette','inspector'] as const).map(item=><button key={item} className={mobilePanel===item?'active':''} aria-pressed={mobilePanel===item} onClick={()=>setMobilePanel(item)}>{item==='canvas'?'Canvas':item==='palette'?'Công cụ':'Inspector'}</button>)}</nav>
    <div className={`canvas-body panel-${mobilePanel}${selectedNode&&presentationMode==='creative'?' has-composer':''}`}>
      <nav className="canvas-rail" aria-label="Công cụ Canvas">
        <button title="Chọn" aria-label="Công cụ chọn" aria-pressed={!desktopPanel}>↖</button>
        <button title="Thêm node" aria-label="Mở công cụ" aria-pressed={desktopPanel==='tools'} onClick={()=>{const open=desktopPanel!=='tools';setDesktopPanel(open?'tools':null);if(open&&presentationMode==='creative'){setSelected([]);setSelectedEdges([]);dispatch({type:'select'})}}}>＋</button>
        <button title="Workspace" aria-label="Mở Workspace" aria-pressed={desktopPanel==='workspace'} onClick={()=>setDesktopPanel(value=>value==='workspace'?null:'workspace')}>▦</button>
        <button title="Lớp" aria-label="Mở danh sách lớp" aria-pressed={showLayers} onClick={()=>setShowLayers(value=>!value)}>☷</button>
        <button title="Sticky note" aria-label="Tạo sticky note" disabled={readOnly} onClick={()=>dispatch({type:'noteAdd',text:'Ghi chú mới'})}>□</button>
        <button title="Bình luận" aria-label="Tạo comment" disabled={readOnly} onClick={()=>dispatch({type:'commentAdd',text:'Bình luận mới'})}>◌</button>
        <span />
        <button title="Hoàn tác" aria-label="Hoàn tác" disabled={!state.past.length||readOnly} onClick={()=>dispatch({type:'undo'})}>↶</button>
        <button title="Làm lại" aria-label="Làm lại" disabled={!state.future.length||readOnly} onClick={()=>dispatch({type:'redo'})}>↷</button>
      </nav>
      <aside className={`canvas-palette${desktopPanel==='tools'||desktopPanel==='workspace'?' is-open':''}${desktopPanel==='workspace'?' workspace-only':' tools-only'}`} aria-label="Palette công cụ"><header className="drawer-heading"><h2>{desktopPanel==='workspace'?'Workspace':'Thêm node'}</h2><button aria-label="Đóng Palette" onClick={()=>setDesktopPanel(null)}>×</button></header>
        {desktopPanel==='tools'&&<><input className="palette-search" aria-label="Tìm công cụ" value={paletteQuery} onChange={event=>setPaletteQuery(event.target.value)} placeholder="Tìm công cụ…"/><button className="catalog-toggle" aria-pressed={catalogMode==='advanced'} onClick={()=>persistPreferences(theme,catalogMode==='simple'?'advanced':'simple')}>{catalogMode==='simple'?'Hiện công cụ nâng cao':'Chỉ hiện công cụ chính'}</button></>}
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
          aria-label={`Thêm ${customerToolLabel(tool)}`}><strong>{customerToolLabel(tool)}</strong><small>{tool.description}</small></button>)}</section>)}</aside>
      <main className="canvas-stage" data-testid="canvas-stage" data-edge-count={page.edges.length} data-display-edge-count={displayEdges.length} onDragOver={event => event.preventDefault()}
        onContextMenu={event=>{if((event.target as HTMLElement).closest('.react-flow__node,.canvas-context-menu'))return
          event.preventDefault();setQuickCreate(null);const screen={x:event.clientX,y:event.clientY}
          setContextMenu({kind:'pane',x:screen.x,y:screen.y,flow:reactFlow.screenToFlowPosition(screen)})}}
        onDrop={event => { const tool = byName.get(event.dataTransfer.getData('application/ltt-tool')); if (tool) addTool(tool, reactFlow.screenToFlowPosition({ x: event.clientX, y: event.clientY })) }}>
        <ReactFlow key={page.id} nodes={displayNodes as CanvasNode[]} edges={displayEdges} nodeTypes={nodeTypes} edgeTypes={edgeTypes}
          onNodesChange={(changes: NodeChange[]) => { const persisted = changes.filter(change => ['position', 'add', 'remove', 'replace'].includes(change.type));
            if (persisted.length) dispatch({ type: persisted.every(change => change.type === 'position') ? 'sync' : 'graph', nodes: applyNodeChanges(persisted, page.nodes) as CanvasNode[], edges: page.edges }) }}
          onEdgesChange={(changes: EdgeChange[]) => { const persisted = changes.filter(change => ['add', 'remove', 'replace'].includes(change.type));
            if (persisted.length) dispatch({ type: 'graph', nodes: page.nodes, edges: applyEdgeChanges(persisted, page.edges) as CanvasEdge[] }) }}
          onConnect={onConnect} onReconnect={onReconnectEdge} edgesReconnectable={!readOnly} onConnectEnd={(event,connectionState)=>{
            if(connectionState.isValid||connectionState.toNode||!connectionState.fromNode||connectionState.fromHandle?.type!=='source')return
            const point='changedTouches' in event&&event.changedTouches.length?event.changedTouches[0]:event as MouseEvent
            const screen={x:point.clientX,y:point.clientY};setContextMenu(null)
            setQuickCreate({sourceId:connectionState.fromNode.id,sourceHandle:connectionState.fromHandle.id??'',x:screen.x,y:screen.y,
              flow:reactFlow.screenToFlowPosition(screen)})
          }} onNodeClick={(event, node) => {const additive=event.ctrlKey||event.metaKey||event.shiftKey
            setContextMenu(null);setQuickCreate(null);setSelectedEdges([]);setDesktopPanel(null)
            setSelected(previous=>additive?(previous.includes(node.id)?previous.filter(id=>id!==node.id):[...previous,node.id]):[node.id])
            dispatch({ type: 'select', id: node.id }) }}
          onNodeContextMenu={(event,node)=>{event.preventDefault();setQuickCreate(null);setSelected([node.id]);dispatch({type:'select',id:node.id});
            setContextMenu({kind:'node',nodeId:node.id,x:event.clientX,y:event.clientY,flow:node.position})}}
          onPaneContextMenu={event=>{event.preventDefault();setQuickCreate(null);const screen={x:event.clientX,y:event.clientY};
            setContextMenu({kind:'pane',x:screen.x,y:screen.y,flow:reactFlow.screenToFlowPosition(screen)})}}
          onEdgeClick={(_event, edge) => { setSelected([]); setSelectedEdges([edge.id]); dispatch({ type: 'select' }) }}
          onNodeDragStart={() => { dragBefore.current = structuredClone(state.document) }}
          onNodeDragStop={() => { if (dragBefore.current) dispatch({ type: 'commit', before: dragBefore.current }); dragBefore.current = undefined }}
          onPaneClick={() => { setContextMenu(null);setQuickCreate(null);setSelected([]); setSelectedEdges([]); dispatch({ type: 'select' }) }} onSelectionChange={onSelectionChange}
          onMoveEnd={(_event, viewport) => dispatch({ type: 'viewport', viewport })}
          nodesDraggable={!readOnly} nodesConnectable={!readOnly} elementsSelectable
          multiSelectionKeyCode={['Control','Meta']} selectionOnDrag panOnDrag={[1,2]}
          defaultViewport={page.viewport} minZoom={0.1} maxZoom={2}
          fitView={!page.nodes.length} deleteKeyCode={null}>
          <FlowStatus />
          {showGrid&&<Background color={theme==='light'?'#d8dde5':'#5b2c29'} gap={20} />}{showMinimap&&<MiniMap pannable zoomable />}<Controls showInteractive={!readOnly} />
        </ReactFlow>
        {!page.nodes.length && <div className="canvas-empty"><strong>Bắt đầu {page.name}</strong><span>Chọn công cụ ở Palette hoặc tạo page mới để tách quy trình.</span></div>}
        {!!validationIssues.length && <div className="validation-banner" role="alert"><strong>Workflow chưa hợp lệ</strong>
          <span>{validationIssues.slice(0, 3).map(issue => issue.message).join(' · ')}</span></div>}
        {showLayers&&<aside className="layers-drawer" aria-label="Danh sách lớp"><header><strong>Lớp · {page.name}</strong>
          <button aria-label="Đóng danh sách lớp" onClick={()=>setShowLayers(false)}>×</button></header>
          <ul>{page.frames.map(frame=><li key={frame.id}><span>FRAME</span>{frame.name}</li>)}
            {page.nodes.map(node=><li key={node.id}><button onClick={()=>dispatch({type:'select',id:node.id})}><span>KHỐI</span>{uniqueNodeLabel(node,page.nodes,byName)}</button></li>)}
            {page.notes.map(note=><li key={note.id}><span>NOTE</span>{note.text}</li>)}
            {page.comments.map(comment=><li key={comment.id}><span>COMMENT</span>{comment.text}</li>)}</ul></aside>}
      </main>
      <nav className="page-dock" aria-label="Chuyển page">{state.document.pages.map(item=><button
        key={item.id} aria-pressed={item.id===page.id} onClick={()=>dispatch({type:'pageSelect',id:item.id})}>{item.name}</button>)}</nav>
      {quickConnect&&<aside className="quick-connect-picker" aria-label="Chọn đích kết nối"><header><div><small>OUTPUT</small><strong>{quickConnect.sourceHandle}</strong></div><button aria-label="Đóng chọn kết nối" onClick={()=>setQuickConnect(null)}>×</button></header>
        {quickOptions.length?<div>{quickOptions.map(option=><button key={`${option.targetId}-${option.targetHandle}`} onClick={()=>{onConnect({source:quickConnect.sourceId,sourceHandle:quickConnect.sourceHandle,target:option.targetId,targetHandle:option.targetHandle});setQuickConnect(null)}}>{option.label}</button>)}</div>
          :<p>Chưa có input tương thích. Thêm một node đích rồi thử lại.</p>}</aside>}
      {quickCreate&&<aside className="quick-create-picker" aria-label="Tạo node đích tương thích" style={{left:Math.min(quickCreate.x,window.innerWidth-320),top:Math.min(quickCreate.y,window.innerHeight-420)}}>
        <header><div><small>KẾT NỐI NHANH</small><strong>Chọn node đích</strong></div><button aria-label="Đóng tạo node nhanh" onClick={()=>setQuickCreate(null)}>×</button></header>
        {quickCreateOptions.length?<div>{quickCreateOptions.map(tool=>{const source=page.nodes.find(node=>node.id===quickCreate.sourceId);const sourceTool=byName.get(String(source?.data.tool));return <button key={tool.name} onClick={()=>addConnectedTool(tool,quickCreate.sourceId,quickCreate.sourceHandle,quickCreate.flow)}><strong>{destinationLabel(sourceTool,quickCreate.sourceHandle,tool)}</strong><small>{tool.description}</small></button>})}</div>:<p>Không có node tương thích với đầu ra này.</p>}
      </aside>}
      {edgeInsert&&<aside className="quick-create-picker edge-insert-picker" aria-label="Chèn bước vào kết nối"
        style={{left:Math.min(edgeInsert.x,window.innerWidth-320),top:Math.min(edgeInsert.y,window.innerHeight-420)}}>
        <header><div><small>CHÈN BƯỚC</small><strong>Chọn hành động tương thích</strong></div><button aria-label="Đóng chèn bước" onClick={()=>setEdgeInsert(null)}>×</button></header>
        {insertOptions.length?<div>{insertOptions.map(tool=><button key={tool.name}
          onClick={()=>insertToolOnEdge(tool,edgeInsert.edgeId,edgeInsert.flow)}><strong>{customerToolLabel(tool)}</strong><small>{tool.description}</small></button>)}</div>:
          <p>Không có bước trung gian tương thích với kết nối này.</p>}
      </aside>}
      {contextMenu&&<aside className={`canvas-context-menu ${contextMenu.kind}`} aria-label={contextMenu.kind==='pane'?'Menu khoảng trống Canvas':'Menu thao tác node'}
        style={{left:Math.min(contextMenu.x,window.innerWidth-310),top:Math.min(contextMenu.y,window.innerHeight-520)}}>
        <header><strong>{contextMenu.kind==='pane'?'Thêm vào Canvas':'Thao tác node'}</strong><button aria-label="Đóng menu ngữ cảnh" onClick={()=>setContextMenu(null)}>×</button></header>
        {contextMenu.kind==='pane'?<><div className="context-tool-list">{customerPaletteTools(palette,catalogMode==='advanced').map(tool=><button key={tool.name} onClick={()=>{addTool(tool,contextMenu.flow);setContextMenu(null)}}><strong>{customerToolLabel(tool)}</strong><small>{categoryLabels[tool.category??'advanced']}</small></button>)}</div>
          <hr/><button onClick={()=>{dispatch({type:'pageView',connections:!showConnections});setContextMenu(null)}}>{showConnections?'Ẩn đường nối':'Hiện đường nối'}</button>
          <button onClick={()=>{dispatch({type:'layout'});setContextMenu(null)}}>Tự động sắp xếp node</button></>:
          <>{contextMenu.nodeId&&<><button disabled={readOnly||!!run} onClick={()=>{void prepareScope({mode:'node',node_id:contextMenu.nodeId});setContextMenu(null)}}>Báo giá & chạy node</button>
            <button disabled={readOnly||!!run} onClick={()=>{void prepareScope({mode:'selection',node_ids:downstreamIds(contextMenu.nodeId!)});setContextMenu(null)}}>Chạy từ đây</button>
            <button disabled={readOnly} onClick={()=>{duplicateNode(contextMenu.nodeId!);setContextMenu(null)}}>Sao chép node</button>
            {state.document.pages.filter(item=>item.id!==page.id).map(item=><button key={item.id} disabled={readOnly}
              onClick={()=>{dispatch({type:'nodeMovePage',id:contextMenu.nodeId!,pageId:item.id});setContextMenu(null)}}>Chuyển sang {item.name}</button>)}
            <button className="danger" disabled={readOnly} onClick={()=>{dispatch({type:'delete',ids:[contextMenu.nodeId!]});setSelected([]);setContextMenu(null)}}>Xóa node</button></>}</>}
      </aside>}
      {selectedNode&&<ContextComposer node={selectedNode} tool={byName.get(String(selectedNode.data.tool))} readOnly={readOnly} presentationMode={presentationMode}
        onClose={()=>{setSelected([]);dispatch({type:'select'})}} onAdvanced={()=>setDesktopPanel('inspector')}
        onRun={()=>void prepareScope({mode:'node',node_id:selectedNode.id})} cost={liveQuotes[selectedNode.id]??costs[selectedNode.id]}
        references={referenceOptions} connectedInputs={connectedInputs} onDisconnect={disconnectInput} onReference={reference=>onConnect({source:reference.source,sourceHandle:reference.sourceHandle,
          target:selectedNode.id,targetHandle:reference.targetHandle})}
        onChange={data=>dispatch({type:'update',id:selectedNode.id,data})}/>}
      {(desktopPanel==='inspector'||mobilePanel==='inspector')&&<Inspector className={desktopPanel==='inspector'?'is-open':''} node={selectedNode} tool={selectedNode ? byName.get(String(selectedNode.data.tool)) : undefined} run={run} csrfToken={csrf}
        runHistory={runHistory} onSelectRun={id=>void loadRun(id).then(setRun).catch(()=>setRunError('Không tải được run.'))}
        onReplay={source=>void runAgain(source,csrf).then(next=>{setRun(next);void refreshRunHistory()}).catch(error=>setRunError(error instanceof Error?error.message:'Không thể replay.'))}
        onRestore={source=>void restoreRunAsWorkflow(source,csrf).then(activateWorkflow).catch(error=>setRunError(error instanceof Error?error.message:'Không thể khôi phục workflow.'))}
        readOnly={readOnly} connections={connectionOptions}
        onConnect={(field, value) => { if (!selectedNode) return; const [source, sourceHandle] = value.split('|')
          onConnect({ source, sourceHandle, target: selectedNode.id, targetHandle: field }) }}
        onChange={data => selectedNode && dispatch({ type: 'update', id: selectedNode.id, data })} />}
    </div>
    {assistantOpen&&<aside className="assistant-drawer" aria-label="Workflow Assistant"><header><strong>Workflow Assistant</strong><button aria-label="Đóng Assistant" onClick={()=>setAssistantOpen(false)}>×</button></header>
      <div className="assistant-modes"><button aria-pressed={assistantMode==='analyze'} onClick={()=>setAssistantMode('analyze')}>Phân tích</button><button aria-pressed={assistantMode==='improve'} onClick={()=>setAssistantMode('improve')}>Đề xuất cải tiến</button></div>
      {!!selected.length&&<p className="assistant-context">Ngữ cảnh: {selected.map(id=>byName.get(String(page.nodes.find(node=>node.id===id)?.data.tool))?.label??id).join(', ')}</p>}
      <textarea aria-label="Yêu cầu Assistant" value={assistantPrompt} onChange={event=>setAssistantPrompt(event.target.value)} placeholder="Ví dụ: thêm nhánh tạo giọng đọc và ghép video…"/>
      <button disabled={!workflow||assistantBusy||(assistantMode==='improve'&&assistantPrompt.trim().length<3)} onClick={async()=>{if(!workflow)return;setAssistantBusy(true);setAssistantResult({});try{const context=selected.length?`${assistantPrompt}\n\nNgữ cảnh node đã chọn: ${selected.join(', ')}`:assistantPrompt;setAssistantResult(await previewAssistant(workflow,assistantMode,context,csrf))}catch(error){setAssistantResult({error:error instanceof Error?error.message:'Assistant lỗi'})}finally{setAssistantBusy(false)}}}>{assistantBusy?'Đang phân tích…':'Tạo bản xem trước'}</button>
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

function FlowStatus(){
  const edges=useStore(state=>state.edges.length)
  const nodes=useStore(state=>state.nodes.length)
  return <span className="sr-only" data-testid="flow-store-status">{nodes} node · {edges} kết nối trong renderer</span>
}

type ReferenceOption={source:string;sourceHandle:string;targetHandle:string;label:string;detail:string}
type ConnectedInput={edgeId:string;label:string;detail:string}

function ContextComposer({node,tool,readOnly,presentationMode,onChange,onAdvanced,onClose,onRun,cost,references,connectedInputs,onReference,onDisconnect}:{node:CanvasNode;tool?:PaletteTool;readOnly:boolean;presentationMode:'creative'|'legacy';
  onChange:(data:Record<string,unknown>)=>void;onAdvanced:()=>void;onClose:()=>void;onRun:()=>void;cost?:number;
  references:ReferenceOption[];connectedInputs:ConnectedInput[];onReference:(reference:ReferenceOption)=>void;onDisconnect:(edgeId:string)=>void}) {
  if(!tool)return null
  const params=(node.data.params??{}) as Record<string,unknown>
  const fields=presentationMode==='creative'?primaryFields(tool,params).slice(0,4):primaryFields(tool,params)
  const setParam=(name:string,value:unknown)=>onChange({params:{...params,[name]:value}})
  return <section className="context-composer" aria-label={`Thiết lập ${customerToolLabel(tool)}`}>
    <header><div><small>Đang làm việc với</small><strong>{customerToolLabel(tool)}</strong></div><nav><button onClick={onAdvanced}>Nâng cao</button><button aria-label="Đóng thiết lập" onClick={onClose}>×</button></nav></header>
    {!!connectedInputs.length&&<div className="composer-input-chips" aria-label="Đầu vào đã kết nối">{connectedInputs.map(input=><span key={input.edgeId}><b>@{input.label}</b><small>{input.detail}</small><button disabled={readOnly} aria-label={`Tháo kết nối ${input.label}`} onClick={()=>onDisconnect(input.edgeId)}>×</button></span>)}</div>}
    {!!references.length&&<label className="composer-reference"><span>Tham chiếu đầu vào</span><select disabled={readOnly} value="" onChange={event=>{
      const reference=references.find(item=>`${item.source}|${item.sourceHandle}|${item.targetHandle}`===event.target.value)
      if(reference)onReference(reference)
    }}><option value="">@ Chọn node liên quan…</option>{references.map(reference=><option
      key={`${reference.source}-${reference.sourceHandle}-${reference.targetHandle}`}
      value={`${reference.source}|${reference.sourceHandle}|${reference.targetHandle}`}>@{reference.label} · {reference.detail}</option>)}</select></label>}
    <div className="context-fields">{fields.map(([name,rule])=>{
      const value=params[name]??rule.default??''
      const label=fieldLabel(name)
      if(rule.values?.length)return <label key={name}><span>{label}{rule.required?' *':''}</span><select disabled={readOnly} value={String(value)} onChange={event=>setParam(name,event.target.value)}>
        <option value="">— chọn —</option>{(rule.options??rule.values.map(item=>({value:item,label:String(item)}))).map(option=><option key={String(option.value)} value={String(option.value)}>{option.label}</option>)}</select></label>
      if(rule.type==='bool')return <label key={name} className="composer-check"><input type="checkbox" disabled={readOnly} checked={Boolean(value)} onChange={event=>setParam(name,event.target.checked)}/><span>{label}</span></label>
      if(['prompt','topic','text'].includes(name))return <label key={name} className="composer-prompt"><span>{label}{rule.required?' *':''}</span><textarea disabled={readOnly} value={String(value)} placeholder="Mô tả điều bạn muốn tạo; dùng @ để nhắc tới node liên quan…" onChange={event=>setParam(name,event.target.value)}/></label>
      return <label key={name}><span>{label}{rule.required?' *':''}</span><input disabled={readOnly} value={String(value)} type={rule.type==='int'||rule.type==='number'?'number':'text'}
        placeholder={name==='url'&&tool.name==='video.social_import'?'Dán link TikTok, YouTube Shorts hoặc Reels…':undefined}
        onChange={event=>setParam(name,rule.type==='int'?Number.parseInt(event.target.value):rule.type==='number'?Number(event.target.value):event.target.value)} /></label>
    })}</div>
    <footer><span>{cost===undefined?'Báo giá được tính bởi server':`Tối đa ${cost} credit`}</span><button className="composer-run" disabled={readOnly} onClick={onRun}>✦ {cost===undefined?'Báo giá & chạy':`${cost} · Tiếp tục`}</button></footer>
  </section>
}

export function CanvasShell() { return <ReactFlowProvider><Editor /></ReactFlowProvider> }
