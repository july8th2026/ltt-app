/**
 * ⭐ MOT CUA BAO GIA CHO CA DO THI — dem SO REQUEST, khong dem cam giac.
 *
 * No §5 cua `docs/superpowers/plans/2026-09-24-wf-v2-MASTER.md`:
 * `CanvasShell.tsx` goi `quoteTool(...)` **cho tung node**, va effect ay chay
 * lai moi lan `page.nodes` doi — tuc moi lan nguoi ta go mot ky tu vao mot o
 * tham so. Mot do thi 12 node = **12 request** moi lan go.
 *
 * ⛔ DEBOUNCE KHONG PHAI CAU TRA LOI. `setTimeout(...,450)` da co san o dong
 *    do tu truoc; no giam TAN SUAT (so lan bung) chu khong giam **do lon cua
 *    mot lan bung** (N request). Bai nay do dung do lon ay: sau khi mot lan
 *    bung da lang, tong so request bao gia phai la **1**, khong phu thuoc N.
 *
 * 🔑 DOI CHUNG bat buoc (`khong-doi-chung-thi-so-khong-khong-phai-phat-hien`):
 *    mot man hinh trang cung tao ra 0 request va se lam bai "≤ 1" xanh. Nen
 *    bai con doi GIAO DIEN THAT SU hien duoc con so credit cua node dang chon.
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { CanvasShell } from '../src/CanvasShell'
import type { NodeDefinition, NhomPalette } from '../src/nodeDefinition'

const cong = (ten: string, kieu: string) => ({ ten, kieu, bat_buoc: false, nhieu: false })

const nd = (type: string, title: string, over: Partial<NodeDefinition> = {}):
  NodeDefinition => ({ type, type_version: 1, kind: 'app', category: 'LTT_APPS',
    title, description: 'mo ta', icon: '', app_name: 'App', cong_vao: [],
    cong_ra: [], tham_so: { type: 'object', properties: {}, required: [] },
    thi_hanh: 'job', side_effect: 'external', resource: {}, timeout_expr: '',
    retry_mac_dinh: { max: 0, backoff_s: 30 },
    gia: { kieu: 'theo_registry', so: 0, job_type: 'j' }, credential: [],
    quyen: [], cho: [], ma_loi: [], co_mock: false, publish_duoc: true, ...over })

const nhomPalette: NhomPalette[] = [
  { category: 'LTT_APPS', nut: [
    nd('app.text.chat', 'Sinh văn bản', { app_name: 'LTT LLM',
      cong_vao: [cong('prompt', 'text')], cong_ra: [cong('content', 'text')],
      tham_so: { type: 'object', required: ['prompt'],
        properties: { prompt: { type: 'string' } } } }) ] },
]

const paletteV3 = { phien_ban: 3, nhom: nhomPalette, luat_noi_day: {
  phien_ban: 2, kieu: ['text'], hau_to_tap_hop: '[]',
  cap_noi_duoc: [['text', 'text']] as [string, string][] } }

/** ⚠️ So node phai LON hon 1, neu khong "N request" va "1 request" trung nhau
 *  va bai nay xanh o ca hai phia cua ban va. */
const SO_NODE = 12

const doThi = (n: number) => ({
  version: 3, goal: '', budget_max_credit: 50, active_page_id: 'page-1',
  pages: [{ id: 'page-1', name: 'Page 1',
    nodes: Array.from({ length: n }, (_, i) => ({
      id: `n${i}`, type: 'tool' as const,
      position: { x: 80 + (i % 4) * 260, y: 80 + Math.floor(i / 4) * 260 },
      data: { tool: 'text.chat', params: { prompt: `xin chao ${i}` },
              fanout: 1, max_retry: 0 } })),
    edges: [], viewport: { x: 0, y: 0, zoom: 1 },
    frames: [], notes: [], comments: [],
    view: { grid: true, connections: true, minimap: true } }],
})

const workflowV3 = { id: 'w1', name: 'Workflow mới', published_version_id: '',
                     revision: 1, document: doThi(SO_NODE) }

/** Moi URL fetch cua mot lan dung — nguon cua con so trong bao cao. */
let duong: string[] = []

