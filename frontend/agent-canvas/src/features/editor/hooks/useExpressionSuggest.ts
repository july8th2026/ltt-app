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
    // 🔴 XOA NGAY khi doi node — ⛔ KHONG doi fetch xong.
    //
    //    Truoc 28/09, `setGoiY(undefined)` CHI chay o nhanh som ben duoi (mat
    //    workflow / mat lua chon / offline). Khi nguoi dung **doi** tu node A
    //    sang node B thi ⛔ khong nhanh nao xoa, nen state giu goi y cua A suot
    //    200 ms debounce + thoi gian mang.
    //
    //    Co `active` chan duoc mot lan GHI muon, nhung no ⛔ khong xoa **gia tri
    //    dang co** — hai viec khac nhau, va ban cu chi lam viec thu nhat.
    //
    // ⚠️ *"Thoang"* ⛔ khong lam no nhe hon: goi y dan THANG vao o tham so. Mot
    //    cu bam trong 200 ms ay chen mot bieu thuc tro toi node KHAC, va bien
    //    dich co the sach (node do ton tai that) ⇒ loi chi lo ra luc chay, o
    //    mot buoc da tinh tien.
    setGoiY(undefined)
    if (!workflow || !selectedNodeId || offline) return
    let active = true
    const timer = window.setTimeout(() => {
      void goiYBieuThuc(workflow.id, selectedNodeId, document, csrf)
        // ⭐ Loc theo `node_id` TAI BIEN, ⛔ khong de tung nguoi goi tu ve.
        //
        //    Lan UI-6 tim ra loi nay va tu ve trong `ChonDuLieu` bang cach so
        //    `goiY.node_id` — dung ve ket qua, sai ve CHO. Hook nay co it nhat
        //    HAI nguoi dung (`ChonDuLieu` cua UI-6, `OBieuThuc` cua UI-5), va
        //    nguoi thu ba se ⛔ khong biet la phai tu ve. Mot bat bien song trong
        //    y thuc cua tung nguoi goi la mot bat bien se mat dung o nguoi goi
        //    tiep theo.
        //
        // ⚠️ Ve nay khac ve `active`: `active` chan **lan huy cua ta**, con day
        //    chan mot phan hoi 200 mang `node_id` KHAC (phan hoi den muon tu mot
        //    request truoc). Hai nguon lech khac nhau, can hai phep chan.
        .then(ket => {
          if (active && ket.node_id === selectedNodeId) setGoiY(ket)
        })
        .catch(() => { if (active) setGoiY(undefined) })
    }, 200)
    return () => { active = false; window.clearTimeout(timer) }
  }, [workflow?.id, selectedNodeId, document, csrf, offline]) // eslint-disable-line react-hooks/exhaustive-deps

  return goiY
}
