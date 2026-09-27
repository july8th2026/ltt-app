import type { RunV3, RunV3Event, RunV3Node } from '../../../workflowApi'
import { tachLoi, type LoiDaTach } from './loiNguoiDoc'
import { khoangMs } from './thoiGian'

/** Mô hình TRÌNH BÀY của một bước trong một lượt chạy — 12 trường của
 *  `09_TARGET_DESIGN.md §8`, dựng từ `RunV3` cộng đồ thị đang mở.
 *
 *  ## ⭐ ĐÂY LÀ NƠI GHI RÕ TRƯỜNG NÀO CÓ CỬA, TRƯỜNG NÀO KHÔNG
 *
 *  Brief của làn này nói *"mọi trường của §8 đã có sẵn trong `RunV3`"*. Đọc
 *  `workflowApi.ts::RunV3Node` và `runs_v3.py::_nodes_json` thì **không đúng
 *  hẳn**, và chỗ lệch quan trọng:
 *
 *  | Trường §8 | Cửa thật hôm nay |
 *  |---|---|
 *  | trạng thái · lần thử · chi phí · lý do chờ | `RunV3Node` — CÓ |
 *  | lỗi | `RunV3Node.error` — CÓ (là mã máy, xem `loiNguoiDoc.ts`) |
 *  | tài nguyên | CHỈ `job_id`. ⛔ Không có tên GPU/lease trong `RunV3` |
 *  | nhật ký | `RunV3.su_kien` — CÓ, nhưng **run-level**: xem dưới |
 *  | thời lượng | ⛔ KHÔNG có mốc bắt đầu/kết thúc THEO BƯỚC |
 *  | đầu vào | ⛔ Không trong `RunV3`. Lấy `params` KHAI trong đồ thị đang mở |
 *  | đầu ra · artifact | ⛔ Không trong `RunV3`; chỉ cửa SO SÁNH trả `output_ref` |
 *  | lịch sử thử lại | Chỉ suy ra được từ `attempt` + sự kiện của bước |
 *
 *  ⇒ Các trường không có cửa trả `null`, ⛔ KHÔNG trả `0`/`{}`. Giao diện phải
 *  hiện "chưa có cửa đo" khác hẳn "đo được, bằng 0" — gộp hai chuyện đó vào một
 *  giá trị là mất khả năng phân biệt, và người đọc sẽ tin một con số bịa.
 *
 *  ## ⭐ `node_id` của sự kiện nằm ở HAI CHỖ
 *
 *  `su_kien.ghi` nhận `node_id=` như một cột riêng, và `dong_co`/`runs_v3` dùng
 *  nó (`NodeResumed`, `SupervisorDecision`). Nhưng `tac_tu.py` ghi `AgentStep`
 *  với `node_id=""` và nhét node vào `du_lieu["node_id"]`. Chỉ đọc cột thì mọi
 *  bước agent mất sạch nhật ký — im lặng, vì mảng rỗng trông y như "chưa có
 *  sự kiện nào". Đọc cả hai chỗ.
 */
export type BuocRun = {
  nodeId: string
  /** Tên bước cho NGƯỜI. ⛔ Không bao giờ là `node_id` thô. */
  ten: string
  /** 1-based, theo thứ tự `RunV3.nodes` (tức thứ tự node trong đồ thị). */
  thuTu: number
  status: string
  nhanTrangThai: string
  /** Nhãn `waiting_kind` đã dịch; rỗng khi bước không `WAITING`. */
  lyDoCho: string
  /** `waiting_kind` THÔ (`HUMAN`/`WEBHOOK`/…) — dùng cho `data-waiting-kind`,
   *  thứ Canvas và các phép kiểm chọn hàng theo. ⛔ Không hiện lên màn hình. */
  waitingKind: string
  /** Bước chờ-người kết thúc vì HẾT HẠN, không vì ai bấm (`het_han`). */
  hetHan: boolean
  lanThu: number
  chiPhi: number
  /** Tài nguyên: `job_id`, hoặc rỗng khi bước không nộp job nào. */
  jobId: string
  loi: LoiDaTach | null
  /** Sự kiện thuộc bước này, theo `seq` tăng. */
  nhatKy: RunV3Event[]
  /** `null` = KHÔNG ĐO ĐƯỢC (không có mốc), ⛔ không phải 0 ms. */
  thoiLuongMs: number | null
  /** Tham số KHAI trong đồ thị đang mở. `null` khi bên gọi không cấp đồ thị. */
  dauVao: Record<string, unknown> | null
  /** `output_ref` — chỉ có sau khi mở "So sánh"; `null` nếu chưa. */
  dauRa: Record<string, unknown> | null
  /** Con trỏ artifact trong `output_ref`, nếu bước này sinh ra tệp. */
  artifact: unknown
}

