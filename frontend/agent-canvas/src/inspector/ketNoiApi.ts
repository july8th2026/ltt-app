// Cua HTTP cua KET NOI (lan UI-5). May chu: `apps/agent/routes/ket_noi_v3.py`.
//
// ⛔ KHONG mot bang ten nha cung cap nao o day. Ma nha cung cap, kieu xac
//    thuc, TEN KHOA bi mat cua tung kieu va trang thai tang cloud deu tai tu
//    `/agent/api/v3/ket-noi/nha-cung-cap` — dung ly do `test_967` ton tai:
//    mot bang trong frontend troi khoi thuc te va khong gi bao.
//
// ⭐ MOT diem goi `fetch` tho, y het `workflowApi.ts`: `Accept:
//    application/json` phai co o MOI loi goi, khong phu thuoc header nao song
//    sot qua Cloudflare (su co `da7fce81`).

/** Mot ket noi, BE MAT AN TOAN: `preview` (4 ky tu cuoi) + `meta` cong khai.
 *  ⛔ `bi_mat_ma_hoa` khong bao gio ra tới đây — xem `credential.liet_ke`. */
export type KetNoi = {
  id: string
  kieu: string
  nha_cung_cap: string
  ten: string
  preview: string
  pham_vi: string[]
  meta: Record<string, unknown>
  het_han_luc: string | null
  thu_hoi_luc: string | null
  dung_lan_cuoi: string | null
  created_at: string | null
}

/** Mot nha cung cap + trang thai tang `cloud` cua no.
 *  `san_sang=false` kem `ly_do='chua_cau_hinh'` nghia la LTT chua dang ky OAuth
 *  app — ⛔ giao dien phai noi thang ra, khong duoc mo mot luong gia vo chay. */
export type NhaCungCap = {
  ma: string
  kieu: string[]
  node_type: string[]
  co_tang_cloud: boolean
  san_sang: boolean
  ly_do: string
  bien_moi_truong: string[]
}

/** Mot o cua form tao ket noi. `nhan` den TU MAY CHU (spec §6 luat 3) — ⛔ khong
 *  mot bang nhan nao trong frontend. */
export type OBiMat = {
  ten: string
  nhan: string
  che: boolean
  nhieu_dong: boolean
}

export type SoNhaCungCap = {
  tang: string[]
  kieu: string[]
  /** `kieu -> cac o bi mat BAT BUOC`. Form tao ket noi sinh HOAN TOAN tu day. */
  khoa_bi_mat: Record<string, OBiMat[]>
  nha_cung_cap: NhaCungCap[]
}

const DUONG = '/agent/api/v3/ket-noi'

function goi(path: string, init?: RequestInit): Promise<Response> {
  return fetch(path, {
    credentials: 'same-origin',
    ...init,
    headers: { Accept: 'application/json', ...(init?.headers ?? {}) },
  })
}

/** Loi may chu tra o `{ma, thong_diep}` — giu `ma` de giao dien noi dung cau.
 *  Mot chuoi thuan thi khong phan biet duoc `cloud_chua_cau_hinh` (mot trang
 *  thai binh thuong) voi `bi_mat_sai_hinh_dang` (nguoi dung go thieu). */
export class LoiKetNoi extends Error {
  ma: string
  bienMoiTruong: string[]
  constructor(thongDiep: string, ma: string, bienMoiTruong: string[] = []) {
    super(thongDiep)
    this.name = 'LoiKetNoi'
    this.ma = ma
    this.bienMoiTruong = bienMoiTruong
  }
}

async function doc(res: Response) {
  if (res.ok) return res.status === 204 ? null : res.json()
  let detail: unknown
  try { detail = (await res.json()).detail } catch { /* khong phai JSON */ }
  const obj = (detail && typeof detail === 'object' && !Array.isArray(detail))
    ? detail as { ma?: string; thong_diep?: string; bien_moi_truong?: string[] }
    : null
  if (obj) throw new LoiKetNoi(obj.thong_diep ?? obj.ma ?? '', obj.ma ?? '',
                               obj.bien_moi_truong ?? [])
  throw new LoiKetNoi(typeof detail === 'string' ? detail
    : `Không gọi được máy chủ (${res.status})`, '')
}

/** Ket noi cua chinh nguoi dang dang nhap, LOC theo kieu ma buoc nay nhan.
 *  ⭐ Loc o MAY CHU: o chon khong bao gio duoc moi mot ket noi ma cong publish
 *     se tu choi (`credential.kiem_ref` doi `kieu` nam trong node). */
export async function taiKetNoi(kieu: string[] = []): Promise<KetNoi[]> {
  const q = kieu.length ? `?kieu=${encodeURIComponent(kieu.join(','))}` : ''
  const raw = await doc(await goi(`${DUONG}${q}`))
  return (raw?.items ?? []) as KetNoi[]
}

export async function taiSoNhaCungCap(): Promise<SoNhaCungCap> {
  return await doc(await goi(`${DUONG}/nha-cung-cap`)) as SoNhaCungCap
}

export type ThanTaoKetNoi = {
  kieu: string
  ten: string
  nha_cung_cap?: string
  tang?: string
  /** `ten khoa -> gia tri`. ⛔ KHONG log, ⛔ khong dua vao `meta`. */
  bi_mat: Record<string, string>
  pham_vi?: string[]
}

export async function taoKetNoi(than: ThanTaoKetNoi,
                                csrfToken: string): Promise<KetNoi> {
  return await doc(await goi(DUONG, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
    body: JSON.stringify({ ...than, csrf_token: csrfToken }),
  })) as KetNoi
}

/** Thu hoi = XOA bi mat o may chu. Hang o lai (bang chung mot run da dung gi).
 *  ⛔ Ket noi cua tai khoan khac tra 404, khong 403. */
export async function thuHoiKetNoi(id: string,
                                   csrfToken: string): Promise<void> {
  await doc(await goi(`${DUONG}/${encodeURIComponent(id)}`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
    body: JSON.stringify({ csrf_token: csrfToken }),
  }))
}
