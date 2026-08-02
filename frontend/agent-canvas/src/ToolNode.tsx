import { Handle, Position, type NodeProps } from '@xyflow/react'
import type { PaletteTool } from './editorState'

type ToolData = Record<string, unknown> & { __tool?: PaletteTool; __cost?: number; __status?: string;
  __artifacts?: { name: string; url: string }[] }

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
    <p>{tool?.app_name ?? 'Không có metadata'}</p>
    <small>{model} · {tool?.requires.join('/') || 'api'} · {typed.__cost ?? '—'} credit tối đa</small>
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
