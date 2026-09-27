type Props = {
  /** `node_id` -> credit tối đa, từ `useLiveQuote` (một cửa cho CẢ đồ thị). */
  liveQuotes: Record<string, number>
  /** Các `node_id` của trang đang chạy — mẫu số của phép cộng. */
  nodeIds: string[]
}

/** BÁO GIÁ hiện TRƯỚC khi bấm "Chạy ngay".
 *
 *  ## 🔴 Vì sao đây không phải một thứ trang trí
 *
 *  Trước lần này, ngăn kéo mời người dùng bấm một nút **tiêu tiền** và dòng duy
 *  nhất về tiền là *"server chốt chi phí tối đa khi publish"* — một câu HỨA,
 *  ⛔ không một con số. `liveQuotes` đã nằm sẵn trong bộ nhớ trình soạn
 *  (`hooks/useLiveQuote.ts`, cùng cửa `bao-gia` mà chân Inspector đang dùng cho
 *  MỘT node) — nó chỉ chưa được cộng lại và chưa được hiện ở chỗ người ta quyết.
 *
 *  ## ⭐ "Chưa đủ giá" ≠ "0 credit"
 *
 *  `useLiveQuote` XOÁ cả bảng khi cửa báo giá hỏng, và bảng cũng trống trong
 *  450 ms debounce đầu. Cộng một bảng thiếu rồi in tổng là hứa một cái giá
 *  KHÔNG có thật — đúng hạng lỗi "màn hình nói sai" về tiền. Nên: đếm số node
 *  CÓ giá, và khi chưa đủ thì nói rõ là chưa đủ, ⛔ không in một con số.
 */
export function BaoGiaTruocKhiChay({ liveQuotes, nodeIds }: Props) {
  const coGia = nodeIds.filter(id => typeof liveQuotes[id] === 'number')
  const tong = coGia.reduce((sum, id) => sum + liveQuotes[id], 0)
  const duGia = nodeIds.length > 0 && coGia.length === nodeIds.length
  return (
    <section className="run-bao-gia" aria-label="Báo giá trước khi chạy">
      <small>CHI PHÍ TỐI ĐA</small>
      {duGia
        ? <strong data-bao-gia-tong={tong}>{tong} credit</strong>
        : <strong data-bao-gia-tong="">Chưa tính đủ giá</strong>}
      <span>
        {duGia
          ? <>cho {nodeIds.length} bước · máy chủ chốt đúng con số này khi publish</>
          : <>đã có giá {coGia.length}/{nodeIds.length} bước — con số đầy đủ hiện ngay khi báo giá về</>}
      </span>
    </section>
  )
}
