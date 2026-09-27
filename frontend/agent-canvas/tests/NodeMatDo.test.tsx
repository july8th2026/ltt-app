/** UI-4 — ba mức mật độ, hai trục trạng thái, và HAI câu node từng nói SAI.
 *
 *  🔴 PHẠM VI CỦA TỆP NÀY HẸP HƠN TÊN NÓ, nói thẳng ra ở đầu tệp:
 *     jsdom ⛔ KHÔNG tính layout. Mọi `getBoundingClientRect()` trả 0, nên một
 *     phép so chiều cao ("node ≤ 320px") ở đây sẽ XANH GIẢ — nó xanh cả khi
 *     node cao 525px. Tệp này kiểm được đúng ba thứ:
 *       1. phép TÍNH (mức nào, cổng nào vào hàng, câu nào in ra) — thuần hàm;
 *       2. CÓ MẶT / VẮNG MẶT trong DOM (cổng nào còn handle, dấu nào còn);
 *       3. thuộc tính `data-*` mà CSS treo lên.
 *     Chiều cao thật, vị trí cổng thật và `elementFromPoint` đo bằng Playwright
 *     trên máy chủ cô lập — `tests/browser/agent_ui_v2_ui4_nghiem_thu.js`.
 */
import { cleanup, render, screen } from '@testing-library/react'
import { ReactFlowProvider } from '@xyflow/react'
import { afterEach, describe, expect, it } from 'vitest'
import { NodeRenderer } from '../src/nodes/NodeRenderer'
import { NGUONG_ZOOM_COMPACT, RONG_MUC, laVoHuong, mucDoNode, phanLoaiCong }
  from '../src/nodes/matDo'
import { dinhDangThoiLuong, huyHieuNode, nhanTomTatChay, soNhanh,
  sucKhoeTuStatus, tomTatCauHinh } from '../src/nodes/tomTat'
import type { Cong, NodeDefinition, NodeKind } from '../src/nodeDefinition'

afterEach(cleanup)

const cong = (ten: string, kieu: string, bat_buoc = false): Cong =>
  ({ ten, kieu, bat_buoc, nhieu: false })

const nd = (kind: NodeKind, over: Partial<NodeDefinition> = {}): NodeDefinition =>
  ({ type: `x.${kind}`, type_version: 2, kind, category: 'LTT_APPS',
     title: 'Tạo Video Seedance', description: 'mo ta dai bi cat 60 ky tu',
     icon: 'I', app_name: 'Tạo video AI',
     cong_vao: [cong('prompt', 'text', true)],
     cong_ra: [cong('video_key', 'video', true)],
     tham_so: { type: 'object', properties: {}, required: [] }, thi_hanh: 'job',
     side_effect: 'external', resource: { class: 'api' },
     timeout_expr: '', retry_mac_dinh: { max: 0, backoff_s: 30 },
     gia: { kieu: 'theo_registry', so: 0, job_type: 'taovideo.generate' },
     credential: [], quyen: ['network'], cho: ['JOB'], ma_loi: [],
     co_mock: false, publish_duoc: true, ...over })

/** 15 tham số THẬT của `app.video.generate` (`apps/taovideo/manifest.py`) đi
 *  qua `luoc_do.cong_vao()`: mỗi tham số là MỘT cổng vào. Đây là node làm nên
 *  con số 525px, nên phép kiểm dùng đúng hình dạng của nó, ⛔ không bịa. */
