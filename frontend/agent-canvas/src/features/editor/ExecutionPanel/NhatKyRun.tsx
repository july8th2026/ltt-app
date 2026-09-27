import type { RunV3Event } from '../../../workflowApi'
import { gio } from './thoiGian'

type Props = {
  suKien: RunV3Event[]
  /** `node_id` -> tên bước. Sự kiện của một bước hiện TÊN bước, ⛔ không `node_id`. */
  tenBuoc: (nodeId: string) => string
}

/** Nhật ký lượt chạy — MỖI DÒNG CÓ DẤU THỜI GIAN.
 *
 *  🔴 Bản cũ in `loai · node_id` và ⛔ KHÔNG có dấu thời gian, dù
 *     `RunV3Event.created_at` có sẵn trong đúng gói dữ liệu đang vẽ. Một nhật ký
 *     không có giờ thì ⛔ không trả lời được câu duy nhất người ta mở nó để hỏi:
 *     *"chỗ nào chậm?"*.
 *
 *  ⭐ `<time dateTime=…>` giữ mốc ISO ĐẦY ĐỦ trong thuộc tính, còn phần hiện ra
 *     chỉ là `hh:mm:ss`. Máy đọc được ngày, người đọc không bị một chuỗi ISO
 *     27 ký tự chắn mất nội dung dòng.
 */
export function NhatKyRun({ suKien, tenBuoc }: Props) {
  if (!suKien.length) return null
  return (
    <ol className="run-nhat-ky run-v3-su-kien">
      {suKien.map(e => {
        // `node_id` nam o HAI cho: cot rieng, va `du_lieu` (xem `buocCuaRun.ts`).
        const trong = e.du_lieu?.node_id
        const nodeId = e.node_id || (typeof trong === 'string' ? trong : '')
        return (
          <li key={e.seq}>
            <time dateTime={e.created_at}>{gio(e.created_at)}</time>
            {' '}<span className="run-nhat-ky-loai">{e.loai}</span>
            {nodeId && <> · {tenBuoc(nodeId)}</>}
          </li>
        )
      })}
    </ol>
  )
}
