import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { RunV3Panel } from '../src/RunV3Panel'
import { BaoGiaTruocKhiChay } from '../src/features/editor/ExecutionPanel/BaoGiaTruocKhiChay'
import { tachLoi } from '../src/features/editor/ExecutionPanel/loiNguoiDoc'
import { runDuHinhDang, runGia, nodeGia, suKienGia, tenBuocGia, thamSoGia } from './runGia'

afterEach(cleanup)

/** Mặt THỰC THI V2 (làn UI-7, `09_TARGET_DESIGN.md §8`).
 *
 * ⭐ CÁCH NGHIỆM THU: đo lớp TRÌNH BÀY bằng dữ liệu run GIẢ (`tests/runGia.ts`),
 *    ⛔ KHÔNG bằng một lượt chạy thật. Worker nạp mã từ `C:\LTTPlatform\app`
 *    (bản ĐÃ DEPLOY) và chạy dưới `LocalSystem`, nên một job thật cho số thật
 *    nhưng trả lời câu KHÁC: nó đo bản deploy, không đo nhánh này. Lý do đầy đủ
 *    ở đầu `tests/runGia.ts`.
 */

const veRun = (props: Partial<Parameters<typeof RunV3Panel>[0]> = {}) =>
  render(<RunV3Panel run={runDuHinhDang()} onCancel={() => {}}
    tenBuoc={tenBuocGia} thamSo={thamSoGia} {...props}/>)

/** Hàng của dòng thời gian, tìm theo TÊN BƯỚC hiện trên màn hình. */
const hang = (ten: string) =>
  [...document.querySelectorAll<HTMLElement>('.run-timeline tbody tr')]
    .find(tr => tr.querySelector('button')?.textContent === ten)

describe('Dòng thời gian hiện TÊN BƯỚC, ⛔ không `node_id` thô', () => {
  it('cột đầu là tên bước cho mọi bước có nhãn', () => {
    veRun()
    const bang = document.querySelector('.run-timeline')!
    expect(within(bang as HTMLElement).getByRole('button', { name: 'Lấy dòng Sheet' })).toBeInTheDocument()
    expect(within(bang as HTMLElement).getByRole('button', { name: 'Tạo ảnh AI' })).toBeInTheDocument()
  })

  it('🔴 `node_id` thô KHÔNG xuất hiện ở cột đầu — kể cả node KHÔNG có nhãn', () => {
    veRun()
    const cotDau = [...document.querySelectorAll('.run-timeline-ten')]
      .map(td => td.textContent ?? '')
    // `nmujtmc1b-0` la chinh vi du trong `01_CURRENT_UI_AUDIT.md §6.1`.
    expect(cotDau.some(t => t.includes('nmujtmc1b-0'))).toBe(false)
    expect(cotDau.some(t => t.includes('n-cho'))).toBe(false)
    // Node khong co nhan lui ve "Bước N", ⛔ khong ve `node_id`.
    expect(cotDau.some(t => t.includes('Bước 5'))).toBe(true)
  })

  it('⛔ KHÔNG hiện thời lượng khi không đo được — `—`, không phải `0s`', () => {
    veRun()
    // `nmujtmc1b-0` co 2 su kien rieng (seq 16 -> 17) => do duoc 1s.
    const coDo = hang('Tạo ảnh AI')!
    expect(coDo.querySelector('.run-timeline-thoi-luong')!.textContent).toBe('1s')
    // `n-dang` khong co su kien nao rieng => khong do duoc.
    const khongDo = hang('Đăng YouTube')!
    expect(khongDo.querySelector('.run-timeline-thoi-luong')!.textContent).toBe('—')
    expect(khongDo.querySelector('.run-timeline-thoi-luong')!.textContent).not.toContain('0s')
  })
})

describe('Nhật ký — MỖI dòng có dấu thời gian', () => {
  it('mọi <li> nhật ký có một <time dateTime> đọc được', () => {
    veRun()
    const dong = [...document.querySelectorAll('.run-v3-su-kien > li')]
    expect(dong.length).toBe(7)
    for (const li of dong) {
      const moc = li.querySelector('time')
      expect(moc, `dòng "${li.textContent}" thiếu dấu thời gian`).toBeTruthy()
      expect(moc!.textContent).toMatch(/^\d{2}:\d{2}:\d{2}$/)
      expect(moc!.getAttribute('datetime')).toContain('2026-09-28T09:')
    }
  })

  it('sự kiện của một bước hiện TÊN bước, kể cả khi `node_id` nằm trong `du_lieu`', () => {
    veRun()
    const chuoi = [...document.querySelectorAll('.run-v3-su-kien > li')]
      .map(li => li.textContent ?? '')
    // `AgentStep` ghi node vao `du_lieu`, khong vao cot rieng (`tac_tu.py`).
    expect(chuoi.some(t => t.includes('AgentStep') && t.includes('Tạo ảnh AI'))).toBe(true)
    expect(chuoi.some(t => t.includes('nmujtmc1b-0'))).toBe(false)
  })
})

