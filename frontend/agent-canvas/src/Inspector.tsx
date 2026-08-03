import type { CanvasNode } from './workflowApi'
import type { AgentRun } from './workflowApi'
import type { PaletteTool } from './editorState'
import { RunInspector } from './RunInspector'

export function Inspector({ node, tool, readOnly, run, onChange, connections = {}, onConnect }:
  { node?: CanvasNode; tool?: PaletteTool; readOnly: boolean;
    run?: AgentRun;
    onChange: (data: Record<string, unknown>) => void;
    connections?: Record<string, { value: string; label: string }[]>;
    onConnect?: (field: string, value: string) => void }) {
  if (!node || !tool) return <aside className="canvas-inspector" aria-label="Inspector">
    <RunInspector run={run}/><div className="node-inspector"><h2>Inspector</h2><p>Chọn một node để cấu hình.</p></div></aside>
  const params = (node.data.params ?? {}) as Record<string, unknown>
  const schema = Object.entries(tool.schema_variants ?? {}).reduce((current, [field, variants]) =>
    variants[String(params[field])] ?? current, tool.params_schema)
  const setParam = (name: string, value: unknown) => onChange({ params: { ...params, [name]: value } })
  return <aside className="canvas-inspector" aria-label="Inspector">
    <RunInspector run={run}/><div className="node-inspector"><h2>{tool.name}</h2><p>{tool.description}</p>
    {Object.entries(schema).map(([name, rule]) => {
      const value = params[name] ?? rule.default ?? ''
      const label = <span>{name}{rule.required ? ' *' : ''}</span>
      const connector = connections[name]?.length ? <label className="connection-field">Nối dữ liệu từ<select
        disabled={readOnly} value="" onChange={event => onConnect?.(name, event.target.value)}>
        <option value="">— chọn output tương thích —</option>{connections[name].map(option =>
          <option key={option.value} value={option.value}>{option.label}</option>)}</select></label> : null
      if (rule.values?.length) return <div key={name}><label>{label}<select disabled={readOnly}
        value={String(value)} onChange={event => setParam(name, event.target.value)}>
        <option value="">— chọn —</option>{(rule.options ?? rule.values.map(item => ({ value: item, label: String(item) })))
          .map(option => <option key={String(option.value)} value={String(option.value)}>{option.label}</option>)}</select></label>{connector}</div>
      if (rule.type === 'bool') return <label key={name} className="check-field"><input
        type="checkbox" disabled={readOnly} checked={Boolean(value)}
        onChange={event => setParam(name, event.target.checked)} />{label}</label>
      if (rule.type === 'int' || rule.type === 'number') return <label key={name}>{label}<input
        type="number" disabled={readOnly} min={rule.min} max={rule.max} value={String(value)}
        onChange={event => setParam(name, rule.type === 'int' ? Number.parseInt(event.target.value) : Number(event.target.value))} /></label>
      return <div key={name}><label>{label}<textarea disabled={readOnly} value={String(value)}
        onChange={event => setParam(name, event.target.value)} /></label>{connector}</div>
    })}
    <label>Fan-out<input type="number" min="1" max="4" disabled={readOnly}
      value={Number(node.data.fanout ?? 1)} onChange={event => onChange({ fanout: Number(event.target.value) })} /></label>
  </div></aside>
}
