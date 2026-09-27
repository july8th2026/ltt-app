import { useCallback, useState } from 'react'
import { ReactFlowProvider, useReactFlow } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import '../../canvas.css'
import { activePage } from '../../editorState'
import type { CanvasDocument } from '../../workflowApi'
import { CommandPalette } from './CommandPalette'
import { ContextMenu } from './ContextMenu'
import { ExecutionPanel } from './ExecutionPanel'
import { LayersDrawer } from './LayersDrawer'
import { LeftRail } from './LeftRail'
import { MobileTabs } from './MobileTabs'
import { PageDock } from './PageDock'
import { StepInspector } from './StepInspector'
import { StepLibrary } from './StepLibrary'
import { WorkflowCanvas } from './WorkflowCanvas'
import { WorkflowHeader } from './WorkflowHeader'
import { dinhNghiaCua } from './graph'
import type { KhuMobile, MenuNguCanh, NganDesktop } from './kieu'
import { useBrowserEnv } from './hooks/useBrowserEnv'
import { useCanvasFrames } from './hooks/useCanvasFrames'
import { useCanvasSelection } from './hooks/useCanvasSelection'
import { useDisplayGraph } from './hooks/useDisplayGraph'
import { useEditorShortcuts } from './hooks/useEditorShortcuts'
import { useExpressionSuggest } from './hooks/useExpressionSuggest'
import { useGraphEdits } from './hooks/useGraphEdits'
import { useLiveQuote } from './hooks/useLiveQuote'
import { useStepLibrary } from './hooks/useStepLibrary'
import { useWorkflowDocument } from './hooks/useWorkflowDocument'
import { useWorkflowRun } from './hooks/useWorkflowRun'

/** Bố cục trình soạn + phím tắt toàn cục. Mọi trạng thái sống trong `hooks/`.
 *
 *  ⭐ VÌ SAO TỆP NÀY MỎNG LÀ MỤC TIÊU, KHÔNG PHẢI THẨM MỸ
 *
 *     Trước lần tách này toàn bộ giao diện nằm trong MỘT hàm 740 dòng ⇒ một
 *     chủ sở hữu ⇒ các làn khác không chạy song song được. Mỗi lần thêm một
 *     `useState` vào đây là lấy lại một phần cái giá đó, nên ⛔ trạng thái mới
 *     đi vào một hook, không vào đây.
 */
