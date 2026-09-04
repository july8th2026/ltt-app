import { describe, expect, it } from 'vitest'
import {
  anhEm, chuCuaThongDiep, dungCay, duongToiLa, laKhiChuyenNhanh, suyLuanCuaThongDiep,
} from '../src/cay'
import type { ThongDiep } from '../src/kieu'

function m(
  id: string, parent: string | null, giay: number,
  g: Partial<ThongDiep> = {},
): ThongDiep {
  return {
    id,
    parent_id: parent,
    role: id.startsWith('u') ? 'user' : 'assistant',
    blocks: [{ type: 'text', text: id }],
    status: 'done',
    model_alias: 'ltt_llm',
    execution_id: null,
    created_at: `2026-09-03T00:00:${String(giay).padStart(2, '0')}.000000+00:00`,
    ...g,
  }
}

//  u1 ─ a1 ─┬─ u2 ─┬─ a2
//           │      └─ a2b
//           └─ u2c ── a2c
const CAY = [
  m('u1', null, 1), m('a1', 'u1', 2),
  m('u2', 'a1', 3), m('a2', 'u2', 4), m('a2b', 'u2', 5),
  m('u2c', 'a1', 6), m('a2c', 'u2c', 7),
]

describe('dungCay', () => {
  it('dung dung du danh sach bi xao tron — cha den sau khong lam con len goc', () => {
    for (const phang of [CAY, [...CAY].reverse(), [CAY[6], CAY[0], CAY[3], CAY[1], CAY[5], CAY[2], CAY[4]]]) {
      const rung = dungCay(phang)
      expect(rung.map((n) => n.message.id)).toEqual(['u1'])
      const a1 = rung[0].children[0]
      expect(a1.message.id).toBe('a1')
      expect(a1.depth).toBe(1)
      expect(a1.children.map((c) => c.message.id)).toEqual(['u2', 'u2c'])
      expect(a1.children.map((c) => c.siblingIndex)).toEqual([0, 1])
      expect(a1.children[0].siblingCount).toBe(2)
      expect(a1.children[0].children.map((c) => c.message.id)).toEqual(['a2', 'a2b'])
      expect(a1.children[0].children[1].depth).toBe(3)
    }
  })

  it('cha vang mat thi nut len goc, khong bien mat', () => {
    const rung = dungCay([m('b', 'khong-co', 2), m('a', null, 1)])
    expect(rung.map((n) => n.message.id)).toEqual(['a', 'b'])
  })

  it('cung created_at thi sap theo id — thu tu on dinh giua hai lan ve', () => {
    const rung = dungCay([m('a2', 'x', 5), m('a1', 'x', 5), m('x', null, 1)])
    expect(rung[0].children.map((n) => n.message.id)).toEqual(['a1', 'a2'])
  })
})

describe('duongToiLa', () => {
  it('tra goc -> la theo dung nhanh', () => {
    expect(duongToiLa(CAY, 'a2b').map((x) => x.id)).toEqual(['u1', 'a1', 'u2', 'a2b'])
    expect(duongToiLa(CAY, 'a2c').map((x) => x.id)).toEqual(['u1', 'a1', 'u2c', 'a2c'])
  })

  it('la khong co / null ⇒ rong', () => {
    expect(duongToiLa(CAY, null)).toEqual([])
    expect(duongToiLa(CAY, 'khong-co')).toEqual([])
  })

  it('vong lap khong lam treo', () => {
    const vong = [m('a', 'b', 1), m('b', 'a', 2)]
    expect(duongToiLa(vong, 'a').length).toBe(2)
  })
})

describe('anhEm + laKhiChuyenNhanh', () => {
  it('anh em la cac nut cung cha, da sap xep', () => {
    expect(anhEm(CAY, CAY[3]).map((x) => x.id)).toEqual(['a2', 'a2b'])
    expect(anhEm(CAY, CAY[0]).map((x) => x.id)).toEqual(['u1'])
  })

  it('chuyen nhanh tra ve LA cua nhanh do, di theo con cuoi cung', () => {
    expect(laKhiChuyenNhanh(CAY, CAY[2], 1)).toBe('a2c')   // u2 -> u2c -> a2c
    expect(laKhiChuyenNhanh(CAY, CAY[5], 0)).toBe('a2b')   // u2c -> u2 -> con cuoi
    expect(laKhiChuyenNhanh(CAY, CAY[3], 1)).toBe('a2b')
    expect(laKhiChuyenNhanh(CAY, CAY[3], 9)).toBeNull()
  })
})

describe('chu hien thi', () => {
  it('dang chay thi lay partial cua execution, khong lay blocks', () => {
    const dang = m('a9', 'u1', 9, {
      status: 'streaming',
      blocks: [],
      execution_id: 'ex1',
      execution: {
        id: 'ex1', status: 'streaming', mode: 'stream', tool_name: 'text.chat',
        partial_text: 'dang viet', reasoning_text: 'nghi', finish_reason: '',
        usage: {}, credit: { giu: 3, thu: 0, hoan: 0 },
        error_code: '', error_text: '', job_id: null, seq: 2,
      },
    })
    expect(chuCuaThongDiep(dang)).toBe('dang viet')
    expect(suyLuanCuaThongDiep(dang)).toBe('nghi')
  })

  it('xong thi lay blocks', () => {
    const xong = m('a8', 'u1', 8, {
      blocks: [{ type: 'reasoning', text: 'nghi ky' }, { type: 'text', text: 'tra loi' }],
    })
    expect(chuCuaThongDiep(xong)).toBe('tra loi')
    expect(suyLuanCuaThongDiep(xong)).toBe('nghi ky')
  })
})
