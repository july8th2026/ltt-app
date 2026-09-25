import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cancelRunV3, createAutosave,
  createRunV3, goiYBieuThuc,
  fromV3, loadRunV3, loadWorkflowV3,
  publishWorkflowV3, RUN_V3_KET_THUC,
  saveWorkflowV3, toV3,
  WorkflowCompileError, WorkflowConflictError,
  type RunV3 } from '../src/workflowApi'

const workflowApiSource = readFileSync(
  join(import.meta.dirname, '../src/workflowApi.ts'), 'utf8')

afterEach(() => { vi.restoreAllMocks(); vi.useRealTimers() })

// ⏭️ 24/09 (lan `p10-don`) + 25/09 (lan `wfa`, task A6): cum v2
//    (`saveWorkflow`/`createRun`/`approveRun`/`loadRun`/`loadRunHistory`/
//    `restoreRunAsWorkflow`/…) bi XOA khoi `workflowApi.ts` — khong con ai
//    goi tu `src/**`, va cua may chu cua no dong tu P8 task 5 (`tests/
//    test_2934`). Cac bai kiem CSRF/If-Match/409/422 cho no da co ban tuong
//    duong o cum v3 duoi day (`saveWorkflowV3`, `publishWorkflowV3`,
//    `createRunV3`) — xoa han thay vi sua header. Banh coc chan cum v2 quay
//    lai qua frontend: `tests/test_3521`. Banh coc TAP HOP ham workflowApi.ts
//    con song: `tests/test_4105_wf_v2_pa_don_ma_chet.py`.
describe('workflow API', () => {
  it('debounces autosave and persists only latest value', async () => {
    vi.useFakeTimers()
    const save = vi.fn(async (_value: number) => {})
    const autosave = createAutosave(save, 500)
    autosave.schedule(1); autosave.schedule(2)
    await vi.advanceTimersByTimeAsync(500)
    expect(save).toHaveBeenCalledTimes(1)
    expect(save).toHaveBeenCalledWith(2)
  })
})

// ── Canvas v3 (Dot 5.2) ────────────────────────────────────────────────────
describe('canvas v3', () => {
  // ⚠️ CO Y dung cong KHAC mac dinh. Bo du lieu dung 'out'/'in' se KHONG phan
  //    biet duoc "giu cong that" voi "hard-code gia tri du phong" — hai duong
  //    cho ra cung ket qua. Bai hoc nay da tra gia o Dot 4 va o `M-1`.
  const v2 = { version: 2 as const, goal: 'g', budget_max_credit: 10,
    active_page_id: 'p1', pages: [{ id: 'p1', name: 'P', nodes: [],
      edges: [{ id: 'e1', source: 'a', target: 'b',
        sourceHandle: 'anh_ra', targetHandle: 'van_ban_vao' }],
      viewport: { x: 0, y: 0, zoom: 1 }, frames: [], notes: [], comments: [] }] }

  it('giu cong khi len v3, va dung DUNG ten truong cua may chu', () => {
    const e = toV3(v2).pages[0].edges[0]
    expect(e).toEqual({ id: 'e1', source_node: 'a', target_node: 'b',
      source_port: 'anh_ra', target_port: 'van_ban_vao', kind: 'DATA' })
    // Khong con ten cu sot lai — mot truong thua se di thang vao CSDL.
    expect(Object.keys(e).sort()).toEqual(
      ['id', 'kind', 'source_node', 'source_port', 'target_node', 'target_port'])
  })

  it('canh KHONG khai cong thi roi ve mac dinh cua may chu', () => {
    const tran = { ...v2, pages: [{ ...v2.pages[0],
      edges: [{ id: 'e2', source: 'a', target: 'b' }] }] }
    const e = toV3(tran).pages[0].edges[0]
    expect([e.source_port, e.target_port]).toEqual(['out', 'in'])
  })

  it('vong tron v2 -> v3 -> v2 khong danh roi cong', () => {
    const lai = fromV3(toV3(v2))
    expect(lai.version).toBe(2)
    expect(lai.pages[0].edges[0].sourceHandle).toBe('anh_ra')
    expect(lai.pages[0].edges[0].targetHandle).toBe('van_ban_vao')
  })

  it('trang v3 THIEU truong trinh bay (tai lieu rong cua may chu) van dung duoc', () => {
    // Dung hinh dang `apps/agent/routes/drafts_v3.py::_tai_lieu_rong()`: trang
    // khong co viewport/frames/notes/comments/view. Truoc ban sua, `CanvasShell`
    // goi `page.frames.map` tren `undefined` va ca canvas thanh man den.
    const rong = { version: 3 as const, goal: '', budget_max_credit: 0,
      active_page_id: 'p1',
      pages: [{ id: 'p1', name: '', nodes: [], edges: [] }] }
    const page = fromV3(rong as unknown as Parameters<typeof fromV3>[0]).pages[0]
    expect(page.frames).toEqual([])
    expect(page.notes).toEqual([])
    expect(page.comments).toEqual([])
    expect(page.viewport).toEqual({ x: 0, y: 0, zoom: 1 })
    expect(page.nodes).toEqual([])
  })

  it('toV3 tren mot tai lieu DA la v3 tra ve nguyen (luy dang)', () => {
    const ba = toV3(v2)
    expect(toV3(ba)).toBe(ba)
  })

  it('nang v1 thang len v3', () => {
    const v1 = { version: 1 as const, goal: 'g', budget_max_credit: 5,
      nodes: [], edges: [{ id: 'e', source: 'a', target: 'b' }],
      viewport: { x: 0, y: 0, zoom: 1 } }
    const ra = toV3(v1)
    expect(ra.version).toBe(3)
    expect(ra.pages[0].edges[0].source_node).toBe('a')
  })
})

