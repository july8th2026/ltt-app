/**
 * BangNghienCuu — bao cao co trich dan, va PHAM VI noi ra. (H44 B6 b5+b6)
 *
 * ## Menh de quan trong nhat khong phai "no ve dung"
 *
 * §1 cua ke hoach: nen tang nay KHONG co kha nang tim web. Mot san pham ten la
 * *"nghien cuu"* im lang ve dieu do la mot loi hua hong. Nen phep kiem dau tien
 * o day chot rang cau pham vi **co mat truoc khi khach go cau hoi**, khong phai
 * duoi ket qua — mot canh bao doc SAU khi da tin la mot canh bao khong con tac
 * dung.
 *
 * ## Va `so_bi_loai` phai hien
 *
 * No la thuoc do do tin cua chinh luot nay. 8 cau bi loai tren 10 nghia la model
 * dang bia; giau con so do la giau dung thu khach can de biet nen tin bao nhieu.
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { BangNghienCuu } from '../src/BangNghienCuu'
import type { BaoCaoNghienCuu, BaoGiaNghienCuu } from '../src/kieu'

const PHAM_VI = 'Đọc tài liệu bạn đã đính vào hội thoại này. Không tìm trên Internet.'

const BG: BaoGiaNghienCuu = {
  uoc_credit: 13, tran_vong: 3, tran_vong_toi_da: 3,
  so_du: 100, du_credit: true, pham_vi: PHAM_VI,
  phien_ban_gia: 'nghien-cuu-v0-tam',
}

const BC: BaoCaoNghienCuu = {
  cau_hoi: 'dieu khoan thanh toan',
  ly_do_dung: 'xong', so_vong: 2, so_bi_loai: 0,
  khang_dinh: [{
    chu: 'Thoi han thanh toan la 30 ngay',
    nguon: [{ tep_id: 'tep12345678', doan_id: 'd1', trang: 3 }],
  }],
  nguon: [{ loai: 'doan_tai_lieu', trich_dan: { tep_id: 'tep12345678', doan_id: 'd1', trang: 3 } }],
  phien_ban_gia: 'nghien-cuu-v0-tam',
}

function apiGia(o: Partial<{
  bg: BaoGiaNghienCuu | Error
  xem: { job_id?: string; trang_thai: string; pham_vi: string
          bao_cao?: BaoCaoNghienCuu; ly_do?: string }
}> = {}) {
  return {
    nghienCuuBaoGia: vi.fn(() => (o.bg instanceof Error
      ? Promise.reject(o.bg) : Promise.resolve(o.bg ?? BG))),
    nghienCuuChay: vi.fn(() => Promise.resolve(
      { job_id: 'jb1', tran_vong: 3, pham_vi: PHAM_VI })),
    nghienCuuXem: vi.fn(() => Promise.resolve(
      o.xem ?? { job_id: 'jb1', trang_thai: 'done', pham_vi: PHAM_VI, bao_cao: BC })),
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  } as any
}

function ve(api: unknown) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return render(<BangNghienCuu api={api as any} convId="c1" onDong={() => {}} />)
}

/**
 * Go mot cau hoi roi bam.
 *
 * ⚠️ `fireEvent.change` chu KHONG `el.value = ...` + `dispatchEvent`. React
 *    vá setter cua `HTMLTextAreaElement.value`, nen gan thang bi no nuot va
 *    `onChange` khong bao gio chay — nut o mai trang thai `disabled`, va phep
 *    kiem do o mot cho khong lien quan gi den menh de no dinh do.
 */
async function hoi(chu = 'dieu khoan') {
  fireEvent.change(screen.getByRole('textbox'), { target: { value: chu } })
  const nut = screen.getByRole('button', { name: 'Nghiên cứu' }) as HTMLButtonElement
  await waitFor(() => expect(nut.disabled).toBe(false))
  fireEvent.click(nut)
}

// ── 1. PHAM VI (buoc 6) ────────────────────────────────────────────────────

describe('pham vi', () => {
  it('hien cau pham vi NGAY khi mo, truoc khi co ket qua nao', async () => {
    ve(apiGia())
    expect(await screen.findByText(PHAM_VI)).toBeTruthy()
    // Chua chay gi ca: khong co bao cao tren man hinh.
    expect(screen.queryByText(/30 ngay/)).toBeNull()
  })

  it('cau pham vi dung TRUOC o nhap trong DOM', async () => {
    const { container } = ve(apiGia())
    await screen.findByText(PHAM_VI)
    const pv = container.querySelector('.ltc-nc__phamvi')!
    const o = container.querySelector('textarea')!
    // `compareDocumentPosition` = 4 nghia la `o` di SAU `pv`.
    expect(pv.compareDocumentPosition(o) & Node.DOCUMENT_POSITION_FOLLOWING)
      .toBeTruthy()
  })

  it('pham vi lay TU MAY CHU, khong phai hang so trong bundle', async () => {
    // ⛔ Mot ban sao trong bundle se troi ve phia NGUY HIEM: bundle cu noi
    //    "khong tim Internet" trong khi may chu da mo `web.tim`.
    const khac = 'Doc tai lieu cua ban VA tim tren Internet.'
    ve(apiGia({ bg: { ...BG, pham_vi: khac } }))
    expect(await screen.findByText(khac)).toBeTruthy()
    expect(screen.queryByText(PHAM_VI)).toBeNull()
  })
})

