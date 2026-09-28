// `useExpressionSuggest` ⛔ KHÔNG được trả gợi ý của node CŨ.
//
// ## Làn UI-6 tìm ra, và họ tự vệ ở SAI TẦNG
//
// Họ báo: *"`goiY` không bị xoá khi đổi node chọn, có thể thoáng hiện gợi ý của
// node CŨ (cũng ảnh hưởng `OBieuThuc` của UI-5)"*. Họ tự vệ trong `ChonDuLieu`
// bằng cách so `goiY.node_id` — đúng về kết quả, sai về **chỗ**.
//
// 🔴 Vì sao chỗ quan trọng: hook này có **ít nhất hai** người dùng
//    (`ChonDuLieu` của UI-6, `OBieuThuc` của UI-5), và người thứ ba sẽ ⛔ không
//    biết là phải tự vệ. Một bất biến sống trong ý thức của từng người gọi là
//    một bất biến sẽ mất đúng ở người gọi tiếp theo — cùng hình dạng với ba lần
//    `canvas_to_plan()` đánh rơi cổng.
// ⇒ Bất biến thuộc về **BIÊN**: hook tự lọc, mọi người gọi hưởng miễn phí.
//
// ## Vì sao nó thoáng hiện chứ không hiện mãi
//
// ```
// useEffect(() => {
//   if (!workflow || !selectedNodeId || offline) { setGoiY(undefined); return }
//   ...setTimeout(200ms) -> fetch -> setGoiY(ket)
// }, [workflow?.id, selectedNodeId, document, ...])
// ```
//
// Cờ `active` chặn một lần **GHI** muộn, nhưng ⛔ không xoá **giá trị đang có**.
// Nên khi đổi từ node A sang node B: state vẫn giữ gợi ý của A suốt 200 ms
// debounce + thời gian mạng. ⛔ Nhánh `setGoiY(undefined)` ⛔ không chạy — nó chỉ
// dành cho ca *mất* lựa chọn, ⛔ không cho ca *đổi* lựa chọn.
//
// ⚠️ Và *"thoáng"* ⛔ không làm nó nhẹ hơn: gợi ý dẫn thẳng vào ô tham số. Một cú
//    bấm trong 200 ms ấy chèn một biểu thức trỏ tới node KHÁC — biên dịch có thể
//    sạch (node đó tồn tại thật), nên lỗi chỉ lộ ra lúc chạy, ở một bước đã tính
//    tiền.
import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useExpressionSuggest } from '../src/features/editor/hooks/useExpressionSuggest'
import * as api from '../src/workflowApi'
import type { CanvasDocument, GoiYBieuThuc, Workflow } from '../src/workflowApi'

afterEach(() => { vi.restoreAllMocks(); vi.useRealTimers() })

const WF = { id: 'w1', name: 'w', status: 'draft', revision: 1,
             estimated: 0 } as unknown as Workflow
const DOC = { version: 2, goal: '', budget_max_credit: 0,
              active_page_id: 'p1',
              pages: [{ id: 'p1', name: '', nodes: [], edges: [],
                        viewport: { x: 0, y: 0, zoom: 1 },
                        frames: [], notes: [], comments: [] }],
            } as unknown as CanvasDocument

function goiYCua(nodeId: string): GoiYBieuThuc {
  return { node_id: nodeId, muc: [], ham: [], loi: null }
}

describe('useExpressionSuggest ⛔ khong tra goi y cua node CU', () => {
  it('doi node ⇒ goi y cu bi XOA NGAY, khong cho fetch xong', async () => {
    // Node A tra ve ngay; node B thi treo (mo phong mang cham / debounce).
    let thaB: ((g: GoiYBieuThuc) => void) | null = null
    vi.spyOn(api, 'goiYBieuThuc').mockImplementation(
      async (_w: string, nodeId: string) => {
        if (nodeId === 'a') return goiYCua('a')
        return new Promise<GoiYBieuThuc>(res => { thaB = res })
      })

    const { result, rerender } = renderHook(
      ({ id }: { id: string }) =>
        useExpressionSuggest(WF, id, DOC, 'csrf', false),
      { initialProps: { id: 'a' } })

    await waitFor(() => expect(result.current?.node_id).toBe('a'))

    // Đổi sang B. B chưa trả về ⇒ ⛔ KHONG duoc con thay goi y cua A.
    rerender({ id: 'b' })
    expect(result.current).toBeUndefined()

    // B tra ve ⇒ moi hien, va hien dung cua B.
    //
    // ⚠️ PHAI cho `thaB` duoc gan truoc da. Lan dau toi goi `thaB?.(...)` ngay
    //    sau `rerender`, tuc TRUOC khi debounce 200 ms kip tao request cho B —
    //    nen `thaB` con `null` va dau `?.` **im lang khong lam gi**, roi
    //    `waitFor` het gio. Bai do vi loi cua phep do, ⛔ khong vi san pham.
    // ⭐ Dau `?.` la mot cho rat de nuot mot buoc: no bien "chua co" thanh
    //    "khong lam gi" ma ⛔ khong mot tin hieu nao.
    await waitFor(() => expect(thaB).not.toBeNull())
    await act(async () => { thaB!(goiYCua('b')) })
    await waitFor(() => expect(result.current?.node_id).toBe('b'))
  })

  it('may chu tra goi y cua node KHAC ⇒ hook BO, khong chuyen tiep', async () => {
    // ⭐ Ve nay do mot dieu khac ve tren: khong phai "cu vs moi" ma
    //    "may chu tra sai node". Mot phan hoi den muon tu mot request truoc co
    //    the mang `node_id` cu; `active` chan duoc ca CHUNG TOI huy, nhung mot
    //    phan hoi 200 tra ve NODE KHAC thi chi so `node_id` moi bat duoc.
    vi.spyOn(api, 'goiYBieuThuc').mockResolvedValue(goiYCua('nguoi-khac'))
    const { result } = renderHook(() =>
      useExpressionSuggest(WF, 'a', DOC, 'csrf', false))
    await new Promise(r => setTimeout(r, 400))
    expect(result.current).toBeUndefined()
  })

  it('doi chung: goi y DUNG node thi VAN qua', async () => {
    // ⛔ Khong co bai nay, mot ban va "luon tra undefined" cung lam hai bai tren
    //    xanh — va tinh nang chet hoan toan trong im lang.
    vi.spyOn(api, 'goiYBieuThuc').mockResolvedValue(goiYCua('a'))
    const { result } = renderHook(() =>
      useExpressionSuggest(WF, 'a', DOC, 'csrf', false))
    await waitFor(() => expect(result.current?.node_id).toBe('a'))
  })

  it('mat lua chon ⇒ undefined (hanh vi cu, ⛔ khong duoc lam hong)', async () => {
    vi.spyOn(api, 'goiYBieuThuc').mockResolvedValue(goiYCua('a'))
    const { result, rerender } = renderHook(
      ({ id }: { id: string | undefined }) =>
        useExpressionSuggest(WF, id, DOC, 'csrf', false),
      { initialProps: { id: 'a' as string | undefined } })
    await waitFor(() => expect(result.current?.node_id).toBe('a'))
    rerender({ id: undefined })
    expect(result.current).toBeUndefined()
  })
})
