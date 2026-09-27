/** Ba mức mật độ của node, và phép phân loại cổng đi kèm (spec `09 §3.1`).
 *
 *  ⭐ Mật độ là TỰ ĐỘNG, ⛔ không có công tắc tay (`08_DECISION_QUESTIONS.md`
 *     Q7). Nguồn duy nhất: zoom của React Flow + node có đang được chọn +
 *     node đã sinh artifact media hay chưa.
 */
import type { Cong, NodeDefinition } from '../nodeDefinition'

export type MucDo = 'compact' | 'normal' | 'expanded'

/** Dưới ngưỡng này chữ trong node không còn đọc được ⇒ chỉ giữ danh tính. */
export const NGUONG_ZOOM_COMPACT = 0.6

/** Chiều rộng từng mức (`09 §3.1`). Dùng chung giữa CSS và phép kiểm: CSS đọc
 *  `--node-rong` mà `NodeKhung` đặt từ bảng này, nên ⛔ không có hai con số. */
export const RONG_MUC: Record<MucDo, number> = {
  compact: 200, normal: 280, expanded: 360,
}

/** Ba trạng thái quyết định mức. Tách khỏi React để kiểm được không cần DOM. */
export type CanCuMatDo = {
  zoom: number
  dangChon: boolean
  /** Node đã sinh artifact media THẬT (không phải "khai một cổng ra media").
   *
   *  ⚠️ Hôm nay luôn `false`: `RunV3Node` (`workflowApi.ts`) mang `status`,
   *     `attempt`, `cost_credit`, `error` — ⛔ KHÔNG mang danh sách artifact.
   *     Đọc `cong_ra.kieu === 'video'` để suy ra "có media" là một phép đo sai
   *     đại lượng: nó đúng với MỌI `app.video.generate`, kể cả node chưa chạy,
   *     và sẽ làm mọi node video nở ra 360px vĩnh viễn. Khoá này để mở khi
   *     máy chủ trả số artifact — đường đi đã có, giá trị thì chưa.
   */
  coArtifactMedia?: boolean
}

/** Chọn mức. Thứ tự ưu tiên là CÓ Ý:
 *
 *  1. node đang chọn ⇒ `expanded` — chọn là một hành vi TƯỜNG MINH của người
 *     dùng, và nó phải thắng zoom: người ta zoom xa rồi bấm vào một node chính
 *     là để xem node ấy rõ hơn.
 *  2. zoom < 0.6 ⇒ `compact`.
 *  3. còn lại ⇒ `normal`.
 */
export function mucDoNode(cc: CanCuMatDo): MucDo {
  if (cc.dangChon || cc.coArtifactMedia) return 'expanded'
  if (cc.zoom < NGUONG_ZOOM_COMPACT) return 'compact'
  return 'normal'
}

/** Kiểu VÔ HƯỚNG — thứ người ta gõ vào form, gần như không bao giờ nối dây.
 *
 *  Nguồn: `he_kieu.KIEU_CO_BAN` (15 kiểu) giao với `luoc_do.KIEU_CONG`. Kiểu
 *  lạ ⇒ coi là KHÔNG vô hướng (an toàn về phía "cho nó một hàng có nhãn"),
 *  vì một kiểu mới của máy chủ không được phép biến mất khỏi node.
 */
const KIEU_VO_HUONG: ReadonlySet<string> = new Set([
  'text', 'number', 'integer', 'boolean',
  'model_ref', 'connection_ref', 'secret_ref',
])

export const laTapHop = (kieu: string): boolean => kieu.endsWith('[]')

export const laVoHuong = (kieu: string): boolean =>
  !laTapHop(kieu) && KIEU_VO_HUONG.has(kieu)

const KIEU_MEDIA: ReadonlySet<string> = new Set(
  ['image', 'video', 'audio', 'document', 'file'])

export const laMedia = (kieu: string): boolean =>
  KIEU_MEDIA.has(kieu.replace('[]', ''))

/** Node có mặt media (⇒ được phép hiện khay preview ở `expanded`). */
export const nodeCoMatMedia = (nd: NodeDefinition): boolean =>
  nd.cong_ra.some(c => laMedia(c.kieu))

/** Hai ngăn cổng: `hang` có NHÃN CHỮ, `khay` chỉ có chấm + tooltip.
 *
 *  🔴 MỌI cổng của cả hai ngăn đều được VẼ HANDLE. Bỏ vẽ một handle là làm
 *     đứt mọi cạnh đang trỏ vào nó — React Flow không tìm thấy handle thì
 *     nó vứt cạnh và không nói gì. Đây là chỗ khác nhau giữa "gọn" và "mất".
 */
export type NganCong = { hang: Cong[]; khay: Cong[] }

/** Phân loại cổng theo mức.
 *
 *  - `expanded`: mọi cổng có nhãn.
 *  - `compact`: mọi cổng vào khay (mức này chỉ giữ danh tính, `09 §3.1`).
 *  - `normal`: có nhãn khi cổng ĐANG CÓ DÂY, BẮT BUỘC, hoặc kiểu KHÔNG vô
 *    hướng (media/mảng/json/any — thứ người ta thật sự nối). Còn lại vào khay.
 *
 *  ⭐ Đây là phép cắt trả lời trực tiếp 525px: `app.video.generate` có 15 tham
 *     số ⇒ `luoc_do.cong_vao()` sinh 15 cổng vào, và 15 HÀNG CHỮ ở bước 24px
 *     là 360px chỉ riêng cổng. Khay xếp chấm theo lưới 24px NGANG nên 9 tham
 *     số vô hướng gọn vào một dòng 24px.
 */
export function phanLoaiCong(congs: readonly Cong[], daNoi: ReadonlySet<string>,
                             mucDo: MucDo): NganCong {
  if (mucDo === 'expanded') return { hang: [...congs], khay: [] }
  if (mucDo === 'compact') return { hang: [], khay: [...congs] }
  const hang: Cong[] = []
  const khay: Cong[] = []
  for (const c of congs) {
    if (daNoi.has(c.ten) || c.bat_buoc || !laVoHuong(c.kieu)) hang.push(c)
    else khay.push(c)
  }
  return { hang, khay }
}
