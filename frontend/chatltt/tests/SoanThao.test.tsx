/**
 * Ba tinh chat cua o soan, va tinh chat dau la ly do tep nay ton tai:
 * go tieng Viet bang Telex/VNI khong duoc bi cat lam doi.
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
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
    expect(gui).toHaveBeenCalledWith('ddaay', [])   // (chu, khoa anh dinh)
  })

  it('Shift+Enter xuong dong, khong gui; o duoc don sau khi gui', () => {
    const gui = vi.fn()
    render(<SoanThao onGui={gui} dangChay={false} onDung={() => {}} />)
    fireEvent.change(o(), { target: { value: 'mot dong' } })
    fireEvent.keyDown(o(), { key: 'Enter', shiftKey: true })
    expect(gui).not.toHaveBeenCalled()
    fireEvent.keyDown(o(), { key: 'Enter' })
    expect(gui).toHaveBeenCalledWith('mot dong', [])
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

describe('SoanThao — dinh anh cho model vision', () => {
  /**
   * ⛔ O chon tep chi hien khi model DA KHAI `reads_images`. Khong co dieu kien
   *    do thi nguoi dung dinh anh vao `ltt_llm` (text-only) roi cho mot cau tra
   *    loi ve buc anh ma model chua bao gio thay. May chu se tu choi, nhung
   *    moi loi tot nhat la loi khong the bam ra duoc.
   */
  it('model KHONG doc anh thi khong co o chon tep', () => {
    render(<SoanThao onGui={vi.fn()} dangChay={false} onDung={vi.fn()}
                     docAnh={false} onTaiAnh={vi.fn()} />)
    expect(screen.queryByLabelText('Đính ảnh')).toBeNull()
  })

  it('model doc anh thi co o chon tep va nut dinh', () => {
    render(<SoanThao onGui={vi.fn()} dangChay={false} onDung={vi.fn()}
                     docAnh onTaiAnh={vi.fn()} />)
    expect(screen.getByLabelText('Đính ảnh')).toBeTruthy()
    expect(screen.getByRole('button', { name: /Ảnh/ })).toBeTruthy()
  })

  it('tai anh xong thi hien ten, va Gui mang theo KHOA chu khong mang ten', async () => {
    const gui = vi.fn()
    const tai = vi.fn(async () => ({ key: 'chatltt/anh-vao/u/abc.png', ten: 'meo.png' }))
    render(<SoanThao onGui={gui} dangChay={false} onDung={vi.fn()}
                     docAnh onTaiAnh={tai} />)
    const o = screen.getByLabelText('Đính ảnh') as HTMLInputElement
    const tep = new File([new Uint8Array([1, 2, 3])], 'meo.png', { type: 'image/png' })
    fireEvent.change(o, { target: { files: [tep] } })
    await waitFor(() => expect(screen.getByText('meo.png')).toBeTruthy())

    fireEvent.change(screen.getByLabelText('Nội dung tin nhắn'),
                     { target: { value: 'anh nay la gi' } })
    fireEvent.click(screen.getByRole('button', { name: 'Gửi' }))
    expect(gui).toHaveBeenCalledWith('anh nay la gi', ['chatltt/anh-vao/u/abc.png'])
  })

  it('bo mot anh da dinh thi no khong di theo luot', async () => {
    const gui = vi.fn()
    const tai = vi.fn(async () => ({ key: 'k1', ten: 'meo.png' }))
    render(<SoanThao onGui={gui} dangChay={false} onDung={vi.fn()}
                     docAnh onTaiAnh={tai} />)
    fireEvent.change(screen.getByLabelText('Đính ảnh'), {
      target: { files: [new File(['x'], 'meo.png', { type: 'image/png' })] },
    })
    await waitFor(() => expect(screen.getByText('meo.png')).toBeTruthy())
    fireEvent.click(screen.getByLabelText('Bỏ ảnh meo.png'))
    fireEvent.change(screen.getByLabelText('Nội dung tin nhắn'),
                     { target: { value: 'khong anh' } })
    fireEvent.click(screen.getByRole('button', { name: 'Gửi' }))
    expect(gui).toHaveBeenCalledWith('khong anh', [])
  })

  it('tai anh loi thi noi ra, khong nuot lang le', async () => {
    const tai = vi.fn(async () => { throw new Error('Ảnh tham chiếu quá lớn.') })
    render(<SoanThao onGui={vi.fn()} dangChay={false} onDung={vi.fn()}
                     docAnh onTaiAnh={tai} />)
    fireEvent.change(screen.getByLabelText('Đính ảnh'), {
      target: { files: [new File(['x'], 'to.png', { type: 'image/png' })] },
    })
    await waitFor(() => expect(screen.getByRole('alert').textContent)
      .toContain('Ảnh tham chiếu quá lớn.'))
  })

  it('vuot tran thi bao va chi nhan du tran', async () => {
    let i = 0
    const tai = vi.fn(async () => ({ key: `k${i++}`, ten: `a${i}.png` }))
    render(<SoanThao onGui={vi.fn()} dangChay={false} onDung={vi.fn()}
                     docAnh onTaiAnh={tai} toiDaAnh={2} />)
    const tep = (n: string) => new File(['x'], n, { type: 'image/png' })
    fireEvent.change(screen.getByLabelText('Đính ảnh'), {
      target: { files: [tep('1.png'), tep('2.png'), tep('3.png')] },
    })
    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy())
    expect(tai).toHaveBeenCalledTimes(2)
  })
})
