import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { friendlyStudioError, StudioShell } from '../src/StudioShell'
import { RenderPanel } from '../src/RenderPanel'
import { normalizeStyle, type StudioProject } from '../src/studioApi'
import { auditTranscript } from '../src/TranscriptQuality'

afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks() })

it('localizes an offline autosave failure without claiming the draft was saved', () => {
  expect(friendlyStudioError(new TypeError('Failed to fetch')))
    .toBe('Mất kết nối — thay đổi chưa được lưu.')
  expect(friendlyStudioError(new Error('Máy chủ từ chối'))).toBe('Máy chủ từ chối')
})

it('audits transcript timing, reading speed and line budget deterministically', () => {
  const track={id:'t',kind:'source' as const,language:'vi',name:'VI',visible:true,
    z_index:0,style_id:'default',cues:[
      {id:'a',start:0,end:.2,text:'',speaker:'',words:[]},
      {id:'b',start:.1,end:1,text:'Một nội dung rất dài để vượt tốc độ đọc',speaker:'S1',words:[]}]}
  const report=auditTranscript(track,10,2)
  expect(report.score).toBe(55)
  expect(report.issues.map(item=>item.code)).toEqual(['empty','short','overlap','speed','length'])
})

it('renders real empty project state without fake media or jobs', async () => {
  const project = { id:'p1', name:'Dự án test', revision:1, status:'active', payload:{
    schema_version:1, active_step:'upload', source:{ key:'', filename:'', duration_s:0,
      width:0, height:0 }, tracks:[], speakers:{}, style:{preset:'default'},
      output:{resolution:'source', format:'mp4',quality:'standard',track_ids:[],
        export_srt:true,export_vtt:true,export_json:true,export_ass:true,bundle_zip:true} } }
  vi.spyOn(globalThis, 'fetch').mockImplementation(async input => {
    const url=String(input); if(url.endsWith('/api/styles'))return new Response(JSON.stringify({items:[]}),{status:200})
    if(url.endsWith('/api/projects'))return new Response(JSON.stringify({items:[{id:'p1',status:'active'}]}),{status:200})
    return new Response(JSON.stringify(project),{status:200})
  })
  render(<StudioShell csrfToken="csrf"/>)
  await waitFor(() => expect(screen.getByDisplayValue('Dự án test')).toBeInTheDocument())
  expect(screen.getByText('Upload video để bắt đầu')).toBeInTheDocument()
  expect(screen.getByRole('button', {name:/WhisperX/})).toBeDisabled()
  expect(screen.queryByText(/job giả/i)).not.toBeInTheDocument()
})

it('opens a real cue from a multi-track timeline and edits its content', async () => {
  const project = { id:'p2', name:'Editor test', revision:3, status:'active', payload:{
    schema_version:1, active_step:'transcript', source:{ key:'media/source.mp4',
      filename:'source.mp4', duration_s:10, width:1920, height:1080 }, tracks:[{
        id:'track-source', kind:'source', language:'vi', name:'Tiếng Việt', visible:true,
        z_index:0, style_id:'default', cues:[{id:'cue-1',start:1,end:3,
          text:'Xin chào LTT',speaker:'SPEAKER_00',words:[]}]
      }, { id:'track-en', kind:'translation', language:'en', name:'English', visible:true,
        z_index:1, style_id:'default', cues:[] }], speakers:{}, style:{preset:'default'},
      output:{resolution:'source',format:'mp4',quality:'standard',track_ids:[],
        export_srt:true,export_vtt:true,export_json:true,export_ass:true,bundle_zip:true} } }
  vi.spyOn(globalThis, 'fetch').mockImplementation(async input => {
    const url=String(input);if(url.endsWith('/api/styles'))return new Response(JSON.stringify({items:[]}),{status:200})
    if(url.endsWith('/api/projects'))return new Response(JSON.stringify({items:[{id:'p2',status:'active'}]}),{status:200})
    return new Response(JSON.stringify(project),{status:200})
  })
  render(<StudioShell csrfToken="csrf"/>)
  const cue=await screen.findAllByRole('button',{name:/Xin chào LTT/})
  fireEvent.click(cue[cue.length-1])
  const editor=screen.getByRole('textbox',{name:'Nội dung cue'})
  expect(editor).toHaveValue('Xin chào LTT')
  fireEvent.change(editor,{target:{value:'Nội dung đã sửa'}})
  expect(editor).toHaveValue('Nội dung đã sửa')
  expect(screen.getByRole('combobox',{name:'Track phụ đề'})).toHaveValue('track-source')
  fireEvent.click(screen.getByRole('button',{name:'STYLE'}))
  expect(screen.getByRole('slider',{name:'Cỡ chữ'})).toHaveValue('48')
  fireEvent.change(screen.getByRole('slider',{name:'Cỡ chữ'}),{target:{value:'64'}})
  expect(screen.getByRole('slider',{name:'Cỡ chữ'})).toHaveValue('64')
})

