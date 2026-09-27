/**
 * ĐẶC TẢ (characterization) — hành vi tinh vi của trình soạn, đo TRƯỚC khi tách
 * `CanvasShell.tsx` thành `features/editor/*`, và phải còn xanh SAU khi tách.
 *
 * ⭐ VÌ SAO TỆP NÀY TỒN TẠI
 *
 *    Tách một hàm 740 dòng là một phép biến đổi mà **không phép kiểm nào
 *    chứng minh là tương đương** — trừ khi có phép kiểm. `CanvasShell.test.tsx`
 *    đã giữ bốn trong sáu hành vi tinh vi (xem bảng dưới); hai hành vi còn lại
 *    thì **không có gì giữ**, nên tách xong sẽ không ai biết chúng còn sống.
 *
 * ⭐ BẢNG ĐỘ PHỦ — sáu hành vi tinh vi, ai giữ cái nào
 *
 *    | Hành vi                                   | Giữ ở đâu |
 *    |-------------------------------------------|-----------|
 *    | SSE lùi dần theo `soHong`/`lanNoiLai`     | `CanvasShell.test.tsx` — "hong lien tiep thi LUI DAN", "luong dong sau khi DA nhan goi" |
 *    | Chốt chống bấm đúp bằng `dangGuiRun` ref  | `CanvasShell.test.tsx` — "bấm đúp lúc lượt đầu ĐANG BAY", "lượt đầu HỎNG rồi" |
 *    | `Idempotency-Key` giữ qua lần thử lại     | `CanvasShell.test.tsx` — "MỘT lần bấm = MỘT khoá", "hai lần bấm KHÁC NHAU" |
 *    | `nhapRun` nối sự kiện theo `seq`          | `CanvasShell.test.tsx` — "hủy run KHÔNG nhân đôi dòng thời gian" |
 *    | **Autosave debounce 800 ms**              | **TỆP NÀY** — trước đó không có gì giữ |
 *    | **`updateNodeInternals` theo rAF**        | **TỆP NÀY** — trước đó không có gì giữ |
 *
 * 🔴 BẪY ĐÃ TRÁNH: `tests/workflowApi.test.ts` có bài
 *    *"debounces autosave and persists only latest value"* — nhìn thì tưởng đã
 *    giữ autosave rồi. Nó đo `createAutosave(save, 500)`, một helper mà
 *    **`CanvasShell` KHÔNG hề gọi**: trình soạn có vòng `window.setTimeout(…,
 *    800)` viết thẳng trong effect. Đọc thứ ĐẠI DIỆN thay vì thứ THẬT thì
 *    tách xong vẫn xanh trong lúc autoave thật đã chết.
 *
 * ⏱️ Đồng hồ THẬT, ⛔ không `vi.useFakeTimers()` — lý do đầy đủ ở
 *    `CanvasShell.test.tsx` (RTL dò đồng hồ giả bằng `typeof jest`, vitest
 *    không đặt biến ấy ⇒ mọi `waitFor` TREO 20 s).
 */
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { NodeDefinition, NhomPalette } from '../src/nodeDefinition'

// ── Bộ đôi cho `useUpdateNodeInternals` ─────────────────────────────────────
//
// ⭐ `vi.mock` được cẩu lên đầu tệp, nên `capNhatNoiBo` phải sống trong một
//    `vi.hoisted` — một `const` thường ở thân tệp thì chưa tồn tại lúc factory
//    chạy (`ReferenceError: Cannot access before initialization`).
//
// ⛔ Chỉ thay ĐÚNG một hook. Mọi thứ còn lại của `@xyflow/react` là hàng thật:
//    thay cả gói thì bài này đo bộ đôi của chính nó, không đo trình soạn.
const gia = vi.hoisted(() => ({ capNhatNoiBo: vi.fn() }))
vi.mock('@xyflow/react', async () => {
  const thuc = await vi.importActual<typeof import('@xyflow/react')>('@xyflow/react')
  return { ...thuc, useUpdateNodeInternals: () => gia.capNhatNoiBo }
})

// Import SAU `vi.mock` để trình soạn nhận bản đã thay hook.
const { CanvasShell } = await import('../src/CanvasShell')

// ── Palette v3 tối thiểu (cùng hình dạng `palette_v3.py::sang_json`) ────────
const cong = (ten: string, kieu: string, nhieu = false) =>
  ({ ten, kieu, bat_buoc: false, nhieu })

const nd = (type: string, title: string, over: Partial<NodeDefinition> = {}):
  NodeDefinition => ({ type, type_version: 1, kind: 'app', category: 'LTT_APPS',
    title, description: 'mo ta', icon: '', app_name: 'App', cong_vao: [],
    cong_ra: [], tham_so: { type: 'object', properties: {}, required: [] },
    thi_hanh: 'job', side_effect: 'external', resource: {}, timeout_expr: '',
    retry_mac_dinh: { max: 0, backoff_s: 30 },
    gia: { kieu: 'theo_registry', so: 0, job_type: 'j' }, credential: [],
    quyen: [], cho: [], ma_loi: [], co_mock: false, publish_duoc: true, ...over })

