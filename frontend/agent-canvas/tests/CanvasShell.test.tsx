import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { CanvasShell } from '../src/CanvasShell'
import { RunInspector } from '../src/RunInspector'

const palette = { version: 1, tools: [
  { name: 'text.generate', label:'Tạo văn bản',category:'content',primary:true,description:'Tạo nội dung từ yêu cầu',
    app_slug:'kichban',app_name:'Kịch bản',requires:['api'],verifiable:[],params_schema:{prompt:{type:'text',required:true}},returns:{text:'text'} },
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

beforeEach(() => {
  document.body.innerHTML = '<div id="agent-canvas-root" data-csrf-token="test-csrf"></div>'
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input)
    if (url.endsWith('/palette')) return new Response(JSON.stringify(palette), { status: 200 })
    if (url.endsWith('/preferences')) return new Response(JSON.stringify({theme:'dark',catalog_mode:'advanced',revision:init?.method?1:0}), { status: 200 })
    if (url.endsWith('/assets')) {const file=init?.body instanceof FormData?init.body.get('file') as File:null
      const name=file?.name||'owned.png';return new Response(JSON.stringify({key:`agent-assets/u/${name}`,kind:'image',
        name,size:123,content_type:'image/png',url:`/agent/api/assets/${name}`}),{status:200})}
    if (url.endsWith('/workflows') && !init?.method) return new Response(JSON.stringify({ items: [] }), { status: 200 })
    if (url.includes('/workflows/w1')) return new Response(JSON.stringify({ ...workflow, revision: 2 }), { status: 200 })
    return new Response(JSON.stringify(workflow), { status: 201 })
  })
})
afterEach(() => vi.restoreAllMocks())

