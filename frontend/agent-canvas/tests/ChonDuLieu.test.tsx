// Bo chon du lieu (§7) — lan UI-6. Bon nhom menh de, moi nhom mot loi DO DUOC
// tren trinh duyet that 28/09 (ghi trong bao cao lan): cay chi hien BUOC
// DUNG TRUOC (theo `goiY.muc` ma may chu da loc), bam mot la CHEN dung bieu
// thuc vao O DICH dang chon, va "chua co gi de chon" phai NOI RO chu khong
// ve mot cay rong.
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ChonDuLieu } from '../src/inspector/ChonDuLieu'
import type { CanvasEdge, CanvasNode, GoiYBieuThuc } from '../src/workflowApi'
import type { LuocDo } from '../src/nodeDefinition'

afterEach(cleanup)

const LUOC_DO: LuocDo = {
  type: 'object', required: [], additionalProperties: false,
  properties: {
    prompt: { type: 'string' },
    so_luong: { type: 'integer' },
    bat_am_thanh: { type: 'boolean' },
    mode: { type: 'string', enum: ['a', 'b'] },
  },
}

const NODES: CanvasNode[] = [
  { id: 'n1', type: 'tool', position: { x: 0, y: 0 }, label: 'Tạo ảnh AI', data: {} },
  { id: 'n2', type: 'tool', position: { x: 0, y: 0 }, data: {} }, // khong label -> dung id
  { id: 'nA', type: 'tool', position: { x: 0, y: 0 }, label: 'Node A', data: {} },
]

const GOI_Y_CO_TO_TIEN: GoiYBieuThuc = {
  node_id: 'nA',
  ham: [],
  loi: null,
  muc: [
    { duong: 'trigger', loai: 'goc', qua_publish: true },
    { duong: 'workflow', loai: 'goc', qua_publish: true },
    { duong: 'nodes.n1.output.image_keys', loai: 'cong', node: 'n1', cong: 'image_keys',
      node_type: 'image.generate', qua_publish: true },
    { duong: 'nodes.n1.output.prompt', loai: 'cong', node: 'n1', cong: 'prompt',
      node_type: 'image.generate', qua_publish: false },
    { duong: 'nodes.n1.status', loai: 'mat_node', node: 'n1', cong: '',
      node_type: 'image.generate', qua_publish: true },
    { duong: 'nodes.n1.error', loai: 'mat_node', node: 'n1', cong: '',
      node_type: 'image.generate', qua_publish: true },
    { duong: 'nodes.n2.output.text', loai: 'cong', node: 'n2', cong: 'text',
      node_type: 'core.set', qua_publish: true },
    { duong: 'nodes.n2.status', loai: 'mat_node', node: 'n2', cong: '',
      node_type: 'core.set', qua_publish: true },
    { duong: 'nodes.n2.error', loai: 'mat_node', node: 'n2', cong: '',
      node_type: 'core.set', qua_publish: true },
  ],
}

const EDGES_CO_DAY: CanvasEdge[] = [{ id: 'e1', source: 'n1', target: 'nA' }]

function veCay(ghiDe: Partial<React.ComponentProps<typeof ChonDuLieu>> = {}) {
  const onChen = ghiDe.onChen ?? vi.fn()
  const utils = render(<ChonDuLieu buocId="nA" nodes={NODES} edges={EDGES_CO_DAY}
    goiY={GOI_Y_CO_TO_TIEN} luocDo={LUOC_DO} giaTri={{}} onChen={onChen} {...ghiDe} />)
  return { ...utils, onChen }
}

describe('cay chi hien BUOC DUNG TRUOC, khong phai moi buoc', () => {
  it('nhom theo NHAN cua buoc (label neu co, id neu khong)', () => {
    veCay()
    expect(screen.getByText('Tạo ảnh AI')).toBeInTheDocument()
    expect(screen.getByText('n2')).toBeInTheDocument()
    // ⛔ "Node A" la CHINH buoc dang chon (khong phai to tien cua no) — no
    //    khong duoc xuat hien nhu mot nhom du lieu.
    expect(screen.queryByText('Node A')).toBeNull()
  })

  it('cong cua buoc truoc ra dung TEN CONG, kem loai buoc lam phu', () => {
    veCay()
    const nut = screen.getByRole('button', { name: /image_keys/ })
    expect(nut).toHaveAttribute('title', 'nodes.n1.output.image_keys')
    expect(nut.textContent).toContain('image.generate')
  })

  it('goc namespace (trigger, workflow…) luon ra du khong co to tien', () => {
    veCay()
    expect(screen.getByText('Trigger')).toBeInTheDocument()
    expect(screen.getByText('Đầu vào workflow')).toBeInTheDocument()
  })

  it('la CHUA qua duoc cong publish mang canh bao', () => {
    veCay()
    const nutHong = screen.getByRole('button', { name: /prompt/ })
    expect(nutHong.className).toContain('chua-publish-duoc')
    expect(nutHong).toHaveTextContent('chưa publish được')
    const nutOn = screen.getByRole('button', { name: /image_keys/ })
    expect(nutOn.className).not.toContain('chua-publish-duoc')
  })
})

