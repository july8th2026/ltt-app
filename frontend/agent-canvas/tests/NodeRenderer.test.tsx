import { cleanup, render, screen } from '@testing-library/react'
import { ReactFlowProvider } from '@xyflow/react'
import { afterEach, describe, expect, it } from 'vitest'
import { NodeRenderer } from '../src/nodes/NodeRenderer'
import type { NodeDefinition, NodeKind } from '../src/nodeDefinition'

afterEach(cleanup)

// ⚠️ `resource` chi con khoa `class`: `palette_v3.RESOURCE_CONG_KHAI = ("class",)`
//    da bo `vram_min_mb`/`slots`/`est_duration_s` (suc chua ha tang, khong phoi
//    ra trinh duyet). Node hien dau GPU TU `class`, khong tu con so VRAM.
const nd = (kind: NodeKind, over: Partial<NodeDefinition> = {}): NodeDefinition =>
  ({ type: `x.${kind}`, type_version: 2, kind, category: 'LTT_APPS',
     title: 'Sinh ảnh', description: 'mo ta', icon: 'I', app_name: 'Tạo ảnh AI',
     cong_vao: [{ ten: 'prompt', kieu: 'text', bat_buoc: true, nhieu: false }],
     cong_ra: [{ ten: 'image_keys', kieu: 'image[]', bat_buoc: true, nhieu: false }],
     tham_so: { type: 'object', properties: {}, required: [] }, thi_hanh: 'job',
     side_effect: 'external', resource: { class: 'gpu' },
     timeout_expr: '', retry_mac_dinh: { max: 0, backoff_s: 30 },
     gia: { kieu: 'theo_registry', so: 0, job_type: 'taoanh.generate' },
     credential: [], quyen: ['network', 'gpu'], cho: ['JOB'], ma_loi: [],
     co_mock: false, publish_duoc: true, ...over })

const ve = (dinhNghia: NodeDefinition, trangThai?: string) => render(
  <ReactFlowProvider>
    <NodeRenderer id="n1" type="ltt" selected={false} zIndex={0} isConnectable
      selectable deletable draggable
      positionAbsoluteX={0} positionAbsoluteY={0} dragging={false}
      data={{ dinhNghia, trangThai }} />
  </ReactFlowProvider>)

describe('NodeRenderer', () => {
  it('ve tieu de, type@version va cong co kieu tu dinh nghia', () => {
    ve(nd('app'))
    expect(screen.getByText('Sinh ảnh')).toBeInTheDocument()
    expect(screen.getByText('x.app@2')).toBeInTheDocument()
    expect(screen.getByTitle('prompt · text')).toBeInTheDocument()
    expect(screen.getByTitle('image_keys · image[]')).toBeInTheDocument()
  })

  it('node class gpu hien dau GPU; class khac hoac resource rong thi khong', () => {
    ve(nd('app'))
    const dau = screen.getByTestId('node-tai-nguyen')
    expect(dau).toHaveTextContent('GPU')
    expect(dau).toHaveAttribute('title', 'Tài nguyên: GPU')
    // Suc chua ha tang khong bao gio ra man hinh (vi du "6000 MB").
    expect(screen.queryByText(/\d{3,}\s*MB/)).not.toBeInTheDocument()
    cleanup()
    ve(nd('data', { resource: { class: 'cpu' }, quyen: ['network'] }))
    expect(screen.queryByTestId('node-tai-nguyen')).not.toBeInTheDocument()
    cleanup()
    ve(nd('data', { resource: {}, quyen: ['network'] }))
    expect(screen.queryByTestId('node-tai-nguyen')).not.toBeInTheDocument()
  })

  it('trigger khong ve cong vao', () => {
    ve(nd('trigger', { cong_vao: [] }))
    expect(screen.queryByTitle(/prompt/)).not.toBeInTheDocument()
    expect(screen.getByTestId('node-kind')).toHaveTextContent('trigger')
  })

  it('moi kind deu ve duoc, khong kind nao roi ra mot component rieng', () => {
    const kinds: NodeKind[] = ['trigger', 'control', 'data', 'app', 'ai',
                               'connector', 'subworkflow']
    for (const k of kinds) {
      ve(nd(k))
      expect(screen.getByTestId('node-kind')).toHaveTextContent(k)
      cleanup()
    }
  })

  it('connector thieu credential thi bao ra', () => {
    ve(nd('connector', { credential: ['oauth2'] }))
    expect(screen.getByText('Cần kết nối')).toBeInTheDocument()
  })

  it('node chua publish duoc thi danh dau va khong giau', () => {
    ve(nd('control', { publish_duoc: false }))
    expect(screen.getByText('Sắp có')).toBeInTheDocument()
  })

  it('huy hieu trang thai run hien khi co', () => {
    ve(nd('app'), 'RUNNING')
    expect(screen.getByTestId('node-trang-thai')).toHaveTextContent('RUNNING')
  })
})
