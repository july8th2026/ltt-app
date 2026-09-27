import { createRoot } from 'react-dom/client'
import '../../src/canvas.css'
import '../../src/styles/run.css'
import { RunV3Panel } from '../../src/RunV3Panel'
import { BaoGiaTruocKhiChay } from '../../src/features/editor/ExecutionPanel/BaoGiaTruocKhiChay'
import { runDuHinhDang, tenBuocGia, thamSoGia } from '../runGia'

/** Hộp thử: đúng các component của mặt thực thi, dữ liệu từ `tests/runGia.ts`.
 *
 * ⛔ KHÔNG dựng lại bố cục của `ExecutionPanel` bằng tay ở đây — chỉ bọc lớp
 *    `.operation-drawer.is-open` để các quy tắc lưới của `canvas.css` có hiệu
 *    lực. Một bản sao bố cục là một bản sao sẽ trôi, và rồi hộp thử sẽ báo xanh
 *    cho một cách xếp mà người dùng không bao giờ thấy.
 */
const run = runDuHinhDang()

createRoot(document.getElementById('hop-thu')!).render(
  <section className="canvas-shell theme-dark" aria-label="Hộp thử mặt thực thi">
    <nav className="operation-drawer is-open" aria-label="Chạy workflow">
      <header><strong>Chạy workflow</strong></header>
      <BaoGiaTruocKhiChay nodeIds={run.nodes.map(n => n.node_id)}
        liveQuotes={{ 'n-sheet': 0, 'nmujtmc1b-0': 3, 'n-video': 8,
                      'n-dang': 1, 'n-cho': 0 }}/>
      <button className="run-confirm">Chạy ngay</button>
      <RunV3Panel run={run} onCancel={() => {}} onChayLaiTu={() => {}}
        tenBuoc={tenBuocGia} thamSo={thamSoGia}/>
    </nav>
  </section>,
)