/** Bảng nhãn cho `status`/`waiting_kind` — bên gọi truyền vào để ⛔ KHÔNG có
 *  bản sao thứ hai của bảng nhãn trong kho mã (xem `RunV3Panel.tsx`). */
export type BangNhan = {
  trangThai: Record<string, string>
  waiting: Record<string, string>
}

export type NguonPhu = {
  /** `node_id` -> tên bước, dựng từ đồ thị (`graph.ts::nhanNode`). */
  tenBuoc?: (nodeId: string) => string
  /** `node_id` -> tham số khai trong đồ thị. */
  thamSo?: (nodeId: string) => Record<string, unknown> | undefined
  /** `node_id` -> `output_ref` (chỉ có từ cửa so sánh). */
  dauRa?: (nodeId: string) => Record<string, unknown> | undefined
}

/** Sự kiện thuộc về `nodeId`? Xem chú thích "node_id nằm ở HAI CHỖ" ở trên. */
function cuaBuoc(e: RunV3Event, nodeId: string): boolean {
  if (e.node_id === nodeId) return true
  const trong = e.du_lieu?.node_id
  return typeof trong === 'string' && trong === nodeId
}

/** Thời lượng của một bước, suy từ mốc sự kiện CỦA CHÍNH nó.
 *
 *  🔴 Cần ÍT NHẤT HAI mốc. Một sự kiện duy nhất cho `den - tu = 0` — đúng hình
 *     dạng "sai số 0 giả": nó sẽ hiện `0s` cho một bước có thể đã chạy 12 giây.
 *     Một mốc ⇒ `null` ⇒ giao diện nói "không đo được".
 */
function thoiLuongBuoc(nhatKy: RunV3Event[]): number | null {
  if (nhatKy.length < 2) return null
  return khoangMs(nhatKy[0].created_at, nhatKy[nhatKy.length - 1].created_at)
}

export function dungBuoc(node: RunV3Node, thuTu: number, run: RunV3,
                         nhan: BangNhan, phu: NguonPhu = {}): BuocRun {
  const nhatKy = run.su_kien.filter(e => cuaBuoc(e, node.node_id))
                            .sort((a, b) => a.seq - b.seq)
  const dauRa = phu.dauRa?.(node.node_id) ?? null
  return {
    nodeId: node.node_id,
    // ⛔ KHÔNG lùi về `node_id` khi không có tên: `nmujtmc1b-0` trên cột đầu là
    //    chính con bọ làn này tồn tại để gỡ. `Bước N` nói ít, nhưng nói THẬT,
    //    và `node_id` vẫn còn nguyên trong phần chi tiết kỹ thuật.
    ten: phu.tenBuoc?.(node.node_id)?.trim() || `Bước ${thuTu}`,
    thuTu,
    status: node.status,
    nhanTrangThai: nhan.trangThai[node.status] ?? node.status,
    lyDoCho: node.status === 'WAITING' && node.waiting_kind
      ? nhan.waiting[node.waiting_kind] ?? node.waiting_kind : '',
    waitingKind: node.waiting_kind,
    hetHan: node.het_han,
    lanThu: node.attempt,
    chiPhi: node.cost_credit,
    jobId: node.job_id,
    loi: tachLoi(node.error),
    nhatKy,
    thoiLuongMs: thoiLuongBuoc(nhatKy),
    dauVao: phu.thamSo?.(node.node_id) ?? null,
    dauRa,
    artifact: dauRa?.artifact_ref ?? null,
  }
}

export function dungCacBuoc(run: RunV3, nhan: BangNhan,
                            phu: NguonPhu = {}): BuocRun[] {
  return run.nodes.map((node, i) => dungBuoc(node, i + 1, run, nhan, phu))
}

/** Sự kiện KHÔNG thuộc bước nào (mức lượt chạy): `WorkflowStarted`,
 *  `WorkflowCompleted`… Nhật ký chung hiện chúng. */
export const suKienMucRun = (run: RunV3) =>
  run.su_kien.filter(e => !e.node_id && typeof e.du_lieu?.node_id !== 'string')
             .sort((a, b) => a.seq - b.seq)

/** Mốc CUỐI của cả lượt chạy — `seq` lớn nhất, ⛔ không phải phần tử cuối mảng.
 *
 *  `nhapRun` nối lô SSE mới vào sau lô cũ, nhưng phản hồi của `/cancel` trả CẢ
 *  lịch sử, nên thứ tự mảng không phải lúc nào cũng là `seq` tăng dần.
 */
export const suKienCuoi = (run: RunV3): RunV3Event | null =>
  run.su_kien.reduce<RunV3Event | null>(
    (max, e) => (!max || e.seq > max.seq) ? e : max, null)
