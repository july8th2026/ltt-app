import { useCallback, useRef, useState } from 'react'
import type { CanvasDocument, Workflow } from '../../../workflowApi'
import { cancelRunV3, chayLaiTuNodeV3, createRunV3, fromV3, publishWorkflowV3,
  RUN_V3_KET_THUC, saveWorkflowV3, soanWorkflowV3, soSanhRunV3,
  WorkflowCompileError, WorkflowConflictError,
  type RunV3, type SoSanhRunV3 } from '../../../workflowApi'
import { nhapRun, taoKhoaChay } from '../graph'
import { useRunStream } from './useRunStream'
import type { NganDesktop, PhaLuu } from '../kieu'

type ThamSo = {
  workflow: Workflow | undefined
  setWorkflow: (w: Workflow | ((truoc: Workflow | undefined) => Workflow | undefined)) => void
  document: CanvasDocument
  csrf: string
  readOnly: boolean
  setPhase: (p: PhaLuu) => void
  moNgan: (ngan: NganDesktop) => void
  autosaveTimer: { current: number | undefined }
  napTaiLieu: (document: CanvasDocument) => void
}

/** publish · tạo run · SSE lùi dần · huỷ · chạy lại · so sánh · Soạn bằng AI.
 *
 *  🔴 Ba hành vi tinh vi sống ở đây và ⛔ KHÔNG được đơn giản hoá. Cả ba đều
 *     có phép kiểm trong `tests/CanvasShell.test.tsx`:
 *
 *     1. `dangGuiRun` (ref) chặn bấm đúp. ⛔ Không thay bằng `disabled` của DOM.
 *     2. `khoaChay` (ref) giữ `Idempotency-Key` qua lần thử lại của CÙNG một
 *        lần bấm, và chỉ xoá khi máy chủ đã nhận được run.
 *     3. `soHong`/`lanNoiLai` là hai bộ đếm KHÁC LOẠI — xem chú thích tại chỗ.
 */