it('shows the server quote before any render submission', async () => {
  const project = { id:'p3', name:'Render test', revision:4, status:'active', payload:{
    schema_version:1, active_step:'render', source:{key:'autosubvideo/u/uploads/a.mp4',
      filename:'a.mp4',duration_s:61,width:1280,height:720}, tracks:[{id:'source',
      kind:'source',language:'vi',name:'Tiếng Việt',visible:true,z_index:0,
      style_id:'default',cues:[{id:'cue-1',start:0,end:2,text:'Xin chào',speaker:'',words:[]}]}],
    speakers:{},style:{preset:'default'},output:{resolution:'1080p',format:'mp4',
      quality:'high',track_ids:['source'],export_srt:true,export_vtt:true,export_json:true,
      export_ass:true,bundle_zip:true}}}
  const fetch=vi.spyOn(globalThis,'fetch').mockImplementation(async input=>{
    const url=String(input)
    if(url.endsWith('/api/styles'))return new Response(JSON.stringify({items:[]}),{status:200})
    if(url.endsWith('/api/capabilities'))return new Response(JSON.stringify({whisperx:false,
      diarization:false,translation:false,credit:{transcribe:0,diarize:0,translate:0}}),{status:200})
    if(url.endsWith('/api/projects'))return new Response(JSON.stringify({items:[{id:'p3',status:'active'}]}),{status:200})
    if(url.endsWith('/quote'))return new Response(JSON.stringify({quote:{credit:8,vnd:800,
      minutes:1.02,quality:'high',resolution:'1080p',format:'mp4',track_ids:['source'],
      project_revision:4,preflight:{score:85,error_count:0,warning_count:3,
        issue_codes:['speed']}}}),{status:200})
    return new Response(JSON.stringify(project),{status:200})
  })
  render(<StudioShell csrfToken="csrf"/>)
  fireEvent.click(await screen.findByRole('button',{name:'Báo giá & xuất video'}))
  const dialog=await screen.findByRole('dialog',{name:'Xác nhận chi phí'})
  expect(dialog).toHaveTextContent('8 credit')
  expect(dialog).toHaveTextContent('Transcript còn 3 cảnh báo')
  expect(fetch.mock.calls.some(([url])=>String(url).endsWith('/render'))).toBe(false)
  fireEvent.click(screen.getByRole('button',{name:'Hủy'}))
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
})

it('keeps render progress separate from auxiliary AI progress', async () => {
  const project = { id:'p-render', name:'Render lifecycle', revision:2, status:'active', payload:{
    schema_version:1, active_step:'render', source:{key:'autosubvideo/u/uploads/a.mp4',
      filename:'a.mp4',duration_s:10,width:1280,height:720}, tracks:[{id:'source',
      kind:'source',language:'vi',name:'Tiếng Việt',visible:true,z_index:0,
      style_id:'default',cues:[{id:'cue-1',start:0,end:2,text:'Xin chào',speaker:'',words:[]}]}],
    speakers:{},style:{preset:'default'},output:{resolution:'source',format:'mp4',
      quality:'standard',track_ids:['source'],export_srt:true,export_vtt:true,
      export_json:true,export_ass:true,bundle_zip:true}}}
  vi.spyOn(globalThis,'fetch').mockImplementation(async (input,init)=>{
    const url=String(input)
    if(url.endsWith('/api/styles'))return new Response(JSON.stringify({items:[]}),{status:200})
    if(url.endsWith('/api/capabilities'))return new Response(JSON.stringify({whisperx:false,
      diarization:false,translation:false,credit:{transcribe:0,diarize:0,translate:0}}),{status:200})
    if(url.endsWith('/api/projects'))return new Response(JSON.stringify({items:[{id:'p-render',status:'active'}]}),{status:200})
    if(url.endsWith('/quote'))return new Response(JSON.stringify({quote:{credit:1,vnd:100,
      minutes:.17,quality:'standard',resolution:'source',format:'mp4',track_ids:['source'],
      project_revision:2}}),{status:200})
    if(url.endsWith('/render')&&init?.method==='POST')return new Response(JSON.stringify({
      job_id:'render-job',status:'queued',quote:{credit:1}}),{status:202})
    return new Response(JSON.stringify(project),{status:200})
  })
  render(<StudioShell csrfToken="csrf"/>)
  fireEvent.click(await screen.findByRole('button',{name:'Báo giá & xuất video'}))
  fireEvent.click(await screen.findByRole('button',{name:'Xác nhận & giữ credit'}))
  expect(await screen.findByText('Đang chờ · 0%')).toBeInTheDocument()
  expect(screen.queryByRole('progressbar',{name:'Tiến độ công cụ AI'})).not.toBeInTheDocument()
})

