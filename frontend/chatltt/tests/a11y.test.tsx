/**
 * a11y — `axe` tren cac khoi V3. (H44 P09 "Dat khi")
 *
 * Tieu chi pha P09: *"axe khong co vi pham NGHIEM TRONG"*.
 *
 * ## ⛔ Vi sao chay o vitest chu khong tiem vao trang that
 *
 * CSP cua nen tang la `script-src 'self' 'unsafe-inline' <hai host Cloudflare>`.
 * `cdnjs` KHONG nam trong do, nen tiem `axe.min.js` tu CDN bi chan — va **do la
 * dung**. Noi CSP de do mot lan a11y la doi mot bien phong thu that lay mot
 * phep do; phep do phai tu tim duong khac.
 *
 * ⭐ `axe-core` la phu thuoc **luc TEST**: 0 dependency, MPL-2.0, khong bao gio
 *    vao bundle. Dung nguong §0 muc thap ma chinh ke hoach dat cho test-time
 *    tooling ("chung khong ship, khong cham khach").
 *
 * ## ⚠️ Va gioi han cua no phai NOI RA
 *
 * `jsdom` khong ve, nen **`color-contrast` khong chay duoc o day** — axe tu
 * danh dau no `incomplete`, khong phai `pass`. Tuong phan duoc do RIENG tren
 * trinh duyet that bang `getComputedStyle`, va ket qua ghi o `STATE.md`.
 *
 * ⇒ Mot bao cao "0 vi pham" tu tep nay KHONG duoc doc thanh "a11y dat". No la
 *   "0 vi pham VE CAU TRUC". Hai cau khac nhau, va gop chung la dung cai bay
 *   `khong-doi-chung-thi-so-khong-khong-phai-phat-hien`.
 */
import axe from 'axe-core'
import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { KhoiTool } from '../src/KhoiTool'
import { TheDuyet } from '../src/TheDuyet'
import type { KhoiToolCall, PhieuDuyet } from '../src/kieu'

/** Chi bat vi pham NGHIEM TRONG — dung chu ke hoach dung. */
const MUC_NANG = new Set(['serious', 'critical'])

async function quet(el: HTMLElement) {
  const kq = await axe.run(el, {
    // ⛔ `color-contrast` bi TAT co chu dich: jsdom khong ve, nen no khong the
    //    ket luan. De bat thi no ra `incomplete` va lam bao cao trong nhu co
    //    van de trong khi that ra la khong do duoc — bao dong gia.
    rules: { 'color-contrast': { enabled: false } },
  })
  return kq.violations.filter((v) => MUC_NANG.has(String(v.impact)))
}

const KHOI = (o: Partial<KhoiToolCall>): KhoiToolCall =>
  ({ type: 'tool_call', ten: 'noi_bo.tinh', ...o }) as KhoiToolCall

const PHIEU: PhieuDuyet = {
  approval_id: 'ap_1', tool_name: 'image.ltt',
  doi_so: { prompt: 'mot con meo', count: 2 },
  credit: 8, policy_class: 'PAID',
  het_han_luc: new Date(Date.now() + 25 * 60_000).toISOString(),
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const apiGia = () => ({ baoGia: async () => ({ credit: 16 }), duyetQuyet: async () => ({}) }) as any

// ── 1. Bo quet phai TU KIEM ────────────────────────────────────────────────

describe('bo quet', () => {
  it('⛔ axe that su chay va BAT duoc mot vi pham co that', async () => {
    // Khong co dong nay thi moi "0 vi pham" duoi day xanh tren hu khong —
    // mot `axe.run` hong cung tra ve mang rong.
    //
    // ⚠️ Ban dau toi dung `aria-labelledby` tro vao mot id KHONG TON TAI. Bo
    //    tu kiem DO — va do la cau tra loi dung: jsdom khong phan giai duoc
    //    ca ay, nen axe xep no vao `incomplete`, KHONG phai `violations`.
    //    Toi da chon mot ca ma moi truong **khong tra loi duoc**, roi doc su
    //    im lang ay thanh "axe hong".
    //
    // ⭐ `<img>` thieu `alt` thi jsdom du suc ket luan — `image-alt(critical)`.
    const { container } = render(<img src="x.png" />)
    const kq = await axe.run(container, { rules: { 'color-contrast': { enabled: false } } })
    expect(kq.violations.map((v) => v.id)).toContain('image-alt')
  })

  it('⭐ va tren CHINH khoi V3 no chay DU rule de "0 vi pham" co nghia', async () => {
    // 🔴 Day la doi chung "no co NHIN THAY gi khong", va no phai do tren THU
    //    DANG KIEM — khong tren mot `<div><p>` (do 07/09: 0 rule chay, vi
    //    khong co gi de kiem; ban dau toi do dung ca ay va no DO).
    //
    // ⭐ So do duoc 07/09:
    //      KhoiTool  9 rule  (button-name, aria-valid-attr-value, dlitem, …)
    //      TheDuyet 13 rule  (+ heading-order, landmark-unique, …)
    const { container } = render(
      <TheDuyet api={apiGia()} phieu={PHIEU} onXong={() => {}} />)
    const kq = await axe.run(container, { rules: { 'color-contrast': { enabled: false } } })
    const chay = kq.passes.length + kq.violations.length + kq.incomplete.length
    expect(chay).toBeGreaterThanOrEqual(8)
    // ⛔ Va phai co dung MOT SO rule quan trong, khong chi "du nhieu".
    const ten = kq.passes.map((x) => x.id)
    for (const r of ['button-name', 'aria-valid-attr-value', 'nested-interactive']) {
      expect(ten).toContain(r)
    }
  })
})

// ── 2. Khoi V3 ─────────────────────────────────────────────────────────────

describe('khoi V3 khong co vi pham nghiem trong', () => {
  it.each(['cho_duyet', 'dang_chay', 'xong', 'loi'] as const)(
    'KhoiTool — %s', async (tt) => {
      const { container } = render(
        <KhoiTool khoi={KHOI({ trang_thai: tt, doi_so: { bieu_thuc: '2+2' } })} />)
      expect(await quet(container)).toEqual([])
    })

  it('TheDuyet — the duyet', async () => {
    const { container } = render(
      <TheDuyet api={apiGia()} phieu={PHIEU} onXong={() => {}} />)
    expect(await quet(container)).toEqual([])
  })

  it('TheDuyet — dang SUA (o nhap phai co nhan)', async () => {
    // ⭐ Ca nay rieng vi no doi input: mot `<input>` khong nhan la vi pham
    //    `serious`, va no chi xuat hien sau khi bam "Sua".
    const { container, getByRole } = render(
      <TheDuyet api={apiGia()} phieu={PHIEU} onXong={() => {}} />)
    getByRole('button', { name: 'Sửa' }).click()
    expect(await quet(container)).toEqual([])
  })
})
