// Autocomplete trong o bieu thuc §6 (P2 Task 8).
//
// 🔑 VE DOI CHUNG. Bai "khong hien node ngoai" MOT MINH thi mot component tra
//    ve danh sach RONG cung xanh. Nen moi bai co ca hai ve: thu PHAI co, va
//    thu PHAI KHONG co — tren cung mot lan render.
//
// ⛔ Danh sach o day la thu MAY CHU tra (`platform_core/workflow/goi_y.py`,
//    `tests/test_1769`). Tep nay do rang component **chi ve lai** no, khong
//    them mot ten nao — vi them mot ten la them mot bieu thuc se bi tu choi
//    luc publish.
import { useState } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { dangGoBieuThuc, OBieuThuc } from '../src/inspector/OBieuThuc'
import { FormTuLuocDo } from '../src/inspector/FormTuLuocDo'
import type { GoiYBieuThuc } from '../src/workflowApi'

afterEach(cleanup)

// May chu da loai `nodes.d.*` (khong phai to tien) TRUOC khi gui — dung nhu
// `test_1769::test_goi_y_CO_node_to_tien_va_KHONG_co_node_ngoai` chot.
const GOI_Y: GoiYBieuThuc = {
  node_id: 'c',
  muc: [
    { duong: 'trigger', loai: 'goc', qua_publish: false },
    { duong: 'vars', loai: 'goc', qua_publish: false },
    { duong: 'nodes.a.output.text', loai: 'cong', node: 'a', cong: 'text',
      node_type: 'app.text.chat', qua_publish: true },
    { duong: 'nodes.b.output.image_keys', loai: 'cong', node: 'b',
      cong: 'image_keys', node_type: 'app.image.generate', qua_publish: true },
    { duong: 'nodes.a.status', loai: 'mat_node', node: 'a',
      node_type: 'app.text.chat', qua_publish: false },
  ],
  ham: [
    { ten: 'upper', nhom: 'chuoi', chu_ky: 'upper(chuoi)', qua_publish: false },
    { ten: 'lower', nhom: 'chuoi', chu_ky: 'lower(chuoi)', qua_publish: false },
  ],
  loi: null,
}

function goTrong(o: HTMLElement, v: string) {
  fireEvent.change(o, { target: { value: v, selectionStart: v.length } })
}

describe('dangGoBieuThuc', () => {
  it('mo khi con tro nam sau mot `{{` chua dong', () => {
    expect(dangGoBieuThuc('Xin {{ nod', 10)).toEqual({ batDau: 6, tu: 'nod' })
  })
  it('KHONG mo khi bieu thuc da dong', () => {
    expect(dangGoBieuThuc('{{ a }} xin', 11)).toBeNull()
  })
  it('KHONG mo sau `\\{{` — spec §6.1 goi do la chu thuong', () => {
    expect(dangGoBieuThuc('\\{{ no', 6)).toBeNull()
  })
  it('KHONG mo khi chua go `{{`', () => {
    expect(dangGoBieuThuc('xin chao', 8)).toBeNull()
  })
})

// ⚠️ O nay la o CO DIEU KHIEN: gia tri do cha giu. Mot ban test render no voi
//    `gia=''` co dinh thi cai o KHONG BAO GIO nhan lai thu vua go — va phep
//    "chen vao cho dang go" se do vi bo do, khong vi san pham.
function Bao({ bat }: { bat: (v: string) => void }) {
  const [gia, setGia] = useState('')
  return <OBieuThuc id="prompt" gia={gia} goiY={GOI_Y}
    onChange={v => { setGia(v); bat(v) }} />
}