// ── 2. Bao cao ─────────────────────────────────────────────────────────────

describe('bao cao', () => {
  it('moi khang dinh hien kem TRICH DAN', async () => {
    ve(apiGia())
    await screen.findByText(PHAM_VI)
    await hoi()
    expect(await screen.findByText(/30 ngay/, {}, { timeout: 5000 })).toBeTruthy()
    expect(screen.getByText(/trang 3/)).toBeTruthy()
  })

  it('trang = 0 KHONG hien "trang 0"', async () => {
    // ⛔ `0` la KHONG BIET (tep khong co khai niem trang), khong phai trang dau.
    const bc: BaoCaoNghienCuu = {
      ...BC,
      khang_dinh: [{ chu: 'Cau tu mot tep .txt',
                     nguon: [{ tep_id: 'tepabc123', doan_id: 'd9', trang: 0 }] }],
    }
    const { container } = ve(apiGia({
      xem: { trang_thai: 'done', pham_vi: PHAM_VI, bao_cao: bc },
    }))
    await screen.findByText(PHAM_VI)
    await hoi()
    await screen.findByText(/tep .txt/, {}, { timeout: 5000 })
    expect(container.textContent).not.toContain('trang 0')
  })

  it('so cau BI LOAI hien ra, khong bi giau', async () => {
    // 🔴 8/10 bi loai nghia la model dang bia. Do la thuoc do do tin cua luot
    //    nay, khong phai mot chi tiet ky thuat.
    const bc: BaoCaoNghienCuu = { ...BC, so_bi_loai: 8 }
    ve(apiGia({ xem: { trang_thai: 'done', pham_vi: PHAM_VI, bao_cao: bc } }))
    await screen.findByText(PHAM_VI)
    await hoi()
    expect(await screen.findByText(/bỏ 8 câu/, {}, { timeout: 5000 })).toBeTruthy()
  })

  it('cham tran thi NOI RA, khong cat im lang', async () => {
    const bc: BaoCaoNghienCuu = { ...BC, ly_do_dung: 'tran_vong' }
    ve(apiGia({ xem: { trang_thai: 'done', pham_vi: PHAM_VI, bao_cao: bc } }))
    await screen.findByText(PHAM_VI)
    await hoi()
    expect(await screen.findByText(/còn tài liệu chưa đọc/, {}, { timeout: 5000 }))
      .toBeTruthy()
  })

  it('bao cao RONG noi ro phai lam gi, khong chi noi "khong co"', async () => {
    const bc: BaoCaoNghienCuu = {
      ...BC, khang_dinh: [], ly_do_dung: 'khong_co_nguon', nguon: [],
    }
    ve(apiGia({ xem: { trang_thai: 'done', pham_vi: PHAM_VI, bao_cao: bc } }))
    await screen.findByText(PHAM_VI)
    await hoi()
    expect(await screen.findByText(/đính thêm tài liệu/, {}, { timeout: 5000 }))
      .toBeTruthy()
  })
})

// ── 3. Hong thi NOI RA ─────────────────────────────────────────────────────

describe('hong', () => {
  it('job failed hien LY DO, khong quay mai', async () => {
    ve(apiGia({
      xem: { job_id: 'jb1', trang_thai: 'failed', pham_vi: PHAM_VI,
             ly_do: 'model khong tra loi duoc' },
    }))
    await screen.findByText(PHAM_VI)
    await hoi()
    const bao = await screen.findByRole('alert', {}, { timeout: 5000 })
    expect(bao.textContent).toContain('model khong tra loi duoc')
    // ⛔ Va nut phai bam lai duoc — khong ket o trang thai "dang chay" vinh vien.
    await waitFor(() => expect(
      (screen.getByRole('button', { name: 'Nghiên cứu' }) as HTMLButtonElement)
        .disabled).toBe(false))
  })

  it('bao gia hong KHONG lam mat o nhap', async () => {
    // ⭐ Khach van phai go duoc; chi la khong biet gia. Mot man hinh trang vi
    //    mot loi phu la mot man hinh khong dung duoc.
    ve(apiGia({ bg: new Error('mat mang') }))
    expect(await screen.findByRole('textbox')).toBeTruthy()
    expect((await screen.findByRole('alert')).textContent).toContain('mat mang')
  })

  it('khong du credit thi VO HIEU nut va noi ra', async () => {
    ve(apiGia({ bg: { ...BG, so_du: 2, du_credit: false } }))
    expect(await screen.findByText(/Chưa đủ để chạy/)).toBeTruthy()
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'x' } })
    await waitFor(() => expect(
      (screen.getByRole('button', { name: 'Nghiên cứu' }) as HTMLButtonElement)
        .disabled).toBe(true))
  })
})
