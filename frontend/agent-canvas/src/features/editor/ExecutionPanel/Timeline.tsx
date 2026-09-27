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
      <caption className="run-an-nhin">Dòng thời gian các bước của lượt chạy</caption>
      {/* ⭐ `<colgroup>`, ⛔ KHONG dat be rong tren `<td>`.
          Voi `table-layout: fixed`, trinh duyet lay be rong cot tu HANG DAU
          (hoac tu `<colgroup>`) va BO QUA moi be rong khai o `<td>` cac hang
          sau. Ban truoc khai `width` tren class cua `<td>` nen khong cot nao
          nhan duoc so nao: ca sau cot tut ve 29px (do 28/09). */}
      <colgroup>
        <col className="run-col-ten"/><col className="run-col-thoi-luong"/>
        <col className="run-col-chi-phi"/><col className="run-col-trang-thai"/>
        <col className="run-col-attempt"/><col className="run-col-thao-tac"/>
      </colgroup>
      <thead>
        <tr><th scope="col">Bước</th><th scope="col">Thời lượng</th>
          <th scope="col">Chi phí</th><th scope="col">Trạng thái</th>
          <th scope="col">Lần thử</th><th scope="col"><span className="run-an-nhin">Thao tác</span></th></tr>
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
              {/* ⭐ Dang CHO thi hien LY DO cho, ⛔ khong hien ca
                  "Đang chờ tín hiệu (chờ người duyệt)" — 37 ky tu trong mot cot
                  ~85px lam hang phinh len 139px (do 28/09 tren trinh duyet
                  that). Ly do la phan mang tin: "cho nguoi duyet" va "cho
                  webhook" doi hoi hai hanh dong khac nhau, con "dang cho tin
                  hieu" thi khong noi gi ma trang thai chua noi. Inspector van
                  hien CA HAI truong rieng. */}
              <td className="run-timeline-trang-thai">
                <span>{b.lyDoCho || b.nhanTrangThai}</span>
              </td>
              <td className="run-timeline-attempt">Lần {b.lanThu}</td>
              {/* ⭐ BIEU TUONG + `aria-label`, ⛔ khong phai 4 chu tren moi hang.
                  Ngan keo chi rong 390px va nut nay lap lai o MOI hang: dang
                  chu day no chiem mot cot rieng, day "Trang thai" xuong 6 dong
                  (do 28/09 tren trinh duyet that). Ten tro nang GIU NGUYEN, nen
                  ban phim va trinh doc man hinh ⛔ khong mat gi. */}
              <td className="run-timeline-thao-tac">
                {p.xong && p.onChayLaiTu &&
                  <button type="button" aria-label="Chạy lại từ đây"
                          title="Chạy lại từ đây"
                          onClick={() => p.onChayLaiTu!(b.nodeId)}>↻</button>}
              </td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}
