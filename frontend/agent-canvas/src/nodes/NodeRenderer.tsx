// Mot component cho MOI node; `kind` chon phan than (spec §13.2).
import type { NodeProps } from '@xyflow/react'
import type { ReactElement } from 'react'
import type { NodeDefinition, NodeKind } from '../nodeDefinition'
import { NodeKhung } from './NodeKhung'

export type DuLieuNode = { dinhNghia: NodeDefinition; trangThai?: string
                           params?: Record<string, unknown> }

function ThanApp({ d }: { d: NodeDefinition }) {
  return <p className="node-mo-ta">{d.app_name}</p>
}

function ThanControl({ d }: { d: NodeDefinition }) {
  // Node dieu khien: nhieu cong ra co TEN NHANH — ten do da nam o `cong_ra`,
  // nen phan than chi noi so nhanh.
  return <p className="node-mo-ta">{d.cong_ra.length} nhánh</p>
}

function ThanSubworkflow({ d }: { d: NodeDefinition }) {
  return <p className="node-mo-ta">{d.title} · v{d.type_version}</p>
}

const THAN: Record<NodeKind, (p: { d: NodeDefinition }) => ReactElement> = {
  trigger: ({ d }) => <p className="node-mo-ta">{d.description}</p>,
  control: ThanControl,
  data: ({ d }) => <p className="node-mo-ta">{d.description}</p>,
  app: ThanApp,
  ai: ThanApp,
  connector: ThanApp,
  subworkflow: ThanSubworkflow,
}

export function NodeRenderer({ data }: NodeProps) {
  const { dinhNghia, trangThai } = data as unknown as DuLieuNode
  const Than = THAN[dinhNghia.kind] ?? THAN.data
  return <NodeKhung dinhNghia={dinhNghia} trangThai={trangThai}>
    <Than d={dinhNghia} />
  </NodeKhung>
}

export const NODE_TYPES = { ltt: NodeRenderer }
