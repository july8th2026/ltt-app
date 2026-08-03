import { Handle, Position, type NodeProps } from '@xyflow/react'
import type { PaletteTool } from './editorState'

type ToolData = Record<string, unknown> & { __tool?: PaletteTool; __cost?: number; __status?: string;
  __artifacts?: { name: string; url: string }[]; __readOnly?: boolean;
  __onQuickConnect?: (output:string)=>void }

export function ToolNode({ data, selected }: NodeProps) {
  const typed = data as ToolData
  const tool = typed.__tool
  const params = (typed.params ?? {}) as Record<string, unknown>
  const model = String(params.model ?? 'mặc định')
  const labels: Record<string, string> = { draft: 'Bản nháp', validated: 'Đã kiểm tra',
    invalid: 'Cần sửa', submitted: 'Đang chạy', retry_needed: 'Đang thử lại',
    done: 'Hoàn tất', error: 'Lỗi', queued: 'Đang chờ' }
  return <article className={`tool-node${selected ? ' is-selected' : ''}`}
    aria-label={`Node ${tool?.name ?? 'không xác định'}`}>
    <header><span aria-hidden="true">{tool?.requires.includes('gpu') ? 'GPU' : tool?.app_slug === 'kichban' ? 'TXT' : 'AI'}</span>
      <strong>{tool?.name ?? 'Tool không tồn tại'}</strong></header>
    <div className="node-preview" aria-hidden="true"><span>{tool?.app_slug === 'kichban' ? 'T' : tool?.name.startsWith('video.') ? '▶' : tool?.name.startsWith('image.') ? '◇' : 'AI'}</span></div>
    <p>{tool?.app_name ?? 'Không có metadata'}</p>
    <small>{model} · {tool?.requires.join('/') || 'api'} · {typed.__cost ?? '—'} credit tối đa</small>
    <em className={`node-status ${typed.__status}`}>{labels[String(typed.__status)] ?? 'Đang chờ'}</em>
    {!!typed.__artifacts?.length && <div className="node-artifacts">{typed.__artifacts.map((item, index) =>
      <a key={`${item.url}-${index}`} href={item.url} target="_blank" rel="noreferrer">Kết quả {item.name}</a>)}</div>}
    {tool && Object.entries(tool.params_schema).map(([name, rule], index) =>
      <Handle key={name} id={name} type="target" position={Position.Left} className="typed-port input-port"
        style={{ top: 48 + index * 34 }} aria-label={`Input ${name}: ${rule.type}`}><span>{name}</span></Handle>)}
    {tool && Object.entries(tool.returns).map(([name, kind], index) =>
      <Handle key={name} id={name} type="source" position={Position.Right} className="typed-port output-port"
        style={{ top: 62 + index * 42 }} aria-label={`Output ${name}: ${kind}`} onClick={event=>{event.stopPropagation();typed.__onQuickConnect?.(name)}}><b>+</b><span>{name}</span></Handle>)}
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