// ── Cua v3 (Dot 5.2 phan D) ────────────────────────────────────────────────
describe('cua v3', () => {
  const rawV3 = {
    id: 'w3', name: 'W3', published_version_id: '', revision: 4,
    document: { version: 3 as const, goal: 'g', budget_max_credit: 10,
      active_page_id: 'p1',
      pages: [{ id: 'p1', name: 'P', nodes: [],
        edges: [{ id: 'e1', source_node: 'a', target_node: 'b',
          source_port: 'anh_ra', target_port: 'van_ban_vao',
          kind: 'DATA' as const }],
        viewport: { x: 0, y: 0, zoom: 1 }, frames: [], notes: [], comments: [] }] },
  }

  it('nap: v3 -> hinh dang React Flow, cong KHONG mat', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(
      JSON.stringify(rawV3), { status: 200,
        headers: { 'Content-Type': 'application/json' } }))
    const wf = await loadWorkflowV3('w3')
    expect(wf.revision).toBe(4)
    expect(wf.canvas.version).toBe(2)          // hinh dang trinh soan
    const e = wf.canvas.pages[0].edges[0]
    expect([e.sourceHandle, e.targetHandle]).toEqual(['anh_ra', 'van_ban_vao'])
  })

  it('luu: gui v3 len may chu, kem If-Match va CSRF', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(rawV3), { status: 200,
        headers: { 'Content-Type': 'application/json' } }))
    const wf = { id: 'w3', name: 'W3', status: 'draft' as const, revision: 4,
      estimated: 0, canvas: fromV3(rawV3.document) }
    await saveWorkflowV3(wf, 'csrf-v3')
    const [url, init] = fetchMock.mock.calls[0]
    expect(String(url)).toContain('/agent/api/v3/workflows/w3')
    expect(new Headers(init!.headers).get('If-Match')).toBe('"4"')
    expect(new Headers(init!.headers).get('X-CSRF-Token')).toBe('csrf-v3')
    const body = JSON.parse(String(init!.body))
    // ⭐ Gui di phai la v3: `source_port`, khong phai `sourceHandle`.
    expect(body.document.version).toBe(3)
    expect(body.document.pages[0].edges[0].source_port).toBe('anh_ra')
    expect(JSON.stringify(body.document)).not.toContain('sourceHandle')
  })

  it('xung dot revision noi len thanh WorkflowConflictError', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('{}', { status: 409 }))
    const wf = { id: 'w3', name: 'W3', status: 'draft' as const, revision: 1,
      estimated: 0, canvas: fromV3(rawV3.document) }
    await expect(saveWorkflowV3(wf, 'c')).rejects.toBeInstanceOf(WorkflowConflictError)
  })

  it('da publish thi status la validated', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(
      JSON.stringify({ ...rawV3, published_version_id: 'v9' }), { status: 200,
        headers: { 'Content-Type': 'application/json' } }))
    expect((await loadWorkflowV3('w3')).status).toBe('validated')
  })
})

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status, headers: { 'Content-Type': 'application/json' } })
}

