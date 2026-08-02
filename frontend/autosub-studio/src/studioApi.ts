export type StudioCue = { id: string; start: number; end: number; text: string;
  speaker: string; words: { start: number; end: number; text: string }[] }
export type StudioTrack = { id: string; kind: 'source' | 'translation' | 'custom';
  language: string; name: string; visible: boolean; z_index: number;
  style_id: string; cues: StudioCue[] }
export type StudioPayload = { schema_version: 1;
  active_step: 'upload' | 'transcript' | 'style' | 'render';
  source: { key: string; filename: string; duration_s: number; width: number; height: number };
  tracks: StudioTrack[]; speakers: Record<string, string>; style: Record<string, unknown>;
  output: { resolution: 'source' | '720p' | '1080p' | '4k'; format: 'mp4' | 'mkv' | 'webm' } }
export type StudioProject = { id: string; name: string; revision: number;
  status: 'active' | 'archived'; payload: StudioPayload }

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
  if (active) return decode(await fetch(`/autosubvideo/api/projects/${active.id}`, {
    credentials: 'same-origin',
  }))
  return decode(await fetch('/autosubvideo/api/projects', { method: 'POST',
    credentials: 'same-origin', headers: { 'Content-Type': 'application/json',
      'X-CSRF-Token': csrf }, body: JSON.stringify({ name: 'Dự án chưa đặt tên' }) }))
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
