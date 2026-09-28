/** Lỗi của một bước: từ `<ma_may>: <chi tiet>` thành một CÂU người đọc được.
 *
 *  ## Hình dạng dữ liệu vào
 *
 *  `RunV3Node.error` đến từ `WorkflowNodeExecution.error` và động cơ luôn ghi
 *  nó theo khuôn `"<ma>: <chi tiet>"` — `"node_khong_ton_tai: core.set"`,
 *  `"credential_loi: thieu access_token"`, `"vuot_tran_bao_gia: 31 > 20"`.
 *  Hôm nay giao diện đổ NGUYÊN chuỗi ấy lên màn hình khách.
 *
 *  ## ⭐ Vì sao bảng này KHÔNG phạm luật "đừng tra bảng trong frontend"
 *
 *  Luật ấy (`test_967`) cấm một bảng **tên app/tool**: danh sách công cụ mọc
 *  theo từng app, nên một bảng chép tay trôi khỏi registry trong im lặng.
 *  Tập MÃ LỖI của động cơ thì khác về bản chất — nó là **hợp đồng đóng** của
 *  `platform_core/workflow`, đổi bằng một lần sửa mã có chủ đích.
 *
 *  Và quan trọng hơn: bảng này ⛔ KHÔNG BAO GIỜ được là cửa duy nhất. Mã nào
 *  chưa có câu dịch vẫn ra một câu người đọc được (`CAU_CHUNG`) **cộng** mã máy
 *  ở phần chi tiết kỹ thuật. Một hàng thiếu ở đây làm câu chữ kém hay, ⛔ không
 *  làm mất thông tin — đó là chỗ khác hẳn một bảng tra tên tool, nơi một hàng
 *  thiếu làm nút biến mất.
 */

/** Lỗi đã tách: câu cho NGƯỜI, và phần cho người GỠ LỖI. */
export type LoiDaTach = {
  /** Câu tiếng Việt đầy đủ, không mã máy. Luôn khác rỗng. */
  cau: string
  /** Mã máy (`bieu_thuc_loi`…) hoặc rỗng khi chuỗi gốc không theo khuôn. */
  ma: string
  /** Phần sau dấu `: ` — giữ NGUYÊN VĂN, không dịch, không cắt. */
  chiTiet: string
  /** Chuỗi gốc y như máy chủ trả. Phần "chi tiết kỹ thuật" hiện cái này. */
  tho: string
}

//: mã máy -> câu người đọc được. ⛔ Không nhét chi tiết vào câu: chi tiết đi
//  riêng ở `chiTiet` để dòng đầu luôn đọc được kể cả khi chi tiết là một cây
//  JSON dài.
const CAU_THEO_MA: Record<string, string> = {
  bieu_thuc_loi: 'Một biểu thức trong bước này không tính được.',
  dau_vao_sai: 'Đầu vào của bước này không đúng kiểu hoặc thiếu trường.',
  loi_he_thong: 'Hệ thống gặp sự cố khi chạy bước này, không phải do thiết lập của bạn.',
  node_khong_ton_tai: 'Bước này trỏ tới một khối không còn trong workflow.',
  cong_cu_khong_con: 'Công cụ mà bước này dùng không còn được cung cấp.',
  credential_loi: 'Kết nối (tài khoản/khoá) mà bước này dùng không dùng được.',
  vuot_tran_bao_gia: 'Bước này tốn nhiều credit hơn mức đã chốt cho lượt chạy.',
  vuot_max_items: 'Bước này sinh ra nhiều phần tử hơn mức cho phép.',
  het_han_cho: 'Bước này chờ quá lâu nên đã bị dừng.',
  run_con_loi: 'Một workflow con mà bước này gọi đã hỏng.',
  qua_sau_subworkflow: 'Workflow lồng nhau quá sâu.',
  noi_lai: 'Không nối lại được luồng thi hành sau khi bước này dừng.',
  chia_0: 'Một phép tính trong bước này chia cho 0.',
  json_parse: 'Dữ liệu không phải JSON hợp lệ.',
  to_number: 'Không đổi được giá trị này thành số.',
  to_int: 'Không đổi được giá trị này thành số nguyên.',
  to_bool: 'Không đổi được giá trị này thành đúng/sai.',
}

/** Câu dùng khi mã máy chưa có hàng trong `CAU_THEO_MA` — hoặc không có mã.
 *
 *  ⭐ Nó KHÔNG được là một câu rỗng nghĩa kiểu "Đã xảy ra lỗi". Người đọc phải
 *     biết ngay ba điều: bước nào hỏng (chỗ hiện câu này đã nói), rằng chi tiết
 *     có ở ngay dưới, và rằng họ nên làm gì tiếp.
 */
const CAU_CHUNG = 'Bước này hỏng. Mở "Chi tiết kỹ thuật" để xem mã lỗi gốc.'

//: Mã máy là `snake_case` không dấu, không khoảng trắng. Dùng để phân biệt
//  `"bieu_thuc_loi: ..."` (CÓ mã) với một câu tự do vô tình chứa dấu hai chấm.
const _MA_MAY = /^[a-z][a-z0-9_]*$/

/** `""` -> `null`. Ngược lại luôn trả một `LoiDaTach` có `cau` khác rỗng. */
export function tachLoi(tho: string): LoiDaTach | null {
  const sach = (tho ?? '').trim()
  if (!sach) return null
  const vachNgan = sach.indexOf(': ')
  const dauTien = vachNgan > 0 ? sach.slice(0, vachNgan) : ''
  const coMa = _MA_MAY.test(dauTien)
  const ma = coMa ? dauTien : ''
  const chiTiet = coMa ? sach.slice(vachNgan + 2).trim() : sach
  return { cau: CAU_THEO_MA[ma] ?? CAU_CHUNG, ma, chiTiet, tho: sach }
}

/** Số mã lỗi đã có câu dịch — để một phép kiểm đếm được, ⛔ không phải để
 *  chốt một con số: bảng chỉ được to ra, và `CAU_CHUNG` đỡ phần còn lại. */
export const SO_MA_CO_CAU = Object.keys(CAU_THEO_MA).length