const VIDEO_GENERATE = nd('app', {
  type: 'app.video.generate', type_version: 1,
  // Hai ten THAT cua `apps/taovideo/manifest.py`, va chung khac nhau — do la
  // ca diem cua `01 §4.1`: `title` la cau bi cat, `app_name` la ten dung duoc.
  title: 'Sinh video từ mô tả', app_name: 'Tạo Video Seedance',
  cong_vao: [
    cong('prompt', 'text', true), cong('model', 'model_ref'),
    cong('resolution', 'text'), cong('duration', 'text'),
    cong('aspect_ratio', 'text'), cong('generate_audio', 'boolean'),
    cong('camera', 'text'), cong('motion', 'text'),
    cong('visual_style', 'text'), cong('seed', 'number'),
    cong('image_key', 'image'), cong('image_keys', 'image[]'),
    cong('video_key', 'video'), cong('audio_key', 'audio'),
    cong('refs', 'json'),
  ],
  cong_ra: [cong('video_key', 'video', true)],
  // ⭐ `tham_so.properties` va `cong_vao` la 1:1 tren node nay, va do khong
  //    phai trung hop: `luoc_do.cong_vao()` sinh MOT cong cho MOI tham so cua
  //    `params_schema`. Chinh quy tac ay lam node cao 525px, nen fixture phai
  //    mang dung quan he do.
  tham_so: { type: 'object', required: ['prompt'],
             properties: Object.fromEntries([
               'prompt', 'model', 'resolution', 'duration', 'aspect_ratio',
               'generate_audio', 'camera', 'motion', 'visual_style', 'seed',
               'image_key', 'image_keys', 'video_key', 'audio_key', 'refs',
             ].map(k => [k, { type: 'string' }])) },
})

type DuLieu = Record<string, unknown>
const ve = (dinhNghia: NodeDefinition, du: DuLieu = {}, chon = false) => render(
  <ReactFlowProvider>
    <NodeRenderer id="n1" type="ltt" selected={chon} zIndex={0} isConnectable
      selectable deletable draggable
      positionAbsoluteX={0} positionAbsoluteY={0} dragging={false}
      data={{ dinhNghia, ...du }} />
  </ReactFlowProvider>)

const khung = () => screen.getByTestId('node-khung')

// ── 1. Ba mức mật độ, TỰ ĐỘNG ─────────────────────────────────────────────

describe('mucDoNode — tu dong theo zoom + trang thai chon (Q7)', () => {
  it('zoom binh thuong => normal; duoi nguong => compact', () => {
    expect(mucDoNode({ zoom: 1, dangChon: false })).toBe('normal')
    expect(mucDoNode({ zoom: NGUONG_ZOOM_COMPACT, dangChon: false })).toBe('normal')
    expect(mucDoNode({ zoom: NGUONG_ZOOM_COMPACT - 0.01, dangChon: false }))
      .toBe('compact')
    expect(mucDoNode({ zoom: 0.2, dangChon: false })).toBe('compact')
  })

  it('dang chon THANG zoom — chon la mot hanh vi tuong minh', () => {
    expect(mucDoNode({ zoom: 0.2, dangChon: true })).toBe('expanded')
    expect(mucDoNode({ zoom: 1, dangChon: true })).toBe('expanded')
  })

  it('co artifact media => expanded, ke ca khi khong duoc chon', () => {
    expect(mucDoNode({ zoom: 1, dangChon: false, coArtifactMedia: true }))
      .toBe('expanded')
  })

  it('ba be rong la BA con so khac nhau, dung thang cua spec 09 §3.1', () => {
    expect(RONG_MUC).toEqual({ compact: 200, normal: 280, expanded: 360 })
  })
})

describe('NodeRenderer doc zoom tu store React Flow', () => {
  it('zoom mac dinh (1) => node ve o muc normal', () => {
    ve(VIDEO_GENERATE)
    expect(khung()).toHaveAttribute('data-muc-do', 'normal')
    expect(khung()).toHaveStyle({ '--node-rong': '280px' })
  })

  it('node duoc chon => expanded, va be rong doi theo', () => {
    ve(VIDEO_GENERATE, {}, true)
    expect(khung()).toHaveAttribute('data-muc-do', 'expanded')
    expect(khung()).toHaveStyle({ '--node-rong': '360px' })
  })
})

// ── 2. Node chỉ mang 5 thứ ────────────────────────────────────────────────