const nhomPalette: NhomPalette[] = [
  { category: 'LTT_APPS', nut: [
    nd('app.text.chat', 'Sinh văn bản', { app_name: 'LTT LLM',
      cong_vao: [cong('prompt', 'text')], cong_ra: [cong('content', 'text')],
      tham_so: { type: 'object', required: ['prompt'],
        properties: { prompt: { type: 'string' } } } }),
  ] },
]

const paletteV3 = { phien_ban: 3, nhom: nhomPalette, luat_noi_day: {
  phien_ban: 2, kieu: ['text'], hau_to_tap_hop: '[]',
  cap_noi_duoc: [['text', 'text']] as [string, string][] } }

const workflowV3 = { id: 'w1', name: 'Workflow mới', published_version_id: '',
  revision: 1,
  document: { version: 3, goal: '', budget_max_credit: 50,
    active_page_id: 'page-1',
    pages: [{ id: 'page-1', name: 'Page 1', nodes: [], edges: [],
      viewport: { x: 0, y: 0, zoom: 1 }, frames: [], notes: [], comments: [],
      view: { grid: true, connections: true, minimap: true } }] } }

beforeEach(() => {
  document.body.innerHTML = '<div id="agent-canvas-root" data-csrf-token="test-csrf"></div>'
  try { localStorage.clear() } catch { /* cua so rieng tu */ }
  gia.capNhatNoiBo.mockClear()
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input)
    if (url.endsWith('/v3/palette')) return new Response(JSON.stringify(paletteV3), { status: 200 })
    if (url.endsWith('/preferences')) return new Response(JSON.stringify({ theme: 'dark',
      catalog_mode: 'simple', presentation_version: 'creative-v1', revision: 0 }), { status: 200 })
    if (url.includes('/bao-gia')) return new Response(JSON.stringify({ gia: {} }), { status: 200 })
    if (url.includes('/quote')) return new Response(JSON.stringify({ valid: true, maximum: 3 }), { status: 200 })
    if (url.includes('/bieu-thuc/goi-y')) return new Response(JSON.stringify({
      node_id: 'n1', muc: [], ham: [], loi: null }), { status: 200 })
    if (url.includes('/api/v3/workflows')) {
      if (init?.method === 'PUT')
        return new Response(JSON.stringify({ ...workflowV3, revision: workflowV3.revision + 1 }), { status: 200 })
      if (url.endsWith('/workflows'))
        return new Response(JSON.stringify({ items: [{ id: 'w1', name: 'Workflow mới', published: false }] }), { status: 200 })
      return new Response(JSON.stringify(workflowV3), { status: 200 })
    }
    return new Response('{}', { status: 200 })
  })
})

afterEach(() => {
  vi.restoreAllMocks()
  Object.defineProperty(window, 'innerWidth', { configurable: true, value: 1024 })
  Object.defineProperty(navigator, 'onLine', { configurable: true, value: true })
})

/** Số lần trình soạn đã PUT tài liệu — tức số lần autosave THẬT SỰ bay đi. */
const soLanLuu = () => vi.mocked(globalThis.fetch).mock.calls
  .filter(([url, init]) => String(url).includes('/api/v3/workflows/')
    && init?.method === 'PUT').length

/** `document.goal` của TỪNG lần PUT, theo thứ tự đã gửi. */
const mucTieuDaLuu = () => vi.mocked(globalThis.fetch).mock.calls
  .filter(([url, init]) => String(url).includes('/api/v3/workflows/')
    && init?.method === 'PUT')
  .map(([, init]) => (JSON.parse(String(init!.body)) as
    { document: { goal: string } }).document.goal)

/** Chờ một khoảng THẬT, trong `act`. Cần cho các khẳng định PHỦ ĐỊNH
 *  ("chưa được lưu") — chúng đòi một cửa sổ thời gian, không đọc ngay được. */
const cho = (ms: number) =>
  act(async () => { await new Promise(xong => setTimeout(xong, ms)) })

/** Mở ngăn "Mẫu & thiết lập" và trả về ô "Mục tiêu workflow". */
async function oMucTieu() {
  fireEvent.click(await screen.findByRole('button', { name: 'Mở mẫu và thiết lập' }))
  return await screen.findByLabelText('Mục tiêu workflow')
}

