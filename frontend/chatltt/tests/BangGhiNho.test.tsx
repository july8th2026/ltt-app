/**
 * BangGhiNho — nguoi dung XEM, SUA, XOA thu may nho ve minh. (H44 B4 buoc 6)
 *
 * ## Menh de quyet dinh: nguoi dung sua duoc CA mau do MAY ghi
 *
 * Do la toan bo loi hua cua B4. Mot bang chi cho sua mau nguoi tu go van "co
 * giao dien quan ly" — va van de nguyen cai ca lam ta lo: may suy ra mot dieu
 * SAI ve khach, roi lap lai no o moi luot sau.
 *
 * ## Va mot menh de ve SU VANG MAT
 *
 * Bang rong vi LOI trong y het bang rong vi CHUA CO GI. Neu khong noi ra,
 * nguoi dung ket luan may da quen het — mot ket luan sai ma khong ai bac.
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { BangGhiNho } from '../src/BangGhiNho'
import { LoiApi, type Api } from '../src/api'
import type { GhiNho } from '../src/kieu'

const M = (o: Partial<GhiNho>): GhiNho => ({
  id: 'gn_1', pham_vi: 'nguoi_dung', muc_tieu_id: '', nguon: 'nguoi',
  noi_dung: 'Toi lam ke toan', meta: {},
  created_at: '2026-09-06T00:00:00+00:00', updated_at: '2026-09-06T00:00:00+00:00',
  ...o,
})

function apiGia(o: Partial<Record<string, unknown>> = {}) {
  return {
    ghiNhoLietKe: vi.fn().mockResolvedValue({
      ghi_nho: [], tran_moi_pham_vi: 2000, tran_mot_ban: 500,
    }),
    ghiNhoThem: vi.fn().mockResolvedValue({ ghi_nho: M({}), trang_thai: 'them' }),
    ghiNhoSua: vi.fn().mockResolvedValue({ ghi_nho: M({}) }),
    ghiNhoXoa: vi.fn().mockResolvedValue({ da_xoa: true }),
    ...o,
  } as unknown as Api
}

const ve = (api: Api) => render(<BangGhiNho api={api} onDong={() => {}} />)

describe('nguon: nguoi vs may', () => {
  it('🔴 sua duoc mau do MAY ghi — day la loi hua cua B4', async () => {
    const api = apiGia({
      ghiNhoLietKe: vi.fn().mockResolvedValue({
        ghi_nho: [M({ id: 'gn_may', nguon: 'model', noi_dung: 'Khach thich ca phe' })],
        tran_moi_pham_vi: 2000, tran_mot_ban: 500,
      }),
    })
    ve(api)
    const nut = await screen.findByLabelText('Sửa: Khach thich ca phe')
    fireEvent.click(nut)
    const o = screen.getByLabelText('Sửa nội dung ghi nhớ')
    fireEvent.change(o, { target: { value: 'Khach da bo ca phe' } })
    fireEvent.click(screen.getByLabelText('Lưu sửa: Khach thich ca phe'))
    await waitFor(() => {
      expect(api.ghiNhoSua).toHaveBeenCalledWith('gn_may', 'Khach da bo ca phe')
    })
  })

  it('noi ro AI viet, bang CHU chu khong bang mau', async () => {
    // ⭐ Mau khong toi duoc trinh doc man hinh, va cung khong toi duoc nguoi mu
    //    mau. Mot mau do MAY suy ra co the SAI — do tin cay khac han mau nguoi
    //    tu dan, nen khac biet ay phai DOC duoc.
    const api = apiGia({
      ghiNhoLietKe: vi.fn().mockResolvedValue({
        ghi_nho: [M({ id: 'a', nguon: 'model' }), M({ id: 'b', nguon: 'nguoi' })],
        tran_moi_pham_vi: 2000, tran_mot_ban: 500,
      }),
    })
    const { container } = ve(api)
    await waitFor(() => expect(container.textContent).toContain('Trợ lý tự ghi'))
    expect(container.textContent).toContain('Bạn tự ghi')
  })
})

describe('nut trong hang sua noi ro no thao tac len mau NAO', () => {
  it('hai nut "Luu" tren mot man hinh phai phan biet duoc', async () => {
    // ⛔ Nut "Luu" cua o THEM va nut "Luu" cua hang SUA doc len giong het nhau.
    //    Cung loi da sua o nut "Xoa": nam cau "button" giong nhau.
    const api = apiGia({
      ghiNhoLietKe: vi.fn().mockResolvedValue({
        ghi_nho: [M({ noi_dung: 'Toi o Ha Noi' })],
        tran_moi_pham_vi: 2000, tran_mot_ban: 500,
      }),
    })
    ve(api)
    fireEvent.click(await screen.findByLabelText('Sửa: Toi o Ha Noi'))
    expect(screen.getByLabelText('Lưu sửa: Toi o Ha Noi')).toBeTruthy()
    expect(screen.getByLabelText('Thôi sửa: Toi o Ha Noi')).toBeTruthy()
  })
})

describe('pham vi hien thanh cau, khong hien ma', () => {
  it.each(['nguoi_dung', 'du_an', 'hoi_thoai'] as const)('%s', async (pv) => {
    const api = apiGia({
      ghiNhoLietKe: vi.fn().mockResolvedValue({
        ghi_nho: [M({ pham_vi: pv, muc_tieu_id: pv === 'nguoi_dung' ? '' : 'x' })],
        tran_moi_pham_vi: 2000, tran_mot_ban: 500,
      }),
    })
    const { container } = ve(api)
    await waitFor(() => expect(container.textContent).toContain('Toi lam ke toan'))
    expect(container.textContent).not.toContain(pv)
  })
})

describe('tran hien TRUOC khi go', () => {
  it('hien so ky tu da dung tren tong', async () => {
    // Mot nguoi go xong mot mau roi moi biet kho day la mot nguoi vua mat cong.
    const api = apiGia({
      ghiNhoLietKe: vi.fn().mockResolvedValue({
        ghi_nho: [M({ noi_dung: 'x'.repeat(120) })],
        tran_moi_pham_vi: 2000, tran_mot_ban: 500,
      }),
    })
    const { container } = ve(api)
    await waitFor(() => expect(container.textContent).toContain('120/2000'))
  })

  it('o nhap chan o TRAN MOT BAN cua may chu, khong o mot hang so cua giao dien', async () => {
    const api = apiGia({
      ghiNhoLietKe: vi.fn().mockResolvedValue({
        ghi_nho: [], tran_moi_pham_vi: 2000, tran_mot_ban: 321,
      }),
    })
    ve(api)
    const o = await screen.findByLabelText('Dặn máy nhớ một điều')
    await waitFor(() => expect(o.getAttribute('maxlength')).toBe('321'))
  })
})

describe('su vang mat phai noi ra', () => {
  it('LOI khong duoc trong giong KHONG CO GI', async () => {
    const api = apiGia({
      ghiNhoLietKe: vi.fn().mockRejectedValue(new LoiApi('http_500', 'May chu hong', 500)),
    })
    const { container } = ve(api)
    await waitFor(() => expect(container.textContent).toContain('May chu hong'))
    expect(container.textContent).not.toContain('Máy chưa nhớ gì về bạn')
  })

  it('kho RONG that thi noi la rong, va moi ai do dan', async () => {
    const { container } = ve(apiGia())
    await waitFor(() => expect(container.textContent).toContain('Máy chưa nhớ gì về bạn'))
  })
})

describe('them', () => {
  it('trung => noi mot cau, KHONG bao loi do', async () => {
    // `bo_qua` la chuyen binh thuong: day lai may mot dieu no da biet.
    const api = apiGia({
      ghiNhoThem: vi.fn().mockResolvedValue({ ghi_nho: M({}), trang_thai: 'bo_qua' }),
    })
    const { container } = ve(api)
    const o = await screen.findByLabelText('Dặn máy nhớ một điều')
    fireEvent.change(o, { target: { value: 'Toi lam ke toan' } })
    fireEvent.submit(o.closest('form')!)
    await waitFor(() => expect(container.textContent).toContain('đã nhớ điều này rồi'))
  })

  it('KhoDay (409) hien ra, khong nuot', async () => {
    const api = apiGia({
      ghiNhoThem: vi.fn().mockRejectedValue(
        new LoiApi('kho_day', 'Kho da day, xoa bot di', 409)),
    })
    const { container } = ve(api)
    const o = await screen.findByLabelText('Dặn máy nhớ một điều')
    fireEvent.change(o, { target: { value: 'them mot mau' } })
    fireEvent.submit(o.closest('form')!)
    await waitFor(() => expect(container.textContent).toContain('Kho da day'))
  })

  it('o rong thi nut Luu bi vo hieu', async () => {
    ve(apiGia())
    await screen.findByLabelText('Dặn máy nhớ một điều')
    expect((screen.getByText('Lưu') as HTMLButtonElement).disabled).toBe(true)
  })
})

describe('xoa', () => {
  it('nut xoa noi ro XOA CAI GI', async () => {
    // ⛔ Nam cai nut "Xoá" giong het nhau la nam cau "button" giong het nhau
    //    voi trinh doc man hinh.
    const api = apiGia({
      ghiNhoLietKe: vi.fn().mockResolvedValue({
        ghi_nho: [M({ id: 'gn_x', noi_dung: 'Toi o Ha Noi' })],
        tran_moi_pham_vi: 2000, tran_mot_ban: 500,
      }),
    })
    ve(api)
    fireEvent.click(await screen.findByLabelText('Xoá: Toi o Ha Noi'))
    await waitFor(() => expect(api.ghiNhoXoa).toHaveBeenCalledWith('gn_x'))
  })
})
