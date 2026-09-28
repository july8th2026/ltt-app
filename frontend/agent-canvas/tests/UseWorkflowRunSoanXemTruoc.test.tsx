// UI-8b (vá B7, `02_SCORECARD.md`): "Soạn bằng AI" (`soanBangAI`) KHÔNG còn
// ghi đè canvas ngay — nó tính diff rồi chờ `apDungSoan`/`huySoan`. Bài này
// canh đúng CHỖ dễ vỡ nhất: `huySoan` phải là ngã rẽ duy nhất KHÔNG chạm
// `document`, và điều đó chỉ có nghĩa nếu có một phép TIÊM LỖI chứng minh nó
// bắt được — xem khối "ĐỐI CHỨNG" cuối tệp và báo cáo đi kèm.
import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useWorkflowRun } from '../src/features/editor/hooks/useWorkflowRun'
import * as api from '../src/workflowApi'
import type { BangDinhNghia } from '../src/features/editor/graph'
import type { CanvasDocument, CanvasDocumentV3, KetQuaSoan, Workflow } from '../src/workflowApi'

afterEach(() => vi.restoreAllMocks())

const BANG: BangDinhNghia = new Map()

const WF: Workflow = { id: 'w1', name: 'wf', status: 'draft', revision: 1,
  estimated: 0, canvas: null as unknown as CanvasDocument }

const DOC_CU: CanvasDocument = { version: 2, goal: 'Làm video mèo', budget_max_credit: 0,
  active_page_id: 'p1', pages: [{ id: 'p1', name: 'Trang 1',
    nodes: [{ id: 'n1', type: 'tool', position: { x: 0, y: 0 }, data: { tool: 'text.summarize' } }],
    edges: [], viewport: { x: 0, y: 0, zoom: 1 }, frames: [], notes: [], comments: [] }] }

const DOC_MOI_V3: CanvasDocumentV3 = { version: 3, goal: 'Làm video mèo', budget_max_credit: 0,
  active_page_id: 'p1', pages: [{ id: 'p1', name: 'Trang 1',
    nodes: [
      { id: 'n1', type: 'tool', position: { x: 0, y: 0 }, data: { tool: 'text.summarize' } },
      { id: 'n2', type: 'tool', position: { x: 1, y: 1 }, data: { tool: 'video.generate' } },
    ], edges: [], viewport: { x: 0, y: 0, zoom: 1 }, frames: [], notes: [], comments: [] }] }

const KET_QUA_SOAN: KetQuaSoan = { workflow_id: 'w1', revision: 7,
  document: DOC_MOI_V3, hop_le: true, loi: [], bao_gia: null }

function dungCu() {
  const napTaiLieu = vi.fn()
  const setWorkflow = vi.fn()
  const setPhase = vi.fn()
  const moNgan = vi.fn()
  const { result } = renderHook(() => useWorkflowRun({
    workflow: WF, setWorkflow, document: DOC_CU, csrf: 'csrf-1', readOnly: false,
    setPhase, moNgan, autosaveTimer: { current: undefined }, napTaiLieu, dinhNghia: BANG,
  }))
  return { result, napTaiLieu, setWorkflow }
}

async function soanXong(result: ReturnType<typeof dungCu>['result']) {
  act(() => { void result.current.soanBangAI() })
  await waitFor(() => expect(result.current.soanXemTruoc).not.toBeNull())
}

describe('useWorkflowRun — UI-8b xem trước trước khi ghi đè', () => {
  it('soanBangAI tính XONG rồi chờ ở soanXemTruoc — ⛔ KHÔNG gọi napTaiLieu ngay', async () => {
    vi.spyOn(api, 'soanWorkflowV3').mockResolvedValue(KET_QUA_SOAN)
    const { result, napTaiLieu } = dungCu()
    await soanXong(result)
    expect(napTaiLieu).not.toHaveBeenCalled()
    expect(result.current.soanXemTruoc?.diff.soNodeThem).toBe(1)
    expect(result.current.soanXemTruoc?.diff.soNodeXoa).toBe(0)
    expect(result.current.soanXemTruoc?.revision).toBe(7)
  })

  it('apDungSoan ⇒ napTaiLieu gọi ĐÚNG MỘT LẦN với tài liệu mới, và cập nhật revision', async () => {
    vi.spyOn(api, 'soanWorkflowV3').mockResolvedValue(KET_QUA_SOAN)
    const { result, napTaiLieu, setWorkflow } = dungCu()
    await soanXong(result)
    act(() => result.current.apDungSoan())
    expect(napTaiLieu).toHaveBeenCalledTimes(1)
    const taiLieuDaNap = napTaiLieu.mock.calls[0][0] as CanvasDocument
    expect(taiLieuDaNap.pages[0].nodes.map(n => n.id)).toEqual(['n1', 'n2'])
    // `revision` phải theo cùng đường setWorkflow cũ dùng — kiểm qua updater.
    const capNhat = setWorkflow.mock.calls[0][0] as (w: Workflow) => Workflow
    expect(capNhat(WF).revision).toBe(7)
    expect(result.current.soanXemTruoc).toBeNull()
  })

  it('🔴 CHỐT — huySoan ⇒ napTaiLieu ⛔ KHÔNG BAO GIỜ được gọi, đồ thị đang dựng y nguyên', async () => {
    vi.spyOn(api, 'soanWorkflowV3').mockResolvedValue(KET_QUA_SOAN)
    const { result, napTaiLieu, setWorkflow } = dungCu()
    await soanXong(result)
    act(() => result.current.huySoan())
    expect(napTaiLieu).not.toHaveBeenCalled()
    expect(setWorkflow).not.toHaveBeenCalled()
    expect(result.current.soanXemTruoc).toBeNull()
  })

  it('hop_le=false ⇒ soanLoi vẫn hiện NGAY (như hành vi trước UI-8b), độc lập với Áp dụng/Huỷ', async () => {
    vi.spyOn(api, 'soanWorkflowV3').mockResolvedValue({ ...KET_QUA_SOAN, hop_le: false,
      loi: [{ ma: 'khong_bao_gia_duoc', node_id: '', thong_diep: 'Không báo giá được.' }] })
    const { result, napTaiLieu } = dungCu()
    await soanXong(result)
    expect(result.current.soanLoi).toBe('Không báo giá được.')
    expect(napTaiLieu).not.toHaveBeenCalled() // vẫn phải qua Áp dụng như mọi lượt khác
  })
})

// ── ĐỐI CHỨNG (bắt buộc, xem báo cáo) ──────────────────────────────────────
//
// Bài "huySoan ⇒ napTaiLieu KHÔNG BAO GIỜ được gọi" ở trên chỉ đáng tin nếu nó
// THẬT SỰ đỏ khi hành vi hỏng. Phép tiêm: sửa tạm `huySoan` trong
// `useWorkflowRun.ts` thành
//   const huySoan = useCallback(() => {
//     if (soanXemTruoc) ts.napTaiLieu(soanXemTruoc.taiLieuMoi)
//     setSoanXemTruoc(null)
//   }, [soanXemTruoc, ts])
// rồi chạy lại CHÍNH bài trên — kết quả tiêm được ghi trong báo cáo cuối
// phiên (chạy thật, không suy diễn), sau đó bản sửa tạm bị revert.
