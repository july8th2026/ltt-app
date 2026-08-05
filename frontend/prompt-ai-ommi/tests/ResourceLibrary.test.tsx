import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { OmmiShell } from '../src/OmmiShell'

const emptyPage = {
  items: [], total: 0, limit: 40, offset: 0,
  counts: { character: 0, background: 0, prop: 0, vehicle: 0, misc: 0 },
  kinds: ['character', 'background', 'prop', 'vehicle', 'misc'],
}

const oneResource = {
  id: 'r1', kind: 'character', name: 'Nhân vật A', description: '',
  prompt_text: 'mo ta nhan vat', attributes: {}, cover_variant_id: '',
  is_catalog: false, archived: false, updated_at: '2026-08-05T00:00:00+00:00',
}

function reply(body: unknown, status = 200) {
  return Promise.resolve({
    ok: status < 400, status,
    json: () => Promise.resolve(body),
  } as Response)
}

let routes: Array<[RegExp, string, () => Promise<Response>]>
let seenUrls: string[]

beforeEach(() => {
  routes = []
  seenUrls = []
  vi.stubGlobal('fetch', vi.fn((url: string, init?: RequestInit) => {
    seenUrls.push(String(url))
    const method = (init?.method ?? 'GET').toUpperCase()
    for (const [pattern, wanted, handler] of routes) {
      if (pattern.test(String(url)) && wanted === method) return handler()
    }
    return reply({ detail: `khong co route ${method} ${url}` }, 404)
  }))
})

afterEach(() => { vi.unstubAllGlobals() })

describe('Kho tài nguyên', () => {
  it('bắt đầu ở Kho tài nguyên và chỉ cho bấm màn đã xây', async () => {
    routes.push([/\/resources\?/, 'GET', () => reply(emptyPage)])
    render(<OmmiShell csrfToken="t"/>)
    await waitFor(() => expect(screen.getByText('Kho còn trống')).toBeTruthy())

    const rail = screen.getByRole('navigation', { name: 'Điều hướng PROMPT AI OMMI' })
    expect(within(rail).getByRole('button', { name: /Kho tài nguyên/ })
      .hasAttribute('disabled')).toBe(false)
    // Màn chưa xây phải vô hiệu và nói rõ, không được là nút chết.
    const notBuilt = within(rail).getByRole('button', { name: /Tổng quan/ })
    expect(notBuilt.hasAttribute('disabled')).toBe(true)
    expect(notBuilt.textContent).toContain('đang xây')
  })

  it('hiện lưới tài nguyên kèm số đếm theo nhóm', async () => {
    routes.push([/\/resources\?/, 'GET', () => reply({
      ...emptyPage, items: [oneResource], total: 1,
      counts: { ...emptyPage.counts, character: 1 },
    })])
    render(<OmmiShell csrfToken="t"/>)
    await waitFor(() => expect(screen.getByText('Nhân vật A')).toBeTruthy())
    expect(screen.getByRole('button', { name: /Nhân vật\s*1/ })).toBeTruthy()
  })

  it('báo lỗi máy chủ bằng đúng thông báo máy chủ trả về', async () => {
    routes.push([/\/resources\?/, 'GET',
      () => reply({ detail: 'Phiên đã hết hạn — tải lại trang.' }, 400)])
    render(<OmmiShell csrfToken="t"/>)
    await waitFor(() => expect(screen.getByRole('alert').textContent)
      .toContain('Phiên đã hết hạn'))
  })

  it('mở panel chi tiết khi chọn một tài nguyên', async () => {
    routes.push([/\/resources\?/, 'GET', () => reply({
      ...emptyPage, items: [oneResource], total: 1 })])
    routes.push([/\/resources\/r1$/, 'GET', () => reply({
      ...oneResource, variants: [], tags: [] })])
    render(<OmmiShell csrfToken="t"/>)
    await waitFor(() => expect(screen.getByText('Nhân vật A')).toBeTruthy())
    fireEvent.click(screen.getByText('Nhân vật A'))
    await waitFor(() => expect(
      screen.getByRole('complementary', { name: /Chi tiết Nhân vật A/ })).toBeTruthy())
    expect(screen.getByLabelText(/Mô tả dùng khi ghép prompt/)).toBeTruthy()
  })

  it('hỏi giá trước và không chạy gì cho tới khi xác nhận', async () => {
    const calls: string[] = []
    routes.push([/\/resources\?/, 'GET', () => reply({
      ...emptyPage, items: [oneResource], total: 1 })])
    routes.push([/\/resources\/r1$/, 'GET', () => reply({
      ...oneResource, variants: [], tags: [] })])
    routes.push([/\/images\/generate$/, 'POST', () => {
      calls.push('generate')
      return reply({ credit: 6, count: 1, reference_count: 0, confirmed: false })
    }])

    render(<OmmiShell csrfToken="t"/>)
    await waitFor(() => expect(screen.getByText('Nhân vật A')).toBeTruthy())
    fireEvent.click(screen.getByText('Nhân vật A'))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Sinh ảnh bằng AI' })).toBeTruthy())
    fireEvent.click(screen.getByRole('button', { name: 'Sinh ảnh bằng AI' }))

    await waitFor(() => expect(screen.getByText('6 credit')).toBeTruthy())
    expect(screen.getByLabelText('Xác nhận chi phí').textContent)
      .toContain('Chưa trừ credit nào cho tới khi bạn xác nhận')
    // Mới hỏi giá đúng một lần; chưa có lần chạy nào.
    expect(calls).toEqual(['generate'])
  })

  it('lọc theo nhóm gọi lại API với đúng nhóm', async () => {
    routes.push([/\/resources\?/, 'GET', () => reply(emptyPage)])
    render(<OmmiShell csrfToken="t"/>)
    await waitFor(() => expect(screen.getByText('Kho còn trống')).toBeTruthy())
    fireEvent.click(screen.getByRole('button', { name: /Bối cảnh/ }))
    await waitFor(() => expect(seenUrls.some((u) => u.includes('kind=background'))).toBe(true))
    // Đổi nhóm phải quay về trang đầu, nếu không người dùng đang ở trang 3 sẽ
    // thấy một danh sách rỗng và tưởng nhóm đó không có gì.
    expect(seenUrls.at(-1)).toContain('offset=0')
  })
})

