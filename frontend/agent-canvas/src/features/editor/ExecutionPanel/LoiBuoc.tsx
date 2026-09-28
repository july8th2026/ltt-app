import type { LoiDaTach } from './loiNguoiDoc'

/** Một lỗi, hiện cho NGƯỜI: câu trước, mã máy sau và GẬP LẠI.
 *
 *  🔴 Bản cũ đổ nguyên `"node_khong_ton_tai: core.set"` lên màn hình khách.
 *     Người dùng ⛔ không biết `core.set` là gì, ⛔ không biết mình làm gì sai,
 *     ⛔ không biết nên bấm gì. Mã máy không vô dụng — nó là thứ duy nhất tra
 *     được khi báo lỗi — nên nó ở lại, chỉ là ở SAU một cái gập.
 *
 *  ⭐ `<details>` thuần, ⛔ không tự dựng cơ chế gập bằng `useState`: bàn phím,
 *     trình đọc màn hình và Ctrl+F của trình duyệt đã hiểu `<details>`.
 */
export function LoiBuoc({ loi }: { loi: LoiDaTach }) {
  return (
    <div className="run-loi" data-loi-ma={loi.ma || undefined}>
      <p className="run-loi-cau">{loi.cau}</p>
      <details>
        <summary>Chi tiết kỹ thuật</summary>
        {!!loi.ma && <p>Mã lỗi: <code>{loi.ma}</code></p>}
        {!!loi.chiTiet && <p className="run-loi-chi-tiet"><code>{loi.chiTiet}</code></p>}
      </details>
    </div>
  )
}
