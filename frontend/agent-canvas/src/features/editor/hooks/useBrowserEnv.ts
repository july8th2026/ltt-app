import { useEffect, useState } from 'react'

/** Trình duyệt nói với trình soạn: còn mạng không, màn hình có hẹp không.
 *
 *  ⭐ Hook này ⛔ KHÔNG phụ thuộc tài liệu, và đó là cả lý do nó tách riêng:
 *     `offline` là **đầu vào** của vòng tự lưu (`useWorkflowDocument`), nên nó
 *     phải có mặt TRƯỚC tài liệu. Gộp nó vào chỗ đọc `page` là tạo một vòng
 *     nhập ngược.
 */
export function useBrowserEnv() {
  const [offline, setOffline] = useState(!navigator.onLine)
  const [readOnly, setReadOnly] = useState(window.innerWidth <= 640)

  useEffect(() => {
    const online = () => setOffline(false); const offlineNow = () => setOffline(true)
    const resize = () => setReadOnly(window.innerWidth <= 640)
    window.addEventListener('online', online); window.addEventListener('offline', offlineNow); window.addEventListener('resize', resize)
    return () => { window.removeEventListener('online', online); window.removeEventListener('offline', offlineNow); window.removeEventListener('resize', resize) }
  }, [])

  return { offline, readOnly }
}
