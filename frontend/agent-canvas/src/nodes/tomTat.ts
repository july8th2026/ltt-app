/** Năm thứ một node được phép mang (`09 §3.2`), phần TÍNH.
 *
 *  Tách khỏi JSX vì đây là chỗ dễ sai NHẤT của node: `01_CURRENT_UI_AUDIT.md`
 *  §4.2 đã bắt được hai câu node nói SAI, và cả hai đều là một phép đếm chạy
 *  trên đại lượng sai. Tệp này kiểm được không cần DOM.
 */
import type { NodeDefinition } from '../nodeDefinition'

// ── Trục 1: SỨC KHOẺ (viền) ────────────────────────────────────────────────

/** Bảy giá trị của `09 §3.3`. ⛔ Không thêm giá trị mà không thêm một luật CSS
 *  cho nó — một sức khoẻ không có viền riêng là một sức khoẻ không tồn tại. */
export type SucKhoe = 'idle' | 'running' | 'waiting' | 'succeeded' | 'failed'
                    | 'skipped' | 'stale'

/** `RunV3Node.status` → sức khoẻ. Nguồn của tập bên trái:
 *  `RunV3Panel.NHAN_TRANG_THAI_NODE`.
 *
 *  ⚠️ `CANCELLED` đi về `skipped`, ⛔ không về `failed`: người dùng bấm huỷ thì
 *     không có gì hỏng, và một viền đỏ ở đó là một lời buộc tội sai.
 */
const SUC_KHOE_TU_STATUS: Record<string, SucKhoe> = {
  PENDING: 'idle', READY: 'idle', QUEUED: 'idle', KHONG_XAC_DINH: 'idle',
  RUNNING: 'running',
  WAITING: 'waiting', RETRY_SCHEDULED: 'waiting',
  SUCCEEDED: 'succeeded',
  FAILED: 'failed', ABANDONED: 'failed',
  SKIPPED: 'skipped', CANCELLED: 'skipped',
}

export const sucKhoeTuStatus = (status: string | undefined): SucKhoe =>
  (status && SUC_KHOE_TU_STATUS[status]) || 'idle'

// ── Trục 2: HUY HIỆU GÓC (định lượng) ──────────────────────────────────────

/** ⭐ `loi_cau_hinh` và `loi_chay` là HAI loại, `09 §3.3` đòi tách chúng. Một
 *  node bị publish từ chối (422) và một node chạy hỏng đòi hai hành động khác
 *  nhau: sửa ô cấu hình, hay chạy lại. Gộp một huy hiệu đỏ là bắt người dùng
 *  tự đoán mình đang ở ca nào. */
export type LoaiHuyHieu = 'loi_cau_hinh' | 'loi_chay' | 'thieu_ket_noi'
                        | 'so_lan_thu'

export type HuyHieu = { loai: LoaiHuyHieu; nhan: string; moTa: string }

export type CanCuHuyHieu = {
  /** Thông điệp 422 của cửa publish, nếu có. */
  loiBienDich?: string
  /** `RunV3Node.error`, nếu có. */
  loiChay?: string
  /** Số cổng vào BẮT BUỘC chưa có dây. */
  thieuKetNoi?: number
  /** `RunV3Node.attempt`. */
  lanThu?: number
}

export function huyHieuNode(cc: CanCuHuyHieu): HuyHieu[] {
  const ra: HuyHieu[] = []
  if (cc.loiBienDich)
    ra.push({ loai: 'loi_cau_hinh', nhan: '!', moTa: `Lỗi cấu hình: ${cc.loiBienDich}` })
  if (cc.loiChay)
    ra.push({ loai: 'loi_chay', nhan: '×', moTa: `Lỗi khi chạy: ${cc.loiChay}` })
  if (cc.thieuKetNoi)
    ra.push({ loai: 'thieu_ket_noi', nhan: String(cc.thieuKetNoi),
              moTa: `${cc.thieuKetNoi} cổng bắt buộc chưa có dây` })
  if (cc.lanThu && cc.lanThu > 1)
    ra.push({ loai: 'so_lan_thu', nhan: `↻${cc.lanThu}`,
              moTa: `Đã thử ${cc.lanThu} lần` })
  return ra
}

// ── Tóm tắt LƯỢT CHẠY ──────────────────────────────────────────────────────

export type TomTatChay = {
  credit?: number
  lanThu?: number
  /** Giây. ⚠️ Suy từ `RunV3.su_kien` (mốc đầu → mốc cuối của node), ⛔ KHÔNG
   *  phải một trường máy chủ trả: `RunV3Node` không có `started_at`/
   *  `finished_at`. Vắng khi node có dưới hai sự kiện. */
  thoiLuongS?: number
}

export function nhanTomTatChay(t: TomTatChay | undefined): string {
  if (!t) return ''
  const phan: string[] = []
  if (t.credit !== undefined) phan.push(`${t.credit} credit`)
  if (t.thoiLuongS !== undefined) phan.push(dinhDangThoiLuong(t.thoiLuongS))
  if (t.lanThu !== undefined && t.lanThu > 1) phan.push(`lần ${t.lanThu}`)
  return phan.join(' · ')
}

export function dinhDangThoiLuong(giay: number): string {
  if (giay < 1) return `${Math.round(giay * 1000)}ms`
  if (giay < 60) return `${giay < 10 ? giay.toFixed(1) : Math.round(giay)}s`
  const phut = Math.floor(giay / 60)
  return `${phut}m ${String(Math.round(giay % 60)).padStart(2, '0')}s`
}