describe('CanvasShell', () => {
  it('loads dynamic palette and adds/configures a tool node', async () => {
    render(<CanvasShell />)
    const palettePanel = await screen.findByLabelText('Palette công cụ')
    expect(palettePanel).not.toHaveClass('is-open')
    fireEvent.click(screen.getByRole('button',{name:'Mở công cụ'}))
    expect(palettePanel).toHaveClass('is-open')
    expect(screen.getByRole('textbox',{name:'Tìm công cụ'})).toBeInTheDocument()
    const add = await screen.findByRole('button', { name: 'Thêm text.generate' })
    fireEvent.click(add)
    const node=await screen.findByLabelText('Node text.generate')
    expect(node).toBeInTheDocument()
    const inline=within(node).getByRole('textbox',{name:'Nội dung trực tiếp trong node'})
    fireEvent.change(inline,{target:{value:'Viết ngay trong node'}})
    expect(inline).toHaveValue('Viết ngay trong node')
    const title=within(node).getByRole('textbox',{name:'Tên hiển thị node'})
    fireEvent.change(title,{target:{value:'Lời dẫn mở đầu'}})
    expect(title).toHaveValue('Lời dẫn mở đầu')
    fireEvent.click(node)
    const prompt = screen.getByRole('textbox', { name: /Mô tả/ })
    fireEvent.change(prompt, { target: { value: 'Chủ đề mới' } })
    expect(prompt).toHaveValue('Chủ đề mới')
    fireEvent.keyDown(window,{key:'Escape'})
    expect(screen.queryByRole('region',{name:'Cấu hình nhanh text.generate'})).not.toBeInTheDocument()
  })

  it('provides undo/redo and accessible regions', async () => {
    render(<CanvasShell />)
    fireEvent.click(await screen.findByRole('button',{name:'Mở công cụ'}))
    const add = await screen.findByRole('button', { name: 'Thêm text.generate' })
    expect(screen.getByRole('region', { name: 'LTT Agent Canvas' })).toBeInTheDocument()
    fireEvent.click(add)
    const undo = screen.getByRole('button', { name: 'Hoàn tác' })
    await waitFor(() => expect(undo).toBeEnabled())
    fireEvent.click(undo)
    expect(screen.queryByLabelText('Node text.generate')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Làm lại' }))
    expect(screen.getByLabelText('Node text.generate')).toBeInTheDocument()
  })

  it('opens layers and keyboard command palette with working display toggles', async () => {
    render(<CanvasShell />)
    await screen.findByRole('button',{name:'Thêm text.generate'})
    fireEvent.click(screen.getByRole('button',{name:'Lớp'}))
    expect(screen.getByRole('complementary',{name:'Danh sách lớp'})).toBeInTheDocument()
    fireEvent.keyDown(window,{key:'k',ctrlKey:true})
    expect(screen.getByRole('dialog',{name:'Bảng lệnh Canvas'})).toBeInTheDocument()
    fireEvent.change(screen.getByRole('textbox',{name:'Tìm lệnh'}),{target:{value:'lưới'}})
    fireEvent.click(screen.getByRole('button',{name:'Ẩn lưới'}))
    expect(screen.getByRole('button',{name:'Lưới'})).toHaveAttribute('aria-pressed','false')
  })

  it('exposes responsive panel controls without hiding inspector semantics', async () => {
    render(<CanvasShell />)
    await screen.findByRole('button',{name:'Thêm text.generate'})
    expect(screen.getByRole('navigation',{name:'Khu vực Canvas'})).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button',{name:'Inspector'}))
    expect(screen.getByRole('button',{name:'Inspector'})).toHaveAttribute('aria-pressed','true')
    expect(screen.getByLabelText('Run inspector')).toHaveTextContent('Kiểm tra workflow')
  })

  it('upgrades legacy canvas and manages pages and annotations', async () => {
    render(<CanvasShell />)
    await screen.findByRole('button',{name:'Thêm text.generate'})
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
    expect(screen.getByRole('button',{name:'Thêm text.generate'})).toHaveTextContent('Tạo văn bản')
    expect(screen.getByRole('button',{name:'Thêm text.script'})).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button',{name:'Chỉ hiện công cụ chính'}))
    expect(screen.queryByRole('button',{name:'Thêm text.script'})).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button',{name:'Chuyển sang nền sáng'}))
    expect(canvas).toHaveClass('theme-light')
    await waitFor(()=>expect(globalThis.fetch).toHaveBeenCalledWith('/agent/api/preferences',expect.objectContaining({method:'PUT'})))
  })

  it('provides pane and node context menus without exposing raw tool fields',async()=>{
    render(<CanvasShell />)
    fireEvent.click(await screen.findByRole('button',{name:'Mở công cụ'}))
    fireEvent.click(screen.getByRole('button',{name:'Thêm image.generate'}))
    const node=await screen.findByLabelText('Node image.generate')
    expect(screen.getByRole('textbox',{name:/Mô tả/})).toBeInTheDocument()
    expect(screen.queryByText('app_slug')).not.toBeInTheDocument()
    fireEvent.contextMenu(node,{clientX:400,clientY:300})
    expect(screen.getByRole('complementary',{name:'Menu thao tác node'})).toHaveTextContent('Chạy từ đây')
    fireEvent.click(screen.getByRole('button',{name:'Đóng menu ngữ cảnh'}))
    fireEvent.contextMenu(document.querySelector('.react-flow__pane')!,{clientX:600,clientY:250})
    expect(screen.getByRole('complementary',{name:'Menu khoảng trống Canvas'})).toHaveTextContent('Tự động sắp xếp node')
  })

  it('connects a compatible node through the contextual @ reference picker',async()=>{
    render(<CanvasShell />)
    fireEvent.click(await screen.findByRole('button',{name:'Mở công cụ'}))
    fireEvent.click(screen.getByRole('button',{name:'Thêm image.generate'}))
    fireEvent.click(screen.getByRole('button',{name:'Thêm image.upscale'}))
    const transform=await screen.findByLabelText('Node image.upscale')
    fireEvent.click(transform)
    expect(within(transform).queryByLabelText('Tải lên')).not.toBeInTheDocument()
    const picker=screen.getByRole('combobox',{name:'Tham chiếu đầu vào'})
    expect(picker).toHaveTextContent('@Tạo hình ảnh · Hình ảnh → Ảnh đầu vào')
    const option=screen.getByRole('option',{name:/@Tạo hình ảnh/}) as HTMLOptionElement
    fireEvent.change(picker,{target:{value:option.value}})
    expect(await screen.findByLabelText('Đầu vào đã kết nối')).toHaveTextContent('@Tạo hình ảnh')
    fireEvent.click(screen.getByRole('button',{name:'Tháo kết nối Tạo hình ảnh'}))
    expect(screen.queryByLabelText('Đầu vào đã kết nối')).not.toBeInTheDocument()
    await waitFor(()=>expect(vi.mocked(globalThis.fetch).mock.calls.some(([,init])=>{
      if(init?.method!=='PUT'||typeof init.body!=='string')return false
      return JSON.parse(init.body).canvas?.pages?.[0]?.edges?.length===0
    })).toBe(true),{timeout:1800})
  })

  it('keeps multiple scalar sources connected to one collection input',async()=>{
    render(<CanvasShell />)
    fireEvent.click(await screen.findByRole('button',{name:'Mở công cụ'}))
    fireEvent.click(screen.getByRole('button',{name:'Thêm video.generate'}))
    fireEvent.click(screen.getByRole('button',{name:'Thêm video.generate'}))
    fireEvent.click(screen.getByRole('button',{name:'Thêm media.merge_video'}))
    fireEvent.click(await screen.findByLabelText('Node media.merge_video'))
    let picker=screen.getByRole('combobox',{name:'Tham chiếu đầu vào'}) as HTMLSelectElement
    const first=[...picker.options].find(option=>option.value)!
    fireEvent.change(picker,{target:{value:first.value}})
    picker=screen.getByRole('combobox',{name:'Tham chiếu đầu vào'}) as HTMLSelectElement
    const second=[...picker.options].find(option=>option.value&&option.value!==first.value)!
    fireEvent.change(picker,{target:{value:second.value}})
    expect(await screen.findByLabelText('Đầu vào đã kết nối')).toHaveTextContent('Video → Video đầu vào')
    expect(screen.getAllByRole('button',{name:'Tháo kết nối Tạo video'})).toHaveLength(2)
    expect(screen.getAllByText(/3 node · 2 kết nối/).length).toBeGreaterThan(0)
    fireEvent.click(screen.getAllByRole('button',{name:'Tháo kết nối Tạo video'})[0])
    expect(screen.getAllByRole('button',{name:'Tháo kết nối Tạo video'})).toHaveLength(1)
    expect(screen.getAllByText(/3 node · 1 kết nối/).length).toBeGreaterThan(0)
  })

  it('supports direct creation and workspace shortcuts without hijacking text input',async()=>{
    render(<CanvasShell />)
    const canvas=await screen.findByRole('region',{name:'LTT Agent Canvas'})
    fireEvent.keyDown(canvas,{key:'i'})
    expect(await screen.findByLabelText('Node image.generate')).toBeInTheDocument()
    fireEvent.keyDown(canvas,{key:'t'})
    const text=await screen.findByLabelText('Node text.generate')
    expect(text).toBeInTheDocument()
    fireEvent.keyDown(canvas,{key:'n'})
    expect(screen.getByLabelText('Sticky note Ghi chú mới')).toBeInTheDocument()
    fireEvent.keyDown(canvas,{key:'d'})
    expect(screen.getByLabelText('Palette công cụ')).toHaveClass('workspace-only')
    const inline=within(text).getByRole('textbox',{name:'Nội dung trực tiếp trong node'})
    fireEvent.keyDown(inline,{key:'i'})
    expect(screen.getAllByLabelText('Node image.generate')).toHaveLength(1)
  })

  it('keeps Upload and Generate as two modes of the same user-facing Image node',async()=>{
    render(<CanvasShell />)
    fireEvent.click(await screen.findByRole('button',{name:'Mở công cụ'}))
    fireEvent.click(screen.getByRole('button',{name:'Thêm image.generate'}))
    const generated=await screen.findByLabelText('Node image.generate')
    fireEvent.change(within(generated).getByLabelText('Tải lên'),{target:{files:[new File(['png'],'owned.png',{type:'image/png'})]}})
    const uploaded=await screen.findByLabelText('Node asset.image')
    expect(within(uploaded).getByRole('textbox',{name:'Tên hiển thị node'})).toHaveValue('Hình ảnh')
    expect(within(uploaded).getByRole('img',{name:'Ảnh đã tải lên'})).toHaveAttribute('src','/agent/api/assets/owned.png')
    expect(within(uploaded).getByRole('button',{name:'Tạo bằng AI'})).toBeInTheDocument()
    fireEvent.click(within(uploaded).getByRole('button',{name:'Tạo bằng AI'}))
    expect(await screen.findByLabelText('Node image.generate')).toBeInTheDocument()
    expect(screen.getByRole('textbox',{name:/Mô tả/})).toBeInTheDocument()
  })

  it('presents Social Video as a URL action and never as a local upload node',async()=>{
    render(<CanvasShell />)
    fireEvent.click(await screen.findByRole('button',{name:'Mở công cụ'}))
    fireEvent.click(screen.getByRole('button',{name:'Thêm video.social_import'}))
    const node=await screen.findByLabelText('Node video.social_import')
    expect(within(node).getByRole('textbox',{name:'Tên hiển thị node'})).toHaveValue('Social Video')
    expect(within(node).getByText('Thêm Social Video')).toBeInTheDocument()
    expect(within(node).queryByLabelText('Tải lên')).not.toBeInTheDocument()
    expect(screen.getByRole('textbox',{name:/Liên kết/})).toHaveAttribute('placeholder',
      'Dán link TikTok, YouTube Shorts hoặc Reels…')
    expect(screen.getByRole('checkbox',{name:'Tôi xác nhận có quyền sử dụng video'})).toBeInTheDocument()
  })

  it('keeps multiple uploads inside one Batch Images node and can switch back to generation',async()=>{
    render(<CanvasShell />)
    fireEvent.click(await screen.findByRole('button',{name:'Mở công cụ'}))
    fireEvent.click(screen.getByRole('button',{name:'Thêm image.batch_generate'}))
    const generated=await screen.findByLabelText('Node image.batch_generate')
    const files=[new File(['a'],'a.png',{type:'image/png'}),new File(['b'],'b.png',{type:'image/png'})]
    fireEvent.change(within(generated).getByLabelText('Tải lên'),{target:{files}})
    const uploaded=await screen.findByLabelText('Node asset.images')
    expect(within(uploaded).getByRole('textbox',{name:'Tên hiển thị node'})).toHaveValue('Bộ ảnh')
    expect(within(uploaded).getAllByRole('img')).toHaveLength(2)
    expect(within(uploaded).getByRole('img',{name:'Ảnh 1 trong bộ ảnh'})).toHaveAttribute('src','/agent/api/assets/a.png')
    fireEvent.click(within(uploaded).getByRole('button',{name:'Tạo bằng AI'}))
    expect(await screen.findByLabelText('Node image.batch_generate')).toBeInTheDocument()
  })
})

it('renders server run checkpoints, costs, decisions and artifacts',()=>{
  render(<RunInspector run={{id:'r1',version:2,status:'done',estimated:8,actual:6,
    quote_hash:'hash',plan:{steps:[{id:'step-1'}]},checkpoint:{'step-1':{status:'done'}},
    decisions:[{event:'approved'}],artifacts:[{step_id:'step-1',name:'video.mp4',url:'/artifact'}]}}/>)
  const inspector=screen.getByLabelText('Run inspector')
  expect(inspector).toHaveTextContent('Hoàn tất')
  expect(inspector).toHaveTextContent('6 credit')
  expect(screen.getByRole('link',{name:'video.mp4'})).toHaveAttribute('href','/artifact')
})

it('shows run failure context, history selection and snapshot replay',()=>{
  const onSelect=vi.fn();const onReplay=vi.fn();const onRestore=vi.fn()
  const run={id:'run-current',version:2,status:'error',estimated:8,actual:3,
    quote_hash:'hash',plan:{steps:[{id:'step-1'}]},checkpoint:{'step-1':{status:'error',error:'provider timeout'}},
    decisions:[],artifacts:[]}
  render(<RunInspector run={{...run,scheduled_at:'2026-08-04T02:00:00.000Z'}} history={[{id:'run-old',version:1,status:'done',estimated:5,actual:4,
    created_at:'2026-08-03',finished_at:'2026-08-03'}]} onSelect={onSelect} onReplay={onReplay} onRestore={onRestore}/>)
  expect(screen.getByLabelText('Run inspector')).toHaveTextContent('provider timeout')
  fireEvent.click(screen.getByRole('button',{name:/Replay từ snapshot này/}))
  expect(onReplay).toHaveBeenCalledWith(expect.objectContaining({id:'run-current'}))
  fireEvent.click(screen.getByRole('button',{name:/Khôi phục thành workflow mới/}))
  expect(onRestore).toHaveBeenCalledWith(expect.objectContaining({id:'run-current'}))
  fireEvent.click(screen.getByRole('button',{name:/run-old/}))
  expect(onSelect).toHaveBeenCalledWith('run-old')
})
