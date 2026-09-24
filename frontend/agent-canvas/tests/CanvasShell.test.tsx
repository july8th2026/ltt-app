import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { CanvasShell } from '../src/CanvasShell'
import type { NodeDefinition, NhomPalette } from '../src/nodeDefinition'

// ── Palette v3 THAT (`apps/agent/routes/palette_v3.py::sang_json`) ──────────
//
// ⛔ Khong con palette v2 (`{tools:[{name,label,category,primary,…}]}`) o day.
//    Plan 02 task 15 cat Canvas sang `/agent/api/v3/palette`: node mang
//    `type`/`type_version`, CONG CO KIEU (`cong_vao`/`cong_ra`) va mot luoc do
//    JSON Schema, con luat noi day tai tu `he_kieu.xuat_luat_noi_day()`.
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
  { category: 'TRIGGERS', nut: [nd('trigger.manual', 'Chạy thủ công', {
      kind: 'trigger', category: 'TRIGGERS', publish_duoc: false,
      cong_ra: [cong('event', 'event')] })] },
  { category: 'LTT_APPS', nut: [
    nd('app.image.generate', 'Sinh ảnh', { app_name: 'Tạo ảnh',
      resource: { class: 'gpu' },
      cong_vao: [cong('prompt', 'text')], cong_ra: [cong('image', 'image')],
      tham_so: { type: 'object', required: ['prompt'],
        properties: { prompt: { type: 'string' } } } }),
    nd('app.text.chat', 'Sinh văn bản', { app_name: 'LTT LLM',
      cong_vao: [cong('prompt', 'text')], cong_ra: [cong('content', 'text')],
      tham_so: { type: 'object', required: ['prompt'],
        properties: { prompt: { type: 'string' }, count: { type: 'integer', default: 1 } } } }),
    // ⭐ App HONG: `_giai_tuy_chon_dong` nem ⇒ node VAN ra palette, voi lucc
    //    do TINH va dau `x-ltt-loi` o ca muc node lan tung truong.
    nd('app.voice.tts', 'Đọc văn bản', { app_name: 'LTT Voice',
      'x-ltt-loi': 'LUACHON_KHONG_TAI_DUOC',
      cong_vao: [cong('text', 'text')], cong_ra: [cong('audio', 'audio')],
      tham_so: { type: 'object', required: [], properties: {
        voice_id: { type: 'string', 'x-ltt-loi': 'LUACHON_KHONG_TAI_DUOC' } } } }),
  ] },
]

const paletteV3 = { phien_ban: 3, nhom: nhomPalette, luat_noi_day: {
  phien_ban: 2, kieu: ['text', 'image', 'audio', 'event'], hau_to_tap_hop: '[]',
  cap_noi_duoc: [['text', 'text'], ['image', 'image'], ['text', 'image']] as [string, string][] } }

const workflow = { id: 'w1', name: 'Workflow mới', status: 'draft', revision: 1, estimated: 0,
  canvas: { version: 1, goal: '', budget_max_credit: 50, nodes: [], edges: [],
    viewport: { x: 0, y: 0, zoom: 1 } } }
// Hinh dang v3 ma cua `/agent/api/v3/*` tra ve (Dot 5.2 phan D). `fromV3`
// se doi no ve hinh dang React Flow ma trinh soan dang dung.
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
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input)
    // ⚠️ TRUOC nhanh `/api/v3/workflows`: thu tu o day tung nuot mot duong roi.
    if (url.endsWith('/v3/palette')) return new Response(JSON.stringify(paletteV3), { status: 200 })
    if (url.endsWith('/v3/luat-noi-day')) return new Response(JSON.stringify(paletteV3.luat_noi_day), { status: 200 })
    if (url.endsWith('/preferences')) return new Response(JSON.stringify({theme:'dark',catalog_mode:'simple',presentation_version:'creative-v1',revision:init?.method?1:0}), { status: 200 })
    if (url.includes('/quote')) return new Response(JSON.stringify({valid:true,maximum:3}), { status: 200 })
    // Cua goi y §6 (P2 Task 8) — TRUOC nhanh `/api/v3/workflows` vi no cung
    // la POST tren cung tien to; de sau thi no rot vao nhanh "tao workflow".
    if (url.includes('/bieu-thuc/goi-y')) return new Response(JSON.stringify({
      node_id: 'n1', muc: [{ duong: 'trigger', loai: 'goc', qua_publish: false }],
      ham: [], loi: null }), { status: 200 })
    if (url.includes('/api/v3/workflows')) {
      if (init?.method === 'PUT')
        return new Response(JSON.stringify({...workflowV3, revision: workflowV3.revision + 1}), { status: 200 })
      if (init?.method === 'POST' && !url.endsWith('/publish'))
        return new Response(JSON.stringify(workflowV3), { status: 201 })
      if (url.endsWith('/publish'))
        return new Response(JSON.stringify({workflow_id:'w1',version_id:'v1',credit_max:20,credit_estimate:12}), { status: 200 })
      if (url.endsWith('/workflows'))
        return new Response(JSON.stringify({ items: [{ id: 'w1', name: 'Workflow mới', published: false }] }), { status: 200 })
      return new Response(JSON.stringify(workflowV3), { status: 200 })
    }
    return new Response(JSON.stringify(workflow), { status: 201 })
  })
})
afterEach(() => {
  vi.restoreAllMocks()
  Object.defineProperty(window,'innerWidth',{configurable:true,value:1024})
  Object.defineProperty(navigator,'onLine',{configurable:true,value:true})
})

