// Hai loi goi palette v3. Tach khoi `workflowApi.ts` CO CHU DICH: plan 01b
// dang viet lai tep do trong mot lan song song.
import type { LuatNoiDay, NhomPalette } from './nodeDefinition'

// `apps/agent/routes/palette_v3.py:palette_v3` tra dung ba khoa nay.
export type PaletteV3 = {
  phien_ban: number
  nhom: NhomPalette[]
  luat_noi_day: LuatNoiDay
}

// ⚠️ `Accept: application/json` TUONG MINH, cung ly do nhu `workflowApi
//    .apiFetch()`: ban sua `da7fce81` phan biet "goi API" voi "dieu huong
//    HTML" bang `Sec-Fetch-Mode`, lui ve `Accept`. Cloudflare lot ca hai thi
//    loi goi nay (Accept: */* mac dinh) bi coi la dieu huong va nhan 302 ve
//    `/login` — palette rong, Canvas trang, va phep do loopback (khong qua
//    Cloudflare) van xanh. Tu khi task 15 cat Canvas sang palette v3, day la
//    loi goi ma ca trinh soan phu thuoc vao.
async function doc<T>(duong: string): Promise<T> {
  const r = await fetch(duong, { credentials: 'same-origin',
                                 headers: { Accept: 'application/json' } })
  if (!r.ok) throw new Error(`${duong} -> ${r.status}`)
  return (await r.json()) as T
}

export const taiPalette = () => doc<PaletteV3>('/agent/api/v3/palette')
export const taiLuatNoiDay = () => doc<LuatNoiDay>('/agent/api/v3/luat-noi-day')
