// `tinhDiffThietKe` — phần THUẦN của UI-8b (vá B7). Không React, không mạng:
// vào hai `CanvasDocument`, ra đếm + tên bước. Xem chú thích trong
// `src/features/editor/DesignerDiff/diff.ts` cho lý do so khớp theo `id`.
import { describe, expect, it } from 'vitest'
import { tinhDiffThietKe } from '../src/features/editor/DesignerDiff/diff'
import type { BangDinhNghia } from '../src/features/editor/graph'
import type { CanvasDocument, CanvasNode } from '../src/workflowApi'
import type { NodeDefinition } from '../src/nodeDefinition'

function dinhNghiaGia(type: string, title: string): NodeDefinition {
  return { type, type_version: 1, kind: 'data', category: 'DATA', title,
    description: '', icon: '', app_name: '', cong_vao: [], cong_ra: [],
    tham_so: { type: 'object', properties: {}, required: [] },
    thi_hanh: 'job', side_effect: '', resource: {}, timeout_expr: '',
    retry_mac_dinh: { max: 0, backoff_s: 0 },
    gia: { kieu: 'mien_phi', so: 0, job_type: '' },
    credential: [], quyen: [], cho: [], ma_loi: [], co_mock: false, publish_duoc: true }
}

// `data.tool` la SLUG (`image.generate`), khoa cua BangDinhNghia cung la slug
// do — xem `dinhNghiaCua` trong `graph.ts`.
const BANG: BangDinhNghia = new Map([
  ['image.generate', dinhNghiaGia('app.image.generate', 'Tạo ảnh AI')],
  ['video.generate', dinhNghiaGia('app.video.generate', 'Tạo video AI')],
  ['text.summarize', dinhNghiaGia('app.text.summarize', 'Tóm tắt văn bản')],
])

function nodeGia(id: string, tool: string, params: Record<string, unknown> = {}): CanvasNode {
  return { id, type: 'tool', position: { x: 0, y: 0 }, data: { tool, params } }
}

function taiLieu(nodes: CanvasNode[],
                 edges: { id: string; source: string; target: string }[] = []): CanvasDocument {
  return { version: 2, goal: 'g', budget_max_credit: 0, active_page_id: 'p1',
    pages: [{ id: 'p1', name: 'Trang 1', nodes, edges,
      viewport: { x: 0, y: 0, zoom: 1 }, frames: [], notes: [], comments: [] }] }
}