describe('node chi mang NAM thu (09 §3.2)', () => {
  it('MOI cong van co handle o ca ba muc — ⛔ khong mot cong nao bien mat', () => {
    // 🔴 Bo ve mot handle la lam dut MOI canh dang tro vao no: React Flow
    //    khong tim thay handle thi no vut canh va khong noi gi. "Gon" ⛔ khong
    //    duoc phep thanh "mat".
    for (const muc of ['compact', 'normal', 'expanded'] as const) {
      ve(VIDEO_GENERATE, { mucDoEp: muc })
      const vao = document.querySelectorAll('.react-flow__handle.target')
      const ra = document.querySelectorAll('.react-flow__handle.source')
      expect(vao.length, `muc ${muc}: cong vao`).toBe(15)
      expect(ra.length, `muc ${muc}: cong ra`).toBe(1)
      // Moi handle mang dung `id` cua cong — do la thu canh tro vao.
      expect([...vao].map(h => h.getAttribute('data-handleid')))
        .toContain('generate_audio')
      cleanup()
    }
  })

  it('normal: cong vo huong TUT XUONG KHAY (khong nhan chu), media o lai hang', () => {
    ve(VIDEO_GENERATE, { mucDoEp: 'normal' })
    // `prompt` bat buoc => hang co nhan.
    expect(screen.getByTitle('prompt · text')).toHaveClass('node-cong')
    // `image_keys` kieu media/mang => hang co nhan.
    expect(screen.getByTitle('image_keys · image[]')).toHaveClass('node-cong')
    // `seed`/`camera` vo huong, khong bat buoc, khong noi => KHAY.
    expect(screen.getByTitle('seed · number')).toHaveClass('node-khay-o')
    expect(screen.getByTitle('camera · text')).toHaveClass('node-khay-o')
    // Va khong mot nhan chu nao cua chung tren mat node.
    expect(screen.queryByText('seed')).not.toBeInTheDocument()
  })

  it('cong DANG CO DAY giu nhan o normal, du no vo huong', () => {
    ve(VIDEO_GENERATE, { mucDoEp: 'normal', congDaNoi: ['seed'] })
    expect(screen.getByTitle('seed · number')).toHaveClass('node-cong')
    expect(screen.getByText('seed')).toBeInTheDocument()
  })

  it('expanded: moi cong ve hang co nhan; compact: moi cong vao khay', () => {
    ve(VIDEO_GENERATE, { mucDoEp: 'expanded' })
    expect(document.querySelectorAll('.node-cong').length).toBe(16)
    expect(document.querySelectorAll('.node-khay-o').length).toBe(0)
    cleanup()
    ve(VIDEO_GENERATE, { mucDoEp: 'compact' })
    expect(document.querySelectorAll('.node-cong').length).toBe(0)
    expect(document.querySelectorAll('.node-khay-o').length).toBe(16)
  })

  it('⛔ `app.video.generate@1` KHONG con tren mat node, no o tooltip', () => {
    ve(VIDEO_GENERATE, { mucDoEp: 'normal' })
    // Phan tu van trong DOM (danh tinh MAY doc) — nhung mang lop bi
    // `display:none`, va chuoi ay co mat trong `title` cua ca node.
    expect(document.querySelector('.node-type')?.textContent)
      .toBe('app.video.generate@1')
    expect(khung()).toHaveAttribute('title',
      'Tạo Video Seedance — app.video.generate@1')
  })

  it('🔴 `app_name` LA tieu de, `title` tut xuong dong nho (01 §4.1)', () => {
    // Phan cap cu bi LON NGUOC: `title` ("Sinh video từ mô tả" — mot cau bi
    // cat 60 ky tu) to va dam nhat, con ten dung duoc nam o hang thu TU.
    ve(VIDEO_GENERATE, { mucDoEp: 'normal' })
    expect(screen.getByText('Tạo Video Seedance')).toHaveClass('node-tieu-de')
    // ⛔ `title` khong bi VUT — no chi tut xuong mot dong nho.
    expect(screen.getByTestId('node-ten-phu'))
      .toHaveTextContent('Sinh video từ mô tả')
  })

  it('node `core.*` co `app_name` RONG => `title` len tieu de, khong dong phu', () => {
    ve(CORE_STOP, { mucDoEp: 'normal' })
    expect(screen.getByText('Dừng')).toHaveClass('node-tieu-de')
    expect(screen.queryByTestId('node-ten-phu')).not.toBeInTheDocument()
  })

  it('⛔ KHONG dung `description` lam tieu de (01 §4.1)', () => {
    ve(VIDEO_GENERATE, { mucDoEp: 'normal' })
    expect(screen.queryByText(/mo ta dai bi cat/)).not.toBeInTheDocument()
  })

  it('phanLoaiCong: `expanded` khong bao gio dung khay', () => {
    const cs = [cong('a', 'text'), cong('b', 'image')]
    expect(phanLoaiCong(cs, new Set(), 'expanded')).toEqual({ hang: cs, khay: [] })
    expect(phanLoaiCong(cs, new Set(), 'compact')).toEqual({ hang: [], khay: cs })
  })

  it('laVoHuong: mang va media KHONG bao gio vo huong', () => {
    expect(laVoHuong('text')).toBe(true)
    expect(laVoHuong('number')).toBe(true)
    expect(laVoHuong('model_ref')).toBe(true)
    expect(laVoHuong('image')).toBe(false)
    expect(laVoHuong('json')).toBe(false)
    expect(laVoHuong('any')).toBe(false)
    expect(laVoHuong('text[]')).toBe(false)
    // Kieu la cua may chu => KHONG vo huong (an toan ve phia "co nhan").
    expect(laVoHuong('kieu_may_chu_moi')).toBe(false)
  })
})