describe('Thư viện', () => {
  it('mở được ba màn thư viện và tải đúng loại', async () => {
    const empty = { items: [], total: 0, catalog: false, counts: {} }
    routes.push([/\/resources\?/, 'GET', () => reply(emptyPage)])
    routes.push([/\/library\/\w+\?/, 'GET', () => reply(empty)])
    render(<OmmiShell csrfToken="t"/>)
    await waitFor(() => expect(screen.getByText('Kho còn trống')).toBeTruthy())

    const rail = screen.getByRole('navigation', { name: 'Điều hướng PROMPT AI OMMI' })
    fireEvent.click(within(rail).getByRole('button', { name: /Meta Director/ }))
    await waitFor(() => expect(screen.getByText('Chưa có meta prompt nào')).toBeTruthy())
    expect(seenUrls.some((u) => u.includes('/library/meta'))).toBe(true)

    fireEvent.click(within(rail).getByRole('button', { name: /Phong cách/ }))
    await waitFor(() => expect(screen.getByText('Chưa có phong cách riêng')).toBeTruthy())
    expect(seenUrls.some((u) => u.includes('/library/style'))).toBe(true)
  })

  it('mẫu có sẵn là chỉ đọc và mời clone thay vì cho sửa', async () => {
    const item = { id: 'm1', kind: 'meta', name: 'Mẫu chung', body: 'noi dung mau',
      is_catalog: true, cloned_from_id: '', archived: false,
      updated_at: '2026-08-05T00:00:00+00:00' }
    routes.push([/\/resources\?/, 'GET', () => reply(emptyPage)])
    routes.push([/\/library\/meta\?/, 'GET',
      () => reply({ items: [item], total: 1, catalog: true, counts: {} })])
    routes.push([/\/library\/meta\/m1$/, 'GET', () => reply(item)])

    render(<OmmiShell csrfToken="t"/>)
    const rail = await screen.findByRole('navigation', { name: 'Điều hướng PROMPT AI OMMI' })
    fireEvent.click(within(rail).getByRole('button', { name: /Meta Director/ }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Mẫu có sẵn' })).toBeTruthy())
    fireEvent.click(screen.getByRole('button', { name: 'Mẫu có sẵn' }))
    await waitFor(() => expect(screen.getByText('Mẫu chung')).toBeTruthy())
    fireEvent.click(screen.getByText('Mẫu chung'))

    await waitFor(() => expect(screen.getByRole('button', { name: 'Dùng mẫu này' })).toBeTruthy())
    // Không được hiện ô sửa rồi mới từ chối lưu — người dùng gõ xong mới biết.
    const box = screen.getByLabelText(/Nội dung chỉ dẫn/) as HTMLTextAreaElement
    expect(box.readOnly).toBe(true)
    expect(screen.queryByRole('button', { name: /Lưu trữ/ })).toBeNull()
  })
})

describe('Storyboard', () => {
  const board = { id: 'b1', project_id: 'p1', name: 'Bảng', meta_prompt_id: '',
    style_id: '', aspect_ratio: '16:9', archived: false,
    updated_at: '2026-08-05T00:00:00+00:00' }
  const scene = { id: 's1', storyboard_id: 'b1', position: 0, title: 'Cảnh 1',
    prompt: 'noi dung canh', camera: '', continuity: '', resource_ids: [],
    image_key: '', version: 1 }

  function openStoryboard() {
    routes.push([/\/resources\?/, 'GET', () => reply(emptyPage)])
    // Đúng hình dạng máy chủ trả: {items: [...]}, không phải mảng trần.
    routes.push([/\/projects$/, 'GET',
      () => reply({ items: [{ id: 'p1', name: 'Dự án', revision: 1 }] })])
    routes.push([/\/storyboards$/, 'GET', () => reply({ items: [board] })])
    routes.push([/\/storyboards\/b1$/, 'GET',
      () => reply({ ...board, scenes: [scene] })])
  }

  it('nói rõ chạy lại một cảnh chỉ tính tiền cảnh đó', async () => {
    openStoryboard()
    routes.push([/\/scenes\/s1\/render$/, 'POST', () => reply({
      credit: 5, scene_id: 's1', reference_count: 0,
      prompt_preview: 'noi dung canh', confirmed: false })])

    render(<OmmiShell csrfToken="t"/>)
    const rail = await screen.findByRole('navigation', { name: 'Điều hướng PROMPT AI OMMI' })
    fireEvent.click(within(rail).getByRole('button', { name: /Storyboard/ }))
    await waitFor(() => expect(screen.getByText('Bảng')).toBeTruthy())
    fireEvent.click(screen.getByText('Bảng'))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Sinh ảnh' })).toBeTruthy())
    fireEvent.click(screen.getByRole('button', { name: 'Sinh ảnh' }))

    const box = await screen.findByLabelText('Xác nhận chi phí cảnh')
    expect(box.textContent).toContain('5 credit')
    expect(box.textContent).toContain('một cảnh')
    expect(box.textContent).toContain('Các cảnh khác không bị đụng tới')
  })

  it('hiện trạng thái rỗng có ích khi chưa có dự án', async () => {
    routes.push([/\/resources\?/, 'GET', () => reply(emptyPage)])
    routes.push([/\/projects$/, 'GET', () => reply({ items: [] })])
    routes.push([/\/storyboards$/, 'GET', () => reply({ items: [] })])

    render(<OmmiShell csrfToken="t"/>)
    const rail = await screen.findByRole('navigation', { name: 'Điều hướng PROMPT AI OMMI' })
    fireEvent.click(within(rail).getByRole('button', { name: /Storyboard/ }))
    await waitFor(() => expect(screen.getByText('Chưa có storyboard nào')).toBeTruthy())
    // Không có dự án thì không mời tạo storyboard — bấm vào sẽ chỉ ra lỗi.
    expect(screen.getByText(/Tạo một dự án ở trang PROMPT AI OMMI trước/)).toBeTruthy()
  })
})