describe('Đặc tả: autosave debounce 800 ms', () => {
  // ⭐ Bài CHỐT. Ba lần gõ liên tiếp phải gộp thành MỘT lần PUT, và lần PUT ấy
  //    mang giá trị CUỐI. Nếu tách làm vỡ debounce, hỏng theo hai kiểu và bài
  //    này bắt được cả hai: ba PUT (bão request mỗi ký tự), hoặc PUT mang giá
  //    trị cũ.
  it('ba lần sửa liên tiếp gộp thành MỘT lần PUT, mang giá trị CUỐI', async () => {
    render(<CanvasShell />)
    const o = await oMucTieu()
    // Tài liệu vừa nạp KHỚP `workflow.canvas` ⇒ chốt trong effect chặn, chưa
    // được lưu gì. Đây là mốc 0 cho phép đếm dưới.
    expect(soLanLuu()).toBe(0)

    // Ba lần gõ ĐỒNG BỘ, không `await` xen giữa: cả ba nằm trong cùng một cửa
    // sổ 800 ms dù máy có bận.
    fireEvent.change(o, { target: { value: 'một' } })
    fireEvent.change(o, { target: { value: 'một hai' } })
    fireEvent.change(o, { target: { value: 'một hai ba' } })

    // 300 ms sau lần gõ cuối: debounce còn đang đếm ⇒ CHƯA bay.
    await cho(300)
    expect(soLanLuu()).toBe(0)

    await waitFor(() => expect(soLanLuu()).toBe(1), { timeout: 4000 })
    expect(mucTieuDaLuu()).toEqual(['một hai ba'])

    // Và không có lần thứ hai đuổi theo: một cửa sổ đóng là một lần PUT.
    await cho(900)
    expect(soLanLuu()).toBe(1)
  })

  // ⛔ Ngoại tuyến thì KHÔNG gửi. Đây là vế `offline` của cùng một effect —
  //    tách rời nó khỏi debounce là cách hỏng dễ nhất, vì cả hai sống trong
  //    một `if` duy nhất.
  it('ngoại tuyến thì KHÔNG autosave, dù đã quá 800 ms', async () => {
    render(<CanvasShell />)
    const o = await oMucTieu()
    act(() => {
      Object.defineProperty(navigator, 'onLine', { configurable: true, value: false })
      window.dispatchEvent(new Event('offline'))
    })
    fireEvent.change(o, { target: { value: 'sửa lúc mất mạng' } })
    await cho(1200)
    expect(soLanLuu()).toBe(0)
  })
})

describe('Đặc tả: updateNodeInternals theo requestAnimationFrame', () => {
  // ⭐ VÌ SAO PHẢI LÀ rAF, không phải gọi thẳng: `updateNodeInternals` đo lại
  //    cổng của node, nên nó phải chạy SAU khi trình duyệt đã layout. Gọi ngay
  //    trong effect thì đo một node chưa có kích thước ⇒ dây nối vẽ lệch.
  //    Bài này khoá đúng cái nhịp ấy: KHÔNG đồng bộ, và CÓ chạy sau một frame.
  it('không gọi ĐỒNG BỘ; sau một frame thì gọi với id node của trang', async () => {
    render(<CanvasShell />)
    fireEvent.click(await screen.findByRole('button', { name: 'Mở công cụ' }))
    gia.capNhatNoiBo.mockClear()

    // `fireEvent` bọc trong `act` ⇒ effect ĐÃ chạy và đã xếp một frame, nhưng
    // callback của frame thì chưa. Đây là chỗ duy nhất phân biệt được "qua
    // rAF" với "gọi thẳng trong effect".
    fireEvent.click(await screen.findByRole('button', { name: /Sinh văn bản/ }))
    expect(gia.capNhatNoiBo).not.toHaveBeenCalled()

    const el = await waitFor(() => {
      const found = document.querySelector<HTMLElement>('.react-flow__node')
      if (!found) throw new Error('chua ve node nao tren khung')
      return found
    })
    const nodeId = el.dataset.id!
    await waitFor(() => expect(gia.capNhatNoiBo).toHaveBeenCalledWith([nodeId]),
      { timeout: 4000 })
  })

  // ⛔ Frame phải bị HUỶ khi effect dọn. Không huỷ thì một callback của lượt
  //    render cũ chạy sau khi component đã tháo — React 19 cảnh báo, và trên
  //    máy thật nó đo cổng của một đồ thị không còn tồn tại.
  //
  // 🔴 ⛔ KHÔNG đo bằng `vi.spyOn(globalThis,'cancelAnimationFrame')`: bản đầu
  //    của bài này làm thế và nó XANH GIẢ — `@xyflow/react` tự gọi
  //    `cancelAnimationFrame` vài lần cho việc của nó, nên phép đo vẫn xanh
  //    sau khi tôi gỡ hẳn khối rAF khỏi `CanvasShell` (đã tiêm lỗi để kiểm).
  //    Phải đo HỆ QUẢ: callback của frame đang chờ **không được** chạy.
  it('frame đang chờ KHÔNG chạy sau khi tháo component', async () => {
    const { unmount } = render(<CanvasShell />)
    fireEvent.click(await screen.findByRole('button', { name: 'Mở công cụ' }))
    // Xếp frame (effect chạy trong `act` của `fireEvent`), rồi THÁO ngay —
    // callback chưa kịp chạy, nên đây đúng là cửa sổ mà bản dọn phải đóng.
    fireEvent.click(await screen.findByRole('button', { name: /Sinh văn bản/ }))
    gia.capNhatNoiBo.mockClear()
    unmount()
    await cho(80)   // nhiều frame đã đi qua
    expect(gia.capNhatNoiBo).not.toHaveBeenCalled()
  })
})
