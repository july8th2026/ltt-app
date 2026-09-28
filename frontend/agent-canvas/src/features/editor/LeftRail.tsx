import { useEffect, useRef, useState } from 'react'
import type { EditorAction } from '../../editorState'
import { useFocusTrap } from './hooks/useFocusTrap'
import type { NganDesktop } from './kieu'

/** Danh sách CHO NGƯỜI ĐỌC — nguồn thật của từng phím ở `useEditorShortcuts.ts`
 *  và `a11y.ts` (React Flow). ⭐ Hạng mục 89 (Keyboard=45) chê "có phím tắt,
 *  không tài liệu" — bảng này là tài liệu, ⛔ không phải phím tắt mới. */
const PHIM_TAT: { to: string; y: string }[] = [
  { to: 'Ctrl/Cmd + K', y: 'Mở bảng lệnh' },
  { to: 'Ctrl/Cmd + Z', y: 'Hoàn tác' },
  { to: 'Ctrl/Cmd + Shift + Z, Ctrl/Cmd + Y', y: 'Làm lại' },
  { to: 'Ctrl/Cmd + D', y: 'Nhân bản khối/lựa chọn đang chọn' },
  { to: 'Ctrl/Cmd + C / V', y: 'Sao chép / dán' },
  { to: 'Ctrl/Cmd + A', y: 'Chọn tất cả khối' },
  { to: 'N', y: 'Tạo sticky note' },
  { to: 'F', y: 'Tạo frame quanh lựa chọn' },
  { to: 'D', y: 'Mở ngăn Mẫu & thiết lập' },
  { to: 'Mũi tên (giữ Shift = 10px)', y: 'Di chuyển khối đang chọn' },
  { to: 'Delete / Backspace', y: 'Xoá khối hoặc đường nối đang chọn' },
  { to: 'Escape', y: 'Đóng ngăn kéo/menu/hộp thoại đang mở' },
  { to: 'Enter / Space (khi khối/dây đang focus)', y: 'Chọn khối hoặc đường nối' },
  { to: '?', y: 'Mở bảng phím tắt này' },
]

type Props = {
  desktopPanel: NganDesktop
  moNgan: (ngan: NganDesktop) => void
  batNgan: (ngan: Exclude<NganDesktop, null>) => void
  hasAnyNodes: boolean
  showLayers: boolean
  batLayers: () => void
  readOnly: boolean
  coQuaKhu: boolean
  coTuongLai: boolean
  boChon: () => void
  dispatch: (action: EditorAction) => void
}

/** Thanh dọc bên trái: chọn · thêm node · mẫu · chi tiết · lớp · ghi chú · undo.
 *
 *  🔴 Nút "Chi tiết node" ở đây là ĐƯỜNG VÀO DUY NHẤT của inspector trên
 *     desktop: `.canvas-mobile-tabs` (nút "Chi tiết") là `display:none` trên
 *     màn rộng. Trước task 15, tham số còn ở `ContextComposer` nổi lên cạnh
 *     node nên thiếu nó không ai thấy; giờ MỌI tham số ở inspector.
 */
export function LeftRail(p: Props) {
  const [moPhimTat, setMoPhimTat] = useState(false)
  const hopThoai = useRef<HTMLElement>(null)
  useFocusTrap(hopThoai, moPhimTat)
  // ⭐ Phím `?` mở bảng — tự quản trong component này, ⛔ không cần EditorShell
  //    biết: cùng chốt "bỏ qua khi đang gõ" như `useEditorShortcuts.ts`.
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target
      if (target instanceof HTMLElement && target.closest('input,textarea,select,[contenteditable="true"]')) return
      if (event.key === '?') { event.preventDefault(); setMoPhimTat(m => !m) }
      else if (event.key === 'Escape') setMoPhimTat(false)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])
  return <>
    <nav className="canvas-rail" aria-label="Công cụ Canvas">
    <button title="Chọn" aria-label="Công cụ chọn" aria-pressed={!p.desktopPanel}>↖</button>
    <button title="Thêm node" aria-label="Mở công cụ" aria-pressed={p.desktopPanel==='tools'} onClick={()=>{const open=p.desktopPanel!=='tools';p.moNgan(open?'tools':null);if(open){p.boChon()}}}>＋</button>
    <button title="Mẫu & thiết lập" aria-label="Mở mẫu và thiết lập" aria-pressed={p.desktopPanel==='workspace'} onClick={()=>p.batNgan('workspace')}>▦</button>
    <button title="Chi tiết node" aria-label="Mở chi tiết node" aria-pressed={p.desktopPanel==='inspector'} onClick={()=>p.batNgan('inspector')}>☰</button>
    {p.hasAnyNodes&&<><button title="Lớp" aria-label="Mở danh sách lớp" aria-pressed={p.showLayers} onClick={p.batLayers}>☷</button>
      <button title="Sticky note" aria-label="Tạo sticky note" disabled={p.readOnly} onClick={()=>p.dispatch({type:'noteAdd',text:'Ghi chú mới'})}>□</button>
      <button title="Bình luận" aria-label="Tạo comment" disabled={p.readOnly} onClick={()=>p.dispatch({type:'commentAdd',text:'Bình luận mới'})}>◌</button></>}
    <span />
    <button title="Hoàn tác" aria-label="Hoàn tác" disabled={!p.coQuaKhu||p.readOnly} onClick={()=>p.dispatch({type:'undo'})}>↶</button>
    <button title="Làm lại" aria-label="Làm lại" disabled={!p.coTuongLai||p.readOnly} onClick={()=>p.dispatch({type:'redo'})}>↷</button>
    <button title="Phím tắt (?)" aria-label="Mở bảng phím tắt" aria-pressed={moPhimTat} onClick={()=>setMoPhimTat(m=>!m)}>?</button>
    </nav>
    {moPhimTat && <div className="command-backdrop" role="presentation" onMouseDown={event=>event.target===event.currentTarget&&setMoPhimTat(false)}>
      <section ref={hopThoai} className="command-palette shortcuts-help" role="dialog" aria-modal="true" aria-label="Bảng phím tắt Canvas">
        <header><strong>Phím tắt</strong><button aria-label="Đóng bảng phím tắt" onClick={()=>setMoPhimTat(false)} autoFocus>×</button></header>
        <dl className="shortcuts-help-list">{PHIM_TAT.map(item=><div key={item.to}><dt>{item.to}</dt><dd>{item.y}</dd></div>)}</dl>
      </section></div>}
  </>
}
