import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { RunV3Panel } from '../src/RunV3Panel'
import type { RunV3 } from '../src/workflowApi'

afterEach(cleanup)

// P9 task 3 (🔴 + mở rộng waitpoint): một node bị đường thi hành BĂM không
// còn hiện "Chờ" (PENDING giả), và một node WAITING vì người duyệt phải đọc
// khác một node WAITING vì webhook -- xem `runs_v3.py::TRANG_THAI_KHONG_XAC_DINH`
// / `_waiting_kind`.
const runGoc = (nodes: RunV3['nodes']): RunV3 => ({
  id: 'r1', workflow_id: 'w1', version_id: 'v1', status: 'RUNNING',
  credit_max: 20, credit_charged: 4, settled: false,
  created_at: '2026-09-24T00:00:00+00:00', nodes,
  su_kien: [], seq_cuoi: 1,
})

describe('RunV3Panel — trạng thái node không được nói dối', () => {
  it('KHONG_XAC_DINH hiện nhãn riêng, KHÔNG hiện "Chờ"', () => {
    render(<RunV3Panel run={runGoc([
      { node_id: 'trong_foreach_sau', status: 'KHONG_XAC_DINH', attempt: 0,
        cost_credit: 0, job_id: '', error: 'khong gop duoc', waiting_kind: '', het_han: false },
    ])} onCancel={() => {}} />)
    const hang = document.querySelector('[data-node-status="KHONG_XAC_DINH"]')
    expect(hang).toBeTruthy()
    expect(hang!.textContent).toContain('Không xác định')
    expect(hang!.textContent).not.toContain('Chờ')
  })

  it('WAITING vì HUMAN đọc khác WAITING vì WEBHOOK', () => {
    render(<RunV3Panel run={runGoc([
      { node_id: 'duyet', status: 'WAITING', attempt: 1, cost_credit: 0,
        job_id: '', error: '', waiting_kind: 'HUMAN', het_han: false },
      { node_id: 'hook', status: 'WAITING', attempt: 1, cost_credit: 0,
        job_id: '', error: '', waiting_kind: 'WEBHOOK', het_han: false },
    ])} onCancel={() => {}} />)
    const duyet = document.querySelector('[data-node-status="WAITING"][data-waiting-kind="HUMAN"]')
    const hook = document.querySelector('[data-node-status="WAITING"][data-waiting-kind="WEBHOOK"]')
    expect(duyet).toBeTruthy(); expect(hook).toBeTruthy()
    expect(duyet!.textContent).toContain('chờ người duyệt')
    expect(hook!.textContent).toContain('chờ webhook')
    expect(duyet!.textContent).not.toEqual(hook!.textContent)
  })

  it('PENDING thường vẫn hiện "Chờ" như trước (không hồi quy)', () => {
    render(<RunV3Panel run={runGoc([
      { node_id: 'a', status: 'PENDING', attempt: 0, cost_credit: 0,
        job_id: '', error: '', waiting_kind: '', het_han: false },
    ])} onCancel={() => {}} />)
    expect(screen.getByText('Chờ')).toBeInTheDocument()
  })
})

// ── P-A task A4: trường quan sát ĐÃ CÓ dữ liệu, chưa hiện ─────────────────
describe('RunV3Panel — bắt đầu/kết thúc/thời lượng/attempt (task A4)', () => {
  it('hiện Bắt đầu ngay khi run CHƯA xong (chỉ có created_at)', () => {
    render(<RunV3Panel run={{ ...runGoc([]), status: 'RUNNING',
      created_at: '2026-09-24T00:00:00+00:00' }} onCancel={() => {}} />)
    expect(screen.getByText(/Bắt đầu 00:00:00/)).toBeInTheDocument()
    expect(screen.queryByText(/Kết thúc/)).toBeNull()
  })

  it('run XONG: hiện Kết thúc (theo sự kiện seq lớn nhất) và Thời lượng', () => {
    render(<RunV3Panel run={{ ...runGoc([]), status: 'SUCCEEDED',
      created_at: '2026-09-24T00:00:00+00:00',
      su_kien: [
        { seq: 1, loai: 'run.created', node_id: '', du_lieu: {},
          created_at: '2026-09-24T00:00:00+00:00' },
        { seq: 2, loai: 'run.succeeded', node_id: '', du_lieu: {},
          created_at: '2026-09-24T00:00:10+00:00' },
      ] }} onCancel={() => {}} />)
    expect(screen.getByText(/Bắt đầu 00:00:00/)).toBeInTheDocument()
    expect(screen.getByText(/Kết thúc 00:00:10/)).toBeInTheDocument()
    expect(screen.getByText(/10s/)).toBeInTheDocument()
  })

  it('cột attempt hiện "Lần N" cho từng node', () => {
    render(<RunV3Panel run={runGoc([
      { node_id: 'a', status: 'SUCCEEDED', attempt: 3, cost_credit: 1,
        job_id: 'j', error: '', waiting_kind: '', het_han: false },
    ])} onCancel={() => {}} />)
    expect(screen.getByText('Lần 3')).toBeInTheDocument()
  })
})

// ── P-A task A1: nút "Chạy lại từ đây" (spec §14) ──────────────────────────
describe('RunV3Panel — chạy lại từ một node (task A1)', () => {
  it('run CHƯA xong: KHÔNG hiện nút chạy lại', () => {
    render(<RunV3Panel run={runGoc([
      { node_id: 'a', status: 'FAILED', attempt: 1, cost_credit: 0,
        job_id: '', error: 'hỏng', waiting_kind: '', het_han: false },
    ])} onCancel={() => {}} onChayLaiTu={() => {}} />)
    expect(screen.queryByRole('button', { name: 'Chạy lại từ đây' })).toBeNull()
  })

  it('run XONG + có onChayLaiTu: bấm gọi đúng node_id', () => {
    const goi = vi.fn()
    render(<RunV3Panel run={{ ...runGoc([
      { node_id: 'nut_hong', status: 'FAILED', attempt: 1, cost_credit: 0,
        job_id: '', error: 'hỏng', waiting_kind: '', het_han: false },
    ]), status: 'FAILED' }} onCancel={() => {}} onChayLaiTu={goi} />)
    const nut = screen.getByRole('button', { name: 'Chạy lại từ đây' })
    fireEvent.click(nut)
    expect(goi).toHaveBeenCalledWith('nut_hong')
  })

  it('run XONG nhưng KHÔNG truyền onChayLaiTu: không vẽ nút (tương thích ngược)', () => {
    render(<RunV3Panel run={{ ...runGoc([
      { node_id: 'a', status: 'SUCCEEDED', attempt: 1, cost_credit: 0,
        job_id: '', error: '', waiting_kind: '', het_han: false },
    ]), status: 'SUCCEEDED' }} onCancel={() => {}} />)
    expect(screen.queryByRole('button', { name: 'Chạy lại từ đây' })).toBeNull()
  })
})