describe('Bấm một bước mở Inspector 12 trường CÓ NHÓM', () => {
  const MUOI_HAI = ['trang_thai', 'dau_vao', 'dau_ra', 'nhat_ky', 'loi', 'lan_thu',
    'thoi_luong', 'chi_phi', 'tai_nguyen', 'ly_do_cho', 'lich_su_thu_lai', 'artifact']

  it('chưa bấm thì KHÔNG có Inspector', () => {
    veRun()
    expect(document.querySelector('.run-node-inspector')).toBeNull()
  })

  it('bấm tên bước mở đủ 12 trường của §8', () => {
    veRun()
    fireEvent.click(screen.getByRole('button', { name: 'Tạo ảnh AI' }))
    const insp = document.querySelector<HTMLElement>('.run-node-inspector')!
    const co = [...insp.querySelectorAll('[data-truong]')]
      .map(el => el.getAttribute('data-truong'))
    for (const truong of MUOI_HAI) expect(co, `thiếu trường ${truong}`).toContain(truong)
    expect(co.length).toBe(MUOI_HAI.length)
  })

  it('các trường nằm trong NHÓM có tên, ⛔ không phải một khối phẳng', () => {
    veRun()
    fireEvent.click(screen.getByRole('button', { name: 'Tạo ảnh AI' }))
    const insp = document.querySelector<HTMLElement>('.run-node-inspector')!
    const nhom = [...insp.querySelectorAll('.run-nhom')]
    expect(nhom.length).toBeGreaterThanOrEqual(3)
    // Moi truong phai thuoc mot nhom — ⛔ khong co truong "roi".
    for (const el of insp.querySelectorAll('[data-truong]'))
      expect(el.closest('.run-nhom'), `trường ${el.getAttribute('data-truong')} không ở trong nhóm`).toBeTruthy()
    for (const g of nhom) expect(g.getAttribute('aria-label')).toBeTruthy()
  })

  it('`node_id` thô sống trong "Chi tiết kỹ thuật", ⛔ không ở dòng thời gian', () => {
    veRun()
    fireEvent.click(screen.getByRole('button', { name: 'Tạo ảnh AI' }))
    const kyThuat = document.querySelector<HTMLElement>('.run-node-inspector .run-ky-thuat')!
    expect(kyThuat.textContent).toContain('nmujtmc1b-0')
    expect(kyThuat.querySelector('summary')!.textContent).toContain('Chi tiết kỹ thuật')
  })

  it('🔴 "chưa có cửa dữ liệu" đọc KHÁC một giá trị thật (⛔ không phải ô trắng)', () => {
    veRun()
    fireEvent.click(screen.getByRole('button', { name: 'Đăng YouTube' }))
    const insp = document.querySelector<HTMLElement>('.run-node-inspector')!
    const thoiLuong = insp.querySelector<HTMLElement>('[data-truong="thoi_luong"] dd')!
    expect(thoiLuong.querySelector('.run-truong-trong')).toBeTruthy()
    expect(thoiLuong.textContent).not.toBe('')
    expect(thoiLuong.textContent).not.toContain('0s')
    // Nguoc lai: chi phi la so THAT, nen ⛔ khong duoc gan nhan "trong".
    const chiPhi = insp.querySelector<HTMLElement>('[data-truong="chi_phi"] dd')!
    expect(chiPhi.querySelector('.run-truong-trong')).toBeNull()
  })

  it('lý do chờ và lần thử lấy đúng từ `waiting_kind`/`attempt`', () => {
    veRun()
    fireEvent.click(screen.getByRole('button', { name: 'Tạo video' }))
    let insp = document.querySelector<HTMLElement>('.run-node-inspector')!
    expect(insp.querySelector('[data-truong="ly_do_cho"] dd')!.textContent)
      .toContain('chờ người duyệt')
    cleanup()
    veRun()
    fireEvent.click(screen.getByRole('button', { name: 'Tạo ảnh AI' }))
    insp = document.querySelector<HTMLElement>('.run-node-inspector')!
    expect(insp.querySelector('[data-truong="lan_thu"] dd')!.textContent).toContain('Lần 3')
    expect(insp.querySelector('[data-truong="lich_su_thu_lai"] dd')!.textContent)
      .toContain('3 lượt')
  })

  it('đầu vào là tham số khai trong đồ thị, ⛔ không phải một khối JSON của cả run', () => {
    veRun()
    fireEvent.click(screen.getByRole('button', { name: 'Tạo ảnh AI' }))
    const dauVao = document.querySelector<HTMLElement>('[data-truong="dau_vao"] dd')!
    expect(dauVao.textContent).toContain('prompt')
    // ⛔ Khong duoc keo ca `nodes`/`su_kien` cua run vao truong nay.
    expect(dauVao.textContent).not.toContain('su_kien')
    expect(dauVao.textContent).not.toContain('credit_max')
  })
})

