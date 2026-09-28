import { useMemo } from 'react'
import { MarkerType } from '@xyflow/react'
import { NHAN_TRANG_THAI_NODE } from '../../../RunV3Panel'
import { RUN_V3_KET_THUC, type CanvasEdge, type CanvasPage,
  type RunV3, type RunV3Node } from '../../../workflowApi'
import { huyHieuNode, sucKhoeTuStatus, type SucKhoe, type TomTatChay }
  from '../../../nodes/tomTat'
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

/** Cổng nào của node nào ĐANG CÓ DÂY. Một `Map<nodeId, Set<tênCổng>>`.
 *
 *  ⭐ Node ⛔ không tự biết điều này: nó chỉ thấy `NodeDefinition` của chính
 *     nó. Mật độ `normal` cần biết để giữ NHÃN cho cổng đã nối — một cổng có
 *     dây mà tụt xuống khay chấm là làm người dùng mất dấu sợi dây của họ.
 */
function congDaNoiTheoNode(edges: readonly CanvasEdge[]): Map<string, Set<string>> {
  const ra = new Map<string, Set<string>>()
  const them = (nodeId: string | undefined, cong: string | null | undefined) => {
    if (!nodeId || !cong) return
    const bo = ra.get(nodeId) ?? new Set<string>()
    bo.add(cong)
    ra.set(nodeId, bo)
  }
  for (const e of edges) {
    them(e.source, e.sourceHandle)
    them(e.target, e.targetHandle)
  }
  return ra
}

/** Thời lượng một node, GIÂY — suy từ mốc sự kiện đầu/cuối của nó.
 *
 *  ⚠️ `RunV3Node` ⛔ KHÔNG có `started_at`/`finished_at`; đây là đại lượng gần
 *     nhất đọc được từ cửa hiện có. Dưới hai sự kiện ⇒ `undefined`, ⛔ không
 *     trả `0`: "0 giây" và "không đo được" là hai câu khác nhau, và gộp chúng
 *     vào một giá trị là mất khả năng phân biệt.
 */
function thoiLuongNode(run: RunV3 | null, nodeId: string): number | undefined {
  if (!run) return undefined
  const moc = run.su_kien
    .filter(sk => sk.node_id === nodeId)
    .map(sk => Date.parse(sk.created_at))
    .filter(t => Number.isFinite(t))
  if (moc.length < 2) return undefined
  const d = (Math.max(...moc) - Math.min(...moc)) / 1000
  return d >= 0 ? d : undefined
}

/** Node đã XONG nhưng kết quả có thể KHÔNG còn ứng với đồ thị hiện tại.
 *
 *  ⭐ `stale` đáng giá riêng với LTT (`09 §3.3`): LTT có sổ credit thật, và một
 *     người xem output cũ mà tưởng là mới sẽ ra quyết định sai trên tiền thật.
 *
 *  🔴 PHẠM VI CỦA PHÉP ĐO NÀY HẸP HƠN TÊN NÓ, nói thẳng ra ở đây:
 *     bắt được  : một node CHA được THÊM VÀO đồ thị sau lượt chạy (cha không
 *                 có trạng thái nào trong `run.nodes`) ⇒ kết quả của node này
 *                 không thể sinh ra từ hình dạng đồ thị đang thấy.
 *     ⛔ KHÔNG bắt được: người dùng SỬA THAM SỐ của chính node này sau khi
 *                 chạy. Muốn bắt thì `RunV3Node` phải mang một băm tham số
 *                 đầu vào, và nó chưa mang. ⇒ ⛔ đừng đọc "không stale" thành
 *                 "kết quả còn mới".
 */
function laCu(page: CanvasPage, run: RunV3 | null, nodeId: string,
              coTrangThai: (id: string) => boolean): boolean {
  if (!run || !RUN_V3_KET_THUC.has(run.status)) return false
  return page.edges.some(e => e.target === nodeId && !coTrangThai(e.source))
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
    const daNoi = congDaNoiTheoNode(page.edges)
    const bangRun = new Map<string, RunV3Node>(
      (run?.nodes ?? []).map(n => [n.node_id, n]))
    const coTrangThai = (id: string) => bangRun.has(id)
    const tools = page.nodes.map(node => {
      const nd = dinhNghiaCua(dinhNghia, node) ?? nutThieu(String(node.data.tool))
      const mucRun = bangRun.get(node.id)
      const trangThaiRun = mucRun?.status
      const congCuaNode = daNoi.get(node.id) ?? new Set<string>()

      // ── Trục 1: SỨC KHOẺ (viền) ────────────────────────────────────────
      let sucKhoe: SucKhoe = sucKhoeTuStatus(trangThaiRun)
      if (sucKhoe === 'succeeded' && laCu(page, run, node.id, coTrangThai))
        sucKhoe = 'stale'

      // ── Trục 2: HUY HIỆU GÓC (định lượng) ──────────────────────────────
      // ⭐ Đếm cổng vào BẮT BUỘC chưa có GIÁ TRỊ. ⛔ KHÔNG đếm mọi cổng chưa
      //    nối: phần lớn 15 cổng của `app.video.generate` là tham số vô hướng,
      //    người dùng gõ chúng ở Inspector, và đòi dây cho chúng là báo động
      //    giả trên MỌI node — thứ làm người ta tắt cả cổng.
      //
      // 🔴 VÀ MỘT CỔNG BẮT BUỘC CÓ HAI ĐƯỜNG ĐƯỢC THOẢ: một sợi dây, HOẶC một
      //    giá trị gõ tay ở Inspector (`luoc_do.cong_vao()` sinh cổng từ CHÍNH
      //    `params_schema`, nên mỗi cổng vào LÀ một tham số). Bản đầu chỉ hỏi
      //    "có dây chưa", và ảnh chụp trình duyệt 28/09 bắt được ngay: một node
      //    `app.video.generate` đã gõ đủ `prompt` vẫn đeo huy hiệu "1 cổng bắt
      //    buộc chưa có dây". Một báo động giả trên MỌI node là đúng cái làm
      //    người ta tắt cả cổng cảnh báo.
      const thamSo = (node.data.params ?? {}) as Record<string, unknown>
      const coGiaTri = (ten: string) => {
        const v = thamSo[ten]
        if (v === undefined || v === null || v === '') return false
        return Array.isArray(v) ? v.length > 0 : true
      }
      const thieuKetNoi = nd.cong_vao
        .filter(c => c.bat_buoc && !congCuaNode.has(c.ten) && !coGiaTri(c.ten))
        .length
      const huyHieu = huyHieuNode({
        loiBienDich: loiNode[node.id],
        loiChay: mucRun?.error || undefined,
        thieuKetNoi,
        lanThu: mucRun?.attempt,
      })

      const tomTatChay: TomTatChay | undefined = mucRun
        ? { credit: mucRun.cost_credit, lanThu: mucRun.attempt,
            thoiLuongS: thoiLuongNode(run, node.id) }
        : undefined

      return { ...node, type: 'ltt',
        // Dau MAY DOC DUOC cho node bi publish tu choi (422 `{ma,node_id}`).
        // React Flow dan `className` len chinh `.react-flow__node`, nen cai
        // dau nay o CUNG cho voi `data-id` — mot phep kiem khong phai doan
        // qua mot chuoi tieng Viet co the doi.
        className: loiNode[node.id] ? 'node-do-loi' : undefined,
        selected: node.id === selectedId || selected.includes(node.id),
        data: { ...node.data, dinhNghia: nd,
          sucKhoe, huyHieu, tomTatChay,
          congDaNoi: [...congCuaNode],
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