export function useWorkflowRun(ts: ThamSo) {
  const [run, setRun] = useState<RunV3 | null>(null)
  const [runError, setRunError] = useState('')
  //: Run mà `run` hiện tại được "Chạy lại từ đây" (task A1). Chỉ tồn tại khi
  //  người dùng đã chạy lại ít nhất một lần — đây cũng là NGUỒN duy nhất cho
  //  "so sánh" (task A2): máy chủ không có cửa liệt kê run theo workflow
  //  (`v3_so_sanh_run` đòi cả hai id), nên cặp (run cũ, run mới) sinh ra từ
  //  chính thao tác chạy lại là chỗ duy nhất trong phạm vi P-A có SẴN hai id
  //  liên quan để so — không bịa thêm một ô nhập id thủ công.
  const [runGoc, setRunGoc] = useState<RunV3 | null>(null)
  const [soSanh, setSoSanh] = useState<SoSanhRunV3 | null>(null)
  const [soSanhLoi, setSoSanhLoi] = useState('')
  //: Task A3 — Agent Designer (`agent_v3.py::v3_soan`). Cửa KHÔNG publish, chỉ
  //  ghi draft + trả báo giá; publish vẫn là hành động riêng của người dùng.
  const [dangSoan, setDangSoan] = useState(false)
  const [soanLoi, setSoanLoi] = useState('')
  //: node_id -> ma loi bien dich (422 `{ma,node_id,thong_diep}` cua publish).
  const [loiNode, setLoiNode] = useState<Record<string, string>>({})
  /** Khoá `Idempotency-Key` của lần bấm "Chạy ngay" đang dở. Rỗng = chưa bấm,
   *  hoặc lần bấm trước đã tạo được run. Xem `chayWorkflow`. */
  const khoaChay = useRef<string>('')
  /** Cờ "ĐANG GỬI một lượt chạy" — bật từ lúc bắt đầu tạo run cho tới khi run
   *  được tạo xong hoặc hỏng.
   *
   *  ⚠️ `Idempotency-Key` và cờ này chữa HAI bệnh khác nhau. Khoá chỉ cứu
   *     *thử lại CÙNG một lần bấm* (mạng đứt): cùng khoá ⇒ máy chủ trả lại
   *     run cũ. **Bấm đúp là hai lần bấm ⇒ hai khoá ⇒ hai run, hai lần giữ
   *     chỗ, hai lần trừ tiền.** Chỉ một chốt ở client chặn được.
   *
   *  ⛔ Vì sao là `ref` chứ không phải chỉ `disabled` của DOM: `disabled` chỉ
   *     có hiệu lực SAU một lượt render, và React bỏ qua sự kiện chuột trên
   *     nút disabled nhưng KHÔNG bỏ qua mọi đường vào khác (phím Enter trên
   *     một điều khiển khác, một lối gọi `chayWorkflow` thêm về sau). Chốt
   *     phải nằm ở tầng logic; `dangGui` bên dưới chỉ để giao diện PHẢN ÁNH
   *     nó. Hai thứ luôn đổi cùng nhau. */
  const dangGuiRun = useRef(false)
  const [dangGui, setDangGui] = useState(false)

  const { datLaiSoHong } = useRunStream(run, setRun, setRunError)

  /** LUU -> PUBLISH -> TAO run. Ba lo phai di dung thu tu: `tao_run` tu choi
   *  mot workflow chua publish (422 `chua_publish`), va publish dong bang
   *  DUNG ban nhap vua luu — nen luu phai xong truoc, khong chay song song. */
  const chayWorkflow = useCallback(async () => {
    const dangChay = run && !RUN_V3_KET_THUC.has(run.status)
    // ⭐ CHOT BAM DUP. Doc ref, khong doc state: state cua lan bam truoc co
    //    the CHUA kip render khi lan bam thu hai toi. Xem `dangGuiRun`.
    if (!ts.workflow || ts.readOnly || dangChay || dangGuiRun.current) return
    dangGuiRun.current = true; setDangGui(true)
    if (ts.autosaveTimer.current) window.clearTimeout(ts.autosaveTimer.current)
    // ⭐ MOT LAN BAM = MOT KHOA. Khoa sinh O DAY, khong sinh trong
    //    `createRunV3`: chi cho nay biet dau la ranh gioi cua "mot lan bam".
    //
    //    Giu trong ref cho toi khi may chu THAT SU nhan duoc run. Neu lo tao
    //    run hong (mang dut, 503) thi lan thu lai — du la nguoi dung tu bam
    //    lai — van mang dung khoa ay, nen mot run da lo tao ben may chu se
    //    duoc tra ve thay vi tao them mot run thu hai va giu cho lan nua.
    //    Thanh cong roi moi xoa khoa ⇒ lan bam KE TIEP la mot khoa moi, va
    //    nguoi dung chay duoc lan thu hai that.
    if (!khoaChay.current) khoaChay.current = taoKhoaChay()
    setRun(null); datLaiSoHong(); ts.moNgan('run'); ts.setPhase('saving'); setRunError(''); setLoiNode({})
    setRunGoc(null); setSoSanh(null); setSoSanhLoi('')
    try {
      const saved = await saveWorkflowV3({ ...ts.workflow, canvas: ts.document }, ts.csrf)
      ts.setWorkflow(saved); ts.setPhase('saved')
      await publishWorkflowV3(saved, ts.csrf)
      const moi = await createRunV3(saved.id, ts.csrf, khoaChay.current)
      khoaChay.current = ''
      setRun(moi)
    } catch (error) {
      if (error instanceof WorkflowCompileError) {
        setRunError(error.message)
        if (error.nodeId) setLoiNode({ [error.nodeId]: error.ma })
      } else if (error instanceof WorkflowConflictError) {
        ts.setPhase('conflict'); setRunError('Workflow vừa đổi ở nơi khác — tải bản mới rồi chạy lại.')
      } else {
        setRunError(error instanceof Error ? error.message : 'Không chạy được.')
      }
    } finally {
      // ⛔ `finally`, khong phai cuoi nhanh `try`: neu co chi duoc ha o duong
      //    THANH CONG thi mot loi 402/503 se khoa nut VINH VIEN va nguoi dung
      //    khong bao gio chay lai duoc. Bai "luot dau HONG roi: bam lai PHAI
      //    gui duoc" giu dung cho nay.
      dangGuiRun.current = false; setDangGui(false)
    }
  }, [run, ts])

  const huyRun = useCallback(() => {
    if (!run) return
    // Cung mot luat nhu vong poll: phan hoi ve muon khong duoc lam song lai
    // mot run da dong, hay de len mot run khac.
    void cancelRunV3(run.id, ts.csrf)
      .then(next => setRun(truoc => truoc && truoc.id === next.id ? nhapRun(truoc, next) : truoc))
      .catch(error => setRunError(error instanceof Error ? error.message : 'Không hủy được.'))
  }, [run, ts.csrf])

  /** Task A1 — chạy lại TỪ MỘT NODE. Tạo run MỚI (khoản giữ mới, tiêu tiền
   *  mới) cùng version, tái dùng output các node không phải hậu duệ của
   *  `nodeId`. `run` cũ trở thành `runGoc` — nguồn cho "So sánh" (task A2). */
  const chayLaiTuNode = useCallback((nodeId: string) => {
    if (!run || !RUN_V3_KET_THUC.has(run.status)) return
    const cu = run
    setRunError(''); setSoSanh(null); setSoSanhLoi('')
    void chayLaiTuNodeV3(run.id, nodeId, ts.csrf, taoKhoaChay())
      .then(moi => { setRunGoc(cu); setRun(moi); datLaiSoHong() })
      .catch(error => setRunError(error instanceof Error ? error.message : 'Không chạy lại được.'))
  }, [run, ts.csrf])

  /** Task A2 — so sánh `run` hiện tại với run nó vừa được chạy lại từ. */
  const soSanhVoiGoc = useCallback(() => {
    if (!run || !runGoc) return
    setSoSanhLoi(''); setSoSanh(null)
    void soSanhRunV3(run.id, runGoc.id)
      .then(setSoSanh)
      .catch(error => setSoSanhLoi(error instanceof Error ? error.message : 'Không so sánh được.'))
  }, [run, runGoc])

  /** Task A3 — Agent Designer (`/soan`). Ghi draft từ `goal` hiện có trên
   *  Canvas rồi NẠP THẲNG tài liệu trả về vào trình soạn — cửa này KHÔNG
   *  publish, người dùng vẫn phải tự bấm "Chạy" để publish + chạy. */
  const soanBangAI = useCallback(() => {
    if (!ts.workflow || ts.readOnly || dangSoan) return
    const goal = ts.document.goal.trim()
    if (!goal) { setSoanLoi('Thiếu mục tiêu.'); return }
    setDangSoan(true); setSoanLoi('')
    void soanWorkflowV3(ts.workflow.id, goal, undefined, ts.csrf)
      .then(kq => {
        ts.napTaiLieu(fromV3(kq.document))
        ts.setWorkflow(truoc => truoc ? { ...truoc, revision: kq.revision } : truoc)
        if (!kq.hop_le && kq.loi.length)
          setSoanLoi(kq.loi.map(l => l.thong_diep).join(' · '))
      })
      .catch(error => setSoanLoi(error instanceof Error ? error.message : 'Không soạn được.'))
      .finally(() => setDangSoan(false))
  }, [ts, dangSoan])

  const taoBanChayMoi = useCallback(() => {
    setRun(null); setRunError(''); datLaiSoHong()
    setRunGoc(null); setSoSanh(null); setSoSanhLoi('')
  }, [])

  return { run, runError, runGoc, soSanh, soSanhLoi, dangSoan, soanLoi, loiNode,
    dangGui, runDaXong: Boolean(run && RUN_V3_KET_THUC.has(run.status)),
    chayWorkflow, huyRun, chayLaiTuNode, soSanhVoiGoc, soanBangAI, taoBanChayMoi }
}
