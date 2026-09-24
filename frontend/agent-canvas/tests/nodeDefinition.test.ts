import { describe, expect, it } from 'vitest'
import { locPalette, noiDuoc, timNut } from '../src/nodeDefinition'
import type { LuatNoiDay, NhomPalette, NodeDefinition } from '../src/nodeDefinition'

const luat: LuatNoiDay = { phien_ban: 2, kieu: ['image', 'video', 'any'],
  hau_to_tap_hop: '[]',
  cap_noi_duoc: [['image', 'image'], ['image', 'image[]'], ['image', 'any'],
                 ['any', 'video'], ['video', 'video']] }

const nut = (type: string, title: string, category = 'LTT_APPS'): NodeDefinition =>
  ({ type, type_version: 1, kind: 'app', category, title, description: 'mo ta ' + type,
     icon: '', app_name: 'App', cong_vao: [], cong_ra: [], thi_hanh: 'job',
     tham_so: { type: 'object', properties: {}, required: [] },
     side_effect: 'external', resource: {}, timeout_expr: '',
     retry_mac_dinh: { max: 0, backoff_s: 30 },
     gia: { kieu: 'mien_phi', so: 0, job_type: '' }, credential: [], quyen: [],
     cho: [], ma_loi: [], co_mock: false, publish_duoc: true })

const nhom: NhomPalette[] = [
  { category: 'TRIGGERS', nut: [nut('trigger.manual', 'Chạy thủ công', 'TRIGGERS')] },
  { category: 'LTT_APPS', nut: [nut('app.image.generate', 'Sinh ảnh'),
                                nut('app.text.chat', 'Sinh văn bản')] },
]

describe('luat noi day tai tu server', () => {
  it('tra bang, khong cai dat lai luat', () => {
    expect(noiDuoc(luat, 'image', 'image[]', 0, false)).toBe(true)
    expect(noiDuoc(luat, 'image', 'video', 0, false)).toBe(false)
    expect(noiDuoc(luat, 'image', 'any', 0, false)).toBe(true)
  })

  it('cong khong nhan nhieu canh thi canh thu hai bi tu choi', () => {
    expect(noiDuoc(luat, 'image', 'image', 1, false)).toBe(false)
    expect(noiDuoc(luat, 'image', 'image', 3, true)).toBe(true)
  })

  it('kieu la khong co trong bang thi tu choi, khong doan', () => {
    expect(noiDuoc(luat, 'hinh_anh', 'image', 0, false)).toBe(false)
  })
})

describe('palette', () => {
  it('tim node theo type qua moi nhom', () => {
    expect(timNut(nhom, 'app.text.chat')?.title).toBe('Sinh văn bản')
    expect(timNut(nhom, 'app.khong.co')).toBeUndefined()
  })

  it('tim kiem theo ten, mo ta va type; nhom rong bi bo', () => {
    expect(locPalette(nhom, 'thủ công').map(n => n.category)).toEqual(['TRIGGERS'])
    expect(locPalette(nhom, 'text.chat')[0].nut.map(n => n.type))
      .toEqual(['app.text.chat'])
    expect(locPalette(nhom, 'mo ta app.image').length).toBe(1)
    expect(locPalette(nhom, '')).toEqual(nhom)
  })
})
