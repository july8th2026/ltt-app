import { afterEach, describe, expect, it, vi } from 'vitest'
import { attachSource, createAutosave, DEFAULT_STYLE, loadOrCreateProject, ProjectConflictError, saveProject,
  type StudioProject } from '../src/studioApi'

const payload = { schema_version: 1 as const, active_step: 'upload' as const,
  source: { key:'', filename:'', duration_s:0, width:0, height:0 }, tracks: [],
  speakers: {}, style: DEFAULT_STYLE, output: { resolution:'source' as const,
    format:'mp4' as const,quality:'standard' as const,track_ids:[],export_srt:true,
    export_vtt:true,export_json:true,export_ass:true,bundle_zip:true } }
const project: StudioProject = { id:'p1', name:'P', revision:1, status:'active', payload }

afterEach(() => vi.restoreAllMocks())

describe('project API', () => {
  it('loads the newest active project', async () => {
    const fetch = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(JSON.stringify({ items:[{ id:'p1', status:'active' }] }), { status:200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(project), { status:200 }))
    expect((await loadOrCreateProject('csrf')).id).toBe('p1')
    expect(fetch).toHaveBeenCalledTimes(2)
  })
  it('creates when no active project exists', async () => {
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(JSON.stringify({ items:[] }), { status:200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(project), { status:201 }))
    expect((await loadOrCreateProject('csrf')).revision).toBe(1)
  })
  it('sends revision and maps conflict', async () => {
    const fetch = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ detail:'stale' }), { status:409 }))
    await expect(saveProject(project, 'csrf')).rejects.toBeInstanceOf(ProjectConflictError)
    const headers = fetch.mock.calls[0][1]?.headers as Record<string,string>
    expect(headers['If-Match']).toBe('"1"')
  })
})

it('stages a Studio source through the project upload contract', async () => {
  const file=new File([new Uint8Array([0,0,0,0])],'source.mp4',{type:'video/mp4'})
  const fetch=vi.spyOn(globalThis,'fetch')
    .mockResolvedValueOnce(new Response(JSON.stringify({mode:'direct',upload_id:'up-1',
      url:'https://upload.test/source',headers:{'Content-Type':'video/mp4'}}),{status:200}))
    .mockResolvedValueOnce(new Response('',{status:200}))
    .mockResolvedValueOnce(new Response(JSON.stringify({...project,revision:2}),{status:200}))
  const saved=await attachSource(project,'csrf',file,{duration:4,width:1280,height:720},()=>{})
  expect(saved.revision).toBe(2)
  const ticket=fetch.mock.calls[0]
  expect(String(ticket[0])).toBe('/autosubvideo/api/uploads')
  expect(JSON.parse(String(ticket[1]?.body))).toMatchObject({expected_size:4,
    filename:'source.mp4',content_type:'video/mp4'})
  const attached=fetch.mock.calls[2][1]?.body as FormData
  expect(attached.get('upload_id')).toBe('up-1')
  expect(attached.get('video_key')).toBeNull()
})

it('autosave coalesces edits and flushes the latest value', async () => {
  vi.useFakeTimers(); const saved: number[] = []
  const autosave = createAutosave<number>(async value => { saved.push(value) }, 50)
  autosave.schedule(1); autosave.schedule(2); await vi.advanceTimersByTimeAsync(51)
  expect(saved).toEqual([2]); autosave.cancel(); vi.useRealTimers()
})

it('autosave serializes an edit arriving while a save is running', async () => {
  let release: (()=>void)|undefined; const saved:number[]=[]
  const autosave=createAutosave<number>(async value=>{saved.push(value)
    if(value===1)await new Promise<void>(resolve=>{release=resolve})},0)
  autosave.schedule(1); await new Promise(resolve=>setTimeout(resolve,5))
  autosave.schedule(2); release?.(); await new Promise(resolve=>setTimeout(resolve,5))
  expect(saved).toEqual([1,2]); autosave.cancel()
})
