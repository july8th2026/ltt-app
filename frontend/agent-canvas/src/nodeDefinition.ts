// Kieu cua NodeDefinition (spec §4.4) va luat noi day tai TU SERVER.
//
// ⛔ Khong cai dat lai luat noi day o day. `he_kieu.xuat_luat_noi_day()` xuat
//    mot BANG CAP; client tra bang. Hai ban cai dat song song thi lech — chi
//    la chua ai do (`platform_core/workflow/he_kieu.py`, G39/M9).
//
// Hinh dang o duoi lay tu JSON THAT ma `apps/agent/routes/palette_v3.py`
// (`sang_json`) va `he_kieu.xuat_luat_noi_day()` tra ve, khong lay tu tri nho.

export type NodeKind = 'trigger'|'control'|'data'|'app'|'ai'|'connector'|'subworkflow'

export type Cong = { ten: string; kieu: string; bat_buoc: boolean; nhieu: boolean }

export type TruongLuocDo = {
  type: string
  enum?: unknown[]
  default?: unknown
  minimum?: number
  maximum?: number
  maxLength?: number
  description?: string
  readOnly?: boolean
  items?: { type: string }
  'x-ltt-kieu'?: string
  'x-ltt-control'?: string
  'x-ltt-nhan'?: Record<string, string>
}

export type LuocDo = {
  type: 'object'
  properties: Record<string, TruongLuocDo>
  required: string[]
}

export type Gia = {
  kieu: 'mien_phi'|'co_dinh'|'theo_registry'
  so: number
  job_type: string
}

//: `nut.RESOURCE_CLASS` — danh sach DONG, `NodeDefinition.__post_init__` tu choi
//  gia tri khac (`nut.py:101`).
export type ResourceClass = 'cpu'|'gpu'|'api'

// ⚠️ CHI khoa `class` ra trinh duyet. `palette_v3.RESOURCE_CONG_KHAI` loc bo
//    `vram_min_mb`/`slots`/`est_duration_s` vi do la suc chua ha tang. Them
//    khoa vao day chi khi route mo khoa do ra truoc.
export type Resource = { class?: ResourceClass }

export type NodeDefinition = {
  type: string
  type_version: number
  kind: NodeKind
  category: string
  title: string
  description: string
  icon: string
  app_name: string
  cong_vao: Cong[]
  cong_ra: Cong[]
  tham_so: LuocDo
  thi_hanh: 'inline'|'job'|'run_con'
  side_effect: string
  resource: Resource
  timeout_expr: string
  retry_mac_dinh: { max: number; backoff_s: number }
  gia: Gia
  credential: string[]
  quyen: string[]
  cho: string[]
  ma_loi: string[]
  co_mock: boolean
  publish_duoc: boolean
}

export type NhomPalette = { category: string; nut: NodeDefinition[] }

export type LuatNoiDay = {
  phien_ban: number
  kieu: string[]
  hau_to_tap_hop: string
  cap_noi_duoc: [string, string][]
  // Hai khoa server VAN tra ve (`he_kieu.xuat_luat_noi_day()`); de tuy chon vi
  // client khong duoc phep dung chung de SUY ra luat — `cap_noi_duoc` la nguon.
  ep_kieu?: [string, string][]
  ghi_chu?: string
}

/** Tra BANG `cap_noi_duoc`. Kieu la khong co trong bang ⇒ tu choi, khong doan
 *  bang tien to/hau to. Thu tu kiem giong `he_kieu.noi_duoc()`: kieu truoc,
 *  suc chua sau. */
export function noiDuoc(luat: LuatNoiDay, kieuRa: string, kieuVao: string,
                        soCanhDangCo: number, nhanNhieuCanh: boolean): boolean {
  const hop = luat.cap_noi_duoc.some(([a, b]) => a === kieuRa && b === kieuVao)
  if (!hop) return false
  return nhanNhieuCanh || soCanhDangCo < 1
}

export function timNut(nhom: NhomPalette[], type: string): NodeDefinition|undefined {
  for (const n of nhom) {
    const found = n.nut.find(x => x.type === type)
    if (found) return found
  }
  return undefined
}

export function locPalette(nhom: NhomPalette[], truyVan: string): NhomPalette[] {
  const q = truyVan.trim().toLocaleLowerCase('vi')
  if (!q) return nhom
  return nhom
    .map(n => ({ category: n.category, nut: n.nut.filter(x =>
      [x.title, x.description, x.type, x.app_name]
        .some(s => s.toLocaleLowerCase('vi').includes(q))) }))
    .filter(n => n.nut.length > 0)
}
