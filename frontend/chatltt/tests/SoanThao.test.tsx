/**
 * Ba tinh chat cua o soan, va tinh chat dau la ly do tep nay ton tai:
 * go tieng Viet bang Telex/VNI khong duoc bi cat lam doi.
 */
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { SoanThao } from '../src/SoanThao'

function o() { return screen.getByLabelText('Nội dung tin nhắn') as HTMLTextAreaElement }

describe('SoanThao', () => {
  it('Enter GIUA luc go IME thi KHONG gui — ca ba duong bao IME', () => {
    const gui = vi.fn()
    render(<SoanThao onGui={gui} dangChay={false} onDung={() => {}} />)
    fireEvent.change(o(), { target: { value: 'ddaay' } })

    // (a) co cua ta: compositionstart chua co compositionend
    fireEvent.compositionStart(o())
    fireEvent.keyDown(o(), { key: 'Enter' })
    expect(gui).not.toHaveBeenCalled()
    fireEvent.compositionEnd(o())

    // (b) Firefox/Edge: `key === 'Process'`
    fireEvent.keyDown(o(), { key: 'Process' })
    expect(gui).not.toHaveBeenCalled()

    // (c) Safari: chi con `keyCode === 229`
    fireEvent.keyDown(o(), { key: 'Enter', keyCode: 229 })
    expect(gui).not.toHaveBeenCalled()

    // Go xong ⇒ Enter gui.
    fireEvent.keyDown(o(), { key: 'Enter' })
    expect(gui).toHaveBeenCalledWith('ddaay')
  })

  it('Shift+Enter xuong dong, khong gui; o duoc don sau khi gui', () => {
    const gui = vi.fn()
    render(<SoanThao onGui={gui} dangChay={false} onDung={() => {}} />)
    fireEvent.change(o(), { target: { value: 'mot dong' } })
    fireEvent.keyDown(o(), { key: 'Enter', shiftKey: true })
    expect(gui).not.toHaveBeenCalled()
    fireEvent.keyDown(o(), { key: 'Enter' })
    expect(gui).toHaveBeenCalledWith('mot dong')
    expect(o().value).toBe('')
  })

  it('chi khoang trang thi khong gui', () => {
    const gui = vi.fn()
    render(<SoanThao onGui={gui} dangChay={false} onDung={() => {}} />)
    fireEvent.change(o(), { target: { value: '   \n  ' } })
    fireEvent.keyDown(o(), { key: 'Enter' })
    expect(gui).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Gửi' })).toBeDisabled()
  })

  it('dang chay ⇒ hien nut Dung, va Enter khong gui them luot nua', () => {
    const gui = vi.fn()
    const dung = vi.fn()
    render(<SoanThao onGui={gui} dangChay onDung={dung} />)
    fireEvent.change(o(), { target: { value: 'them' } })
    fireEvent.keyDown(o(), { key: 'Enter' })
    expect(gui).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Dừng' }))
    expect(dung).toHaveBeenCalled()
  })

  it('vo hieu khi model chua san sang', () => {
    render(<SoanThao onGui={() => {}} dangChay={false} onDung={() => {}} vohieu goiY="Model chưa sẵn sàng" />)
    expect(o()).toBeDisabled()
    expect(o().placeholder).toBe('Model chưa sẵn sàng')
  })
})
