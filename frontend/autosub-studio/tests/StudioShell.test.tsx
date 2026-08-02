import { render, screen, waitFor } from '@testing-library/react'
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
