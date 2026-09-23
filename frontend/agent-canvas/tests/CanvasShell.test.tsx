import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { CanvasShell } from '../src/CanvasShell'

const palette = { version: 1, tools: [
  { name: 'text.generate', label:'Tạo văn bản',category:'content',primary:true,description:'Tạo nội dung từ yêu cầu',
    app_slug:'kichban',app_name:'Kịch bản',requires:['api'],verifiable:[],params_schema:{prompt:{type:'text',required:true},image_key:{type:'image'}},returns:{text:'text'} },
  { name: 'image.generate', label:'Tạo hình ảnh',category:'content',primary:true,description:'Tạo ảnh từ mô tả',
    app_slug:'taoanh',app_name:'Tạo ảnh',requires:['gpu'],verifiable:[],params_schema:{prompt:{type:'text',required:true}},returns:{image:'image'} },
  { name: 'asset.image', label:'Ảnh đầu vào',category:'input',primary:false,description:'Ảnh tải lên',
    app_slug:'mediatools',app_name:'Media',requires:[],verifiable:[],params_schema:{image_key:{type:'string',required:true}},returns:{image_key:'image'} },
  { name: 'video.social_import', label:'Social Video',category:'input',primary:false,description:'Video từ liên kết',
    app_slug:'mediatools',app_name:'Media',requires:[],verifiable:[],params_schema:{url:{type:'string',required:true},confirm_rights:{type:'bool',required:true}},returns:{video_key:'video'} },
  { name: 'image.batch_generate', label:'Tạo nhiều ảnh',category:'specialized',primary:false,description:'Tạo bộ ảnh',
    app_slug:'taoanh',app_name:'Tạo ảnh',requires:['gpu'],verifiable:[],params_schema:{prompt:{type:'text',required:true},count:{type:'int',default:4}},returns:{image_keys:'image[]'} },
  { name: 'asset.images', label:'Bộ ảnh',category:'input',primary:false,description:'Bộ ảnh tải lên',
    app_slug:'mediatools',app_name:'Media',requires:[],verifiable:[],params_schema:{image_keys:{type:'json',required:true}},returns:{image_keys:'image[]'} },
  { name: 'video.generate', label:'Tạo video',category:'content',primary:true,description:'Tạo video từ mô tả',
    app_slug:'seedance',app_name:'Seedance',requires:['gpu'],verifiable:[],params_schema:{prompt:{type:'text',required:true}},returns:{video:'video'} },
  { name: 'audio.generate', label:'Tạo âm thanh',category:'content',primary:true,description:'Tạo âm thanh từ văn bản',
    app_slug:'mediatools',app_name:'Media',requires:[],verifiable:[],params_schema:{text:{type:'text',required:true}},returns:{audio_key:'audio'} },
  { name: 'image.upscale', label:'Nâng cấp ảnh',category:'transform',primary:false,description:'Tăng độ nét ảnh',
    app_slug:'upscale',app_name:'Upscale',requires:['gpu'],verifiable:[],params_schema:{image_key:{type:'image',required:true}},returns:{image:'image'} },
  { name: 'media.merge_video', label:'Ghép video',category:'transform',primary:false,description:'Ghép nhiều video',
    app_slug:'mediatools',app_name:'Media',requires:[],verifiable:[],params_schema:{videos:{type:'video[]',required:true},transition:{type:'enum',default:'cut',values:['cut']}},returns:{video_key:'video'} },
  { name: 'text.script', label:'Viết kịch bản',category:'specialized',primary:false,description:'Viết kịch bản',
    app_slug:'kichban',app_name:'Kịch bản',requires:['api'],verifiable:[],params_schema:{topic:{type:'text',required:true}},returns:{script:'text'} }
] }
const workflow = { id: 'w1', name: 'Workflow mới', status: 'draft', revision: 1, estimated: 0,
  canvas: { version: 1, goal: '', budget_max_credit: 50, nodes: [], edges: [],
    viewport: { x: 0, y: 0, zoom: 1 } } }
