/**
 * Trình soạn mở ĐÚNG workflow mà TRANG yêu cầu — ⛔ không phải `items[0]`.
 *
 * 🔴 LỖI ĐÃ ĐO ĐƯỢC (`01_CURRENT_UI_AUDIT.md` §1.1). `loadOrCreateWorkflowV3`
 *    lấy `items[0]` của danh sách sắp `updated_at DESC`, và trình soạn **tự
 *    lưu** — nên workflow mở ra luôn là workflow sửa gần nhất. Cộng với việc
 *    giao diện cũ không có danh sách, sản phẩm **qua giao diện** là
 *    *một-workflow-một-tài-khoản*: backend giữ nhiều, giao diện không có cửa
 *    nào tới chúng.
 *
 * ⭐ HAI BÀI, VÌ MỘT BÀI KHÔNG ĐỦ
 *
 *    Bài 1 một mình xanh được bằng một hàm *"luôn gọi `loadWorkflowV3`"* —
 *    nhưng như thế lối vào không-id (`/agent/canvas`, `test_1726` chốt nó) sẽ
 *    gọi `GET /workflows/` với id rỗng và chết. Nên bài 2 là **vế đối chứng**:
 *    không có `data-workflow-id` thì đường cũ phải còn nguyên.
 *
 * ⛔ Bài này KHÔNG được xanh chỉ vì đường dẫn xuất hiện đâu đó trong mã: nó đo
 *    lời gọi `fetch` THẬT mà trình soạn phát ra khi nạp.
 */
import { render, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { NhomPalette } from '../src/nodeDefinition'

const paletteV3 = { phien_ban: 3, nhom: [] as NhomPalette[], luat_noi_day: {
  phien_ban: 2, kieu: ['text'], hau_to_tap_hop: '[]',
  cap_noi_duoc: [['text', 'text']] as [string, string][] } }

const tailieu = (id: string) => ({
  id, name: 'WF ' + id, published_version_id: '', revision: 1,
  document: { version: 3, goal: '', budget_max_credit: 0,
    active_page_id: 'page-1',
    pages: [{ id: 'page-1', name: 'Page 1', nodes: [], edges: [],
      viewport: { x: 0, y: 0, zoom: 1 }, frames: [], notes: [], comments: [],
      view: { grid: true, connections: true, minimap: true } }] } })

/** Danh sách CỐ Ý có hai mục, và mục đầu KHÁC mục ta yêu cầu: nếu trình soạn
 *  vẫn lấy `items[0]`, bài 1 đỏ với đúng cái id sai đó trong thông điệp. */
const DANH_SACH = { items: [
  { id: 'moi-nhat', name: 'WF moi-nhat', published: false },
  { id: 'w2', name: 'WF w2', published: false }] }

function gan(html: string) { document.body.innerHTML = html }

beforeEach(() => {
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input)
    if (url.endsWith('/v3/palette')) return new Response(JSON.stringify(paletteV3), { status: 200 })
    if (url.endsWith('/preferences')) return new Response(JSON.stringify({ theme: 'dark',
      catalog_mode: 'simple', presentation_version: 'creative-v1', revision: 0 }), { status: 200 })
    if (url.includes('/api/v3/workflows')) {
      if (init?.method === 'PUT') return new Response(JSON.stringify(tailieu('w2')), { status: 200 })
      if (url.endsWith('/workflows')) return new Response(JSON.stringify(DANH_SACH), { status: 200 })
      return new Response(JSON.stringify(tailieu(url.split('/').pop() ?? '')), { status: 200 })
    }
    return new Response('{}', { status: 200 })
  })
})

afterEach(() => { vi.restoreAllMocks(); document.body.innerHTML = '' })

/** Mọi URL đã `fetch`, theo thứ tự. */
const daGoi = () => vi.mocked(globalThis.fetch).mock.calls.map(([u]) => String(u))

describe('trang nói mở workflow nào', () => {
  it('có data-workflow-id ⇒ nạp ĐÚNG id đó, ⛔ không hỏi danh sách để chọn', async () => {
    gan('<div id="agent-canvas-root" data-csrf-token="t" data-workflow-id="w2"></div>')
    const { CanvasShell } = await import('../src/CanvasShell')
    render(<CanvasShell />)

    await waitFor(() => expect(daGoi().some(u => u.includes('/api/v3/workflows/w2')))
      .toBe(true), { timeout: 4000 })
    // ⛔ Và KHÔNG đi qua danh sách: `items[0]` là `moi-nhat`, nên một lời gọi
    //    danh sách ở đây nghĩa là quyết định vẫn nằm ở chỗ cũ.
    expect(daGoi().filter(u => u.endsWith('/api/v3/workflows'))).toEqual([])
    expect(daGoi().some(u => u.includes('/api/v3/workflows/moi-nhat'))).toBe(false)
  })

  it('KHÔNG có data-workflow-id ⇒ giữ đường cũ (danh sách rồi items[0])', async () => {
    gan('<div id="agent-canvas-root" data-csrf-token="t"></div>')
    const { CanvasShell } = await import('../src/CanvasShell')
    render(<CanvasShell />)

    await waitFor(() => expect(daGoi().some(u => u.endsWith('/api/v3/workflows')))
      .toBe(true), { timeout: 4000 })
    await waitFor(() => expect(daGoi().some(u => u.includes('/api/v3/workflows/moi-nhat')))
      .toBe(true), { timeout: 4000 })
  })
})
