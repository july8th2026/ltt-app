/**
 * Khoi tai san trong hoi thoai: anh, am thanh, tien do, va MOT dieu de quen —
 * moi duong tai deu phai di qua cua co kiem so huu, khong phai `/static`.
 */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Api } from '../src/api'
import { ThongDiepView } from '../src/ThongDiepView'
import type { ThiHanh, ThongDiep } from '../src/kieu'

const KHONG = () => {}

function ex(g: Partial<ThiHanh> = {}): ThiHanh {
  return {
    id: 'ex1', status: 'done', mode: 'job', tool_name: 'image.ltt',
    partial_text: '', reasoning_text: '', finish_reason: '',
    usage: {}, credit: { giu: 12, thu: 6, hoan: 6 },
    error_code: '', error_text: '', job_id: 'job1', seq: 3, ...g,
  }
}

function tin(g: Partial<ThongDiep> = {}): ThongDiep {
  return {
    id: 'a1', parent_id: 'u1', role: 'assistant', blocks: [],
    status: 'done', model_alias: '', execution_id: 'ex1',
    created_at: '2026-09-03T00:00:02.000000+00:00', ...g,
  }
}

const api = new Api('/chatltt/api', 't')
const duong = (k: string) => api.duongTaiSan(k)

describe('Khoi tai san', () => {
  it('anh ve qua cua co kiem so huu, co alt, KHONG qua /static', () => {
    const m = tin({
      execution: ex(),
      blocks: [
        { type: 'image', key: 'anhnoibo/u1/job1/0.png' },
        { type: 'image', key: 'anhnoibo/u1/job1/1.png' },
      ],
    })
    const { container } = render(
      <ThongDiepView m={m} phang={[m]} onChuyenNhanh={KHONG}
        onTaoLai={KHONG} onSuaGuiLai={KHONG} duongTaiSan={duong} />,
    )
    const anh = [...container.querySelectorAll('img')]
    expect(anh).toHaveLength(2)
    expect(anh[0].getAttribute('src')).toBe('/chatltt/tai-san/anhnoibo/u1/job1/0.png')
    expect(anh[0].getAttribute('src')).not.toContain('/static/')
    expect(anh[0].getAttribute('alt')).toContain('Ảnh 1')
    expect(anh[0].getAttribute('loading')).toBe('lazy')
  })

  it('am thanh co trinh phat, va co van ban du phong khi trinh duyet khong phat duoc', () => {
    const m = tin({
      execution: ex({ tool_name: 'speech.ltt' }),
      blocks: [{ type: 'audio', key: 'voice/out/u1/job1/tieng.wav' }],
    })
    const { container } = render(
      <ThongDiepView m={m} phang={[m]} onChuyenNhanh={KHONG}
        onTaoLai={KHONG} onSuaGuiLai={KHONG} duongTaiSan={duong} />,
    )
    const am = container.querySelector('audio')!
    expect(am).toHaveAttribute('controls')
    expect(am.getAttribute('src')).toBe('/chatltt/tai-san/voice/out/u1/job1/tieng.wav')
    expect(am.textContent).toContain('không phát được')
  })

  it('dang tao thi noi ra, kem % khi co', () => {
    const m = tin({ status: 'queued', execution: ex({ status: 'queued', usage: { progress: 40 } }) })
    const { rerender } = render(
      <ThongDiepView m={m} phang={[m]} onChuyenNhanh={KHONG}
        onTaoLai={KHONG} onSuaGuiLai={KHONG} duongTaiSan={duong} />,
    )
    expect(screen.getByRole('status')).toHaveTextContent('Đang tạo… 40%')

    const chuaCo = tin({ status: 'queued', execution: ex({ status: 'queued' }) })
    rerender(<ThongDiepView m={chuaCo} phang={[chuaCo]} onChuyenNhanh={KHONG}
      onTaoLai={KHONG} onSuaGuiLai={KHONG} duongTaiSan={duong} />)
    expect(screen.getByRole('status')).toHaveTextContent('Đang tạo…')
  })

  it('luot JOB khong co nut "Tao lai" — tao lai mot anh la mot lan tra tien nua', () => {
    const job = tin({ execution: ex(), blocks: [{ type: 'image', key: 'anhnoibo/u1/j/0.png' }] })
    const { rerender } = render(
      <ThongDiepView m={job} phang={[job]} onChuyenNhanh={KHONG}
        onTaoLai={KHONG} onSuaGuiLai={KHONG} duongTaiSan={duong} />,
    )
    expect(screen.queryByRole('button', { name: 'Tạo lại' })).toBeNull()

    const text = tin({
      execution: ex({ mode: 'stream', tool_name: 'text.chat' }),
      blocks: [{ type: 'text', text: 'xin chao' }],
    })
    rerender(<ThongDiepView m={text} phang={[text]} onChuyenNhanh={KHONG}
      onTaoLai={KHONG} onSuaGuiLai={KHONG} duongTaiSan={duong} />)
    expect(screen.getByRole('button', { name: 'Tạo lại' })).toBeInTheDocument()
  })

  it('khong truyen `duongTaiSan` thi khong ve tai san — fail-closed', () => {
    const m = tin({ execution: ex(), blocks: [{ type: 'image', key: 'anhnoibo/u1/j/0.png' }] })
    const { container } = render(
      <ThongDiepView m={m} phang={[m]} onChuyenNhanh={KHONG}
        onTaoLai={KHONG} onSuaGuiLai={KHONG} />,
    )
    expect(container.querySelector('img')).toBeNull()
  })
})