const runV3: RunV3 = { id: 'r1', workflow_id: 'w1', version_id: 'v1',
  status: 'QUEUED', credit_max: 3, credit_charged: 0, settled: false,
  created_at: '2026-09-24T00:00:00+00:00',
  nodes: [{ node_id: 'a', status: 'PENDING', attempt: 1, cost_credit: 0,
            job_id: '', error: '', waiting_kind: '', het_han: false }],
  su_kien: [{ seq: 1, loai: 'WorkflowStarted', node_id: '', du_lieu: {},
              created_at: '2026-09-24T00:00:00+00:00' }],
  seq_cuoi: 1 }

describe('run v3', () => {
  it('createRunV3 gọi cửa v3 kèm CSRF', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValue(json(runV3, 201))
    expect(await createRunV3('w1', 'tok', 'khoa-bam-lan-1')).toEqual(runV3)
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/agent/api/v3/workflows/w1/runs')
    expect((init as RequestInit).method).toBe('POST')
    expect((init as RequestInit & { headers: Record<string, string> })
      .headers['X-CSRF-Token']).toBe('tok')
  })

  it('createRunV3 gửi Idempotency-Key do NGƯỜI GỌI đưa vào', async () => {
    // 🔑 Khoa phai den TU BEN NGOAI. Neu `createRunV3` tu sinh khoa thi moi
    //    loi goi la mot khoa moi — trong nhu co chong trung, ma khong chong
    //    duoc gi: bam hai lan van ra hai run, hai lan giu cho, hai lan tru tien.
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValue(json(runV3, 201))
    await createRunV3('w1', 'tok', 'khoa-cua-mot-lan-bam')
    expect(new Headers(fetchMock.mock.calls[0][1]!.headers)
      .get('Idempotency-Key')).toBe('khoa-cua-mot-lan-bam')
  })

  it('createRunV3 gửi ĐÚNG khoá được đưa, không tự chế ra khoá khác', async () => {
    // 🔑 Ve doi chung cho bai tren: mot ban va bo qua tham so va gui hang so
    //    cung se lam bai tren xanh. Hai khoa khac nhau phai ra hai header khac.
    // ⚠️ `mockResolvedValue` tra CUNG mot `Response` cho ca hai loi goi, va
    //    than cua no chi doc duoc MOT lan ("Body is unusable"). Bai hai lan goi
    //    phai dung `mockImplementation` de moi lan co mot `Response` moi.
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockImplementation(async () => json(runV3, 201))
    await createRunV3('w1', 'tok', 'khoa-A-dai-hon-8')
    await createRunV3('w1', 'tok', 'khoa-B-dai-hon-8')
    const doc = fetchMock.mock.calls.map(
      ([, init]) => new Headers(init!.headers).get('Idempotency-Key'))
    expect(doc).toEqual(['khoa-A-dai-hon-8', 'khoa-B-dai-hon-8'])
  })

  it('loadRunV3 gửi con trỏ sau= để chỉ lấy sự kiện mới', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValue(json({ ...runV3, su_kien: [], seq_cuoi: 7 }))
    const next = await loadRunV3('r1', 7)
    expect(fetchMock.mock.calls[0][0]).toBe('/agent/api/v3/runs/r1?sau=7')
    expect(next.seq_cuoi).toBe(7)
  })

  it('cancelRunV3 dịch 409 thành lỗi đọc được, không nuốt', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      json({ detail: { ma: 'da_ket_thuc', thong_diep: 'Đã kết thúc.' } }, 409))
    await expect(cancelRunV3('r1', 'tok')).rejects.toThrow('Đã kết thúc.')
  })

  it('RUN_V3_KET_THUC phủ đủ 5 trạng thái kết thúc của run', () => {
    expect([...RUN_V3_KET_THUC].sort()).toEqual(
      ['CANCELLED', 'FAILED', 'SUCCEEDED', 'SYSTEM_FAILURE', 'TIMED_OUT'])
  })
})

