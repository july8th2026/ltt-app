import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from 'react'
import { addEdge, applyEdgeChanges, applyNodeChanges, Background, Controls, MarkerType, MiniMap, Position,
  ReactFlow, ReactFlowProvider, useReactFlow, type Connection, type EdgeChange,
  useStore, useUpdateNodeInternals, type NodeChange } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import './canvas.css'
import { activePage, cloneGraphSelection, connectionAllowed, connectionCreatesCycle, editorReducer, emptyDocument, nextNode,
  type PaletteTool } from './editorState'
import { Inspector } from './Inspector'
import { AnnotationNode, CreativeToolNode, FrameNode, ToolNode } from './ToolNode'
import { CanvasEdgeView } from './CanvasEdgeView'
import { fieldLabel, mediaKind, nodeModality, outputLabel, primaryFields } from './nodePresentation'
import { CANVAS_PRESENTATION_VERSION, customerPaletteTools, customerToolLabel,
  destinationLabel, primaryOutputHandle } from './presentationAdapter'
// ⛔ KHONG import lai cum v2 (`applyAssistant`, `previewAssistant`,
//    `loadSnapshots`, `restoreSnapshot`, `createShare`, `cloneWorkflow`,
//    `exportWorkflow`, `importWorkflow`).
//
//    Trinh soan nap workflow qua `loadOrCreateWorkflowV3` — id thuoc bang
//    `workflow` (v3). Cum tren tra id ay trong `agent_workflows` (v2) va khong
//    thay ⇒ **404 ngay lan bam dau**. Cua may chu van con nguyen; viec chuyen
//    chung sang `/agent/api/v3/` la mot pha rieng. Cho toi luc ay, giao dien
//    khong duoc moi nguoi dung lam mot viec se 404.
//
//    `tests/test_1728_canvas_khong_goi_duong_chet.py` chot dieu nay bang bang
//    dinh tuyen THAT, nen mot lan import lai se do ngay.
import { loadOrCreateWorkflowV3, loadPalette, loadPreferences,
  savePreferences, saveWorkflowV3,
  quoteTool, uploadAsset, WorkflowConflictError, type CanvasDocument,
  type CanvasEdge, type CanvasNode, type Workflow } from './workflowApi'
// Cua v3: trinh soan LUU -> PUBLISH -> TAO run -> DOC. No khong con "lai"
// dong co bang `tickRun` nua; may chu tu tien, client chi poll.
import { cancelRunV3, createRunV3, loadRunV3, publishWorkflowV3,
  RUN_V3_KET_THUC, WorkflowCompileError, type RunV3 } from './workflowApi'
import { RunV3Panel } from './RunV3Panel'

const nodeTypes = { tool: ToolNode, creativeTool: CreativeToolNode, frame: FrameNode, annotation: AnnotationNode }
const edgeTypes = { creative: CanvasEdgeView }

/** Khoá `Idempotency-Key` cho MỘT lần bấm "Chạy ngay".
 *
 * `crypto.randomUUID()` dài 36 ký tự, nằm gọn trong khoảng 8..255 mà
 * `platform_core/public_api/idempotency.py` đòi.
 *
 * ⚠️ `randomUUID` đòi **secure context**. Trang chạy qua `https://` (Cloudflare)
 *    và qua loopback đều đủ điều kiện, nhưng một bản tự dựng phục vụ qua `http://`
 *    một tên máy nội bộ thì không — ở đó `crypto.randomUUID` là `undefined` và
 *    nút "Chạy ngay" sẽ ném `TypeError` thay vì chạy. Nên có lối lui; nó không
 *    cần chuẩn mật mã, chỉ cần **không trùng giữa hai lần bấm**.
 */
function taoKhoaChay(): string {
  const nguon = globalThis.crypto as Crypto | undefined
  if (typeof nguon?.randomUUID === 'function') return nguon.randomUUID()
  return `run-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`
}

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

// Trang thai node v3 (chu HOA, spec §5.3) -> tu vung mau sac ma `ToolNode`
// da biet. ⛔ Khong doi `ToolNode` o day: no la viec cua plan 02.
/** Nhip poll co ban, va do LUI DAN khi cua doc hong.
 *  LUI chu khong DUNG: man hinh nay theo doi mot luot chay DANG TIEU TIEN, nen
 *  bo cuoc nghia la de nguoi dung nhin mot anh chup cu ma tuong la that. Va
 *  khong im lang — moi nhip hong deu hien ngay o dong loi cua ngan keo, va
 *  dong ay tu bien mat khi mot nhip thanh cong. "Thu lai vo han trong im lang"
 *  moi la noi doi; thu lai CO NOI thi khong. */
const NHIP_POLL_MS=1500
const LUI_TOI_DA=3                       //: 1,5s -> 3s -> 6s -> 12s roi giu 12s
const LOI_POLL='Không đọc được lượt chạy — đang thử lại…'
const nhipCho=(soHong:number)=>NHIP_POLL_MS*2**Math.min(soHong,LUI_TOI_DA)

/** Noi su kien theo `seq`: chi giu cai MOI hon cai da co.
 *
 *  🔴 Do duoc tren trinh duyet 23/09: cua huy (`POST /runs/{id}/cancel`) KHONG
 *     nhan `?sau=`, nen no tra CA lich su; con vong poll tra phan tang dan.
 *     Noi mu quang lam dong thoi gian hien `WorkflowStarted` hai lan. Loc theo
 *     `seq` dung cho ca hai nguon, va khong phu thuoc nguon nao tra gi. */
function nhapRun(truoc:RunV3|null,next:RunV3):RunV3{
  if(!truoc||truoc.id!==next.id)return next
  const cuoi=truoc.su_kien.reduce((max,e)=>Math.max(max,e.seq),0)
  return {...next,su_kien:[...truoc.su_kien,...next.su_kien.filter(e=>e.seq>cuoi)]}
}

