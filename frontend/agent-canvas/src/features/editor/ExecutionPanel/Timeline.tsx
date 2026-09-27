import type { BuocRun } from './buocCuaRun'
import { nhanThoiLuong } from './thoiGian'

type Props = {
  buoc: BuocRun[]
  /** `node_id` đang mở trong Inspector — hàng của nó được đánh dấu. */
  dangChon: string
  chon: (nodeId: string) => void
  /** Run đã kết thúc? Chỉ khi ấy "Chạy lại từ đây" mới có nghĩa. */
  xong: boolean
  onChayLaiTu?: (nodeId: string) => void
}

/** Dòng thời gian THEO BƯỚC — thay bảng phẳng `node_id/trạng thái/credit/lỗi`.
 *
 *  ## ⭐ Cột đầu là TÊN BƯỚC, và đó là cả điểm của tệp này
 *
 *  Bản cũ in `node_id` thô (`nmujtmc1b-0`, `n-img`). Người dùng ⛔ không có cách
 *  nào biết `nmujtmc1b-0` là bước nào — id ấy do trình soạn sinh, không xuất
 *  hiện ở bất kỳ chỗ nào khác trên màn hình. `node_id` vẫn đọc được, nhưng ở
 *  Inspector, trong phần "Chi tiết kỹ thuật" — nơi người đi gỡ lỗi tìm nó.
 *
 *  ## ⭐ Thời lượng RỖNG hiện `—`, ⛔ không hiện `0s`
 *
 *  `RunV3` không có mốc bắt đầu/kết thúc theo bước (xem `buocCuaRun.ts`), nên
 *  phần lớn bước chỉ đo được khi chúng có ≥ 2 sự kiện riêng. Một `0s` ở đây là
 *  một con số BỊA: nó không phân biệt được "chạy tức thì" với "không có cửa
 *  đo", và người đọc sẽ tin cái đầu.
 */
export function Timeline(p: Props) {
  // Mốc chia tỉ lệ thanh tiến trình: bước LÂU NHẤT đo được. Không bước nào đo
  // được ⇒ không thanh nào có bề rộng, và đó là câu trả lời đúng.
  const lauNhat = p.buoc.reduce((max, b) => Math.max(max, b.thoiLuongMs ?? 0), 0)
  return (
    <table className="run-timeline">
      <caption className="sr-only">Dòng thời gian các bước của lượt chạy</caption>
      <thead>
        <tr><th scope="col">Bước</th><th scope="col">Thời lượng</th>
          <th scope="col">Chi phí</th><th scope="col">Trạng thái</th>
          <th scope="col">Lần thử</th><th scope="col"><span className="sr-only">Thao tác</span></th></tr>
      </thead>
      <tbody>
        {p.buoc.map(b => {
          const nhan = nhanThoiLuong(b.thoiLuongMs)
          const phanTram = lauNhat > 0 && b.thoiLuongMs !== null
            ? Math.max(4, Math.round((b.thoiLuongMs / lauNhat) * 100)) : 0
          return (
            <tr key={b.nodeId} data-node-status={b.status}
                data-waiting-kind={b.waitingKind || undefined}
                data-chon={b.nodeId === p.dangChon || undefined}>
              <td className="run-timeline-ten">
                <span className="run-timeline-thanh" aria-hidden="true"
                      style={phanTram ? { width: `${phanTram}%` } : undefined}/>
                <button type="button" onClick={() => p.chon(b.nodeId)}
                        aria-expanded={b.nodeId === p.dangChon}>{b.ten}</button>
              </td>
              {/* ⛔ `—` chu KHONG `0s` khi khong do duoc — xem chu thich dau tep. */}
              <td className="run-timeline-thoi-luong">
                {nhan ?? <span title="Lượt chạy chưa cho đủ mốc để đo bước này">—</span>}
              </td>
              <td className="run-timeline-chi-phi">{b.chiPhi} credit</td>
              <td className="run-timeline-trang-thai">
                <span>{b.nhanTrangThai}</span>
                {b.lyDoCho && <> ({b.lyDoCho})</>}
              </td>
              <td className="run-timeline-attempt">Lần {b.lanThu}</td>
              <td>
                {p.xong && p.onChayLaiTu &&
                  <button type="button" onClick={() => p.onChayLaiTu!(b.nodeId)}>
                    Chạy lại từ đây
                  </button>}
              </td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}
