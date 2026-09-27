import { useEffect } from 'react'
import { useReactFlow, useUpdateNodeInternals } from '@xyflow/react'
import type { CanvasNode } from '../../../workflowApi'
import type { BangDinhNghia } from '../graph'

/** Hai phép đo lại chỉ đúng SAU khi trình duyệt đã layout.
 *
 *  ⭐ VÌ SAO QUA `requestAnimationFrame`, không gọi thẳng: `updateNodeInternals`
 *     đo lại **cổng** của node. Gọi ngay trong effect thì đo một node chưa có
 *     kích thước ⇒ dây nối vẽ lệch khỏi cổng.
 *
 *  ⛔ Bản dọn `cancelAnimationFrame` là BẮT BUỘC, không phải lịch sự: một
 *     callback của lượt render cũ chạy sau khi component đã tháo sẽ đo cổng
 *     của một đồ thị không còn tồn tại.
 *
 *  Đặc tả cả hai điều trên: `tests/CanvasShellDacTa.test.tsx`.
 */
export function useCanvasFrames(page: { id: string; nodes: CanvasNode[] },
                                dinhNghia: BangDinhNghia,
                                readOnly: boolean,
                                selectedNodeId: string | undefined) {
  const reactFlow = useReactFlow()
  const updateNodeInternals = useUpdateNodeInternals()

  useEffect(() => {
    if (!dinhNghia.size || !page.nodes.length) return
    const frame = requestAnimationFrame(() => updateNodeInternals(page.nodes.map(node => node.id)))
    return () => cancelAnimationFrame(frame)
  }, [updateNodeInternals, dinhNghia, page.nodes, selectedNodeId])

  useEffect(() => {
    if (!readOnly || !page.nodes.length) return
    const frame = requestAnimationFrame(() => reactFlow.fitView({ padding: .12, maxZoom: .9, duration: 0 }))
    return () => cancelAnimationFrame(frame)
  }, [readOnly, page.id, page.nodes.length, reactFlow])
}
