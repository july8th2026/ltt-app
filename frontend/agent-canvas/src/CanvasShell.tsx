import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from 'react'
import { addEdge, applyEdgeChanges, applyNodeChanges, Background, Controls, MarkerType, MiniMap,
  ReactFlow, ReactFlowProvider, useReactFlow, type Connection, type EdgeChange,
  useStore, useUpdateNodeInternals, type NodeChange } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import './canvas.css'
import { activePage, cloneGraphSelection, connectionCreatesCycle, editorReducer,
  emptyDocument, nextNode } from './editorState'
import { CanvasEdgeView } from './CanvasEdgeView'
// ⭐ MOT component cho moi node, MOT form sinh tu luoc do, MOT palette sinh tu
//    `/agent/api/v3/palette`. Bon tep trinh bay go cung (`nodePresentation.ts`,
//    `presentationAdapter.ts`, `ToolNode.tsx`, `Inspector.tsx`) da xoa o plan
//    02 task 15 — chung la bang tra cuu ma `tests/test_967_*` dem hang chet.
//    Them mot app khong con phai sua mot dong nao trong `src/`.
import { NODE_TYPES } from './nodes/NodeRenderer'
import { AnnotationNode, FrameNode } from './nodes/TrangTri'
import { MIME_NODE, PaletteV2 } from './palette/PaletteV2'
import { FormTuLuocDo } from './inspector/FormTuLuocDo'
import { noiDuoc, slugCongCu, timNut, typeTuSlug } from './nodeDefinition'
import type { LuatNoiDay, NhomPalette, NodeDefinition } from './nodeDefinition'
import { taiPalette } from './paletteApi'
// ⛔ KHONG import lai cum v2 (`applyAssistant`, `previewAssistant`,
//    `loadSnapshots`, `restoreSnapshot`, `createShare`, `cloneWorkflow`,
//    `exportWorkflow`, `importWorkflow`, `loadPalette`).
//
//    Trinh soan nap workflow qua `loadOrCreateWorkflowV3` — id thuoc bang
//    `workflow` (v3). Cum tren tra id ay trong `agent_workflows` (v2) va khong
//    thay ⇒ **404 ngay lan bam dau**. Cua may chu van con nguyen; viec chuyen
//    chung sang `/agent/api/v3/` la mot pha rieng. Cho toi luc ay, giao dien
//    khong duoc moi nguoi dung lam mot viec se 404.
//
//    `tests/test_1728_canvas_khong_goi_duong_chet.py` chot dieu nay bang bang
//    dinh tuyen THAT, nen mot lan import lai se do ngay.
import { loadOrCreateWorkflowV3, loadPreferences,
  savePreferences, saveWorkflowV3,
  quoteTool, WorkflowConflictError, type CanvasDocument,
  type CanvasEdge, type CanvasNode, type Workflow } from './workflowApi'
// Cua v3: trinh soan LUU -> PUBLISH -> TAO run -> DOC. No khong con "lai"
// dong co bang `tickRun` nua; may chu tu tien, client chi poll.
import { cancelRunV3, createRunV3, loadRunV3, publishWorkflowV3,
  RUN_V3_KET_THUC, WorkflowCompileError, type RunV3 } from './workflowApi'
import { NHAN_TRANG_THAI_NODE, RunV3Panel } from './RunV3Panel'

// ⚠️ `NODE_TYPES` (`{ ltt: NodeRenderer }`) ve MOI node cua do thi — do la ca
//    y do cua spec §13.2. `frame`/`annotation` khong phai node do thi: chung
//    la trang tri, khong cong, khong tham so, `bien_dich.py` khong thay. React
//    Flow ve moi thu bang MOT bang nen chung phai nam day; go chung ra thi
//    frame/sticky note roi ve node mac dinh va man hinh hong im lang.
const nodeTypes = { ...NODE_TYPES, frame: FrameNode, annotation: AnnotationNode }
const edgeTypes = { creative: CanvasEdgeView }

//: `apps/agent/routes/workspace.py` chi nhan dung gia tri nay. No khong phai
//  mot che do trinh bay nua — chi la hang so hop dong cua cua `/preferences`.
const PHIEN_BAN_TRINH_BAY = 'creative-v1' as const

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

/** Dinh nghia THAY THE cho mot node ma palette khong con tra ve.
 *
 *  🔴 Node bi xoa khoi tool registry, hoac nguoi dung mat quyen app, thi
 *     `dinhNghia.get(...)` tra `undefined`. Loc no khoi `displayNodes` la cach
 *     hong te nhat: node BIEN MAT khoi man hinh nhung van nam trong tai lieu
 *     va van duoc luu — nguoi dung sua mot do thi ho khong nhin thay het.
 *     Ve no ra, noi ro la khong con, va de nguoi dung xoa duoc.
 */
