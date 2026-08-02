import type { CSSProperties, ReactNode } from 'react'
import { normalizeStyle, type StudioCue, type StudioStyle, type StylePreset } from './studioApi'

export function StyleInspector({tab,setTab,style,presets,onStyle,onPreset}:{
  tab:'templates'|'style'|'animation';setTab:(tab:'templates'|'style'|'animation')=>void;
  style:StudioStyle;presets:StylePreset[];onStyle:(patch:Partial<StudioStyle>)=>void;
  onPreset:(preset:StylePreset)=>void}) {
  return <><nav>{(['templates','style','animation'] as const).map(item=><button key={item}
    className={tab===item?'active':''} onClick={()=>setTab(item)}>{item.toUpperCase()}</button>)}</nav>
    {tab==='templates'&&<div className="template-grid">{presets.map(preset=><button key={preset.id}
      type="button" className={style.preset===preset.id?'selected':''} onClick={()=>onPreset(preset)}
      style={{fontFamily:preset.config.font_family,color:preset.config.font_color,
        backgroundColor:preset.config.bg_box?`${preset.config.bg_color}99`:undefined}}>
      <strong>THE QUICK<br/>BROWN FOX</strong><small>{preset.label}</small></button>)}</div>}
    {tab==='style'&&<div className="style-controls">
      <Control label="Font"><select value={style.font_family} onChange={e=>onStyle({font_family:e.target.value})}>{['Arial','Montserrat','Oswald','Anton','Georgia','Impact','Comic Sans MS'].map(v=><option key={v}>{v}</option>)}</select></Control>
      <Control label="Cỡ chữ"><input aria-label="Cỡ chữ" type="range" min="12" max="120" value={style.font_size} onChange={e=>onStyle({font_size:Number(e.target.value)})}/><output>{style.font_size}</output></Control>
      <Control label="Màu chữ"><input aria-label="Màu chữ" type="color" value={style.font_color} onChange={e=>onStyle({font_color:e.target.value})}/></Control>
      <Control label="Viền"><input aria-label="Màu viền" type="color" value={style.outline_color} onChange={e=>onStyle({outline_color:e.target.value})}/><input aria-label="Độ dày viền" type="number" min="0" max="10" value={style.outline_width} onChange={e=>onStyle({outline_width:Number(e.target.value)})}/></Control>
      <Control label="Shadow"><input aria-label="Màu shadow" type="color" value={style.shadow_color} onChange={e=>onStyle({shadow_color:e.target.value})}/><input aria-label="Độ lệch shadow" type="number" min="0" max="10" value={style.shadow_offset} onChange={e=>onStyle({shadow_offset:Number(e.target.value)})}/></Control>
      <Control label="Nền"><input aria-label="Bật nền" type="checkbox" checked={style.bg_box} onChange={e=>onStyle({bg_box:e.target.checked})}/><input aria-label="Màu nền" type="color" value={style.bg_color} onChange={e=>onStyle({bg_color:e.target.value})}/></Control>
      <Control label="Vị trí"><select aria-label="Vị trí" value={style.alignment} onChange={e=>onStyle({alignment:Number(e.target.value)})}><option value="8">Trên</option><option value="5">Giữa</option><option value="2">Dưới</option></select></Control>
      <Control label="Karaoke"><select aria-label="Karaoke" value={style.highlight_mode} onChange={e=>onStyle({highlight_mode:e.target.value as StudioStyle['highlight_mode']})}><option value="none">Tắt</option><option value="word">Word pop</option><option value="underline">Underline</option><option value="bg_flash">Flash</option><option value="all_text">Toàn câu</option><option value="keyword">Từ khóa</option></select><input aria-label="Màu karaoke" type="color" value={style.highlight_color} onChange={e=>onStyle({highlight_color:e.target.value})}/></Control>
      {style.highlight_mode==='keyword'&&<Control label="Từ khóa"><input aria-label="Từ khóa" value={style.keyword_highlights.join(', ')} onChange={e=>onStyle({keyword_highlights:e.target.value.split(',').map(v=>v.trim()).filter(Boolean)})}/></Control>}
      <div className="toggle-row"><label><input type="checkbox" checked={style.bold} onChange={e=>onStyle({bold:e.target.checked})}/> Bold</label><label><input type="checkbox" checked={style.italic} onChange={e=>onStyle({italic:e.target.checked})}/> Italic</label></div>
    </div>}
    {tab==='animation'&&<div className="style-controls animation-grid">{([
      ['none','Không'],['fade','Fade'],['pop','Pop'],['slide_up','Slide up']] as const).map(([id,label])=><button key={id} className={style.animation===id?'selected':''} onClick={()=>onStyle({animation:id})}><span className={`animation-demo ${id}`}>Aa</span>{label}</button>)}<Control label="Thời gian"><input aria-label="Thời gian animation" type="range" min="0" max="1000" step="20" value={style.animation_ms} onChange={e=>onStyle({animation_ms:Number(e.target.value)})}/><output>{style.animation_ms}ms</output></Control></div>}
  </>
}

function Control({label,children}:{label:string;children:ReactNode}){return <label className="style-control"><span>{label}</span><div>{children}</div></label>}

export function SubtitlePreview({cue,currentTime,rawStyle}:{cue:StudioCue;currentTime:number;rawStyle:Partial<StudioStyle>}) {
  const style=normalizeStyle(rawStyle); const words=cue.text.split(/\s+/); const progress=Math.max(0,Math.min(1,(currentTime-cue.start)/Math.max(.05,cue.end-cue.start)));const active=Math.min(words.length-1,Math.floor(progress*words.length))
  const vertical=style.alignment>=7?{top:`${style.margin_v}px`}:style.alignment>=4?{top:'50%',transform:'translateY(-50%)'}:{bottom:`${style.margin_v}px`}
  const css:CSSProperties={...vertical,fontFamily:style.font_family,fontSize:`clamp(14px,${style.font_size/22}vw,${style.font_size}px)`,fontWeight:style.bold?800:400,fontStyle:style.italic?'italic':'normal',color:style.font_color,WebkitTextStroke:`${style.outline_width}px ${style.outline_color}`,textShadow:`${style.shadow_offset}px ${style.shadow_offset}px ${Math.max(1,style.shadow_offset)}px ${style.shadow_color}`,background:style.bg_box?hexAlpha(style.bg_color,style.bg_opacity):undefined,padding:style.bg_box?`${style.bg_padding}px`:undefined}
  return <div key={cue.id} className={`subtitle-overlay animation-${style.animation}`} style={{...css,'--animation-ms':`${style.animation_ms}ms`} as CSSProperties}>{words.map((word,index)=>{const marked=style.highlight_mode==='all_text'||(style.highlight_mode==='word'&&index===active)||(style.highlight_mode==='keyword'&&style.keyword_highlights.some(k=>k.toLowerCase()===word.replace(/[^\p{L}\p{N}]/gu,'').toLowerCase()));return <span key={`${index}-${word}`} className={marked?'highlighted':''} style={marked?{color:style.highlight_mode==='keyword'?style.keyword_highlight_color:style.highlight_color}:undefined}>{word}{' '}</span>})}</div>
}

function hexAlpha(hex:string,opacity:number){const alpha=Math.round(Math.max(0,Math.min(1,opacity))*255).toString(16).padStart(2,'0');return `${hex}${alpha}`}
