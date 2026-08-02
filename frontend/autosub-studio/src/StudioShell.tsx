import { ChangeEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { EditorTimeline } from './EditorTimeline'
import { attachSource, createAutosave, importTranscript, loadOrCreateProject,
  loadCapabilities, loadProject, loadStudioJob, loadStyles, normalizeStyle,
  ProjectConflictError, readVideoMetadata, saveProject, startDiarization,
  startTranscription, startTranslation, cancelStudioJob, type StudioCapabilities,
  type StudioCue, type StudioJob, type StudioProject, type StudioTrack, type StylePreset } from './studioApi'
import { StyleInspector, SubtitlePreview } from './StyleInspector'
import { RenderPanel } from './RenderPanel'
import { useProjectHistory } from './useProjectHistory'
import './studio.css'

const steps = [
  ['upload', '1', 'Upload'], ['transcript', '2', 'Transcript'],
  ['style', '3', 'Style'], ['render', '4', 'Render'],
] as const

export function StudioShell({ csrfToken }: { csrfToken: string }) {
  const [project, setProject] = useState<StudioProject | null>(null)
  const projectRef = useRef<StudioProject | null>(null)
  const videoRef = useRef<HTMLVideoElement>(null)
  const [state, setState] = useState<'loading'|'ready'|'saving'|'saved'|'conflict'|'error'>('loading')
  const [message, setMessage] = useState('Đang tải project…')
  const [upload, setUpload] = useState(0)
  const [currentTime, setCurrentTime] = useState(0)
  const [selectedTrackId, setSelectedTrackId] = useState('')
  const [selectedCueId, setSelectedCueId] = useState('')
  const [query, setQuery] = useState('')
  const [styleTab,setStyleTab]=useState<'templates'|'style'|'animation'>('templates')
  const [presets,setPresets]=useState<StylePreset[]>([])
  const [capabilities,setCapabilities]=useState<StudioCapabilities|null>(null)
  const [auxJob,setAuxJob]=useState<StudioJob|null>(null)
  const [targetLanguage,setTargetLanguage]=useState('en')

  useEffect(() => { loadOrCreateProject(csrfToken).then(row => {
    projectRef.current = row; setProject(row); setSelectedTrackId(row.payload.tracks[0]?.id||'')
    setState('ready'); setMessage('Sẵn sàng')
  }).catch(error => { setState('error'); setMessage(String(error.message || error)) }) }, [csrfToken])
  useEffect(()=>{loadStyles().then(setPresets).catch(()=>setMessage('Không tải được preset'))},[])
  useEffect(()=>{loadCapabilities().then(setCapabilities).catch(()=>setCapabilities(null))},[])
  useEffect(()=>{if(!auxJob||!['queued','running'].includes(auxJob.status))return
    const timer=window.setInterval(()=>{void loadStudioJob(auxJob.id).then(async job=>{setAuxJob(job)
      setMessage(`${job.message||job.status} · ${job.progress}%`)
      if(job.status==='done'&&projectRef.current&&job.type!=='autosubvideo.render'){const fresh=await loadProject(projectRef.current.id);projectRef.current=fresh;setProject(fresh);setSelectedTrackId(fresh.payload.tracks.at(-1)?.id||'');setMessage('AI auxiliary hoàn tất · 0 credit')}
      if(job.status==='done'&&job.type==='autosubvideo.render')setMessage('Render hoàn tất · sẵn sàng tải xuống')
      if(job.status==='error')setMessage(job.error||'Job lỗi')})},1200)
    return()=>window.clearInterval(timer)},[auxJob?.id,auxJob?.status])

  const autosave = useMemo(() => createAutosave<StudioProject>(async (draft) => {
    setState('saving'); setMessage('Đang lưu…')
    try {
      const revision = projectRef.current?.revision ?? draft.revision
      const saved = await saveProject({...draft, revision}, csrfToken)
      const current = projectRef.current
      const merged = current?.id === saved.id ? {...current, revision:saved.revision} : saved
      projectRef.current = merged; setProject(merged); setState('saved'); setMessage('Đã lưu')
    } catch (error) {
      if (error instanceof ProjectConflictError) { setState('conflict'); setMessage(error.message) }
      else { setState('error'); setMessage(String((error as Error).message || error)) }
    }
  }), [csrfToken])
  useEffect(() => () => autosave.cancel(), [autosave])

  const applyHistory = useCallback((value:StudioProject) => {
    const next={...structuredClone(value),revision:projectRef.current?.revision??value.revision}
    projectRef.current=next;setProject(next);autosave.schedule(next)
  },[autosave])
  const history=useProjectHistory(project,applyHistory)
  const mutate = useCallback((fn: (draft: StudioProject) => void, record=true) => {
    if (!projectRef.current) return
    const before=projectRef.current; const draft=structuredClone(before); fn(draft)
    if(record)history.record(before)
    projectRef.current = draft; setProject(draft); autosave.schedule(draft)
  },[autosave,history])

  useEffect(()=>{const handler=(event:KeyboardEvent)=>{if(!(event.ctrlKey||event.metaKey))return
    if(event.key.toLowerCase()==='z'){event.preventDefault();event.shiftKey?history.redo(projectRef.current):history.undo(projectRef.current)}
    if(event.key.toLowerCase()==='y'){event.preventDefault();history.redo(projectRef.current)}}
    window.addEventListener('keydown',handler);return()=>window.removeEventListener('keydown',handler)},[history])

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
      projectRef.current = saved; setProject(saved); setSelectedTrackId(saved.payload.tracks[0]?.id||'')
      setState('saved'); setMessage('Đã nhập transcript')
    } catch (error) { setState('error'); setMessage(String((error as Error).message || error)) }
  }
  const transcribe = async () => {
    if (!projectRef.current) return; setMessage('Đang tạo job WhisperX…')
    try { const job = await startTranscription(projectRef.current, csrfToken)
      setMessage(`WhisperX đang chạy · job ${job.job_id.slice(0,8)} · 0 credit`)
    } catch (error) { setState('error'); setMessage(String((error as Error).message || error)) }
  }
  const runAux=async(operation:'diarize'|'translate')=>{if(!projectRef.current)return
    setMessage(operation==='diarize'?'Đang tạo job Pyannote…':'Đang tạo job Gemini…')
    try{const trackId=selectedTrackId||projectRef.current.payload.tracks[0]?.id||''
      const response=operation==='diarize'?await startDiarization(projectRef.current,csrfToken):
      await startTranslation(projectRef.current,csrfToken,trackId,targetLanguage)
      setAuxJob({id:response.job_id,type:`autosubvideo.${operation}`,status:response.status,
        progress:0,message:'đang xếp hàng',error:'',result:{}});setMessage(`${operation} đang xếp hàng · 0 credit`)
    }catch(error){setState('error');setMessage(String((error as Error).message||error))}}

  if (!project) return <div className={`studio-state ${state}`}>{message}</div>
  const source=project.payload.source; const sourceUrl=source.key?`/autosubvideo/v/${source.key}`:''
  const selectedTrack=project.payload.tracks.find(track=>track.id===selectedTrackId)||project.payload.tracks[0]
  const selectedCue=selectedTrack?.cues.find(cue=>cue.id===selectedCueId)
  const cues=project.payload.tracks.reduce((total,track)=>total+track.cues.length,0)
  const filtered=selectedTrack?.cues.filter(cue=>cue.text.toLowerCase().includes(query.toLowerCase()))||[]

  const cueChange=(trackId:string,cueId:string,patch:Partial<StudioCue>)=>mutate(d=>{const cue=findCue(d,trackId,cueId);if(cue)Object.assign(cue,patch)})
  const addTrack=()=>mutate(d=>{const index=d.payload.tracks.length+1;const track:StudioTrack={id:`track-${crypto.randomUUID()}`,kind:'custom',language:'vi',name:`Phụ đề ${index}`,visible:true,z_index:Math.max(-1,...d.payload.tracks.map(t=>t.z_index))+1,style_id:'default',cues:[]};d.payload.tracks.push(track);setSelectedTrackId(track.id);d.payload.active_step='transcript'})
  const addCue=()=>{if(!selectedTrack)return;const start=Math.min(currentTime,Math.max(0,source.duration_s-.1));const end=Math.max(start+.05,Math.min(source.duration_s||start+2,start+2));const id=`cue-${crypto.randomUUID()}`;mutate(d=>{const track=d.payload.tracks.find(t=>t.id===selectedTrack.id);track?.cues.push({id,start,end,text:'Phụ đề mới',speaker:'',words:[]});track?.cues.sort((a,b)=>a.start-b.start)});setSelectedCueId(id)}
  const removeCue=()=>{if(!selectedTrack||!selectedCue)return;mutate(d=>{const track=d.payload.tracks.find(t=>t.id===selectedTrack.id);if(track)track.cues=track.cues.filter(c=>c.id!==selectedCue.id)});setSelectedCueId('')}
  const splitCue=()=>{if(!selectedTrack||!selectedCue)return;const at=currentTime>selectedCue.start+.05&&currentTime<selectedCue.end-.05?currentTime:(selectedCue.start+selectedCue.end)/2;const id=`cue-${crypto.randomUUID()}`;mutate(d=>{const track=d.payload.tracks.find(t=>t.id===selectedTrack.id);const cue=track?.cues.find(c=>c.id===selectedCue.id);if(!track||!cue)return;const words=cue.text.trim().split(/\s+/);const cut=Math.max(1,Math.ceil(words.length/2));const second={...cue,id,start:at,text:words.slice(cut).join(' ')||cue.text,words:[]};cue.end=at;cue.text=words.slice(0,cut).join(' ');cue.words=[];track.cues.push(second);track.cues.sort((a,b)=>a.start-b.start)});setSelectedCueId(id)}
  const mergeNext=()=>{if(!selectedTrack||!selectedCue)return;const index=selectedTrack.cues.findIndex(c=>c.id===selectedCue.id);const next=selectedTrack.cues[index+1];if(!next)return;mutate(d=>{const track=d.payload.tracks.find(t=>t.id===selectedTrack.id);const cue=track?.cues.find(c=>c.id===selectedCue.id);if(!track||!cue)return;cue.end=next.end;cue.text=`${cue.text} ${next.text}`.trim();cue.words=[];track.cues=track.cues.filter(c=>c.id!==next.id)})}
  const seek=(time:number)=>{setCurrentTime(time);if(videoRef.current)videoRef.current.currentTime=time}

  return <main className="studio-shell" data-save-state={state}>
    <header className="studio-topbar"><div className="studio-brand"><span className="studio-mark">LTT</span><strong>AUTO SUB VIDEO</strong></div>
      <ol className="studio-steps">{steps.map(([id,n,label])=><li key={id} className={project.payload.active_step===id?'active':''}><button type="button" onClick={()=>mutate(d=>{d.payload.active_step=id})}><span>{n}</span>{label}</button></li>)}</ol>
      <div className="history-tools"><button aria-label="Hoàn tác" disabled={!history.canUndo} onClick={()=>history.undo(projectRef.current)}>↶</button><button aria-label="Làm lại" disabled={!history.canRedo} onClick={()=>history.redo(projectRef.current)}>↷</button><span className={`studio-save ${state}`}>{message}</span></div></header>
    <section className="studio-grid">
      <aside className="studio-left"><label className="project-label">PROJECT<input aria-label="Tên project" value={project.name} onChange={event=>mutate(d=>{d.name=event.target.value})}/></label>
        <section><h2>FILES</h2><label className="drop-zone"><input type="file" accept="video/*" onChange={onVideo}/><span>＋</span><strong>Kéo thả hoặc chọn video</strong><small>MP4, MOV, MKV · tối đa 120 phút</small></label>{upload>0&&upload<100&&<progress value={upload} max="100"/>}{source.key&&<article className="source-file"><strong>{source.filename}</strong><small>{Math.round(source.duration_s)}s · {source.width}×{source.height}</small></article>}</section>
        <section className="transcript-panel"><h2>TRANSCRIPT</h2><div className="quick-actions"><label className="subtle-button">Nhập SRT/VTT/ASS<input type="file" accept=".srt,.vtt,.ass,.ssa,.json" onChange={onTranscript}/></label><button type="button" onClick={transcribe} disabled={!source.key}>WhisperX · 0 credit</button></div>
          <div className="track-tools"><select aria-label="Track phụ đề" value={selectedTrack?.id||''} onChange={e=>{setSelectedTrackId(e.target.value);setSelectedCueId('')}}>{project.payload.tracks.map(track=><option key={track.id} value={track.id}>{track.name} · {track.language}</option>)}</select><button onClick={addTrack} aria-label="Thêm track">＋ Track</button>{selectedTrack&&<button aria-label="Ẩn hiện track" onClick={()=>mutate(d=>{const track=d.payload.tracks.find(t=>t.id===selectedTrack.id);if(track)track.visible=!track.visible})}>{selectedTrack.visible?'◉':'○'}</button>}</div>
          <div className="ai-actions"><button onClick={()=>void runAux('diarize')} disabled={!capabilities?.diarization||!selectedTrack?.cues.length||!!auxJob&&['queued','running'].includes(auxJob.status)}>Phân vai · 0 credit</button><div><select aria-label="Ngôn ngữ dịch" value={targetLanguage} onChange={e=>setTargetLanguage(e.target.value)}><option value="en">English</option><option value="vi">Tiếng Việt</option><option value="zh">中文</option><option value="ja">日本語</option><option value="ko">한국어</option><option value="fr">Français</option><option value="de">Deutsch</option><option value="es">Español</option></select><button onClick={()=>void runAux('translate')} disabled={!capabilities?.translation||!selectedTrack?.cues.length||!!auxJob&&['queued','running'].includes(auxJob.status)}>Dịch Gemini · 0 credit</button></div>{auxJob&&<div className="aux-progress"><progress value={auxJob.progress} max="100"/><span>{auxJob.message||auxJob.status}</span>{['queued','running'].includes(auxJob.status)&&<button onClick={()=>void cancelStudioJob(auxJob.id,csrfToken).then(()=>setAuxJob({...auxJob,status:'cancelled'}))}>Hủy</button>}</div>}{capabilities&&!capabilities.diarization&&<small>Pyannote chưa cấu hình token.</small>}{capabilities&&!capabilities.translation&&<small>Gemini translation chưa cấu hình key.</small>}</div>
          <input className="cue-search" aria-label="Tìm transcript" placeholder="Tìm transcript…" value={query} onChange={e=>setQuery(e.target.value)}/>
          <div className="cue-list">{filtered.map(cue=><button type="button" key={cue.id} className={cue.id===selectedCueId?'active':''} onClick={()=>{setSelectedCueId(cue.id);seek(cue.start)}}><time>{formatTime(cue.start)}</time><span>{cue.speaker&&<b>{cue.speaker}</b>}{cue.text||'(trống)'}</span></button>)}</div><p className="count-line">{project.payload.tracks.length} track · {cues} cue</p></section>
      </aside>
      <section className="studio-stage"><div className="preview-toolbar"><span>Fit (100%)</span><span>{source.width&&source.height?`${source.width}:${source.height}`:'16:9'}</span></div>
        <div className="video-canvas">{source.key?<><video ref={videoRef} controls preload="metadata" src={sourceUrl} onTimeUpdate={e=>setCurrentTime(e.currentTarget.currentTime)}/>{selectedCue&&currentTime>=selectedCue.start&&currentTime<=selectedCue.end&&<SubtitlePreview cue={selectedCue} currentTime={currentTime} rawStyle={project.payload.style}/>}</>:<div className="empty-preview"><span>▶</span><strong>Video preview</strong><small>Upload video để bắt đầu</small></div>}</div>
        <div className="transport"><button aria-label="Về đầu" onClick={()=>seek(0)}>|◀</button><button aria-label="Phát hoặc dừng" onClick={()=>videoRef.current?.paused?void videoRef.current.play():videoRef.current?.pause()}>▶</button><button aria-label="Tới cuối" onClick={()=>seek(source.duration_s)}>▶|</button><span>{formatTime(currentTime)} / {formatTime(source.duration_s)}</span></div>
        <EditorTimeline tracks={project.payload.tracks} duration={source.duration_s} currentTime={currentTime} sourceUrl={sourceUrl} selectedCueId={selectedCueId} onSelect={setSelectedCueId} onSeek={seek} onCueChange={cueChange}/>
        <div className="cue-editor"><div className="cue-editor-tools"><button onClick={addCue} disabled={!selectedTrack}>＋ Cue</button><button onClick={splitCue} disabled={!selectedCue}>Tách</button><button onClick={mergeNext} disabled={!selectedCue}>Gộp sau</button><button onClick={removeCue} disabled={!selectedCue}>Xóa</button></div>{selectedCue?<><textarea aria-label="Nội dung cue" value={selectedCue.text} onChange={e=>cueChange(selectedTrack.id,selectedCue.id,{text:e.target.value})}/><div className="timing-inputs"><label>Bắt đầu<input aria-label="Thời gian bắt đầu" type="number" min="0" step="0.01" value={selectedCue.start} onChange={e=>cueChange(selectedTrack.id,selectedCue.id,{start:Number(e.target.value)})}/></label><label>Kết thúc<input aria-label="Thời gian kết thúc" type="number" min="0.05" step="0.01" value={selectedCue.end} onChange={e=>cueChange(selectedTrack.id,selectedCue.id,{end:Number(e.target.value)})}/></label><label>Speaker<input aria-label="Speaker" value={selectedCue.speaker} onChange={e=>cueChange(selectedTrack.id,selectedCue.id,{speaker:e.target.value})}/></label></div></>:<p>Chọn một cue trên timeline hoặc thêm cue mới.</p>}</div>
      </section>
      <aside className="studio-right">{project.payload.active_step==='render'?<RenderPanel project={project} csrf={csrfToken} job={auxJob} onJob={setAuxJob} onMessage={setMessage} onChange={fn=>mutate(fn)}/>:<StyleInspector tab={styleTab} setTab={setStyleTab}
        style={normalizeStyle(project.payload.style)} presets={presets}
        onPreset={preset=>mutate(d=>{d.payload.style=normalizeStyle({preset:preset.id,...preset.config,highlight_mode:preset.highlight_mode,highlight_color:preset.highlight_color});d.payload.active_step='style'})}
        onStyle={patch=>mutate(d=>{d.payload.style=normalizeStyle({...d.payload.style,...patch,preset:'custom'});d.payload.active_step='style'})}/>}</aside>
    </section>
  </main>
}

function findCue(project:StudioProject,trackId:string,cueId:string){return project.payload.tracks.find(track=>track.id===trackId)?.cues.find(cue=>cue.id===cueId)}
function formatTime(seconds:number){const safe=Number.isFinite(seconds)?Math.max(0,seconds):0;const h=Math.floor(safe/3600),m=Math.floor((safe%3600)/60),s=Math.floor(safe%60);return [h,m,s].map(value=>String(value).padStart(2,'0')).join(':')}
