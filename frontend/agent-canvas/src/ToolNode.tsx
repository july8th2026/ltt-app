import { Handle, Position, type NodeProps } from '@xyflow/react'
import type { PaletteTool } from './editorState'
import { emptyMessage, fieldLabel, hasMeaningfulInput, mediaKind, nodeModality, outputLabel } from './nodePresentation'

type ToolData = Record<string, unknown> & { __tool?: PaletteTool; __cost?: number; __status?: string;
  __artifacts?: { name: string; url: string }[]; __readOnly?: boolean;
  __inputFields?:string[]; __label?:string;
  __onQuickConnect?: (output:string)=>void; __onOpen?:()=>void; __onRun?:()=>void;
  __onUpload?:(file:File)=>void; __onRename?:(label:string)=>void;
  __onDuplicate?:()=>void; __onParamChange?:(name:string,value:unknown)=>void }

const icon:Record<string,string>={text:'≡',image:'▧',video:'▶',audio:'♪',batch:'▦',transform:'↗',input:'⇧',tool:'✦'}

export function ToolNode({ data, selected }: NodeProps) {
  const typed = data as ToolData
  const tool = typed.__tool
  const params = (typed.params ?? {}) as Record<string, unknown>
  const modality=nodeModality(tool);const media=mediaKind(tool);const empty=emptyMessage(tool)
  const configured=tool?hasMeaningfulInput(tool,params):false
  const labels: Record<string, string> = { draft: 'Bản nháp', validated: 'Sẵn sàng',
    invalid: 'Cần bổ sung', submitted: 'Đang chạy', retry_needed: 'Đang thử lại',
    done: 'Hoàn tất', error: 'Có lỗi', queued: 'Đang chờ', running:'Đang xử lý' }
  const firstArtifact=typed.__artifacts?.[0]
  const summary=String(params.prompt??params.topic??params.text??params.url??params.source_url??params.asset_name??'').trim()
  const accept=media==='image'?'image/png,image/jpeg,image/webp':media==='video'?'video/*':media==='audio'?'audio/*':undefined
  const textField=tool&&Object.keys(tool.params_schema).find(name=>['text','topic','prompt'].includes(name))
  const upload=(file?:File)=>{if(file&&!typed.__readOnly)typed.__onUpload?.(file)}
  return <article className={`tool-node modality-${modality}${selected ? ' is-selected' : ''}`}
    aria-label={`Node ${tool?.name ?? 'không xác định'}`}
    onDragOver={event=>{if(accept&&!typed.__readOnly){event.preventDefault();event.dataTransfer.dropEffect='copy'}}}
    onDrop={event=>{if(!accept||typed.__readOnly)return;event.preventDefault();event.stopPropagation();upload(event.dataTransfer.files?.[0])}}>
    <header><span aria-hidden="true">{icon[modality]}</span><input className="node-title nodrag" aria-label="Tên hiển thị node"
      value={typed.__label||tool?.label||tool?.name||'Công cụ không tồn tại'} disabled={typed.__readOnly}
      onClick={event=>event.stopPropagation()} onChange={event=>typed.__onRename?.(event.target.value)}/>
      <button className="node-more nodrag" aria-label="Mở thao tác node" onClick={event=>{event.stopPropagation();typed.__onOpen?.()}}>•••</button></header>
    <div className={`node-preview${firstArtifact?' has-output':''}`}>
      {firstArtifact&&media==='image'?<img src={firstArtifact.url} alt="Kết quả hình ảnh"/>:
       firstArtifact&&media==='video'?<video src={firstArtifact.url} controls preload="metadata"/>:
       firstArtifact&&media==='audio'?<audio src={firstArtifact.url} controls preload="metadata"/>:
       modality==='text'&&textField?<div className="node-inline-text nodrag"><textarea aria-label="Nội dung trực tiếp trong node"
         disabled={typed.__readOnly} value={String(params[textField]??'')} placeholder="Viết trực tiếp hoặc dùng Tạo bằng AI…"
         onClick={event=>event.stopPropagation()} onChange={event=>typed.__onParamChange?.(textField,event.target.value)}/>
         <button className="accent" disabled={typed.__readOnly} onClick={event=>{event.stopPropagation();typed.__onOpen?.()}}>Tạo bằng AI</button></div>:
       <div className="node-empty"><i aria-hidden="true">{icon[modality]}</i><strong>{configured?'Đã có nội dung':empty.title}</strong>
         <span>{configured?(summary||'Sẵn sàng thiết lập và chạy.'):empty.hint}</span>
         <div className="node-primary-actions nodrag">
           {accept&&<label className="node-upload">Tải lên<input type="file" accept={accept} disabled={typed.__readOnly}
             onChange={event=>{upload(event.target.files?.[0]);event.target.value=''}}/></label>}
           {!['input','transform'].includes(modality)&&<button className="accent" disabled={typed.__readOnly}
             onClick={event=>{event.stopPropagation();typed.__onOpen?.()}}>Tạo bằng AI</button>}
           {modality==='transform'&&<button disabled={typed.__readOnly} onClick={event=>{event.stopPropagation();typed.__onOpen?.()}}>Chọn đầu vào</button>}
         </div></div>}
    </div>
    <footer><span className={`node-status ${typed.__status}`}>{labels[String(typed.__status)] ?? 'Đang chờ'}</span>
      <button className="node-run nodrag" disabled={typed.__readOnly||typed.__status==='running'} onClick={event=>{event.stopPropagation();typed.__onRun?.()}}>
        {typed.__cost===undefined?'Báo giá':`${typed.__cost} credit · Chạy`}</button></footer>
    {!!typed.__artifacts?.length && <div className="node-artifacts nodrag">{typed.__artifacts.map((item, index) =>
      <div key={`${item.url}-${index}`}><span>{item.name}</span><nav aria-label={`Thao tác ${item.name}`}>
        <a href={item.url} target="_blank" rel="noreferrer" aria-label={`Mở rộng ${item.name}`}>Mở</a>
        <button aria-label={`Sao chép liên kết ${item.name}`} onClick={()=>void navigator.clipboard?.writeText(item.url)}>Chép URL</button>
        <a href={item.url} download aria-label={`Tải xuống ${item.name}`}>Tải</a>
      </nav></div>)}<button className="node-duplicate" disabled={typed.__readOnly} onClick={typed.__onDuplicate}>Nhân bản node</button></div>}
    {tool && Object.entries(tool.params_schema).filter(([name])=>typed.__inputFields?.includes(name)).map(([name, rule], index) =>
      <Handle key={name} id={name} type="target" position={Position.Left} className="typed-port input-port"
        style={{ top: 56 + index * 34 }} aria-label={`Đầu vào ${fieldLabel(name)}: ${rule.type}`}><span>{fieldLabel(name)}</span></Handle>)}
    {tool && Object.entries(tool.returns).map(([name, kind], index) =>
      <Handle key={name} id={name} type="source" position={Position.Right} className="typed-port output-port"
        style={{ top: 68 + index * 42 }} aria-label={`Đầu ra ${outputLabel(name,String(kind))}: ${kind}`} onClick={event=>{event.stopPropagation();typed.__onQuickConnect?.(name)}}><b>+</b><span>{outputLabel(name,String(kind))}</span></Handle>)}
  </article>
}

export function FrameNode({ data }: NodeProps) {
  const typed = data as { name?: string; count?: number }
  return <section className="canvas-frame-node" aria-label={`Frame ${typed.name ?? ''}`}>
    <header><strong>{typed.name ?? 'Frame'}</strong><span>{typed.count ?? 0} node</span></header>
  </section>
}

export function AnnotationNode({ data }: NodeProps) {
  const typed = data as { kind?: 'note' | 'comment'; text?: string }
  return <article className={`canvas-annotation-node ${typed.kind ?? 'note'}`}
    aria-label={`${typed.kind === 'comment' ? 'Comment' : 'Sticky note'} ${typed.text ?? ''}`}>
    <small>{typed.kind === 'comment' ? 'COMMENT' : 'NOTE'}</small>
    <p>{typed.text}</p>
  </article>
}
