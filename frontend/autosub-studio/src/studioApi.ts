export type StudioCue = { id: string; start: number; end: number; text: string;
  speaker: string; words: { start: number; end: number; text: string }[] }
export type StudioTrack = { id: string; kind: 'source' | 'translation' | 'custom';
  language: string; name: string; visible: boolean; z_index: number;
  style_id: string; cues: StudioCue[] }
export type StudioStyle = { preset:string; font_family:string; font_size:number;
  font_color:string; bold:boolean; italic:boolean; font_fallback:string;
  outline_color:string; outline_width:number; shadow_color:string; shadow_offset:number;
  alignment:number; margin_v:number; margin_h:number; line_spacing:number;
  bg_box:boolean; bg_color:string; bg_opacity:number; bg_padding:number;
  safe_area_percent:number; max_chars_per_line:number; max_lines:number;
  highlight_mode:'none'|'word'|'bg_flash'|'underline'|'all_text'|'keyword';
  highlight_color:string; keyword_highlights:string[]; keyword_highlight_color:string;
  animation:'none'|'fade'|'pop'|'slide_up'; animation_ms:number }
export type StylePreset = { id:string; label:string; description:string;
  config:Omit<StudioStyle,'preset'>; highlight_mode:StudioStyle['highlight_mode'];
  highlight_color:string }
export type StudioPayload = { schema_version: 1;
  active_step: 'upload' | 'transcript' | 'style' | 'render';
  source: { key: string; filename: string; duration_s: number; width: number; height: number };
  tracks: StudioTrack[]; speakers: Record<string, string>; style: StudioStyle;
  output: { resolution: 'source' | '720p' | '1080p' | '4k'; format: 'mp4' | 'mkv' | 'webm';
    quality:'draft'|'standard'|'high'; track_ids:string[]; export_srt:boolean;
    export_vtt:boolean;export_json:boolean;export_ass:boolean; bundle_zip:boolean } }
export type StudioProject = { id: string; name: string; revision: number;
  status: 'active' | 'archived'; payload: StudioPayload }
export type StudioCapabilities={whisperx:boolean;diarization:boolean;translation:boolean;
  credit:{transcribe:number;diarize:number;translate:number}}
export type StudioJob={id:string;type:string;status:string;progress:number;message:string;
  error:string;result:Record<string,unknown>;elapsed_s?:number;eta_s?:number|null;
  project_id?:string;created_at?:string}

export function studioJobStatusLabel(status:string){return ({queued:'Đang chờ',
  running:'Đang xử lý',done:'Hoàn tất',error:'Lỗi',cancelled:'Đã hủy'} as Record<string,string>)[status]||status}

export class ProjectConflictError extends Error {}

async function decode(response: Response) {
  if (response.ok) return response.json()
  if (response.status === 409) throw new ProjectConflictError('Project đã đổi ở phiên khác')
  let message = `Yêu cầu lỗi (${response.status})`
  try {
    const body = await response.json()
    message = typeof body.detail === 'string' ? body.detail : message
  } catch { /* non-json */ }
  throw new Error(message)
}

export async function loadOrCreateProject(csrf: string): Promise<StudioProject> {
  const listing = await decode(await fetch('/autosubvideo/api/projects', {
    credentials: 'same-origin',
  }))
  const active = listing.items.find((item: { status: string }) => item.status === 'active')
  if (active) return loadProject(active.id)
  return decode(await fetch('/autosubvideo/api/projects', { method: 'POST',
    credentials: 'same-origin', headers: { 'Content-Type': 'application/json',
      'X-CSRF-Token': csrf }, body: JSON.stringify({ name: 'Dự án chưa đặt tên' }) }))
}

export async function loadProject(id:string):Promise<StudioProject>{
  return decode(await fetch(`/autosubvideo/api/projects/${id}`,{credentials:'same-origin'}))
}

