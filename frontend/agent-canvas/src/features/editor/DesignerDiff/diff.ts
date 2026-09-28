/** Diff THUẦN giữa hai `CanvasDocument` — không React, không lời gọi mạng.
 *
 *  ⭐ UI-8b (B7 — `02_SCORECARD.md`): "Soạn bằng AI" GHI ĐÈ đồ thị đang dựng.
 *     Vế "mất lịch sử hoàn tác" đã được vá (`EditorShell.tsx` dispatch
 *     `giuLichSu:true`) — vế còn lại là người dùng ⛔ không thấy TRƯỚC đồ thị
 *     sẽ đổi thế nào. Hàm này tính phần "thấy trước" đó; component
 *     `DesignerDiff.tsx` chỉ vẽ nó ra.
 *
 *  ⭐ So khớp NODE theo `id` trước — id ổn định qua các lần soạn lại CÙNG một
 *     bản nháp (máy chủ giữ `node_id` của các bước không đổi khi sinh lại, xem
 *     `platform_core/agent/ke_hoach_v3.py`). Id chỉ có ở MỘT bên ⇒ thêm/xoá;
 *     id có ở CẢ hai bên thì so `data.tool` (loại bước) và `data.params`
 *     (tham số) — khác một trong hai ⇒ "đổi tham số".
 *
 *  ⭐ CẠNH chỉ so theo `id` (thêm/xoá) — spec không đòi phân biệt "cạnh đổi",
 *     và `CanvasEdge.id` đã mã hoá cả `source/target/handle`
 *     (`noiDoThi` ở `graph.ts`: `${source}-${sourceHandle}-${target}-
 *     ${targetHandle}`), nên một cạnh "đổi đầu nối" tự nhiên hiện ra thành
 *     một cặp xoá+thêm với id khác nhau — không cần một nhánh so sánh riêng.
 */
import type { CanvasDocument, CanvasEdge, CanvasNode } from '../../../workflowApi'
import { nhanNode, type BangDinhNghia } from '../graph'

export type TrangThaiDoiNode = 'them' | 'xoa' | 'doi_tham_so'

export type MucDoiNode = { id: string; ten: string; trangThai: TrangThaiDoiNode }
export type MucDoiEdge = { id: string; trangThai: 'them' | 'xoa' }

export type KetQuaDiffThietKe = {
  nodes: MucDoiNode[]
  edges: MucDoiEdge[]
  soNodeThem: number
  soNodeXoa: number
  soNodeDoiThamSo: number
  soEdgeThem: number
  soEdgeXoa: number
  /** `false` ⇒ AI trả lại đúng đồ thị cũ (không có gì để xem trước). */
  coThayDoi: boolean
}

function tatCaNode(doc: CanvasDocument): CanvasNode[] {
  return doc.pages.flatMap(trang => trang.nodes)
}
function tatCaEdge(doc: CanvasDocument): CanvasEdge[] {
  return doc.pages.flatMap(trang => trang.edges)
}

/** Sắp XẾP KHOÁ đệ quy trước khi so — `JSON.stringify` trần giữ THỨ TỰ CHÈN,
 *  nên hai đối tượng tham số bằng nhau về Ý NGHĨA nhưng máy chủ tái sinh với
 *  thứ tự khoá khác (hoàn toàn có thể — `bien_dich.py` không hứa giữ thứ tự)
 *  sẽ bị tính NHẦM thành "đổi tham số". Đó là một đại lượng sai: người dùng
 *  thấy "1 bước đổi tham số" cho một bước KHÔNG hề đổi. */
function chuanHoa(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(chuanHoa)
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.keys(value as Record<string, unknown>).sort()
      .map(khoa => [khoa, chuanHoa((value as Record<string, unknown>)[khoa])]))
  }
  return value
}

/** `data.params` là dữ liệu JSON thuần (tham số node, xem `bien_dich.py`) —
 *  so bằng chuỗi JSON ĐÃ CHUẨN HOÁ khoá là đủ, ⛔ không cần so sâu bằng tay. */
function thamSoKhacNhau(a: CanvasNode, b: CanvasNode): boolean {
  if (a.data.tool !== b.data.tool) return true
  return JSON.stringify(chuanHoa(a.data.params ?? null))
    !== JSON.stringify(chuanHoa(b.data.params ?? null))
}

export function tinhDiffThietKe(cu: CanvasDocument, moi: CanvasDocument,
                                bang: BangDinhNghia): KetQuaDiffThietKe {
  const nodesCu = tatCaNode(cu), nodesMoi = tatCaNode(moi)
  const edgesCu = tatCaEdge(cu), edgesMoi = tatCaEdge(moi)
  const mapCu = new Map(nodesCu.map(node => [node.id, node]))
  const mapMoi = new Map(nodesMoi.map(node => [node.id, node]))

  const nodes: MucDoiNode[] = []
  for (const node of nodesMoi) {
    if (!mapCu.has(node.id)) {
      nodes.push({ id: node.id, ten: nhanNode(node, nodesMoi, bang), trangThai: 'them' })
    }
  }
  for (const node of nodesCu) {
    if (!mapMoi.has(node.id)) {
      nodes.push({ id: node.id, ten: nhanNode(node, nodesCu, bang), trangThai: 'xoa' })
    }
  }
  for (const node of nodesMoi) {
    const truoc = mapCu.get(node.id)
    if (truoc && thamSoKhacNhau(truoc, node)) {
      nodes.push({ id: node.id, ten: nhanNode(node, nodesMoi, bang), trangThai: 'doi_tham_so' })
    }
  }

  const idCanhCu = new Set(edgesCu.map(edge => edge.id))
  const idCanhMoi = new Set(edgesMoi.map(edge => edge.id))
  const edges: MucDoiEdge[] = []
  for (const id of idCanhMoi) if (!idCanhCu.has(id)) edges.push({ id, trangThai: 'them' })
  for (const id of idCanhCu) if (!idCanhMoi.has(id)) edges.push({ id, trangThai: 'xoa' })

  const soNodeThem = nodes.filter(item => item.trangThai === 'them').length
  const soNodeXoa = nodes.filter(item => item.trangThai === 'xoa').length
  const soNodeDoiThamSo = nodes.filter(item => item.trangThai === 'doi_tham_so').length
  const soEdgeThem = edges.filter(item => item.trangThai === 'them').length
  const soEdgeXoa = edges.filter(item => item.trangThai === 'xoa').length

  return { nodes, edges, soNodeThem, soNodeXoa, soNodeDoiThamSo, soEdgeThem, soEdgeXoa,
    coThayDoi: nodes.length > 0 || edges.length > 0 }
}
