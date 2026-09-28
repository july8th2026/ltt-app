import type { RunV3, RunV3Event, RunV3Node } from '../src/workflowApi'

/** ⭐ CỬA ĐẶT TRẠNG THÁI — dựng một `RunV3` GIẢ đủ mọi hình dạng cần đo.
 *
 * ## Vì sao cửa này là việc ĐẦU TIÊN của làn UI-7, không phải việc cuối
 *
 * Hai dữ kiện đo được, cộng dồn, khoá đường "chạy một workflow thật rồi xem":
 *
 *   1. Worker nạp mã từ `nssm get LTTStudioWorker AppDirectory` =
 *      `C:\LTTPlatform\app` — tức **bản ĐÃ DEPLOY**. Một job thật đo bản deploy,
 *      ⛔ không đo nhánh này.
 *   2. Worker chạy dưới `LocalSystem`, PATH khác hẳn phiên người dùng.
 *
 * ⇒ Chạy thật cho số THẬT nhưng trả lời **câu khác**. Việc của làn UI-7 là lớp
 *   TRÌNH BÀY, nên phép đo đúng là: bơm một `RunV3` có hình dạng đã biết vào
 *   đúng các component ấy, rồi kiểm giao diện vẽ ra gì.
 *
 * ## Tệp này ở `tests/`, ⛔ KHÔNG ở `src/`
 *
 *   - `src/` là thứ đi vào bản dựng của khách. Một bộ dựng run giả trong đó là
 *     một cửa hậu đặt trạng thái trên production, ⛔ không phải một tiện ích.
 *   - `test_967` quét MỌI chuỗi hình dạng `<mien>.<hanh_dong>` trong `src/` và
 *     `DA_CHET` nay RỖNG. Tên tool giả (`app.text.chat`…) trong `src/` làm bánh
 *     cóc ấy đỏ ngay.
 *
 * Kịch bản trình duyệt nạp cùng tệp này (`tests/harness/`), nên hình dạng đo ở
 * vitest và hình dạng đo trên layout thật là MỘT — ⛔ không hai bộ dữ liệu trôi
 * khỏi nhau.
 */

const T0 = '2026-09-28T09:00:00+00:00'

/** `+giay` giây sau `T0`, dạng ISO — để mốc trong fixture đọc được bằng mắt. */
export const luc = (giay: number) =>
  new Date(Date.parse(T0) + giay * 1000).toISOString().replace('.000Z', '+00:00')

export function nodeGia(p: Partial<RunV3Node> & { node_id: string }): RunV3Node {
  return { status: 'PENDING', attempt: 0, cost_credit: 0, job_id: '', error: '',
           waiting_kind: '', het_han: false, ...p }
}

export function suKienGia(p: Partial<RunV3Event> & { seq: number; loai: string }): RunV3Event {
  return { node_id: '', du_lieu: {}, created_at: luc(p.seq), ...p }
}

export function runGia(p: Partial<RunV3> = {}): RunV3 {
  return { id: 'r-gia', workflow_id: 'w-gia', version_id: 'v-gia',
           status: 'RUNNING', credit_max: 20, credit_charged: 4, settled: false,
           created_at: T0, nodes: [], su_kien: [], seq_cuoi: 0, ...p }
}

/** Lượt chạy ĐỦ HÌNH DẠNG mà tiêu chí nghiệm thu của làn đòi:
 *
 *   - nhiều bước, để dòng thời gian có gì mà xếp;
 *   - một bước `FAILED` kèm lỗi dạng `<ma>: <chi tiet>` (kiểm câu người đọc);
 *   - một bước `WAITING` kèm `waiting_kind` (kiểm "lý do chờ");
 *   - một bước `attempt > 1` (kiểm "lần thử" và "lịch sử thử lại");
 *   - một bước có ≥ 2 sự kiện riêng (thời lượng ĐO ĐƯỢC) và một bước không có
 *     sự kiện nào (thời lượng KHÔNG đo được) — hai ca này phải hiện KHÁC nhau;
 *   - một sự kiện mang `node_id` trong `du_lieu` thay vì ở cột riêng
 *     (`tac_tu.py` ghi `AgentStep` như vậy).
 */
export function runDuHinhDang(): RunV3 {
  return runGia({
    status: 'FAILED', credit_charged: 7, credit_max: 20,
    nodes: [
      nodeGia({ node_id: 'n-sheet', status: 'SUCCEEDED', attempt: 1, cost_credit: 0,
                job_id: 'job-sheet' }),
      nodeGia({ node_id: 'nmujtmc1b-0', status: 'SUCCEEDED', attempt: 3,
                cost_credit: 3, job_id: 'job-anh' }),
      nodeGia({ node_id: 'n-video', status: 'WAITING', attempt: 1, cost_credit: 4,
                job_id: 'job-video', waiting_kind: 'HUMAN' }),
      nodeGia({ node_id: 'n-dang', status: 'FAILED', attempt: 1,
                error: 'credential_loi: thieu access_token' }),
      nodeGia({ node_id: 'n-cho', status: 'PENDING' }),
    ],
    su_kien: [
      suKienGia({ seq: 1, loai: 'WorkflowStarted', du_lieu: { inputs: { chu_de: 'thu' } } }),
      suKienGia({ seq: 2, loai: 'BudgetChecked', node_id: 'n-sheet' }),
      suKienGia({ seq: 3, loai: 'SupervisorDecision', node_id: 'n-sheet' }),
      suKienGia({ seq: 4, loai: 'WaitpointOpened', node_id: 'n-video' }),
      // `node_id` trong `du_lieu`, KHONG o cot rieng — xem `buocCuaRun.ts`.
      suKienGia({ seq: 16, loai: 'AgentStep', du_lieu: { node_id: 'nmujtmc1b-0', buoc: 0 } }),
      suKienGia({ seq: 17, loai: 'AgentStep', du_lieu: { node_id: 'nmujtmc1b-0', buoc: 1 } }),
      suKienGia({ seq: 30, loai: 'WorkflowFailed', du_lieu: { status: 'FAILED' } }),
    ],
    seq_cuoi: 30,
  })
}

/** Tên bước cho `runDuHinhDang` — đóng vai `graph.ts::nhanNode` trong phép đo.
 *
 * ⚠️ `n-cho` KHÔNG có tên: đó là ca một node vừa bị xoá khỏi đồ thị giữa hai
 *    version. Giao diện phải lùi về `Bước N`, ⛔ KHÔNG về `node_id`.
 */
export const TEN_BUOC: Record<string, string> = {
  'n-sheet': 'Lấy dòng Sheet',
  'nmujtmc1b-0': 'Tạo ảnh AI',
  'n-video': 'Tạo video',
  'n-dang': 'Đăng YouTube',
}

export const tenBuocGia = (nodeId: string) => TEN_BUOC[nodeId] ?? ''

/** Báo giá mỗi bước của `runDuHinhDang` — dạng của `useLiveQuote` (node_id ->
 *  credit). Tổng = 12; ⭐ `0` là một cái giá THẬT, ⛔ không phải "chưa có giá",
 *  nên nó phải nằm trong bảng. */
export const GIA_MOI_BUOC: Record<string, number> = {
  'n-sheet': 0, 'nmujtmc1b-0': 3, 'n-video': 8, 'n-dang': 1, 'n-cho': 0,
}

export const thamSoGia = (nodeId: string) =>
  nodeId === 'nmujtmc1b-0'
    ? { prompt: 'mot con meo', so_anh: 2, kich_thuoc: { rong: 1024, cao: 1024 } }
    : undefined
