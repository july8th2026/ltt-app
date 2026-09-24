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
    // `apps/agent/routes/palette_v3.py::_tham_so_co_dau` gan dau nay len DUNG
    // nhung truong chua tai duoc lua chon dong. Luoc do con lai la ban TINH —
    // `voice_id` tinh la mot `string` TU DO.
    voice_id: { type: 'string', 'x-ltt-loi': 'LUACHON_KHONG_TAI_DUOC' },
    so_giong: { type: 'integer', 'x-ltt-loi': 'LUACHON_KHONG_TAI_DUOC' },
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

  // ── x-ltt-loi: MAT XICH CUOI cua phan quyet "palette la catalogue" ──────
  //
  // 🔴 Khi giai tuy chon dong cua mot tool nem loi, `palette_v3.sang_json` van
  //    tra node ra palette — voi luoc do TINH va mot dau doc duoc. Luoc do
  //    tinh cua `voice_id` la mot `string` TU DO. Khong khoa o lai thi nguoi
  //    dung go bua mot `voice_id`, publish qua, va hong LUC CHAY — dung cai
  //    ma dau `x-ltt-loi` sinh ra de chan.
  //
  // ⚠️ Phep do o day la `toBeDisabled()`, KHONG phai "onChange khong duoc goi".
  //    `fireEvent.change` ban thang su kien vao phan tu, nen no goi duoc
  //    handler cua ca mot o `disabled` — trinh duyet that thi khong. Mot
  //    `expect(bat).not.toHaveBeenCalled()` o day do jsdom, khong do san pham:
  //    no do khi ta khoa o, va do la mot phep do lech chieu. `disabled` moi la
  //    thu trinh duyet cuong che.
  it('truong mang x-ltt-loi bi KHOA lai, khong phai o chu tu do', () => {
    render(<FormTuLuocDo luocDo={luocDo} giaTri={{}} onChange={vi.fn()} />)
    const o = screen.getByLabelText('voice_id')
    expect(o).toBeDisabled()
    // Va no la o CHU (luoc do tinh) — tuc chinh hinh dang nguy hiem: neu
    // khong khoa, no trong y het mot tham so khoe manh.
    expect(o).toHaveAttribute('type', 'text')
  })

  it('truong mang x-ltt-loi noi ro VI SAO bi khoa', () => {
    render(<FormTuLuocDo luocDo={luocDo} giaTri={{}} onChange={vi.fn()} />)
    expect(screen.getAllByText('Chưa tải được lựa chọn').length).toBe(2)
  })

  // Mot o SO mang dau loi cung phai khoa — ke ca nut "dung bieu thuc".
  it('o SO mang x-ltt-loi khong mo duoc loi thoat bieu thuc', () => {
    render(<FormTuLuocDo luocDo={luocDo} giaTri={{}} onChange={vi.fn()} />)
    expect(screen.getByLabelText('so_giong')).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Dùng biểu thức cho so_giong' }))
      .toBeDisabled()
  })

  // ── O SO: phai GO MOI duoc bieu thuc, khong chi hien thi cai da luu ──────
  //
  // 🔴 Nhanh `laBieuThuc` chi voi toi khi gia tri DA LUU la bieu thuc. Voi mot
  //    o `<input type="number">`, go `{` khong vao duoc gia tri — nen khong co
  //    duong nao BIEN mot o so thanh bieu thuc tu giao dien. Tham chieu chi
  //    dat duoc bang cach sua JSON o noi khac. Can mot cong tac tuong minh.
  it('nut "dung bieu thuc" bien o SO thanh o chu va gui chuoi nguyen ven', () => {
    const bat = vi.fn()
    render(<FormTuLuocDo luocDo={luocDo} giaTri={{ count: 2 }} onChange={bat} />)
    expect(screen.getByLabelText('count')).toHaveAttribute('type', 'number')
    const cong_tac = screen.getByRole('button', { name: 'Dùng biểu thức cho count' })
    expect(cong_tac).toHaveAttribute('aria-pressed', 'false')
    fireEvent.click(cong_tac)
    expect(cong_tac).toHaveAttribute('aria-pressed', 'true')
    const o = screen.getByLabelText('count')
    expect(o).toHaveAttribute('type', 'text')
    fireEvent.change(o, { target: { value: '{{ nodes.a.output.n }}' } })
    expect(bat).toHaveBeenCalledWith('count', '{{ nodes.a.output.n }}')
  })

  // Gia tri DA LUU la bieu thuc ⇒ cong tac phai BAT SAN, neu khong mot lan
  // render lai se doi o ve `type=number` va nuot tham chieu.
  it('gia tri da luu la bieu thuc thi cong tac bat san', () => {
    render(<FormTuLuocDo luocDo={luocDo}
      giaTri={{ count: '{{ nodes.a.output.n }}' }} onChange={vi.fn()} />)
    expect(screen.getByRole('button', { name: 'Dùng biểu thức cho count' }))
      .toHaveAttribute('aria-pressed', 'true')
  })

  // O CHU khong can cong tac: no von go duoc `{{ }}` (bai o tren da chot).
  it('o CHU khong moc them cong tac bieu thuc', () => {
    render(<FormTuLuocDo luocDo={luocDo} giaTri={{}} onChange={vi.fn()} />)
    expect(screen.queryByRole('button', { name: 'Dùng biểu thức cho prompt' }))
      .toBeNull()
  })

  it('readOnly toan form khoa moi o, ke ca enum va checkbox', () => {
    render(<FormTuLuocDo luocDo={luocDo} giaTri={{}} readOnly onChange={vi.fn()} />)
    expect(screen.getByLabelText('prompt *')).toBeDisabled()
    expect(screen.getByLabelText('target_height')).toBeDisabled()
    expect(screen.getByLabelText('preview')).toBeDisabled()
    expect(screen.getByLabelText('cau_hinh')).toBeDisabled()
  })
})