describe('lỗi biên dịch 422 giữ được ma + node_id', () => {
  it('publish 422 ném WorkflowCompileError mang node_id', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(json({ detail: {
      ma: 'bieu_thuc_chua_ho_tro', node_id: 'n_2',
      thong_diep: 'Biểu thức chưa hỗ trợ.' } }, 422))
    // 🔴 Trước bản này `decode()` bóp object thành chuỗi: `ma` và `node_id`
    //    biến mất, nên giao diện không tô được node hỏng — người dùng chỉ
    //    thấy một câu tiếng Việt và phải tự dò 40 node.
    const loi = await publishWorkflowV3(
      { id: 'w1' } as never, 'tok').catch(e => e)
    expect(loi).toBeInstanceOf(WorkflowCompileError)
    expect(loi.ma).toBe('bieu_thuc_chua_ho_tro')
    expect(loi.nodeId).toBe('n_2')
    expect(loi.message).toBe('Biểu thức chưa hỗ trợ.')
  })

  it('422 KHÔNG có `ma` vẫn là Error thường', async () => {
    // 🔑 Vế đối chứng: nếu mọi 422 đều thành WorkflowCompileError thì lớp
    //    lỗi mới không còn nói lên điều gì.
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      json({ detail: 'Tài liệu rỗng.' }, 422))
    const loi = await publishWorkflowV3({ id: 'w1' } as never, 'tok')
      .catch(e => e)
    expect(loi).not.toBeInstanceOf(WorkflowCompileError)
    expect(loi.message).toBe('Tài liệu rỗng.')
  })
})

describe('decode() không bóp méo lỗi máy chủ', () => {
  it('detail dạng MẢNG (lỗi validate FastAPI) không ra "[object Object]"', async () => {
    // 🔴 `/agent/**` KHÔNG đi qua bộ viết lại của `server/api/errors.py`
    //    (nó chỉ nhận `/api/v1`), nên lỗi validate rơi vào bộ xử lý mặc định
    //    của FastAPI và `detail` là một MẢNG. Mảng bị nhánh object loại ra,
    //    rồi `new Error(detail as string)` in đúng chữ "[object Object]" lên
    //    màn hình người dùng. Hình dạng dưới đây là thứ `sau: int = Query(0,
    //    ge=0)` thật sự trả cho `loadRunV3('r1', -1)`.
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(json({ detail: [{
      type: 'greater_than_equal', loc: ['query', 'sau'],
      msg: 'Input should be greater than or equal to 0',
      input: '-1', ctx: { ge: 0 } }] }, 422))
    const loi = await loadRunV3('r1', -1).catch(e => e)
    expect(loi.message).not.toBe('[object Object]')
    expect(loi.message).toContain('greater_than_equal')
  })

  it('402 thieu_credit KHÔNG phải lỗi biên dịch đồ thị', async () => {
    // 🔑 Hết credit là chuyện của ví, không phải của node nào cả. Ném
    //    WorkflowCompileError với `nodeId` rỗng làm giao diện xử lý nó như
    //    lỗi biên dịch — đúng kiểu gộp nhầm mà vòng trước vừa gỡ cho 409.
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(json({ detail: {
      ma: 'thieu_credit', thong_diep: 'Không đủ credit.' } }, 402))
    const loi = await createRunV3('w1', 'tok', 'khoa-bai-loi').catch(e => e)
    expect(loi).not.toBeInstanceOf(WorkflowCompileError)
    expect(loi.message).toBe('Không đủ credit.')
  })

  it('503 dong_co_chua_san_sang KHÔNG phải lỗi biên dịch đồ thị', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(json({ detail: {
      ma: 'dong_co_chua_san_sang', thong_diep: 'Động cơ chưa sẵn sàng.' } }, 503))
    const loi = await createRunV3('w1', 'tok', 'khoa-bai-loi').catch(e => e)
    expect(loi).not.toBeInstanceOf(WorkflowCompileError)
    expect(loi.message).toBe('Động cơ chưa sẵn sàng.')
  })

  it('422 có `ma` nhưng KHÔNG có node_id vẫn là Error thường', async () => {
    // `inputs_qua_lon`/`chua_publish` mang `ma` nhưng không chỉ được node nào.
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(json({ detail: {
      ma: 'chua_publish', thong_diep: 'Workflow chưa publish.' } }, 422))
    const loi = await createRunV3('w1', 'tok', 'khoa-bai-loi').catch(e => e)
    expect(loi).not.toBeInstanceOf(WorkflowCompileError)
    expect(loi.message).toBe('Workflow chưa publish.')
  })

  it('422 có node_id VẪN ném WorkflowCompileError (vế đối chứng)', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(json({ detail: {
      ma: 'bieu_thuc_chua_ho_tro', node_id: 'n_9',
      thong_diep: 'Biểu thức chưa hỗ trợ.' } }, 422))
    const loi = await createRunV3('w1', 'tok', 'khoa-bai-loi').catch(e => e)
    expect(loi).toBeInstanceOf(WorkflowCompileError)
    expect(loi.nodeId).toBe('n_9')
    expect(loi.ma).toBe('bieu_thuc_chua_ho_tro')
  })
})