function nutThieu(slug: string): NodeDefinition {
  return { type: typeTuSlug(slug), type_version: 0, kind: 'data',
    category: 'DATA', title: slug,
    description: 'Node này không còn trong bảng node — kiểm tra quyền app hoặc xoá nó.',
    icon: '', app_name: '', cong_vao: [], cong_ra: [],
    tham_so: { type: 'object', properties: {}, required: [] },
    thi_hanh: 'job', side_effect: '', resource: {}, timeout_expr: '',
    retry_mac_dinh: { max: 0, backoff_s: 0 },
    gia: { kieu: 'mien_phi', so: 0, job_type: '' },
    credential: [], quyen: [], cho: [], ma_loi: [],
    co_mock: false, publish_duoc: false }
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

type BangDinhNghia = Map<string, NodeDefinition>

/** `NodeDefinition` cua mot node trong do thi.
 *
 *  ⭐ Node v3 luu `data.tool` = **slug cong cu** (`image.generate`), con
 *     `NodeDefinition.type` la `app.image.generate`
 *     (`platform_core/workflow/nut.py::tu_toolspec`). `bien_dich._node` doc
 *     dung `data.tool` ay, nen hinh dang luu tru KHONG doi o task nay — chi
 *     lop trinh bay doi. Ghep tien to o dung MOT cho: `typeTuSlug`.
 */
const dinhNghiaCua = (bang: BangDinhNghia, node?: CanvasNode) =>
  node ? bang.get(String(node.data.tool)) : undefined

/** Noi hai cong, tra do thi moi — hoac `undefined` neu luat tu choi.
 *
 *  ⛔ Luat noi day tai TU SERVER (`he_kieu.xuat_luat_noi_day()`), khong cai
 *     dat lai o client: hai ban cai dat song song thi lech, va lech im lang.
 */
function noiDoThi(nodes:CanvasNode[],edges:CanvasEdge[],connection:Connection,
                  bang:BangDinhNghia,luat:LuatNoiDay|null){
  if(!luat||!connection.source||!connection.target||!connection.sourceHandle||!connection.targetHandle)return undefined
  const ndRa=dinhNghiaCua(bang,nodes.find(node=>node.id===connection.source))
  const ndVao=dinhNghiaCua(bang,nodes.find(node=>node.id===connection.target))
  const ra=ndRa?.cong_ra.find(c=>c.ten===connection.sourceHandle)
  const vao=ndVao?.cong_vao.find(c=>c.ten===connection.targetHandle)
  if(!ra||!vao)return undefined
  if(connectionCreatesCycle(edges,connection.source,connection.target))return undefined
  const sourceHandle=connection.sourceHandle;const targetHandle=connection.targetHandle
  const cungCong=edges.filter(edge=>edge.target===connection.target&&edge.targetHandle===targetHandle)
  // Cong nhan nhieu canh ⇒ GIU cac canh cu (tru chinh canh dang noi lai).
  // Cong mot canh ⇒ canh moi THAY canh cu, nen so canh "dang co" la 0.
  const giuLai=vao.nhieu?cungCong.filter(edge=>!(edge.source===connection.source&&edge.sourceHandle===sourceHandle)):[]
  if(!noiDuoc(luat,ra.kieu,vao.kieu,giuLai.length,vao.nhieu))return undefined
  const conLai=edges.filter(edge=>!(edge.target===connection.target&&edge.targetHandle===targetHandle)).concat(giuLai)
  const nextEdges=addEdge({...connection,
    id:`${connection.source}-${sourceHandle}-${connection.target}-${targetHandle}`},conLai) as CanvasEdge[]
  const thamChieu=[...giuLai.map(edge=>`$${edge.source}.${edge.sourceHandle}`),`$${connection.source}.${sourceHandle}`]
  const nextNodes=nodes.map(node=>node.id===connection.target?{...node,data:{...node.data,params:{...(node.data.params as object??{}),
    [targetHandle]:vao.nhieu?[...new Set(thamChieu)]:`$${connection.source}.${sourceHandle}`}}}:node)
  return {nodes:nextNodes,edges:nextEdges}
}

function nhanNode(node:CanvasNode,nodes:CanvasNode[],bang:BangDinhNghia){
  const ten=(item:CanvasNode)=>item.label?.trim()||dinhNghiaCua(bang,item)?.title||String(item.data.tool)
  const base=ten(node)
  const peers=nodes.filter(item=>ten(item)===base)
  return peers.length>1?`${base} ${peers.findIndex(item=>item.id===node.id)+1}`:base
}

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

function Editor() {
  const [state, dispatch] = useReducer(editorReducer, { document: emptyDocument(), past: [], future: [] })
  const [workflow, setWorkflow] = useState<Workflow>()
  const [nhomPalette, setNhomPalette] = useState<NhomPalette[]>([])
  const [luatNoiDay, setLuatNoiDay] = useState<LuatNoiDay|null>(null)
  const [phase, setPhase] = useState<'loading' | 'ready' | 'saving' | 'saved' | 'conflict' | 'error'>('loading')
  const [offline, setOffline] = useState(!navigator.onLine)
  const [selected, setSelected] = useState<string[]>([])
  const [selectedEdges, setSelectedEdges] = useState<string[]>([])
  const [readOnly, setReadOnly] = useState(window.innerWidth <= 640)
  const [mobilePanel,setMobilePanel]=useState<'canvas'|'palette'|'inspector'>('canvas')
  const [desktopPanel,setDesktopPanel]=useState<'tools'|'workspace'|'run'|'inspector'|null>(null)
  const [paletteQuery,setPaletteQuery]=useState('')
  const [theme,setTheme]=useState<'light'|'dark'>('dark')
  //: Giu nguyen de gui tra `/preferences` — palette v3 khong con khai niem
  //  "cong cu chinh" nen khong co cong tac nao doi no nua.
  const [catalogMode,setCatalogMode]=useState<'simple'|'advanced'>('advanced')
  /** 8 `type` node dung gan day nhat (spec §13.4), luu `localStorage`. */
  const [ganDay,setGanDay]=useState<string[]>(()=>{
    // `localStorage` NEM (khong chi tra rong) trong cua so rieng tu / khi
    // chan cookie ben thu ba — mot canvas den vi mot danh sach goi y.
    try{const tho=localStorage.getItem('ltt.palette.ganDay')
      return tho?JSON.parse(tho) as string[]:[]}catch{return []}
  })
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
  const reactFlow = useReactFlow()
  const updateNodeInternals=useUpdateNodeInternals()
  const page = activePage(state.document)
  const showGrid=page.view?.grid??true
  const showConnections=page.view?.connections??true
  const showMinimap=page.view?.minimap??true
  // ⭐ Khoa la SLUG cong cu (`image.generate`) vi do la thu `data.tool` giu va
  //    `bien_dich._node` doc. `NodeDefinition.type` mang tien to `app.`.
  const dinhNghia = useMemo(() => {
    const m: BangDinhNghia = new Map()
    for (const n of nhomPalette) for (const x of n.nut) m.set(slugCongCu(x), x)
    return m
  }, [nhomPalette])
  const hasAnyNodes=state.document.pages.some(item=>item.nodes.length>0)
  const selectedNode = page.nodes.find(node => node.id === state.selectedId)
  const selectedDinhNghia = dinhNghiaCua(dinhNghia, selectedNode)
  const selectedEdge = page.edges.find(edge=>selectedEdges.includes(edge.id))

  useEffect(()=>{
    if(!dinhNghia.size||!page.nodes.length)return
    const frame=requestAnimationFrame(()=>updateNodeInternals(page.nodes.map(node=>node.id)))
    return()=>cancelAnimationFrame(frame)
  },[updateNodeInternals,dinhNghia,page.nodes,selectedNode?.id])

  useEffect(()=>{
    if(!readOnly||!page.nodes.length)return
    const frame=requestAnimationFrame(()=>reactFlow.fitView({padding:.12,maxZoom:.9,duration:0}))
    return()=>cancelAnimationFrame(frame)
  },[readOnly,page.id,page.nodes.length,reactFlow])

  useEffect(() => {
    let active = true
    Promise.all([taiPalette(), loadOrCreateWorkflowV3(csrf), loadPreferences()])
      .then(([p, loaded, preferences]) => {
        if (!active) return
        setNhomPalette(p.nhom); setLuatNoiDay(p.luat_noi_day)
        setTheme(preferences.theme); setCatalogMode(preferences.catalog_mode)
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
        setCommandOpen(false);setShowLayers(false);setDesktopPanel(null);setContextMenu(null)
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

  const themNode = useCallback((nd: NodeDefinition, position?: { x: number; y: number }) => {
    if (readOnly) return
    const node = nextNode(nd, page.nodes.length)
    if (position) node.position = position
    dispatch({ type: 'graph', nodes: [...page.nodes, node], edges: page.edges })
    dispatch({ type: 'select', id: node.id })
    setGanDay(cu=>{
      const moi=[nd.type,...cu.filter(t=>t!==nd.type)].slice(0,8)
      try{localStorage.setItem('ltt.palette.ganDay',JSON.stringify(moi))}catch{/* rieng tu */}
      return moi
    })
    // Vua them xong ⇒ mo luon tham so cua no. Ngan keo palette dong lai o day
    // dang nao cung dong; de nguoi dung phai tu tim duong toi inspector sau
    // moi lan keo mot node la bat ho lam mot viec vo nghia.
    setDesktopPanel('inspector')
  }, [readOnly, page])

  /** Luat cho `isValidConnection` cua React Flow — duong "co duoc keo khong",
   *  tach khoi `noiDoThi` la duong "noi roi thi do thi moi ra sao". */
  const chapNhanCanh = useCallback((c: { source?: string|null
      sourceHandle?: string|null; target?: string|null
      targetHandle?: string|null }) => {
    if (!luatNoiDay || !c.source || !c.target || !c.sourceHandle || !c.targetHandle) return false
    const ra = dinhNghiaCua(dinhNghia, page.nodes.find(n => n.id === c.source))
      ?.cong_ra.find(x => x.ten === c.sourceHandle)
    const vao = dinhNghiaCua(dinhNghia, page.nodes.find(n => n.id === c.target))
      ?.cong_vao.find(x => x.ten === c.targetHandle)
    if (!ra || !vao) return false
    if (connectionCreatesCycle(page.edges, c.source, c.target)) return false
    const daCo = page.edges.filter(e => e.target === c.target &&
      e.targetHandle === c.targetHandle && e.source !== c.source).length
    return noiDuoc(luatNoiDay, ra.kieu, vao.kieu, vao.nhieu ? daCo : 0, vao.nhieu)
  }, [luatNoiDay, dinhNghia, page.nodes, page.edges])

  const onConnect = useCallback((connection: Connection) => {
    const next=noiDoThi(page.nodes,page.edges,connection,dinhNghia,luatNoiDay);if(next)dispatch({type:'graph',...next})
  }, [dinhNghia, luatNoiDay, page])

  const onReconnectEdge=useCallback((oldEdge:CanvasEdge,connection:Connection)=>{
    if(readOnly)return
    const base=removeEdgeFromGraph(page.nodes,page.edges,oldEdge.id)
    const next=noiDoThi(base.nodes,base.edges,connection,dinhNghia,luatNoiDay);if(next)dispatch({type:'graph',...next})
  },[readOnly,page,dinhNghia,luatNoiDay])

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
  const toggleErrorBranch=()=>{if(!selectedEdge||readOnly)return;const condition=selectedEdge.data?.condition==='error'?'success':'error';dispatch({type:'graph',nodes:page.nodes,edges:page.edges.map(edge=>edge.id===selectedEdge.id?{...edge,data:{...edge.data,condition}}:edge)})}
  // ⛔ `cloneCurrent` / `downloadTemplate` / `importTemplate` da go cung ba nut
  //    cua chung. Hai cai dau goi `/agent/api/workflows/{id}/clone|export` (v2)
  //    voi mot id v3 ⇒ 404. Cai thu ba goi `/agent/api/workflows/import` —
  //    duong nay CON SONG, nhung no tao mot ban ghi `agent_workflows` (v2) roi
  //    dat id v2 ay vao trinh soan; lan tu dong luu ke tiep di qua
  //    `saveWorkflowV3` va 404. Mot loi moi dan toi canvas khong luu duoc thi
  //    hong hon mot loi moi 404 ngay, nen no di cung hai cai kia.
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
    if (event.key === 'Escape') { setCommandOpen(false);setShowLayers(false);setDesktopPanel(null);setContextMenu(null);
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
      const key=event.key.toLowerCase()
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
    const tools = page.nodes.map(node => {
      const nd = dinhNghiaCua(dinhNghia, node) ?? nutThieu(String(node.data.tool))
      const trangThaiRun = run?.nodes.find(item => item.node_id === node.id)?.status
      return { ...node, type: 'ltt',
        // Dau MAY DOC DUOC cho node bi publish tu choi (422 `{ma,node_id}`).
        // React Flow dan `className` len chinh `.react-flow__node`, nen cai
        // dau nay o CUNG cho voi `data-id` — mot phep kiem khong phai doan
        // qua mot chuoi tieng Viet co the doi.
        className: loiNode[node.id] ? 'node-do-loi' : undefined,
        selected: node.id === state.selectedId || selected.includes(node.id),
        data: { ...node.data, dinhNghia: nd,
          trangThai: loiNode[node.id] ? 'Lỗi biên dịch'
            : trangThaiRun ? NHAN_TRANG_THAI_NODE[trangThaiRun] ?? trangThaiRun
            : undefined } }
    })
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
  }, [page, state.selectedId, selected, dinhNghia, loiNode, run])
  const displayEdges = useMemo(() => (showConnections ? page.edges : []).map(edge => {
    const isError = edge.data?.condition === 'error'
    const ndRa = dinhNghiaCua(dinhNghia, page.nodes.find(node => node.id === edge.source))
    const kind=String(ndRa?.cong_ra.find(c=>c.ten===edge.sourceHandle)?.kieu??'data').replace('[]','')
    const trangThai=(id:string)=>run?.nodes.find(item=>item.node_id===id)?.status
    const running=run?.status==='RUNNING'&&trangThai(edge.source)==='SUCCEEDED'&&trangThai(edge.target)!=='SUCCEEDED'
    return { ...edge,type:'creative',
      selected:selectedEdges.includes(edge.id),label:isError?'Lỗi':undefined,
      markerEnd:{type:MarkerType.ArrowClosed,width:16,height:16},animated:isError||running,
      className:`edge-${kind}${isError?' error-branch':''}${running?' is-running':''}`,
      data:{...edge.data,modality:kind,running} }
  }), [page.edges,page.nodes,selectedEdges,showConnections,dinhNghia,run])
  if (phase === 'loading') return <section className="canvas-state" aria-live="polite">Đang tải workflow…</section>
  if (phase === 'error' && !workflow) return <section className="canvas-state error" role="alert">Không tải được Canvas. <button onClick={() => location.reload()}>Thử lại</button></section>
  const runDaXong=Boolean(run&&RUN_V3_KET_THUC.has(run.status))
  const doiGiaoDien=(nextTheme:'light'|'dark')=>{
    setTheme(nextTheme)
    void savePreferences({theme:nextTheme,catalog_mode:catalogMode,
      presentation_version:PHIEN_BAN_TRINH_BAY},csrf).catch(()=>setPhase('error'))
  }
  return <section className={`canvas-shell theme-${theme}`}
    aria-label="LTT Agent Canvas" tabIndex={0} onKeyDown={onKeyDown}>
    <header className="canvas-toolbar"><a className="canvas-home" href="/agent" aria-label="Về Agent AI">LTT</a><div className="workflow-identity"><input aria-label="Tên workflow"
      value={workflow?.name ?? ''} disabled={!workflow || readOnly} onChange={event=>workflow&&setWorkflow({...workflow,name:event.target.value})}
      onBlur={()=>workflow&&saveWorkflowV3({...workflow,canvas:state.document},csrf).then(setWorkflow).catch(()=>setPhase('error'))}/>
      {/* Trinh soan chay runtime v3 tu plan 01b (`saveWorkflowV3` ->
          `publishWorkflowV3` -> `createRunV3`). Nhan "Canvas v2" o day la mot
          nhan SAI — nghiem thu production 23/09 bat duoc. */}
      <span>{readOnly ? 'Mobile · chỉ xem' : `Canvas v3 · ${page.name} · ${page.nodes.length} node · ${page.edges.length} kết nối`}</span></div>
      <div className="canvas-top-actions"><span className={`save-state ${phase}`} aria-live="polite">{offline ? 'Ngoại tuyến' : phase === 'saving' ? 'Đang lưu…' : phase === 'conflict' ? 'Xung đột' : phase === 'error' ? 'Lỗi lưu' : 'Đã lưu'}</span>
        {phase==='conflict'&&<button className="save-recovery" onClick={()=>location.reload()}>Tải bản mới</button>}
        {phase==='error'&&<button className="save-recovery" onClick={()=>setRetryNonce(value=>value+1)}>Thử lưu lại</button>}
        <button title="Đổi giao diện" aria-label={theme==='light'?'Chuyển sang nền tối':'Chuyển sang nền sáng'} onClick={()=>doiGiaoDien(theme==='light'?'dark':'light')}>{theme==='light'?'☾':'☀'}</button>
        <button title="Bảng lệnh" aria-label="Mở bảng lệnh" onClick={()=>setCommandOpen(true)}>⌘</button>
        {/* Nut "AI" (Assistant) va "↗" (Phien ban & chia se) da bo: ca hai ngan
            keo phia sau chung chi goi cua v2, va cua v2 khong biet id v3. */}
        <button className="run-primary" disabled={readOnly||!page.nodes.length} aria-pressed={desktopPanel==='run'} onClick={()=>setDesktopPanel(value=>value==='run'?null:'run')}>Chạy</button></div>
      <nav className={`operation-drawer${desktopPanel==='run'?' is-open':''}`} aria-label="Chạy workflow"><header><strong>Chạy workflow</strong><button aria-label="Đóng bảng chạy" onClick={()=>setDesktopPanel(null)}>×</button></header>
        <div className="run-tools"><button disabled={!selected.length || readOnly} onClick={duplicate}>Nhân bản</button>
          <button disabled={(!selected.length && !selectedEdges.length) || readOnly}
            onClick={() => dispatch(selectedEdges.length ? { type: 'deleteEdges', ids: selectedEdges } : { type: 'delete', ids: selected })}>Xóa</button>
          {selectedEdges.length===1&&<button disabled={readOnly} onClick={toggleErrorBranch}>Nhánh: {selectedEdge?.data?.condition==='error'?'Lỗi':'Thành công'}</button>}
          <button disabled={readOnly} onClick={() => dispatch({ type: 'layout' })}>Tự xếp</button>
          <button aria-pressed={showLayers} onClick={()=>setShowLayers(value=>!value)}>Lớp</button>
          <button aria-pressed={showGrid} onClick={()=>dispatch({type:'pageView',grid:!showGrid})}>Lưới</button>
          <button aria-pressed={showConnections} onClick={()=>dispatch({type:'pageView',connections:!showConnections})}>Đường nối</button>
          <button aria-pressed={showMinimap} onClick={()=>dispatch({type:'pageView',minimap:!showMinimap})}>Bản đồ</button></div>
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
        {runError && <span className="run-error" role="alert">{runError}</span>}</nav></header>
    <nav className="canvas-mobile-tabs" aria-label="Khu vực Canvas">{(['canvas','palette','inspector'] as const).map(item=><button key={item} className={mobilePanel===item?'active':''} aria-pressed={mobilePanel===item} onClick={()=>setMobilePanel(item)}>{item==='canvas'?'Canvas':item==='palette'?'Công cụ':'Chi tiết'}</button>)}</nav>
    <div className={`canvas-body panel-${mobilePanel}`}>
      <nav className="canvas-rail" aria-label="Công cụ Canvas">
        <button title="Chọn" aria-label="Công cụ chọn" aria-pressed={!desktopPanel}>↖</button>
        <button title="Thêm node" aria-label="Mở công cụ" aria-pressed={desktopPanel==='tools'} onClick={()=>{const open=desktopPanel!=='tools';setDesktopPanel(open?'tools':null);if(open){setSelected([]);setSelectedEdges([]);dispatch({type:'select'})}}}>＋</button>
        <button title="Mẫu & thiết lập" aria-label="Mở mẫu và thiết lập" aria-pressed={desktopPanel==='workspace'} onClick={()=>setDesktopPanel(value=>value==='workspace'?null:'workspace')}>▦</button>
        {/* 🔴 Nut nay la DUONG VAO DUY NHAT cua inspector tren desktop:
            `.canvas-mobile-tabs` (nut "Chi tiết") la `display:none` tren man
            rong. Truoc task 15, tham so con o `ContextComposer` noi len canh
            node nen thieu no khong ai thay; gio MOI tham so o inspector. */}
        <button title="Chi tiết node" aria-label="Mở chi tiết node" aria-pressed={desktopPanel==='inspector'} onClick={()=>setDesktopPanel(value=>value==='inspector'?null:'inspector')}>☰</button>
        {hasAnyNodes&&<><button title="Lớp" aria-label="Mở danh sách lớp" aria-pressed={showLayers} onClick={()=>setShowLayers(value=>!value)}>☷</button>
          <button title="Sticky note" aria-label="Tạo sticky note" disabled={readOnly} onClick={()=>dispatch({type:'noteAdd',text:'Ghi chú mới'})}>□</button>
          <button title="Bình luận" aria-label="Tạo comment" disabled={readOnly} onClick={()=>dispatch({type:'commentAdd',text:'Bình luận mới'})}>◌</button></>}
        <span />
        <button title="Hoàn tác" aria-label="Hoàn tác" disabled={!state.past.length||readOnly} onClick={()=>dispatch({type:'undo'})}>↶</button>
        <button title="Làm lại" aria-label="Làm lại" disabled={!state.future.length||readOnly} onClick={()=>dispatch({type:'redo'})}>↷</button>
      </nav>
      <aside className={`canvas-palette${desktopPanel==='tools'||desktopPanel==='workspace'?' is-open':''}${desktopPanel==='workspace'?' workspace-only':' tools-only'}`} aria-label="Palette công cụ"><header className="drawer-heading"><h2>{desktopPanel==='workspace'?'Mẫu & thiết lập':'Thêm block'}</h2><button aria-label="Đóng Palette" onClick={()=>setDesktopPanel(null)}>×</button></header>
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
        </section>
        <div className="workflow-settings"><label>Mục tiêu workflow<textarea disabled={readOnly}
          value={state.document.goal} onChange={event => dispatch({ type: 'document', goal: event.target.value })} /></label>
          {/* O "Ngan sach toi da" da GO (review I4): khong mot tep
              `platform_core/workflow/*` nao doc `budget_max_credit` o v3 — dong
              co chot tran bang `version.estimated_max` luc publish. Giu lai o
              nhap ay la hua voi nguoi dung mot tran chi tieu ma khong ai thi
              hanh: noi doi ve TIEN. Tran that hien o bang luot chay
              (`credit_charged/credit_max`, RunV3Panel). Khoa `budget_max_credit`
              van con trong `document` vi `di_tru_m1.py` mang no sang tu ban
              nhap cu — go o nhap khong duoc lam mat du lieu ay. */}</div>
        <PaletteV2 nhom={nhomPalette} truyVan={paletteQuery} onTruyVan={setPaletteQuery}
          onChon={nd=>themNode(nd)} ganDay={ganDay} /></aside>
      <section className="canvas-stage" data-testid="canvas-stage" data-edge-count={page.edges.length} data-display-edge-count={displayEdges.length} onDragOver={event => event.preventDefault()}
        onContextMenu={event=>{if((event.target as HTMLElement).closest('.react-flow__node,.canvas-context-menu'))return
          event.preventDefault();const screen={x:event.clientX,y:event.clientY}
          setContextMenu({kind:'pane',x:screen.x,y:screen.y,flow:reactFlow.screenToFlowPosition(screen)})}}
        onDrop={event => { const nd = timNut(nhomPalette, event.dataTransfer.getData(MIME_NODE))
          if (nd) themNode(nd, reactFlow.screenToFlowPosition({ x: event.clientX, y: event.clientY })) }}>
        <ReactFlow key={page.id} nodes={displayNodes as CanvasNode[]} edges={displayEdges} nodeTypes={nodeTypes} edgeTypes={edgeTypes} ariaLabelConfig={NHAN_TRO_NANG_VI}
          onNodesChange={(changes: NodeChange[]) => { const persisted = changes.filter(change => ['position', 'add', 'remove', 'replace'].includes(change.type));
            if (persisted.length) dispatch({ type: persisted.every(change => change.type === 'position') ? 'sync' : 'graph', nodes: applyNodeChanges(persisted, page.nodes) as CanvasNode[], edges: page.edges }) }}
          onEdgesChange={(changes: EdgeChange[]) => { const persisted = changes.filter(change => ['add', 'remove', 'replace'].includes(change.type));
            if (persisted.length) dispatch({ type: 'graph', nodes: page.nodes, edges: applyEdgeChanges(persisted, page.edges) as CanvasEdge[] }) }}
          onConnect={onConnect} isValidConnection={chapNhanCanh} onReconnect={onReconnectEdge} edgesReconnectable={!readOnly}
          onNodeClick={(event, node) => {const additive=event.ctrlKey||event.metaKey||event.shiftKey
            // Bam vao node ⇒ mo inspector. Do la cu chi tu nhien nhat, va sau
            // task 15 khong con bang nao noi len canh node de sua tham so.
            setContextMenu(null);setSelectedEdges([]);setDesktopPanel('inspector')
            setSelected(previous=>additive?(previous.includes(node.id)?previous.filter(id=>id!==node.id):[...previous,node.id]):[node.id])
            dispatch({ type: 'select', id: node.id }) }}
          onNodeContextMenu={(event,node)=>{event.preventDefault();setSelected([node.id]);dispatch({type:'select',id:node.id});
            setContextMenu({kind:'node',nodeId:node.id,x:event.clientX,y:event.clientY,flow:node.position})}}
          onPaneContextMenu={event=>{event.preventDefault();const screen={x:event.clientX,y:event.clientY};
            setContextMenu({kind:'pane',x:screen.x,y:screen.y,flow:reactFlow.screenToFlowPosition(screen)})}}
          onEdgeClick={(_event, edge) => { setSelected([]); setSelectedEdges([edge.id]); dispatch({ type: 'select' }) }}
          onNodeDragStart={() => { dragBefore.current = structuredClone(state.document) }}
          onNodeDragStop={() => { if (dragBefore.current) dispatch({ type: 'commit', before: dragBefore.current }); dragBefore.current = undefined }}
          onPaneClick={() => { setContextMenu(null);setSelected([]); setSelectedEdges([]); dispatch({ type: 'select' }) }} onSelectionChange={onSelectionChange}
          onMoveEnd={(_event, viewport) => dispatch({ type: 'viewport', viewport })}
          nodesDraggable={!readOnly} nodesConnectable={!readOnly} elementsSelectable
          multiSelectionKeyCode={['Control','Meta']} selectionOnDrag panOnDrag={[1,2]}
          defaultViewport={page.viewport} minZoom={0.1} maxZoom={2}
          fitView={!page.nodes.length} deleteKeyCode={null}>
          <FlowStatus />
          {showGrid&&<Background color={theme==='light'?'#d8dde5':'#242a31'} gap={20} />}{showMinimap&&<MiniMap pannable zoomable />}<Controls orientation="horizontal" showInteractive={!readOnly} />
        </ReactFlow>
        {!page.nodes.length && <section className="canvas-empty first-run" aria-label="Bắt đầu workflow"><small>BẮT ĐẦU</small><h2>Kéo một node từ bảng node</h2>
          <p>Mỗi node là một bước. Nối cổng ra của bước trước vào cổng vào của bước sau, rồi bấm Chạy.</p>
          <button className="blank-flow" onClick={()=>setDesktopPanel('tools')}>Mở bảng node</button></section>}
        {!!Object.keys(loiNode).length && <div className="validation-banner" role="alert"><strong>Workflow chưa biên dịch được</strong>
          <span>{runError||Object.values(loiNode).join(' · ')}</span></div>}
        {showLayers&&<aside className="layers-drawer" aria-label="Danh sách lớp"><header><strong>Lớp · {page.name}</strong>
          <button aria-label="Đóng danh sách lớp" onClick={()=>setShowLayers(false)}>×</button></header>
          <ul>{page.frames.map(frame=><li key={frame.id}><span>FRAME</span>{frame.name}</li>)}
            {page.nodes.map(node=><li key={node.id}><button onClick={()=>dispatch({type:'select',id:node.id})}><span>KHỐI</span>{nhanNode(node,page.nodes,dinhNghia)}</button></li>)}
            {page.notes.map(note=><li key={note.id}><span>NOTE</span>{note.text}</li>)}
            {page.comments.map(comment=><li key={comment.id}><span>COMMENT</span>{comment.text}</li>)}</ul></aside>}
      </section>
      <nav className="page-dock" aria-label="Chuyển page">{state.document.pages.map((item,index)=><button
        key={item.id} aria-pressed={item.id===page.id} onClick={()=>dispatch({type:'pageSelect',id:item.id})}>{item.name||`Page ${index+1}`}</button>)}</nav>
      {contextMenu&&<aside className={`canvas-context-menu ${contextMenu.kind}`} aria-label={contextMenu.kind==='pane'?'Menu khoảng trống Canvas':'Menu thao tác node'}
        style={{left:Math.min(contextMenu.x,window.innerWidth-310),top:Math.min(contextMenu.y,window.innerHeight-520)}}>
        <header><strong>{contextMenu.kind==='pane'?'Thêm vào Canvas':'Thao tác node'}</strong><button aria-label="Đóng menu ngữ cảnh" onClick={()=>setContextMenu(null)}>×</button></header>
        {contextMenu.kind==='pane'?<><button onClick={()=>{setDesktopPanel('tools');setContextMenu(null)}}>Mở bảng node</button>
          <hr/><button onClick={()=>{dispatch({type:'pageView',connections:!showConnections});setContextMenu(null)}}>{showConnections?'Ẩn đường nối':'Hiện đường nối'}</button>
          <button onClick={()=>{dispatch({type:'layout'});setContextMenu(null)}}>Tự động sắp xếp node</button></>:
          <>{contextMenu.nodeId&&<><button disabled={readOnly} onClick={()=>{duplicateNode(contextMenu.nodeId!);setContextMenu(null)}}>Sao chép node</button>
            {state.document.pages.filter(item=>item.id!==page.id).map(item=><button key={item.id} disabled={readOnly}
              onClick={()=>{dispatch({type:'nodeMovePage',id:contextMenu.nodeId!,pageId:item.id});setContextMenu(null)}}>Chuyển sang {item.name}</button>)}
            <button className="danger" disabled={readOnly} onClick={()=>{dispatch({type:'delete',ids:[contextMenu.nodeId!]});setSelected([]);setContextMenu(null)}}>Xóa node</button></>}</>}
      </aside>}
      {(desktopPanel==='inspector'||mobilePanel==='inspector')&&
        <aside className={`canvas-inspector${desktopPanel==='inspector'?' is-open':''}`} aria-label="Chi tiết node">
          {selectedNode&&selectedDinhNghia
            ? <><small>THAM SỐ</small><h2>{selectedDinhNghia.title}</h2>
                <p className="inspector-type">{selectedDinhNghia.type}@{selectedDinhNghia.type_version}</p>
                {selectedDinhNghia['x-ltt-loi']&&<p className="inspector-loi" role="status">
                  Một phần lựa chọn của node này chưa tải được — các ô ấy bị khóa.</p>}
                <input aria-label="Tên hiển thị của node" disabled={readOnly}
                  value={selectedNode.label??''} placeholder={selectedDinhNghia.title}
                  onChange={event=>dispatch({type:'nodeLabel',id:selectedNode.id,label:event.target.value})}/>
                <FormTuLuocDo luocDo={selectedDinhNghia.tham_so}
                  giaTri={(selectedNode.data.params ?? {}) as Record<string, unknown>}
                  readOnly={readOnly}
                  onChange={(ten, v) => dispatch({type:'update',id:selectedNode.id,data:{ params: {
                    ...(selectedNode.data.params as Record<string, unknown>), [ten]: v } }})} />
                <footer className="inspector-gia">{liveQuotes[selectedNode.id]===undefined
                  ? 'Chi phí do server xác nhận'
                  : `Tối đa ${liveQuotes[selectedNode.id]} credit`}</footer>
              </>
            : <p>Chọn một node để xem tham số.</p>}
        </aside>}
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
