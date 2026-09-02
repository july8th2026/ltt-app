/**
 * Hai tinh chat khong duoc mat: HTML tho trong Markdown khong bao gio thanh
 * DOM (AC-12), va khoi suy luan noi duoc trang thai cua no cho trinh doc man
 * hinh (AC-13).
 */
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ThongDiepView } from '../src/ThongDiepView'
import type { ThongDiep } from '../src/kieu'

function tin(g: Partial<ThongDiep> = {}): ThongDiep {
  return {
    id: 'a1', parent_id: 'u1', role: 'assistant',
    blocks: [{ type: 'text', text: 'xin chao' }],
    status: 'done', model_alias: 'ltt_llm', execution_id: null,
    created_at: '2026-09-03T00:00:02.000000+00:00',
    ...g,
  }
}

const KHONG = () => {}

describe('ThongDiepView — an toan noi dung', () => {
  it('HTML tho bi ESCAPE thanh chu, khong thanh the', () => {
    const doc = tin({
      blocks: [{
        type: 'text',
        text: '<script>window.__xss=1</script>\n\n<img src=x onerror="window.__xss=2">',
      }],
    })
    const { container } = render(
      <ThongDiepView m={doc} phang={[doc]} onChuyenNhanh={KHONG}
        onTaoLai={KHONG} onSuaGuiLai={KHONG} />,
    )
    expect(container.querySelector('script')).toBeNull()
    expect(container.querySelector('img')).toBeNull()
    expect(container.textContent).toContain('<script>')
    expect((window as unknown as Record<string, unknown>).__xss).toBeUndefined()
  })

  it('Markdown that (dam, khoi ma, bang GFM) van duoc ve', () => {
    const doc = tin({
      blocks: [{ type: 'text', text: '**dam**\n\n```py\nprint(1)\n```\n\n| a | b |\n|---|---|\n| 1 | 2 |' }],
    })
    const { container } = render(
      <ThongDiepView m={doc} phang={[doc]} onChuyenNhanh={KHONG}
        onTaoLai={KHONG} onSuaGuiLai={KHONG} />,
    )
    expect(container.querySelector('strong')?.textContent).toBe('dam')
    expect(container.querySelector('pre code')?.textContent).toContain('print(1)')
    expect(container.querySelectorAll('table td').length).toBe(2)
  })

  it('tin cua NGUOI DUNG khong di qua Markdown — hien nguyen van', () => {
    const doc = tin({ role: 'user', blocks: [{ type: 'text', text: '**khong dam**' }] })
    const { container } = render(
      <ThongDiepView m={doc} phang={[doc]} onChuyenNhanh={KHONG}
        onTaoLai={KHONG} onSuaGuiLai={KHONG} />,
    )
    expect(container.querySelector('strong')).toBeNull()
    expect(container.textContent).toContain('**khong dam**')
  })
})

describe('ThongDiepView — suy luan va nhanh', () => {
  it('khoi suy luan: aria-expanded + aria-controls tro dung vung, nhan doi khi xong', () => {
    const dang = tin({
      status: 'streaming', blocks: [], execution_id: 'ex1',
      execution: {
        id: 'ex1', status: 'streaming', mode: 'stream', tool_name: 'text.chat',
        partial_text: '', reasoning_text: 'dang nghi', finish_reason: '',
        usage: {}, credit: { giu: 3, thu: 0, hoan: 0 },
        error_code: '', error_text: '', job_id: null, seq: 1,
      },
    })
    const { rerender } = render(
      <ThongDiepView m={dang} phang={[dang]} onChuyenNhanh={KHONG}
        onTaoLai={KHONG} onSuaGuiLai={KHONG} />,
    )
    const nut = screen.getByRole('button', { name: /Đang suy nghĩ/ })
    expect(nut).toHaveAttribute('aria-expanded', 'false')
    const vung = document.getElementById(nut.getAttribute('aria-controls')!)
    expect(vung).not.toBeNull()
    expect(vung).toHaveAttribute('hidden')
    fireEvent.click(nut)
    expect(screen.getByRole('button', { name: /Đang suy nghĩ/ }))
      .toHaveAttribute('aria-expanded', 'true')

    const xong = tin({ blocks: [{ type: 'reasoning', text: 'da nghi' }, { type: 'text', text: 'ok' }] })
    rerender(<ThongDiepView m={xong} phang={[xong]} onChuyenNhanh={KHONG}
      onTaoLai={KHONG} onSuaGuiLai={KHONG} />)
    expect(screen.getByRole('button', { name: 'Suy luận' })).toBeInTheDocument()
  })

  it('mot anh em thi khong hien dieu huong nhanh; hai thi co, va bam goi dung chi so', () => {
    const a = tin({ id: 'a1' })
    const b = tin({ id: 'a2', created_at: '2026-09-03T00:00:03.000000+00:00' })
    const chuyen = vi.fn()
    const { rerender } = render(
      <ThongDiepView m={a} phang={[a]} onChuyenNhanh={chuyen}
        onTaoLai={KHONG} onSuaGuiLai={KHONG} />,
    )
    expect(screen.queryByLabelText('Chuyển nhánh')).toBeNull()

    rerender(<ThongDiepView m={a} phang={[a, b]} onChuyenNhanh={chuyen}
      onTaoLai={KHONG} onSuaGuiLai={KHONG} />)
    expect(screen.getByRole('status')).toHaveTextContent('1 / 2')
    expect(screen.getByLabelText('Nhánh trước')).toBeDisabled()
    fireEvent.click(screen.getByLabelText('Nhánh sau'))
    expect(chuyen).toHaveBeenCalledWith(a, 1)
  })

  it('bi cat va bi huy deu noi ra bang chu, khong im lang', () => {
    const cat = tin({ blocks: [{ type: 'text', text: 'dai' }, { type: 'status', code: 'length' }] })
    const { rerender } = render(
      <ThongDiepView m={cat} phang={[cat]} onChuyenNhanh={KHONG}
        onTaoLai={KHONG} onSuaGuiLai={KHONG} />,
    )
    expect(screen.getByText('Bị cắt ở trần độ dài')).toBeInTheDocument()

    const huy = tin({ status: 'cancelled', blocks: [{ type: 'status', code: 'cancelled' }] })
    rerender(<ThongDiepView m={huy} phang={[huy]} onChuyenNhanh={KHONG}
      onTaoLai={KHONG} onSuaGuiLai={KHONG} />)
    expect(screen.getByText('Đã dừng')).toBeInTheDocument()

    const loi = tin({
      status: 'failed',
      blocks: [{ type: 'error', code: 'ban', text: 'may B dang ban' }],
    })
    rerender(<ThongDiepView m={loi} phang={[loi]} onChuyenNhanh={KHONG}
      onTaoLai={KHONG} onSuaGuiLai={KHONG} />)
    expect(screen.getByRole('alert')).toHaveTextContent('may B dang ban')
  })
})
