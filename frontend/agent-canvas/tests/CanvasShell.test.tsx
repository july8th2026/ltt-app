import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { CanvasShell } from '../src/CanvasShell'
import { RunInspector } from '../src/RunInspector'

const palette = { version: 1, tools: [
  { name: 'text.generate', label:'Tạo văn bản',category:'content',primary:true,description:'Tạo nội dung từ yêu cầu',
    app_slug:'kichban',app_name:'Kịch bản',requires:['api'],verifiable:[],params_schema:{prompt:{type:'text',required:true}},returns:{text:'text'} },
  { name: 'image.generate', label:'Tạo hình ảnh',category:'content',primary:true,description:'Tạo ảnh từ mô tả',
    app_slug:'taoanh',app_name:'Tạo ảnh',requires:['gpu'],verifiable:[],params_schema:{prompt:{type:'text',required:true}},returns:{image:'image'} },
  { name: 'video.generate', label:'Tạo video',category:'content',primary:true,description:'Tạo video từ mô tả',
    app_slug:'seedance',app_name:'Seedance',requires:['gpu'],verifiable:[],params_schema:{prompt:{type:'text',required:true}},returns:{video:'video'} },
  { name: 'image.upscale', label:'Nâng cấp ảnh',category:'transform',primary:false,description:'Tăng độ nét ảnh',
    app_slug:'upscale',app_name:'Upscale',requires:['gpu'],verifiable:[],params_schema:{image_key:{type:'image',required:true}},returns:{image:'image'} },
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
    expect(within(node).queryByRole('textbox')).not.toBeInTheDocument()
    fireEvent.click(node)
    const prompt = screen.getByRole('textbox', { name: /Mô tả/ })
    fireEvent.change(prompt, { target: { value: 'Chủ đề mới' } })
    expect(prompt).toHaveValue('Chủ đề mới')
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
    fireEvent.click(await screen.findByLabelText('Node image.upscale'))
    const picker=screen.getByRole('combobox',{name:'Tham chiếu đầu vào'})
    expect(picker).toHaveTextContent('@Tạo hình ảnh · Hình ảnh → Ảnh đầu vào')
    const option=screen.getByRole('option',{name:/@Tạo hình ảnh/}) as HTMLOptionElement
    fireEvent.change(picker,{target:{value:option.value}})
    await waitFor(()=>expect(vi.mocked(globalThis.fetch).mock.calls.some(([,init])=>{
      if(init?.method!=='PUT'||typeof init.body!=='string')return false
      return JSON.parse(init.body).canvas?.pages?.[0]?.edges?.length===1
    })).toBe(true),{timeout:1800})
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
