import { Handle, Position, type NodeProps } from '@xyflow/react'
import type { PaletteTool } from './editorState'

type ToolData = Record<string, unknown> & { __tool?: PaletteTool; __cost?: number; __status?: string;
  __artifacts?: { name: string; url: string }[]; __readOnly?: boolean;
  __onParamChange?: (name:string,value:unknown)=>void }

export function ToolNode({ data, selected }: NodeProps) {
  const typed = data as ToolData
  const tool = typed.__tool
  const params = (typed.params ?? {}) as Record<string, unknown>
  const model = String(params.model ?? 'mặc định')
  const schema = Object.entries(tool?.schema_variants ?? {}).reduce((current,[field,variants])=>
    variants[String(params[field])]??current,tool?.params_schema??{})
  const compactFields=Object.entries(schema).filter(([,rule])=>rule.type==='model_ref'||rule.required||rule.values?.length).slice(0,3)
  const labels: Record<string, string> = { draft: 'Bản nháp', validated: 'Đã kiểm tra',
    invalid: 'Cần sửa', submitted: 'Đang chạy', retry_needed: 'Đang thử lại',
    done: 'Hoàn tất', error: 'Lỗi', queued: 'Đang chờ' }
  return <article className={`tool-node${selected ? ' is-selected' : ''}`}
    aria-label={`Node ${tool?.name ?? 'không xác định'}`}>
    <header><span aria-hidden="true">{tool?.requires.includes('gpu') ? 'GPU' : tool?.app_slug === 'kichban' ? 'TXT' : 'AI'}</span>
      <strong>{tool?.name ?? 'Tool không tồn tại'}</strong></header>
    <p>{tool?.app_name ?? 'Không có metadata'}</p>
    <small>{model} · {tool?.requires.join('/') || 'api'} · {typed.__cost ?? '—'} credit tối đa</small>
    {!!compactFields.length&&<div className="node-composer">{compactFields.map(([name,rule])=>{
      const value=params[name]??rule.default??''
      if(rule.values?.length)return <label key={name}>{name}<select className="nodrag nowheel" disabled={typed.__readOnly} value={String(value)}
        onChange={event=>typed.__onParamChange?.(name,event.target.value)} onPointerDown={event=>event.stopPropagation()}>
        <option value="">— chọn —</option>{(rule.options??rule.values.map(item=>({value:item,label:String(item)}))).map(option=><option
          key={String(option.value)} value={String(option.value)}>{option.label}</option>)}</select></label>
      if(rule.type==='bool')return <label key={name} className="compact-check"><input className="nodrag" type="checkbox" disabled={typed.__readOnly}
        checked={Boolean(value)} onChange={event=>typed.__onParamChange?.(name,event.target.checked)}/>{name}</label>
      return <label key={name}>{name}<input className="nodrag nowheel" disabled={typed.__readOnly} value={String(value)}
        type={rule.type==='int'||rule.type==='number'?'number':'text'} onPointerDown={event=>event.stopPropagation()}
        onChange={event=>typed.__onParamChange?.(name,rule.type==='int'?Number.parseInt(event.target.value):rule.type==='number'?Number(event.target.value):event.target.value)}/></label>
    })}</div>}
    <em className={`node-status ${typed.__status}`}>{labels[String(typed.__status)] ?? 'Đang chờ'}</em>
    {!!typed.__artifacts?.length && <div className="node-artifacts">{typed.__artifacts.map((item, index) =>
      <a key={`${item.url}-${index}`} href={item.url} target="_blank" rel="noreferrer">Kết quả {item.name}</a>)}</div>}
    {tool && Object.entries(tool.params_schema).map(([name, rule], index) =>
      <Handle key={name} id={name} type="target" position={Position.Left}
        style={{ top: 72 + index * 16 }} aria-label={`Input ${name}: ${rule.type}`} />)}
    {tool && Object.entries(tool.returns).map(([name, kind], index) =>
      <Handle key={name} id={name} type="source" position={Position.Right}
        style={{ top: 72 + index * 16 }} aria-label={`Output ${name}: ${kind}`} />)}
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
