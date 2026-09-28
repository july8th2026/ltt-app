// `DesignerDiff` — lớp XEM TRƯỚC của "Soạn bằng AI" (UI-8b, vá B7:
// `02_SCORECARD.md`). Component chỉ vẽ một `KetQuaDiffThietKe` đã tính sẵn và
// gọi đúng MỘT trong hai callback; test ở đây KHÔNG lặp lại phép toán diff
// (xem `DesignerDiffLogic.test.ts`) mà canh phần trợ năng + đại lượng hiển thị.
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest'
import { DesignerDiff } from '../src/features/editor/DesignerDiff/DesignerDiff'
import type { KetQuaDiffThietKe } from '../src/features/editor/DesignerDiff/diff'

afterEach(cleanup)

// jsdom KHÔNG làm layout thật ⇒ `offsetParent` luôn `null`, và bộ lọc
// "chỉ phần tử ĐANG HIỆN" của `useFocusTrap` (`el.offsetParent !== null`)
// loại sạch mọi phần tử — bẫy Tab không kiểm được nếu không vá chỗ này. Vá
// CHỈ trong tệp này (không đụng `tests/setup.ts` dùng chung): coi một phần
// tử có `parentNode` là "đang hiện", đúng giả định của `useFocusTrap` khi
// chạy trong trình duyệt thật.
beforeAll(() => {
  Object.defineProperty(HTMLElement.prototype, 'offsetParent', {
    configurable: true, get() { return this.parentNode as Element | null },
  })
})

const DIFF_CO_DOI: KetQuaDiffThietKe = {
  nodes: [
    { id: 'nmukpruo1-1', ten: 'Tạo ảnh AI', trangThai: 'them' },
    { id: 'nmukpruo1-2', ten: 'Tóm tắt văn bản', trangThai: 'xoa' },
    { id: 'nmukpruo1-3', ten: 'Tạo video AI', trangThai: 'doi_tham_so' },
  ],
  edges: [{ id: 'e1', trangThai: 'them' }],
  soNodeThem: 1, soNodeXoa: 1, soNodeDoiThamSo: 1,
  soEdgeThem: 1, soEdgeXoa: 0, coThayDoi: true,
}

describe('DesignerDiff — đại lượng hiển thị', () => {
  it('đếm hiện đúng "+N bước, −N bước, N bước đổi tham số"', () => {
    render(<DesignerDiff diff={DIFF_CO_DOI} apDung={vi.fn()} huy={vi.fn()} />)
    expect(screen.getByText(/\+1 bước, −1 bước, 1 bước đổi tham số/)).toBeInTheDocument()
  })

  it('hiện TÊN BƯỚC đọc được, ⛔ KHÔNG hiện node_id thô ở đâu trong nội dung đọc được', () => {
    render(<DesignerDiff diff={DIFF_CO_DOI} apDung={vi.fn()} huy={vi.fn()} />)
    expect(screen.getByText('Tạo ảnh AI')).toBeInTheDocument()
    expect(screen.getByText('Tóm tắt văn bản')).toBeInTheDocument()
    expect(screen.getByText('Tạo video AI')).toBeInTheDocument()
    // ⚠️ Đo bằng TEXT NODE thấy được (textContent của mục danh sách), không
    //    phải bằng grep chuỗi trên toàn bộ HTML — một `key=` React hay một
    //    `data-*` mang id vẫn hợp lệ, miễn NGƯỜI đọc không thấy nó.
    for (const li of Array.from(document.querySelectorAll('.designer-diff-item')))
      expect(li.textContent).not.toMatch(/nmukpruo1-/)
  })

  it('không có gì đổi ⇒ báo rõ, ⛔ không hiện danh sách rỗng khó hiểu', () => {
    const rong: KetQuaDiffThietKe = { nodes: [], edges: [], soNodeThem: 0, soNodeXoa: 0,
      soNodeDoiThamSo: 0, soEdgeThem: 0, soEdgeXoa: 0, coThayDoi: false }
    render(<DesignerDiff diff={rong} apDung={vi.fn()} huy={vi.fn()} />)
    expect(screen.getByText(/không có gì để áp dụng/i)).toBeInTheDocument()
    expect(document.querySelector('.designer-diff-list')).toBeNull()
  })
})