function Editor() {
  const [mobilePanel, setMobilePanel] = useState<KhuMobile>('canvas')
  const [desktopPanel, setDesktopPanel] = useState<NganDesktop>(null)
  const [contextMenu, setContextMenu] = useState<MenuNguCanh | null>(null)
  const [showLayers, setShowLayers] = useState(false)
  const [commandOpen, setCommandOpen] = useState(false)
  //: ⚠️ Truy vấn bảng lệnh ở ĐÂY, không trong `CommandPalette` — bản gốc chỉ
  //  xoá nó sau khi CHẠY một lệnh, nên `Esc` giữ lại chữ đã gõ. Xem chú thích
  //  trong `CommandPalette.tsx`.
  const [commandQuery, setCommandQuery] = useState('')

  const csrf = document.querySelector<HTMLElement>('#agent-canvas-root')?.dataset.csrfToken ?? ''
  const { offline, readOnly } = useBrowserEnv()
  const doc = useWorkflowDocument(csrf, offline)
  const { state, dispatch, workflow, phase, theme, dinhNghia } = doc
  const page = activePage(state.document)
  const showGrid = page.view?.grid ?? true
  const showConnections = page.view?.connections ?? true
  const showMinimap = page.view?.minimap ?? true

  const dispatchSelect = useCallback((id?: string) => dispatch({ type: 'select', id }), [dispatch])
  const sel = useCanvasSelection(dispatchSelect)
  const selectedNode = page.nodes.find(node => node.id === state.selectedId)
  const selectedDinhNghia = dinhNghiaCua(dinhNghia, selectedNode)
  const selectedEdge = page.edges.find(edge => sel.selectedEdges.includes(edge.id))
  const moNgan = useCallback((ngan: NganDesktop) => setDesktopPanel(ngan), [])
  const batNgan = useCallback((ngan: Exclude<NganDesktop, null>) =>
    setDesktopPanel(value => value === ngan ? null : ngan), [])
  const batLayers = useCallback(() => setShowLayers(value => !value), [])

  useCanvasFrames(page, dinhNghia, readOnly, selectedNode?.id)
  const reactFlow = useReactFlow()
  const kho = useStepLibrary()
  const run = useWorkflowRun({ workflow, setWorkflow: doc.setWorkflow,
    document: state.document, csrf, readOnly, setPhase: doc.setPhase, moNgan,
    autosaveTimer: doc.autosaveTimer,
    // ⭐ `giuLichSu` — "Soạn bằng AI" GHI ĐÈ đồ thị đang dựng, nên trạng thái cũ
    //    phải vào `past`. Không có nó thì Ctrl+Z không cứu được và họ mất việc.
    napTaiLieu: (document: CanvasDocument) =>
      dispatch({ type: 'replace', document, giuLichSu: true }) })
  const liveQuotes = useLiveQuote(workflow, state.document, page.nodes.length, csrf, offline)
  const goiY = useExpressionSuggest(workflow, selectedNode?.id, state.document, csrf, offline)
  const edits = useGraphEdits({ page, document: state.document, dinhNghia,
    luatNoiDay: doc.luatNoiDay, readOnly, selected: sel.selected, selectedEdge,
    setSelected: sel.setSelected, setSelectedEdges: sel.setSelectedEdges,
    ghiNhanDaDung: kho.ghiNhanDaDung, moNgan, dispatch })
  const { displayNodes, displayEdges } = useDisplayGraph({ page,
    selectedId: state.selectedId, selected: sel.selected,
    selectedEdges: sel.selectedEdges, dinhNghia, loiNode: run.loiNode,
    run: run.run, showConnections })

  const dongHet = useCallback(() => {
    setCommandOpen(false); setShowLayers(false); setDesktopPanel(null); setContextMenu(null)
    sel.boChon()
  }, [sel])
  const onKeyDown = useEditorShortcuts({ page, readOnly, selected: sel.selected,
    selectedEdges: sel.selectedEdges, setSelected: sel.setSelected,
    setSelectedEdges: sel.setSelectedEdges, moBangLenh: () => setCommandOpen(true),
    dongHet, moNgan, duplicate: edits.duplicate, copy: edits.copy,
    paste: edits.paste, dispatch })

  if (phase === 'loading') return <section className="canvas-state" aria-live="polite">Đang tải workflow…</section>
  if (phase === 'error' && !workflow) return <section className="canvas-state error" role="alert">Không tải được Canvas. <button onClick={() => location.reload()}>Thử lại</button></section>

  return <section className={`canvas-shell theme-${theme}`}
    aria-label="LTT Agent Canvas" tabIndex={0} onKeyDown={onKeyDown}>
    <WorkflowHeader workflow={workflow} setWorkflow={doc.setWorkflow} luuTen={doc.luuTen}
      page={page} readOnly={readOnly} offline={offline} phase={phase} theme={theme}
      doiGiaoDien={doc.doiGiaoDien} thuLuuLai={doc.thuLuuLai} desktopPanel={desktopPanel}
      moNgan={moNgan} moBangLenh={() => setCommandOpen(true)}>
      <ExecutionPanel dangMo={desktopPanel==='run'} moNgan={moNgan} page={page}
        workflow={workflow} phase={phase} readOnly={readOnly} run={run.run}
        runError={run.runError} runGoc={run.runGoc} runDaXong={run.runDaXong}
        dangGui={run.dangGui} soSanh={run.soSanh} soSanhLoi={run.soSanhLoi}
        chayWorkflow={() => void run.chayWorkflow()} huyRun={run.huyRun}
        chayLaiTuNode={run.chayLaiTuNode} soSanhVoiGoc={run.soSanhVoiGoc}
        taoBanChayMoi={run.taoBanChayMoi} selected={sel.selected}
        selectedEdges={sel.selectedEdges} selectedEdge={selectedEdge}
        showGrid={showGrid} showConnections={showConnections} showMinimap={showMinimap}
        showLayers={showLayers} batLayers={batLayers} duplicate={edits.duplicate}
        toggleErrorBranch={edits.toggleErrorBranch} dispatch={dispatch}/>
    </WorkflowHeader>
    <MobileTabs khu={mobilePanel} datKhu={setMobilePanel}/>
    <div className={`canvas-body panel-${mobilePanel}`}>
      <LeftRail desktopPanel={desktopPanel} moNgan={moNgan} batNgan={batNgan}
        hasAnyNodes={state.document.pages.some(item=>item.nodes.length>0)}
        showLayers={showLayers} batLayers={batLayers} readOnly={readOnly}
        coQuaKhu={!!state.past.length} coTuongLai={!!state.future.length}
        boChon={sel.boChon} dispatch={dispatch}/>
      <StepLibrary desktopPanel={desktopPanel} moNgan={moNgan} document={state.document}
        page={page} selected={sel.selected} readOnly={readOnly} workflow={workflow}
        nhomPalette={doc.nhomPalette} paletteQuery={kho.paletteQuery}
        setPaletteQuery={kho.setPaletteQuery} ganDay={kho.ganDay}
        themNode={edits.themNode} dangSoan={run.dangSoan} soanLoi={run.soanLoi}
        soanBangAI={run.soanBangAI} xoaLuaChon={sel.xoaLuaChon} dispatch={dispatch}/>
      <WorkflowCanvas page={page} document={state.document} displayNodes={displayNodes}
        displayEdges={displayEdges} readOnly={readOnly} theme={theme} showGrid={showGrid}
        showMinimap={showMinimap} nhomPalette={doc.nhomPalette} reactFlow={reactFlow}
        themNode={edits.themNode} onConnect={edits.onConnect}
        chapNhanCanh={edits.chapNhanCanh} onReconnectEdge={edits.onReconnectEdge}
        onSelectionChange={sel.onSelectionChange} datMenu={setContextMenu}
        chonNode={(event, nodeId) => {
          const additive=event.ctrlKey||event.metaKey||event.shiftKey
          // Bam vao node ⇒ mo inspector. Do la cu chi tu nhien nhat, va sau
          // task 15 khong con bang nao noi len canh node de sua tham so.
          setContextMenu(null);sel.setSelectedEdges([]);setDesktopPanel('inspector')
          sel.setSelected(additive?(sel.selected.includes(nodeId)?sel.selected.filter(id=>id!==nodeId):[...sel.selected,nodeId]):[nodeId])
          dispatch({ type: 'select', id: nodeId })
        }}
        chonNodeChoMenu={nodeId => { sel.setSelected([nodeId]); dispatch({ type: 'select', id: nodeId }) }}
        chonCanh={edgeId => { sel.setSelected([]); sel.setSelectedEdges([edgeId]); dispatchSelect() }}
        boChon={sel.boChon} batDauKeo={edits.batDauKeo} ketThucKeo={edits.ketThucKeo}
        moNgan={moNgan} dispatch={dispatch}>
        {!!Object.keys(run.loiNode).length && <div className="validation-banner" role="alert"><strong>Workflow chưa biên dịch được</strong>
          <span>{run.runError||Object.values(run.loiNode).join(' · ')}</span></div>}
        {showLayers&&<LayersDrawer page={page} dinhNghia={dinhNghia}
          dong={() => setShowLayers(false)} dispatch={dispatch}/>}
      </WorkflowCanvas>
      <PageDock document={state.document} activeId={page.id} dispatch={dispatch}/>
      {contextMenu&&<ContextMenu menu={contextMenu} dong={() => setContextMenu(null)}
        document={state.document} page={page} readOnly={readOnly}
        showConnections={showConnections} moNgan={moNgan}
        duplicateNode={edits.duplicateNode}
        xoaNode={nodeId => { dispatch({type:'delete',ids:[nodeId]}); sel.setSelected([]) }}
        dispatch={dispatch}/>}
      {/* 🔴 Tren MOBILE, inspector chi theo TAB MOBILE — ⛔ khong theo
          `desktopPanel`. Bam mot node dat `desktopPanel='inspector'`, va dieu
          kien cu (`desktopPanel==='inspector' || mobilePanel==='inspector'`)
          lam inspector dinh cung tren man hinh: doi sang tab "Cong cu" hay
          quay ve "Canvas" no VAN hien, de len khung ve.

          Do tren trinh duyet that 27/09 (390x844), sau khi bam mot node:
              tab "Chi tiet"  -> inspector hien   ✅
              tab "Cong cu"   -> inspector VAN hien  ❌
              tab "Canvas"    -> inspector VAN hien  ❌

          Day la LOI KE THUA tu `CanvasShell` cu, khong phai do lan UI-3 gay ra
          — ho giu nguyen dieu kien goc dung nhu yeu cau (thuan di chuyen). No
          chi lo ra khi co nguoi doi tab, va truoc do khong phep kiem nao lam
          viec ay. `tests/browser/agent_ui_v2_ui3_mobile.js` nay giu cho nay. */}
      {(readOnly ? mobilePanel==='inspector'
                 : desktopPanel==='inspector')&&
        <StepInspector dangMo={desktopPanel==='inspector'} selectedNode={selectedNode}
          dinhNghia={selectedDinhNghia} readOnly={readOnly} goiY={goiY}
          liveQuotes={liveQuotes} dispatch={dispatch}/>}
    </div>
    {commandOpen&&<CommandPalette truyVan={commandQuery} datTruyVan={setCommandQuery}
      dong={() => setCommandOpen(false)}
      dongVaXoa={() => { setCommandOpen(false); setCommandQuery('') }}
      showGrid={showGrid} showConnections={showConnections} showMinimap={showMinimap}
      dispatch={dispatch}/>}
  </section>
}

export function CanvasShell() { return <ReactFlowProvider><Editor /></ReactFlowProvider> }
