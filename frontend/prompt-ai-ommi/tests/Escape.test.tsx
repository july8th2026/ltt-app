import { fireEvent, render } from '@testing-library/react'
import { useState } from 'react'
import { describe, expect, it } from 'vitest'
import { useEscape } from '../src/useEscape'

/**
 * H19.9 — Escape phải đóng lớp phủ.
 *
 * Đo bằng trình duyệt thật (2026-08-06) cho thấy OMMI đạt phần khó: 31 phần tử
 * đi hết một vòng Tab đều có viền focus rõ, không phần tử tương tác nào thiếu
 * tên đọc được, không `tabindex` dương. Thứ DUY NHẤT thiếu là lối ra bằng bàn
 * phím — mở panel rồi phải Tab qua toàn bộ nội dung mới tới được nút "×".
 */
function Thu({ batDau = true }: { batDau?: boolean }) {
  const [mo, setMo] = useState(batDau)
  useEscape(mo, () => setMo(false))
  return <div data-testid="trang">{mo ? <p>đang mở</p> : <p>đã đóng</p>}</div>
}

describe('useEscape', () => {
  it('Escape đóng lớp phủ đang mở', () => {
    const { getByTestId } = render(<Thu />)
    expect(getByTestId('trang').textContent).toBe('đang mở')
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(getByTestId('trang').textContent).toBe('đã đóng')
  })

  it('phím khác không đóng gì', () => {
    const { getByTestId } = render(<Thu />)
    fireEvent.keyDown(document, { key: 'Enter' })
    fireEvent.keyDown(document, { key: 'a' })
    expect(getByTestId('trang').textContent).toBe('đang mở')
  })

  it('không gắn listener khi lớp phủ đang đóng', () => {
    // Gắn listener khi không có gì để đóng nghĩa là Escape của người dùng bị
    // "ăn" mất ở đây thay vì tới lớp phủ thật sự đang mở bên ngoài.
    const goi: string[] = []
    const goc = document.addEventListener.bind(document)
    document.addEventListener = ((t: string, ...r: unknown[]) => {
      if (t === 'keydown') goi.push(t)
      return goc(t, ...(r as [EventListenerOrEventListenerObject]))
    }) as typeof document.addEventListener
    try {
      render(<Thu batDau={false} />)
      expect(goi).toEqual([])
    } finally {
      document.addEventListener = goc
    }
  })
})
