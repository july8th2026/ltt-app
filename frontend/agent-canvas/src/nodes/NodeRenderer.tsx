// Mot component cho MOI node; `kind` chon phan than (spec §13.2).
import { useStore, type NodeProps } from '@xyflow/react'
import { useMemo } from 'react'
import type { NodeDefinition } from '../nodeDefinition'
import { NodeKhung } from './NodeKhung'
import { mucDoNode, type MucDo } from './matDo'
import { tomTatCauHinh, type HuyHieu, type SucKhoe, type TomTatChay } from './tomTat'

export type DuLieuNode = {
  dinhNghia: NodeDefinition
  trangThai?: string
  params?: Record<string, unknown>
  /** Truc 1/2 + cong da noi + tom tat chay — `useDisplayGraph` tinh, vi chi no
   *  thay CA do thi va CA luot chay. Node khong duoc tu doan mot trong bon. */
  sucKhoe?: SucKhoe
  huyHieu?: HuyHieu[]
  congDaNoi?: string[]
  tomTatChay?: TomTatChay
  /** Ep muc do — CHI dung cho phep kiem va cho Storybook-kieu render. ⛔ Khong
   *  phai mot cong tac cho nguoi dung (`08_DECISION_QUESTIONS.md` Q7: mat do
   *  TU DONG theo zoom + trang thai chon, khong co cong tac tay). */
  mucDoEp?: MucDo
}

export function NodeRenderer({ data, selected }: NodeProps) {
  const d = data as unknown as DuLieuNode
  // ⭐ `transform[2]` la ZOOM cua React Flow. `useStore` dang ky dung mot o
  //    nay, nen node ve lai khi zoom doi — va CHI khi zoom doi.
  const zoom = useStore(s => s.transform[2])
  const mucDo = d.mucDoEp ?? mucDoNode({ zoom, dangChon: !!selected })
  const daNoi = useMemo(() => new Set(d.congDaNoi ?? []), [d.congDaNoi])
  const tomTat = tomTatCauHinh(d.dinhNghia, d.params)
  return <NodeKhung dinhNghia={d.dinhNghia} trangThai={d.trangThai}
    sucKhoe={d.sucKhoe} huyHieu={d.huyHieu} congDaNoi={daNoi}
    tomTatChay={d.tomTatChay} mucDo={mucDo}>
    {/* 🔴 MOT dong tom tat cho MOI `kind`, ⛔ khong con bang `THAN` bay nhanh.
        Bang cu cho `control` mot ham rieng in `{cong_ra.length} nhánh`, va do
        la mot phep dem SAI DAI LUONG: `core.stop` -> "0 nhánh" (no khong co
        cong ra — do la ca y nghia cua no), `core.switch` -> "1 nhánh" LUON
        LUON (ten nhanh nam trong tham so `nhanh: array`). `tomTat.soNhanh()`
        doc dung nguon, va tra `undefined` khi node khong re nhanh. */}
    {tomTat ? <p className="node-mo-ta" data-testid="node-tom-tat">{tomTat}</p> : null}
  </NodeKhung>
}

export const NODE_TYPES = { ltt: NodeRenderer }
