import type { AgentRun,AgentRunSummary } from './workflowApi'

const labels:Record<string,string>={awaiting_approval:'Chờ phê duyệt',running:'Đang chạy',done:'Hoàn tất',error:'Lỗi',cancelled:'Đã hủy',queued:'Đang chờ'}

export function RunInspector({run,history=[],onSelect,onReplay,onRestore}:{run?:AgentRun;history?:AgentRunSummary[];onSelect?:(id:string)=>void;onReplay?:(run:AgentRun)=>void;onRestore?:(run:AgentRun)=>void}){
  if(!run)return <section className="run-inspector" aria-label="Run inspector"><h2>Bản chạy</h2><p>Kiểm tra workflow và tạo bản chạy để xem checkpoint, chi phí và artifact.</p><RunHistory items={history} onSelect={onSelect}/></section>
  const steps=run.plan.steps||[]
  return <section className="run-inspector" aria-label="Run inspector">
    <header><h2>Bản chạy</h2><span className={`run-badge ${run.status}`}>{run.status==='running'&&run.scheduled_at&&new Date(run.scheduled_at)>new Date()?'Đã lên lịch':labels[run.status]||run.status}</span></header>
    {run.scheduled_at&&<p className="scheduled-time">Thời điểm chạy: <time dateTime={run.scheduled_at}>{new Date(run.scheduled_at).toLocaleString('vi-VN')}</time></p>}
    <dl><div><dt>Ước tính</dt><dd>{run.estimated} credit</dd></div><div><dt>Thực tế</dt><dd>{run.actual} credit</dd></div><div><dt>Phiên bản</dt><dd>v{run.version}</dd></div></dl>
    <ol className="run-steps">{steps.map(step=>{const state=run.checkpoint[step.id]||{};const status=String(state.status||'queued');return <li key={step.id}><span className={`run-dot ${status}`} aria-hidden="true"/><div><strong>{step.id}</strong><small>{labels[status]||status}{state.error||state.reason?` · ${String(state.error||state.reason)}`:''}</small></div></li>})}</ol>
    {!!run.artifacts?.length&&<div className="run-artifacts"><h3>ARTIFACTS</h3>{run.artifacts.map((item,index)=><a key={`${item.step_id}-${index}`} href={item.url}>{item.name}</a>)}</div>}
    {!!run.decisions.length&&<details><summary>Nhật ký quyết định ({run.decisions.length})</summary><ol>{run.decisions.slice(-8).map((item,index)=><li key={index}>{String(item.event||item.status||'decision')}</li>)}</ol></details>}
    {['done','error','cancelled'].includes(run.status)&&onReplay&&<button className="replay-run" onClick={()=>onReplay(run)}>Replay từ snapshot này</button>}
    {onRestore&&<button className="restore-workflow" onClick={()=>onRestore(run)}>Khôi phục thành workflow mới</button>}
    <RunHistory items={history} selected={run.id} onSelect={onSelect}/>
  </section>
}

function RunHistory({items,selected,onSelect}:{items:AgentRunSummary[];selected?:string;onSelect?:(id:string)=>void}){return items.length?<div className="run-history"><h3>LỊCH SỬ</h3>{items.map(item=><button key={item.id} className={item.id===selected?'selected':''} aria-pressed={item.id===selected} onClick={()=>onSelect?.(item.id)}><span className={`run-dot ${item.status}`} aria-hidden="true"/><strong>{item.id.slice(0,8)}</strong><small>{labels[item.status]||item.status} · {item.actual}/{item.estimated} credit</small></button>)}</div>:null}
