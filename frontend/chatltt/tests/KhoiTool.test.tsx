/**
 * KhoiTool — ve khoi `tool_call`. (H44 P09 buoc 4)
 *
 * ## Ba menh de, va menh de thu hai la ly do tep nay ton tai
 *
 * 1. Bon trang thai hien ra bon cau tieng Viet khac nhau.
 * 2. **`tom_tat` KHONG duoc do ra man hinh.** No viet cho MODEL doc: voi mot
 *    luot thanh cong no la JSON (`{"key": "a.png"}`). Ve no ra la dung thu
 *    `KhoiLa.test.tsx` goi la *"te hon vo"*, chi khac la JSON nam trong mot
 *    cai khung dep.
 * 3. Khoi CU (khong co `trang_thai`) van doc duoc — 220 hoi thoai that.
 */
import { fireEvent, render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { KhoiTool, cauLoi, nhanTool } from '../src/KhoiTool'
import type { KhoiToolCall } from '../src/kieu'

const K = (o: Partial<KhoiToolCall>): KhoiToolCall =>
  ({ type: 'tool_call', ten: 'noi_bo.tinh', ...o }) as KhoiToolCall

const chuCua = (o: Partial<KhoiToolCall>) =>
  render(<KhoiTool khoi={K(o)} />).container.textContent ?? ''

// ── 1. Bon trang thai ──────────────────────────────────────────────────────

describe('trang thai', () => {
  it('bon trang thai ra BON cau khac nhau', () => {
    const cau = (['cho_duyet', 'dang_chay', 'xong', 'loi'] as const)
      .map((t) => chuCua({ trang_thai: t }))
    expect(new Set(cau).size).toBe(4)
  })

  it.each(['cho_duyet', 'dang_chay', 'xong', 'loi'] as const)(
    '%s hien bang tieng Viet, khong hien ma tho', (t) => {
      const chu = chuCua({ trang_thai: t })
      expect(chu).not.toContain(t)
      expect(chu).toMatch(/[À-ỹ]/)
    })

  it('trang thai di ra DOM de CSS bat duoc', () => {
    const { container } = render(<KhoiTool khoi={K({ trang_thai: 'loi' })} />)
    expect(container.querySelector('[data-trang-thai="loi"]')).not.toBeNull()
  })
})

// ── 2. `tom_tat` khong ro ra ───────────────────────────────────────────────

describe('tom_tat viet cho MODEL, khong cho nguoi', () => {
  it('luot XONG khong do JSON ket qua ra man hinh', () => {
    const chu = chuCua({ trang_thai: 'xong', tom_tat: '{"key": "a.png"}' })
    expect(chu).not.toContain('key')
    expect(chu).not.toContain('a.png')
    expect(chu).not.toContain('{')
  })

  it('luot LOI hien PHAN CAU CHU, bo ma may', () => {
    const chu = chuCua({ trang_thai: 'loi',
      tom_tat: 'LOI[het_tien]: khong du credit' })
    expect(chu).toContain('khong du credit')
    expect(chu).not.toContain('het_tien')
    expect(chu).not.toContain('LOI[')
  })

  it('loi khong co cau chu van co mot cau, khong de trong', () => {
    expect(cauLoi('LOI[x]:')).toMatch(/[À-ỹ]/)
    expect(cauLoi('')).toMatch(/[À-ỹ]/)
  })
})

// ── 3. Doi so ──────────────────────────────────────────────────────────────

describe('doi so', () => {
  it('khoa CO nhan hien thanh nhan, khong hien ten khoa', () => {
    // `cho_duyet` => tu mo, nen than hien san.
    const chu = chuCua({ trang_thai: 'cho_duyet', doi_so: { bieu_thuc: '2+2' } })
    expect(chu).toContain('2+2')
    expect(chu).not.toContain('bieu_thuc')
  })

  it('khoa CHUA co nhan thi AN han, khong hien ten khoa', () => {
    const chu = chuCua({ trang_thai: 'cho_duyet',
      doi_so: { chua_ai_dat_nhan: 'gia tri bi mat' } })
    expect(chu).not.toContain('chua_ai_dat_nhan')
    expect(chu).not.toContain('gia tri bi mat')
  })

  it('gia tri la doi tuong KHONG bi JSON.stringify ra man hinh', () => {
    const chu = chuCua({ trang_thai: 'cho_duyet',
      doi_so: { noi_dung: { long: 'nested' } } })
    expect(chu).not.toContain('nested')
    expect(chu).not.toContain('[object Object]')
    expect(chu).not.toContain('{')
  })

  it('boolean hien thanh co/khong, khong hien true/false', () => {
    const chu = chuCua({ trang_thai: 'cho_duyet', doi_so: { lau_dai: true } })
    expect(chu).toContain('có')
    expect(chu).not.toContain('true')
  })
})

// ── 4. Gap / mo ────────────────────────────────────────────────────────────

describe('gap lai mac dinh, tu mo khi CON VIEC', () => {
  it('xong => gap lai: doi so KHONG co trong DOM', () => {
    const chu = chuCua({ trang_thai: 'xong', doi_so: { bieu_thuc: '2+2' } })
    expect(chu).not.toContain('2+2')
  })

  it('dang chay => tu mo', () => {
    const chu = chuCua({ trang_thai: 'dang_chay', doi_so: { bieu_thuc: '2+2' } })
    expect(chu).toContain('2+2')
  })

  it('bam thi mo ra duoc', () => {
    const { container, getByRole } = render(
      <KhoiTool khoi={K({ trang_thai: 'xong', doi_so: { bieu_thuc: '2+2' } })} />)
    expect(container.textContent).not.toContain('2+2')
    fireEvent.click(getByRole('button'))
    expect(container.textContent).toContain('2+2')
  })

  it('khong co gi de mo thi nut KHONG gia vo la mot nut', () => {
    // ⭐ `aria-expanded` tren mot nut khong mo duoc la mot loi noi doi voi
    //    trinh doc man hinh — no hua mot vung noi dung khong ton tai.
    const { getByRole } = render(<KhoiTool khoi={K({ trang_thai: 'xong' })} />)
    const nut = getByRole('button')
    expect(nut.getAttribute('aria-expanded')).toBeNull()
    expect((nut as HTMLButtonElement).disabled).toBe(true)
  })
})

// ── 5. Khoi CU (tuong thich nguoc) ─────────────────────────────────────────

describe('khoi CU khong co `trang_thai`', () => {
  it('ok=false => loi', () => {
    expect(chuCua({ ok: false, tom_tat: 'LOI[x]: hong roi' }))
      .toContain('hong roi')
  })

  it('cho_duyet=true => cho duyet', () => {
    const a = chuCua({ ok: true, cho_duyet: true })
    const b = chuCua({ trang_thai: 'cho_duyet' })
    expect(a).toBe(b)
  })

  it('ok=true => xong', () => {
    expect(chuCua({ ok: true })).toBe(chuCua({ trang_thai: 'xong' }))
  })

  it('`trang_thai` THANG khi co ca hai — no la nguon chan ly', () => {
    // Khoi moi mang ca hai; neu bo ve doc `ok` truoc thi mot buoc dang chay
    // (ok=true) se hien "Xong" — dung lo hong P09 vua bit o backend.
    expect(chuCua({ trang_thai: 'dang_chay', ok: true }))
      .toBe(chuCua({ trang_thai: 'dang_chay' }))
  })
})

// ── 6. Nhan ten tool ───────────────────────────────────────────────────────

describe('nhan ten tool', () => {
  it('ten da biet ra cau tieng Viet', () => {
    expect(nhanTool('noi_bo.tim_tai_lieu')).toMatch(/[À-ỹ]/)
  })

  it('ten CHUA biet khong lam lo tien to ky thuat', () => {
    // ⛔ `noi_bo.` / `image.` la manh cua he thong. Ngo ra phan sau dau cham.
    const n = nhanTool('noi_bo.mot_tool_moi')
    expect(n).not.toContain('noi_bo')
    expect(n).not.toContain('.')
    expect(n).toContain('mot tool moi')
  })

  it('khong co ten van co mot nhan, khong de trong', () => {
    expect(nhanTool('').length).toBeGreaterThan(0)
  })
})

// ── 7. Ten kha truy cap ────────────────────────────────────────────────────

describe('ten kha truy cap', () => {
  it('nut co aria-label ROI RAC giua ten va trang thai', () => {
    // 🔴 Do 06/09 tren trinh duyet that: hai `<span>` lien nhau khong co
    //    khoang trang, nen `button.textContent` la "Tinh toanDang cho ban
    //    duyet" — dinh lien. `gap` cua flexbox tach chung tren MAN HINH nhung
    //    khong tach trong CHUOI, nen loi nay khong nhin thay duoc.
    const { getByRole } = render(<KhoiTool khoi={K({ trang_thai: 'cho_duyet' })} />)
    const nhan = getByRole('button').getAttribute('aria-label') ?? ''
    expect(nhan).toContain('Tính toán')
    expect(nhan).toContain('Đang chờ bạn duyệt')
    expect(nhan).not.toContain('toánĐang')
  })

  it('doi so dung <dl>/<dt>/<dd>, khong phai hai <span> canh nhau', () => {
    // Trinh doc man hinh ngat giua `<dt>` va `<dd>`; hai `<span>` thi khong.
    const { container } = render(
      <KhoiTool khoi={K({ trang_thai: 'cho_duyet', doi_so: { bieu_thuc: '2+2' } })} />)
    expect(container.querySelector('dl dt')?.textContent).toBe('Phép tính')
    expect(container.querySelector('dl dd')?.textContent).toBe('2+2')
  })
})
