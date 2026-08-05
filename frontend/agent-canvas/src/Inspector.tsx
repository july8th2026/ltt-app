import type { PaletteTool } from './editorState'
import type { AgentRun, AgentRunSummary, CanvasNode } from './workflowApi'
import { fieldLabel, primaryFields } from './nodePresentation'
import { customerToolLabel } from './presentationAdapter'
import { RunInspector } from './RunInspector'

type InspectorProps = {
  node?: CanvasNode
  tool?: PaletteTool
  readOnly: boolean
  csrfToken: string
  run?: AgentRun
  runHistory?: AgentRunSummary[]
  onSelectRun?: (id: string) => void
  onReplay?: (run: AgentRun) => void
  onRestore?: (run: AgentRun) => void
  onChange: (data: Record<string, unknown>) => void
  connections?: Record<string, { value: string; label: string }[]>
  onConnect?: (field: string, value: string) => void
  className?: string
}

const contentFields = new Set(['prompt', 'topic', 'text', 'url', 'source_url'])

export function Inspector({node, tool, readOnly, run, runHistory, onSelectRun, onReplay,
  onRestore, onChange, className = ''}: InspectorProps) {
  const history = <details className="run-history-details"><summary>Lịch sử chạy</summary>
    <RunInspector run={run} history={runHistory} onSelect={onSelectRun} onReplay={onReplay} onRestore={onRestore}/>
  </details>
  if (!node || !tool) return <aside className={`canvas-inspector ${className}`} aria-label="Chi tiết block">
    <div className="node-inspector"><h2>Chi tiết</h2><p>Chọn một block để xem các tùy chọn tạo nội dung.</p></div>{history}
  </aside>

  const params = (node.data.params ?? {}) as Record<string, unknown>
  const fields = primaryFields(tool, params).filter(([name]) => !contentFields.has(name)).slice(0, 6)
  const setParam = (name: string, value: unknown) => onChange({params: {...params, [name]: value}})
  return <aside className={`canvas-inspector ${className}`} aria-label="Chi tiết block">
    <div className="node-inspector"><small>TÙY CHỌN TẠO</small><h2>{customerToolLabel(tool)}</h2>
      <p>Chỉ những lựa chọn ảnh hưởng trực tiếp đến kết quả được hiển thị tại đây.</p>
      {fields.map(([name, rule]) => {
        const value = params[name] ?? rule.default ?? ''
        const label = <span>{fieldLabel(name)}{rule.required ? ' *' : ''}</span>
        if (rule.values?.length) return <label key={name}>{label}<select disabled={readOnly}
          value={String(value)} onChange={event => setParam(name, event.target.value)}>
          <option value="">— chọn —</option>{(rule.options ?? rule.values.map(item => ({value: item, label: String(item)})))
            .map(option => <option key={String(option.value)} value={String(option.value)}>{option.label}</option>)}</select></label>
        if (rule.type === 'bool') return <label key={name} className="check-field"><input type="checkbox"
          disabled={readOnly} checked={Boolean(value)} onChange={event => setParam(name, event.target.checked)}/>{label}</label>
        return <label key={name}>{label}<input disabled={readOnly} value={String(value)}
          type={rule.type === 'int' || rule.type === 'number' ? 'number' : 'text'} min={rule.min} max={rule.max}
          onChange={event => setParam(name, rule.type === 'int' ? Number.parseInt(event.target.value) :
            rule.type === 'number' ? Number(event.target.value) : event.target.value)}/></label>
      })}
      {!fields.length && <p className="detail-empty">Block này không cần thêm tùy chọn. Nội dung và thao tác chạy nằm ngay trong block.</p>}
    </div>{history}
  </aside>
}