// ── 3. Hai trục trạng thái ────────────────────────────────────────────────

describe('hai truc trang thai (09 §3.3)', () => {
  it('bay gia tri suc khoe, va CANCELLED ⛔ khong phai failed', () => {
    expect(sucKhoeTuStatus('RUNNING')).toBe('running')
    expect(sucKhoeTuStatus('WAITING')).toBe('waiting')
    expect(sucKhoeTuStatus('RETRY_SCHEDULED')).toBe('waiting')
    expect(sucKhoeTuStatus('SUCCEEDED')).toBe('succeeded')
    expect(sucKhoeTuStatus('FAILED')).toBe('failed')
    expect(sucKhoeTuStatus('SKIPPED')).toBe('skipped')
    // Nguoi dung bam huy thi khong co gi hong — mot vien do o day la mot loi
    // buoc toi sai.
    expect(sucKhoeTuStatus('CANCELLED')).toBe('skipped')
    expect(sucKhoeTuStatus(undefined)).toBe('idle')
    expect(sucKhoeTuStatus('MOT_STATUS_LA')).toBe('idle')
  })

  it('vien treo tren `data-suc-khoe`, ke ca `stale`', () => {
    for (const sk of ['idle', 'running', 'waiting', 'succeeded', 'failed',
                      'skipped', 'stale'] as const) {
      ve(nd('app'), { sucKhoe: sk })
      expect(khung()).toHaveAttribute('data-suc-khoe', sk)
      cleanup()
    }
  })

  it('🔴 loi CAU HINH va loi CHAY la HAI huy hieu khac nhau', () => {
    const hh = huyHieuNode({ loiBienDich: 'thieu_tham_so', loiChay: 'timeout' })
    expect(hh.map(h => h.loai)).toEqual(['loi_cau_hinh', 'loi_chay'])
    // Hai hanh dong khac nhau: sua o cau hinh, hay chay lai. Gop mot huy hieu
    // do la bat nguoi dung tu doan minh dang o ca nao.
    expect(hh[0].moTa).toContain('Lỗi cấu hình')
    expect(hh[1].moTa).toContain('Lỗi khi chạy')
  })

  it('huy hieu dinh luong: thieu ket noi va so lan thu', () => {
    expect(huyHieuNode({ thieuKetNoi: 2 })[0]).toMatchObject(
      { loai: 'thieu_ket_noi', nhan: '2' })
    // Lan thu 1 la binh thuong — ⛔ khong bao dong.
    expect(huyHieuNode({ lanThu: 1 })).toEqual([])
    expect(huyHieuNode({ lanThu: 3 })[0]).toMatchObject(
      { loai: 'so_lan_thu', nhan: '↻3' })
    expect(huyHieuNode({})).toEqual([])
  })

  it('huy hieu ve ra DOM va ⛔ khong bao gio bat chuot', () => {
    ve(nd('app'), { huyHieu: huyHieuNode({ thieuKetNoi: 1 }) })
    const hh = screen.getByTestId('node-huy-hieu')
    expect(hh).toHaveClass('node-huy-hieu')
    expect(hh.querySelector('.node-hh-thieu_ket_noi')?.textContent).toBe('1')
  })

  it('tom tat luot chay: credit · thoi luong · lan thu', () => {
    expect(nhanTomTatChay({ credit: 12, thoiLuongS: 64, lanThu: 1 }))
      .toBe('12 credit · 1m 04s')
    expect(nhanTomTatChay({ credit: 0, lanThu: 2 })).toBe('0 credit · lần 2')
    expect(nhanTomTatChay(undefined)).toBe('')
    // ⭐ `thoiLuongS` VANG khac `thoiLuongS === 0`: "khong do duoc" va "0 giay"
    //    la hai cau khac nhau.
    expect(nhanTomTatChay({ credit: 3 })).toBe('3 credit')
    expect(nhanTomTatChay({ credit: 3, thoiLuongS: 0 })).toBe('3 credit · 0ms')
  })

  it('dinhDangThoiLuong khong nhay bac', () => {
    expect(dinhDangThoiLuong(0.25)).toBe('250ms')
    expect(dinhDangThoiLuong(3.4)).toBe('3.4s')
    expect(dinhDangThoiLuong(42)).toBe('42s')
    expect(dinhDangThoiLuong(125)).toBe('2m 05s')
  })

  it('chan node chi ve khi CO tom tat chay', () => {
    ve(nd('app'), { mucDoEp: 'normal' })
    expect(screen.queryByTestId('node-tom-tat-chay')).not.toBeInTheDocument()
    cleanup()
    ve(nd('app'), { mucDoEp: 'normal', tomTatChay: { credit: 12 } })
    expect(screen.getByTestId('node-tom-tat-chay')).toHaveTextContent('12 credit')
  })
})

