import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { DuyetNguoi } from '../src/features/editor/ExecutionPanel/DuyetNguoi'
import { nodeGia, runDuHinhDang, runGia, tenBuocGia } from './runGia'
import type { RunV3 } from '../src/workflowApi'

afterEach(() => { cleanup(); vi.restoreAllMocks() })

/** `DuyetNguoi` đọc CSRF từ `#agent-canvas-root` (cùng chỗ `EditorShell.tsx`
 *  đọc) — dựng đúng phần tử đó cho mỗi bài, giống DOM thật của trang Canvas. */
beforeEach(() => {
  const root = document.createElement('div')
  root.id = 'agent-canvas-root'
  root.dataset.csrfToken = 'csrf-duyet-thu'
  document.body.appendChild(root)
})

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status, headers: { 'Content-Type': 'application/json' } })
}

// ⭐ 28/09: `DuyetNguoi` ⛔ KHONG con nhan prop `thamSo` (nguon BAN NHAP). Cau
//    hoi duyet nay den tu CHINH payload cua run — `runs_v3` doc no tu
//    `version.graph`, ban DA GHIM ma dong co dang thi hanh.
//
// 🔴 Vi sao doi: ban nhap sua duoc trong luc run dang cho nguoi, nen doc tu ban
//    nhap cho phep chuoi nay — publish `"Dang bai nay len kenh chinh?"`, chay,
//    roi ai do sua ban nhap thanh `"Xoa toan bo playlist?"`, nguoi duyet doc cau
//    MOI va bam Duyet, dong co di nhanh `approve` cua ban CU. Ho dong y voi mot
//    cau hoi ho **chua tung duoc hoi**. Xem `tests/test_5605_*`.
//
// ⇒ Fixture nay gan `cau_hoi`/`het_han_che_do` vao dung NODE cua run, y nhu may
//   chu lam.
function ganCauHoi(run: RunV3, nodeId: string,
                   cau_hoi: string, het_han_che_do?: string): RunV3 {
  return { ...run, nodes: run.nodes.map(n =>
    n.node_id === nodeId ? { ...n, cau_hoi, het_han_che_do } : n) }
}
const CAU_HOI = 'Video này có đăng được không?'

