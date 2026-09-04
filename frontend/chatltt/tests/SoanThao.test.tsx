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

describe('SoanThao — bon khuyet tat dinh kem tim ra tren production', () => {
  const tep = (n: string) => new File(['x'], n, { type: 'image/png' })

  it('MOT tep hong khong duoc giet ca lo', async () => {
    // 🔴 Do 03/09: chon 3 anh, mot cai hong ⇒ chi con 1/3. `try` bao ca vong
    //    lap nen tep sau tep hong khong bao gio duoc thu. Dung loi LibreChat
    //    da dinh: *Uploading multiple files fails ENTIRELY if any single file
    //    exceeds fileSizeLimit*.
    let i = 0
    const tai = vi.fn(async (f: File) => {
      i += 1
      if (f.name === 'hong.png') throw new Error('tham_so')
      return { key: `k${i}`, ten: f.name }
    })
    render(<SoanThao onGui={vi.fn()} dangChay={false} onDung={vi.fn()}
                     docAnh onTaiAnh={tai} toiDaAnh={4} />)
    fireEvent.change(screen.getByLabelText('Đính ảnh'), {
      target: { files: [tep('a.png'), tep('hong.png'), tep('c.png')] },
    })
    await waitFor(() => expect(tai).toHaveBeenCalledTimes(3))
    await waitFor(() => expect(screen.getByText('a.png')).toBeTruthy())
    expect(screen.getByText('c.png')).toBeTruthy()      // tep SAU tep hong
    expect(screen.getByRole('alert').textContent).toContain('hong.png')
  })

  it('loi hien thanh CAU, khong phai ma HTTP', async () => {
    const loi = Object.assign(new Error('http_400'), { code: 'http_400' })
    const tai = vi.fn(async () => { throw loi })
    render(<SoanThao onGui={vi.fn()} dangChay={false} onDung={vi.fn()}
                     docAnh onTaiAnh={tai} />)
    fireEvent.change(screen.getByLabelText('Đính ảnh'), { target: { files: [tep('x.png')] } })
    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy())
    const t = screen.getByRole('alert').textContent || ''
    expect(t).toContain('không phải ảnh hợp lệ')
    expect(t).not.toMatch(/^Không tải được 1 ảnh — x\.png: http_400$/)
  })

  it('doi hoi thoai thi BO anh dang dinh', async () => {
    // Anh cua hoi thoai truoc di theo sang hoi thoai sau = nguoi dung tra tien
    // cho mot ngu canh ho khong he chon.
    const tai = vi.fn(async (f: File) => ({ key: 'k1', ten: f.name }))
    const { rerender } = render(
      <SoanThao onGui={vi.fn()} dangChay={false} onDung={vi.fn()}
                docAnh onTaiAnh={tai} hoiThoai="cv1" />)
    fireEvent.change(screen.getByLabelText('Đính ảnh'), { target: { files: [tep('meo.png')] } })
    await waitFor(() => expect(screen.getByText('meo.png')).toBeTruthy())

    rerender(<SoanThao onGui={vi.fn()} dangChay={false} onDung={vi.fn()}
                       docAnh onTaiAnh={tai} hoiThoai="cv2" />)
    await waitFor(() => expect(screen.queryByText('meo.png')).toBeNull())
  })

  it('doi sang model khong doc anh thi bo anh VA noi ra', async () => {
    const tai = vi.fn(async (f: File) => ({ key: 'k1', ten: f.name }))
    const { rerender } = render(
      <SoanThao onGui={vi.fn()} dangChay={false} onDung={vi.fn()}
                docAnh onTaiAnh={tai} hoiThoai="cv1" />)
    fireEvent.change(screen.getByLabelText('Đính ảnh'), { target: { files: [tep('meo.png')] } })
    await waitFor(() => expect(screen.getByText('meo.png')).toBeTruthy())

    rerender(<SoanThao onGui={vi.fn()} dangChay={false} onDung={vi.fn()}
                       docAnh={false} onTaiAnh={tai} hoiThoai="cv1" />)
    await waitFor(() => expect(screen.queryByText('meo.png')).toBeNull())
    expect(screen.getByRole('alert').textContent).toContain('không đọc ảnh')
  })
})
