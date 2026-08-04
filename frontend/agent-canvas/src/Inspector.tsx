import type { CanvasNode } from './workflowApi'
import type { AgentRun } from './workflowApi'
import type { AgentRunSummary } from './workflowApi'
import type { PaletteTool } from './editorState'
import { RunInspector } from './RunInspector'
import { useState } from 'react'
import { uploadAsset } from './workflowApi'

export function Inspector({ node, tool, readOnly, csrfToken, run,runHistory,onSelectRun,onReplay,onRestore, onChange, connections = {}, onConnect, className = '' }:
  { node?: CanvasNode; tool?: PaletteTool; readOnly: boolean;
    csrfToken: string;
    run?: AgentRun;
    runHistory?:AgentRunSummary[];onSelectRun?:(id:string)=>void;onReplay?:(run:AgentRun)=>void;onRestore?:(run:AgentRun)=>void;
    onChange: (data: Record<string, unknown>) => void;
    connections?: Record<string, { value: string; label: string }[]>;
    onConnect?: (field: string, value: string) => void; className?: string }) {
  if (!node || !tool) return <aside className={`canvas-inspector ${className}`} aria-label="Inspector">
    <RunInspector run={run} history={runHistory} onSelect={onSelectRun} onReplay={onReplay} onRestore={onRestore}/><div className="node-inspector"><h2>Inspector</h2><p>Chọn một node để cấu hình.</p></div></aside>
  const params = (node.data.params ?? {}) as Record<string, unknown>
  const schema = Object.entries(tool.schema_variants ?? {}).reduce((current, [field, variants]) =>
    variants[String(params[field])] ?? current, tool.params_schema)
  const setParam = (name: string, value: unknown) => onChange({ params: { ...params, [name]: value } })
  return <aside className={`canvas-inspector ${className}`} aria-label="Inspector">
    <RunInspector run={run} history={runHistory} onSelect={onSelectRun} onReplay={onReplay} onRestore={onRestore}/><div className="node-inspector"><h2>{tool.name}</h2><p>{tool.description}</p>
    {Object.entries(schema).filter(([name])=>name!=='refs'&&!name.startsWith('_')).map(([name, rule]) => {
      const value = params[name] ?? rule.default ?? ''
      const assetKind = tool.name.startsWith('asset.') && name === `${tool.name.slice(6)}_key`
        ? tool.name.slice(6) : ''
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
      if (assetKind || ['image','video','audio'].includes(rule.type)) return <div key={name}><AssetField
        name={name} kind={assetKind || rule.type} value={String(value)} disabled={readOnly} csrfToken={csrfToken}
        onValue={next=>setParam(name,next)}/>{connector}</div>
      return <div key={name}><label>{label}<textarea disabled={readOnly} value={String(value)}
        onChange={event => setParam(name, event.target.value)} /></label>{connector}</div>
    })}
    <label>Fan-out<input type="number" min="1" max="4" disabled={readOnly}
      value={Number(node.data.fanout ?? 1)} onChange={event => onChange({ fanout: Number(event.target.value) })} /></label>
  </div></aside>
}

function AssetField({name,kind,value,disabled,csrfToken,onValue}:{name:string;kind:string;value:string;
  disabled:boolean;csrfToken:string;onValue:(value:string)=>void}){
  const [busy,setBusy]=useState(false);const [error,setError]=useState('')
  return <label className="asset-field"><span>{name} *</span><input aria-label={`Tải ${kind}`} type="file"
    accept={`${kind}/*`} disabled={disabled||busy} onChange={async event=>{const file=event.target.files?.[0]
      if(!file)return;setBusy(true);setError('');try{const result=await uploadAsset(file,csrfToken);onValue(result.key)}
      catch(reason){setError(reason instanceof Error?reason.message:'Tải asset thất bại')}finally{setBusy(false)}}}/>
    <small>{busy?'Đang tải…':value||'Chưa có asset'}</small>{error&&<em>{error}</em>}</label>
}