export async function saveProject(project: StudioProject, csrf: string,
                                  signal?: AbortSignal): Promise<StudioProject> {
  return decode(await fetch(`/autosubvideo/api/projects/${project.id}`, { method: 'PUT',
    credentials: 'same-origin', headers: { 'Content-Type': 'application/json',
      'X-CSRF-Token': csrf, 'If-Match': `"${project.revision}"` },
    body: JSON.stringify({ name: project.name, payload: project.payload }), signal }))
}

export async function attachSource(project: StudioProject, csrf: string, file: File,
                                   metadata: { duration: number; width: number; height: number },
                                   onProgress: (value: number) => void): Promise<StudioProject> {
  const ticketBody = new FormData()
  ticketBody.append('filename', file.name); ticketBody.append('content_type', file.type)
  const ticket = await decode(await fetch('/autosubvideo/upload-url', {
    method: 'POST', credentials: 'same-origin', body: ticketBody,
  }))
  const form = new FormData()
  form.append('revision', String(project.revision)); form.append('csrf_token', csrf)
  form.append('filename', file.name); form.append('duration_s', String(metadata.duration))
  form.append('width', String(metadata.width)); form.append('height', String(metadata.height))
  if (ticket.mode === 'direct') {
    const response = await fetch(ticket.url, { method: 'PUT', headers: ticket.headers, body: file })
    if (!response.ok) throw new Error(`Upload R2 lỗi (${response.status})`)
    form.append('video_key', ticket.key); onProgress(90)
  } else {
    form.append('video', file); onProgress(30)
  }
  return decode(await fetch(`/autosubvideo/api/projects/${project.id}/source`, {
    method: 'POST', credentials: 'same-origin', headers: { 'X-CSRF-Token': csrf }, body: form,
  }))
}

export async function importTranscript(project: StudioProject, csrf: string, file: File) {
  const form = new FormData(); form.append('transcript', file)
  form.append('revision', String(project.revision)); form.append('language', 'vi')
  form.append('track_name', file.name); form.append('csrf_token', csrf)
  return decode(await fetch(`/autosubvideo/api/projects/${project.id}/import`, {
    method: 'POST', credentials: 'same-origin', headers: { 'X-CSRF-Token': csrf }, body: form,
  })) as Promise<StudioProject>
}

export async function startTranscription(project: StudioProject, csrf: string) {
  return decode(await fetch(`/autosubvideo/api/projects/${project.id}/transcribe`, {
    method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json',
      'X-CSRF-Token': csrf, 'If-Match': `"${project.revision}"` },
    body: JSON.stringify({ language: '', model: 'large-v3' }),
  }))
}

export async function loadStyles():Promise<StylePreset[]> {
  const body=await decode(await fetch('/autosubvideo/api/styles',{credentials:'same-origin'}))
  return body.items
}

export async function loadCapabilities():Promise<StudioCapabilities>{
  return decode(await fetch('/autosubvideo/api/capabilities',{credentials:'same-origin'}))
}

async function startAux(project:StudioProject,csrf:string,operation:'diarize'|'translate',body:Record<string,unknown>){
  return decode(await fetch(`/autosubvideo/api/projects/${project.id}/${operation}`,{
    method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json',
      'X-CSRF-Token':csrf,'If-Match':`"${project.revision}"`},body:JSON.stringify(body)}))
}
export function startDiarization(project:StudioProject,csrf:string,min=0,max=0){
  return startAux(project,csrf,'diarize',{min_speakers:min,max_speakers:max})
}
export function startTranslation(project:StudioProject,csrf:string,trackId:string,targetLanguage:string){
  return startAux(project,csrf,'translate',{track_id:trackId,target_language:targetLanguage})
}
export async function loadStudioJob(id:string):Promise<StudioJob>{
  return decode(await fetch(`/autosubvideo/api/jobs/${id}`,{credentials:'same-origin'}))
}
export async function loadStudioJobs(projectId:string):Promise<StudioJob[]>{
  const body=await decode(await fetch(`/autosubvideo/api/jobs?project_id=${encodeURIComponent(projectId)}&limit=20`,
    {credentials:'same-origin'}))
  return Array.isArray(body.items)?body.items:[]
}
export async function cancelStudioJob(id:string,csrf:string){
  return decode(await fetch(`/autosubvideo/api/jobs/${id}/cancel`,{method:'POST',
    credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:'{}'}))
}
export type RenderQuote={credit:number;vnd:number;minutes:number;quality:string;
  resolution:string;format:string;track_ids:string[];project_revision:number}
