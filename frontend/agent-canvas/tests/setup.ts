import '@testing-library/jest-dom/vitest'

class TestResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = TestResizeObserver as typeof ResizeObserver

class TestDOMMatrixReadOnly {
  m11=1
  m12=0
  m21=0
  m22=1
  m41=0
  m42=0
  constructor(_transform?:string) {}
}
window.DOMMatrixReadOnly=TestDOMMatrixReadOnly as unknown as typeof DOMMatrixReadOnly

/**
 * `EventSource` GIẢ cho jsdom (jsdom **không** có API này).
 *
 * ⛔ Đây là một **bộ đôi thay cho API của trình duyệt**, không phải một đường
 *    thứ hai của sản phẩm: `src/` chỉ biết đúng một cách đọc run (SSE). Nó
 *    lấy dữ liệu qua `fetch` — đã bị `vi.mock` trong từng bài — nên mọi phép
 *    kiểm chặn đường `/api/v3/runs/…` vẫn chặn được, và `fetch.mock.calls`
 *    vẫn là chỗ đọc "Canvas đã gọi những gì".
 *
 * ⚠️ Nó KHÔNG tự nối lại. Đúng như `EventSource` thật sau khi `close()`, và
 *    đúng như hợp đồng của `workflowApi.theoDoiRunV3` (đóng ngay ở `onerror`;
 *    việc nối lại thuộc `CanvasShell`, nơi có lùi dần + dòng lỗi).
 *
 * Thân phản hồi: một gói `text/event-stream` thật thì tách theo khung SSE;
 * một thân JSON trần (mock cũ của các bài poll) coi như MỘT sự kiện `run`.
 */
class TestEventSource extends EventTarget {
  static readonly CONNECTING = 0
  static readonly OPEN = 1
  static readonly CLOSED = 2
  readyState = TestEventSource.CONNECTING
  onerror: ((su: Event) => void) | null = null
  onmessage: ((su: MessageEvent) => void) | null = null
  onopen: ((su: Event) => void) | null = null
  readonly withCredentials = false
  constructor(readonly url: string) {
    super()
    void this.moLuong()
  }
  private async moLuong() {
    try {
      const phanHoi = await fetch(this.url)
      if (this.readyState === TestEventSource.CLOSED) return
      if (!phanHoi.ok) throw new Error(String(phanHoi.status))
      const tho = await phanHoi.text()
      if (this.readyState === TestEventSource.CLOSED) return
      this.readyState = TestEventSource.OPEN
      // ⭐ Nhỏ giọt, không đổ một lần. Một luồng SSE thật gửi từng khung theo
      //    thời gian (máy chủ quét CSDL 1 s/lần), và giao diện phải ĐÚNG ở
      //    từng khung — không chỉ ở khung cuối. Đổ hết trong một microtask
      //    làm mọi bài "trạng thái giữa chừng" (bấm Hủy khi còn QUEUED) đo
      //    một màn hình đã nhảy tới trạng thái cuối.
      for (const [loai, dulieu] of khungSSE(tho)) {
        await new Promise(nghi => setTimeout(nghi, NHIP_KHUNG_MS))
        if (this.readyState === TestEventSource.CLOSED) return
        this.dispatchEvent(new MessageEvent(loai, { data: dulieu }))
      }
      // Máy chủ ĐÓNG luồng khi hết khung (thật: mốc 90 s, `_SSE_DONG_SAU_S`).
      // `EventSource` thật báo `onerror` rồi tự nối lại; ở đây chỉ báo, vì
      // việc nối lại thuộc `CanvasShell` (lùi dần + dòng lỗi).
      if (this.readyState === TestEventSource.CLOSED) return
      this.readyState = TestEventSource.CLOSED
      this.onerror?.(new Event('error'))
      return
    } catch {
      if (this.readyState === TestEventSource.CLOSED) return
      this.readyState = TestEventSource.CLOSED
      this.onerror?.(new Event('error'))
    }
  }
  close() { this.readyState = TestEventSource.CLOSED }
}

/** Giãn cách giữa hai khung của luồng giả (ms). */
const NHIP_KHUNG_MS = 120
const XUONG_DONG = String.fromCharCode(10)
const DOI_KHUNG = XUONG_DONG + XUONG_DONG

/** `[loai, data]` của từng khung. Thân JSON trần ⇒ một khung `run`. */
function khungSSE(tho: string): [string, string][] {
  if (!tho.includes('data:')) return [['run', tho]]
  const ra: [string, string][] = []
  for (const khoi of tho.split(DOI_KHUNG)) {
    if (!khoi.trim()) continue
    let loai = 'message'
    const dong: string[] = []
    for (const d of khoi.split(XUONG_DONG)) {
      if (d.startsWith('event:')) loai = d.slice(6).trim()
      else if (d.startsWith('data:')) dong.push(d.slice(5).trim())
    }
    if (dong.length) ra.push([loai, dong.join(XUONG_DONG)])
  }
  return ra
}

globalThis.EventSource = TestEventSource as unknown as typeof EventSource
