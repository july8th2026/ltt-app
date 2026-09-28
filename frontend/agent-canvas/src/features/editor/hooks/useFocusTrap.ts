import { useEffect, type RefObject } from 'react'

const CHON_DUOC =
  'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),' +
  'textarea:not([disabled]),[tabindex]:not([tabindex="-1"])'

/** Bẫy focus trong một ngăn kéo/hộp thoại — hạng mục 89 (Keyboard) + 90 (Focus)
 *  của `02_SCORECARD.md`: trước bản vá này, `Tab` từ phần tử cuối trong
 *  `CommandPalette`/`LayersDrawer`/`ContextMenu`/`ExecutionPanel` thoát thẳng
 *  ra Canvas phía sau — vi phạm mô hình "hộp thoại nổi trên nội dung".
 *
 *  ⭐ Chỉ bẫy `Tab`/`Shift+Tab` vòng lại ĐẦU/CUỐI — ⛔ KHÔNG chặn `Escape` (đã
 *     có `useEditorShortcuts` xử lý ở tầng `window`) và ⛔ KHÔNG tự ý đổi
 *     `autoFocus` đã có (vd. ô tìm của `CommandPalette`) để không phá hành vi
 *     "mở lại còn nguyên chữ đã gõ" đã ghi trong `CommandPalette.tsx`.
 *
 *  `active=false` (mặc định `true`) tắt bẫy mà KHÔNG unmount hook — dùng cho
 *  `ExecutionPanel`, luôn gắn trong DOM và chỉ ẩn/hiện bằng CSS `is-open`. */
export function useFocusTrap(ref: RefObject<HTMLElement | null>, active = true) {
  useEffect(() => {
    if (!active) return
    const container = ref.current
    if (!container) return
    const truocDo = document.activeElement as HTMLElement | null
    if (!container.contains(document.activeElement)) {
      const dauTien = container.querySelector<HTMLElement>(CHON_DUOC)
      dauTien?.focus()
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'Tab') return
      const items = Array.from(container.querySelectorAll<HTMLElement>(CHON_DUOC))
        .filter(el => el.offsetParent !== null)
      if (!items.length) return
      const dau = items[0]
      const cuoi = items[items.length - 1]
      const hienTai = document.activeElement as HTMLElement | null
      if (event.shiftKey) {
        if (hienTai === dau || !container.contains(hienTai)) { event.preventDefault(); cuoi.focus() }
      } else if (hienTai === cuoi || !container.contains(hienTai)) {
        event.preventDefault(); dau.focus()
      }
    }
    container.addEventListener('keydown', onKeyDown)
    return () => {
      container.removeEventListener('keydown', onKeyDown)
      // ⭐ Tra focus ve noi da mo ngan — nguoi dung ban phim khong bi "roi"
      //    xuong <body> sau khi dong.
      if (truocDo && document.body.contains(truocDo)) truocDo.focus()
    }
  }, [ref, active])
}