describe('bam mot la ⇒ CHEN dung bieu thuc vao O DICH dang chon', () => {
  it('o rong: chen `{{ duong }}` nguyen', () => {
    const { onChen } = veCay()
    fireEvent.change(screen.getByLabelText('Chèn vào ô'), { target: { value: 'prompt' } })
    fireEvent.click(screen.getByRole('button', { name: /image_keys/ }))
    expect(onChen).toHaveBeenCalledWith('prompt', '{{ nodes.n1.output.image_keys }}')
  })

  it('o da co chu: NOI THEM, khong ghi de', () => {
    const { onChen } = veCay({ giaTri: { prompt: 'Vẽ một' } })
    fireEvent.change(screen.getByLabelText('Chèn vào ô'), { target: { value: 'prompt' } })
    fireEvent.click(screen.getByRole('button', { name: /image_keys/ }))
    expect(onChen).toHaveBeenCalledWith('prompt', 'Vẽ một {{ nodes.n1.output.image_keys }}')
  })

  it('o dich CHI liet ke truong nhan duoc bieu thuc — bo enum va boolean', () => {
    veCay()
    const chon = screen.getByLabelText('Chèn vào ô') as HTMLSelectElement
    const cacTuyChon = [...chon.options].map(o => o.value)
    expect(cacTuyChon).toEqual(['prompt', 'so_luong'])
    expect(cacTuyChon).not.toContain('mode')
    expect(cacTuyChon).not.toContain('bat_am_thanh')
  })

  it('readOnly: la khoa, khong chen duoc', () => {
    const { onChen } = veCay({ readOnly: true })
    const nut = screen.getByRole('button', { name: /image_keys/ })
    expect(nut).toBeDisabled()
    fireEvent.click(nut)
    expect(onChen).not.toHaveBeenCalled()
  })
})

describe('`goiY` chua ve (undefined) la DANG TAI, ⛔ khong phai "khong co gi"', () => {
  // ⚠️ Do duoc tren trinh duyet that (28/09): `useExpressionSuggest` doi mot
  //    debounce 200ms + mot chuyen may chu. Gop trang thai nay voi "khong co
  //    to tien" lam mot phep do dem QUA SOM luon thay 0 — dung hinh dang "hai
  //    trang thai gop thanh mot gia tri".
  it('hien mot cau DANG TAI, ⛔ khong phai cau "chua co bước nào đứng trước"', () => {
    veCay({ goiY: undefined })
    expect(screen.getByText('Đang tải dữ liệu dùng được…')).toBeInTheDocument()
    expect(screen.queryByText(/chưa có bước nào đứng trước/)).toBeNull()
    expect(screen.queryByText('Bước trước')).toBeNull()
  })
})

describe('`goiY` cua BUOC KHAC (hook dung chung chua kip xoa) bi COI LA CHUA VE', () => {
  // ⚠️ Do duoc tren trinh duyet that (28/09): `useExpressionSuggest` khong xoa
  //    `goiY` khi doi `selectedNodeId`, chi ghi de khi ban moi ve. Chon buoc B
  //    (co to tien) roi bam sang buoc A (khong co to tien) trong luc goi-y cua
  //    A con dang bay: mot nhip ngan cay se hien NHAM ket qua cua B cho A neu
  //    khong tu kiem `node_id`.
  it('goiY.node_id KHAC buocId dang chon ⇒ xu ly nhu dang tai, ⛔ khong dung do lieu cu', () => {
    veCay({ buocId: 'n1', edges: [], goiY: GOI_Y_CO_TO_TIEN /* node_id: 'nA', khong phai 'n1' */ })
    expect(screen.getByText('Đang tải dữ liệu dùng được…')).toBeInTheDocument()
    expect(screen.queryByText('Tạo ảnh AI')).toBeNull()
  })
})

describe('CHUA co gi de chon phai NOI RO, ⛔ khong ve cay rong', () => {
  it('buoc dau tien (khong day vao): cau ro rang, khong phai "Bước trước" rong', () => {
    veCay({ buocId: 'n1', edges: [], goiY: { node_id: 'n1', ham: [], loi: null,
      muc: [{ duong: 'trigger', loai: 'goc', qua_publish: true }] } })
    expect(screen.queryByText('Bước trước')).toBeNull()
    expect(screen.getByText(/chưa có bước nào đứng trước/)).toBeInTheDocument()
  })

  it('do thi chua bien dich duoc: hien ro loi, khong phai mot cay im lang', () => {
    veCay({ goiY: { node_id: 'nA', ham: [], muc: [{ duong: 'trigger', loai: 'goc', qua_publish: true }],
      loi: { ma: 'chu_trinh', thong_diep: 'Đồ thị có chu trình.' } } })
    expect(screen.getByText(/Đồ thị có chu trình\./)).toBeInTheDocument()
    expect(screen.queryByText('Bước trước')).toBeNull()
    expect(screen.queryByText(/chưa có bước nào đứng trước/)).toBeNull()
  })
})

describe('tim kiem loc cay', () => {
  it('go ten cong: chi con la khop, nhom cha van hien de biet no thuoc buoc nao', () => {
    veCay()
    fireEvent.change(screen.getByLabelText('Tìm dữ liệu'), { target: { value: 'image_keys' } })
    expect(screen.getByText('Tạo ảnh AI')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /prompt/ })).toBeNull()
    expect(screen.queryByText('Trigger')).toBeNull()
  })

  it('go dung ten mot buoc: hien HET cong cua buoc do', () => {
    veCay()
    fireEvent.change(screen.getByLabelText('Tìm dữ liệu'), { target: { value: 'Tạo ảnh AI' } })
    expect(screen.getByRole('button', { name: /image_keys/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /prompt/ })).toBeInTheDocument()
    expect(screen.queryByText('n2')).toBeNull()
  })
})
