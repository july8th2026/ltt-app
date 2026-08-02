import { ChangeEvent, useEffect, useMemo, useRef, useState } from 'react'
import { attachSource, createAutosave, importTranscript, loadOrCreateProject,
  ProjectConflictError, readVideoMetadata, saveProject, startTranscription,
  type StudioProject } from './studioApi'
import './studio.css'

const steps = [
  ['upload', '1', 'Upload'], ['transcript', '2', 'Transcript'],
  ['style', '3', 'Style'], ['render', '4', 'Render'],
] as const

export function StudioShell({ csrfToken }: { csrfToken: string }) {
  const [project, setProject] = useState<StudioProject | null>(null)
  const projectRef = useRef<StudioProject | null>(null)
  const [state, setState] = useState<'loading'|'ready'|'saving'|'saved'|'conflict'|'error'>('loading')
  const [message, setMessage] = useState('Đang tải project…')
  const [upload, setUpload] = useState(0)
  useEffect(() => { loadOrCreateProject(csrfToken).then(row => {
    projectRef.current = row; setProject(row); setState('ready'); setMessage('Sẵn sàng')
  }).catch(error => { setState('error'); setMessage(String(error.message || error)) }) }, [csrfToken])

  const autosave = useMemo(() => createAutosave<StudioProject>(async (draft, signal) => {
    setState('saving'); setMessage('Đang lưu…')
    try {
      const saved = await saveProject(draft, csrfToken, signal)
      projectRef.current = saved; setProject(saved); setState('saved'); setMessage('Đã lưu')
    } catch (error) {
      if (signal.aborted) return
      if (error instanceof ProjectConflictError) { setState('conflict'); setMessage(error.message) }
      else { setState('error'); setMessage(String((error as Error).message || error)) }
    }
  }), [csrfToken])
  useEffect(() => () => autosave.cancel(), [autosave])

  const mutate = (fn: (draft: StudioProject) => void) => {
    if (!projectRef.current) return
    const draft = structuredClone(projectRef.current); fn(draft)
    projectRef.current = draft; setProject(draft); autosave.schedule(draft)
  }

  const onVideo = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]; if (!file || !projectRef.current) return
    setUpload(1); setMessage('Đọc metadata…')
    try {
      const metadata = await readVideoMetadata(file)
      const saved = await attachSource(projectRef.current, csrfToken, file, metadata, setUpload)
      projectRef.current = saved; setProject(saved); setUpload(100); setState('saved'); setMessage('Đã tải video')
    } catch (error) { setState('error'); setMessage(String((error as Error).message || error)); setUpload(0) }
  }
  const onTranscript = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]; if (!file || !projectRef.current) return
    setMessage('Đang nhập transcript…')
    try { const saved = await importTranscript(projectRef.current, csrfToken, file)
      projectRef.current = saved; setProject(saved); setState('saved'); setMessage('Đã nhập transcript')
    } catch (error) { setState('error'); setMessage(String((error as Error).message || error)) }
  }
  const transcribe = async () => {
    if (!projectRef.current) return
    setMessage('Đang tạo job WhisperX…')
    try { const job = await startTranscription(projectRef.current, csrfToken)
      setMessage(`WhisperX đang chạy · job ${job.job_id.slice(0, 8)} · 0 credit`)
    } catch (error) { setState('error'); setMessage(String((error as Error).message || error)) }
  }

  if (!project) return <div className={`studio-state ${state}`}>{message}</div>
  const source = project.payload.source; const cues = project.payload.tracks.reduce(
    (total, track) => total + track.cues.length, 0)
  return <main className="studio-shell" data-save-state={state}>
    <header className="studio-topbar">
      <div className="studio-brand"><span className="studio-mark">LTT</span><strong>AUTO SUB VIDEO</strong></div>
      <ol className="studio-steps">{steps.map(([id, n, label]) => <li key={id}
        className={project.payload.active_step === id ? 'active' : ''}><button type="button"
        onClick={() => mutate(d => { d.payload.active_step = id })}><span>{n}</span>{label}</button></li>)}</ol>
      <div className={`studio-save ${state}`}>{message}</div>
    </header>
    <section className="studio-grid">
      <aside className="studio-left">
        <label className="project-label">PROJECT<input aria-label="Tên project" value={project.name}
          onChange={event => mutate(d => { d.name = event.target.value })}/></label>
        <section><h2>FILES</h2><label className="drop-zone"><input type="file" accept="video/*"
          onChange={onVideo}/><span>＋</span><strong>Kéo thả hoặc chọn video</strong><small>MP4, MOV, MKV · tối đa 120 phút</small></label>
          {upload > 0 && upload < 100 && <progress value={upload} max="100"/>}
          {source.key && <article className="source-file"><strong>{source.filename}</strong><small>{Math.round(source.duration_s)}s · {source.width}×{source.height}</small></article>}
        </section>
        <section><h2>TRANSCRIPT</h2><div className="quick-actions"><label className="subtle-button">Nhập SRT/VTT/ASS<input type="file" accept=".srt,.vtt,.ass,.ssa,.json" onChange={onTranscript}/></label>
          <button type="button" onClick={transcribe} disabled={!source.key}>WhisperX · 0 credit</button></div>
          <p className="count-line">{project.payload.tracks.length} track · {cues} cue</p></section>
      </aside>
      <section className="studio-stage">
        <div className="preview-toolbar"><span>Fit (100%)</span><span>{source.width && source.height ? `${source.width}:${source.height}` : '16:9'}</span></div>
        <div className="video-canvas">{source.key ? <video controls preload="metadata"
          src={`/autosubvideo/v/${source.key}`} /> : <div className="empty-preview"><span>▶</span><strong>Video preview</strong><small>Upload video để bắt đầu</small></div>}</div>
        <div className="transport"><button aria-label="Về đầu">|◀</button><button aria-label="Phát">▶</button><button aria-label="Tới cuối">▶|</button><span>00:00:00 / {formatTime(source.duration_s)}</span></div>
        <div className="timeline-placeholder"><div className="ruler">00:00 <span>00:05</span><span>00:10</span><span>00:15</span></div><div className="track-row"><strong>CC</strong><span>{cues ? `${cues} cue đã sẵn sàng` : 'Timeline sẽ xuất hiện khi có transcript'}</span></div></div>
      </section>
      <aside className="studio-right"><nav><button className="active">TEMPLATES</button><button>STYLE</button><button>ANIMATION</button></nav>
        <div className="template-grid">{['LTT Bold','Cinematic','Neon Punch','Kids Color','Word Emphasis','Minimal'].map(name => <button key={name} type="button" onClick={() => mutate(d => { d.payload.style = { preset: name.toLowerCase().replace(' ','_') } })}><strong>THE QUICK<br/>BROWN FOX</strong><small>{name}</small></button>)}</div>
        <section className="inspector-empty"><strong>Style inspector</strong><p>Chọn tab Style để chỉnh font, màu, stroke, shadow và karaoke.</p></section>
      </aside>
    </section>
  </main>
}

function formatTime(seconds: number) {
  const safe = Number.isFinite(seconds) ? Math.max(0, seconds) : 0
  const h = Math.floor(safe / 3600), m = Math.floor((safe % 3600) / 60), s = Math.floor(safe % 60)
  return [h, m, s].map(value => String(value).padStart(2, '0')).join(':')
}
