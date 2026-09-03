/**
 * cay.ts — dung cay tu danh sach phang, va di theo mot nhanh. Ham THUAN.
 *
 * Ky thuat muon tu LibreChat v0.8.7 @ 9e74cc0 (MIT) — xem
 * `docs/CHATLTT/reports/01_librechat_tham_chieu.md` §1:
 *   · `buildTree` (`packages/data-provider/src/messages.ts:5-50`) — chi so anh
 *     em theo CHA, khong theo vi tri trong mang;
 *   · `selectActiveBranchTail` (`client/src/utils/messages.ts:29-58`) — di tu
 *     goc xuong theo chi so anh em da chon.
 *
 * ⭐ Hai cho co y KHAC ho, va ca hai deu la sua mot diem yeu da do duoc:
 *
 *   1. `dungCay` duyet HAI luot nen KHONG doi cha dung truoc con. `buildTree`
 *      cua ho duyet mot luot, nen mot cha den sau lam con bi day len goc —
 *      chinh cai "conversation folding" ma 5 test `convoStructure.spec.ts` cua
 *      ho ton tai de canh.
 *
 *   2. Chi so anh em o day dem tu 0 = CU NHAT. Cua ho dao nguoc (0 = moi nhat,
 *      `MultiMessage.tsx:42`), va quy uoc dao la mot cho de nham khi doc.
 */
import type { ThongDiep } from './kieu'

export type Nut = {
  message: ThongDiep
  children: Nut[]
  depth: number
  /** Vi tri trong danh sach anh em (cung `parent_id`), 0 = cu nhat. */
  siblingIndex: number
  siblingCount: number
}

function truoc(a: ThongDiep, b: ThongDiep): number {
  if (a.created_at !== b.created_at) return a.created_at < b.created_at ? -1 : 1
  return a.id < b.id ? -1 : a.id > b.id ? 1 : 0
}

/** Danh sach phang (BAT KY thu tu) -> rung. Cha vang mat ⇒ nut len goc. */
export function dungCay(phang: readonly ThongDiep[]): Nut[] {
  const nut = new Map<string, Nut>()
  for (const m of phang) {
    nut.set(m.id, { message: m, children: [], depth: 0, siblingIndex: 0, siblingCount: 0 })
  }
  const thuTu = [...phang].sort(truoc)
  const goc: Nut[] = []
  for (const m of thuTu) {
    const n = nut.get(m.id)!
    const cha = m.parent_id ? nut.get(m.parent_id) : undefined
    if (cha) cha.children.push(n)
    else goc.push(n)
  }
  const danh = (ds: Nut[], depth: number) => {
    ds.forEach((n, i) => {
      n.depth = depth
      n.siblingIndex = i
      n.siblingCount = ds.length
      danh(n.children, depth + 1)
    })
  }
  danh(goc, 0)
  return goc
}

/** Duong goc -> `leafId`. Rong khi khong tim thay la. */
export function duongToiLa(phang: readonly ThongDiep[], leafId: string | null): ThongDiep[] {
  if (!leafId) return []
  const theoId = new Map(phang.map((m) => [m.id, m]))
  const ra: ThongDiep[] = []
  const daQua = new Set<string>()
  let hien = theoId.get(leafId)
  while (hien && !daQua.has(hien.id)) {
    daQua.add(hien.id)
    ra.push(hien)
    hien = hien.parent_id ? theoId.get(hien.parent_id) : undefined
  }
  return ra.reverse()
}

/** Anh em cua mot thong diep (cung cha), da sap xep. */
export function anhEm(phang: readonly ThongDiep[], m: ThongDiep): ThongDiep[] {
  return phang.filter((x) => x.parent_id === m.parent_id).sort(truoc)
}

/**
 * La sau khi chuyen sang anh em thu `idx` cua `m`: di xuong theo con **cuoi
 * cung** o moi tang.
 *
 * ⭐ Con cuoi chu khong phai con dau: nguoi dung vua tao mot nhanh moi thi ho
 *    muon thay nhanh vua tao, khong phai nhanh dau tien tu nam ngoai.
 */
export function laKhiChuyenNhanh(
  phang: readonly ThongDiep[], m: ThongDiep, idx: number,
): string | null {
  const ds = anhEm(phang, m)
  const chon = ds[idx]
  if (!chon) return null
  let hien = chon
  for (;;) {
    const con = phang.filter((x) => x.parent_id === hien.id).sort(truoc)
    if (!con.length) return hien.id
    hien = con[con.length - 1]
  }
}

/** Van ban hien thi cua mot thong diep: gop moi khoi `text`. */
export function chuCuaThongDiep(m: ThongDiep): string {
  if (m.execution && (m.status === 'streaming' || m.status === 'queued')) {
    return m.execution.partial_text
  }
  return m.blocks.filter((k) => k.type === 'text').map((k) => k.text ?? '').join('\n\n')
}

/** Phan suy luan dang hien thi (dang chay thi lay tu execution). */
export function suyLuanCuaThongDiep(m: ThongDiep): string {
  if (m.execution && (m.status === 'streaming' || m.status === 'queued')) {
    return m.execution.reasoning_text
  }
  return m.blocks.filter((k) => k.type === 'reasoning').map((k) => k.text ?? '').join('\n\n')
}