describe('DuyetNguoi — chỉ hiện cho bước ĐANG chờ NGƯỜI', () => {
  it('bước WAITING + waiting_kind HUMAN có thẻ duyệt với câu hỏi', () => {
    render(<DuyetNguoi tenBuoc={tenBuocGia}
      run={ganCauHoi(runDuHinhDang(), 'n-video', CAU_HOI)}/>)
    const the = document.querySelector('[data-duyet-node="n-video"]')
    expect(the).toBeTruthy()
    expect(the!.textContent).toContain('Video này có đăng được không?')
    expect(screen.getByRole('button', { name: 'Duyệt' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Từ chối' })).toBeInTheDocument()
  })

  it('🔴 WAITING vì core.delay (waiting_kind=DELAY) KHÔNG hiện nút duyệt', () => {
    const run = runGia({ nodes: [
      nodeGia({ node_id: 'd1', status: 'WAITING', waiting_kind: 'DELAY' })] })
    render(<DuyetNguoi run={run} tenBuoc={tenBuocGia}/>)
    expect(document.querySelector('[data-duyet-node]')).toBeNull()
    expect(screen.queryByRole('button', { name: 'Duyệt' })).toBeNull()
  })

  it('WAITING vì core.wait (waiting_kind=WEBHOOK hoặc EVENT) cũng không hiện', () => {
    const run = runGia({ nodes: [
      nodeGia({ node_id: 'w1', status: 'WAITING', waiting_kind: 'WEBHOOK' }),
      nodeGia({ node_id: 'w2', status: 'WAITING', waiting_kind: 'EVENT' })] })
    render(<DuyetNguoi run={run} tenBuoc={tenBuocGia}/>)
    expect(document.querySelector('[data-duyet-node]')).toBeNull()
  })

  it('waiting_kind ghép "HUMAN,WEBHOOK" (N-of-M chưa đủ) VẪN hiện — không phải so `===`', () => {
    const run = runGia({ nodes: [
      nodeGia({ node_id: 'm1', status: 'WAITING', waiting_kind: 'HUMAN,WEBHOOK' })] })
    render(<DuyetNguoi run={run} tenBuoc={tenBuocGia}/>)
    expect(document.querySelector('[data-duyet-node="m1"]')).toBeTruthy()
  })

  it('run null hoặc không có bước nào WAITING+HUMAN ⇒ không vẽ gì', () => {
    const { container } = render(<DuyetNguoi run={null} tenBuoc={tenBuocGia}/>)
    expect(container.firstChild).toBeNull()
  })

  it('mặc định `het_han` (không khai `het_han` trong tham số) hiện đúng REJECT (spec §5.7)', () => {
    render(<DuyetNguoi run={runDuHinhDang()} tenBuoc={tenBuocGia}/>)
    expect(document.querySelector('[data-duyet-het-han]')!.textContent)
      .toContain('sẽ tự động TỪ CHỐI')
  })

  it('`het_han_che_do=route` hiện đúng câu "đi theo nhánh"', () => {
    // ⭐ Che do het han nay di kem NODE cua run (ban da ghim), khong con la mot
    //    prop `thamSo` doc tu ban nhap.
    render(<DuyetNguoi tenBuoc={tenBuocGia}
      run={ganCauHoi(runDuHinhDang(), 'n-video', CAU_HOI, 'route')}/>)
    expect(document.querySelector('[data-duyet-het-han]')!.textContent)
      .toContain('nhánh "hết hạn"')
  })
})

describe('DuyetNguoi — bấm nút gọi ĐÚNG cửa HTTP', () => {
  it('Duyệt: POST đúng URL, thân {quyet_dinh:"approve"}, header CSRF từ DOM', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(json({ ok: true }))
    render(<DuyetNguoi run={runDuHinhDang()} tenBuoc={tenBuocGia}/>)
    fireEvent.click(screen.getByRole('button', { name: 'Duyệt' }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1))
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/agent/api/v3/runs/r-gia/nodes/n-video/duyet')
    expect(init?.method).toBe('POST')
    expect(new Headers(init?.headers).get('X-CSRF-Token')).toBe('csrf-duyet-thu')
    expect(JSON.parse(String(init?.body))).toEqual(
      { quyet_dinh: 'approve', csrf_token: 'csrf-duyet-thu' })
  })

  it('Từ chối: thân mang "reject"', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(json({ ok: true }))
    render(<DuyetNguoi run={runDuHinhDang()} tenBuoc={tenBuocGia}/>)
    fireEvent.click(screen.getByRole('button', { name: 'Từ chối' }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1))
    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body)).quyet_dinh).toBe('reject')
  })

  it('trong lúc gửi, CẢ HAI nút của đúng thẻ đó bị khoá (chống bấm đúp)', async () => {
    let moKhoa: (() => void) | undefined
    vi.spyOn(globalThis, 'fetch').mockReturnValue(
      new Promise(resolve => { moKhoa = () => resolve(json({ ok: true })) }))
    render(<DuyetNguoi run={runDuHinhDang()} tenBuoc={tenBuocGia}/>)
    const nutDuyet = screen.getByRole('button', { name: 'Duyệt' })
    const nutTuChoi = screen.getByRole('button', { name: 'Từ chối' })
    fireEvent.click(nutDuyet)
    expect(screen.getByRole('button', { name: 'Đang gửi…' })).toBeDisabled()
    expect(nutTuChoi).toBeDisabled()
    moKhoa?.()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Duyệt' })).not.toBeDisabled())
  })

  it('máy chủ trả lỗi {detail:{thong_diep}} ⇒ hiện đúng câu đó, KHÔNG throw', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(json(
      { detail: { ma: 'da_het_han', thong_diep: 'Đã quá hạn chờ.' } }, 409))
    render(<DuyetNguoi run={runDuHinhDang()} tenBuoc={tenBuocGia}/>)
    fireEvent.click(screen.getByRole('button', { name: 'Duyệt' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Đã quá hạn chờ.')
    // Nút phải mở khoá lại sau khi lỗi về — người dùng còn thử lại được.
    expect(screen.getByRole('button', { name: 'Duyệt' })).not.toBeDisabled()
  })
})
