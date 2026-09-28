import { applyEdgeChanges, applyNodeChanges, Background, Controls, MiniMap, ReactFlow,
  useStore, type Connection, type EdgeChange, type NodeChange,
  type ReactFlowInstance } from '@xyflow/react'
import { NODE_TYPES } from '../../nodes/NodeRenderer'
import { AnnotationNode, FrameNode } from '../../nodes/TrangTri'
import { CanvasEdgeView } from '../../CanvasEdgeView'
import { MIME_NODE } from '../../palette/PaletteV2'
import { timNut } from '../../nodeDefinition'
import type { NhomPalette, NodeDefinition } from '../../nodeDefinition'
import type { EditorAction } from '../../editorState'
import type { CanvasDocument, CanvasEdge, CanvasNode, CanvasPage } from '../../workflowApi'
import { NHAN_TRO_NANG_VI } from './a11y'
import type { GiaoDien, MenuNguCanh } from './kieu'

// ⚠️ `NODE_TYPES` (`{ ltt: NodeRenderer }`) ve MOI node cua do thi — do la ca
//    y do cua spec §13.2. `frame`/`annotation` khong phai node do thi: chung
//    la trang tri, khong cong, khong tham so, `bien_dich.py` khong thay. React
//    Flow ve moi thu bang MOT bang nen chung phai nam day; go chung ra thi
//    frame/sticky note roi ve node mac dinh va man hinh hong im lang.
const nodeTypes = { ...NODE_TYPES, frame: FrameNode, annotation: AnnotationNode }
const edgeTypes = { creative: CanvasEdgeView }

type Props = {
  page: CanvasPage
  document: CanvasDocument
  displayNodes: unknown[]
  displayEdges: unknown[]
  readOnly: boolean
  theme: GiaoDien
  showGrid: boolean
  showMinimap: boolean
  nhomPalette: NhomPalette[]
  reactFlow: ReactFlowInstance
  themNode: (nd: NodeDefinition, position?: { x: number; y: number }) => void
  onConnect: (connection: Connection) => void
  /** ⚠️ Hình dạng LỎNG, cố ý: `isValidConnection` của React Flow gọi hàm này
   *  với `CanvasEdge | Connection`, và `CanvasEdge.sourceHandle` có thể là
   *  `undefined` trong khi `Connection.sourceHandle` thì không. */
  chapNhanCanh: (c: { source?: string|null; sourceHandle?: string|null
    target?: string|null; targetHandle?: string|null }) => boolean
  onReconnectEdge: (oldEdge: CanvasEdge, connection: Connection) => void
  onSelectionChange: (s: { nodes: { id: string }[]; edges: { id: string }[] }) => void
  datMenu: (menu: MenuNguCanh | null) => void
  chonNode: (event: { ctrlKey: boolean; metaKey: boolean; shiftKey: boolean }, nodeId: string) => void
  /** Phải chuột trên node: chọn ĐÚNG node ấy. ⛔ KHÔNG mở inspector — bản gốc
   *  chỉ `setSelected([id])` + `select`, và một menu ngữ cảnh làm ngăn phải bật
   *  ra là một cú giật màn hình người dùng không yêu cầu. */
  chonNodeChoMenu: (nodeId: string) => void
  chonCanh: (edgeId: string) => void
  boChon: () => void
  batDauKeo: () => void
  ketThucKeo: () => void
  moNgan: (ngan: 'tools') => void
  dispatch: (action: EditorAction) => void
  children?: React.ReactNode
}

/** Khung vẽ: `ReactFlow` + bảng `nodeTypes`/`edgeTypes` + mọi cử chỉ trên khung.
 *
 *  ⚠️ `key={page.id}` là CỐ Ý: đổi page phải dựng lại renderer, không thì
 *     viewport và node internals của page cũ theo sang page mới.
 */
