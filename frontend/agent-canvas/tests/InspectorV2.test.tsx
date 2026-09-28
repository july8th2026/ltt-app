// Inspector V2 (§6) — lan UI-5. Ba nhom menh de, moi nhom mot loi DO DUOC.
//
// 1. Truong phu thuoc phai AN khi cha chua co gia tri (⛔ khong hien xam).
//    Do duoc 27/09: mot buoc vua tha xuong hien BA dropdown "— chưa có lựa
//    chọn nào —" cung luc.
// 2. O KET NOI chi hien khi buoc THAT SU doi mot ket noi, va "+ Tạo kết nối"
//    la DONG DAU cua chinh dropdown (luong Activepieces, MIT) — tao tai cho,
//    ⛔ khong roi trang.
// 3. Bon tab chua lam phai NOI RA la chung chua lam. ⛔ Mot tab trong trong
//    nhu da hoat dong lam nguoi dung ket luan "tinh nang nay hong".
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { useState } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { FormTuLuocDo } from '../src/inspector/FormTuLuocDo'
import { OKetNoi } from '../src/inspector/OKetNoi'
import { StepInspector } from '../src/inspector/StepInspector'
import type { BuocCoKetNoi } from '../src/inspector/StepInspector'
import type { LuocDo, NodeDefinition } from '../src/nodeDefinition'

afterEach(() => { cleanup(); vi.restoreAllMocks() })

// Hinh dang lay tu JSON THAT (`palette_v3.sang_json` + `luoc_do.
// sang_json_schema`), ⛔ khong tu tri nho: `x-ltt-dong.nguon` la mot MARKER
// (`app_property`), va ba truong cung `depends_on` MOT tham so la hinh dang da
// gay loi that.
const LUOC_DO: LuocDo = {
  type: 'object',
  required: ['model'],
  additionalProperties: false,
  properties: {
    model: { type: 'string', enum: ['a', 'b'] },
    resolution: { type: 'string', enum: ['720p', '1080p'],
                  'x-ltt-dong': { nguon: 'app_property', prop: 'model' } },
    duration: { type: 'integer', enum: [4, 8],
                'x-ltt-dong': { nguon: 'app_property', prop: 'model' } },
    aspect_ratio: { type: 'string', enum: ['16:9', '9:16'],
                    'x-ltt-dong': { nguon: 'app_property', prop: 'model' } },
    bat_phu_de: { type: 'boolean',
                  'x-ltt-dong': { nguon: 'app_property', prop: 'im_lang' } },
    im_lang: { type: 'boolean', default: false },
  },
}

function HarnessForm({ dau = {} as Record<string, unknown> }) {
  const [gia, setGia] = useState<Record<string, unknown>>(dau)
  return <FormTuLuocDo luocDo={LUOC_DO} giaTri={gia}
    onChange={(t, v) => setGia(c => ({ ...c, [t]: v }))} />
}

describe('§6 luat 1 — truong phu thuoc phai AN, khong hien xam', () => {
  it('cha chua co gia tri: ⛔ KHONG mot o phu thuoc nao duoc ve', () => {
    render(<HarnessForm />)
    expect(screen.getByLabelText('model *')).toBeInTheDocument()
    for (const ten of ['resolution', 'duration', 'aspect_ratio']) {
      expect(screen.queryByLabelText(ten)).toBeNull()
    }
    // ⭐ Va KHONG con mot dropdown chet nao — do la chinh loi da do duoc.
    expect(screen.queryByText('— chưa có lựa chọn nào —')).toBeNull()
  })

  it('MOT dong noi ro dieu kien thay cho BA o bi an', () => {
    render(<HarnessForm />)
    // ⛔ Khong im lang hoan toan: mot o bien mat khong dau vet thi khach tuong
    //    buoc nay thieu tham so.
    expect(screen.getByText('Tuỳ theo: model')).toBeInTheDocument()
    expect(screen.getByText('Chọn model để hiện thêm 3 ô.')).toBeInTheDocument()
  })

  it('cha co gia tri: ba o HIEN ra', () => {
    render(<HarnessForm />)
    fireEvent.change(screen.getByLabelText('model *'), { target: { value: 'a' } })
    for (const ten of ['resolution', 'duration', 'aspect_ratio']) {
      expect(screen.getByLabelText(ten)).toBeInTheDocument()
    }
    expect(screen.queryByText('Chọn model để hiện thêm 3 ô.')).toBeNull()
  })

  it('🔑 `false` la MOT GIA TRI, khong phai "chua chon"', () => {
    // ⛔ `!gia` coi `false`/`0` la trong, va the la o phu thuoc bi an dung luc
    //    cha DA co gia tri — dung hinh dang "hai trang thai gop thanh mot".
    render(<HarnessForm dau={{ im_lang: false }} />)
    expect(screen.getByLabelText('bat_phu_de')).toBeInTheDocument()
  })

  it('doi chung: cha VANG HAN thi o phu thuoc bi an', () => {
    render(<HarnessForm dau={{}} />)
    expect(screen.queryByLabelText('bat_phu_de')).toBeNull()
  })
})