describe('DesignerDiff — hành động', () => {
  it('bấm "Áp dụng" gọi apDung, ⛔ KHÔNG gọi huy', () => {
    const apDung = vi.fn(); const huy = vi.fn()
    render(<DesignerDiff diff={DIFF_CO_DOI} apDung={apDung} huy={huy} />)
    fireEvent.click(screen.getByRole('button', { name: 'Áp dụng' }))
    expect(apDung).toHaveBeenCalledTimes(1)
    expect(huy).not.toHaveBeenCalled()
  })

  it('bấm "Huỷ" gọi huy, ⛔ KHÔNG gọi apDung', () => {
    const apDung = vi.fn(); const huy = vi.fn()
    render(<DesignerDiff diff={DIFF_CO_DOI} apDung={apDung} huy={huy} />)
    fireEvent.click(screen.getByRole('button', { name: 'Huỷ' }))
    expect(huy).toHaveBeenCalledTimes(1)
    expect(apDung).not.toHaveBeenCalled()
  })

  it('Escape = Huỷ', () => {
    const apDung = vi.fn(); const huy = vi.fn()
    render(<DesignerDiff diff={DIFF_CO_DOI} apDung={apDung} huy={huy} />)
    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' })
    expect(huy).toHaveBeenCalledTimes(1)
    expect(apDung).not.toHaveBeenCalled()
  })

  it('bấm ra ngoài (backdrop) = Huỷ', () => {
    const apDung = vi.fn(); const huy = vi.fn()
    render(<DesignerDiff diff={DIFF_CO_DOI} apDung={apDung} huy={huy} />)
    fireEvent.mouseDown(screen.getByRole('presentation'))
    expect(huy).toHaveBeenCalledTimes(1)
  })
})

describe('DesignerDiff — trợ năng (chuẩn UI-10b)', () => {
  it('role="dialog" + aria-modal + aria-labelledby trỏ tới tiêu đề thật', () => {
    render(<DesignerDiff diff={DIFF_CO_DOI} apDung={vi.fn()} huy={vi.fn()} />)
    const hopThoai = screen.getByRole('dialog')
    expect(hopThoai).toHaveAttribute('aria-modal', 'true')
    const idTieuDe = hopThoai.getAttribute('aria-labelledby')
    expect(idTieuDe).toBeTruthy()
    expect(document.getElementById(idTieuDe!)?.textContent).toBe('Xem trước thay đổi từ AI')
  })

  it('mở lớp ⇒ tiêu điểm rơi vào TRONG hộp thoại (bẫy focus)', () => {
    render(<DesignerDiff diff={DIFF_CO_DOI} apDung={vi.fn()} huy={vi.fn()} />)
    expect(screen.getByRole('dialog').contains(document.activeElement)).toBe(true)
  })

  it('Tab từ nút cuối cùng vòng lại nút ĐẦU TIÊN — không thoát ra Canvas phía sau', () => {
    render(<DesignerDiff diff={DIFF_CO_DOI} apDung={vi.fn()} huy={vi.fn()} />)
    const huyBtn = screen.getByRole('button', { name: 'Huỷ' })
    const apDungBtn = screen.getByRole('button', { name: 'Áp dụng' })
    apDungBtn.focus()
    expect(document.activeElement).toBe(apDungBtn)
    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Tab' })
    expect(document.activeElement).toBe(huyBtn)
  })

  it('Shift+Tab từ nút đầu tiên vòng lại nút CUỐI — hai hướng đều bị bẫy', () => {
    render(<DesignerDiff diff={DIFF_CO_DOI} apDung={vi.fn()} huy={vi.fn()} />)
    const huyBtn = screen.getByRole('button', { name: 'Huỷ' })
    const apDungBtn = screen.getByRole('button', { name: 'Áp dụng' })
    expect(document.activeElement).toBe(huyBtn) // huy la phan tu chon duoc DAU TIEN
    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Tab', shiftKey: true })
    expect(document.activeElement).toBe(apDungBtn)
  })

  it('cả hai nút đều có nhãn đọc được (accessible name), ⛔ không phải icon trơ', () => {
    render(<DesignerDiff diff={DIFF_CO_DOI} apDung={vi.fn()} huy={vi.fn()} />)
    expect(screen.getByRole('button', { name: 'Huỷ' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Áp dụng' })).toBeInTheDocument()
  })
})
