import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { useState } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { FormTuLuocDo } from '../src/inspector/FormTuLuocDo'
import type { LuocDo } from '../src/nodeDefinition'

afterEach(cleanup)

// Hinh dang lay tu `platform_core/workflow/luoc_do.py` THAT (`sang_json_schema`),
// khong lay tu tri nho: `additionalProperties: false` co that trong JSON tra ve,
// `x-ltt-dong.nguon` la `app_property` (marker gui client), va mot `enum` RONG
// la mot gia tri hop le nghia la *"ban chua co lua chon nao"*.
const luocDo: LuocDo = {
  type: 'object',
  required: ['prompt'],
  additionalProperties: false,
  properties: {
    prompt: { type: 'string', maxLength: 4000 },
    ghi_chu: { type: 'string', 'x-ltt-control': 'textarea' },
    count: { type: 'integer', minimum: 1, maximum: 4, default: 1 },
    temperature: { type: 'number', minimum: 0, maximum: 2 },
    preview: { type: 'boolean', default: false },
    target_height: { type: 'integer', enum: [1080, 2160], default: 1080 },
    model: { type: 'string', enum: ['a', 'b'], 'x-ltt-control': 'dropdown-dong',
             'x-ltt-nhan': { a: 'Nhanh', b: 'Đẹp' } },
    giong_nhan_ban: { type: 'string', enum: [] },
    resolution: { type: 'string', enum: ['720p', '1080p'],
                  'x-ltt-dong': { nguon: 'app_property', prop: 'model' } },
    cau_hinh: { type: 'object', 'x-ltt-kieu': 'json' },
    duration_s: { type: 'number', readOnly: true, 'x-ltt-control': 'may_tu_dien' },
  },
}

function Harness({ onChange = vi.fn() }: { onChange?: (t: string, v: unknown) => void }) {
  const [gia, setGia] = useState<Record<string, unknown>>({ prompt: 'xin chao' })
  return <FormTuLuocDo luocDo={luocDo} giaTri={gia} onChange={(t, v) => {
    setGia(c => ({ ...c, [t]: v })); onChange(t, v) }} />
}

describe('FormTuLuocDo', () => {
  it('sinh mot o cho moi thuoc tinh, danh dau truong bat buoc', () => {
    render(<Harness />)
    expect(screen.getByLabelText('prompt *')).toHaveValue('xin chao')
    expect(screen.getByLabelText('count')).toHaveValue(1)
  })

  it('x-ltt-control textarea cho o nhieu dong', () => {
    render(<Harness />)
    expect(screen.getByLabelText('ghi_chu').tagName).toBe('TEXTAREA')
  })

  it('enum thanh combobox, nhan lay tu x-ltt-nhan', () => {
    render(<Harness />)
    expect(screen.getByRole('option', { name: 'Nhanh' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: '2160' })).toBeInTheDocument()
  })

  it('enum SO tra ve SO chu khong phai chuoi', () => {
    const bat = vi.fn()
    render(<Harness onChange={bat} />)
    fireEvent.change(screen.getByLabelText('target_height'),
                     { target: { value: '2160' } })
    expect(bat).toHaveBeenCalledWith('target_height', 2160)
  })

  it('so va bool tra ve dung kieu', () => {
    const bat = vi.fn()
    render(<Harness onChange={bat} />)
    fireEvent.change(screen.getByLabelText('count'), { target: { value: '3' } })
    expect(bat).toHaveBeenCalledWith('count', 3)
    fireEvent.click(screen.getByLabelText('preview'))
    expect(bat).toHaveBeenCalledWith('preview', true)
  })

  it('object thanh o code-json va bao loi khi JSON hong, khong nuot', () => {
    const bat = vi.fn()
    render(<Harness onChange={bat} />)
    const o = screen.getByLabelText('cau_hinh')
    fireEvent.change(o, { target: { value: '{"a":' } })
    expect(screen.getByText('JSON không hợp lệ')).toBeInTheDocument()
    expect(bat).not.toHaveBeenCalledWith('cau_hinh', expect.anything())
    fireEvent.change(o, { target: { value: '{"a":1}' } })
    expect(bat).toHaveBeenCalledWith('cau_hinh', { a: 1 })
  })

  it('truong may tu dien hien nhung khoa lai', () => {
    render(<Harness />)
    expect(screen.getByLabelText('duration_s')).toBeDisabled()
  })

  it('chuoi bieu thuc {{ }} di qua nguyen ven', () => {
    const bat = vi.fn()
    render(<Harness onChange={bat} />)
    fireEvent.change(screen.getByLabelText('prompt *'),
                     { target: { value: '{{ nodes.a.output.text }}' } })
    expect(bat).toHaveBeenCalledWith('prompt', '{{ nodes.a.output.text }}')
  })

  // ⭐ Mot tham so SO co the dang giu mot BIEU THUC (spec §4.6: literal HOAC
  //    `{{ }}`). O do phai la o CHU — mot `<input type="number">` xoa sach
  //    chuoi khong phai so, va tham chieu bien mat im lang.
  it('o SO dang giu bieu thuc thi la o chu va di qua nguyen ven', () => {
    const bat = vi.fn()
    render(<FormTuLuocDo luocDo={luocDo}
      giaTri={{ count: '{{ nodes.a.output.n }}' }} onChange={bat} />)
    const o = screen.getByLabelText('count')
    expect(o).toHaveAttribute('type', 'text')
    expect(o).toHaveValue('{{ nodes.a.output.n }}')
    fireEvent.change(o, { target: { value: '{{ nodes.b.output.n }}' } })
    expect(bat).toHaveBeenCalledWith('count', '{{ nodes.b.output.n }}')
  })

  // ⭐ GENERIC_GAP D10 (spec §4.6): `enum: []` nghia la *"ban chua co lua chon
  //    nao"*, KHAC HAN mot `string` tu do. Mot o chu tu do o day thi khach go
  //    duoc `voice_id` cua nguoi khac.
  it('enum RONG la "chua co lua chon nao", khong phai o chu tu do', () => {
    render(<Harness />)
    const o = screen.getByLabelText('giong_nhan_ban')
    expect(o.tagName).toBe('SELECT')
    expect(o).toBeDisabled()
    expect(screen.getByText('Chưa có lựa chọn nào')).toBeInTheDocument()
  })

  it('truong phu thuoc tham so khac noi ro nguon dong', () => {
    render(<Harness />)
    expect(screen.getByText('Tuỳ theo: model')).toBeInTheDocument()
  })

  it('luoc do khong co thuoc tinh thi noi ro, khong ve form rong', () => {
    render(<FormTuLuocDo luocDo={{ type: 'object', properties: {}, required: [] }}
      giaTri={{}} onChange={vi.fn()} />)
    expect(screen.getByText('Node này không có tham số.')).toBeInTheDocument()
  })

  it('readOnly toan form khoa moi o, ke ca enum va checkbox', () => {
    render(<FormTuLuocDo luocDo={luocDo} giaTri={{}} readOnly onChange={vi.fn()} />)
    expect(screen.getByLabelText('prompt *')).toBeDisabled()
    expect(screen.getByLabelText('target_height')).toBeDisabled()
    expect(screen.getByLabelText('preview')).toBeDisabled()
    expect(screen.getByLabelText('cau_hinh')).toBeDisabled()
  })
})