// ── O ket noi ─────────────────────────────────────────────────────────────

const SO_NHA_CUNG_CAP = {
  tang: ['self', 'cloud'],
  kieu: ['api_key', 'bearer', 'basic', 'oauth2'],
  khoa_bi_mat: {
    api_key: [{ ten: 'gia_tri', nhan: 'Khoá API', che: true, nhieu_dong: false }],
    oauth2: [
      { ten: 'client_id', nhan: 'Client ID', che: false, nhieu_dong: false },
      { ten: 'client_secret', nhan: 'Client Secret', che: true, nhieu_dong: false },
    ],
  },
  nha_cung_cap: [{
    ma: 'nhacungcap_thu', kieu: ['oauth2'], node_type: ['buoc_can_oauth'],
    co_tang_cloud: true, san_sang: false, ly_do: 'chua_cau_hinh',
    bien_moi_truong: ['LTT_OAUTH_NHACUNGCAP_THU_CLIENT_ID',
                      'LTT_OAUTH_NHACUNGCAP_THU_CLIENT_SECRET'],
  }],
}

const KET_NOI_API_KEY = {
  id: 'kn-1', kieu: 'api_key', nha_cung_cap: '', ten: 'Khoá của tôi',
  preview: '...4242', pham_vi: [], meta: {}, het_han_luc: null,
  thu_hoi_luc: null, dung_lan_cuoi: null, created_at: null,
}

function mockFetch(khiTao?: () => Response) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(
    async (duong: RequestInfo | URL, init?: RequestInit) => {
      const u = String(duong)
      if (init?.method === 'POST') {
        return khiTao ? khiTao() : new Response(
          JSON.stringify({ ...KET_NOI_API_KEY, id: 'kn-moi' }),
          { status: 201, headers: { 'Content-Type': 'application/json' } })
      }
      if (u.includes('nha-cung-cap')) {
        return new Response(JSON.stringify(SO_NHA_CUNG_CAP),
          { headers: { 'Content-Type': 'application/json' } })
      }
      return new Response(JSON.stringify({ items: [KET_NOI_API_KEY] }),
        { headers: { 'Content-Type': 'application/json' } })
    })
}