describe('Lỗi hiện câu người đọc được, mã máy GẬP LẠI', () => {
  it('`credential_loi: …` thành một câu, mã nằm trong <details>', () => {
    veRun()
    fireEvent.click(screen.getByRole('button', { name: 'Đăng YouTube' }))
    const loi = document.querySelector<HTMLElement>('.run-loi')!
    const cau = loi.querySelector<HTMLElement>('.run-loi-cau')!
    expect(cau.textContent).toBe('Kết nối (tài khoản/khoá) mà bước này dùng không dùng được.')
    // ⛔ Ma may KHONG o cau dau.
    expect(cau.textContent).not.toContain('credential_loi')
    expect(cau.textContent).not.toContain('access_token')
    const gap = loi.querySelector<HTMLDetailsElement>('details')!
    expect(gap.open).toBe(false)
    expect(gap.textContent).toContain('credential_loi')
    expect(gap.textContent).toContain('thieu access_token')
  })

  it('mã lỗi CHƯA có câu dịch vẫn ra một câu người đọc được + mã ở chi tiết', () => {
    // `tachLoi` la lop thuan — do o day thay vi dung mot fixture rieng.
    const l = tachLoi('mot_ma_chua_ai_dich: chi tiet gi do')!
    expect(l.ma).toBe('mot_ma_chua_ai_dich')
    expect(l.chiTiet).toBe('chi tiet gi do')
    expect(l.cau).not.toContain('_')
    expect(l.cau).toContain('Chi tiết kỹ thuật')
  })

  it('chuỗi KHÔNG theo khuôn `<ma>: <chi tiet>` không bị cắt mất', () => {
    const l = tachLoi('khong co ma: nhung co dau hai cham')!
    // "khong co ma" co khoang trang ⇒ khong phai ma may ⇒ giu nguyen ca chuoi.
    expect(l.ma).toBe('')
    expect(l.chiTiet).toBe('khong co ma: nhung co dau hai cham')
    expect(tachLoi('')).toBeNull()
    expect(tachLoi('   ')).toBeNull()
  })
})

describe('Báo giá hiện TRƯỚC khi bấm Chạy — một CON SỐ, không một lời hứa', () => {
  it('đủ giá mọi bước: hiện tổng credit', () => {
    render(<BaoGiaTruocKhiChay nodeIds={['a', 'b', 'c']}
      liveQuotes={{ a: 3, b: 5, c: 4 }}/>)
    const khoi = screen.getByRole('region', { name: 'Báo giá trước khi chạy' })
    expect(within(khoi).getByText('12 credit')).toBeInTheDocument()
    expect(khoi.querySelector('[data-bao-gia-tong="12"]')).toBeTruthy()
  })

  it('🔴 thiếu giá một bước: ⛔ KHÔNG in một tổng sai, nói rõ là chưa đủ', () => {
    render(<BaoGiaTruocKhiChay nodeIds={['a', 'b', 'c']} liveQuotes={{ a: 3, b: 5 }}/>)
    const khoi = screen.getByRole('region', { name: 'Báo giá trước khi chạy' })
    expect(khoi.textContent).toContain('Chưa tính đủ giá')
    expect(khoi.textContent).toContain('2/3')
    // ⛔ `8 credit` la mot cai gia KHONG co that.
    expect(khoi.textContent).not.toContain('8 credit')
    expect(khoi.querySelector('[data-bao-gia-tong="8"]')).toBeNull()
  })

  it('giá 0 credit thật vẫn in `0 credit`, ⛔ không thành "chưa tính đủ"', () => {
    render(<BaoGiaTruocKhiChay nodeIds={['a']} liveQuotes={{ a: 0 }}/>)
    expect(screen.getByText('0 credit')).toBeInTheDocument()
  })
})

describe('Đối chứng — phép đo có bắt được lỗi cũ không?', () => {
  it('một run KHÔNG có `tenBuoc` vẫn ⛔ không in `node_id` ra cột đầu', () => {
    render(<RunV3Panel onCancel={() => {}} run={runGia({
      nodes: [nodeGia({ node_id: 'nmujtmc1b-0', status: 'RUNNING' })],
      su_kien: [suKienGia({ seq: 1, loai: 'WorkflowStarted' })] })}/>)
    const cotDau = document.querySelector('.run-timeline-ten')!
    expect(cotDau.textContent).toContain('Bước 1')
    expect(cotDau.textContent).not.toContain('nmujtmc1b-0')
  })

  it('run rỗng (0 bước) không nổ, và ⛔ không vẽ Inspector', () => {
    render(<RunV3Panel run={runGia({ nodes: [] })} onCancel={() => {}}/>)
    expect(document.querySelectorAll('.run-timeline tbody tr').length).toBe(0)
    expect(document.querySelector('.run-node-inspector')).toBeNull()
  })
})
