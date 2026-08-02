import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { StudioShell } from '../src/StudioShell'

afterEach(() => vi.restoreAllMocks())

it('renders real empty project state without fake media or jobs', async () => {
  const project = { id:'p1', name:'Dự án test', revision:1, status:'active', payload:{
    schema_version:1, active_step:'upload', source:{ key:'', filename:'', duration_s:0,
      width:0, height:0 }, tracks:[], speakers:{}, style:{preset:'default'},
      output:{resolution:'source', format:'mp4'} } }
  vi.spyOn(globalThis, 'fetch')
    .mockResolvedValueOnce(new Response(JSON.stringify({items:[{id:'p1',status:'active'}]}), {status:200}))
    .mockResolvedValueOnce(new Response(JSON.stringify(project), {status:200}))
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
      output:{resolution:'source',format:'mp4'} } }
  vi.spyOn(globalThis, 'fetch')
    .mockResolvedValueOnce(new Response(JSON.stringify({items:[{id:'p2',status:'active'}]}),{status:200}))
    .mockResolvedValueOnce(new Response(JSON.stringify(project),{status:200}))
  render(<StudioShell csrfToken="csrf"/>)
  const cue=await screen.findAllByRole('button',{name:/Xin chào LTT/})
  fireEvent.click(cue[cue.length-1])
  const editor=screen.getByRole('textbox',{name:'Nội dung cue'})
  expect(editor).toHaveValue('Xin chào LTT')
  fireEvent.change(editor,{target:{value:'Nội dung đã sửa'}})
  expect(editor).toHaveValue('Nội dung đã sửa')
  expect(screen.getByRole('combobox',{name:'Track phụ đề'})).toHaveValue('track-source')
})