// ── Accept: application/json tuong minh (rui ro Cloudflare lot Sec-Fetch-*) ─
//
// Ban sua `da7fce81` phan biet "goi API" voi "dieu huong HTML" bang
// Sec-Fetch-Mode, lui ve Accept. Neu Cloudflare lot header Sec-Fetch-* thi
// vong poll (Accept: */*  mac dinh cua fetch()) se bi coi la dieu huong va
// quay lai 302 — mat ban sua ma phep do loopback (khong qua Cloudflare) van
// xanh. Client phai tu gui Accept: application/json, khong phu thuoc header
// nao song sot qua Cloudflare.
describe('Accept: application/json tren moi loi goi API', () => {
  it('CHI CO MOT diem goi fetch() tho trong module — moi ham API phai di qua no', () => {
    // Kiem TINH nay bat duoc CA loi goi fetch() them SAU NAY ma khong qua
    // apiFetch(): mot phep kiem liet ke tay tung ham (9 ham hom nay) se mac
    // ngay khi ai do them ham thu 10. `fetch(` chu thuong (khac `apiFetch(`
    // vi khong co \b truoc chu F hoa) phai chi xuat hien DUY NHAT MOT lan —
    // ben trong apiFetch(), noi Accept duoc gan cho moi loi goi.
    const rawFetchCalls = workflowApiSource.match(/(?<![.\w])fetch\(/g) ?? []
    expect(rawFetchCalls).toHaveLength(1)
  })

  // Cua goi y §6 (P2 Task 8). ⚠️ No la duong ma CA hop autocomplete phu
  // thuoc vao: mot cu 302 ve /login o day lam hop goi y rong trong im lang —
  // dung hinh dang su co `da7fce81` da gay cho palette.
  it('goiYBieuThuc POST dung duong, gui Accept + CSRF va tai lieu v3', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ node_id: 'n1', muc: [], ham: [], loi: null }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }))
    const canvasThu = { version: 2 as const, goal: 'g', budget_max_credit: 10,
      active_page_id: 'page-1', pages: [{ id: 'page-1', name: 'Page 1', nodes: [],
        edges: [], viewport: { x: 0, y: 0, zoom: 1 }, frames: [], notes: [], comments: [] }] }
    await goiYBieuThuc('w1', 'n1', canvasThu, 'csrf-test')
    const [url, init] = fetchMock.mock.calls[0]
    expect(String(url)).toBe('/agent/api/v3/workflows/w1/bieu-thuc/goi-y')
    expect(init?.method).toBe('POST')
    const headers = new Headers(init!.headers)
    expect(headers.get('Accept')).toBe('application/json')
    expect(headers.get('X-CSRF-Token')).toBe('csrf-test')
    // Tai lieu gui di phai la v3 (canh mang CONG), khong phai v2.
    expect(JSON.parse(String(init?.body)).document.version).toBe(3)
  })

  it('PUT (saveWorkflowV3) gui Accept ma khong de de ghi Content-Type', async () => {
    const rawV3Toi = { id: 'w3', name: 'W3', published_version_id: '', revision: 4,
      document: { version: 3 as const, goal: '', budget_max_credit: 0,
        active_page_id: 'p1', pages: [{ id: 'p1', name: 'P', nodes: [], edges: [],
          viewport: { x: 0, y: 0, zoom: 1 }, frames: [], notes: [], comments: [] }] } }
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(rawV3Toi), { status: 200,
        headers: { 'Content-Type': 'application/json' } }))
    await saveWorkflowV3({ id: 'w3', name: 'W3', status: 'draft', revision: 4,
      estimated: 0, canvas: fromV3(rawV3Toi.document) }, 'csrf-test')
    const headers = new Headers(fetchMock.mock.calls[0][1]!.headers)
    expect(headers.get('Accept')).toBe('application/json')
    expect(headers.get('Content-Type')).toBe('application/json')
  })

  it('poll v3 (loadRunV3, vong 1,5s) gui Accept — dung ca khi Sec-Fetch-* bi lot', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(json(runV3))
    await loadRunV3('r1', 0)
    expect(new Headers(fetchMock.mock.calls[0][1]?.headers).get('Accept'))
      .toBe('application/json')
  })
})