/** Request BAO GIA, dung mot bo loc khong phu thuoc ten cua moi:
 *  ca `/tools/{ten}/quote` (duong cu) lan `/bao-gia` (duong moi) deu tinh. */
const soRequestBaoGia = () =>
  duong.filter(u => u.includes('/quote') || u.includes('/bao-gia')).length

beforeEach(() => {
  duong = []
  document.body.innerHTML = '<div id="agent-canvas-root" data-csrf-token="test-csrf"></div>'
  try { localStorage.clear() } catch { /* cua so rieng tu */ }
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input)
    duong.push(url)
    if (url.endsWith('/v3/palette')) return new Response(JSON.stringify(paletteV3), { status: 200 })
    if (url.endsWith('/v3/luat-noi-day')) return new Response(JSON.stringify(paletteV3.luat_noi_day), { status: 200 })
    if (url.endsWith('/preferences')) return new Response(JSON.stringify({ theme: 'dark',
      catalog_mode: 'advanced', presentation_version: 'creative-v1', revision: init?.method ? 1 : 0 }), { status: 200 })
    // Duong CU: mot request moi node, tra ve mot so.
    if (url.includes('/quote')) return new Response(JSON.stringify({ valid: true, maximum: 3 }), { status: 200 })
    // Duong MOI: mot request mang ca do thi, tra ve bang gia tung node.
    if (url.includes('/bao-gia')) return new Response(JSON.stringify({
      gia: Object.fromEntries(doThi(SO_NODE).pages[0].nodes.map(n => [n.id, 3])),
      loi: {} }), { status: 200 })
    if (url.includes('/bieu-thuc/goi-y')) return new Response(JSON.stringify({
      node_id: 'n0', muc: [], ham: [], loi: null }), { status: 200 })
    if (url.includes('/api/v3/workflows')) {
      if (init?.method === 'PUT')
        return new Response(JSON.stringify({ ...workflowV3, revision: workflowV3.revision + 1 }), { status: 200 })
      if (url.endsWith('/workflows') && init?.method !== 'POST')
        return new Response(JSON.stringify({ items: [{ id: 'w1', name: 'Workflow mới', published: false }] }), { status: 200 })
      return new Response(JSON.stringify(workflowV3), { status: 200 })
    }
    return new Response('{}', { status: 200 })
  })
})
afterEach(() => { vi.restoreAllMocks() })

/** Cho cho lan "bung" bao gia lang han (debounce 450 ms + mot vong mang). */
const choBaoGiaLang = async () => {
  await waitFor(() => expect(soRequestBaoGia()).toBeGreaterThan(0), { timeout: 4000 })
  const truoc = soRequestBaoGia()
  await new Promise(r => setTimeout(r, 700))
  expect(soRequestBaoGia()).toBe(truoc)          // da lang that su
  return truoc
}

describe('bao gia truc tiep tren canvas', () => {
  it(`MOT request bao gia cho ca do thi ${SO_NODE} node, khong phai ${SO_NODE}`,
     async () => {
    render(<CanvasShell />)
    await waitFor(() => expect(document.querySelectorAll('.react-flow__node').length)
      .toBe(SO_NODE), { timeout: 4000 })
    const so = await choBaoGiaLang()
    expect(so).toBe(1)
  })

  it('🔑 doi chung: gia THAT SU hien tren giao dien', async () => {
    render(<CanvasShell />)
    await waitFor(() => expect(document.querySelectorAll('.react-flow__node').length)
      .toBe(SO_NODE), { timeout: 4000 })
    await choBaoGiaLang()
    // Node dau duoc chon => `onNodeClick` mo Inspector => o "Tối đa N credit"
    // phai hien con so TU MAY CHU. ⛔ Chi `click`: `mousedown` keo d3-drag cua
    // React Flow vao mot duong khong co `window` trong jsdom.
    fireEvent.click(document.querySelector<HTMLElement>('.react-flow__node')!)
    await waitFor(() => expect(screen.getByText(/Tối đa 3 credit/)).toBeTruthy(),
                  { timeout: 4000 })
  })
})
