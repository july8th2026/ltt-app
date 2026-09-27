import { useEffect, useState } from 'react'
import { baoGiaDoThi, type CanvasDocument, type Workflow } from '../../../workflowApi'

/** Báo giá trực tiếp: MỘT request cho CẢ đồ thị (no §5, lần p10-don).
 *
 *  ⛔ KHONG quay lai vong `page.nodes.map(quoteTool)`. Effect nay chay lai moi
 *     lan `state.document` doi — tuc moi lan go mot ky tu — nen mot request MOI
 *     NODE nghia la do thi 30 node ban 30 request cho mot phim.
 *     `tests/BaoGiaMotCua.test.tsx` dem dung con so ay va do o ban cu (12).
 *
 *  ⚠️ Debounce 450 ms da co tu truoc va KHONG phai ban va: no giam tan suat
 *     bung, khong giam do lon mot lan bung.
 */
export function useLiveQuote(workflow: Workflow | undefined, document: CanvasDocument,
                             soNode: number, csrf: string, offline: boolean) {
  const [liveQuotes, setLiveQuotes] = useState<Record<string, number>>({})

  useEffect(() => {
    if (!workflow || !soNode || offline) { setLiveQuotes({}); return }
    let active = true
    const timer = window.setTimeout(() => {
      void baoGiaDoThi(workflow.id, document, csrf)
        .then(bang => { if (active) setLiveQuotes(bang.gia ?? {}) })
        // ⛔ Hong thi XOA bang gia, khong giu so cu: mot con so cu ben canh
        //    tham so vua doi la mot loi im lang ma nguoi dung khong the phat hien.
        .catch(() => { if (active) setLiveQuotes({}) })
    }, 450)
    return () => { active = false; window.clearTimeout(timer) }
  }, [workflow?.id, document, csrf, offline]) // eslint-disable-line react-hooks/exhaustive-deps

  return liveQuotes
}
