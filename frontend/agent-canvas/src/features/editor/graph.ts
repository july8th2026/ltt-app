/** Phép biến đổi ĐỒ THỊ thuần — không React, không state, không lời gọi mạng.
 *
 *  ⭐ Tách ra khỏi `CanvasShell` vì chúng là phần DỄ KIỂM nhất của trình soạn:
 *     vào đồ thị, ra đồ thị. Trước đây chúng nằm ở mức module trong một tệp
 *     959 dòng nên không ai gọi được chúng lẻ.
 */
import { addEdge, type Connection } from '@xyflow/react'
import { connectionCreatesCycle } from '../../editorState'
import { noiDuoc, typeTuSlug } from '../../nodeDefinition'
import type { LuatNoiDay, NodeDefinition } from '../../nodeDefinition'
import type { CanvasEdge, CanvasNode, RunV3 } from '../../workflowApi'

export type BangDinhNghia = Map<string, NodeDefinition>

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
export function taoKhoaChay(): string {
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
export function nutThieu(slug: string): NodeDefinition {
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

export function removeEdgeFromGraph(nodes:CanvasNode[],edges:CanvasEdge[],edgeId:string){
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

/** `NodeDefinition` cua mot node trong do thi.
 *
 *  ⭐ Node v3 luu `data.tool` = **slug cong cu** (`image.generate`), con
 *     `NodeDefinition.type` la `app.image.generate`
 *     (`platform_core/workflow/nut.py::tu_toolspec`). `bien_dich._node` doc
 *     dung `data.tool` ay, nen hinh dang luu tru KHONG doi o task nay — chi
 *     lop trinh bay doi. Ghep tien to o dung MOT cho: `typeTuSlug`.
 */
export const dinhNghiaCua = (bang: BangDinhNghia, node?: CanvasNode) =>
  node ? bang.get(String(node.data.tool)) : undefined

/** Noi hai cong, tra do thi moi — hoac `undefined` neu luat tu choi.
 *
 *  ⛔ Luat noi day tai TU SERVER (`he_kieu.xuat_luat_noi_day()`), khong cai
 *     dat lai o client: hai ban cai dat song song thi lech, va lech im lang.
 */
export function noiDoThi(nodes:CanvasNode[],edges:CanvasEdge[],connection:Connection,
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

export function nhanNode(node:CanvasNode,nodes:CanvasNode[],bang:BangDinhNghia){
  const ten=(item:CanvasNode)=>item.label?.trim()||dinhNghiaCua(bang,item)?.title||String(item.data.tool)
  const base=ten(node)
  const peers=nodes.filter(item=>ten(item)===base)
  return peers.length>1?`${base} ${peers.findIndex(item=>item.id===node.id)+1}`:base
}

/** Noi su kien theo `seq`: chi giu cai MOI hon cai da co.
 *
 *  🔴 Do duoc tren trinh duyet 23/09: cua huy (`POST /runs/{id}/cancel`) KHONG
 *     nhan `?sau=`, nen no tra CA lich su; con vong poll tra phan tang dan.
 *     Noi mu quang lam dong thoi gian hien `WorkflowStarted` hai lan. Loc theo
 *     `seq` dung cho ca hai nguon, va khong phu thuoc nguon nao tra gi. */
export function nhapRun(truoc:RunV3|null,next:RunV3):RunV3{
  if(!truoc||truoc.id!==next.id)return next
  const cuoi=truoc.su_kien.reduce((max,e)=>Math.max(max,e.seq),0)
  return {...next,su_kien:[...truoc.su_kien,...next.su_kien.filter(e=>e.seq>cuoi)]}
}
