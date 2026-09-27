import { FormTuLuocDo } from '../../../inspector/FormTuLuocDo'
import type { EditorAction } from '../../../editorState'
import type { NodeDefinition } from '../../../nodeDefinition'
import type { CanvasNode, GoiYBieuThuc } from '../../../workflowApi'

type Props = {
  dangMo: boolean
  selectedNode: CanvasNode | undefined
  dinhNghia: NodeDefinition | undefined
  readOnly: boolean
  goiY: GoiYBieuThuc | undefined
  liveQuotes: Record<string, number>
  dispatch: (action: EditorAction) => void
}

/** Chi tiết node — bọc `FormTuLuocDo` (form sinh TỪ LƯỢC ĐỒ JSON của node).
 *
 *  ⛔ Không bảng tra cứu nào ở đây. Mọi ô đến từ `dinhNghia.tham_so`, một JSON
 *     Schema máy chủ sinh — nên thêm một app KHÔNG phải sửa một dòng nào trong
 *     `src/` (`tests/test_967` đếm hàng chết nếu ai đó thêm bảng tra lại).
 */
export function StepInspector(p: Props) {
  return <aside className={`canvas-inspector${p.dangMo?' is-open':''}`} aria-label="Chi tiết node">
    {p.selectedNode&&p.dinhNghia
      ? <><small>THAM SỐ</small><h2>{p.dinhNghia.title}</h2>
          <p className="inspector-type">{p.dinhNghia.type}@{p.dinhNghia.type_version}</p>
          {p.dinhNghia['x-ltt-loi']&&<p className="inspector-loi" role="status">
            Một phần lựa chọn của node này chưa tải được — các ô ấy bị khóa.</p>}
          <input aria-label="Tên hiển thị của node" disabled={p.readOnly}
            value={p.selectedNode.label??''} placeholder={p.dinhNghia.title}
            onChange={event=>p.dispatch({type:'nodeLabel',id:p.selectedNode!.id,label:event.target.value})}/>
          <FormTuLuocDo luocDo={p.dinhNghia.tham_so}
            giaTri={(p.selectedNode.data.params ?? {}) as Record<string, unknown>}
            readOnly={p.readOnly} goiY={p.goiY}
            onChange={(ten, v) => p.dispatch({type:'update',id:p.selectedNode!.id,data:{ params: {
              ...(p.selectedNode!.data.params as Record<string, unknown>), [ten]: v } }})} />
          <footer className="inspector-gia">{p.liveQuotes[p.selectedNode.id]===undefined
            ? 'Chi phí do server xác nhận'
            : `Tối đa ${p.liveQuotes[p.selectedNode.id]} credit`}</footer>
        </>
      : <p>Chọn một node để xem tham số.</p>}
  </aside>
}
