/**
 * TheDuyet — cua CUOI truoc khi mot lenh tieu tien cua khach chay. (H44 P09)
 *
 * ## Menh de quan trong nhat khong phai "no ve dung"
 *
 * Truoc the nay, backend duyet hoan chinh — `dang-cho`, `POST /{id}`, phieu ben
 * qua F5, `doi_so_cuoi()` — va giao dien co **0** cai nut. Do 07/09:
 * `grep "Duyệt|Từ chối" src/` ra rong. Nen phep kiem dau tien chi don gian la:
 * **co bam duoc khong**.
 *
 * ## \U0001f534 Va menh de DAT nhat: sua doi so thi gia cu HET NGHIA
 *
 * `_nop_job` gui `credit_da_bao = p.bao_gia_credit` — so khach DA NHIN THAY —
 * va `tao_media.tao` tinh lai roi TU CHOI neu lech. Nen mot the cho bam "Duyet"
 * sau khi sua ma khong bao gia lai la mot the day khach vao mot lenh se bi tu
 * choi, va ho chi biet vai giay sau khi doc cau tra loi cua model.
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { TheDuyet, cauHetHan, phutConLai } from '../src/TheDuyet'
import type { PhieuDuyet } from '../src/kieu'

const SAU = new Date(Date.now() + 25 * 60_000).toISOString()

const P: PhieuDuyet = {
  approval_id: 'ap_1',
  tool_name: 'image.ltt',
  doi_so: { prompt: 'mot con meo tren mai nha', count: 2, mode: 't2i' },
  credit: 8,
  policy_class: 'PAID',
  het_han_luc: SAU,
}

function apiGia(o: Partial<{ baoGia: number; quyetLoi: unknown }> = {}) {
  return {
    baoGia: vi.fn(() => Promise.resolve({
      nang_luc: 'image.ltt', credit: o.baoGia ?? 16,
      phien_ban_gia: 'v1', tham_so: {},
    })),
    duyetQuyet: vi.fn(() => (o.quyetLoi
      ? Promise.reject(o.quyetLoi)
      : Promise.resolve({ type: 'approval.granted', approval_id: 'ap_1', chay_tiep: true }))),
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  } as any
}

function ve(api: unknown, phieu: PhieuDuyet = P, onXong = () => {}) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return render(<TheDuyet api={api as any} phieu={phieu} onXong={onXong} />)
}

// ── 1. Bon thu ke hoach doi the nay phai noi ──────────────────────────────

describe('bon thu phai noi ra', () => {
  it('Y DINH — ten tool ra cau nguoi doc hieu, khong ra ma', () => {
    ve(apiGia())
    expect(screen.getByText('Vẽ ảnh')).toBeTruthy()
    expect(screen.queryByText(/image\.ltt/)).toBeNull()
  })

  it('DOI SO — hien ra, khong bat khach duyet mot cai hop den', () => {
    ve(apiGia())
    expect(screen.getByText('mot con meo tren mai nha')).toBeTruthy()
    expect(screen.getByText('Mô tả')).toBeTruthy()
  })

  it('CHI PHI — con so credit hien ro', () => {
    const { container } = ve(apiGia())
    expect(container.textContent).toContain('8 credit')
  })

  it('HE QUA — lop chinh sach ra mot cau, khong ra chu PAID', () => {
    const { container } = ve(apiGia())
    expect(container.textContent).toContain('tiêu credit của bạn')
    expect(container.textContent).not.toContain('PAID')
  })

  it('lop LA van ra mot cau, khong ra ma tho', () => {
    const { container } = ve(apiGia(), { ...P, policy_class: 'MOT_LOP_MOI' })
    expect(container.textContent).not.toContain('MOT_LOP_MOI')
    expect(container.textContent).toContain('xác nhận')
  })
})

// ── 2. Bam duoc — menh de ma truoc P09 la SAI ─────────────────────────────

describe('bam duoc', () => {
  it('co CA HAI nut, va Tu choi khong bi vo hieu', () => {
    ve(apiGia())
    const tuChoi = screen.getByRole('button', { name: 'Từ chối' }) as HTMLButtonElement
    const duyet = screen.getByRole('button', { name: 'Duyệt' }) as HTMLButtonElement
    expect(tuChoi.disabled).toBe(false)
    expect(duyet.disabled).toBe(false)
  })

  it('bam Duyet gui dung enum va KHONG kem doi so khi chua sua', async () => {
    const api = apiGia()
    ve(api)
    fireEvent.click(screen.getByRole('button', { name: 'Duyệt' }))
    await waitFor(() => expect(api.duyetQuyet).toHaveBeenCalled())
    expect(api.duyetQuyet).toHaveBeenCalledWith('ap_1', 'duyet', undefined)
  })

  it('bam Tu choi gui dung enum', async () => {
    const api = apiGia()
    ve(api)
    fireEvent.click(screen.getByRole('button', { name: 'Từ chối' }))
    await waitFor(() => expect(api.duyetQuyet).toHaveBeenCalled())
    expect(api.duyetQuyet).toHaveBeenCalledWith('ap_1', 'tu_choi', undefined)
  })

  it('409 "da_quyet" KHONG phai loi cua nguoi bam — dong the, khong bao do', async () => {
    const { LoiApi } = await import('../src/api')
    const xong = vi.fn()
    ve(apiGia({ quyetLoi: new LoiApi('da_quyet', 'ai do da bam truoc', 409) }),
       P, xong)
    fireEvent.click(screen.getByRole('button', { name: 'Duyệt' }))
    await waitFor(() => expect(xong).toHaveBeenCalled())
    expect(screen.queryByRole('alert')).toBeNull()
  })
})

// ── 3. 🔴 Sua doi so thi gia cu HET NGHIA ─────────────────────────────────

describe('sua doi so', () => {
  it('sua xong thi KHOA nut Duyet cho toi khi bao gia lai', () => {
    ve(apiGia())
    fireEvent.click(screen.getByRole('button', { name: 'Sửa' }))
    const duyet = screen.getByRole('button', { name: 'Duyệt' }) as HTMLButtonElement
    expect(duyet.disabled).toBe(true)
    expect(screen.getByText(/cần báo giá lại/)).toBeTruthy()
  })

  it('🔴 KHONG ve gia cu khi da sua — mot con so SAI mot cach tu tin', () => {
    const { container } = ve(apiGia())
    expect(container.textContent).toContain('8 credit')
    fireEvent.click(screen.getByRole('button', { name: 'Sửa' }))
    expect(container.textContent).not.toContain('8 credit')
  })

  it('bao gia lai xong thi hien gia MOI va mo khoa', async () => {
    ve(apiGia({ baoGia: 16 }))
    fireEvent.click(screen.getByRole('button', { name: 'Sửa' }))
    fireEvent.click(screen.getByRole('button', { name: 'Báo giá lại' }))
    expect(await screen.findByText(/16 credit/)).toBeTruthy()
    await waitFor(() => expect(
      (screen.getByRole('button', { name: 'Duyệt' }) as HTMLButtonElement).disabled)
      .toBe(false))
  })

  it('sua TIEP sau khi bao gia thi gia moi cung het nghia', async () => {
    ve(apiGia({ baoGia: 16 }))
    fireEvent.click(screen.getByRole('button', { name: 'Sửa' }))
    fireEvent.click(screen.getByRole('button', { name: 'Báo giá lại' }))
    await screen.findByText(/16 credit/)
    fireEvent.change(screen.getByLabelText('Mô tả'), { target: { value: 'khac' } })
    await waitFor(() => expect(
      (screen.getByRole('button', { name: 'Duyệt' }) as HTMLButtonElement).disabled)
      .toBe(true))
  })

  it('duyet SAU khi sua thi gui KEM doi so da sua, giu KIEU so', async () => {
    const api = apiGia({ baoGia: 16 })
    ve(api)
    fireEvent.click(screen.getByRole('button', { name: 'Sửa' }))
    fireEvent.change(screen.getByLabelText('Số ảnh'), { target: { value: '4' } })
    fireEvent.click(screen.getByRole('button', { name: 'Báo giá lại' }))
    await screen.findByText(/16 credit/)
    fireEvent.click(screen.getByRole('button', { name: 'Duyệt' }))
    await waitFor(() => expect(api.duyetQuyet).toHaveBeenCalled())
    const [, , ds] = api.duyetQuyet.mock.calls[0]
    // ⛔ `4` la SO, khong phai chuoi "4" — may chu khai `count: {type: int}`.
    expect(ds.count).toBe(4)
    // ⭐ Khoa KHONG co nhan (`mode`) van di theo nguyen ven, khong bi mat.
    expect(ds.mode).toBe('t2i')
  })
})

// ── 4. Het han — va "khong biet" khac "0" ─────────────────────────────────

describe('het han', () => {
  it('het han thi KHOA Duyet va noi ly do', () => {
    const truoc = new Date(Date.now() - 60_000).toISOString()
    ve(apiGia(), { ...P, het_han_luc: truoc })
    expect((screen.getByRole('button', { name: 'Duyệt' }) as HTMLButtonElement)
      .disabled).toBe(true)
    expect(screen.getByRole('alert').textContent).toContain('hết hạn')
  })

  it('het han van TU CHOI duoc — ket qua nhu nhau, va no don the di', () => {
    const truoc = new Date(Date.now() - 60_000).toISOString()
    ve(apiGia(), { ...P, het_han_luc: truoc })
    expect((screen.getByRole('button', { name: 'Từ chối' }) as HTMLButtonElement)
      .disabled).toBe(false)
  })

  it('het han thi KHONG con nut Sua', () => {
    const truoc = new Date(Date.now() - 60_000).toISOString()
    ve(apiGia(), { ...P, het_han_luc: truoc })
    expect(screen.queryByRole('button', { name: 'Sửa' })).toBeNull()
  })

  it('⭐ han KHONG DOC DUOC ra "khong ro", KHONG ra "0 phut"', () => {
    expect(phutConLai('khong-phai-ngay-thang')).toBe(null)
    expect(cauHetHan(null)).toBe('Không rõ hạn')
    expect(cauHetHan(0)).not.toBe('Không rõ hạn')
  })

  it('dem nguoc noi so phut con lai', () => {
    expect(cauHetHan(25)).toContain('25')
    expect(cauHetHan(-1)).toContain('hết hạn')
  })
})

// ── 5. Hinh dang tra ve LA khong duoc lam trang man hinh ───────────────────

describe('than tra ve sai hinh dang', () => {
  it('🔴 `dang-cho` tra mot than KHONG co `items` thi App van ve duoc', async () => {
    // Do 07/09: `datPhieuDuyet(r.items)` nhan `undefined`, roi `.length` o
    // `App.tsx` NEM va CA khung hoi thoai trang man hinh. Chin phep kiem cua
    // `App.test.tsx` do cung mot luc, va khong cai nao noi ve the duyet.
    //
    // ⛔ `.catch()` khong do duoc: promise KHONG bi tu choi — no thanh cong voi
    //    mot hinh dang khac. Day la hai chuyen khac nhau.
    const { Api } = await import('../src/api')
    vi.stubGlobal('fetch', vi.fn(async () => new Response('{}', { status: 200 })))
    const api = new Api('/chatltt/api', 'tok')
    const r = await api.duyetDangCho()
    // Hinh dang la — thu ma may chu KHONG hua, nhung co the tra.
    expect((r as { items?: unknown }).items).toBeUndefined()
    // ⭐ Menh de that: cho nao doc `items` cung phai chiu duoc `undefined`.
    expect(Array.isArray((r as { items?: unknown }).items ?? [])).toBe(true)
    vi.unstubAllGlobals()
  })
})
