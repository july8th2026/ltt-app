import type { EditorAction } from '../../../editorState'
import type { Workflow } from '../../../workflowApi'

type Props = {
  goal: string
  workflow: Workflow | undefined
  readOnly: boolean
  dangSoan: boolean
  soanLoi: string
  soanBangAI: () => void
  dispatch: (action: EditorAction) => void
}

/** Mục tiêu workflow + Agent Designer ("Soạn bằng AI").
 *
 *  ⛔ Ô "Ngân sách tối đa" đã GỠ (review I4): không một tệp
 *     `platform_core/workflow/*` nào đọc `budget_max_credit` ở v3 — động cơ
 *     chốt trần bằng `version.estimated_max` lúc publish. Giữ lại ô nhập ấy là
 *     hứa với người dùng một trần chi tiêu mà không ai thi hành: nói dối về
 *     TIỀN. Trần thật hiện ở bảng lượt chạy (`credit_charged/credit_max`,
 *     `RunV3Panel`). Khoá `budget_max_credit` vẫn còn trong `document` vì
 *     `di_tru_m1.py` mang nó sang từ bản nháp cũ — gỡ ô nhập ⛔ không được làm
 *     mất dữ liệu ấy.
 *
 *  ⭐ Task A3 — "Soạn bằng AI" soạn draft TỪ mục tiêu ở trên bằng `/soan` rồi
 *     nạp thẳng document trả về. Cửa này KHÔNG publish — người dùng vẫn tự bấm
 *     "Chạy" sau đó. Nó GHI ĐÈ đồ thị đang dựng, nên lượt nạp ấy đẩy trạng thái
 *     cũ vào lịch sử hoàn tác (`giuLichSu`) để Ctrl+Z cứu được.
 */
export function WorkflowSettings(p: Props) {
  return <div className="workflow-settings"><label>Mục tiêu workflow<textarea disabled={p.readOnly}
    value={p.goal} onChange={event => p.dispatch({ type: 'document', goal: event.target.value })} /></label>
    <button disabled={p.readOnly||!p.workflow||!p.goal.trim()||p.dangSoan}
      aria-busy={p.dangSoan||undefined} onClick={p.soanBangAI}>
      {p.dangSoan?'Đang soạn…':'Soạn bằng AI'}</button>
    {p.soanLoi && <span className="run-error" role="alert">{p.soanLoi}</span>}</div>
}
