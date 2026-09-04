/**
 * Vo ChatLTT: phim tat, so du, "Doc to", va trang thai "chua san sang".
 *
 * ⭐ May chu duoc gia lap o muc `fetch` — dung khuon that (duong dan + than
 *    JSON), nen mot lan doi hop dong ben may chu se lam test nay do chu khong
 *    im lang chay tiep tren mot ban sao da cu.
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Api } from '../src/api'
import { App } from '../src/App'

const NANG_LUC = {
  nang_luc: [
    {
      ten: 'text.chat', phuong_thuc: 'text', che_do: 'stream', nhan: 'Chat',
      models: { ltt_llm: { description: 'text' }, ltt_llm_vision: { description: 'vision' } },
      tuy_chon: {}, gia: {}, duong_dan_app: '/ltt-llm', san_sang: 'san_sang', hop_dong: {},
    },
    {
      ten: 'speech.ltt', phuong_thuc: 'audio', che_do: 'job', nhan: 'Giọng',
      models: {}, tuy_chon: { voice_id: [{ value: 'vc_1', label: 'Giọng của tôi' }] },
      gia: {}, duong_dan_app: '/ltt-voice', san_sang: 'san_sang', hop_dong: {},
    },
  ],
}

const SU_THAT = {
  conversation: {
    id: 'cv1', title: 'Thử', model_alias: 'ltt_llm', current_leaf_id: 'a1',
    archived: false, created_at: '2026-09-03T00:00:00+00:00',
    updated_at: '2026-09-03T00:00:03+00:00',
  },
  messages: [
    {
      id: 'u1', parent_id: null, role: 'user', blocks: [{ type: 'text', text: 'hỏi' }],
      status: 'done', model_alias: '', execution_id: null,
      created_at: '2026-09-03T00:00:01+00:00',
    },
    {
      id: 'a1', parent_id: 'u1', role: 'assistant',
      blocks: [{ type: 'text', text: 'trả lời' }], status: 'done',
      model_alias: 'ltt_llm', execution_id: 'ex1',
      created_at: '2026-09-03T00:00:02+00:00',
      execution: {
        id: 'ex1', status: 'done', mode: 'stream', tool_name: 'text.chat',
        partial_text: 'trả lời', reasoning_text: '', finish_reason: 'stop',
        usage: {}, credit: { giu: 3, thu: 1, hoan: 2 },
        error_code: '', error_text: '', job_id: null, seq: 5,
      },
    },
  ],
}

function datMayChuGia(g: { soDu?: number; nangLuc?: unknown; coHoiThoai?: boolean } = {}) {
  const goi = vi.fn(async (url: string) => {
    const u = String(url)
    const j = (x: unknown) => new Response(JSON.stringify(x), { status: 200 })
    if (u.endsWith('/so-du')) return j({ credit: g.soDu ?? 4995 })
    if (u.endsWith('/danh-muc')) return j(g.nangLuc ?? NANG_LUC)
    if (u.includes('/hoi-thoai?') || u.endsWith('/hoi-thoai')) {
      return j({ hoi_thoai: g.coHoiThoai === false ? [] : [SU_THAT.conversation] })
    }
    if (u.includes('/hoi-thoai/cv1')) return j(SU_THAT)
    return j({})
  })
  vi.stubGlobal('fetch', goi)
  return goi
}

function veApp() {
  return render(<App api={new Api('/chatltt/api', 'tok')} />)
}

afterEach(() => { vi.unstubAllGlobals() })

describe('App — so du', () => {
  it('hien so du va doc len cho trinh doc man hinh', async () => {
    datMayChuGia({ soDu: 4995 })
    veApp()
    const o = await screen.findByLabelText('Số dư 4995 credit')
    expect(o).toHaveTextContent('4.995')
    expect(o).toHaveAttribute('aria-live', 'polite')
  })
})

describe('App — phim tat', () => {
  it('Ctrl+Shift+O mo hoi thoai moi va dua con tro ve o soan', async () => {
    datMayChuGia()
    veApp()
    const muc = await screen.findByRole('button', { name: 'Thử' })
    fireEvent.click(muc)
    await waitFor(() => expect(screen.getByText('trả lời')).toBeInTheDocument())

    fireEvent.keyDown(window, { key: 'O', ctrlKey: true, shiftKey: true })
    await waitFor(() => {
      expect(screen.getByText('Bắt đầu bằng một câu hỏi.')).toBeInTheDocument()
    })
    expect(document.activeElement).toBe(screen.getByLabelText('Nội dung tin nhắn'))
  })

  it('Shift+Esc dua con tro ve o soan', async () => {
    datMayChuGia()
    veApp()
    await screen.findByLabelText('Nội dung tin nhắn')
    ;(screen.getByLabelText('Tìm hội thoại') as HTMLElement).focus()
    expect(document.activeElement).not.toBe(screen.getByLabelText('Nội dung tin nhắn'))
    fireEvent.keyDown(window, { key: 'Escape', shiftKey: true })
    expect(document.activeElement).toBe(screen.getByLabelText('Nội dung tin nhắn'))
  })

  it('Ctrl+Shift+X khi KHONG co luot nao dang chay thi khong chan phim goc', async () => {
    datMayChuGia()
    veApp()
    await screen.findByLabelText('Nội dung tin nhắn')
    const e = new KeyboardEvent('keydown',
      { key: 'X', ctrlKey: true, shiftKey: true, cancelable: true })
    window.dispatchEvent(e)
    expect(e.defaultPrevented).toBe(false)
  })
})

describe('App — Doc to va trang thai nang luc', () => {
  it('"Doc to" chuyen chu sang o tieng, va VAN phai xac nhan gia', async () => {
    datMayChuGia()
    veApp()
    fireEvent.click(await screen.findByRole('button', { name: 'Thử' }))
    const doc = await screen.findByRole('button', { name: 'Đọc to' })
    fireEvent.click(doc)
    const o = await screen.findByLabelText('Văn bản cần đọc')
    expect((o as HTMLTextAreaElement).value).toBe('trả lời')
    // Chua co o gia: nguoi dung phai bam "Xem giá" truoc.
    expect(screen.queryByLabelText('Xác nhận giá')).toBeNull()
    expect(screen.getByRole('button', { name: 'Xem giá' })).toBeEnabled()
  })

  it('tieng KHONG san sang ⇒ khong co nut "Doc to", nut "Tao giong" bi tat', async () => {
    const tat = {
      nang_luc: [
        NANG_LUC.nang_luc[0],
        { ...NANG_LUC.nang_luc[1], san_sang: 'chua_san_sang' },
      ],
    }
    datMayChuGia({ nangLuc: tat })
    veApp()
    fireEvent.click(await screen.findByRole('button', { name: 'Thử' }))
    await waitFor(() => expect(screen.getByText('trả lời')).toBeInTheDocument())
    expect(screen.queryByRole('button', { name: 'Đọc to' })).toBeNull()
    expect(screen.getByRole('button', { name: 'Tạo giọng' })).toBeDisabled()
  })

  it('text KHONG san sang ⇒ chip canh bao va o soan bi tat', async () => {
    const tat = {
      nang_luc: [{ ...NANG_LUC.nang_luc[0], san_sang: 'chua_san_sang' }],
    }
    datMayChuGia({ nangLuc: tat })
    veApp()
    expect(await screen.findByText('Model chưa sẵn sàng')).toBeInTheDocument()
    expect(screen.getByLabelText('Nội dung tin nhắn')).toBeDisabled()
  })
})

describe('App — hoi thoai co DIA CHI trong URL', () => {
  /**
   * 🔴 Truoc Phase 13, tai lai trang la MAT CHO DANG DUNG. Danh sach hoi thoai
   *    con nguyen va `current_leaf_id` giu dung nhanh — nhung man hinh roi ve
   *    "Bat dau bang mot cau hoi", vi khong co gi trong URL noi ta dang o dau.
   *
   * ⭐ Va mat cho dung chi la trieu chung de thay nhat. Thu thuc su thieu la
   *    hoi thoai KHONG CO DIA CHI: khong danh dau trang duoc, khong gui link
   *    cho nguoi khac duoc, Back/Forward khong di lai duoc. Ba thao tac nguoi
   *    ta lam hang ngay voi mot san pham chat.
   */
  afterEach(() => { window.location.hash = '' })

  it('mo dung hoi thoai ma hash chi toi, ngay tu luot ve dau', async () => {
    window.location.hash = '#cv1'
    datMayChuGia()
    veApp()
    await waitFor(() => expect(screen.getByText('trả lời')).toBeTruthy())
  })

  it('chon mot hoi thoai thi ghi vao hash', async () => {
    datMayChuGia()
    veApp()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Thử' })).toBeTruthy())
    fireEvent.click(screen.getByRole('button', { name: 'Thử' }))
    await waitFor(() => expect(window.location.hash).toBe('#cv1'))
  })

  it('hash tro toi hoi thoai KHONG doc duoc thi bao loi VA thoat ra duoc', async () => {
    // Link cu, hoi thoai da xoa, hay link cua nguoi khac (may chu tra 404).
    // Chi hien loi thi trang dung yen va tai lai van the — nguoi dung mac ket.
    window.location.hash = '#khong-ton-tai'
    vi.stubGlobal('fetch', vi.fn(async (url: string) => {
      const u = String(url)
      const j = (x: unknown) => new Response(JSON.stringify(x), { status: 200 })
      if (u.endsWith('/so-du')) return j({ credit: 10 })
      if (u.endsWith('/danh-muc')) return j(NANG_LUC)
      if (u.includes('/hoi-thoai?') || u.endsWith('/hoi-thoai')) return j({ hoi_thoai: [] })
      return new Response(JSON.stringify({ detail: 'khong thay' }), { status: 404 })
    }))
    veApp()
    await waitFor(() => expect(window.location.hash).toBe(''), { timeout: 4000 })
    expect(screen.getByText('Bắt đầu bằng một câu hỏi.')).toBeTruthy()
  })
})