it('polls a WhisperX job and reloads the project when transcription completes', async () => {
  const empty = { id:'p-asr', name:'ASR lifecycle', revision:2, status:'active', payload:{
    schema_version:1, active_step:'transcript', source:{key:'autosubvideo/u/source.mp4',
      filename:'source.mp4',duration_s:10,width:1280,height:720}, tracks:[], speakers:{},
    style:normalizeStyle({preset:'default'}), output:{resolution:'source',format:'mp4',quality:'standard',
      track_ids:[],export_srt:true,export_vtt:true,export_json:true,export_ass:true,bundle_zip:true}}} as StudioProject
  const complete = structuredClone(empty)
  complete.revision=3;complete.payload.tracks=[{id:'track-source',kind:'source',language:'vi',
    name:'Bản chép lời',visible:true,z_index:0,style_id:'default',cues:[{id:'cue-1',
      start:0,end:2,text:'Xin chào LTT',speaker:'',words:[]}]}]
  let projectLoads=0
  vi.spyOn(globalThis,'fetch').mockImplementation(async (input,init)=>{
    const url=String(input)
    if(url.endsWith('/api/styles'))return new Response(JSON.stringify({items:[]}),{status:200})
    if(url.endsWith('/api/capabilities'))return new Response(JSON.stringify({whisperx:true,
      diarization:false,translation:false,credit:{transcribe:0,diarize:0,translate:0}}),{status:200})
    if(url.endsWith('/api/projects'))return new Response(JSON.stringify({items:[{id:'p-asr',status:'active'}]}),{status:200})
    if(url.includes('/api/jobs?'))return new Response(JSON.stringify({items:[]}),{status:200})
    if(url.endsWith('/transcribe')&&init?.method==='POST')return new Response(JSON.stringify({
      job_id:'asr-job-12345678',status:'queued',credit:0}),{status:202})
    if(url.endsWith('/api/jobs/asr-job-12345678'))return new Response(JSON.stringify({
      id:'asr-job-12345678',type:'autosubvideo.transcribe',status:'done',progress:100,
      message:'chép lời hoàn tất',error:'',result:{}}),{status:200})
    if(url.endsWith('/api/projects/p-asr')){projectLoads+=1;return new Response(JSON.stringify(
      projectLoads===1?empty:complete),{status:200})}
    return new Response(JSON.stringify(empty),{status:200})
  })
  render(<StudioShell csrfToken="csrf"/>)
  fireEvent.click(await screen.findByRole('button',{name:/WhisperX/}))
  await waitFor(() => expect(screen.getByRole('status'))
    .toHaveTextContent('AI auxiliary hoàn tất · 0 credit'), {timeout:10_000})
  expect(screen.getByText('1 track · 1 cue')).toBeInTheDocument()
  expect(screen.getAllByText('Xin chào LTT').length).toBeGreaterThan(0)
})

it('marks completed render artifacts as browser downloads', () => {
  const project={id:'p-download',name:'Download',revision:1,status:'active',payload:{
    schema_version:1,active_step:'render',source:{key:'source.mp4',filename:'source.mp4',
      duration_s:10,width:1280,height:720},tracks:[],speakers:{},style:normalizeStyle({preset:'default'}),
    output:{resolution:'source',format:'mp4',quality:'standard',track_ids:[],export_srt:true,
      export_vtt:true,export_json:true,export_ass:true,bundle_zip:true}}} as StudioProject
  render(<RenderPanel project={project} csrf="csrf" job={{id:'job-download',
    type:'autosubvideo.render',status:'done',progress:100,message:'',error:'',result:{
      video_key:'render.mp4',ass_key:'sub.ass',bundle_key:'subtitle-bundle.zip'}}}
    onJob={()=>{}} onChange={()=>{}} onMessage={()=>{}}/>)
  expect(screen.getByRole('link',{name:'Tải video'})).toHaveAttribute('download')
  expect(screen.getByRole('link',{name:'Tải ASS'})).toHaveAttribute('download')
  expect(screen.getByRole('link',{name:'Tải ZIP'})).toHaveAttribute('download')
})

it('reports optional AI capabilities honestly and exposes the active workflow step', async () => {
  const project = { id:'p4', name:'Capability test', revision:1, status:'active', payload:{
    schema_version:1, active_step:'transcript', source:{key:'',filename:'',duration_s:0,width:0,height:0},
    tracks:[],speakers:{},style:{preset:'default'},output:{resolution:'source',format:'mp4',
      quality:'standard',track_ids:[],export_srt:true,export_vtt:true,export_json:true,
      export_ass:true,bundle_zip:true}}}
  vi.spyOn(globalThis,'fetch').mockImplementation(async input=>{
    const url=String(input)
    if(url.endsWith('/api/styles'))return new Response(JSON.stringify({items:[]}),{status:200})
    if(url.endsWith('/api/capabilities'))return new Response(JSON.stringify({whisperx:true,
      diarization:false,translation:true,credit:{transcribe:0,diarize:0,translate:0}}),{status:200})
    if(url.endsWith('/api/projects'))return new Response(JSON.stringify({items:[{id:'p4',status:'active'}]}),{status:200})
    return new Response(JSON.stringify(project),{status:200})
  })
  render(<StudioShell csrfToken="csrf"/>)
  const capabilities=await screen.findByLabelText('Trạng thái công cụ AI')
  expect(capabilities).toHaveTextContent('WhisperXTranscript và word timingSẵn sàng')
  expect(capabilities).toHaveTextContent('PyannotePhân vai ẩn danhChưa cấu hình')
  expect(capabilities).toHaveTextContent('LTT LLMDịch transcript theo cueSẵn sàng')
  expect(screen.getByRole('button',{name:/Transcript/})).toHaveAttribute('aria-current','step')
})
