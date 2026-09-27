import { createRoot } from 'react-dom/client'
// 🔴 `canvas.css` LA BAT BUOC. Mot ban nhap cua tep nay lam roi dong import
//    nay, va hop thu van chay: React ve du moi phan tu, phep nghiem thu van
//    PASS. Nhung `getComputedStyle(shell).getPropertyValue('--text-primary')`
//    tra RONG — tuc trang do ⛔ khong co MOT token nao, khong nen ngan keo,
//    khong be rong 390px that. Moi ket luan ve bo cuc va mau tren trang ay la
//    ket luan ve mot trang KHONG AI co. Do la hang loi "doc thu DAI DIEN".
import '../../src/canvas.css'
import { ExecutionPanel } from '../../src/features/editor/ExecutionPanel'
import type { BangDinhNghia } from '../../src/features/editor/graph'
import type { CanvasNode, CanvasPage } from '../../src/workflowApi'
import { GIA_MOI_BUOC, TEN_BUOC, runDuHinhDang, thamSoGia } from '../runGia'

/** Hộp thử: ⭐ MOUNT CHÍNH `ExecutionPanel`, dữ liệu từ `tests/runGia.ts`.
 *
 * ⛔ KHÔNG dựng lại bố cục ngăn kéo bằng tay ở đây. Bản nháp đầu của tệp này
 *    làm đúng thế — tự viết `<nav class="operation-drawer">` rồi gắn từng mảnh
 *    vào — và nó đo một cách xếp mà người dùng ⛔ không bao giờ thấy: nó không
 *    chứng minh được `ExecutionPanel` gỡ hàng 7 nút, cũng không chứng minh được
 *    báo giá nằm TRƯỚC nút trong bố cục THẬT. Một bản sao bố cục là một bản sao
 *    sẽ trôi.
 *
 * ## ⭐ Vì sao hộp thử, ⛔ không phải máy chủ cô lập dựng bản build
 *
 * Máy chủ cô lập (`tests/browser/agent_ui_v2_ui0_may_chu.py`) phục vụ bản ĐÃ
 * DỰNG ở `server/static/agent-canvas/`, và `vite.config.ts` đặt
 * `emptyOutDir: true` cho thư mục ấy. Thư mục đó là **sổ dùng chung** của các
 * làn đang chạy song song (UI-4, UI-1) và nằm ngoài quyền sở hữu của làn UI-7
 * ⇒ một lần `vite build` để xem giao diện của mình sẽ **xoá bản dựng của làn
 * khác**. Hộp thử dưới `vite dev` đọc NGUỒN, nên không chạm vào sổ ấy.
 *
 * `?run=1` bật lượt chạy; ⛔ không có nó thì panel ở pha TRƯỚC KHI CHẠY (báo
 * giá + nút "Chạy ngay") — hai pha ấy loại trừ nhau trong chính `ExecutionPanel`.
 */
const run = runDuHinhDang()
const coRun = new URLSearchParams(location.search).has('run')

const node = (id: string, i: number): CanvasNode => ({
  id, type: 'tool', position: { x: 0, y: i * 90 }, label: TEN_BUOC[id],
  data: { tool: 'khoi-thu', params: thamSoGia(id) ?? {} },
})

/** ⭐ `n-cho` CÓ TRONG LƯỢT CHẠY nhưng ⛔ KHÔNG trong `page.nodes` — và đó là
 *  ca thật, không phải một lối tắt của hộp thử.
 *
 *  Một lượt chạy trỏ vào một `version_id` đã chốt; đồ thị đang mở trong trình
 *  soạn thì đi tiếp. Một bước bị XOÁ sau khi lượt chạy ấy khởi động vẫn còn
 *  trong `RunV3.nodes` mà ⛔ không còn nhãn nào để tra. Đó là ca DUY NHẤT làm
 *  `tenBuoc` trả rỗng — `nhanNode` không bao giờ trả rỗng cho một node CÓ trên
 *  canvas (nó lùi về tiêu đề palette rồi tới `data.tool`). Nên nếu hộp thử cho
 *  mọi node của run đều có mặt trên trang, lối lui `Bước N` là **mã không bao
 *  giờ chạy** và phép kiểm nó ⛔ không đo gì.
 */
const VANG_TREN_CANVAS = 'n-cho'

const page: CanvasPage = {
  id: 'page-1', name: 'Page 1',
  nodes: run.nodes.filter(n => n.node_id !== VANG_TREN_CANVAS)
                  .map((n, i) => node(n.node_id, i)),
  edges: [], viewport: { x: 0, y: 0, zoom: 1 },
  frames: [], notes: [], comments: [],
}

const dinhNghia: BangDinhNghia = new Map()
const khong = () => {}

/* 🔴 `.canvas-toolbar` LA BAT BUOC, ⛔ khong phai trang tri.
 *
 * `canvas.css` neo moi quy tac bo cuc cua ngan keo vao `.canvas-toolbar >
 * .operation-drawer.is-open` — be rong `min(390px, 100vw - 72px)`, luoi hai
 * cot, chieu cao toi da. Ban nhap dau cua hop thu quen lop ay, nen ngan keo
 * trai rong het 1440px: dong thoi gian gian ra gap bon lan be rong that va anh
 * chup nghiem thu cho thay mot bo cuc ⛔ KHONG AI nhin thay. Do la dung hang
 * loi "doc thu DAI DIEN thay vi doc thu that". */
createRoot(document.getElementById('hop-thu')!).render(
  <section className="canvas-shell theme-dark" aria-label="Hộp thử mặt thực thi">
   <header className="canvas-toolbar">
    <ExecutionPanel dangMo moNgan={khong} page={page} dinhNghia={dinhNghia}
      liveQuotes={GIA_MOI_BUOC}
      workflow={{ id: 'w-gia', name: 'Hộp thử', status: 'draft', revision: 1,
        estimated: 0, canvas: { version: 2, goal: '', budget_max_credit: 0,
        active_page_id: 'page-1', pages: [page] } }}
      phase="ready" readOnly={false} run={coRun ? run : null}
      runError="" runGoc={null} runDaXong={coRun} dangGui={false}
      soSanh={null} soSanhLoi=""
      chayWorkflow={khong} huyRun={khong} chayLaiTuNode={khong}
      soSanhVoiGoc={khong} taoBanChayMoi={khong}/>
   </header>
  </section>,
)