describe('App — noi lai luong sau khi tai lai trang', () => {
  /**
   * 🔴 ĐO ĐƯỢC TRÊN PRODUCTION 03/09. F5 giữa lúc model đang trả lời:
   *
   *        giao diện        máy chủ
   *     t+ 0s   chữ = 0     streaming, partial =    0
   *     t+25s   chữ = 0     streaming, partial = 3429   ← vẫn đang sinh
   *
   *    Máy chủ chạy hoàn hảo. Giao diện trắng cho tới khi người dùng tự F5
   *    **lần nữa**.
   *
   * ⭐ Máy chủ đã dựng sẵn từ Phase 08a: `dang_chay` là sổ fan-out nhiều người
   *    nghe, và route ghi thẳng "Nối lại = mở lại `stream?after=<seq>`".
   *    Thiếu đúng một chỗ: client chưa bao giờ gọi.
   */
  it('thay mot luot dang streaming thi TU MO lai stream', async () => {
    const dangChay = {
      ...SU_THAT,
      messages: [
        SU_THAT.messages[0],
        {
          ...SU_THAT.messages[1],
          status: 'streaming',
          blocks: [],
          execution: { ...SU_THAT.messages[1].execution, status: 'streaming', mode: 'stream' },
        },
      ],
    }
    const goi = vi.fn(async (url: string) => {
      const u = String(url)
      const j = (x: unknown) => new Response(JSON.stringify(x), { status: 200 })
      if (u.endsWith('/so-du')) return j({ credit: 10 })
      if (u.endsWith('/danh-muc')) return j(NANG_LUC)
      if (u.includes('/hoi-thoai?') || u.endsWith('/hoi-thoai')) {
        return j({ hoi_thoai: [SU_THAT.conversation] })
      }
      if (u.includes('/stream')) {
        return new Response('event: end\ndata: {"seq":9}\n\n',
          { status: 200, headers: { 'content-type': 'text/event-stream' } })
      }
      if (u.includes('/hoi-thoai/cv1')) return j(dangChay)
      return j({})
    })
    vi.stubGlobal('fetch', goi)
    window.location.hash = '#cv1'
    veApp()

    await waitFor(() => {
      const duong = goi.mock.calls.map((c) => String(c[0]))
      expect(duong.some((d) => d.includes('/luot/ex1/stream'))).toBe(true)
    }, { timeout: 4000 })
    window.location.hash = ''
  })

  it('luot DA XONG thi KHONG mo stream — khong goi thua', async () => {
    // ⛔ Thieu dieu kien nay thi moi lan mo mot hoi thoai cu la mot ket noi SSE
    //    vo ich toi may chu, nhan len theo so lan nguoi dung bam quanh sidebar.
    datMayChuGia()
    window.location.hash = '#cv1'
    const goi = (globalThis.fetch as unknown as ReturnType<typeof vi.fn>)
    veApp()
    await waitFor(() => expect(screen.getByText('trả lời')).toBeTruthy())
    const duong = goi.mock.calls.map((c) => String(c[0]))
    expect(duong.some((d) => d.includes('/stream'))).toBe(false)
    window.location.hash = ''
  })
})

