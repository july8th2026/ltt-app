import { useMemo, useRef } from 'react'
import { RunDiff } from '../../../RunDiff'
import { RunInspector } from '../../../RunInspector'
import { RunV3Panel } from '../../../RunV3Panel'
import '../../../styles/run.css'
import type { CanvasPage, RunV3, SoSanhRunV3, Workflow } from '../../../workflowApi'
import { nhanNode, type BangDinhNghia } from '../graph'
import { useFocusTrap } from '../hooks/useFocusTrap'
import type { PhaLuu, NganDesktop } from '../kieu'
import { BaoGiaTruocKhiChay } from './BaoGiaTruocKhiChay'
import { DuyetNguoi } from './DuyetNguoi'

type Props = {
  moNgan: (ngan: NganDesktop) => void
  dangMo: boolean
  page: CanvasPage
  /** Bảng định nghĩa palette — nguồn của TÊN BƯỚC khi node chưa được đặt nhãn. */
  dinhNghia: BangDinhNghia
  /** `node_id` -> credit tối đa (`hooks/useLiveQuote.ts`). */
  liveQuotes: Record<string, number>
  workflow: Workflow | undefined
  phase: PhaLuu
  readOnly: boolean
  run: RunV3 | null
  runError: string
  runGoc: RunV3 | null
  runDaXong: boolean
  dangGui: boolean
  soSanh: SoSanhRunV3 | null
  soSanhLoi: string
  chayWorkflow: () => void
  huyRun: () => void
  chayLaiTuNode: (nodeId: string) => void
  soSanhVoiGoc: () => void
  taoBanChayMoi: () => void
}

/** Ngăn kéo "Chạy workflow" — và ⭐ CHỈ nói về chạy.
 *
 *  ## 🔴 Bảy nút đã rời khỏi đây, và vì sao đó là một lỗi chứ không phải gu
 *
 *  Ngăn kéo này từng chứa *Nhân bản · Xóa · Nhánh · Tự xếp · Lớp · Lưới ·
 *  Đường nối · Bản đồ* — **7/8 điều khiển là lệnh SỬA hoặc XEM**, trong một
 *  ngăn tên là "Chạy workflow" (`01_CURRENT_UI_AUDIT.md §6`). Chúng đã về đúng
 *  chỗ: `CommandPalette` (nhân bản · xoá · nhánh lỗi · tự xếp · ba công tắc
 *  hiển thị) và `LeftRail` (Lớp). ⛔ Không cái nào bị xoá — mỗi lệnh vẫn còn
 *  bàn phím (`useEditorShortcuts`) và/hoặc menu ngữ cảnh như trước.
 *
 *  ## 🔴 Và một con số xuất hiện TRƯỚC khi tiêu tiền
 *
 *  Chỗ của 7 nút ấy giờ là `BaoGiaTruocKhiChay`. Trước đây người dùng được mời
 *  bấm "Chạy ngay" — hành động **trừ credit** — mà dòng duy nhất về tiền là một
 *  lời hứa (*"server chốt chi phí tối đa khi publish"*). `liveQuotes` đã có sẵn
 *  trong bộ nhớ trình soạn suốt thời gian đó.
 *
 *  ⛔ 01b chay CA do thi da publish: khong con chon pham vi, khong con
 *     `use_cache`, khong con buoc duyet bao gia — ba thu ay la ngu nghia cua
 *     Plan v1. May chu chot `credit_max` ngay luc publish.
 */
