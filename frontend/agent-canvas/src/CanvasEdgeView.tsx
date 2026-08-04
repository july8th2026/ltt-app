import {BaseEdge,EdgeLabelRenderer,getSmoothStepPath,type EdgeProps} from '@xyflow/react'

type EdgeData={condition?:'success'|'error';modality?:string;running?:boolean;
  onInsert?:(client:{x:number;y:number})=>void}

export function CanvasEdgeView({id,sourceX,sourceY,targetX,targetY,sourcePosition,targetPosition,
  markerEnd,style,data,selected}:EdgeProps){
  const [path,labelX,labelY]=getSmoothStepPath({sourceX,sourceY,targetX,targetY,sourcePosition,targetPosition,borderRadius:14})
  const typed=(data??{}) as EdgeData
  return <><BaseEdge id={id} path={path} markerEnd={markerEnd} style={style}/>
    <EdgeLabelRenderer><button className={`edge-insert nodrag nopan${selected?' selected':''}`}
      aria-label="Chèn bước vào kết nối" title="Chèn bước"
      style={{transform:`translate(-50%,-50%) translate(${labelX}px,${labelY}px)`}}
      onClick={event=>{event.stopPropagation();typed.onInsert?.({x:event.clientX,y:event.clientY})}}>+</button></EdgeLabelRenderer>
  </>
}
