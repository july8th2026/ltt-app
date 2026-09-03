import { afterEach, describe, expect, it, vi } from 'vitest'
import { Api, docSSE, LoiApi } from '../src/api'

function luongTu(...khoi: string[]): Response {
  const enc = new TextEncoder()
  const body = new ReadableStream<Uint8Array>({
    start(c) {
      for (const k of khoi) c.enqueue(enc.encode(k))
      c.close()
    },
  })
  return new Response(body, { status: 200 })
}

afterEach(() => { vi.unstubAllGlobals() })

describe('Api', () => {
  it('dinh kem CSRF va tra loi CO MA khi that bai', async () => {
    const goi = vi.fn(async (_url: string, _init?: RequestInit) => new Response(
      JSON.stringify({ error: { code: 'ban', message: 'may B dang ban' } }),
      { status: 503 },
    ))
    vi.stubGlobal('fetch', goi)
    const api = new Api('/chatltt/api', 'tok-1')
    await expect(api.taoHoiThoai('ltt_llm')).rejects.toMatchObject({
      code: 'ban', status: 503,
    })
    const init = goi.mock.calls[0][1]!
    expect((init.headers as Record<string, string>)['X-CSRF-Token']).toBe('tok-1')
  })

  it('than khong phai JSON van giu duoc ma HTTP', async () => {
    vi.stubGlobal('fetch', async () => new Response('<html>502</html>', { status: 502 }))
    const api = new Api('/chatltt/api', 't')
    await expect(api.lietKe()).rejects.toBeInstanceOf(LoiApi)
    await expect(api.lietKe()).rejects.toMatchObject({ code: 'http_502' })
  })

  it('`parent_id: null` va "khong khai" la HAI than khac nhau', async () => {
    const goi = vi.fn(async (_url: string, _init?: RequestInit) =>
      new Response('{}', { status: 200 }))
    vi.stubGlobal('fetch', goi)
    const api = new Api('/chatltt/api', 't')
    await api.guiLuot('cv1', { text: 'a' })
    await api.guiLuot('cv1', { text: 'a', parentId: null })
    await api.guiLuot('cv1', { text: 'a', parentId: 'msg_9' })
    const than = goi.mock.calls.map((c) => JSON.parse(c[1]!.body as string))
    expect('parent_id' in than[0]).toBe(false)
    expect(than[1].parent_id).toBeNull()
    expect(than[2].parent_id).toBe('msg_9')
  })
})

describe('docSSE', () => {
  it('gop khoi bi cat GIUA DONG roi moi phan tich', async () => {
    const tron = 'event: response.delta\ndata: {"type":"response.delta","text":"xin chao"}\n\n'
    vi.stubGlobal('fetch', async () => luongTu(
      tron.slice(0, 12), tron.slice(12, 40), tron.slice(40),
    ))
    const sk: unknown[] = []
    await docSSE('/x', (s) => sk.push(s), new AbortController().signal)
    expect(sk).toEqual([
      { type: 'response.delta', data: { type: 'response.delta', text: 'xin chao' } },
    ])
  })

  it('bo qua `: ping` va dong khong phai JSON, khong lam vo luong', async () => {
    vi.stubGlobal('fetch', async () => luongTu(
      ': ping\n\n',
      'event: snapshot\ndata: {"seq":1}\n\n',
      'data: khong-phai-json\n\n',
      'event: end\ndata: {"seq":2}\n\n',
    ))
    const sk: { type: string }[] = []
    await docSSE('/x', (s) => sk.push(s), new AbortController().signal)
    expect(sk.map((s) => s.type)).toEqual(['snapshot', 'end'])
  })

  it('HTTP loi ⇒ LoiApi, khong im lang', async () => {
    vi.stubGlobal('fetch', async () => new Response(null, { status: 404 }))
    await expect(
      docSSE('/x', () => {}, new AbortController().signal),
    ).rejects.toBeInstanceOf(LoiApi)
  })
})
