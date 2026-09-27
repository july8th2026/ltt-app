import { useCallback, useState } from 'react'

/** Lựa chọn trên khung vẽ: node nào, cạnh nào.
 *
 *  ⚠️ `selected` (nhiều node) và `state.selectedId` (một node cho Inspector) là
 *     HAI thứ, ⛔ đừng gộp: chọn ba node để nhân bản không có nghĩa là Inspector
 *     biết hiện tham số của node nào. Nên `onSelectionChange` đặt `selectedId`
 *     CHỈ khi đúng một node được chọn, và xoá nó khi có cạnh được chọn.
 */
export function useCanvasSelection(dispatchSelect: (id?: string) => void) {
  const [selected, setSelected] = useState<string[]>([])
  const [selectedEdges, setSelectedEdges] = useState<string[]>([])

  const onSelectionChange = useCallback(({ nodes, edges }:
      { nodes: { id: string }[]; edges: { id: string }[] }) => {
    const next = nodes.map(node => node.id).sort()
    const nextEdges = edges.map(edge => edge.id).sort()
    if (nextEdges.length) dispatchSelect()
    else if (next.length === 1) dispatchSelect(next[0])
    // ⭐ Giu nguyen THAM CHIEU khi danh sach khong doi. React Flow ban
    //    `onSelectionChange` moi lan no ve lai, nen mot mang moi moi lan la
    //    mot vong render vo ich — va `displayNodes` phu thuoc `selected`.
    setSelected(previous => previous.length === next.length && previous.every((id, index) => id === next[index])
      ? previous : next)
    setSelectedEdges(previous => previous.length === nextEdges.length && previous.every((id, index) => id === nextEdges[index])
      ? previous : nextEdges)
  }, [dispatchSelect])

  /** Bỏ lựa chọn TRÊN KHUNG (node + cạnh), GIỮ `state.selectedId`.
   *
   *  ⚠️ Hai hàm dưới đây ⛔ KHÔNG hoán đổi được, và bản gốc dùng đúng hai thứ
   *     khác nhau ở hai chỗ khác nhau:
   *       · đổi/thêm Page  -> `xoaLuaChon()`, giữ `selectedId`
   *       · mở bảng node · bấm khoảng trống · Escape -> `boChon()`, xoá cả
   *     Gộp chúng lại là đổi thứ Inspector hiển thị sau một cú đổi page. */
  const xoaLuaChon = useCallback(() => {
    setSelected([]); setSelectedEdges([])
  }, [])

  /** Bỏ mọi lựa chọn — node, cạnh, VÀ node của Inspector. */
  const boChon = useCallback(() => {
    setSelected([]); setSelectedEdges([]); dispatchSelect()
  }, [dispatchSelect])

  return { selected, setSelected, selectedEdges, setSelectedEdges,
    onSelectionChange, xoaLuaChon, boChon }
}