describe('§6 luat 2 — o ket noi, tao duoc TAI CHO', () => {
  let goi: ReturnType<typeof mockFetch>
  beforeEach(() => { goi = mockFetch() })

  it('"+ Tạo kết nối" la DONG DAU cua chinh dropdown', async () => {
    render(<OKetNoi kieuChoPhep={['api_key']} buocType="buoc_thu" giaTri=""
      csrf="t" onChange={vi.fn()} />)
    const o = await screen.findByLabelText('Kết nối *')
    // ⭐ DONG DAU. ⛔ Khong phai mot nut o trang khac: nguoi dung khong roi
    //    ngu canh dang cau hinh.
    expect((o as HTMLSelectElement).options[0].textContent).toBe('+ Tạo kết nối')
  })

  it('goi may chu LOC theo dung `kieu` ma buoc nay nhan', async () => {
    render(<OKetNoi kieuChoPhep={['oauth2', 'api_key']} buocType="b" giaTri=""
      csrf="t" onChange={vi.fn()} />)
    await screen.findByLabelText('Kết nối *')
    // ⭐ Loc o MAY CHU: o chon khong bao gio duoc moi mot ket noi ma cong
    //    publish se tu choi (`credential.kiem_ref` doi dung `kieu`).
    const duong = goi.mock.calls.map(c => String(c[0]))
    expect(duong.some(d => d.includes('kieu=oauth2%2Capi_key'))).toBe(true)
  })

  it('tao xong thi CHON LUON ket noi moi, khong bat chon lai', async () => {
    const bat = vi.fn()
    render(<OKetNoi kieuChoPhep={['api_key']} buocType="b" giaTri=""
      csrf="t-csrf" onChange={bat} />)
    const o = await screen.findByLabelText('Kết nối *')
    fireEvent.change(o, { target: { value: '\u0000tao-ket-noi' } })
    const form = await screen.findByRole('form', { name: 'Tạo kết nối mới' })
    // Nhan o den TU MAY CHU (`khoa_bi_mat`), ⛔ khong mot bang nhan nao o day.
    fireEvent.change(within(form).getByLabelText('Khoá API'),
                     { target: { value: 'sk-thu-4242' } })
    fireEvent.click(within(form).getByRole('button', { name: 'Lưu kết nối' }))
    await waitFor(() => expect(bat).toHaveBeenCalledWith('kn-moi'))
    const post = goi.mock.calls.find(c => (c[1] as RequestInit)?.method === 'POST')
    expect(String(post?.[0])).toBe('/agent/api/v3/ket-noi')
    const than = JSON.parse(String((post?.[1] as RequestInit).body))
    // ⛔ Chi DUNG cac khoa may chu doi — mot khoa la bi 422, va do la dung.
    expect(Object.keys(than.bi_mat)).toEqual(['gia_tri'])
    expect(than.kieu).toBe('api_key')
  })

  it('o bi mat `che` la o CHE, ⛔ khong phai o chu thuong', async () => {
    render(<OKetNoi kieuChoPhep={['api_key']} buocType="b" giaTri=""
      csrf="t" onChange={vi.fn()} />)
    fireEvent.change(await screen.findByLabelText('Kết nối *'),
                     { target: { value: '\u0000tao-ket-noi' } })
    const o = await screen.findByLabelText('Khoá API')
    expect(o).toHaveAttribute('type', 'password')
    expect(o).toHaveAttribute('autocomplete', 'off')
  })

  it('tang CLOUD chua cau hinh: noi THANG ra va khoa lai', async () => {
    render(<OKetNoi kieuChoPhep={['oauth2']} buocType="buoc_can_oauth" giaTri=""
      csrf="t" onChange={vi.fn()} />)
    fireEvent.change(await screen.findByLabelText('Kết nối *'),
                     { target: { value: '\u0000tao-ket-noi' } })
    const form = await screen.findByRole('form', { name: 'Tạo kết nối mới' })
    // 🔴 ⛔ Khong bia mot luong gia vo hoat dong: dang ky OAuth app la viec
    //    CHI CHU DU AN lam duoc.
    expect(within(form).getByText(/LTT chưa cấu hình cho nhà cung cấp này/))
      .toBeInTheDocument()
    expect(within(form).getByRole('radio', {
      name: /Ứng dụng do LTT quản lý/ })).toBeDisabled()
    expect(within(form).getByRole('radio', {
      name: /Ứng dụng của tôi/ })).not.toBeDisabled()
  })

  it('loi may chu KHONG bi nuot — danh sach rong phai phan biet duoc', async () => {
    vi.restoreAllMocks()
    // ⚠️ `mockImplementation`, ⛔ khong `mockResolvedValue`: mot `Response`
    //    dung chung bi doc than HAI lan (`Promise.all` goi hai cua), va loi
    //    "body unusable" se thay cho thong diep that — phep do do sai thu.
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => new Response(
      JSON.stringify({ detail: { ma: 'x', thong_diep: 'Máy chủ từ chối.' } }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }))
    render(<OKetNoi kieuChoPhep={['api_key']} buocType="b" giaTri=""
      csrf="t" onChange={vi.fn()} />)
    expect(await screen.findByText('Máy chủ từ chối.')).toBeInTheDocument()
  })
})

// ── Nam tab ──────────────────────────────────────────────────────────────