// Hinh dang v3 ma cua `/agent/api/v3/*` tra ve (Dot 5.2 phan D). `fromV3`
// se doi no ve hinh dang React Flow ma trinh soan dang dung, nen phan con lai
// cua tep nay khong doi.
const workflowV3 = { id: 'w1', name: 'Workflow mới', published_version_id: '',
  revision: 1,
  document: { version: 3, goal: '', budget_max_credit: 50,
    active_page_id: 'page-1',
    pages: [{ id: 'page-1', name: 'Page 1', nodes: [], edges: [],
      viewport: { x: 0, y: 0, zoom: 1 }, frames: [], notes: [], comments: [],
      view: { grid: true, connections: true, minimap: true } }] } }
const validatedWorkflow={...workflow,revision:3,validation:{issues:[],step_costs:[],estimated_max_credit:7}}
const awaitingRun={id:'r1',version:1,status:'awaiting_approval',plan:{steps:[{id:'n1'},{id:'n2'}]},
  checkpoint:{},estimated:7,actual:0,quote_hash:'quote-test',decisions:[]}

beforeEach(() => {
  document.body.innerHTML = '<div id="agent-canvas-root" data-csrf-token="test-csrf"></div>'
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input)
    if (url.endsWith('/palette')) return new Response(JSON.stringify(palette), { status: 200 })
    if (url.endsWith('/preferences')) return new Response(JSON.stringify({theme:'dark',catalog_mode:'simple',presentation_version:'creative-v1',revision:init?.method?1:0}), { status: 200 })
    if (url.endsWith('/assets')) {const file=init?.body instanceof FormData?init.body.get('file') as File:null
      const name=file?.name||'owned.png';return new Response(JSON.stringify({key:`agent-assets/u/${name}`,kind:'image',
        name,size:123,content_type:'image/png',url:`/agent/api/assets/${name}`}),{status:200})}
    if (url.endsWith('/agent/api/runs') && !init?.method) return new Response(JSON.stringify({items:[]}),{status:200})
    // ⚠️ PHAI dung TRUOC cac nhanh `/workflows` cu: duong v3 cung ket thuc
    //    bang `/workflows`, nen dat sau se bi nhanh cu nuot mat.
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
    if (url.endsWith('/validate')) return new Response(JSON.stringify(validatedWorkflow),{status:200})
    if (url.endsWith('/workflows/w1/runs')&&init?.method==='POST') return new Response(JSON.stringify(awaitingRun),{status:201})
    if (url.endsWith('/runs/r1/approve')) return new Response(JSON.stringify({...awaitingRun,version:2,status:'running'}),{status:200})
    if (url.endsWith('/runs/r1/cancel')) return new Response(JSON.stringify({...awaitingRun,version:3,status:'cancelled'}),{status:200})
    if (url.endsWith('/runs/r1/again')) return new Response(JSON.stringify({...awaitingRun,version:4}),{status:201})
    if (url.endsWith('/workflows') && !init?.method) return new Response(JSON.stringify({ items: [] }), { status: 200 })
    if (url.includes('/workflows/w1')) return new Response(JSON.stringify({ ...workflow, revision: 2 }), { status: 200 })
    return new Response(JSON.stringify(workflow), { status: 201 })
  })
})
afterEach(() => {
  vi.restoreAllMocks()
  Object.defineProperty(window,'innerWidth',{configurable:true,value:1024})
  Object.defineProperty(navigator,'onLine',{configurable:true,value:true})
})

