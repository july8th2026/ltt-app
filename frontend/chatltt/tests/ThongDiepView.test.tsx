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
    // ⚠️ DOI 03/09: truoc day phep kiem nay chot rang chuoi NOI BO
    //    (`may B dang ban`) phai hien ra. Do la mot phep kiem chot dung hanh vi
    //    sau — no bao ve viec dat van ban chan doan truoc mat khach.
    //
    //    Do tren production: khi can suat admission, o tra loi hien dung chuoi
    //    `het suat thuc thi`. Nay ma di truoc va cho ra mot cau doc duoc; chuoi
    //    chan doan chi con la luoi do khi khong ma nao khop.
    expect(screen.getByRole('alert')).toHaveTextContent('Model đang bận')
    expect(screen.getByRole('alert')).not.toHaveTextContent('may B dang ban')
  })
})

describe('Markdown — mot xuong dong don phai la mot xuong dong', () => {
  /**
   * 🔴 Do 03/09 tren PRODUCTION. Hoi "liet ke 3 mau, moi mau mot dong": model
   *    tra ve dung ba dong, giao dien ve ra MOT doan lien "Đỏ Xanh dương Vàng"
   *    — mot `<p>`, khong `<br>` nao.
   *
   *    CommonMark coi xuong dong DON la soft break va hien thi thanh dau CACH.
   *    Dung theo dac ta; sai theo ky vong cua moi nguoi dung mot san pham chat.
   *
   * ⛔ Va khong hiem: danh sach khong gach dau dong, dia chi, tho, cac buoc
   *    lam theo thu tu — tat ca deu dinh thanh mot doan chay dai.
   */
  it('ba dong thanh ba dong, khong dinh lien', () => {
    const m = tin({ blocks: [{ type: 'text', text: 'Đỏ\nXanh dương\nVàng' }] })
    const { container } = render(
      <ThongDiepView m={m} phang={[m]} onChuyenNhanh={KHONG}
        onTaoLai={KHONG} onSuaGuiLai={KHONG} />,
    )
    expect(container.querySelectorAll('br').length).toBeGreaterThanOrEqual(2)
  })

  it('van KHONG bat HTML tho — mo hinh chong XSS khong doi', () => {
    const m = tin({ blocks: [{ type: 'text', text: 'a\n<img src=x onerror="alert(1)">' }] })
    const { container } = render(
      <ThongDiepView m={m} phang={[m]} onChuyenNhanh={KHONG}
        onTaoLai={KHONG} onSuaGuiLai={KHONG} />,
    )
    expect(container.querySelector('img')).toBeNull()
    expect(container.textContent).toContain('onerror')   // hien thanh CHU, khong chay
  })
})

describe('Loi hien ra phai la mot CAU, khong phai van ban noi bo', () => {
  /**
   * 🔴 ĐO TRÊN PRODUCTION 03/09. Chạy 45 lượt liên tiếp làm cạn suất admission,
   *    và ô trả lời hiện đúng chuỗi `het suat thuc thi` — văn bản nội bộ, tiếng
   *    Việt không dấu, viết cho người đọc log, đặt vào đúng chỗ câu trả lời.
   *
   * ⛔ Bản cũ ưu tiên `loi.text` TRƯỚC `loi.code`. Nghĩa là càng nhiều thông
   *    tin chẩn đoán ở tầng dưới thì người dùng càng thấy nhiều thứ khó hiểu —
   *    đúng chiều ngược lại.
   */
  const veLoi = (code: string, text: string) => {
    const m = tin({ status: 'failed', blocks: [{ type: 'error', code, text }] })
    return render(<ThongDiepView m={m} phang={[m]} onChuyenNhanh={KHONG}
      onTaoLai={KHONG} onSuaGuiLai={KHONG} />)
  }

  it('ma co trong bang thi hien CAU, khong hien van ban noi bo', () => {
    veLoi('suat', 'het suat thuc thi')
    const t = screen.getByRole('alert').textContent || ''
    expect(t).toContain('Model đang bận')
    expect(t).not.toContain('het suat thuc thi')
  })

  it('noi ro luot bi tu choi KHONG mat tien', () => {
    // Nguoi dung gap loi giua chung se hoi dung mot cau: "toi co mat tien khong".
    veLoi('ban', 'busy')
    expect(screen.getByRole('alert').textContent).toContain('không bị tính tiền')
  })

  it('ma la + van ban KHONG DAU ⇒ khong hien van ban do', () => {
    veLoi('ma_la_khong_biet', 'internal pipeline stage 3 aborted')
    const t = screen.getByRole('alert').textContent || ''
    expect(t).not.toContain('pipeline')
    expect(t).toContain('Thử lại')
  })

  it('ma la + van ban CO DAU ⇒ van hien, vi no viet cho nguoi dung', () => {
    veLoi('ma_la_khong_biet', 'Ảnh tham chiếu quá lớn.')
    expect(screen.getByRole('alert').textContent).toContain('Ảnh tham chiếu quá lớn.')
  })
})

describe('Cho tai nguyen: noi ra ly do, khong noi "Dang tao"', () => {
  /**
   * 🔴 Đo 04/09 trên production: job ảnh nằm `queued` nhiều phút vì GPU máy B
   *    bận. Log worker nói rõ từng vòng — một câu tiếng Việt **viết sẵn cho
   *    người dùng**, kèm cả gợi ý — nhưng nó dừng lại ở log. Màn hình vẫn nói
   *    "Đang tạo…".
   *
   * ⛔ `defer_resource` không chạm sổ tiền và không tiêu lượt thử, nên đó là
   *    một lần chờ hoàn toàn lành. Che nó đi không bảo vệ ai — nó chỉ biến một
   *    lần chờ CÓ LÝ DO thành một lần treo VÔ CỚ.
   */
  const ve = (usage: Record<string, unknown>) => {
    const m = tin({
      status: 'queued', blocks: [],
      execution: { id: 'ex1', status: 'queued', mode: 'job', tool_name: 'image.ltt',
        partial_text: '', reasoning_text: '', finish_reason: '', usage,
        credit: { giu: 3, thu: 0, hoan: 0 }, error_code: '', error_text: '',
        job_id: 'j1', seq: 2 },
    })
    return render(<ThongDiepView m={m} phang={[m]} onChuyenNhanh={KHONG}
      onTaoLai={KHONG} onSuaGuiLai={KHONG} />)
  }

  it('dang cho may ban ⇒ noi ro, kem so giay', () => {
    ve({ cho_tai_nguyen: 17 })
    const t = screen.getByRole('status').textContent || ''
    expect(t).toContain('Máy đang bận')
    expect(t).toContain('17 giây')
    expect(t).not.toContain('Đang tạo')
  })

  it('den han thu lai ⇒ van la CHO, khong nhap nhay ve "Dang tao"', () => {
    ve({ cho_tai_nguyen: 0 })
    expect(screen.getByRole('status').textContent).toContain('Máy đang bận')
  })

  it('khong cho gi ⇒ van la "Dang tao" kem tien do', () => {
    ve({ progress: 45 })
    const t = screen.getByRole('status').textContent || ''
    expect(t).toContain('Đang tạo')
    expect(t).toContain('45%')
  })
})
