import { useEffect, useState } from 'react'
import { goiYBieuThuc, type CanvasDocument, type GoiYBieuThuc,
  type Workflow } from '../../../workflowApi'

/** Gợi ý biểu thức §6 cho node đang chọn (P2 Task 8).
 *
 *  ⭐ GUI KEM tai lieu dang go, khong doi autosave: node nguoi dung vua tha
 *     xuong phai co trong goi y NGAY, chu khong sau 800 ms.
 *  ⛔ Hong thi `undefined`, KHONG lui ve mot danh sach cuc bo: may chu sinh
 *     goi y, trinh duyet khong co bang nao de lui ve khi no vang. Mot goi y
 *     sai dan thang vao o tham so va se bi tu choi luc publish.
 */
export function useExpressionSuggest(workflow: Workflow | undefined,
                                     selectedNodeId: string | undefined,
                                     document: CanvasDocument,
                                     csrf: string, offline: boolean) {
  const [goiY, setGoiY] = useState<GoiYBieuThuc | undefined>(undefined)

  useEffect(() => {
    if (!workflow || !selectedNodeId || offline) { setGoiY(undefined); return }
    let active = true
    const timer = window.setTimeout(() => {
      void goiYBieuThuc(workflow.id, selectedNodeId, document, csrf)
        .then(ket => { if (active) setGoiY(ket) })
        .catch(() => { if (active) setGoiY(undefined) })
    }, 200)
    return () => { active = false; window.clearTimeout(timer) }
  }, [workflow?.id, selectedNodeId, document, csrf, offline]) // eslint-disable-line react-hooks/exhaustive-deps

  return goiY
}