describe('CanvasShell', () => {
  it('loads dynamic palette and adds/configures a tool node', async () => {
    render(<CanvasShell />)
    const palettePanel = await screen.findByLabelText('Palette công cụ')
    expect(palettePanel).not.toHaveClass('is-open')
    fireEvent.click(screen.getByRole('button',{name:'Mở công cụ'}))
    expect(palettePanel).toHaveClass('is-open')
    expect(screen.getByRole('textbox',{name:'Tìm công cụ'})).toBeInTheDocument()
    const add = await screen.findByRole('button', { name: 'Thêm Văn bản' })
    fireEvent.click(add)
    const node=await screen.findByLabelText('Khối Văn bản')
    expect(node).toBeInTheDocument()
    const inline=within(node).getByRole('textbox',{name:'Nội dung trực tiếp trong node'})
    fireEvent.change(inline,{target:{value:'Viết ngay trong node'}})
    expect(inline).toHaveValue('Viết ngay trong node')
    const title=within(node).getByRole('textbox',{name:'Tên hiển thị node'})
    fireEvent.change(title,{target:{value:'Lời dẫn mở đầu'}})
    expect(title).toHaveValue('Lời dẫn mở đầu')
    fireEvent.click(node)
    expect(screen.getByRole('region',{name:'Thiết lập Văn bản'})).toBeInTheDocument()
    fireEvent.change(inline, { target: { value: 'Chủ đề mới' } })
    expect(inline).toHaveValue('Chủ đề mới')
    fireEvent.keyDown(window,{key:'Escape'})
    expect(screen.queryByRole('region',{name:'Thiết lập Văn bản'})).not.toBeInTheDocument()
  })

  it('provides undo/redo and accessible regions', async () => {
    render(<CanvasShell />)
    fireEvent.click(await screen.findByRole('button',{name:'Mở công cụ'}))
    const add = await screen.findByRole('button', { name: 'Thêm Văn bản' })
    expect(screen.getByRole('region', { name: 'LTT Agent Canvas' })).toBeInTheDocument()
    fireEvent.click(add)
    const undo = screen.getByRole('button', { name: 'Hoàn tác' })
    await waitFor(() => expect(undo).toBeEnabled())
    fireEvent.click(undo)
    expect(screen.queryByLabelText('Khối Văn bản')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Làm lại' }))
    expect(screen.getByLabelText('Khối Văn bản')).toBeInTheDocument()
  })

  it('opens layers and keyboard command palette with working display toggles', async () => {
    render(<CanvasShell />)
    fireEvent.click(await screen.findByRole('button',{name:'Thêm Văn bản'}))
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
    await screen.findByRole('button',{name:'Thêm Văn bản'})
    expect(screen.getByRole('navigation',{name:'Khu vực Canvas'})).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button',{name:'Chi tiết'}))
    expect(screen.getByRole('button',{name:'Chi tiết'})).toHaveAttribute('aria-pressed','true')
    expect(screen.getByLabelText('Chi tiết block')).toHaveTextContent('Chọn một block')
    // ⛔ Lich su run (`AgentRun` v1) da bo khoi bang chi tiet — trang thai
    //    luot chay v3 chi o ngan keo "Chay workflow".
    expect(screen.queryByLabelText('Run inspector')).not.toBeInTheDocument()
  })

  it('upgrades legacy canvas and manages pages and annotations', async () => {
    render(<CanvasShell />)
    await screen.findByRole('button',{name:'Thêm Văn bản'})
    expect(screen.getByText(/Canvas v2/)).toBeInTheDocument()
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

  it('defaults to a dark, complete catalog and persists explicit choices', async () => {
    render(<CanvasShell />)
    const canvas=await screen.findByRole('region',{name:'LTT Agent Canvas'})
    expect(canvas).toHaveClass('theme-dark')
    fireEvent.click(screen.getByRole('button',{name:'Mở công cụ'}))
    expect(screen.getByRole('button',{name:'Thêm Văn bản'})).toHaveTextContent('Văn bản')
    expect(screen.getByRole('button',{name:'Thêm Hình ảnh'})).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Thêm Video'})).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Thêm Âm thanh'})).toBeInTheDocument()
    expect(screen.queryByRole('button',{name:'Thêm Viết kịch bản'})).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button',{name:'Hiện công cụ nâng cao'}))
    expect(screen.getByRole('button',{name:'Thêm Viết kịch bản'})).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button',{name:'Chuyển sang nền sáng'}))
    expect(canvas).toHaveClass('theme-light')
    await waitFor(()=>expect(globalThis.fetch).toHaveBeenCalledWith('/agent/api/preferences',expect.objectContaining({method:'PUT'})))
  })

  it('provides pane and node context menus without exposing raw tool fields',async()=>{
    render(<CanvasShell />)
    fireEvent.click(await screen.findByRole('button',{name:'Mở công cụ'}))
    fireEvent.click(screen.getByRole('button',{name:'Thêm Hình ảnh'}))
    const node=await screen.findByLabelText('Khối Hình ảnh')
    expect(screen.getByRole('textbox',{name:/Mô tả/})).toBeInTheDocument()
    expect(screen.queryByText('app_slug')).not.toBeInTheDocument()
    fireEvent.click(within(node).getByRole('button',{name:'Mở thao tác node'}))
    // ⛔ 01b chay CA do thi: hai muc "Bao gia & chay block/tu day" la `scope`
    //    cua Plan v1 va da bo — khong duoc de lai nut chet.
    const menu=screen.getByRole('complementary',{name:'Menu thao tác node'})
    expect(menu).toHaveTextContent('Sao chép node')
    expect(menu).not.toHaveTextContent('Báo giá')
    fireEvent.click(screen.getByRole('button',{name:'Đóng menu ngữ cảnh'}))
    fireEvent.contextMenu(node,{clientX:400,clientY:300})
    expect(screen.getByRole('complementary',{name:'Menu thao tác node'})).toHaveTextContent('Xóa node')
    fireEvent.click(screen.getByRole('button',{name:'Đóng menu ngữ cảnh'}))
    fireEvent.contextMenu(document.querySelector('.react-flow__pane')!,{clientX:600,clientY:250})
    expect(screen.getByRole('complementary',{name:'Menu khoảng trống Canvas'})).toHaveTextContent('Tự động sắp xếp node')
  })

  it('guides first-run users through both canonical chains before exposing advanced chrome',async()=>{
    render(<CanvasShell />)
    const firstRun=await screen.findByRole('region',{name:'Bắt đầu workflow'})
    expect(firstRun).toHaveTextContent('Chọn một mẫu')
    expect(screen.queryByTitle('Assistant')).not.toBeInTheDocument()
    expect(screen.queryByRole('button',{name:'Mở danh sách lớp'})).not.toBeInTheDocument()
    fireEvent.click(within(firstRun).getByRole('button',{name:/Prompt thành hình ảnh/}))
    expect(await screen.findByRole('region',{name:'Thiết lập Văn bản'})).toBeInTheDocument()
    expect(screen.getAllByText(/2 node · 1 kết nối/).length).toBeGreaterThan(0)
    expect(screen.getByTitle('Assistant')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button',{name:'Hoàn tác'}))
    const reset=await screen.findByRole('region',{name:'Bắt đầu workflow'})
    fireEvent.click(within(reset).getByRole('button',{name:/Hiểu nội dung hình ảnh/}))
    expect(await screen.findByRole('region',{name:'Thiết lập Hình ảnh'})).toBeInTheDocument()
    expect(screen.getAllByText(/2 node · 1 kết nối/).length).toBeGreaterThan(0)
  })

  it('exposes save-conflict recovery in the active toolbar',async()=>{
    const fetchMock=vi.mocked(globalThis.fetch)
    const base=fetchMock.getMockImplementation()!
    fetchMock.mockImplementation(async(input,init)=>{
      if(String(input).includes('/workflows/w1')&&init?.method==='PUT')return new Response('{}',{status:409})
      return base(input,init)
    })
    render(<CanvasShell />)
    fireEvent.click(await screen.findByRole('button',{name:'Thêm Văn bản'}))
    // 🔴 Cho nay tung viet `{timeout:1900}` va lam ca buoc gate chap chon.
    // Nut chi hien sau khi autosave PUT tra 409; chuoi debounce + fetch tren
    // may RANH mat ~1,5s, nen 1900ms chi con ~400ms bien. Do duoc mot luot do
    // that: that bai o 2381ms — duoi xa gio cua vitest, tuc KHONG phai het
    // gio khung test ma la mot con so chinh cho may ranh.
    //
    // ⚠️ Mot con so cho lon KHONG giau loi: neu nut khong bao gio hien, phep
    // kiem van do — chi la do muon hon. Cai no bo di la bien qua mong giua
    // "cham" va "hong".
    expect(await screen.findByRole('button',{name:'Tải bản mới'},{timeout:10_000})).toBeInTheDocument()
    expect(screen.getAllByText('Xung đột').length).toBeGreaterThan(0)
  })

  it('queues offline edits, retries after reconnect and keeps mobile read-only',async()=>{
    render(<CanvasShell />)
    fireEvent.click(await screen.findByRole('button',{name:'Thêm Văn bản'}))
    fireEvent(window,new Event('offline'))
    expect(await screen.findAllByText(/Ngoại tuyến/)).not.toHaveLength(0)
    const putCount=()=>vi.mocked(globalThis.fetch).mock.calls.filter(([url,init])=>
      String(url).includes('/workflows/w1')&&init?.method==='PUT').length
    const before=putCount()
    fireEvent.change(screen.getByRole('textbox',{name:'Nội dung trực tiếp trong node'}),{target:{value:'Sửa khi mất mạng'}})
    await new Promise(resolve=>setTimeout(resolve,900))
    expect(putCount()).toBe(before)
    Object.defineProperty(navigator,'onLine',{configurable:true,value:true})
    fireEvent(window,new Event('online'))
    await waitFor(()=>expect(putCount()).toBeGreaterThan(before),{timeout:10_000})
    Object.defineProperty(window,'innerWidth',{configurable:true,value:390})
    fireEvent(window,new Event('resize'))
    expect(screen.getByRole('button',{name:'Chạy'})).toBeDisabled()
  })

  it('connects a compatible node through the contextual @ reference picker',async()=>{
    render(<CanvasShell />)
    fireEvent.click(await screen.findByRole('button',{name:'Mở công cụ'}))
    fireEvent.click(screen.getByRole('button',{name:'Thêm Hình ảnh'}))
    fireEvent.click(screen.getByRole('button',{name:'Mở công cụ'}))
    fireEvent.click(screen.getByRole('button',{name:'Hiện công cụ nâng cao'}))
    fireEvent.click(screen.getByRole('button',{name:'Thêm Nâng cấp ảnh'}))
    const transform=await screen.findByLabelText('Khối Nâng cấp ảnh')
    fireEvent.click(transform)
    expect(within(transform).queryByLabelText('Tải lên')).not.toBeInTheDocument()
    const picker=screen.getByRole('combobox',{name:'Thêm nội dung từ block khác'})
    expect(picker).toHaveTextContent('@Hình ảnh · Hình ảnh → Ảnh đầu vào')
    const option=screen.getByRole('option',{name:/@Hình ảnh/}) as HTMLOptionElement
    fireEvent.change(picker,{target:{value:option.value}})
    expect(await screen.findByLabelText('Đầu vào đã kết nối')).toHaveTextContent('@Hình ảnh')
    fireEvent.click(screen.getByRole('button',{name:'Chèn bước vào kết nối'}))
    expect(screen.getByRole('complementary',{name:'Chèn bước vào kết nối'})).toHaveTextContent('Chọn hành động tương thích')
    fireEvent.click(screen.getByRole('button',{name:'Đóng chèn bước'}))
    fireEvent.click(screen.getByRole('button',{name:'Tháo kết nối Hình ảnh'}))
    expect(screen.queryByLabelText('Đầu vào đã kết nối')).not.toBeInTheDocument()
    // ⚠️ Doc `document`, khong `canvas`: tu Dot 5.2 phan D trinh soan ghi qua
    //    cua v3, va hinh dang TREN DAY la v3. Bai nay ghim dung hinh dang ay —
    //    nen no phai doi cung, khong duoc noi long thanh "co mot PUT nao do".
    await waitFor(()=>expect(vi.mocked(globalThis.fetch).mock.calls.some(([,init])=>{
      if(init?.method!=='PUT'||typeof init.body!=='string')return false
      const d=JSON.parse(init.body).document
      return d?.version===3&&d?.pages?.[0]?.edges?.length===0
    })).toBe(true),{timeout:10_000})
  })

  it('hides reference options that would loop back into the current block',async()=>{
    render(<CanvasShell />)
    fireEvent.click(await screen.findByRole('button',{name:'Mở công cụ'}))
    fireEvent.click(screen.getByRole('button',{name:'Thêm Văn bản'}))
    fireEvent.click(screen.getByRole('button',{name:'Mở công cụ'}))
    fireEvent.click(screen.getByRole('button',{name:'Thêm Hình ảnh'}))
    fireEvent.click(await screen.findByLabelText('Khối Hình ảnh'))
    const picker=screen.getByRole('combobox',{name:'Thêm nội dung từ block khác'})
    fireEvent.change(picker,{target:{value:(screen.getByRole('option',{name:/@Văn bản/}) as HTMLOptionElement).value}})
    expect(await screen.findByLabelText('Đầu vào đã kết nối')).toHaveTextContent('@Văn bản')
    fireEvent.click(screen.getByLabelText('Khối Văn bản'))
    // Hình ảnh feeds this block already: connectGraph refuses the reverse edge
    // as a cycle, so offering it would leave the customer with a dead control.
    expect(screen.queryByRole('option',{name:/@Hình ảnh/})).not.toBeInTheDocument()
    expect(screen.getAllByText(/2 node · 1 kết nối/).length).toBeGreaterThan(0)
  })

  it('keeps multiple scalar sources connected to one collection input',async()=>{
    render(<CanvasShell />)
    fireEvent.click(await screen.findByRole('button',{name:'Mở công cụ'}))
    fireEvent.click(screen.getByRole('button',{name:'Thêm Video'}))
    fireEvent.click(screen.getByRole('button',{name:'Thêm Video'}))
    fireEvent.click(screen.getByRole('button',{name:'Mở công cụ'}))
    fireEvent.click(screen.getByRole('button',{name:'Hiện công cụ nâng cao'}))
    fireEvent.click(screen.getByRole('button',{name:'Thêm Ghép video'}))
    fireEvent.click(await screen.findByLabelText('Khối Ghép video'))
    let picker=screen.getByRole('combobox',{name:'Thêm nội dung từ block khác'}) as HTMLSelectElement
    const first=[...picker.options].find(option=>option.value)!
    fireEvent.change(picker,{target:{value:first.value}})
    picker=screen.getByRole('combobox',{name:'Thêm nội dung từ block khác'}) as HTMLSelectElement
    const second=[...picker.options].find(option=>option.value&&option.value!==first.value)!
    fireEvent.change(picker,{target:{value:second.value}})
    expect(await screen.findByLabelText('Đầu vào đã kết nối')).toHaveTextContent('Video → Video đầu vào')
    expect(screen.getByRole('button',{name:'Tháo kết nối Video 1'})).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Tháo kết nối Video 2'})).toBeInTheDocument()
    expect(screen.getAllByText(/3 node · 2 kết nối/).length).toBeGreaterThan(0)
    fireEvent.click(screen.getByRole('button',{name:'Tháo kết nối Video 1'}))
    expect(screen.queryByRole('button',{name:'Tháo kết nối Video 1'})).not.toBeInTheDocument()
    expect(screen.getAllByText(/3 node · 1 kết nối/).length).toBeGreaterThan(0)
  })

  it('supports direct creation and workspace shortcuts without hijacking text input',async()=>{
    render(<CanvasShell />)
    const canvas=await screen.findByRole('region',{name:'LTT Agent Canvas'})
    fireEvent.keyDown(canvas,{key:'i'})
    expect(await screen.findByLabelText('Khối Hình ảnh')).toBeInTheDocument()
    fireEvent.keyDown(canvas,{key:'t'})
    const text=await screen.findByLabelText('Khối Văn bản')
    expect(text).toBeInTheDocument()
    fireEvent.keyDown(canvas,{key:'n'})
    expect(screen.getByLabelText('Sticky note Ghi chú mới')).toBeInTheDocument()
    fireEvent.keyDown(canvas,{key:'d'})
    expect(screen.getByLabelText('Palette công cụ')).toHaveClass('workspace-only')
    const inline=within(text).getByRole('textbox',{name:'Nội dung trực tiếp trong node'})
    fireEvent.keyDown(inline,{key:'i'})
    expect(screen.getAllByLabelText('Khối Hình ảnh')).toHaveLength(1)
  })

  it('opens a compatibility-filtered next-step picker from the single output plus',async()=>{
    render(<CanvasShell />)
    fireEvent.click(await screen.findByRole('button',{name:'Mở công cụ'}))
    fireEvent.click(screen.getByRole('button',{name:'Thêm Văn bản'}))
    fireEvent.click(screen.getByLabelText('Kết nối Nội dung'))
    const picker=screen.getByRole('complementary',{name:'Chọn bước tiếp theo'})
    expect(picker).toHaveTextContent('TẠO BLOCK MỚI')
    expect(within(picker).getByRole('button',{name:/Tạo hình ảnh/})).toBeInTheDocument()
    expect(picker).not.toHaveTextContent('asset.image')
    fireEvent.click(within(picker).getByRole('button',{name:/Tạo hình ảnh/}))
    const created=(await screen.findAllByLabelText('Khối Hình ảnh'))[0]
    expect(within(created).getByRole('textbox',{name:'Mô tả'})).toHaveAttribute('placeholder','Dùng nội dung từ block đã kết nối')
    expect((within(created).getByRole('textbox',{name:'Mô tả'}) as HTMLTextAreaElement).value).not.toContain('$')
  })

  it('keeps Upload and Generate as two modes of the same user-facing Image node',async()=>{
    render(<CanvasShell />)
    fireEvent.click(await screen.findByRole('button',{name:'Mở công cụ'}))
    fireEvent.click(screen.getByRole('button',{name:'Thêm Hình ảnh'}))
    const generated=await screen.findByLabelText('Khối Hình ảnh')
    fireEvent.change(within(generated).getByLabelText('Tải lên'),{target:{files:[new File(['png'],'owned.png',{type:'image/png'})]}})
    const preview=await screen.findByRole('img',{name:'Ảnh đã tải lên'})
    const uploaded=preview.closest('article')!
    expect(within(uploaded).getByRole('textbox',{name:'Tên hiển thị node'})).toHaveValue('Hình ảnh')
    expect(preview).toHaveAttribute('src','/agent/api/assets/owned.png')
    expect(within(uploaded).getByRole('button',{name:'Tạo lại'})).toBeInTheDocument()
    fireEvent.click(within(uploaded).getByRole('button',{name:'Tạo lại'}))
    expect(await screen.findByLabelText('Khối Hình ảnh')).toBeInTheDocument()
    expect(screen.getByRole('textbox',{name:/Mô tả/})).toBeInTheDocument()
  })

  it('presents Social Video as a URL action and never as a local upload node',async()=>{
    render(<CanvasShell />)
    fireEvent.click(await screen.findByRole('button',{name:'Mở công cụ'}))
    fireEvent.click(screen.getByRole('button',{name:'Hiện công cụ nâng cao'}))
    fireEvent.click(screen.getByRole('button',{name:'Thêm Nhập video từ liên kết'}))
    const node=await screen.findByLabelText('Khối Nhập video từ liên kết')
    expect(within(node).getByRole('textbox',{name:'Tên hiển thị node'})).toHaveValue('Nhập video từ liên kết')
    expect(within(node).getByText('Thêm Social Video')).toBeInTheDocument()
    expect(within(node).queryByLabelText('Tải lên')).not.toBeInTheDocument()
    expect(screen.getByRole('textbox',{name:/Liên kết/})).toHaveAttribute('placeholder',
      'Dán link TikTok, YouTube Shorts hoặc Reels…')
    fireEvent.click(within(node).getByRole('button',{name:'Chi tiết'}))
    expect(screen.getByRole('checkbox',{name:/Tôi xác nhận có quyền sử dụng video/})).toBeInTheDocument()
  })

  it('keeps multiple uploads inside one Batch Images node and can switch back to generation',async()=>{
    render(<CanvasShell />)
    fireEvent.click(await screen.findByRole('button',{name:'Mở công cụ'}))
    fireEvent.click(screen.getByRole('button',{name:'Hiện công cụ nâng cao'}))
    fireEvent.click(screen.getByRole('button',{name:'Thêm Tạo bộ ảnh'}))
    const generated=await screen.findByLabelText('Khối Tạo bộ ảnh')
    const files=[new File(['a'],'a.png',{type:'image/png'}),new File(['b'],'b.png',{type:'image/png'})]
    fireEvent.change(within(generated).getByLabelText('Tải lên'),{target:{files}})
    const uploaded=await screen.findByLabelText('Khối Hình ảnh')
    expect(within(uploaded).getByRole('textbox',{name:'Tên hiển thị node'})).toHaveValue('Hình ảnh')
    expect(within(uploaded).getAllByRole('img')).toHaveLength(2)
    expect(within(uploaded).getByRole('img',{name:'Ảnh 1 trong bộ ảnh'})).toHaveAttribute('src','/agent/api/assets/a.png')
    fireEvent.click(within(uploaded).getByRole('button',{name:'Tạo lại'}))
    expect(await screen.findByLabelText('Khối Tạo bộ ảnh')).toBeInTheDocument()
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
function mockRunV3(xen?: (url: string, init?: RequestInit) => Response | undefined) {
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
  fireEvent.click(await screen.findByRole('button', { name: 'Thêm Văn bản' }))
  await screen.findByLabelText('Khối Văn bản')
  const nodeId = document.querySelector<HTMLElement>('.react-flow__node')!.dataset.id!
  fireEvent.click(screen.getByRole('button', { name: 'Chạy' }))
  const drawer = screen.getByRole('navigation', { name: 'Chạy workflow' })
  const nut = await within(drawer).findByRole('button', { name: 'Chạy ngay' })
  await waitFor(() => expect(nut).toBeEnabled())
  fireEvent.click(nut)
  return { drawer, nodeId }
}

const duongDaGoi = () => vi.mocked(globalThis.fetch).mock.calls.map(([url]) => String(url))

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
    // mot lan nua de mock tra ve dung id node dang co tren canvas.
    fireEvent.click(within(ket.drawer).getByRole('button', { name: 'Chạy ngay' }))
    // Thong diep hien o HAI cho co chu dich: bang bao loi tren canvas va dong
    // loi trong ngan keo chay. Neo vao ngan keo de bai nay khong do vi "nhieu
    // ket qua" khi bang kia cung noi cung mot cau.
    expect(await within(ket.drawer).findByText(/Node không có trong registry\./)).toBeTruthy()
    await waitFor(() => expect(
      document.querySelector(`[data-loi-node="${ket.nodeId}"]`)).toBeTruthy())
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
})

