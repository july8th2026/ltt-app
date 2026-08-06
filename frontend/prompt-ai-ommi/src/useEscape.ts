import { useEffect } from 'react'

/**
 * Đóng một lớp phủ bằng phím Escape.
 *
 * Vì sao cần: bốn màn của OMMI đều mở panel chi tiết / hộp xác nhận, và trước
 * 2026-08-06 **không màn nào xử lý Escape**. Người dùng bàn phím mở panel ra
 * rồi phải Tab qua toàn bộ nội dung mới tới được nút "×" — hoặc dùng chuột.
 * Đo bằng trình duyệt thật mới thấy: viền focus đều ổn, chỉ thiếu đúng lối ra.
 *
 * Đặt ở một hook dùng chung thay vì chép vào từng màn: bốn bản sao của cùng
 * một `addEventListener` là bốn chỗ để quên gỡ listener.
 */
export function useEscape(dangMo: boolean, dong: () => void) {
  useEffect(() => {
    if (!dangMo) return
    const xuLy = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        // Chặn lan lên: hai lớp phủ chồng nhau thì Escape chỉ được đóng lớp
        // trên cùng, không phải đóng sạch cả hai cùng lúc.
        e.stopPropagation()
        dong()
      }
    }
    document.addEventListener('keydown', xuLy)
    return () => document.removeEventListener('keydown', xuLy)
  }, [dangMo, dong])
}
