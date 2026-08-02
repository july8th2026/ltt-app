import { useMemo, useState } from 'react'
import type { StudioCue, StudioTrack } from './studioApi'
import { Waveform } from './Waveform'

type Props = { tracks: StudioTrack[]; duration: number; currentTime: number; sourceUrl: string;
  selectedCueId: string; onSelect: (id:string) => void; onSeek:(time:number)=>void;
  onCueChange:(trackId:string,cueId:string,patch:Partial<StudioCue>)=>void }

export function EditorTimeline(props: Props) {
  const {tracks,duration,currentTime,sourceUrl,selectedCueId,onSelect,onSeek,onCueChange}=props
  const safeDuration=Math.max(duration, ...tracks.flatMap(t=>t.cues.map(c=>c.end)), 1)
  const [drag,setDrag]=useState<{track:string;cue:string;mode:'move'|'start'|'end';x:number;start:number;end:number}|null>(null)
  const ticks=useMemo(()=>Array.from({length:6},(_,i)=>safeDuration*i/5),[safeDuration])
  const move=(event:React.PointerEvent<HTMLDivElement>)=>{
    if(!drag)return; const rect=event.currentTarget.getBoundingClientRect()
    const delta=(event.clientX-drag.x)/Math.max(1,rect.width)*safeDuration
    if(drag.mode==='move'){const length=drag.end-drag.start; const start=Math.max(0,Math.min(safeDuration-length,drag.start+delta)); onCueChange(drag.track,drag.cue,{start,end:start+length})}
    if(drag.mode==='start')onCueChange(drag.track,drag.cue,{start:Math.max(0,Math.min(drag.end-.05,drag.start+delta))})
    if(drag.mode==='end')onCueChange(drag.track,drag.cue,{end:Math.max(drag.start+.05,Math.min(safeDuration,drag.end+delta))})
  }
  return <div className="timeline-editor" onPointerMove={move} onPointerUp={()=>setDrag(null)} onPointerCancel={()=>setDrag(null)}>
    <Waveform src={sourceUrl} duration={safeDuration} currentTime={currentTime} onSeek={onSeek}/>
    <div className="timeline-ruler">{ticks.map(t=><button key={t} onClick={()=>onSeek(t)}>{formatShort(t)}</button>)}</div>
    <div className="timeline-lanes" onPointerDown={event=>{if(event.target===event.currentTarget){const rect=event.currentTarget.getBoundingClientRect();onSeek((event.clientX-rect.left)/rect.width*safeDuration)}}}>
      <i className="playhead" style={{left:`${currentTime/safeDuration*100}%`}}/>
      {tracks.map(track=><div className={`timeline-lane ${track.visible?'':'muted'}`} key={track.id}>
        <span className="lane-label" title={track.name}>{track.kind==='translation'?'TR':'CC'}</span>
        <div className="lane-content">{track.cues.map(cue=><button type="button" key={cue.id}
          className={`cue-block ${selectedCueId===cue.id?'selected':''}`} style={{left:`${cue.start/safeDuration*100}%`,width:`${Math.max(.5,(cue.end-cue.start)/safeDuration*100)}%`}}
          onClick={()=>{onSelect(cue.id);onSeek(cue.start)}} onPointerDown={event=>{event.currentTarget.setPointerCapture(event.pointerId);setDrag({track:track.id,cue:cue.id,mode:'move',x:event.clientX,start:cue.start,end:cue.end})}}>
          <i className="cue-handle start" onPointerDown={event=>{event.stopPropagation();setDrag({track:track.id,cue:cue.id,mode:'start',x:event.clientX,start:cue.start,end:cue.end})}}/>
          <span>{cue.text||'(trống)'}</span><i className="cue-handle end" onPointerDown={event=>{event.stopPropagation();setDrag({track:track.id,cue:cue.id,mode:'end',x:event.clientX,start:cue.start,end:cue.end})}}/>
        </button>)}</div>
      </div>)}</div>
  </div>
}

function formatShort(seconds:number){const m=Math.floor(seconds/60);const s=Math.floor(seconds%60);return `${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`}
