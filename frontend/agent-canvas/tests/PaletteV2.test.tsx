import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { PaletteV2 } from '../src/palette/PaletteV2'
import type { NhomPalette, NodeDefinition } from '../src/nodeDefinition'

afterEach(cleanup)

const nd = (type: string, title: string, over: Partial<NodeDefinition> = {}):
  NodeDefinition => ({ type, type_version: 1, kind: 'app', category: 'LTT_APPS',
    title, description: 'mo ta', icon: '', app_name: 'App', cong_vao: [],
    cong_ra: [], tham_so: { type: 'object', properties: {}, required: [] },
    thi_hanh: 'job', side_effect: 'external', resource: {}, timeout_expr: '',
    retry_mac_dinh: { max: 0, backoff_s: 30 },
    gia: { kieu: 'theo_registry', so: 0, job_type: 'j' }, credential: [],
    quyen: [], cho: [], ma_loi: [], co_mock: false, publish_duoc: true, ...over })

// ⚠️ `resource` cong khai CHI con `class`: `palette_v3.RESOURCE_CONG_KHAI =
//    ("class",)` loc bo `vram_min_mb`/`slots`/`est_duration_s`. Nen the node
//    noi "GPU", khong noi mot con so VRAM — con so do khong ra toi trinh duyet.
const nhom: NhomPalette[] = [
  { category: 'TRIGGERS', nut: [nd('trigger.manual', 'Chạy thủ công',
      { kind: 'trigger', category: 'TRIGGERS', publish_duoc: false })] },
  { category: 'LTT_APPS', nut: [nd('app.image.generate', 'Sinh ảnh',
      { resource: { class: 'gpu' } }),
    nd('app.text.chat', 'Sinh văn bản')] },
]

describe('PaletteV2', () => {
  it('nhom theo category voi nhan tieng Viet', () => {
    render(<PaletteV2 nhom={nhom} truyVan="" onTruyVan={vi.fn()} onChon={vi.fn()} />)
    expect(screen.getByRole('heading', { name: 'Kích hoạt' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'App LTT' })).toBeInTheDocument()
  })

  it('the node hien type@version, gia va tai nguyen', () => {
    render(<PaletteV2 nhom={nhom} truyVan="" onTruyVan={vi.fn()} onChon={vi.fn()} />)
    expect(screen.getByText('app.image.generate@1')).toBeInTheDocument()
    expect(screen.getByTestId('palette-tai-nguyen')).toHaveTextContent('GPU')
    expect(screen.getAllByText('Theo bảng giá').length).toBe(3)
  })

  // ⭐ `palette_v3.sang_json` gan dau o MUC NODE khi node ra palette voi luoc
  //    do TINH. The phai NOI RA — nguoi dung keo node ve roi moi phat hien
  //    mot nua tham so bi khoa thi da muon.
  it('node mang x-ltt-loi noi ro la chua tai duoc lua chon', () => {
    const hong: NhomPalette[] = [{ category: 'LTT_APPS', nut: [
      nd('app.voice.tts', 'Đọc văn bản', { 'x-ltt-loi': 'LUACHON_KHONG_TAI_DUOC' })] }]
    render(<PaletteV2 nhom={hong} truyVan="" onTruyVan={vi.fn()} onChon={vi.fn()} />)
    expect(screen.getByText('Chưa tải được lựa chọn')).toBeInTheDocument()
  })

  it('node BINH THUONG khong deo nhan canh bao oan', () => {
    render(<PaletteV2 nhom={nhom} truyVan="" onTruyVan={vi.fn()} onChon={vi.fn()} />)
    expect(screen.queryByText('Chưa tải được lựa chọn')).toBeNull()
  })

  it('node chua publish duoc thi vo hieu, khong moi keo', () => {
    render(<PaletteV2 nhom={nhom} truyVan="" onTruyVan={vi.fn()} onChon={vi.fn()} />)
    expect(screen.getByRole('button', { name: /Chạy thủ công/ })).toBeDisabled()
  })

  it('bam mot the goi onChon voi dung dinh nghia', () => {
    const chon = vi.fn()
    render(<PaletteV2 nhom={nhom} truyVan="" onTruyVan={vi.fn()} onChon={chon} />)
    fireEvent.click(screen.getByRole('button', { name: /Sinh văn bản/ }))
    expect(chon).toHaveBeenCalledWith(expect.objectContaining(
      { type: 'app.text.chat' }))
  })

  it('o tim kiem loc va bao khi khong con gi', () => {
    const { rerender } = render(<PaletteV2 nhom={nhom} truyVan="văn bản"
      onTruyVan={vi.fn()} onChon={vi.fn()} />)
    expect(screen.queryByText('Sinh ảnh')).not.toBeInTheDocument()
    rerender(<PaletteV2 nhom={nhom} truyVan="khong-co-gi" onTruyVan={vi.fn()}
      onChon={vi.fn()} />)
    expect(screen.getByText('Không tìm thấy node nào.')).toBeInTheDocument()
  })

  it('go vao o tim kiem bao len tren', () => {
    const go = vi.fn()
    render(<PaletteV2 nhom={nhom} truyVan="" onTruyVan={go} onChon={vi.fn()} />)
    fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'ảnh' } })
    expect(go).toHaveBeenCalledWith('ảnh')
  })

  it('gan day hien thanh mot nhom rieng o tren cung', () => {
    render(<PaletteV2 nhom={nhom} truyVan="" onTruyVan={vi.fn()} onChon={vi.fn()}
      ganDay={['app.text.chat']} />)
    const tieu_de = screen.getAllByRole('heading').map(h => h.textContent)
    expect(tieu_de[0]).toBe('Gần đây')
  })
})