describe('tinhDiffThietKe', () => {
  it('không đổi gì ⇒ coThayDoi=false, mọi đếm bằng 0', () => {
    const doc = taiLieu([nodeGia('n1', 'image.generate', { prompt: 'a' })])
    const diff = tinhDiffThietKe(doc, doc, BANG)
    expect(diff.coThayDoi).toBe(false)
    expect(diff).toMatchObject({ soNodeThem: 0, soNodeXoa: 0, soNodeDoiThamSo: 0,
      soEdgeThem: 0, soEdgeXoa: 0 })
    expect(diff.nodes).toHaveLength(0)
  })

  it('node mới (id chỉ có ở tài liệu MỚI) ⇒ "them", tên lấy từ NodeDefinition — KHÔNG phải id thô', () => {
    const cu = taiLieu([nodeGia('n1', 'image.generate')])
    const moi = taiLieu([nodeGia('n1', 'image.generate'), nodeGia('nmukpruo1-1', 'video.generate')])
    const diff = tinhDiffThietKe(cu, moi, BANG)
    expect(diff.soNodeThem).toBe(1)
    expect(diff.nodes).toContainEqual({ id: 'nmukpruo1-1', ten: 'Tạo video AI', trangThai: 'them' })
    // Đại lượng đúng: tên hiển thị không phải id kỹ thuật.
    expect(diff.nodes.map(n => n.ten)).not.toContain('nmukpruo1-1')
  })

  it('node mất (id chỉ có ở tài liệu CŨ) ⇒ "xoa"', () => {
    const cu = taiLieu([nodeGia('n1', 'image.generate'), nodeGia('n2', 'text.summarize')])
    const moi = taiLieu([nodeGia('n1', 'image.generate')])
    const diff = tinhDiffThietKe(cu, moi, BANG)
    expect(diff.soNodeXoa).toBe(1)
    expect(diff.nodes).toContainEqual({ id: 'n2', ten: 'Tóm tắt văn bản', trangThai: 'xoa' })
  })

  it('cùng id, đổi params ⇒ "doi_tham_so"', () => {
    const cu = taiLieu([nodeGia('n1', 'image.generate', { prompt: 'a' })])
    const moi = taiLieu([nodeGia('n1', 'image.generate', { prompt: 'b' })])
    const diff = tinhDiffThietKe(cu, moi, BANG)
    expect(diff.soNodeDoiThamSo).toBe(1)
    expect(diff.nodes).toEqual([{ id: 'n1', ten: 'Tạo ảnh AI', trangThai: 'doi_tham_so' }])
  })

  it('cùng id, đổi LOẠI công cụ (data.tool) ⇒ cũng tính "doi_tham_so"', () => {
    const cu = taiLieu([nodeGia('n1', 'image.generate', { prompt: 'a' })])
    const moi = taiLieu([nodeGia('n1', 'video.generate', { prompt: 'a' })])
    const diff = tinhDiffThietKe(cu, moi, BANG)
    expect(diff.soNodeDoiThamSo).toBe(1)
  })

  it('cùng id, params bằng nhau (thứ tự khoá khác) ⇒ KHÔNG tính đổi', () => {
    const cu = taiLieu([nodeGia('n1', 'image.generate', { a: 1, b: 2 })])
    const moi = taiLieu([nodeGia('n1', 'image.generate', { b: 2, a: 1 })])
    const diff = tinhDiffThietKe(cu, moi, BANG)
    expect(diff.soNodeDoiThamSo).toBe(0)
    expect(diff.coThayDoi).toBe(false)
  })

  it('cạnh: thêm/xoá đếm riêng theo id, ⛔ không có hạng "đổi"', () => {
    const cu = taiLieu([nodeGia('a', 'image.generate'), nodeGia('b', 'text.summarize')],
      [{ id: 'a-out-b-in', source: 'a', target: 'b' }])
    const moi = taiLieu([nodeGia('a', 'image.generate'), nodeGia('b', 'text.summarize'),
      nodeGia('c', 'video.generate')],
      [{ id: 'a-out-c-in', source: 'a', target: 'c' }])
    const diff = tinhDiffThietKe(cu, moi, BANG)
    expect(diff.soEdgeThem).toBe(1)
    expect(diff.soEdgeXoa).toBe(1)
    expect(diff.edges).toContainEqual({ id: 'a-out-c-in', trangThai: 'them' })
    expect(diff.edges).toContainEqual({ id: 'a-out-b-in', trangThai: 'xoa' })
  })

  it('node trùng tên (không có label riêng) được đánh số như `nhanNode` — bất biến hiển thị dùng chung với phần còn lại của app', () => {
    const moi = taiLieu([nodeGia('x1', 'image.generate'), nodeGia('x2', 'image.generate')])
    const diff = tinhDiffThietKe(taiLieu([]), moi, BANG)
    const ten = diff.nodes.map(n => n.ten).sort()
    expect(ten).toEqual(['Tạo ảnh AI 1', 'Tạo ảnh AI 2'])
  })

  it('node không còn trong bảng định nghĩa (app bị gỡ quyền) ⇒ vẫn có tên đọc được, dùng slug thay vì rỗng', () => {
    const moi = taiLieu([nodeGia('n9', 'app.mat.roi')])
    const diff = tinhDiffThietKe(taiLieu([]), moi, BANG)
    expect(diff.nodes[0].ten).toBe('app.mat.roi')
  })
})