/** So node DO THI dang ve tren khung (khong tinh the o palette). */
const soNode = () => document.querySelectorAll('.react-flow__node').length

/** Mo bang node va them "Sinh văn bản". Tra ve phan tu node vua ve.
 *
 *  ⚠️ Phai gioi han trong `.react-flow__node`: `app.text.chat@1` xuat hien o
 *     CA the palette lan node — mot `findByText` tran se nhap nhang. */
async function themVanBan() {
  fireEvent.click(await screen.findByRole('button', { name: 'Mở công cụ' }))
  fireEvent.click(await screen.findByRole('button', { name: /Sinh văn bản/ }))
  return await waitFor(() => {
    const el = document.querySelector<HTMLElement>('.react-flow__node')
    if (!el) throw new Error('chua ve node nao tren khung')
    return el
  })
}

describe('CanvasShell', () => {
  // ⭐ Bai CHOT cua task 15: nhan node den TU `NodeDefinition` cua palette, va
  //    node duoc ve bang MOT component (`NodeRenderer`). Truoc do nhan di qua
  //    `presentationAdapter.customerToolLabel` — mot bang tra cuu go cung.
  it('vẽ node bằng NodeRenderer và lấy nhãn từ NodeDefinition', async () => {
    render(<CanvasShell />)
    const node = await themVanBan()
    expect(within(node).getByText('Sinh văn bản')).toBeInTheDocument()
    expect(within(node).getByText('app.text.chat@1')).toBeInTheDocument()
    expect(within(node).getByTestId('node-kind')).toHaveTextContent('app')
    // Cong CO KIEU den tu `cong_vao`/`cong_ra`, khong tu mot bang tra cuu.
    expect(within(node).getByTitle('prompt · text')).toBeInTheDocument()
    expect(within(node).getByTitle('content · text')).toBeInTheDocument()
  })

  it('palette v3 nhóm theo category và thẻ hiện type@version', async () => {
    render(<CanvasShell />)
    fireEvent.click(await screen.findByRole('button', { name: 'Mở công cụ' }))
    const bang = await screen.findByRole('complementary', { name: 'Bảng node' })
    expect(within(bang).getByRole('heading', { name: 'Kích hoạt' })).toBeInTheDocument()
    expect(within(bang).getByRole('heading', { name: 'App LTT' })).toBeInTheDocument()
    expect(within(bang).getByText('app.image.generate@1')).toBeInTheDocument()
    // Node loi chua bien dich duoc (`publish_duoc=False`) ⇒ vo hieu, khong moi keo.
    expect(within(bang).getByRole('button', { name: /Chạy thủ công/ })).toBeDisabled()
  })

  // ⛔ Nhan cu ghi "Canvas v2" trong khi trinh soan da chay runtime v3 tu
  //    plan 01b — nghiem thu production 23/09 bat duoc.
  it('thanh công cụ nói đúng phiên bản Canvas', async () => {
    render(<CanvasShell />)
    await screen.findByRole('button', { name: 'Mở công cụ' })
    expect(screen.getByText(/Canvas v3/)).toBeInTheDocument()
    expect(screen.queryByText(/Canvas v2/)).toBeNull()
  })

  it('inspector sinh form TỪ LƯỢC ĐỒ của node đang chọn', async () => {
    render(<CanvasShell />)
    await themVanBan()
    fireEvent.click(screen.getByRole('button', { name: 'Chi tiết' }))
    const inspector = screen.getByRole('complementary', { name: 'Chi tiết node' })
    const prompt = within(inspector).getByLabelText('prompt *')
    fireEvent.change(prompt, { target: { value: 'viết một đoạn' } })
    expect(prompt).toHaveValue('viết một đoạn')
    // O SO co cong tac bieu thuc (task 15, viec them 2).
    expect(within(inspector).getByRole('button', { name: 'Dùng biểu thức cho count' }))
      .toBeInTheDocument()
  })

  // ⭐ Mat xich cuoi cua "palette la catalogue": node hong ra palette voi lucc
  //    do TINH. Lucc do tinh cua `voice_id` la mot `string` TU DO — khong khoa
  //    thi nguoi dung go bua, publish qua, va hong LUC CHAY.
  it('node mang x-ltt-loi: palette cảnh báo và inspector khoá ô lại', async () => {
    render(<CanvasShell />)
    fireEvent.click(await screen.findByRole('button', { name: 'Mở công cụ' }))
    const bang = await screen.findByRole('complementary', { name: 'Bảng node' })
    expect(within(bang).getByText('Chưa tải được lựa chọn')).toBeInTheDocument()
    fireEvent.click(within(bang).getByRole('button', { name: /Đọc văn bản/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Chi tiết' }))
    const inspector = screen.getByRole('complementary', { name: 'Chi tiết node' })
    expect(within(inspector).getByLabelText('voice_id')).toBeDisabled()
  })

  // 🔴 DO DUOC TREN TRINH DUYET THAT 24/09: tren desktop `.canvas-mobile-tabs`
  //    la `display:none`, nen nut "Chi tiết" chi ton tai o mobile. Sau khi
  //    task 15 don `ContextComposer`, MOI tham so chi con o inspector — va tren
  //    desktop khong con mot duong nao mo no. jsdom khong doc CSS nen bai
  //    "responsive panel" van xanh: no bam duoc mot nut ma nguoi dung khong
  //    thay. Hai duong vao, va ca hai deu phai co.
  it('mở được inspector trên desktop: nút ở thanh dọc VÀ bấm vào node', async () => {
    render(<CanvasShell />)
    const node = await themVanBan()
    const nut = screen.getByRole('button', { name: 'Mở chi tiết node' })
    const co = () => screen.queryByRole('complementary', { name: 'Chi tiết node' })
    // Them node xong thi inspector MO SAN: tham so cua node vua keo ve phai
    // thay duoc ngay, khong bat nguoi dung di tim mot duong nua.
    expect(nut).toHaveAttribute('aria-pressed', 'true')
    expect(co()).toHaveClass('is-open')
    // 1. Nut o thanh doc dong/mo duoc — `.canvas-rail` hien o moi be ngang.
    fireEvent.click(nut)
    expect(co()).toBeNull()
    fireEvent.click(nut)
    expect(co()).toHaveClass('is-open')
    // 2. Bam vao node tren khung cung mo — do la cu chi tu nhien nhat.
    fireEvent.click(nut)
    expect(co()).toBeNull()
    fireEvent.click(node)
    expect(co()).toHaveClass('is-open')
  })

  it('nhớ node dùng gần đây qua localStorage', async () => {
    render(<CanvasShell />)
    await themVanBan()
    expect(JSON.parse(localStorage.getItem('ltt.palette.ganDay')!))
      .toEqual(['app.text.chat'])
    expect(await screen.findByRole('heading', { name: 'Gần đây' })).toBeInTheDocument()
  })

  it('provides undo/redo and accessible regions', async () => {
    render(<CanvasShell />)
    await themVanBan()
    expect(screen.getByRole('region', { name: 'LTT Agent Canvas' })).toBeInTheDocument()
    expect(soNode()).toBe(1)
    const undo = screen.getByRole('button', { name: 'Hoàn tác' })
    await waitFor(() => expect(undo).toBeEnabled())
    fireEvent.click(undo)
    expect(soNode()).toBe(0)
    fireEvent.click(screen.getByRole('button', { name: 'Làm lại' }))
    expect(soNode()).toBe(1)
  })

  it('opens layers and keyboard command palette with working display toggles', async () => {
    render(<CanvasShell />)
    await themVanBan()
    fireEvent.click(screen.getByRole('button',{name:'Mở danh sách lớp'}))
    expect(screen.getByRole('complementary',{name:'Danh sách lớp'})).toBeInTheDocument()
    fireEvent.keyDown(window,{key:'k',ctrlKey:true})
    expect(screen.getByRole('dialog',{name:'Bảng lệnh Canvas'})).toBeInTheDocument()
    fireEvent.change(screen.getByRole('textbox',{name:'Tìm lệnh'}),{target:{value:'lưới'}})
    fireEvent.click(screen.getByRole('button',{name:'Ẩn lưới'}))
    fireEvent.keyDown(window,{key:'k',ctrlKey:true})
    fireEvent.change(screen.getByRole('textbox',{name:'Tìm lệnh'}),{target:{value:'lưới'}})
    expect(screen.getByRole('button',{name:'Hiện lưới'})).toBeInTheDocument()
  })

  it('exposes responsive panel controls without hiding inspector semantics', async () => {
    render(<CanvasShell />)
    await screen.findByRole('button',{name:'Mở công cụ'})
    expect(screen.getByRole('navigation',{name:'Khu vực Canvas'})).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button',{name:'Chi tiết'}))
    expect(screen.getByRole('button',{name:'Chi tiết'})).toHaveAttribute('aria-pressed','true')
    expect(screen.getByLabelText('Chi tiết node')).toHaveTextContent('Chọn một node')
    // ⛔ Lich su run (`AgentRun` v1) da bo khoi bang chi tiet — trang thai
    //    luot chay v3 chi o ngan keo "Chay workflow".
    expect(screen.queryByLabelText('Run inspector')).not.toBeInTheDocument()
  })

  it('upgrades legacy canvas and manages pages and annotations', async () => {
    render(<CanvasShell />)
    fireEvent.click(await screen.findByRole('button',{name:'Mở công cụ'}))
    fireEvent.click(screen.getByRole('button',{name:'+ Page'}))
    expect(screen.getByRole('textbox',{name:/Đổi tên Page 2/})).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button',{name:'+ Sticky note'}))
    fireEvent.click(screen.getByRole('button',{name:'+ Comment'}))
    expect(screen.getByLabelText('Sticky note Ghi chú mới')).toBeInTheDocument()
    expect(screen.getByLabelText('Comment Bình luận mới')).toBeInTheDocument()
    fireEvent.change(screen.getByRole('textbox',{name:'Nội dung sticky note'}),{target:{value:'Duyệt màu'}})
    expect(screen.getByLabelText('Sticky note Duyệt màu')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button',{name:'Xóa comment'}))
    expect(screen.queryByLabelText(/Comment Bình luận mới/)).not.toBeInTheDocument()
  })

  it('defaults to a dark theme and persists an explicit choice', async () => {
    render(<CanvasShell />)
    const canvas=await screen.findByRole('region',{name:'LTT Agent Canvas'})
    expect(canvas).toHaveClass('theme-dark')
    fireEvent.click(screen.getByRole('button',{name:'Chuyển sang nền sáng'}))
    expect(canvas).toHaveClass('theme-light')
    await waitFor(()=>expect(globalThis.fetch).toHaveBeenCalledWith('/agent/api/preferences',expect.objectContaining({method:'PUT'})))
  })

  it('provides pane and node context menus without exposing raw tool fields',async()=>{
    render(<CanvasShell />)
    const node=await themVanBan()
    expect(screen.queryByText('app_slug')).not.toBeInTheDocument()
    fireEvent.contextMenu(node,{clientX:400,clientY:300})
    // ⛔ 01b chay CA do thi: hai muc "Bao gia & chay block/tu day" la `scope`
    //    cua Plan v1 va da bo — khong duoc de lai nut chet.
    const menu=screen.getByRole('complementary',{name:'Menu thao tác node'})
    expect(menu).toHaveTextContent('Sao chép node')
    expect(menu).not.toHaveTextContent('Báo giá')
    fireEvent.click(screen.getByRole('button',{name:'Đóng menu ngữ cảnh'}))
    fireEvent.contextMenu(document.querySelector('.react-flow__pane')!,{clientX:600,clientY:250})
    expect(screen.getByRole('complementary',{name:'Menu khoảng trống Canvas'})).toHaveTextContent('Tự động sắp xếp node')
  })

  it('exposes save-conflict recovery in the active toolbar',async()=>{
    const fetchMock=vi.mocked(globalThis.fetch)
    const base=fetchMock.getMockImplementation()!
    fetchMock.mockImplementation(async(input,init)=>{
      if(String(input).includes('/workflows/w1')&&init?.method==='PUT')return new Response('{}',{status:409})
      return base(input,init)
    })
    render(<CanvasShell />)
    await themVanBan()
    // 🔴 Cho nay tung viet `{timeout:1900}` va lam ca buoc gate chap chon.
    // Nut chi hien sau khi autosave PUT tra 409; chuoi debounce + fetch tren
    // may RANH mat ~1,5s, nen 1900ms chi con ~400ms bien.
    expect(await screen.findByRole('button',{name:'Tải bản mới'},{timeout:10_000})).toBeInTheDocument()
    expect(screen.getAllByText('Xung đột').length).toBeGreaterThan(0)
  })

  it('queues offline edits, retries after reconnect and keeps mobile read-only',async()=>{
    render(<CanvasShell />)
    await themVanBan()
    fireEvent(window,new Event('offline'))
    expect(await screen.findAllByText(/Ngoại tuyến/)).not.toHaveLength(0)
    const putCount=()=>vi.mocked(globalThis.fetch).mock.calls.filter(([url,init])=>
      String(url).includes('/workflows/w1')&&init?.method==='PUT').length
    const before=putCount()
    fireEvent.click(screen.getByRole('button',{name:'Chi tiết'}))
    fireEvent.change(screen.getByLabelText('prompt *'),{target:{value:'Sửa khi mất mạng'}})
    await new Promise(resolve=>setTimeout(resolve,900))
    expect(putCount()).toBe(before)
    Object.defineProperty(navigator,'onLine',{configurable:true,value:true})
    fireEvent(window,new Event('online'))
    await waitFor(()=>expect(putCount()).toBeGreaterThan(before),{timeout:10_000})
    Object.defineProperty(window,'innerWidth',{configurable:true,value:390})
    fireEvent(window,new Event('resize'))
    expect(screen.getByRole('button',{name:'Chạy'})).toBeDisabled()
  })
})


// ── Chay workflow tren v3 (Dot 5.2 phan D / plan 01b task 6) ─────────────
// Vong doi mot luot chay o day KHONG con la "bao gia -> duyet -> tick":
// trinh soan LUU ban nhap, PUBLISH mot version, roi TAO run va chi DOC.
// Ba loi goi ay phai di dung thu tu — publish truoc run — vi `tao_run` tu
// choi mot workflow chua publish (422 `chua_publish`).
const runV3Goc = { id: 'r1', workflow_id: 'w1', version_id: 'v1', status: 'QUEUED',
  credit_max: 20, credit_charged: 0, settled: false,
  created_at: '2026-09-24T00:00:00+00:00',
  nodes: [] as { node_id: string; status: string; attempt: number
    cost_credit: number; job_id: string; error: string }[],
  su_kien: [{ seq: 1, loai: 'run.created', node_id: '', du_lieu: {},
    created_at: '2026-09-24T00:00:00+00:00' }],
  seq_cuoi: 1 }

/** Giu nguyen mock goc cua `beforeEach`, chi chen them cac cua v3 cua run. */
function mockRunV3(xen?: (url: string, init?: RequestInit) =>
    Response | Promise<Response> | undefined) {
  const fetchMock = vi.mocked(globalThis.fetch)
  const base = fetchMock.getMockImplementation()!
  fetchMock.mockImplementation(async (input, init) => {
    const url = String(input)
    const rieng = xen?.(url, init)
    if (rieng) return rieng
    if (url.includes('/api/v3/workflows/') && url.endsWith('/runs') && init?.method === 'POST')
      return new Response(JSON.stringify(runV3Goc), { status: 201 })
    // ⚠️ Cua huy KHONG nhan `?sau=`: no tra CA lich su su kien (runs_v3.py).
    //    Mock phai giong the, neu khong bai duoi khong do duoc loi nhan doi.
    if (url.includes('/api/v3/runs/') && url.endsWith('/cancel'))
      return new Response(JSON.stringify({ ...runV3Goc, status: 'CANCELLED',
        su_kien: [...runV3Goc.su_kien,
          { seq: 2, loai: 'WorkflowCancelled', node_id: '', du_lieu: {},
            created_at: '2026-09-24T00:00:05+00:00' }], seq_cuoi: 2 }), { status: 200 })
    if (url.includes('/api/v3/runs/'))
      return new Response(JSON.stringify({ ...runV3Goc, status: 'SUCCEEDED',
        credit_charged: 4, settled: true,
        su_kien: [{ seq: 2, loai: 'run.succeeded', node_id: '', du_lieu: {},
          created_at: '2026-09-24T00:00:10+00:00' }], seq_cuoi: 2 }), { status: 200 })
    return base(input, init)
  })
}

/** Them mot node, mo ngan keo chay, bam "Chay ngay". Tra ve ngan keo + id node. */
async function bamChay() {
  render(<CanvasShell />)
  await themVanBan()
  const nodeId = document.querySelector<HTMLElement>('.react-flow__node')!.dataset.id!
  fireEvent.click(screen.getByRole('button', { name: 'Chạy' }))
  const drawer = screen.getByRole('navigation', { name: 'Chạy workflow' })
  const nut = await within(drawer).findByRole('button', { name: 'Chạy ngay' })
  await waitFor(() => expect(nut).toBeEnabled())
  fireEvent.click(nut)
  return { drawer, nodeId }
}

const duongDaGoi = () => vi.mocked(globalThis.fetch).mock.calls.map(([url]) => String(url))

/** Khoá `Idempotency-Key` của TỪNG lời gọi tạo run, theo thứ tự đã gửi. */
const khoaTaoRun = () => vi.mocked(globalThis.fetch).mock.calls
  .filter(([url, init]) => String(url).includes('/api/v3/workflows/')
    && String(url).endsWith('/runs') && init?.method === 'POST')
  .map(([, init]) => new Headers(init!.headers).get('Idempotency-Key'))

/** ⏱️ KHONG dung `vi.useFakeTimers()` o day, va day la ly do — no la mot bay
 *  im lang: `@testing-library/dom` do dong ho gia bang `typeof jest !==
 *  'undefined'`, ma vitest khong dat bien ay. Hau qua khong phai "RTL bo qua
 *  dong ho gia" ma la TREO: `asyncWrapper` cua @testing-library/react xa hang
 *  microtask bang `await new Promise(r => setTimeout(r, 0))` roi chi day dong
 *  ho khi `jestFakeTimersAreEnabled()`. Voi vitest, cai `setTimeout` ay bi gia
 *  lap va KHONG AI day => moi `findBy*`/`waitFor` treo den khi vitest cat, ke
 *  ca khi phan tu da co san trong DOM. (Do ngay 23/09: 6 bai treo 20s mot bai.)
 *
 *  Nen cac bai duoi dung dong ho THAT va tra gia bang vai giay cho. Nhip poll
 *  la 1,5s + lui dan, nen mot bai hai nhip het ~4,5s. */
const trangThaiRun = (drawer: HTMLElement) =>
  drawer.querySelector<HTMLElement>('[data-run-status]')?.dataset.runStatus ?? ''
/** Cho mot khoang THAT, trong `act`, de phan hoi ve muon kip duoc xu ly. Dung
 *  cho cac khang dinh PHU DINH ("khong duoc doi") — chung can mot cua so thoi
 *  gian, khong the chi doc ngay. */
const cho = (ms: number) =>
  act(async () => { await new Promise(resolve => setTimeout(resolve, ms)) })

describe('Chạy workflow trên v3', () => {
  it('bấm Chạy: lưu v3 → publish v3 → tạo run v3, đúng thứ tự', async () => {
    mockRunV3()
    const { drawer } = await bamChay()
    expect(await within(drawer).findByText('QUEUED')).toBeInTheDocument()
    const goi = duongDaGoi()
    const v3 = goi.filter(u => u.includes('/agent/api/v3/'))
    expect(v3.some(u => u.startsWith('/agent/api/v3/workflows/') &&
      !u.includes('/publish') && !u.endsWith('/runs'))).toBe(true)
    expect(v3.findIndex(u => u.includes('/publish')))
      .toBeLessThan(v3.findIndex(u => u.endsWith('/runs')))
    // ⛔ Ve doi chung: khong duoc con mot loi goi chay v2 nao. Mot cai sot lai
    //    la Canvas vua tao `WorkflowRun` v3 vua lai `AgentRun` v1.
    expect(goi.some(u => u.includes('/agent/api/workflows/'))).toBe(false)
  })

  it('MỘT lần bấm = MỘT khoá; thử lại cùng lần bấm gửi LẠI khoá ấy', async () => {
    // 🔴 Do duoc qua HTTP that 23/09: bam "Chay ngay" hai lan tao HAI run, HAI
    //    lan giu cho, HAI lan tru tien. Cua v3 nay doi `Idempotency-Key`.
    //    Lan thu lai cua CUNG mot lan bam phai mang LAI dung khoa cu — neu
    //    khong, may chu coi day la mot lan chay moi va tru tien lan nua.
    let hong = true
    mockRunV3((url, init) =>
      url.includes('/api/v3/workflows/') && url.endsWith('/runs')
        && init?.method === 'POST' && hong
        ? new Response(JSON.stringify({ detail: 'Mạng lỗi.' }), { status: 503 })
        : undefined)
    const { drawer } = await bamChay()
    expect(await within(drawer).findByText(/Mạng lỗi\./)).toBeTruthy()
    hong = false
    // `findBy`, khong `getBy`: trong lúc lượt trước còn bay, nút mang nhãn
    // "Đang gửi…" (cờ chặn bấm đúp) — phải chờ nó trở lại "Chạy ngay".
    fireEvent.click(await within(drawer).findByRole('button', { name: 'Chạy ngay' }))
    await waitFor(() => expect(khoaTaoRun().length).toBe(2))
    const khoa = khoaTaoRun()
    expect(khoa[0]).toBeTruthy()
    expect(khoa[0]!.length).toBeGreaterThanOrEqual(8)   // MIN_KEY_LENGTH may chu
    expect(khoa[1]).toBe(khoa[0])
  })

  it('hai lần bấm KHÁC NHAU gửi khoá KHÁC NHAU', async () => {
    // 🔑 Ve doi chung bat buoc cho bai tren. Khong co no, mot ban va gui mot
    //    HANG SO cung xanh — va khi ay nguoi dung se khong bao gio chay duoc
    //    lan thu hai: may chu tra lai dung run cu cho moi lan bam ve sau.
    mockRunV3((url, init) =>
      url.includes('/api/v3/workflows/') && url.endsWith('/runs')
        && init?.method === 'POST'
        ? new Response(JSON.stringify({ ...runV3Goc, status: 'SUCCEEDED',
            credit_charged: 4, settled: true }), { status: 201 })
        : undefined)
    const { drawer } = await bamChay()
    await waitFor(() => expect(khoaTaoRun().length).toBe(1))
    // Mot lan bam MOI: run cu da ket thuc, nguoi dung mo mot ban chay khac.
    fireEvent.click(await within(drawer).findByRole('button',
      { name: 'Tạo bản chạy mới' }))
    fireEvent.click(await within(drawer).findByRole('button', { name: 'Chạy ngay' }))
    await waitFor(() => expect(khoaTaoRun().length).toBe(2))
    const khoa = khoaTaoRun()
    expect(khoa[1]).toBeTruthy()
    expect(khoa[1]).not.toBe(khoa[0])
  })

  // -- Bam dup (vong sua 23/09) -------------------------------------------
  // ⚠️ `Idempotency-Key` va bam dup la HAI benh khac nhau. Khoa chi cuu
  //    "THU LAI CUNG mot lan bam" (mang dut): cung khoa => may chu tra lai
  //    run cu. Bam dup sinh HAI lan bam => HAI khoa => hai run, hai lan giu
  //    cho, hai lan tru tien. Chi mot cai chot O CLIENT moi chan duoc.
  /** Treo lo `POST …/runs` cho toi khi goi `moKhoa()`. Tra ve co bao "da gui". */
  function treoTaoRun(ketQua: () => Response) {
    let moKhoa: () => void = () => {}
    const treo = new Promise<void>(resolve => { moKhoa = resolve })
    const trangThai = { daGui: false }
    mockRunV3((url, init) => {
      if (url.includes('/api/v3/workflows/') && url.endsWith('/runs')
          && init?.method === 'POST') {
        trangThai.daGui = true
        return treo.then(ketQua)
      }
      return undefined
    })
    return { trangThai, moKhoa: () => moKhoa() }
  }

  it('bấm đúp lúc lượt đầu ĐANG BAY: đúng MỘT run được tạo', async () => {
    const { trangThai, moKhoa } = treoTaoRun(() =>
      new Response(JSON.stringify(runV3Goc), { status: 201 }))
    const { drawer } = await bamChay()
    // Cho toi dung cua so nguy hiem: luu + publish DA xong (nen `phase` khong
    // con 'saving' va nut het bi khoa vi ly do luu), con `tao_run` CHUA ve.
    await waitFor(() => expect(trangThai.daGui).toBe(true), { timeout: 10_000 })
    // 🔴 VE DO CHINH (cai HAI that): lan bam thu hai khong duoc de lai dau vet
    //    nao o cua tao run. Hai POST = hai run = hai lan tru tien.
    const nut = drawer.querySelector<HTMLButtonElement>('button.run-confirm')!
    fireEvent.click(nut)
    fireEvent.click(nut)
    await cho(50)
    expect(khoaTaoRun()).toHaveLength(1)
    // Va nguoi dung phai THAY luot dau dang bay — nuot im lang lam ho bam them.
    expect(nut.textContent).toMatch(/Đang gửi/)
    expect(nut).toBeDisabled()
    moKhoa()
    expect(await within(drawer).findByText('QUEUED')).toBeInTheDocument()
    expect(khoaTaoRun()).toHaveLength(1)
  })

  it('lượt đầu HỎNG rồi: bấm lại PHẢI gửi được', async () => {
    // ⛔ Ve doi chung BAT BUOC cho bai tren: mot ban va khoa nut VINH VIEN
    //    cung xanh o bai tren, va nguoi dung se khong bao gio chay lai duoc
    //    sau mot loi 402/503.
    const { trangThai, moKhoa } = treoTaoRun(() =>
      new Response(JSON.stringify({ detail: 'Không đủ credit.' }), { status: 402 }))
    const { drawer } = await bamChay()
    await waitFor(() => expect(trangThai.daGui).toBe(true), { timeout: 10_000 })
    moKhoa()
    expect(await within(drawer).findByText(/Không đủ credit\./)).toBeTruthy()
    // Co "dang gui" phai duoc DAT LAI o duong hong, khong chi o duong thanh cong.
    const nut = await within(drawer).findByRole('button', { name: 'Chạy ngay' })
    await waitFor(() => expect(nut).toBeEnabled())
    fireEvent.click(nut)
    await waitFor(() => expect(khoaTaoRun().length).toBe(2), { timeout: 10_000 })
  })

  it('run tạo XONG rồi: bấm lại tạo được run MỚI', async () => {
    mockRunV3((url, init) =>
      url.includes('/api/v3/workflows/') && url.endsWith('/runs')
        && init?.method === 'POST'
        ? new Response(JSON.stringify({ ...runV3Goc, status: 'SUCCEEDED',
            credit_charged: 4, settled: true }), { status: 201 })
        : undefined)
    const { drawer } = await bamChay()
    await waitFor(() => expect(khoaTaoRun().length).toBe(1))
    fireEvent.click(await within(drawer).findByRole('button',
      { name: 'Tạo bản chạy mới' }))
    const nut = await within(drawer).findByRole('button', { name: 'Chạy ngay' })
    await waitFor(() => expect(nut).toBeEnabled())
    fireEvent.click(nut)
    await waitFor(() => expect(khoaTaoRun().length).toBe(2), { timeout: 10_000 })
  })

  it('publish 422 hiện thông điệp VÀ đánh dấu node hỏng', async () => {
    let nodeLoi = ''
    mockRunV3(url => url.includes('/publish')
      ? new Response(JSON.stringify({ detail: { ma: 'node_khong_biet',
          node_id: nodeLoi, thong_diep: 'Node không có trong registry.' } }),
        { status: 422 })
      : undefined)
    const ket = await bamChay()
    nodeLoi = ket.nodeId
    // Lan bam dau co the da gui publish truoc khi `nodeLoi` duoc gan — bam lai
    // mot lan nua de mock tra ve dung id node dang co tren canvas. `findBy`:
    // lan bam dau con dang bay thi nut mang nhan "Dang gui…" — cho no ve.
    fireEvent.click(await within(ket.drawer).findByRole('button', { name: 'Chạy ngay' }))
    // Thong diep hien o HAI cho co chu dich: bang bao loi tren canvas va dong
    // loi trong ngan keo chay. Neo vao ngan keo de bai nay khong do vi "nhieu
    // ket qua" khi bang kia cung noi cung mot cau.
    expect(await within(ket.drawer).findByText(/Node không có trong registry\./)).toBeTruthy()
    // `node-do-loi` nam tren chinh `.react-flow__node` (CanvasShell dat qua
    // `className`), cung cho voi `data-id` — khong phai doan qua mot chuoi
    // tieng Viet co the doi.
    await waitFor(() => expect(document.querySelector(
      `.react-flow__node.node-do-loi[data-id="${ket.nodeId}"]`)).toBeTruthy())
    // Publish do => KHONG duoc tao run: tien chi duoc giu khi do thi bien dich duoc.
    expect(duongDaGoi().some(u => u.endsWith('/runs') &&
      u.includes('/api/v3/'))).toBe(false)
  })

  it('hủy run KHÔNG nhân đôi dòng thời gian', async () => {
    // 🔴 Do duoc mot lan tren trinh duyet (loopback, 23/09): bam "Huy chay" roi
    //    dong thoi gian hien WorkflowStarted HAI lan. Noi mu quang lo nhu vay
    //    vi cua huy tra ca lich su, con vong poll tra phan tang dan.
    mockRunV3()
    const { drawer } = await bamChay()
    await within(drawer).findByText('QUEUED')
    fireEvent.click(within(drawer).getByRole('button', { name: 'Hủy chạy' }))
    expect(await within(drawer).findByText('CANCELLED')).toBeInTheDocument()
    const dong = [...drawer.querySelectorAll('.run-v3-su-kien li')].map(li => li.textContent)
    expect(dong.filter(t => t === 'run.created')).toHaveLength(1)
    expect(dong).toContain('WorkflowCancelled')
  })

  it('poll đọc lại run và nối sự kiện, dừng khi run kết thúc, hủy được', async () => {
    mockRunV3()
    const { drawer } = await bamChay()
    await within(drawer).findByText('QUEUED')
    // Nut huy chi ton tai khi run CHUA ket thuc.
    expect(within(drawer).getByRole('button', { name: 'Hủy chạy' })).toBeInTheDocument()
    expect(await within(drawer).findByText('SUCCEEDED', {}, { timeout: 10_000 })).toBeInTheDocument()
    const doc = duongDaGoi().filter(u => u.includes('/api/v3/runs/'))
    expect(doc.some(u => u.includes('sau=1'))).toBe(true)
    // Su kien phai NOI, khong thay: lich su con lai ca hai dong.
    expect(drawer.textContent).toContain('run.created')
    expect(drawer.textContent).toContain('run.succeeded')
    expect(within(drawer).queryByRole('button', { name: 'Hủy chạy' })).not.toBeInTheDocument()
  })

  // -- Vong sua 1 (review C1 / I2) ----------------------------------------
  it('MOT nhip poll hong khong giet vong poll: nhip sau van toi', async () => {
    // Benh: nhip ke chi duoc len lich khi `run` DOI tham chieu. Nhanh `.catch`
    // khong dung toi `run` => effect khong chay lai => khong con `setTimeout`
    // nao nua. Mot blip mang la mot run DANG TIEU TIEN dung mai o RUNNING, va
    // chi tai lai trang moi cuu duoc.
    // Bai nay do dung cai chet do: nhip THU HAI co xay ra khong. Khang dinh ve
    // `runError` chi la phan them — mot minh no do trieu chung, khong do benh.
    let soLanDoc = 0
    mockRunV3(url => {
      if (url.includes('/api/v3/runs/') && !url.endsWith('/cancel')) {
        soLanDoc += 1
        if (soLanDoc === 1) throw new TypeError('Failed to fetch')
      }
      return undefined
    })
    const { drawer } = await bamChay()
    await within(drawer).findByText('QUEUED')
    expect(await within(drawer).findByText(/đang thử lại/i, {}, { timeout: 10_000 }))
      .toBeInTheDocument()
    expect(soLanDoc).toBe(1)
    // 🔴 VE DO CHINH: vong poll phai con song sau cu nga.
    expect(await within(drawer).findByText('SUCCEEDED', {}, { timeout: 15_000 }))
      .toBeInTheDocument()
    expect(soLanDoc).toBeGreaterThanOrEqual(2)
    // ... va khi poll khoe lai thi thong diep loi phai BIEN MAT, khong o lai
    // vinh vien tren mot man hinh dang chay binh thuong.
    expect(within(drawer).queryByText(/đang thử lại/i)).toBeNull()
  })

  it('phan hoi poll ve MUON khong lam song lai run da huy', async () => {
    // Benh: khong co co `active`. Mot GET poll dang bay, nguoi dung bam
    // "Huy chay", cua huy tra CANCELLED — roi phan hoi poll cu (RUNNING) ve
    // sau va de nguoc trang thai. Nut "Huy chay" hien lai cho mot luot da
    // chet; bam lan hai an 409 "Luot chay da ket thuc" cho mot thao tac DA
    // thanh cong.
    let moKhoa: () => void = () => {}
    const treo = new Promise<void>(resolve => { moKhoa = resolve })
    let daTreo = false
    mockRunV3(url => {
      if (url.includes('/api/v3/runs/') && !url.endsWith('/cancel') && !daTreo) {
        daTreo = true
        return treo.then(() => new Response(JSON.stringify(
          { ...runV3Goc, status: 'RUNNING' }), { status: 200 }))
      }
      return undefined
    })
    const { drawer } = await bamChay()
    await within(drawer).findByText('QUEUED')
    await waitFor(() => expect(daTreo).toBe(true), { timeout: 10_000 })
    fireEvent.click(within(drawer).getByRole('button', { name: 'Hủy chạy' }))
    await within(drawer).findByText('CANCELLED')
    moKhoa()                                   // phan hoi cu ve MUON
    await cho(50)
    expect(trangThaiRun(drawer)).toBe('CANCELLED')
    expect(within(drawer).queryByRole('button', { name: 'Hủy chạy' })).toBeNull()
  })

  it('phan hoi poll ve MUON khong lam song lai run da DONG', async () => {
    let moKhoa: () => void = () => {}
    const treo = new Promise<void>(resolve => { moKhoa = resolve })
    let daTreo = false
    mockRunV3(url => {
      if (url.includes('/api/v3/runs/') && !url.endsWith('/cancel') && !daTreo) {
        daTreo = true
        return treo.then(() => new Response(JSON.stringify(
          { ...runV3Goc, status: 'RUNNING' }), { status: 200 }))
      }
      return undefined
    })
    const { drawer } = await bamChay()
    await within(drawer).findByText('QUEUED')
    await waitFor(() => expect(daTreo).toBe(true), { timeout: 10_000 })
    // Huy roi bam "Tao ban chay moi" => `setRun(null)`: bang luot chay bien mat.
    fireEvent.click(within(drawer).getByRole('button', { name: 'Hủy chạy' }))
    await within(drawer).findByText('CANCELLED')
    fireEvent.click(within(drawer).getByRole('button', { name: 'Tạo bản chạy mới' }))
    expect(trangThaiRun(drawer)).toBe('')
    moKhoa()
    await cho(50)
    expect(trangThaiRun(drawer)).toBe('')
    expect(within(drawer).queryByLabelText('Lượt chạy')).toBeNull()
  })

  // -- Do phu dung lai tu bai v1 da xoa (review, phan quyet 4) -------------
  it('publish 422 KHONG bi dan nhan "Loi luu"', async () => {
    // Manh (a) cua bai `keeps global budget validation visible and does not
    // mislabel it as a save failure`: mot loi o duong CHAY khong duoc hien ra
    // nhu loi LUU. Ban nhap DA luu that; noi nguoc lai la day nguoi dung di
    // cuu mot thu khong hong.
    mockRunV3(url => url.includes('/publish')
      ? new Response(JSON.stringify({ detail: { ma: 'node_khong_biet',
          node_id: 'n1', thong_diep: 'Node không có trong registry.' } }),
        { status: 422 })
      : undefined)
    const { drawer } = await bamChay()
    expect(await within(drawer).findByText(/Node không có trong registry\./)).toBeTruthy()
    // Doc NGAY: vong autosave se luu lai ban nhap sau 800ms va dua huy hieu ve
    // 'Da luu' du co chuyen gi — waitFor o day se do chinh vong autosave chu
    // khong do nhan cua loi publish.
    const huyHieu = document.querySelector<HTMLElement>('.canvas-top-actions .save-state')!
    expect(huyHieu.textContent).toBe('Đã lưu')
  })

  it('tran chi tieu hien tren giao dien v3, o "Ngan sach toi da" chet da go', async () => {
    // Manh (b): tran chi tieu phai duoc CHOT o dau do va nguoi dung phai THAY.
    // O v3, may chu chot `credit_max` luc publish va tra ve trong run — giao
    // dien phai hien no. O nhap cu khong con duoc doc boi bat ky tep
    // `platform_core/workflow/*` nao, nen giu lai la hua mot tran ma khong ai
    // thi hanh.
    mockRunV3()
    const { drawer } = await bamChay()
    await within(drawer).findByText('QUEUED')
    expect(within(drawer).getByText('0/20 credit')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Mở mẫu và thiết lập' }))
    expect(screen.queryByLabelText(/Ngân sách tối đa/)).toBeNull()
  })
})