export function ExecutionPanel(p: Props) {
  // Ngan nay LUON gan trong DOM (an/hien bang CSS `is-open`, xem canvas.css) —
  // bay focus chi BAT khi dang mo, keo khong thi no khoa Tab ca luc an.
  const ngan = useRef<HTMLElement>(null)
  useFocusTrap(ngan, p.dangMo)
  // TÊN BƯỚC cho dòng thời gian và nhật ký. `nhanNode` là CÙNG hàm mà bảng
  // "Lớp" và menu ngữ cảnh dùng ⇒ một bước có MỘT tên trên khắp giao diện.
  const tenBuoc = useMemo(() => {
    const bang = new Map(p.page.nodes.map(node =>
      [node.id, nhanNode(node, p.page.nodes, p.dinhNghia)]))
    return (nodeId: string) => bang.get(nodeId) ?? ''
  }, [p.page.nodes, p.dinhNghia])
  const thamSo = useMemo(() => {
    const bang = new Map(p.page.nodes.map(node =>
      [node.id, (node.data.params ?? {}) as Record<string, unknown>]))
    return (nodeId: string) => bang.get(nodeId)
  }, [p.page.nodes])
  // `output_ref` chi ton tai o cua SO SANH; lay tu phia `b` (luot dang xem).
  const dauRa = useMemo(() => {
    const bang = new Map((p.soSanh?.b.nodes ?? [])
      .map(node => [node.node_id, node.output_ref]))
    return (nodeId: string) => bang.get(nodeId)
  }, [p.soSanh])

  return <nav ref={ngan} className={`operation-drawer${p.dangMo?' is-open':''}`} aria-label="Chạy workflow"><header><strong>Chạy workflow</strong><button aria-label="Đóng bảng chạy" onClick={()=>p.moNgan(null)}>×</button></header>
    {/* ⭐ Bao gia TRUOC nut, khong sau: nguoi ta doc tu tren xuong, va quyet
        dinh tieu tien duoc dua o dong ngay tren cai nut. */}
    {!p.run&&<BaoGiaTruocKhiChay liveQuotes={p.liveQuotes}
      nodeIds={p.page.nodes.map(node=>node.id)}/>}
    {/* Nhan doi theo `dangGui`: nuot im lang lan bam thu hai chi lam nguoi
        dung bam them nua. Ho phai THAY lang minh da di. */}
    {!p.run&&<button className="run-confirm" aria-busy={p.dangGui||undefined}
      disabled={p.readOnly||!p.workflow||!p.page.nodes.length||p.phase==='saving'||p.dangGui}
      onClick={p.chayWorkflow}>{p.dangGui?'Đang gửi…':'Chạy ngay'}</button>}
    {p.runDaXong&&<button onClick={p.taoBanChayMoi}>Tạo bản chạy mới</button>}
    {/* Task UI-8a — TRÊN dòng thời gian: đây là hành động khẩn, không phải
        một dòng lịch sử để cuộn tới. */}
    {/* ⛔ KHONG truyen `thamSo`: cau hoi duyet den tu payload cua RUN (ban da
        ghim), ⛔ khong tu ban nhap. Xem `DuyetNguoi.tsx` + `test_5605`. */}
    <DuyetNguoi run={p.run} tenBuoc={tenBuoc}/>
    <RunV3Panel run={p.run} onCancel={p.huyRun} onChayLaiTu={p.chayLaiTuNode}
      tenBuoc={tenBuoc} thamSo={thamSo} dauRa={dauRa}/>
    {p.runError && <span className="run-error" role="alert">{p.runError}</span>}
    {/* Task A2 — nguồn của cặp so sánh la (run cũ, run "chạy lại từ" nó);
        xem chú thích ở khai báo `runGoc`. */}
    {p.run&&p.runGoc&&p.runDaXong&&<button onClick={p.soSanhVoiGoc}>So sánh với lượt gốc</button>}
    {p.soSanhLoi && <span className="run-error" role="alert">{p.soSanhLoi}</span>}
    {p.soSanh && <RunDiff soSanh={p.soSanh}/>}
    {/* Cay JSON tho — GAP LAI. Loi thoat cho nguoi di go loi, ⛔ khong con la
        be mat chinh: xem chu thich dau `RunInspector.tsx`. */}
    <RunInspector run={p.run}/></nav>
}
