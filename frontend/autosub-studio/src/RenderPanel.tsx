import { useState } from 'react'
import { cancelStudioJob, quoteRender, retryStudioJob, startRender,
  type RenderQuote, type StudioJob, type StudioProject } from './studioApi'

export function RenderPanel({project,csrf,job,onJob,onChange,onMessage}:{
  project:StudioProject;csrf:string;job:StudioJob|null;onJob:(job:StudioJob)=>void;
  onChange:(fn:(draft:StudioProject)=>void)=>void;onMessage:(text:string)=>void}){
  const [quote,setQuote]=useState<RenderQuote|null>(null)
  const output=project.payload.output
  const patch=(value:Partial<typeof output>)=>onChange(d=>{d.payload.output={...d.payload.output,...value};d.payload.active_step='render'})
  const getQuote=async()=>{try{setQuote(await quoteRender(project,csrf))}catch(error){onMessage(String((error as Error).message||error))}}
  const confirm=async()=>{try{const response=await startRender(project,csrf);setQuote(null)
    onJob({id:response.job_id,type:'autosubvideo.render',status:response.status,progress:0,
      message:'đang xếp hàng',error:'',result:{}});onMessage(`Đã giữ ${response.quote.credit} credit · render đang xếp hàng`)
  }catch(error){onMessage(String((error as Error).message||error))}}
  const selected=output.track_ids.length?new Set(output.track_ids):new Set(project.payload.tracks.filter(t=>t.visible).map(t=>t.id))
  const toggle=(id:string)=>{const next=new Set(selected);next.has(id)?next.delete(id):next.add(id);patch({track_ids:[...next]})}
  const active=job&&['queued','running'].includes(job.status)
  const result=job?.result||{}
  const key=(name:string)=>typeof result[name]==='string'?String(result[name]):''
  return <div className="render-panel"><h2>XUẤT VIDEO</h2>
    <label>Độ phân giải<select aria-label="Độ phân giải render" value={output.resolution} onChange={e=>patch({resolution:e.target.value as typeof output.resolution})}><option value="source">Giữ nguyên</option><option value="720p">720p</option><option value="1080p">1080p</option><option value="4k">4K</option></select></label>
    <label>Định dạng<select aria-label="Định dạng render" value={output.format} onChange={e=>patch({format:e.target.value as typeof output.format})}><option>mp4</option><option>mkv</option><option>webm</option></select></label>
    <label>Chất lượng<select aria-label="Chất lượng render" value={output.quality} onChange={e=>patch({quality:e.target.value as typeof output.quality})}><option value="draft">Nháp</option><option value="standard">Chuẩn</option><option value="high">Cao</option></select></label>
    <fieldset><legend>Track sẽ khắc</legend>{project.payload.tracks.map(track=><label key={track.id}><input type="checkbox" checked={selected.has(track.id)} disabled={!track.visible||!track.cues.length} onChange={()=>toggle(track.id)}/>{track.name} · {track.language}</label>)}</fieldset>
    <div className="export-options"><label><input type="checkbox" checked={output.export_srt} onChange={e=>patch({export_srt:e.target.checked})}/> SRT từng track</label><label><input type="checkbox" checked={output.export_vtt} onChange={e=>patch({export_vtt:e.target.checked})}/> WebVTT từng track</label><label><input type="checkbox" checked={output.export_json} onChange={e=>patch({export_json:e.target.checked})}/> JSON từng track</label><label><input type="checkbox" checked={output.export_ass} onChange={e=>patch({export_ass:e.target.checked})}/> ASS kết hợp</label><label><input type="checkbox" checked={output.bundle_zip} onChange={e=>patch({bundle_zip:e.target.checked})}/> ZIP phụ đề</label></div>
    <button className="render-primary" disabled={!project.payload.source.key||active||!selected.size} onClick={()=>void getQuote()}>Báo giá & xuất video</button>
    {job&&<section className="render-job"><strong>{job.status} · {job.progress}%</strong><progress value={job.progress} max="100"/><small>{job.message||job.error}{job.eta_s?` · còn khoảng ${Math.ceil(job.eta_s)}s`:''}</small>{active&&<button onClick={()=>void cancelStudioJob(job.id,csrf).then(()=>onJob({...job,status:'cancelled'}))}>Hủy render</button>}{['error','cancelled'].includes(job.status)&&<button onClick={()=>void retryStudioJob(job.id,csrf).then(r=>onJob({...job,id:r.job_id,status:r.status,progress:0,error:''}))}>Thử lại</button>}{job.status==='done'&&<div className="download-links">{key('video_key')&&<a href={`/autosubvideo/v/${key('video_key')}`}>Tải video</a>}{key('ass_key')&&<a href={`/autosubvideo/f/${key('ass_key')}`}>Tải ASS</a>}{key('bundle_key')&&<a href={`/autosubvideo/f/${key('bundle_key')}`}>Tải ZIP</a>}</div>}</section>}
    {quote&&<div className="credit-modal" role="dialog" aria-modal="true" aria-label="Xác nhận chi phí"><div><h3>Xác nhận xuất video</h3><strong>{quote.credit} credit</strong><p>≈ {quote.vnd.toLocaleString('vi-VN')}đ · {quote.minutes} phút · {quote.resolution} · {quote.format.toUpperCase()}</p><p>{quote.track_ids.length} track · snapshot revision {quote.project_revision}</p><footer><button onClick={()=>setQuote(null)}>Hủy</button><button className="render-primary" onClick={()=>void confirm()}>Xác nhận & giữ credit</button></footer></div></div>}
  </div>
}
