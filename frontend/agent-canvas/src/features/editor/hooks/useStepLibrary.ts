import { useCallback, useState } from 'react'
import type { NodeDefinition } from '../../../nodeDefinition'

const KHOA_GAN_DAY = 'ltt.palette.ganDay'

/** Bảng node: ô tìm, và 8 `type` dùng gần đây nhất (spec §13.4).
 *
 *  ⛔ MOI lan doc/ghi `localStorage` deu boc `try`: no NEM (khong chi tra rong)
 *     trong cua so rieng tu / khi chan cookie ben thu ba. Mot canvas den vi mot
 *     danh sach goi y la mot cai gia khong ai tra.
 */
export function useStepLibrary() {
  const [paletteQuery, setPaletteQuery] = useState('')
  const [ganDay, setGanDay] = useState<string[]>(() => {
    try {
      const tho = localStorage.getItem(KHOA_GAN_DAY)
      return tho ? JSON.parse(tho) as string[] : []
    } catch { return [] }
  })

  const ghiNhanDaDung = useCallback((nd: NodeDefinition) => {
    setGanDay(cu => {
      const moi = [nd.type, ...cu.filter(t => t !== nd.type)].slice(0, 8)
      try { localStorage.setItem(KHOA_GAN_DAY, JSON.stringify(moi)) } catch { /* rieng tu */ }
      return moi
    })
  }, [])

  return { paletteQuery, setPaletteQuery, ganDay, ghiNhanDaDung }
}
