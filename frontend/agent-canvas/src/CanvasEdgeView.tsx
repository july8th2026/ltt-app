import {BaseEdge,getSmoothStepPath,type EdgeProps} from '@xyflow/react'

// ⛔ NUT "+" CHEN BUOC DA GO (UI-0 Task 5) — dung khoi phuc ma khong noi day.
//
// No goi `data.onInsert?.(...)`, va `onInsert` CHUA BAO GIO duoc gan o bat ky
// dau trong `src/`: `CanvasShell.displayEdges` khong dat khoa do. Bam that tren
// trinh duyet 27/09/2026:
//
//     node truoc/sau : 3 -> 3        canh truoc/sau : 2 -> 2
//     picker mo      : false         palette mo     : false
//     inspector mo   : false         bang lenh mo   : false
//
// Tuc: mot nut khong-op, ve tren MOI canh cua moi do thi. Mot nut chet lam
// nguoi dung mat niem tin vao MOI nut con lai — dat hon nhieu so voi viec
// khong co nut nao.
//
// ⭐ UI-4 se dung lai no CO THAT (quick-add tu cong + chen giua canh). Luc do
//    phai noi `onInsert` TRUOC, roi moi ve nut.
export function CanvasEdgeView({id,sourceX,sourceY,targetX,targetY,
  sourcePosition,targetPosition,markerEnd,style}:EdgeProps){
  const [path]=getSmoothStepPath({sourceX,sourceY,targetX,targetY,
    sourcePosition,targetPosition,borderRadius:14})
  return <BaseEdge id={id} path={path} markerEnd={markerEnd} style={style}/>
}