// ── 4. 🔴 HAI câu node từng nói SAI (`01 §4.2`) ────────────────────────────

const CORE_STOP = nd('control', {
  type: 'core.stop', type_version: 1, title: 'Dừng', app_name: '',
  cong_vao: [cong('in', 'any')], cong_ra: [],
  tham_so: { type: 'object',
             properties: { trang_thai: { type: 'string' },
                           ly_do: { type: 'string' } }, required: [] } })

const CORE_SWITCH = nd('control', {
  type: 'core.switch', type_version: 1, title: 'Rẽ nhiều nhánh', app_name: '',
  cong_vao: [cong('in', 'any')], cong_ra: [cong('nhanh', 'control')],
  tham_so: { type: 'object',
             properties: { bieu_thuc: { type: 'string' },
                           nhanh: { type: 'array' },
                           mac_dinh: { type: 'string' } },
             required: ['bieu_thuc', 'nhanh'] } })

const CORE_IF = nd('control', {
  type: 'core.if', type_version: 1, title: 'Rẽ nhánh', app_name: '',
  cong_vao: [cong('in', 'any')],
  cong_ra: [cong('true', 'control'), cong('false', 'control')],
  tham_so: { type: 'object', properties: { dieu_kien: { type: 'string' } },
             required: ['dieu_kien'] } })

