/**
 * BangDuAn — quan ly du an. (H44 B5 buoc 6)
 *
 * ## Menh de quyet dinh: nut XOA phai noi dieu gi se xay ra
 *
 * Nguoi dung nghi minh dang don mot cai NHAN. Neu thao tac ay dot luon noi
 * dung thi khong lay lai duoc, va ho chi phat hien SAU KHI da bam. Mot hop
 * thoai "ban co chac khong" khong noi duoc dieu gi se xay ra — nguoi ta bam
 * Yes theo phan xa.
 *
 * ## Va khoa lac quan phai LO RA, khong bi giau
 *
 * 409 la mot cau khac han 400: co nguoi sua truoc, khong phai ban go sai.
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { BangDuAn } from '../src/BangDuAn'
import { LoiApi, type Api } from '../src/api'
import type { DuAn } from '../src/kieu'

const D = (o: Partial<DuAn> = {}): DuAn => ({
  id: 'p1', ten: 'Ke toan 2026', revision: 3,
  created_at: '2026-09-06T00:00:00+00:00', updated_at: '2026-09-06T00:00:00+00:00',
  ...o,
})

function apiGia(o: Partial<Record<string, unknown>> = {}) {
  return {
    duAnLietKe: vi.fn().mockResolvedValue({ du_an: [] }),
    duAnTao: vi.fn().mockResolvedValue({ du_an: D() }),
    duAnDoiTen: vi.fn().mockResolvedValue({ du_an: D() }),
    duAnXoa: vi.fn().mockResolvedValue({ da_xoa: true }),
    duAnHoiThoai: vi.fn().mockResolvedValue({ hoi_thoai: [] }),
    ...o,
  } as unknown as Api
}

const ve = (api: Api) => render(<BangDuAn api={api} onDong={() => {}} />)

const coMot = (o: Partial<DuAn> = {}) => apiGia({
  duAnLietKe: vi.fn().mockResolvedValue({ du_an: [D(o)] }),
})

// ── 1. Nut xoa: HAI NHIP, va no noi dieu gi se xay ra ─────────────────────

describe('nut xoa hai nhip', () => {
  it('🔴 nhip MOT khong xoa gi — no hoi so hoi thoai va noi ra', async () => {
    const api = apiGia({
      duAnLietKe: vi.fn().mockResolvedValue({ du_an: [D()] }),
      duAnHoiThoai: vi.fn().mockResolvedValue({
        hoi_thoai: [{ id: 'a', title: 'x' }, { id: 'b', title: 'y' }],
      }),
    })
    const { container } = ve(api)
    fireEvent.click(await screen.findByLabelText('Xoá dự án: Ke toan 2026'))
    await waitFor(() => expect(container.textContent)
      .toContain('2 cuộc trò chuyện sẽ ở lại'))
    expect(api.duAnXoa).not.toHaveBeenCalled()
  })

  it('nhip HAI moi xoa that', async () => {
    const api = apiGia({
      duAnLietKe: vi.fn().mockResolvedValue({ du_an: [D()] }),
      duAnHoiThoai: vi.fn().mockResolvedValue({ hoi_thoai: [{ id: 'a', title: 'x' }] }),
    })
    ve(api)
    fireEvent.click(await screen.findByLabelText('Xoá dự án: Ke toan 2026'))
    const lai = await screen.findByLabelText(/Bấm lần nữa để xoá/)
    fireEvent.click(lai)
    await waitFor(() => expect(api.duAnXoa).toHaveBeenCalledWith('p1'))
  })

  it('⛔ HOVER va FOCUS khong lam gi — nguoi dung cam ung khong bao gio hover', async () => {
    // Ban dau con so gan vao `onMouseEnter`/`onFocus`. Kiem tren trinh duyet
    // that lam lo ra rang canh bao quan trong nhat cua man hinh nay khi do nam
    // sau mot cu chi ma mot nua so nguoi khong co.
    //
    // ⚠️ Ban dau cua CHINH phep kiem nay quet `BangDuAn.toString()` tim chu
    //    'onMouseEnter' — va no do vi **doan chu thich ngay tren day**. Dung
    //    bay da co tai lieu: mot bo do quet van ban trung phat viec giai thich.
    //    ⇒ Do HANH VI: ho/focus thi khong co gi hien ra.
    const api = apiGia({
      duAnLietKe: vi.fn().mockResolvedValue({ du_an: [D()] }),
      duAnHoiThoai: vi.fn().mockResolvedValue({ hoi_thoai: [{ id: 'a', title: 'x' }] }),
    })
    const { container } = ve(api)
    const nut = await screen.findByLabelText('Xoá dự án: Ke toan 2026')
    fireEvent.mouseEnter(nut)
    fireEvent.focus(nut)
    await new Promise((r) => setTimeout(r, 30))
    expect(api.duAnHoiThoai).not.toHaveBeenCalled()
    expect(container.textContent).not.toContain('sẽ ở lại')
  })

  it('nhan cua NUT mang cau canh bao, khong chi mot dong chu canh ben', async () => {
    // ⭐ Mot dong chu canh nut khong toi duoc trinh doc man hinh khi nguoi dung
    //    dang o TREN nut.
    const api = apiGia({
      duAnLietKe: vi.fn().mockResolvedValue({ du_an: [D()] }),
      duAnHoiThoai: vi.fn().mockResolvedValue({ hoi_thoai: [{ id: 'a', title: 'x' }] }),
    })
    ve(api)
    fireEvent.click(await screen.findByLabelText('Xoá dự án: Ke toan 2026'))
    await screen.findByLabelText(/1 cuộc trò chuyện sẽ ở lại/)
  })

  it('khong dem duoc thi nhip hai VAN xoa duoc', async () => {
    // Mot con so khong doc duoc khong duoc lam hong ca thao tac.
    const api = apiGia({
      duAnLietKe: vi.fn().mockResolvedValue({ du_an: [D()] }),
      duAnHoiThoai: vi.fn().mockRejectedValue(new LoiApi('http_500', 'x', 500)),
    })
    ve(api)
    fireEvent.click(await screen.findByLabelText('Xoá dự án: Ke toan 2026'))
    fireEvent.click(await screen.findByLabelText(/Bấm lần nữa để xoá/))
    await waitFor(() => expect(api.duAnXoa).toHaveBeenCalledWith('p1'))
  })
})

// ── 2. Khoa lac quan ───────────────────────────────────────────────────────

describe('revision', () => {
  it('doi ten gui lai revision NGUYEN VEN cua hang', async () => {
    const api = coMot({ revision: 7 })
    ve(api)
    fireEvent.click(await screen.findByLabelText('Đổi tên: Ke toan 2026'))
    fireEvent.change(screen.getByLabelText('Sửa tên dự án'),
      { target: { value: 'Ten moi' } })
    fireEvent.click(screen.getByLabelText('Lưu tên: Ke toan 2026'))
    await waitFor(() =>
      expect(api.duAnDoiTen).toHaveBeenCalledWith('p1', 'Ten moi', 7))
  })

  it('409 hien mot cau RIENG va tai lai, khong bao "tham so sai"', async () => {
    const api = coMot()
    ;(api.duAnDoiTen as ReturnType<typeof vi.fn>)
      .mockRejectedValue(new LoiApi('xung_dot', 'Project da duoc sua o phien khac.', 409))
    const { container } = ve(api)
    fireEvent.click(await screen.findByLabelText('Đổi tên: Ke toan 2026'))
    fireEvent.click(screen.getByLabelText('Lưu tên: Ke toan 2026'))
    await waitFor(() => expect(container.textContent).toContain('sửa ở nơi khác'))
    // ⭐ Va no PHAI tai lai: man hinh dang giu mot `revision` da cu.
    expect(api.duAnLietKe).toHaveBeenCalledTimes(2)
  })
})

// ── 3. Su vang mat phai noi ra ─────────────────────────────────────────────

describe('bang rong', () => {
  it('LOI khong duoc trong giong CHUA CO GI', async () => {
    const api = apiGia({
      duAnLietKe: vi.fn().mockRejectedValue(new LoiApi('http_500', 'May chu hong', 500)),
    })
    const { container } = ve(api)
    await waitFor(() => expect(container.textContent).toContain('May chu hong'))
    expect(container.textContent).not.toContain('Chưa có dự án nào')
  })

  it('rong THAT thi noi la rong va giai thich du an de lam gi', async () => {
    const { container } = ve(apiGia())
    await waitFor(() => expect(container.textContent).toContain('Chưa có dự án nào'))
  })
})

// ── 4. Tao ─────────────────────────────────────────────────────────────────

describe('tao', () => {
  it('o rong thi nut Tao bi vo hieu', async () => {
    ve(apiGia())
    await screen.findByLabelText('Tên dự án mới')
    expect((screen.getByText('Tạo') as HTMLButtonElement).disabled).toBe(true)
  })

  it('tao xong thi tai lai danh sach', async () => {
    const api = apiGia()
    ve(api)
    const o = await screen.findByLabelText('Tên dự án mới')
    fireEvent.change(o, { target: { value: 'Du an moi' } })
    fireEvent.submit(o.closest('form')!)
    await waitFor(() => expect(api.duAnTao).toHaveBeenCalledWith('Du an moi'))
    await waitFor(() => expect(api.duAnLietKe).toHaveBeenCalledTimes(2))
  })
})

// ── 5. Nhan kha truy cap phan biet duoc ────────────────────────────────────

describe('nhan nut', () => {
  it('ba nut tren mot hang deu noi ro chung thao tac len du an NAO', async () => {
    // ⛔ Cung loi da sua o `BangGhiNho`: n cai nut giong het nhau la n cau
    //    "button" giong het nhau voi trinh doc man hinh.
    ve(coMot())
    await screen.findByLabelText('Mở dự án: Ke toan 2026')
    expect(screen.getByLabelText('Đổi tên: Ke toan 2026')).toBeTruthy()
    expect(screen.getByLabelText('Xoá dự án: Ke toan 2026')).toBeTruthy()
  })
})