const TRANG_THAI_NODE_UI:Record<string,string>={PENDING:'queued',READY:'queued',
  QUEUED:'queued',RUNNING:'running',WAITING:'queued',RETRY_SCHEDULED:'retry_needed',
  SUCCEEDED:'done',FAILED:'error',SKIPPED:'queued',CANCELLED:'error',ABANDONED:'error'}

type StarterFlowKind='text-image'|'image-text'|'image-video'

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
  const [liveQuotes,setLiveQuotes]=useState<Record<string,number>>({})
  const [retryNonce, setRetryNonce] = useState(0)
  const [run, setRun] = useState<RunV3|null>(null)
  const [runError, setRunError] = useState('')
  //: so nhip poll HONG LIEN TIEP. Vua lam thoi gian cho lui dan, vua la thu
  //  duy nhat lam effect poll chay lai sau mot cu nga — `run` khong doi khi
  //  request hong, nen khong co no thi khong con `setTimeout` nao ca.
  const [soHong, setSoHong] = useState(0)
  //: node_id -> ma loi bien dich (422 `{ma,node_id,thong_diep}` cua publish).
  const [loiNode,setLoiNode]=useState<Record<string,string>>({})
  // Trang thai cua Assistant / Phien ban / Share da go cung luc voi cac nut
  // cua chung — xem chu thich o khoi `import`.
  const copied = useRef<{nodes:CanvasNode[];edges:CanvasEdge[]}>({nodes:[],edges:[]})
  const autosaveTimer = useRef<number | undefined>(undefined)
  /** Khoá `Idempotency-Key` của lần bấm "Chạy ngay" đang dở. Rỗng = chưa bấm,
   *  hoặc lần bấm trước đã tạo được run. Xem `chayWorkflow`. */
  const khoaChay = useRef<string>('')
  /** Cờ "ĐANG GỬI một lượt chạy" — bật từ lúc bắt đầu tạo run cho tới khi run
   *  được tạo xong hoặc hỏng.
   *
   *  ⚠️ `Idempotency-Key` và cờ này chữa HAI bệnh khác nhau. Khoá chỉ cứu
   *     *thử lại CÙNG một lần bấm* (mạng đứt): cùng khoá ⇒ máy chủ trả lại
   *     run cũ. **Bấm đúp là hai lần bấm ⇒ hai khoá ⇒ hai run, hai lần giữ
   *     chỗ, hai lần trừ tiền.** Chỉ một chốt ở client chặn được.
   *
   *  ⛔ Vì sao là `ref` chứ không phải chỉ `disabled` của DOM: `disabled` chỉ
   *     có hiệu lực SAU một lượt render, và React bỏ qua sự kiện chuột trên
   *     nút disabled nhưng KHÔNG bỏ qua mọi đường vào khác (phím Enter trên
   *     một điều khiển khác, một lối gọi `chayWorkflow` thêm về sau). Chốt
   *     phải nằm ở tầng logic; `dangGui` bên dưới chỉ để giao diện PHẢN ÁNH
   *     nó. Hai thứ luôn đổi cùng nhau. */
  const dangGuiRun = useRef(false)
  const [dangGui,setDangGui] = useState(false)
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
  const hasAnyNodes=state.document.pages.some(item=>item.nodes.length>0)
  const selectedNode = page.nodes.find(node => node.id === state.selectedId)
  const selectedEdge = page.edges.find(edge=>selectedEdges.includes(edge.id))
  const referenceOptions=useMemo(()=>{
    if(!selectedNode)return []
    const targetTool=byName.get(String(selectedNode.data.tool))
    return page.nodes.filter(node=>node.id!==selectedNode.id).flatMap(node=>{
      const sourceTool=byName.get(String(node.data.tool))
      if(!sourceTool||!targetTool)return []
      // Same cycle guard the output `+` picker uses: offering a reference that
      // connectGraph then refuses looks to the customer like a dead control.
      if(connectionCreatesCycle(page.edges,node.id,selectedNode.id))return []
      for(const sourceHandle of Object.keys(sourceTool.returns))for(const targetHandle of Object.keys(targetTool.params_schema)){
        if(connectionAllowed(sourceTool,sourceHandle,targetTool,targetHandle))return [{source:node.id,sourceHandle,targetHandle,
          label:uniqueNodeLabel(node,page.nodes,byName),detail:`${outputLabel(sourceHandle,sourceTool.returns[sourceHandle])} → ${fieldLabel(targetHandle)}`}]
      }
      return []
    })
  },[selectedNode,page.nodes,page.edges,byName])
  const connectedInputs=useMemo(()=>selectedNode?page.edges.filter(edge=>edge.target===selectedNode.id).map(edge=>{
    const source=page.nodes.find(node=>node.id===edge.source);const sourceTool=byName.get(String(source?.data.tool))
    return {edgeId:edge.id,label:source?uniqueNodeLabel(source,page.nodes,byName):edge.source,
      detail:`${outputLabel(edge.sourceHandle??'',String(sourceTool?.returns[edge.sourceHandle??'']??''))} → ${fieldLabel(edge.targetHandle??'đầu vào')}`}
  }):[],[selectedNode,page.edges,page.nodes,byName])

  useEffect(()=>{
    if(!palette.length||!page.nodes.length)return
    const frame=requestAnimationFrame(()=>updateNodeInternals(page.nodes.map(node=>node.id)))
    return()=>cancelAnimationFrame(frame)
  },[updateNodeInternals,palette.length,page.nodes.length,selectedNode?.id])

  useEffect(()=>{
    if(!readOnly||!page.nodes.length)return
    const frame=requestAnimationFrame(()=>reactFlow.fitView({padding:.12,maxZoom:.9,duration:0}))
    return()=>cancelAnimationFrame(frame)
  },[readOnly,page.id,page.nodes.length,reactFlow])

  useEffect(()=>{
    if(!selectedNode||readOnly||presentationMode!=='creative')return
    const frame=requestAnimationFrame(()=>{
      const nodeElement=[...document.querySelectorAll<HTMLElement>('.react-flow__node')]
        .find(element=>element.dataset.id===selectedNode.id)
      const stageElement=document.querySelector<HTMLElement>('.canvas-stage')
      if(!nodeElement||!stageElement)return
      const nodeBox=nodeElement.getBoundingClientRect();const stageBox=stageElement.getBoundingClientRect()
      const obscured=nodeBox.bottom>stageBox.bottom-8||nodeBox.top<stageBox.top+8||nodeBox.left<stageBox.left+64||nodeBox.right>stageBox.right-16
      if(obscured)void reactFlow.fitView({nodes:page.nodes,padding:.12,maxZoom:.9,duration:180})
    })
    return()=>cancelAnimationFrame(frame)
  },[selectedNode?.id,readOnly,presentationMode,page.id,page.nodes,reactFlow])

  useEffect(() => {
    let active = true
    Promise.all([loadPalette(), loadOrCreateWorkflowV3(csrf), loadPreferences()]).then(([result, loaded, preferences]) => {
      if (!active) return
      setPalette(result.tools); setCatalogMeta({models:result.models?.length??0,
        routing:result.routing?.mode??''}); setTheme(preferences.theme); setCatalogMode(preferences.catalog_mode)
      setWorkflow(loaded); dispatch({ type: 'replace', document: loaded.canvas }); setPhase('ready')
    }).catch(() => active && setPhase('error'))
    return () => { active = false }
  }, [csrf])

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
    if (!run || RUN_V3_KET_THUC.has(run.status)) return
    // `active` = phan hoi nay con dung voi man hinh nao khong. Khong co no,
    // mot GET ve MUON de nguoc CANCELLED -> RUNNING (nut "Huy chay" hien lai
    // cho mot luot da chet), hoac lam song lai mot run vua `setRun(null)`.
    let active = true
    const timer = window.setTimeout(() => {
      void loadRunV3(run.id, run.seq_cuoi)
        // Su kien ve theo lo tang dan (`?sau=<seq>`) — NOI, khong thay. Thay
        // la mat lich su moi nhip, va dong thoi gian chi con mot dong.
        .then(next => {
          if (!active) return
          setSoHong(0)
          // Chi xoa thong diep cua CHINH vong poll: mot loi huy/chay dang hien
          // khong phai viec cua no.
          setRunError(cu => cu === LOI_POLL ? '' : cu)
          setRun(truoc => truoc && truoc.id === next.id ? nhapRun(truoc, next) : truoc)
        })
        .catch(() => {
          if (!active) return
          // `soHong` doi => effect chay lai => CO nhip ke tiep. Day moi la
          // duong song: nhanh nay khong dung toi `run`, nen neu chi
          // `setRunError` thi vong poll dung han sau mot blip mang.
          setSoHong(soHong + 1)
          setRunError(LOI_POLL)
        })
    }, nhipCho(soHong))
    return () => { active = false; window.clearTimeout(timer) }
  }, [run, soHong])

  useEffect(() => {
    if (!workflow || phase === 'loading' || offline) return
    if (JSON.stringify(workflow.canvas) === JSON.stringify(state.document)) return
    autosaveTimer.current = window.setTimeout(async () => {
      setPhase('saving')
      try {
        const saved = await saveWorkflowV3({ ...workflow, canvas: state.document }, csrf)
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

  const applyStarterFlow=useCallback((kind:StarterFlowKind)=>{
    if(readOnly||page.nodes.length)return
    const [sourceKind,targetKind]=kind.split('-') as ['text'|'image','image'|'text'|'video']
    const tools=customerPaletteTools(palette,true)
    const sourceTool=tools.find(tool=>tool.primary&&nodeModality(tool)===sourceKind)
      ??tools.find(tool=>nodeModality(tool)===sourceKind)
    const targetTool=tools.find(tool=>tool.primary&&nodeModality(tool)===targetKind)
      ??tools.find(tool=>nodeModality(tool)===targetKind)
    if(!sourceTool||!targetTool){setRunError('Chưa có block phù hợp cho mẫu này.');return}
    const source=nextNode(sourceTool,0);const target=nextNode(targetTool,1)
    source.position={x:140,y:180};target.position={x:540,y:180}
    const sourceHandle=primaryOutputHandle(sourceTool)
    const targetHandle=sourceHandle&&Object.keys(targetTool.params_schema).find(field=>
      connectionAllowed(sourceTool,sourceHandle,targetTool,field))
    const connected=sourceHandle&&targetHandle?connectGraph([source,target],[],{
      source:source.id,sourceHandle,target:target.id,targetHandle},byName):undefined
    if(!connected){setRunError('Hai block của mẫu chưa có cổng kết nối tương thích.');return}
    dispatch({type:'graph',...connected});dispatch({type:'select',id:source.id})
    setSelected([source.id]);setSelectedEdges([]);setDesktopPanel(null);setRunError('')
  },[readOnly,page.nodes.length,palette,byName])

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

  /** LUU -> PUBLISH -> TAO run. Ba lo phai di dung thu tu: `tao_run` tu choi
   *  mot workflow chua publish (422 `chua_publish`), va publish dong bang
   *  DUNG ban nhap vua luu — nen luu phai xong truoc, khong chay song song. */
  const chayWorkflow=useCallback(async()=>{
    const dangChay=run&&!RUN_V3_KET_THUC.has(run.status)
    // ⭐ CHOT BAM DUP. Doc ref, khong doc state: state cua lan bam truoc co
    //    the CHUA kip render khi lan bam thu hai toi. Xem `dangGuiRun`.
    if(!workflow||readOnly||dangChay||dangGuiRun.current)return
    dangGuiRun.current=true;setDangGui(true)
    if(autosaveTimer.current)window.clearTimeout(autosaveTimer.current)
    // ⭐ MOT LAN BAM = MOT KHOA. Khoa sinh O DAY, khong sinh trong
    //    `createRunV3`: chi cho nay biet dau la ranh gioi cua "mot lan bam".
    //
    //    Giu trong ref cho toi khi may chu THAT SU nhan duoc run. Neu lo tao
    //    run hong (mang dut, 503) thi lan thu lai — du la nguoi dung tu bam
    //    lai — van mang dung khoa ay, nen mot run da lo tao ben may chu se
    //    duoc tra ve thay vi tao them mot run thu hai va giu cho lan nua.
    //    Thanh cong roi moi xoa khoa ⇒ lan bam KE TIEP la mot khoa moi, va
    //    nguoi dung chay duoc lan thu hai that.
    if(!khoaChay.current)khoaChay.current=taoKhoaChay()
    setRun(null);setSoHong(0);setDesktopPanel('run');setPhase('saving');setRunError('');setLoiNode({})
    try{
      const saved=await saveWorkflowV3({...workflow,canvas:state.document},csrf)
      setWorkflow(saved);setPhase('saved')
      await publishWorkflowV3(saved,csrf)
      const moi=await createRunV3(saved.id,csrf,khoaChay.current)
      khoaChay.current=''
      setRun(moi)
    }catch(error){
      if(error instanceof WorkflowCompileError){
        setRunError(error.message)
        if(error.nodeId)setLoiNode({[error.nodeId]:error.ma})
      }else if(error instanceof WorkflowConflictError){
        setPhase('conflict');setRunError('Workflow vừa đổi ở nơi khác — tải bản mới rồi chạy lại.')
      }else{
        setRunError(error instanceof Error?error.message:'Không chạy được.')
      }
    }finally{
      // ⛔ `finally`, khong phai cuoi nhanh `try`: neu co chi duoc ha o duong
      //    THANH CONG thi mot loi 402/503 se khoa nut VINH VIEN va nguoi dung
      //    khong bao gio chay lai duoc. Bai "luot dau HONG roi: bam lai PHAI
      //    gui duoc" giu dung cho nay.
      dangGuiRun.current=false;setDangGui(false)
    }
  },[workflow,readOnly,run,state.document,csrf])

  const huyRun=useCallback(()=>{
    if(!run)return
    // Cung mot luat nhu vong poll: phan hoi ve muon khong duoc lam song lai
    // mot run da dong, hay de len mot run khac.
    void cancelRunV3(run.id,csrf)
      .then(next=>setRun(truoc=>truoc&&truoc.id===next.id?nhapRun(truoc,next):truoc))
      .catch(error=>setRunError(error instanceof Error?error.message:'Không hủy được.'))
  },[run,csrf])


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
  // ⛔ `cloneCurrent` / `downloadTemplate` / `importTemplate` da go cung ba nut
  //    cua chung. Hai cai dau goi `/agent/api/workflows/{id}/clone|export` (v2)
  //    voi mot id v3 ⇒ 404. Cai thu ba goi `/agent/api/workflows/import` —
  //    duong nay CON SONG, nhung no tao mot ban ghi `agent_workflows` (v2) roi
  //    dat id v2 ay vao trinh soan; lan tu dong luu ke tiep di qua
  //    `saveWorkflowV3` va 404. Mot loi moi dan toi canvas khong luu duoc thi
  //    hong hon mot loi moi 404 ngay, nen no di cung hai cai kia.
  //    `activateWorkflow` go theo vi khong con ai goi.
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
    measured:{width,height:readOnly?244:creative?(node.id===selectedNode?.id?370:258):334},handles:[
      ...inputFields.map((id,index)=>({id,type:'target' as const,position:Position.Left,x:-22,y:34+index*34,width:44,height:44})),
      ...outputHandles.map((id,index)=>({id,type:'source' as const,position:Position.Right,x:width-22,y:46+index*42,width:44,height:44}))],
    selected: node.id === state.selectedId || selected.includes(node.id),
    data: { ...node.data, __tool: tool, __cost: liveQuotes[node.id],
      __readOnly: readOnly,__inputFields:inputFields,__label:node.label,
      __onParamChange: (name:string,value:unknown) => dispatch({type:'update',id:node.id,data:{
        params:{...((node.data.params??{}) as Record<string,unknown>),[name]:value}}}),
      __onRename:(label:string)=>dispatch({type:'nodeLabel',id:node.id,label}),
      __onDuplicate:()=>duplicateNode(node.id),
      __onMenu:(x:number,y:number)=>{setSelected([node.id]);setSelectedEdges([]);dispatch({type:'select',id:node.id});
        setDesktopPanel(null);setQuickCreate(null);setContextMenu({kind:'node',nodeId:node.id,x,y,flow:node.position})},
      __onQuickConnect: (sourceHandle:string)=>setQuickConnect({sourceId:node.id,sourceHandle}),
      __onOpen:()=>{setSelected([node.id]);setSelectedEdges([]);dispatch({type:'select',id:node.id});setDesktopPanel('inspector')},
      __onUpload:(files:File[])=>void uploadToNode(node.id,files),
      __onGenerate:()=>generateInNode(node.id),
      __references:node.id===selectedNode?.id?referenceOptions:[],
      __connectedInputs:node.id===selectedNode?.id?connectedInputs:[],
      __onReference:(reference:ReferenceOption)=>onConnect({source:reference.source,sourceHandle:reference.sourceHandle,
        target:node.id,targetHandle:reference.targetHandle}),
      __onDisconnect:disconnectInput,
      __loiNode: loiNode[node.id] ? node.id : undefined,
      __status: loiNode[node.id] ? 'invalid'
        : TRANG_THAI_NODE_UI[String(run?.nodes.find(item => item.node_id === node.id)?.status ?? '')]
        ?? 'draft' } })})
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
  }, [page, state.selectedId, selected, selectedNode, byName, palette, liveQuotes, loiNode, run,
    readOnly,presentationMode,uploadToNode,generateInNode,duplicateNode,referenceOptions,connectedInputs,onConnect,disconnectInput])
  const displayEdges = useMemo(() => (showConnections ? page.edges : []).map(edge => {
    const isError = edge.data?.condition === 'error'
    const sourceTool=byName.get(String(page.nodes.find(node=>node.id===edge.source)?.data.tool))
    const kind=String(sourceTool?.returns[edge.sourceHandle??'']??'data').replace('[]','')
    const trangThai=(id:string)=>run?.nodes.find(item=>item.node_id===id)?.status
    const running=run?.status==='RUNNING'&&trangThai(edge.source)==='SUCCEEDED'&&trangThai(edge.target)!=='SUCCEEDED'
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
  const quickNewOptions=quickConnect?customerPaletteTools(palette,catalogMode==='advanced').filter(tool=>{
    const source=page.nodes.find(node=>node.id===quickConnect.sourceId);const sourceTool=byName.get(String(source?.data.tool))
    return Object.keys(tool.params_schema).some(field=>connectionAllowed(sourceTool,quickConnect.sourceHandle,tool,field))
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
  const runDaXong=Boolean(run&&RUN_V3_KET_THUC.has(run.status))
  const persistPreferences=(nextTheme:'light'|'dark',nextCatalog:'simple'|'advanced')=>{
    setTheme(nextTheme);setCatalogMode(nextCatalog)
    void savePreferences({theme:nextTheme,catalog_mode:nextCatalog,
      presentation_version:CANVAS_PRESENTATION_VERSION},csrf).catch(()=>setPhase('error'))
  }
  return <section className={`canvas-shell theme-${theme}`} data-presentation={presentationMode}
    aria-label="LTT Agent Canvas" tabIndex={0} onKeyDown={onKeyDown}>
    <header className="canvas-toolbar"><a className="canvas-home" href="/agent" aria-label="Về Agent AI">LTT</a><div className="workflow-identity"><input aria-label="Tên workflow"
      value={workflow?.name ?? ''} disabled={!workflow || readOnly} onChange={event=>workflow&&setWorkflow({...workflow,name:event.target.value})}
      onBlur={()=>workflow&&saveWorkflowV3({...workflow,canvas:state.document},csrf).then(setWorkflow).catch(()=>setPhase('error'))}/>
      <span>{readOnly ? 'Mobile · chỉ xem' : `Canvas v2 · ${page.name} · ${page.nodes.length} node · ${page.edges.length} kết nối`}</span></div>
      <div className="canvas-top-actions"><span className={`save-state ${phase}`} aria-live="polite">{offline ? 'Ngoại tuyến' : phase === 'saving' ? 'Đang lưu…' : phase === 'conflict' ? 'Xung đột' : phase === 'error' ? 'Lỗi lưu' : 'Đã lưu'}</span>
        {phase==='conflict'&&<button className="save-recovery" onClick={()=>location.reload()}>Tải bản mới</button>}
        {phase==='error'&&<button className="save-recovery" onClick={()=>setRetryNonce(value=>value+1)}>Thử lưu lại</button>}
        <button title="Đổi giao diện" aria-label={theme==='light'?'Chuyển sang nền tối':'Chuyển sang nền sáng'} onClick={()=>persistPreferences(theme==='light'?'dark':'light',catalogMode)}>{theme==='light'?'☾':'☀'}</button>
        <button title="Bảng lệnh" aria-label="Mở bảng lệnh" onClick={()=>setCommandOpen(true)}>⌘</button>
        {/* Nut "AI" (Assistant) va "↗" (Phien ban & chia se) da bo: ca hai ngan
            keo phia sau chung chi goi cua v2, va cua v2 khong biet id v3. */}
        <button className="run-primary" disabled={readOnly||!page.nodes.length} aria-pressed={desktopPanel==='run'} onClick={()=>setDesktopPanel(value=>value==='run'?null:'run')}>Chạy</button></div>
      <nav className={`operation-drawer${desktopPanel==='run'?' is-open':''}`} aria-label="Chạy workflow"><header><strong>Chạy workflow</strong><button aria-label="Đóng bảng chạy" onClick={()=>setDesktopPanel(null)}>×</button></header>
        {presentationMode==='legacy'&&<div className="legacy-run-tools"><button disabled={!selected.length || readOnly} onClick={duplicate}>Nhân bản</button>
          <button disabled={(!selected.length && !selectedEdges.length) || readOnly}
            onClick={() => dispatch(selectedEdges.length ? { type: 'deleteEdges', ids: selectedEdges } : { type: 'delete', ids: selected })}>Xóa</button>
          {selectedEdges.length===1&&<button disabled={readOnly} onClick={toggleErrorBranch}>Nhánh: {selectedEdge?.data?.condition==='error'?'Lỗi':'Thành công'}</button>}
          <button disabled={readOnly} onClick={() => dispatch({ type: 'layout' })}>Tự xếp</button>
          <button aria-pressed={showLayers} onClick={()=>setShowLayers(value=>!value)}>Lớp</button>
          <button aria-pressed={showGrid} onClick={()=>dispatch({type:'pageView',grid:!showGrid})}>Lưới</button>
          <button aria-pressed={showConnections} onClick={()=>dispatch({type:'pageView',connections:!showConnections})}>Đường nối</button>
          <button aria-pressed={showMinimap} onClick={()=>dispatch({type:'pageView',minimap:!showMinimap})}>Bản đồ</button></div>}
        {/* 01b chay CA do thi da publish: khong con chon pham vi, khong con
            `use_cache`, khong con buoc duyet bao gia — ba thu ay la ngu nghia
            cua Plan v1. May chu chot `credit_max` ngay luc publish. */}
        <section className="run-scope-preview" aria-label="Phạm vi và chi phí"><small>PHẠM VI</small><strong>Toàn workflow</strong>
          <span>{page.nodes.length} block · server chốt chi phí tối đa khi publish</span></section>
        {/* Nhan doi theo `dangGui`: nuot im lang lan bam thu hai chi lam nguoi
            dung bam them nua. Ho phai THAY lang minh da di. */}
        {!run&&<button className="run-confirm" aria-busy={dangGui||undefined}
          disabled={readOnly||!workflow||!page.nodes.length||phase==='saving'||dangGui}
          onClick={()=>void chayWorkflow()}>{dangGui?'Đang gửi…':'Chạy ngay'}</button>}
        {runDaXong&&<button onClick={()=>{setRun(null);setRunError('');setSoHong(0)}}>Tạo bản chạy mới</button>}
        <RunV3Panel run={run} onCancel={huyRun}/>
        {runError && <span className="run-error" role="alert">{runError}</span>}</nav>
      {presentationMode==='legacy'&&<div className={`legacy-save-state save-state ${phase}`} aria-live="polite">{offline ? 'Ngoại tuyến · chờ thử lại' : phase === 'saving' ? 'Đang lưu…' : phase === 'conflict'
        ? <>Xung đột <button onClick={() => location.reload()}>Tải bản mới</button></>
        : phase === 'error' ? <>Lưu lỗi <button onClick={() => setRetryNonce(value => value + 1)}>Thử lại</button></> : 'Đã lưu'}</div>}</header>
    <nav className="canvas-mobile-tabs" aria-label="Khu vực Canvas">{(['canvas','palette','inspector'] as const).map(item=><button key={item} className={mobilePanel===item?'active':''} aria-pressed={mobilePanel===item} onClick={()=>setMobilePanel(item)}>{item==='canvas'?'Canvas':item==='palette'?'Công cụ':'Chi tiết'}</button>)}</nav>
    <div className={`canvas-body panel-${mobilePanel}${selectedNode&&presentationMode==='legacy'?' has-composer':''}`}>
      <nav className="canvas-rail" aria-label="Công cụ Canvas">
        <button title="Chọn" aria-label="Công cụ chọn" aria-pressed={!desktopPanel}>↖</button>
        <button title="Thêm node" aria-label="Mở công cụ" aria-pressed={desktopPanel==='tools'} onClick={()=>{const open=desktopPanel!=='tools';setDesktopPanel(open?'tools':null);if(open&&presentationMode==='creative'){setSelected([]);setSelectedEdges([]);dispatch({type:'select'})}}}>＋</button>
        <button title="Mẫu & thiết lập" aria-label="Mở mẫu và thiết lập" aria-pressed={desktopPanel==='workspace'} onClick={()=>setDesktopPanel(value=>value==='workspace'?null:'workspace')}>▦</button>
        {hasAnyNodes&&<><button title="Lớp" aria-label="Mở danh sách lớp" aria-pressed={showLayers} onClick={()=>setShowLayers(value=>!value)}>☷</button>
          <button title="Sticky note" aria-label="Tạo sticky note" disabled={readOnly} onClick={()=>dispatch({type:'noteAdd',text:'Ghi chú mới'})}>□</button>
          <button title="Bình luận" aria-label="Tạo comment" disabled={readOnly} onClick={()=>dispatch({type:'commentAdd',text:'Bình luận mới'})}>◌</button></>}
        <span />
        <button title="Hoàn tác" aria-label="Hoàn tác" disabled={!state.past.length||readOnly} onClick={()=>dispatch({type:'undo'})}>↶</button>
        <button title="Làm lại" aria-label="Làm lại" disabled={!state.future.length||readOnly} onClick={()=>dispatch({type:'redo'})}>↷</button>
      </nav>
      <aside className={`canvas-palette${desktopPanel==='tools'||desktopPanel==='workspace'?' is-open':''}${desktopPanel==='workspace'?' workspace-only':' tools-only'}`} aria-label="Palette công cụ"><header className="drawer-heading"><h2>{desktopPanel==='workspace'?'Mẫu & thiết lập':'Thêm block'}</h2><button aria-label="Đóng Palette" onClick={()=>setDesktopPanel(null)}>×</button></header>
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
            <small>{frame.node_ids.length} node</small><button aria-label={`Xóa ${frame.name}`} disabled={readOnly}
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
          {/* O "Ngan sach toi da" da GO (review I4): khong mot tep
              `platform_core/workflow/*` nao doc `budget_max_credit` o v3 — dong
              co chot tran bang `version.estimated_max` luc publish. Giu lai o
              nhap ay la hua voi nguoi dung mot tran chi tieu ma khong ai thi
              hanh: noi doi ve TIEN. Tran that hien o bang luot chay
              (`credit_charged/credit_max`, RunV3Panel). Khoa `budget_max_credit`
              van con trong `document` vi `di_tru_m1.py` mang no sang tu ban
              nhap cu — go o nhap khong duoc lam mat du lieu ay. */}
          {/* Nut "AI dung Canvas" da bo: `planWorkflow` sinh Plan v1, va lop ay
              chet o task 8 (spec §17.6). Assistant v3 la viec cua phase 11. */}
          {/* Nhom "Nhan workflow / Xuat mau / Nhap mau" da bo: ca ba di qua cua
              v2 (`/agent/api/workflows/...`) trong khi trinh soan nap id tu cua
              v3 — bam vao la 404, hoac (nhap mau) lam canvas khong luu duoc
              nua. Cua may chu van con; noi lai chung o `/agent/api/v3/` la mot
              pha rieng. */}</div>
        {Object.entries(groups).map(([group, tools]) => <section key={group}><h3>{group}</h3>
        {tools?.map(tool => <button key={tool.name} draggable={!readOnly} disabled={readOnly}
          onDragStart={event => event.dataTransfer.setData('application/ltt-tool', tool.name)} onClick={() => addTool(tool)}
          aria-label={`Thêm ${customerToolLabel(tool)}`}><strong>{customerToolLabel(tool)}</strong><small>{tool.description}</small></button>)}</section>)}</aside>
      <section className="canvas-stage" data-testid="canvas-stage" data-edge-count={page.edges.length} data-display-edge-count={displayEdges.length} onDragOver={event => event.preventDefault()}
        onContextMenu={event=>{if((event.target as HTMLElement).closest('.react-flow__node,.canvas-context-menu'))return
          event.preventDefault();setQuickCreate(null);const screen={x:event.clientX,y:event.clientY}
          setContextMenu({kind:'pane',x:screen.x,y:screen.y,flow:reactFlow.screenToFlowPosition(screen)})}}
        onDrop={event => { const tool = byName.get(event.dataTransfer.getData('application/ltt-tool')); if (tool) addTool(tool, reactFlow.screenToFlowPosition({ x: event.clientX, y: event.clientY })) }}>
        <ReactFlow key={page.id} nodes={displayNodes as CanvasNode[]} edges={displayEdges} nodeTypes={nodeTypes} edgeTypes={edgeTypes} ariaLabelConfig={NHAN_TRO_NANG_VI}
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
          {showGrid&&<Background color={theme==='light'?'#d8dde5':'#242a31'} gap={20} />}{showMinimap&&<MiniMap pannable zoomable />}<Controls orientation="horizontal" showInteractive={!readOnly} />
        </ReactFlow>
        {!page.nodes.length && <section className="canvas-empty first-run" aria-label="Bắt đầu workflow"><small>3 BƯỚC ĐẦU TIÊN</small><h2>Tạo kết quả đầu tiên</h2><ol><li>Chọn một mẫu</li><li>Nhập hoặc tải nội dung</li><li>Kiểm tra chi phí trước khi chạy</li></ol><div className="starter-flows">
          <button onClick={()=>applyStarterFlow('text-image')}><strong>Prompt thành hình ảnh</strong><span>Viết một lần, tạo ảnh từ nội dung đó</span></button>
          <button onClick={()=>applyStarterFlow('image-text')}><strong>Hiểu nội dung hình ảnh</strong><span>Tải hoặc tạo ảnh, rồi yêu cầu AI phân tích</span></button>
          <button onClick={()=>applyStarterFlow('image-video')}><strong>Ảnh thành video</strong><span>Dùng ảnh làm khung đầu cho video</span></button>
          <button className="blank-flow" onClick={()=>setDesktopPanel('tools')}>Bắt đầu với Canvas trống</button></div></section>}
        {!!Object.keys(loiNode).length && <div className="validation-banner" role="alert"><strong>Workflow chưa biên dịch được</strong>
          <span>{runError||Object.values(loiNode).join(' · ')}</span></div>}
        {showLayers&&<aside className="layers-drawer" aria-label="Danh sách lớp"><header><strong>Lớp · {page.name}</strong>
          <button aria-label="Đóng danh sách lớp" onClick={()=>setShowLayers(false)}>×</button></header>
          <ul>{page.frames.map(frame=><li key={frame.id}><span>FRAME</span>{frame.name}</li>)}
            {page.nodes.map(node=><li key={node.id}><button onClick={()=>dispatch({type:'select',id:node.id})}><span>KHỐI</span>{uniqueNodeLabel(node,page.nodes,byName)}</button></li>)}
            {page.notes.map(note=><li key={note.id}><span>NOTE</span>{note.text}</li>)}
            {page.comments.map(comment=><li key={comment.id}><span>COMMENT</span>{comment.text}</li>)}</ul></aside>}
      </section>
      <nav className="page-dock" aria-label="Chuyển page">{state.document.pages.map((item,index)=><button
        key={item.id} aria-pressed={item.id===page.id} onClick={()=>dispatch({type:'pageSelect',id:item.id})}>{item.name||`Page ${index+1}`}</button>)}</nav>
      {quickConnect&&<aside className="quick-connect-picker" aria-label="Chọn bước tiếp theo"><header><div><small>BƯỚC TIẾP THEO TỪ</small><strong>{(()=>{const source=page.nodes.find(node=>node.id===quickConnect.sourceId);const sourceTool=byName.get(String(source?.data.tool));return outputLabel(quickConnect.sourceHandle,String(sourceTool?.returns[quickConnect.sourceHandle]??''))})()}</strong></div><button aria-label="Đóng chọn bước tiếp theo" onClick={()=>setQuickConnect(null)}>×</button></header>
        {!!quickOptions.length&&<section><small>NỐI VỚI BLOCK ĐÃ CÓ</small>{quickOptions.map(option=><button key={`${option.targetId}-${option.targetHandle}`} onClick={()=>{onConnect({source:quickConnect.sourceId,sourceHandle:quickConnect.sourceHandle,target:option.targetId,targetHandle:option.targetHandle});setQuickConnect(null)}}>{option.label}</button>)}</section>}
        {!!quickNewOptions.length&&<section><small>TẠO BLOCK MỚI</small>{quickNewOptions.map(tool=>{const source=page.nodes.find(node=>node.id===quickConnect.sourceId);const sourceTool=byName.get(String(source?.data.tool));return <button key={tool.name} onClick={()=>{addConnectedTool(tool,quickConnect.sourceId,quickConnect.sourceHandle,{x:(source?.position.x??0)+420,y:source?.position.y??0});setQuickConnect(null)}}><strong>{destinationLabel(sourceTool,quickConnect.sourceHandle,tool)}</strong><span>{categoryLabels[tool.category??'advanced']}</span></button>})}</section>}
        {!quickOptions.length&&!quickNewOptions.length&&<p>Không có bước tương thích với nội dung này.</p>}</aside>}
      {quickCreate&&<aside className="quick-create-picker" aria-label="Tạo block đích tương thích" style={{left:Math.min(quickCreate.x,window.innerWidth-320),top:Math.min(quickCreate.y,window.innerHeight-420)}}>
        <header><div><small>BƯỚC TIẾP THEO</small><strong>Chọn kết quả muốn tạo</strong></div><button aria-label="Đóng tạo block nhanh" onClick={()=>setQuickCreate(null)}>×</button></header>
        {quickCreateOptions.length?<div>{quickCreateOptions.map(tool=>{const source=page.nodes.find(node=>node.id===quickCreate.sourceId);const sourceTool=byName.get(String(source?.data.tool));return <button key={tool.name} onClick={()=>addConnectedTool(tool,quickCreate.sourceId,quickCreate.sourceHandle,quickCreate.flow)}><strong>{destinationLabel(sourceTool,quickCreate.sourceHandle,tool)}</strong><small>{categoryLabels[tool.category??'advanced']}</small></button>})}</div>:<p>Không có bước tương thích với nội dung này.</p>}
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
          <>{contextMenu.nodeId&&<><button disabled={readOnly} onClick={()=>{duplicateNode(contextMenu.nodeId!);setContextMenu(null)}}>Sao chép node</button>
            {state.document.pages.filter(item=>item.id!==page.id).map(item=><button key={item.id} disabled={readOnly}
              onClick={()=>{dispatch({type:'nodeMovePage',id:contextMenu.nodeId!,pageId:item.id});setContextMenu(null)}}>Chuyển sang {item.name}</button>)}
            <button className="danger" disabled={readOnly} onClick={()=>{dispatch({type:'delete',ids:[contextMenu.nodeId!]});setSelected([]);setContextMenu(null)}}>Xóa node</button></>}</>}
      </aside>}
      {selectedNode&&presentationMode==='legacy'&&<ContextComposer node={selectedNode} tool={byName.get(String(selectedNode.data.tool))} readOnly={readOnly} presentationMode={presentationMode}
        onClose={()=>{setSelected([]);dispatch({type:'select'})}} onAdvanced={()=>setDesktopPanel('inspector')}
        cost={liveQuotes[selectedNode.id]}
        references={referenceOptions} connectedInputs={connectedInputs} onDisconnect={disconnectInput} onReference={reference=>onConnect({source:reference.source,sourceHandle:reference.sourceHandle,
          target:selectedNode.id,targetHandle:reference.targetHandle})}
        onChange={data=>dispatch({type:'update',id:selectedNode.id,data})}/>}
      {(desktopPanel==='inspector'||mobilePanel==='inspector')&&<Inspector className={desktopPanel==='inspector'?'is-open':''} node={selectedNode} tool={selectedNode ? byName.get(String(selectedNode.data.tool)) : undefined} csrfToken={csrf}
        readOnly={readOnly} connections={connectionOptions}
        onConnect={(field, value) => { if (!selectedNode) return; const [source, sourceHandle] = value.split('|')
          onConnect({ source, sourceHandle, target: selectedNode.id, targetHandle: field }) }}
        onChange={data => selectedNode && dispatch({ type: 'update', id: selectedNode.id, data })} />}
    </div>
    {/* Ngan keo Assistant (AI) va ngan keo "Phien ban & chia se" da bo.
        Ca hai chi goi cua v2: `/agent/api/workflows/{id}/assistant/*`,
        `/snapshots`, `/snapshots/{rev}/restore`, `/shares`. Trinh soan nap id
        tu cua v3 nen moi lan bam deu 404. May chu van giu nguyen cum nay; noi
        lai chung o `/agent/api/v3/` la mot pha rieng. */}
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

function ContextComposer({node,tool,readOnly,presentationMode,onChange,onAdvanced,onClose,cost,references,connectedInputs,onReference,onDisconnect}:{node:CanvasNode;tool?:PaletteTool;readOnly:boolean;presentationMode:'creative'|'legacy';
  onChange:(data:Record<string,unknown>)=>void;onAdvanced:()=>void;onClose:()=>void;cost?:number;
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
    <footer><span>{cost===undefined?'Chi phí do server xác nhận':`Tối đa ${cost} credit`}</span></footer>
  </section>
}

// Nhãn trợ năng của React Flow mặc định là tiếng Anh (`Zoom In`, `Fit View`, `Mini Map`…);
// @xyflow/react ≥12.5 nhận `ariaLabelConfig` để thay (khoá: @xyflow/system constants).
const NHAN_TRO_NANG_VI = {
  'node.a11yDescription.default': 'Nhấn Enter hoặc Space để chọn khối. Nhấn Delete để xoá, Escape để huỷ.',
  'node.a11yDescription.keyboardDisabled': 'Nhấn Enter hoặc Space để chọn khối, rồi dùng phím mũi tên để di chuyển. Nhấn Delete để xoá, Escape để huỷ.',
  'node.a11yDescription.ariaLiveMessage': ({ x, y }: { direction: string; x: number; y: number }) => `Đã di chuyển khối. Vị trí mới x: ${x}, y: ${y}`,
  'edge.a11yDescription.default': 'Nhấn Enter hoặc Space để chọn dây nối. Nhấn Delete để xoá, Escape để huỷ.',
  'controls.ariaLabel': 'Điều khiển khung vẽ',
  'controls.zoomIn.ariaLabel': 'Phóng to',
  'controls.zoomOut.ariaLabel': 'Thu nhỏ',
  'controls.fitView.ariaLabel': 'Vừa khung nhìn',
  'controls.interactive.ariaLabel': 'Bật/tắt tương tác',
  'minimap.ariaLabel': 'Bản đồ thu nhỏ',
  'handle.ariaLabel': 'Điểm nối',
}

export function CanvasShell() { return <ReactFlowProvider><Editor /></ReactFlowProvider> }