describe('🔴 soNhanh — `cong_ra.length` ⛔ KHONG phai dai luong "so nhanh"', () => {
  it('core.stop: KHONG re nhanh => `undefined`, va node ⛔ khong in "0 nhánh"', () => {
    expect(soNhanh(CORE_STOP, {})).toBeUndefined()
    ve(CORE_STOP, { mucDoEp: 'normal', params: { trang_thai: 'SUCCEEDED' } })
    expect(screen.queryByText(/nhánh/)).not.toBeInTheDocument()
    // Thay vao do node noi dieu no THAT SU lam.
    expect(screen.getByTestId('node-tom-tat')).toHaveTextContent('SUCCEEDED')
  })

  it('core.switch: so nhanh doc tu THAM SO `nhanh`, ⛔ khong tu cong ra', () => {
    // Cong ra cua `core.switch` LUON la 1 (`nhanh`) — do la vi sao node cu in
    // "1 nhánh" voi moi cau hinh.
    expect(CORE_SWITCH.cong_ra.length).toBe(1)
    expect(soNhanh(CORE_SWITCH, { nhanh: ['vi', 'en', 'ja'] }))
      .toEqual({ so: 3, ten: ['vi', 'en', 'ja'] })
    // ⭐ Tu ba nhanh tro xuong, node in TEN — ten vua la danh tinh vua LA con
    //    so, va no tra loi cau hoi thuc su ("nhanh nao?") thay vi mot con so
    //    nguoi dung con phai mo Inspector ra doi chieu.
    ve(CORE_SWITCH, { mucDoEp: 'normal', params: { nhanh: ['vi', 'en', 'ja'] } })
    expect(screen.getByTestId('node-tom-tat')).toHaveTextContent('vi · en · ja')
    // 🔴 Cau SAI cu — "1 nhánh" voi MOI cau hinh — khong con duong nao ra.
    expect(screen.queryByText('1 nhánh')).not.toBeInTheDocument()
  })

  it('core.switch qua ba nhanh: in SO, va so do dung', () => {
    const nhieu = ['vi', 'en', 'ja', 'ko', 'zh']
    expect(soNhanh(CORE_SWITCH, { nhanh: nhieu })?.so).toBe(5)
    ve(CORE_SWITCH, { mucDoEp: 'normal', params: { nhanh: nhieu } })
    expect(screen.getByTestId('node-tom-tat')).toHaveTextContent('5 nhánh')
  })

  it('core.switch: `mac_dinh` la MOT nhanh nua, va no doc duoc', () => {
    expect(soNhanh(CORE_SWITCH, { nhanh: ['vi'], mac_dinh: 'khac' }))
      .toEqual({ so: 2, ten: ['vi', 'khac (mặc định)'] })
    // `mac_dinh` trung mot nhanh da khai thi ⛔ khong dem hai lan.
    expect(soNhanh(CORE_SWITCH, { nhanh: ['vi', 'en'], mac_dinh: 'vi' })?.so)
      .toBe(2)
  })

  it('core.switch chua cau hinh: `nhanh` rong => 0 nhanh, va do la SU THAT', () => {
    expect(soNhanh(CORE_SWITCH, { nhanh: [] })).toEqual({ so: 0, ten: [] })
    ve(CORE_SWITCH, { mucDoEp: 'normal', params: { nhanh: [] } })
    expect(screen.getByTestId('node-tom-tat')).toHaveTextContent('0 nhánh')
  })

  it('core.if: cong ra CHINH la nhanh => in TEN, khong in so', () => {
    expect(soNhanh(CORE_IF, { dieu_kien: 'x > 1' }))
      .toEqual({ so: 2, ten: ['true', 'false'] })
    ve(CORE_IF, { mucDoEp: 'normal', params: { dieu_kien: 'x > 1' } })
    expect(screen.getByTestId('node-tom-tat')).toHaveTextContent('true · false')
  })

  it('node `app` MOT cong ra ⛔ khong bao gio bi goi la mot nhanh', () => {
    expect(soNhanh(VIDEO_GENERATE, {})).toBeUndefined()
  })
})

describe('tomTatCauHinh — mot DONG, ⛔ khong phai mot form', () => {
  it('toi da ba tham so, gia tri dai bi cat', () => {
    // ⛔ Chua cau hinh KHONG roi ve `app_name`/`title`: ca hai da o tren mat
    //    node roi (tieu de + dong phu), lap lai la tieu mot dong de noi lai.
    expect(tomTatCauHinh(VIDEO_GENERATE, {})).toBe('Chưa cấu hình')
    const day = nd('app', { tham_so: { type: 'object', required: [], properties: {
      model: { type: 'string' }, resolution: { type: 'string' },
      duration: { type: 'string' }, seed: { type: 'number' } } } })
    expect(tomTatCauHinh(day, { model: 'seedance', resolution: '1080p',
      duration: '8s', seed: 7 })).toBe('seedance · 1080p · 8s')
  })

  it('gia tri rong / null bi bo qua, mang dem so muc, bool doc duoc', () => {
    const x = nd('app', { tham_so: { type: 'object', required: [], properties: {
      a: { type: 'string' }, b: { type: 'boolean' },
      c: { type: 'array' } } } })
    expect(tomTatCauHinh(x, { a: '', b: true, c: ['p', 'q'] }))
      .toBe('bật · 2 mục')
  })

  it('gia tri qua dai bi cat, ⛔ khong tran ra mot node cao them', () => {
    const x = nd('app', { tham_so: { type: 'object', required: [],
      properties: { prompt: { type: 'string' } } } })
    const t = tomTatCauHinh(x, { prompt: 'a'.repeat(200) })
    expect(t.length).toBeLessThanOrEqual(22)
    expect(t.endsWith('…')).toBe(true)
  })
})
