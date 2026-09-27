import { useCallback, useRef } from 'react'
import type { Connection } from '@xyflow/react'
import { cloneGraphSelection, connectionCreatesCycle, nextNode,
  type EditorAction } from '../../../editorState'
import { noiDuoc, type LuatNoiDay, type NodeDefinition } from '../../../nodeDefinition'
import type { CanvasDocument, CanvasEdge, CanvasPage } from '../../../workflowApi'
import { dinhNghiaCua, noiDoThi, removeEdgeFromGraph, type BangDinhNghia } from '../graph'

type ThamSo = {
  page: CanvasPage
  document: CanvasDocument
  dinhNghia: BangDinhNghia
  luatNoiDay: LuatNoiDay | null
  readOnly: boolean
  selected: string[]
  selectedEdge: CanvasEdge | undefined
  setSelected: (ids: string[]) => void
  setSelectedEdges: (ids: string[]) => void
  ghiNhanDaDung: (nd: NodeDefinition) => void
  moNgan: (ngan: 'inspector') => void
  dispatch: (action: EditorAction) => void
}

/** Mọi thao tác SỬA đồ thị: thêm · nối · nối lại · nhân bản · dán · nhánh lỗi. */
export function useGraphEdits(ts: ThamSo) {
  const { page, dinhNghia, luatNoiDay, readOnly, dispatch } = ts
  const copied = useRef<{ nodes: CanvasPage['nodes']; edges: CanvasEdge[] }>({ nodes: [], edges: [] })
  const dragBefore = useRef<CanvasDocument | undefined>(undefined)

  const themNode = useCallback((nd: NodeDefinition, position?: { x: number; y: number }) => {
    if (readOnly) return
    const node = nextNode(nd, page.nodes.length)
    if (position) node.position = position
    dispatch({ type: 'graph', nodes: [...page.nodes, node], edges: page.edges })
    dispatch({ type: 'select', id: node.id })
    ts.ghiNhanDaDung(nd)
    // Vua them xong ⇒ mo luon tham so cua no. Ngan keo palette dong lai o day
    // dang nao cung dong; de nguoi dung phai tu tim duong toi inspector sau
    // moi lan keo mot node la bat ho lam mot viec vo nghia.
    ts.moNgan('inspector')
  }, [readOnly, page, dispatch, ts])

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
  }, [dinhNghia, luatNoiDay, page, dispatch])

  const onReconnectEdge = useCallback((oldEdge: CanvasEdge, connection: Connection) => {
    if(readOnly)return
    const base=removeEdgeFromGraph(page.nodes,page.edges,oldEdge.id)
    const next=noiDoThi(base.nodes,base.edges,connection,dinhNghia,luatNoiDay);if(next)dispatch({type:'graph',...next})
  },[readOnly,page,dinhNghia,luatNoiDay,dispatch])

  const duplicateNode = useCallback((nodeId: string) => {
    if(readOnly)return;const source=page.nodes.find(node=>node.id===nodeId);if(!source)return
    const clone={...structuredClone(source),id:`${source.id}-copy-${Date.now()}`,
      position:{x:source.position.x+32,y:source.position.y+32}}
    dispatch({type:'graph',nodes:[...page.nodes,clone],edges:page.edges});dispatch({type:'select',id:clone.id});ts.setSelected([clone.id])
  },[readOnly,page,dispatch,ts])

  const duplicate = useCallback(() => {
    if (readOnly) return
    const source=page.nodes.filter(node=>ts.selected.includes(node.id))
    if(!source.length)return
    const cloned=cloneGraphSelection(source,page.edges)
    dispatch({type:'graph',nodes:[...page.nodes,...cloned.nodes],edges:[...page.edges,...cloned.edges]})
    ts.setSelected(cloned.nodeIds);ts.setSelectedEdges([])
  }, [readOnly, page, dispatch, ts])

  const copy = useCallback(() => {
    const ids=new Set(ts.selected)
    copied.current={nodes:page.nodes.filter(node=>ids.has(node.id)).map(node=>structuredClone(node)),
      edges:page.edges.filter(edge=>ids.has(edge.source)&&ids.has(edge.target)).map(edge=>structuredClone(edge))}
  }, [page, ts.selected])

  const paste = useCallback(() => {
    if(readOnly||!copied.current.nodes.length)return
    const cloned=cloneGraphSelection(copied.current.nodes,copied.current.edges)
    dispatch({type:'graph',nodes:[...page.nodes,...cloned.nodes],edges:[...page.edges,...cloned.edges]})
    ts.setSelected(cloned.nodeIds);ts.setSelectedEdges([])
  },[readOnly,page,dispatch,ts])

  const toggleErrorBranch = useCallback(() => {
    const canh=ts.selectedEdge
    if(!canh||readOnly)return
    const condition=canh.data?.condition==='error'?'success':'error'
    dispatch({type:'graph',nodes:page.nodes,edges:page.edges.map(edge=>edge.id===canh.id?{...edge,data:{...edge.data,condition}}:edge)})
  }, [ts.selectedEdge, readOnly, page, dispatch])

  /** Kéo node: chốt MỘT bước hoàn tác cho cả lượt kéo, không một bước mỗi pixel.
   *  `onNodesChange` ghi vị trí bằng `sync` (không đụng lịch sử); `commit` ở
   *  cuối lượt mới đẩy ảnh chụp TRƯỚC khi kéo vào `past`. */
  const batDauKeo = useCallback(() => { dragBefore.current = structuredClone(ts.document) }, [ts.document])
  const ketThucKeo = useCallback(() => {
    if (dragBefore.current) dispatch({ type: 'commit', before: dragBefore.current })
    dragBefore.current = undefined
  }, [dispatch])

  return { themNode, chapNhanCanh, onConnect, onReconnectEdge, duplicateNode,
    duplicate, copy, paste, toggleErrorBranch, batDauKeo, ketThucKeo }
}
