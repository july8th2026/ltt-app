import type { AgentRun } from './workflowApi'

const labels:Record<string,string>={awaiting_approval:'Chờ phê duyệt',running:'Đang chạy',done:'Hoàn tất',error:'Lỗi',cancelled:'Đã hủy',queued:'Đang chờ'}

export function RunInspector({run}:{run?:AgentRun}){
  if(!run)return <section className="run-inspector" aria-label="Run inspector"><h2>Bản chạy</h2><p>Kiểm tra workflow và tạo bản chạy để xem checkpoint, chi phí và artifact.</p></section>
  const steps=run.plan.steps||[]
  return <section className="run-inspector" aria-label="Run inspector">
    <header><h2>Bản chạy</h2><span className={`run-badge ${run.status}`}>{labels[run.status]||run.status}</span></header>
    <dl><div><dt>Ước tính</dt><dd>{run.estimated} credit</dd></div><div><dt>Thực tế</dt><dd>{run.actual} credit</dd></div><div><dt>Phiên bản</dt><dd>v{run.version}</dd></div></dl>
    <ol className="run-steps">{steps.map(step=>{const state=run.checkpoint[step.id]||{};const status=String(state.status||'queued');return <li key={step.id}><span className={`run-dot ${status}`} aria-hidden="true"/><div><strong>{step.id}</strong><small>{labels[status]||status}</small></div></li>})}</ol>
    {!!run.artifacts?.length&&<div className="run-artifacts"><h3>ARTIFACTS</h3>{run.artifacts.map((item,index)=><a key={`${item.step_id}-${index}`} href={item.url}>{item.name}</a>)}</div>}
    {!!run.decisions.length&&<details><summary>Nhật ký quyết định ({run.decisions.length})</summary><ol>{run.decisions.slice(-8).map((item,index)=><li key={index}>{String(item.event||item.status||'decision')}</li>)}</ol></details>}
  </section>
}