// ── Tóm tắt CẤU HÌNH — một dòng, ⛔ không phải một form ─────────────────────

/** Bao nhiêu tham số được lên node. Quá ba thì nó thành một form, và cả điểm
 *  của `09 §3.2` là node ⛔ KHÔNG phải form. */
const TRAN_THAM_SO_TOM_TAT = 3
const TRAN_KY_TU_GIA_TRI = 22

/** Tham số KHÔNG bao giờ lên dòng tóm tắt: chúng dài, hoặc là bí mật, hoặc
 *  đã có chỗ riêng (biểu thức hiện ở Inspector). */
const BO_QUA_TOM_TAT: ReadonlySet<string> = new Set(['refs', 'secret', 'api_key'])

const gonGiaTri = (v: unknown): string | undefined => {
  if (v === null || v === undefined || v === '') return undefined
  if (typeof v === 'boolean') return v ? 'bật' : 'tắt'
  if (Array.isArray(v)) return v.length ? `${v.length} mục` : undefined
  if (typeof v === 'object') return undefined
  const s = String(v)
  if (!s.trim()) return undefined
  return s.length > TRAN_KY_TU_GIA_TRI ? `${s.slice(0, TRAN_KY_TU_GIA_TRI - 1)}…` : s
}

/** 🔴 Nhánh của một node điều khiển — chỗ `01 §4.2` bắt được HAI câu sai.
 *
 *  `ThanControl` cũ in `{cong_ra.length} nhánh` cho mọi node `control`. Hậu
 *  quả đo được trên trình duyệt:
 *
 *      core.stop    -> "0 nhánh"   (nó KHÔNG có cổng ra, đó là cả ý nghĩa)
 *      core.switch  -> "1 nhánh"   (luôn luôn: nó khai ĐÚNG MỘT cổng ra
 *                                   `nhanh`, tên nhánh nằm trong THAM SỐ
 *                                   `nhanh: array`)
 *
 *  Tức `cong_ra.length` ⛔ không phải đại lượng "số nhánh". Hàm này trả
 *  `undefined` khi node KHÔNG rẽ nhánh, và người gọi ⛔ không in gì.
 */
export function soNhanh(nd: NodeDefinition,
                        params: Record<string, unknown> | undefined):
                        { so: number; ten: string[] } | undefined {
  // Cổng ra khai tường minh `nhanh: array` trong tham số ⇒ THAM SỐ là nguồn.
  const khaiTay = params?.nhanh
  if (Array.isArray(khaiTay)) {
    const ten = khaiTay.map(String).filter(Boolean)
    const macDinh = params?.mac_dinh ? String(params.mac_dinh) : ''
    return { so: ten.length + (macDinh && !ten.includes(macDinh) ? 1 : 0),
             ten: macDinh ? [...ten, `${macDinh} (mặc định)`] : ten }
  }
  // ⛔ Node không có cổng ra KHÔNG rẽ nhánh. `core.stop` kết thúc lượt chạy.
  if (nd.cong_ra.length === 0) return undefined
  // Nhiều cổng ra kiểu `control` (ví dụ `core.if` -> `true`/`false`): CHÍNH
  // các cổng ấy là nhánh, và tên chúng đọc được — nên in TÊN, không in số.
  const dieuKhien = nd.cong_ra.filter(c => c.kieu === 'control')
  if (dieuKhien.length >= 2)
    return { so: dieuKhien.length, ten: dieuKhien.map(c => c.ten) }
  return undefined
}

/** Dòng tóm tắt cấu hình của một node. Rỗng ⇒ ⛔ người gọi không vẽ dòng nào
 *  (một dòng rỗng vẫn tốn 18px và vẫn nói "ở đây có thông tin"). */
export function tomTatCauHinh(nd: NodeDefinition,
                             params: Record<string, unknown> | undefined): string {
  const nhanh = nd.kind === 'control' ? soNhanh(nd, params) : undefined
  if (nhanh)
    return nhanh.ten.length && nhanh.ten.length <= TRAN_THAM_SO_TOM_TAT
      ? nhanh.ten.join(' · ')
      : `${nhanh.so} nhánh`
  const phan: string[] = []
  for (const ten of Object.keys(nd.tham_so.properties ?? {})) {
    if (phan.length >= TRAN_THAM_SO_TOM_TAT) break
    if (BO_QUA_TOM_TAT.has(ten)) continue
    const gt = gonGiaTri(params?.[ten])
    if (gt !== undefined) phan.push(gt)
  }
  // ⛔ KHÔNG rơi về `app_name`/`title`/`description` khi chưa có tham số nào:
  //   - `app_name` đã là TIÊU ĐỀ của node, và `title` đã là dòng phụ ⇒ lặp lại
  //     một trong hai ở đây là tiêu một dòng để nói lại điều vừa nói;
  //   - `description` là câu bị cắt 60 ký tự (`01 §4.1`).
  // Node CÓ tham số mà chưa đặt gì là một điều CÓ THẬT và cần nói ra. Node
  // không có tham số nào thì ⇒ rỗng, và người gọi ⛔ không vẽ dòng nào.
  if (!phan.length)
    return Object.keys(nd.tham_so.properties ?? {}).length ? 'Chưa cấu hình' : ''
  return phan.join(' · ')
}