/**
 * Năng lực CHƯA sẵn sàng thì phải tự hỏi lại — đừng bắt người dùng bấm F5.
 *
 * 🔴 Trước 04/09 danh mục chỉ được nạp **một lần** lúc gắn component. Model ảnh
 *    và giọng nằm ở máy B và nạp sau vài phút, nên ai mở trang trước đó sẽ thấy
 *    nút "Tạo giọng" vô hiệu **vĩnh viễn**: không có gì báo, không có gì đổi, và
 *    lối thoát duy nhất là F5 mà không ai nói cho họ biết.
 *
 * ⭐ Lỗi này lộ ra từ chính một dòng BỎ QUA của bộ kiểm giao diện, không phải từ
 *    một dòng đỏ: *"model tiếng chưa nạp — máy chủ nói `speech.ltt=san_sang`"*.
 *    Một câu tự mâu thuẫn. Thứ bắt được nó là đọc kỹ một dòng BOQUA thay vì hài
 *    lòng vì nó không đỏ.
 */
describe('nang luc chua san sang', () => {
  const chuaSanSang = {
    nang_luc: NANG_LUC.nang_luc.map((n) => (
      n.ten === 'speech.ltt' ? { ...n, san_sang: 'dang_nap' } : n)),
  }

  afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals() })

  it('hoi lai danh muc khi con nang luc chua san sang', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const goi = datMayChuGia({ nangLuc: chuaSanSang })
    veApp()
    await waitFor(() => expect(
      goi.mock.calls.filter((c) => String(c[0]).endsWith('/danh-muc')).length).toBe(1))

    await vi.advanceTimersByTimeAsync(21_000)
    await waitFor(() => expect(
      goi.mock.calls.filter((c) => String(c[0]).endsWith('/danh-muc')).length)
      .toBeGreaterThan(1))
  })

  it('DU sang sang roi thi KHONG hoi lai — vong lap phai tu dung', async () => {
    // ⛔ Nua kia cua menh de. Mot vong lap chay mai la mot vong lap se bi ai do
    //    tat di vi ton, va lan tat do mang theo ca truong hop dang can no.
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const goi = datMayChuGia()
    veApp()
    await waitFor(() => expect(
      goi.mock.calls.filter((c) => String(c[0]).endsWith('/danh-muc')).length).toBe(1))

    await vi.advanceTimersByTimeAsync(65_000)
    expect(goi.mock.calls.filter((c) => String(c[0]).endsWith('/danh-muc')).length).toBe(1)
  })
})