export function WorkflowCanvas(p: Props) {
  return <section className="canvas-stage" data-testid="canvas-stage" data-edge-count={p.page.edges.length} data-display-edge-count={p.displayEdges.length} onDragOver={event => event.preventDefault()}
    onContextMenu={event=>{if((event.target as HTMLElement).closest('.react-flow__node,.canvas-context-menu'))return
      event.preventDefault();const screen={x:event.clientX,y:event.clientY}
      p.datMenu({kind:'pane',x:screen.x,y:screen.y,flow:p.reactFlow.screenToFlowPosition(screen)})}}
    onDrop={event => { const nd = timNut(p.nhomPalette, event.dataTransfer.getData(MIME_NODE))
      if (nd) p.themNode(nd, p.reactFlow.screenToFlowPosition({ x: event.clientX, y: event.clientY })) }}>
    <ReactFlow key={p.page.id} nodes={p.displayNodes as CanvasNode[]} edges={p.displayEdges as CanvasEdge[]} nodeTypes={nodeTypes} edgeTypes={edgeTypes} ariaLabelConfig={NHAN_TRO_NANG_VI}
      onNodesChange={(changes: NodeChange[]) => { const persisted = changes.filter(change => ['position', 'add', 'remove', 'replace'].includes(change.type));
        if (persisted.length) p.dispatch({ type: persisted.every(change => change.type === 'position') ? 'sync' : 'graph', nodes: applyNodeChanges(persisted, p.page.nodes) as CanvasNode[], edges: p.page.edges }) }}
      onEdgesChange={(changes: EdgeChange[]) => { const persisted = changes.filter(change => ['add', 'remove', 'replace'].includes(change.type));
        if (persisted.length) p.dispatch({ type: 'graph', nodes: p.page.nodes, edges: applyEdgeChanges(persisted, p.page.edges) as CanvasEdge[] }) }}
      onConnect={p.onConnect} isValidConnection={p.chapNhanCanh} onReconnect={p.onReconnectEdge} edgesReconnectable={!p.readOnly}
      onNodeClick={(event, node) => p.chonNode(event, node.id)}
      onNodeContextMenu={(event,node)=>{event.preventDefault();p.chonNodeChoMenu(node.id);
        p.datMenu({kind:'node',nodeId:node.id,x:event.clientX,y:event.clientY,flow:node.position})}}
      onPaneContextMenu={event=>{event.preventDefault();const screen={x:event.clientX,y:event.clientY};
        p.datMenu({kind:'pane',x:screen.x,y:screen.y,flow:p.reactFlow.screenToFlowPosition(screen)})}}
      onEdgeClick={(_event, edge) => p.chonCanh(edge.id)}
      onNodeDragStart={p.batDauKeo}
      onNodeDragStop={p.ketThucKeo}
      onPaneClick={() => { p.datMenu(null); p.boChon() }} onSelectionChange={p.onSelectionChange}
      onMoveEnd={(_event, viewport) => p.dispatch({ type: 'viewport', viewport })}
      nodesDraggable={!p.readOnly} nodesConnectable={!p.readOnly} elementsSelectable
      multiSelectionKeyCode={['Control','Meta']} selectionOnDrag panOnDrag={[1,2]}
      defaultViewport={p.page.viewport} minZoom={0.1} maxZoom={2}
      fitView={!p.page.nodes.length} deleteKeyCode={null}>
      <FlowStatus />
      {p.showGrid&&<Background color={p.theme==='light'?'#d8dde5':'#242a31'} gap={20} />}{p.showMinimap&&<MiniMap pannable zoomable />}<Controls orientation="horizontal" showInteractive={!p.readOnly} />
    </ReactFlow>
    {!p.page.nodes.length && <section className="canvas-empty first-run" aria-label="Bắt đầu workflow"><small>BẮT ĐẦU</small><h2>Kéo một node từ bảng node</h2>
      <p>Mỗi node là một bước. Nối cổng ra của bước trước vào cổng vào của bước sau, rồi bấm Chạy.</p>
      <button className="blank-flow" onClick={()=>p.moNgan('tools')}>Mở bảng node</button></section>}
    {p.children}
  </section>
}

function FlowStatus(){
  const edges=useStore(state=>state.edges.length)
  const nodes=useStore(state=>state.nodes.length)
  return <span className="sr-only" data-testid="flow-store-status">{nodes} node · {edges} kết nối trong renderer</span>
}
