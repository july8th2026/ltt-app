/**
 * A5 — bo hien thi phai BO QUA khoi LA, khong duoc vo va khong duoc do JSON.
 *
 * ⚠️ VIET LAI 06/09 (H44 P09), va **khong phai** de noi long.
 *
 * Ban truoc dung `tool_call` lam vi du cho "khoi la". P09 ve khoi ay, nen
 * `tool_call` chuyen tu **chua ai dinh nghia** sang **da dinh nghia** — va ba
 * phep kiem kia van XANH trong khi menh de cua chung da doi nghia duoi chan.
 * Do la truong hop te nhat: mot phep kiem xanh dang do mot thu khac han ten no.
 *
 * ⇒ Luat da ghi: **menh de phai BAT BIEN voi tap hop**, va ban viet lai phai
 *   KHO xanh hon. Menh de dung khong phai *"`tool_call` khong hien"* ma:
 *
 *     Khoi CHUA AI DINH NGHIA  -> khong ve gi
 *     Khoi DA DINH NGHIA       -> ve ra CAU tieng Viet, khong bao gio khoa JSON
 *
 * Ve `tool_call` (nay la loai da biet) o `KhoiTool.test.tsx`.
 *
 * ⛔ Hai cach hong, va cach thu hai moi la cach that:
 *   1. Giao dien NEM va ca cuoc hoi thoai trang xoa.
 *   2. Giao dien "khoan dung" bang cach do nguyen khoi ra man hinh — khong vo,
 *      nhung te hon vo: no trong nhu san pham von the.
 */
import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ThongDiepView } from '../src/ThongDiepView'
import type { Khoi, ThongDiep } from '../src/kieu'

function tin(blocks: Khoi[]): ThongDiep {
  return {
    id: 'a1', parent_id: 'u1', role: 'assistant', blocks,
    status: 'done', model_alias: 'ltt-3.8', execution_id: null,
    created_at: '2026-09-05T00:00:02.000000+00:00',
  }
}

const KHONG = () => {}

function ve(blocks: Khoi[]) {
  return render(
    <ThongDiepView m={tin(blocks)} phang={[tin(blocks)]} onChuyenNhanh={KHONG}
      onTaoLai={KHONG} onSuaGuiLai={KHONG} />,
  )
}

// `as unknown as Khoi`: dung y. `LoaiKhoi` la union DONG, nen mot loai la
// khong bieu dien duoc bang kieu — va do chinh la tinh huong dang kiem.
const LA = (o: Record<string, unknown>) => o as unknown as Khoi

/**
 * ⭐ NHIEU loai la, khong mot. Mot phep kiem dung dung MOT ten chi chung minh
 *    bo ve bo qua **cai ten do**; ngay ai do them mot `switch` co nhanh
 *    `default: return <pre>{JSON.stringify(k)}</pre>` thi no van xanh neu ten
 *    ay tinh co bi bat rieng o tren.
 */
const LOAI_LA = ['chua_ai_nghi_ra', 'widget', 'citation_group', 'mcp_resource']

describe('A5 — khoi CHUA AI DINH NGHIA', () => {
  it('khoi la KHONG lam vo, chu quanh no van hien', () => {
    const { container } = ve([
      { type: 'text', text: 'truoc' },
      LA({ type: 'chua_ai_nghi_ra', payload: { a: 1 } }),
      { type: 'text', text: 'sau' },
    ])
    expect(container.textContent).toContain('truoc')
    expect(container.textContent).toContain('sau')
  })

  it.each(LOAI_LA)('loai la %s: khong ten, khong khoa, khong JSON ra man hinh', (loai) => {
    const { container } = ve([
      { type: 'text', text: 'ket qua la 4' },
      LA({ type: loai, doi_so: { bieu_thuc: '2+2' }, payload: { x: 1 } }),
    ])
    const chu = container.textContent ?? ''
    expect(chu).toContain('ket qua la 4')
    expect(chu).not.toContain(loai)
    expect(chu).not.toContain('bieu_thuc')
    expect(chu).not.toContain('payload')
    expect(chu).not.toContain('[object Object]')
  })

  it('tin CHI co khoi la van ve ra khung tin, khong ve rong hoac nem', () => {
    // Ca nay xay ra that: backend moi tra ve mot luot chi co khoi kieu moi,
    // chua co chu — giao dien cu phai chiu duoc.
    const { container } = ve([LA({ type: 'chua_ai_nghi_ra', payload: { a: 1 } })])
    expect(container.querySelector('.ltc-tin')).not.toBeNull()
    expect(container.textContent).not.toContain('chua_ai_nghi_ra')
  })

  it('khoi la KHONG chen the vao DOM', () => {
    const { container } = ve([
      LA({ type: 'chua_ai_nghi_ra', text: '<img src=x onerror="window.__xss=3">' }),
    ])
    expect(container.querySelector('img')).toBeNull()
    expect((window as unknown as Record<string, unknown>).__xss).toBeUndefined()
  })
})

describe('A5 — chieu NGUOC LAI: khoi DA DINH NGHIA phai duoc doc', () => {
  it('khoi status van duoc doc — bo qua la la, khong phai bo qua het', () => {
    // ⭐ Mot ban sua "an toan" bang cach chi ve `text` se xanh o moi phep tren
    //    va do o day — dung nhu no phai the.
    const { container } = ve([
      { type: 'text', text: 'toi da thu 8 vong' },
      { type: 'status', code: 'tran_vong' },
    ])
    expect(container.textContent).toContain('toi da thu 8 vong')
    expect(container.querySelector('.ltc-tin')).not.toBeNull()
  })

  it('khoi tool_call — nay la loai DA BIET — phai ve ra thu gi do', () => {
    // 🔴 Day la dong thay the cho ba phep kiem cu. Chung chot `tool_call`
    //    KHONG hien; menh de ay het dung tu P09, va neu khong co dong nay thi
    //    viec `tool_call` bi bo ve tro lai se **khong ai biet**.
    const { container } = ve([
      { type: 'tool_call', ten: 'noi_bo.tinh', doi_so: { bieu_thuc: '2+2' },
        trang_thai: 'xong' } as unknown as Khoi,
    ])
    expect(container.querySelector('.ltc-tool')).not.toBeNull()
  })

  it.each(['tran_vong', 'tran_tool', 'tran_trung', 'huy'])(
    'ly do ket %s hien thanh CAU TIENG VIET, khong hien ma tho',
    (ma) => {
      // 🔴 `NHAN_TRANG_THAI[ma] ?? ma` co nghia la mot ma THIEU NHAN se roi
      //    NGUYEN ra man hinh. No khong nem, khong do, nen khong ai bao loi —
      //    nguoi dung chi doc thay chu `tran_vong` giua cuoc tro chuyen.
      const { container } = ve([
        { type: 'text', text: 'xong phan lam duoc' },
        { type: 'status', code: ma },
      ])
      const chu = container.textContent ?? ''
      expect(chu).not.toContain(ma)
      // Co dau tieng Viet => la mot cau, khong phai mot ma.
      expect(chu).toMatch(/[À-ỹ]/)
    },
  )
})
