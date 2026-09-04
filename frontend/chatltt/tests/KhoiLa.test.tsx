/**
 * A5 — bo hien thi phai BO QUA khoi la, khong duoc vo va khong duoc do JSON.
 *
 * V3 them cac loai khoi moi (`tool_call`, va nhung loai chua ai nghi ra) vao
 * `chatltt_message.blocks`. Mot ban giao dien CU se nhan chung tu may chu ngay
 * khi backend deploy truoc frontend — thu tu do la thu tu binh thuong, khong
 * phai su co.
 *
 * ⛔ Hai cach hong, va cach thu hai moi la cach that:
 *
 *   1. Giao dien NEM va ca cuoc hoi thoai trang xoa.
 *   2. Giao dien "khoan dung" bang cach do nguyen khoi ra man hinh — nguoi dung
 *      thay `{"type":"tool_call","doi_so":{...}}` giua cau tra loi. Khong vo,
 *      nhung te hon vo: no trong nhu san pham von the.
 *
 * Nen phep kiem nay chot ca hai chieu: VE duoc phan hieu duoc, va KHONG ve gi
 * cho phan khong hieu.
 */
import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ThongDiepView } from '../src/ThongDiepView'
import type { Khoi, ThongDiep } from '../src/kieu'

function tin(blocks: Khoi[]): ThongDiep {
  return {
    id: 'a1', parent_id: 'u1', role: 'assistant', blocks,
    status: 'done', model_alias: 'ltt_llm', execution_id: null,
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

describe('A5 — khoi la', () => {
  it('khoi la KHONG lam vo, chu quanh no van hien', () => {
    const { container } = ve([
      { type: 'text', text: 'truoc' },
      LA({ type: 'tool_call', ten: 'noi_bo.tinh', doi_so: { bieu_thuc: '2+2' } }),
      { type: 'text', text: 'sau' },
    ])
    expect(container.textContent).toContain('truoc')
    expect(container.textContent).toContain('sau')
  })

  it('khoi la KHONG bi do ra man hinh duoi dang JSON', () => {
    const { container } = ve([
      { type: 'text', text: 'ket qua la 4' },
      LA({ type: 'tool_call', ten: 'noi_bo.tinh', doi_so: { bieu_thuc: '2+2' } }),
    ])
    const chu = container.textContent ?? ''
    expect(chu).not.toContain('tool_call')
    expect(chu).not.toContain('bieu_thuc')
    expect(chu).not.toContain('[object Object]')
  })

  it('tin CHI co khoi la van ve ra khung tin, khong ve rong hoac nem', () => {
    // Ca truong hop nay xay ra that: backend moi tra ve mot luot chi co tool,
    // chua co chu — giao dien cu phai chiu duoc.
    const { container } = ve([LA({ type: 'chua_ai_nghi_ra', payload: { a: 1 } })])
    expect(container.querySelector('.ltc-tin')).not.toBeNull()
    expect(container.textContent).not.toContain('chua_ai_nghi_ra')
  })

  it('khoi la KHONG chen the vao DOM', () => {
    const { container } = ve([
      LA({ type: 'tool_call', text: '<img src=x onerror="window.__xss=3">' }),
    ])
    expect(container.querySelector('img')).toBeNull()
    expect((window as unknown as Record<string, unknown>).__xss).toBeUndefined()
  })

  it('khoi QUEN thuoc (status) van duoc doc — bo qua la la, khong phai bo qua het', () => {
    // ⭐ Chieu nguoc lai. Mot ban sua "an toan" bang cach chi ve `text` se xanh
    //    o bon phep tren va do o day — dung nhu no phai the.
    const { container } = ve([
      { type: 'text', text: 'toi da thu 8 vong' },
      { type: 'status', code: 'tran_vong' },
    ])
    expect(container.textContent).toContain('toi da thu 8 vong')
    expect(container.querySelector('.ltc-tin')).not.toBeNull()
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
