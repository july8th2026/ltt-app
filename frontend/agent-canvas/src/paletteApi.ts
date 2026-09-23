// Hai loi goi palette v3. Tach khoi `workflowApi.ts` CO CHU DICH: plan 01b
// dang viet lai tep do trong mot lan song song.
import type { LuatNoiDay, NhomPalette } from './nodeDefinition'

// `apps/agent/routes/palette_v3.py:palette_v3` tra dung ba khoa nay.
export type PaletteV3 = {
  phien_ban: number
  nhom: NhomPalette[]
  luat_noi_day: LuatNoiDay
}

async function doc<T>(duong: string): Promise<T> {
  const r = await fetch(duong, { credentials: 'same-origin' })
  if (!r.ok) throw new Error(`${duong} -> ${r.status}`)
  return (await r.json()) as T
}

export const taiPalette = () => doc<PaletteV3>('/agent/api/v3/palette')
export const taiLuatNoiDay = () => doc<LuatNoiDay>('/agent/api/v3/luat-noi-day')
