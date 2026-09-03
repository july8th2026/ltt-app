/**
 * Dong trang thai luot: pha suy tu SU KIEN THAT, va khung KHONG DOI kich thuoc.
 *
 * 🔴 Do 03/09 tren production: ba giay ruoi im lang, roi mot cu nhay bo cuc
 *    0,0749 khi khoi "Suy luan" moc ra. CLS ca luot = 0,1642 — vuot nguong
 *    "kem" (0,1) cua Google.
 */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { phaCua, TrangThaiLuot } from '../src/TrangThaiLuot'
import type { ThiHanh } from '../src/kieu'

function ex(g: Partial<ThiHanh> = {}): ThiHanh {
  return {
    id: 'ex1', status: 'streaming', mode: 'stream', tool_name: 'text.chat',
    partial_text: '', reasoning_text: '', finish_reason: '', usage: {},
    credit: { giu: 0, thu: 0, hoan: 0 }, error_code: '', error_text: '',
    job_id: null, seq: 0, ...g,
  }
}

describe('phaCua — suy tu thu DA CO, khong tu mot truong moi', () => {
  it('chua mot su kien nao ⇒ dang xep hang', () => {
    expect(phaCua(ex({ seq: 0 }), false)).toBe('xep_hang')
    expect(phaCua(null, false)).toBe('xep_hang')
  })

  it('`response.started` da toi ⇒ dang chuan bi', () => {
    expect(phaCua(ex({ seq: 3 }), false)).toBe('chuan_bi')
  })

  it('reasoning dang chay ⇒ dang suy nghi', () => {
    expect(phaCua(ex({ seq: 9, reasoning_text: 'hm...' }), false)).toBe('suy_nghi')
  })

  it('da co chu tra loi ⇒ dong nay het viec', () => {
    expect(phaCua(ex({ seq: 40, reasoning_text: 'x', partial_text: 'y' }), true)).toBe('')
  })
})

describe('TrangThaiLuot — khung khong bao gio doi kich thuoc', () => {
  /**
   * ⛔ An bang `visibility`, KHONG `display: none`. `display: none` tra lai
   *    chieu cao cho dong chay — tuc dung lai dung cai cu nhay ta vua tranh.
   *    Day la nguyen tac 3 cua LibreChat, va no la nguyen tac HINH HOC chu
   *    khong phai tham my.
   */
  it('khong co pha nao thi VAN ve khung, chi an di', () => {
    const { container } = render(
      <TrangThaiLuot ex={ex({ seq: 0 })} daCoChu dangChay={false} />,
    )
    const el = container.querySelector('.ltc-trangthai') as HTMLElement
    expect(el).toBeTruthy()
    expect(el.style.visibility).toBe('hidden')
    expect(el.style.display).not.toBe('none')
  })

  it('doc len cho trinh doc man hinh, va noi dung pha', () => {
    render(<TrangThaiLuot ex={ex({ seq: 5 })} daCoChu={false} dangChay />)
    const el = screen.getByRole('status')
    expect(el.getAttribute('aria-live')).toBe('polite')
    expect(el.textContent).toContain('Đang chuẩn bị')
  })

  it('pha suy nghi noi ro la dang suy nghi', () => {
    render(<TrangThaiLuot ex={ex({ seq: 9, reasoning_text: 'a' })} daCoChu={false} dangChay />)
    expect(screen.getByRole('status').textContent).toContain('Đang suy nghĩ')
  })

  it('khong bia ra pha nao ta khong co su kien cho no', () => {
    // "Dang tim tai lieu" nghe hay, nhung ChatLTT khong co buoc do. Bia mot
    // tien trinh khong ton tai thi ngay nao them RAG that se khong ai con tin
    // dong trang thai nay nua.
    const { container } = render(
      <TrangThaiLuot ex={ex({ seq: 5 })} daCoChu={false} dangChay />,
    )
    const chu = container.textContent || ''
    for (const bia of ['tài liệu', 'tìm kiếm', 'web', 'công cụ']) {
      expect(chu.toLowerCase()).not.toContain(bia)
    }
  })
})