describe('OBieuThuc', () => {
  const ve = (onChange: (v: string) => void = vi.fn()) => {
    render(<Bao bat={onChange} />)
    return screen.getByRole('combobox')
  }

  it('chua go `{{` thi KHONG co hop goi y nao', () => {
    const o = ve()
    goTrong(o, 'xin chao')
    expect(screen.queryByRole('listbox')).toBeNull()
  })

  it('go `{{` thi hien goi y CUA MAY CHU — ca node lan ham', () => {
    const o = ve()
    goTrong(o, '{{ ')
    const muc = screen.getAllByRole('option').map(e => e.textContent)
    expect(muc.some(t => t?.includes('nodes.a.output.text'))).toBe(true)
    expect(muc.some(t => t?.includes('upper'))).toBe(true)
    // ⭐ VE DOI CHUNG: khong mot ten nao ngoai danh sach may chu gui.
    expect(muc.some(t => t?.includes('nodes.d'))).toBe(false)
    expect(muc.some(t => t?.includes('slugify'))).toBe(false)
  })

  it('loc theo chu dang go, va van giu ca hai ve', () => {
    const o = ve()
    goTrong(o, '{{ nodes.a')
    const muc = screen.getAllByRole('option').map(e => e.textContent ?? '')
    expect(muc.some(t => t.includes('nodes.a.output.text'))).toBe(true)
    expect(muc.some(t => t.includes('nodes.b'))).toBe(false)
    expect(muc.some(t => t.includes('upper'))).toBe(false)
  })

  it('bam mot goi y thi CHEN vao o, khong thay ca chuoi', () => {
    const bat = vi.fn()
    const o = ve(bat)
    goTrong(o, 'Xin {{ nodes.a')
    fireEvent.mouseDown(screen.getByText('nodes.a.output.text'))
    expect(bat).toHaveBeenLastCalledWith('Xin {{ nodes.a.output.text')
  })

  it('phim mui ten + Enter chon duoc, Escape dong hop', () => {
    const bat = vi.fn()
    const o = ve(bat)
    goTrong(o, '{{ nodes')
    fireEvent.keyDown(o, { key: 'ArrowDown' })
    fireEvent.keyDown(o, { key: 'Enter' })
    expect(bat).toHaveBeenLastCalledWith('{{ nodes.b.output.image_keys')
    goTrong(o, '{{ nodes')
    fireEvent.keyDown(o, { key: 'Escape' })
    expect(screen.queryByRole('listbox')).toBeNull()
  })

  it('muc chua qua duoc cong publish ĐUOC HIEN nhung co dau canh bao', () => {
    const o = ve()
    goTrong(o, '{{ ')
    const tuy = screen.getAllByRole('option')
    const trigger = tuy.find(e => e.textContent?.startsWith('trigger'))!
    expect(trigger.className).toContain('chua-publish-duoc')
    const cong = tuy.find(e => e.textContent?.startsWith('nodes.a.output.text'))!
    expect(cong.className).not.toContain('chua-publish-duoc')
  })

  it('khong co goi y (may chu hong) thi KHONG bia danh sach nao', () => {
    render(<OBieuThuc id="p2" gia="" onChange={vi.fn()} />)
    goTrong(screen.getByRole('combobox'), '{{ ')
    expect(screen.queryByRole('listbox')).toBeNull()
  })
})

describe('FormTuLuocDo noi voi o bieu thuc', () => {
  const luocDo = { type: 'object' as const, required: ['prompt'], properties: {
    prompt: { type: 'string' as const },
    count: { type: 'integer' as const },
  } }

  it('o CHU la o bieu thuc: go `{{` ra goi y', () => {
    render(<FormTuLuocDo luocDo={luocDo} giaTri={{}} goiY={GOI_Y}
      onChange={vi.fn()} />)
    goTrong(screen.getByLabelText('prompt *'), '{{ nodes')
    expect(screen.getAllByRole('option').length).toBeGreaterThan(0)
  })

  // ⚠️ Cong tac `{{ }}` cua o SO (phase 2) phai con nguyen: o so CHUA mo cong
  //    tac van la `type=number`, va hop goi y khong duoc che no.
  it('o SO giu cong tac `{{ }}`, mo ra moi thanh o bieu thuc', () => {
    render(<FormTuLuocDo luocDo={luocDo} giaTri={{ count: 2 }} goiY={GOI_Y}
      onChange={vi.fn()} />)
    expect(screen.getByLabelText('count')).toHaveAttribute('type', 'number')
    fireEvent.click(screen.getByRole('button', { name: 'Dùng biểu thức cho count' }))
    const o = screen.getByLabelText('count')
    expect(o).toHaveAttribute('type', 'text')
    goTrong(o, '{{ nodes')
    expect(screen.getAllByRole('option').length).toBeGreaterThan(0)
  })
})
