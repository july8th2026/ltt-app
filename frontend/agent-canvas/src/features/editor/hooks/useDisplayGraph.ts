import { useMemo } from 'react'
import { MarkerType } from '@xyflow/react'
import { NHAN_TRANG_THAI_NODE } from '../../../RunV3Panel'
import type { CanvasPage, RunV3 } from '../../../workflowApi'
import { dinhNghiaCua, nutThieu, type BangDinhNghia } from '../graph'

type ThamSo = {
  page: CanvasPage
  selectedId: string | undefined
  selected: string[]
  selectedEdges: string[]
  dinhNghia: BangDinhNghia
  loiNode: Record<string, string>
  run: RunV3 | null
  showConnections: boolean
}

/** Đồ thị TRÌNH BÀY — thứ React Flow vẽ, sinh từ tài liệu + trạng thái lượt chạy.
 *
 *  ⚠️ Node trang trí (`frame`/`annotation`) KHÔNG phải node đồ thị: chúng không
 *     có cổng, không tham số, `bien_dich.py` không thấy. Chúng nằm chung mảng
 *     vì React Flow vẽ mọi thứ bằng MỘT bảng `nodeTypes`.
 */
export function useDisplayGraph(ts: ThamSo) {
  const { page, selectedId, selected, selectedEdges, dinhNghia, loiNode, run,
    showConnections } = ts

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
        selected: node.id === selectedId || selected.includes(node.id),
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
  }, [page, selectedId, selected, dinhNghia, loiNode, run])

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

  return { displayNodes, displayEdges }
}