export async function quoteRender(project:StudioProject,csrf:string){
  const body=await decode(await fetch(`/autosubvideo/api/projects/${project.id}/quote`,{
    method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json',
      'X-CSRF-Token':csrf,'If-Match':`"${project.revision}"`},
    body:JSON.stringify({output:project.payload.output})}))
  return body.quote as RenderQuote
}
export async function startRender(project:StudioProject,csrf:string){
  return decode(await fetch(`/autosubvideo/api/projects/${project.id}/render`,{
    method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json',
      'X-CSRF-Token':csrf,'If-Match':`"${project.revision}"`},
    body:JSON.stringify({output:project.payload.output})}))
}
export async function retryStudioJob(id:string,csrf:string){
  return decode(await fetch(`/autosubvideo/api/jobs/${id}/retry`,{method:'POST',
    credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:'{}'}))
}

export const DEFAULT_STYLE:StudioStyle={preset:'default',font_family:'Arial',font_size:48,
  font_color:'#FFFFFF',bold:true,italic:false,font_fallback:'Arial,Helvetica,sans-serif',
  outline_color:'#000000',outline_width:2,shadow_color:'#000000',shadow_offset:1,
  alignment:2,margin_v:30,margin_h:20,line_spacing:0,bg_box:false,bg_color:'#000000',
  bg_opacity:.5,bg_padding:10,safe_area_percent:0,max_chars_per_line:42,max_lines:2,
  highlight_mode:'none',highlight_color:'#FFD700',keyword_highlights:[],
  keyword_highlight_color:'#FF4444',animation:'none',animation_ms:180}

export function normalizeStyle(value:Partial<StudioStyle>|undefined):StudioStyle {
  return {...DEFAULT_STYLE,...value,keyword_highlights:value?.keyword_highlights||[]}
}

export function createAutosave<T>(save: (value: T, signal: AbortSignal) => Promise<void>,
                                  delayMs = 700) {
  let timer: ReturnType<typeof setTimeout> | undefined
  let controller: AbortController | undefined
  let latest: T | undefined
  let running = false
  let cancelled = false
  const flush = async () => {
    if (timer) clearTimeout(timer); timer = undefined
    if (running || latest === undefined || cancelled) return
    running = true
    try {
      while (latest !== undefined && !cancelled) {
        const value = latest; latest = undefined
        controller = new AbortController()
        await save(value, controller.signal)
      }
    } finally { running = false }
  }
  return { schedule(value: T) { if (cancelled) return; latest = value; if (timer) clearTimeout(timer)
      timer = setTimeout(() => { void flush() }, delayMs) }, flush,
    cancel() { cancelled = true; if (timer) clearTimeout(timer); controller?.abort(); latest = undefined } }
}

export function readVideoMetadata(file: File): Promise<{ duration: number; width: number; height: number }> {
  return new Promise((resolve, reject) => {
    const video = document.createElement('video'); const url = URL.createObjectURL(file)
    video.preload = 'metadata'; video.onloadedmetadata = () => {
      URL.revokeObjectURL(url); resolve({ duration: video.duration || 0,
        width: video.videoWidth || 0, height: video.videoHeight || 0 }) }
    video.onerror = () => { URL.revokeObjectURL(url); reject(new Error('Không đọc được video')) }
    video.src = url
  })
}
