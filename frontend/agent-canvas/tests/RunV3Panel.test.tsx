import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
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
        cost_credit: 0, job_id: '', error: 'khong gop duoc', waiting_kind: '' },
    ])} onCancel={() => {}} />)
    const hang = document.querySelector('[data-node-status="KHONG_XAC_DINH"]')
    expect(hang).toBeTruthy()
    expect(hang!.textContent).toContain('Không xác định')
    expect(hang!.textContent).not.toContain('Chờ')
  })

  it('WAITING vì HUMAN đọc khác WAITING vì WEBHOOK', () => {
    render(<RunV3Panel run={runGoc([
      { node_id: 'duyet', status: 'WAITING', attempt: 1, cost_credit: 0,
        job_id: '', error: '', waiting_kind: 'HUMAN' },
      { node_id: 'hook', status: 'WAITING', attempt: 1, cost_credit: 0,
        job_id: '', error: '', waiting_kind: 'WEBHOOK' },
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
        job_id: '', error: '', waiting_kind: '' },
    ])} onCancel={() => {}} />)
    expect(screen.getByText('Chờ')).toBeInTheDocument()
  })
})