const ND: NodeDefinition = {
  type: 'buoc_thu', type_version: 1, kind: 'connector', category: 'CONNECTORS',
  title: 'Bước thử', description: '', icon: '', app_name: '',
  cong_vao: [], cong_ra: [], tham_so: LUOC_DO, thi_hanh: 'job',
  side_effect: 'external', resource: {}, timeout_expr: '',
  retry_mac_dinh: { max: 0, backoff_s: 0 },
  gia: { kieu: 'co_dinh', so: 0, job_type: '' },
  credential: ['api_key'], quyen: [], cho: [], ma_loi: [],
  co_mock: false, publish_duoc: true,
}

const BUOC: BuocCoKetNoi = {
  id: 'n1', type: 'tool', position: { x: 0, y: 0 }, data: { params: {} },
}

function veInspector(ghiDe: Partial<React.ComponentProps<typeof StepInspector>> = {}) {
  return render(<StepInspector buoc={BUOC} dinhNghia={ND} nodes={[BUOC]}
    edges={[]} csrf="t" onLabel={vi.fn()} onParam={vi.fn()}
    onKetNoi={vi.fn()} {...ghiDe} />)
}

describe('§6 — nam tab', () => {
  beforeEach(() => { mockFetch() })

  it('nam tab, tab Cấu hình mo san', () => {
    veInspector()
    for (const ten of ['Cấu hình', 'Dữ liệu vào', 'Tuỳ chọn', 'Kết quả',
                       'Chạy thử']) {
      expect(screen.getByRole('button', { name: ten })).toBeInTheDocument()
    }
    expect(screen.getByRole('button', { name: 'Cấu hình' }))
      .toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByLabelText('model *')).toBeInTheDocument()
  })

  it('ba tab chua lam NOI RA la chung chua lam', () => {
    // ⚠️ "Dữ liệu vào" lam THAT o lan UI-6 (`ChonDuLieu` — xem
    //    `ChonDuLieu.test.tsx`) nen KHONG con trong danh sach dat cho o day.
    veInspector()
    for (const ten of ['Tuỳ chọn', 'Kết quả', 'Chạy thử']) {
      fireEvent.click(screen.getByRole('button', { name: ten }))
      // ⛔ Mot tab trong trong nhu da hoat dong la thu te nhat.
      expect(screen.getByText(`${ten} — chưa hoạt động`)).toBeInTheDocument()
    }
  })

  it('buoc KHONG doi ket noi: ⛔ KHONG hien o ket noi', () => {
    veInspector({ dinhNghia: { ...ND, credential: [] } })
    expect(screen.queryByLabelText('Kết nối *')).toBeNull()
    // ...va o van hien khi buoc DOI (doi chung cho menh de tren).
    cleanup()
    veInspector()
    expect(screen.getByText('Kết nối *')).toBeInTheDocument()
  })

  it('khong chon buoc nao thi noi ro, khong ve mot panel rong', () => {
    render(<StepInspector buoc={null} dinhNghia={null} nodes={[]} edges={[]}
      csrf="t" onLabel={vi.fn()} onParam={vi.fn()} onKetNoi={vi.fn()} />)
    expect(screen.getByText('Chọn một node để xem tham số.')).toBeInTheDocument()
  })

  it('hanh dong o chan panel; "Chạy thử bước" MO tab, khong bam rong', () => {
    const xoa = vi.fn()
    const nhanBan = vi.fn()
    veInspector({ onXoa: xoa, onNhanBan: nhanBan })
    // ⚠️ Ten khac tab ("Chạy thử") co y: hai dieu khien trung ten trong mot
    //    panel thi nguoi doc man hinh nghe hai lan cung mot cau.
    fireEvent.click(screen.getByRole('button', { name: 'Chạy thử bước' }))
    expect(screen.getByText('Chạy thử — chưa hoạt động')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Cấu hình' }))
    fireEvent.click(screen.getByRole('button', { name: 'Nhân bản' }))
    fireEvent.click(screen.getByRole('button', { name: 'Xóa bước' }))
    expect(nhanBan).toHaveBeenCalledOnce()
    expect(xoa).toHaveBeenCalledOnce()
  })

  it('chi phi: `undefined` va `0` KHONG duoc gop thanh mot cau', () => {
    veInspector()
    expect(screen.getByText('Chi phí do server xác nhận')).toBeInTheDocument()
    cleanup()
    veInspector({ gia: 0 })
    expect(screen.getByText('Tối đa 0 credit')).toBeInTheDocument()
  })
})
