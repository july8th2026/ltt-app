import { useMemo } from 'react'
import type { StudioCue, StudioTrack } from './studioApi'

export type TranscriptIssue={cueId:string;severity:'error'|'warning';code:string;message:string}

export function auditTranscript(track:StudioTrack|undefined,maxCharsPerLine=42,maxLines=2){
  if(!track)return {score:0,issues:[] as TranscriptIssue[]}
  const issues:TranscriptIssue[]=[];const sorted=[...track.cues].sort((a,b)=>a.start-b.start)
  sorted.forEach((cue,index)=>{
    const duration=Math.max(.01,cue.end-cue.start);const chars=cue.text.trim().length
    if(!chars)issues.push({cueId:cue.id,severity:'error',code:'empty',message:'Cue không có nội dung'})
    if(index>0&&cue.start<sorted[index-1].end)issues.push({cueId:cue.id,severity:'error',code:'overlap',message:'Chồng thời gian với cue trước'})
    if(duration<.5)issues.push({cueId:cue.id,severity:'warning',code:'short',message:'Thời lượng dưới 0,5 giây'})
    if(chars/duration>20)issues.push({cueId:cue.id,severity:'warning',code:'speed',message:`Tốc độ đọc ${Math.round(chars/duration)} ký tự/giây`})
    if(chars>maxCharsPerLine*maxLines)issues.push({cueId:cue.id,severity:'warning',code:'length',message:`Dài hơn giới hạn ${maxCharsPerLine*maxLines} ký tự`})
  })
  const score=Math.max(0,100-issues.reduce((sum,item)=>sum+(item.severity==='error'?15:5),0))
  return {score,issues}
}

export function TranscriptQuality({track,speakers,maxCharsPerLine,maxLines,onCue,onSpeaker}:{
  track:StudioTrack|undefined;speakers:Record<string,string>;maxCharsPerLine:number;maxLines:number;
  onCue:(cue:StudioCue)=>void;onSpeaker:(id:string,name:string)=>void}){
  const report=useMemo(()=>auditTranscript(track,maxCharsPerLine,maxLines),[track,maxCharsPerLine,maxLines])
  const speakerIds=useMemo(()=>[...new Set((track?.cues||[]).map(cue=>cue.speaker).filter(Boolean))].sort(),[track])
  const cueById=new Map((track?.cues||[]).map(cue=>[cue.id,cue]))
  return <section className="transcript-quality" aria-label="Kiểm tra chất lượng transcript">
    <div className="quality-head"><h2>TRANSCRIPT QA</h2><strong className={report.score>=90?'good':report.score>=70?'warn':'bad'}>{report.score}/100</strong></div>
    {track?.cues.length?<>{report.issues.length?<div className="quality-issues">{report.issues.slice(0,8).map((issue,index)=>{const cue=cueById.get(issue.cueId);return <button type="button" key={`${issue.cueId}-${issue.code}-${index}`} className={issue.severity} onClick={()=>cue&&onCue(cue)}><span>{issue.severity==='error'?'Lỗi':'Cảnh báo'}</span>{issue.message}</button>})}{report.issues.length>8&&<small>Và {report.issues.length-8} vấn đề khác</small>}</div>:<p className="quality-pass">Không phát hiện lỗi timing/nội dung/tốc độ đọc.</p>}
      <div className="speaker-workflow"><h3>NGƯỜI NÓI</h3>{speakerIds.length?speakerIds.map(id=><label key={id}><span>{id}</span><input aria-label={`Tên hiển thị cho ${id}`} value={speakers[id]||''} placeholder={id} onChange={event=>onSpeaker(id,event.target.value)}/></label>):<small>Chưa có speaker. Dùng Phân vai hoặc nhập speaker trong cue.</small>}</div></>:<p className="quality-empty">Nhập hoặc tạo transcript để chạy QA.</p>}
  </section>
}
