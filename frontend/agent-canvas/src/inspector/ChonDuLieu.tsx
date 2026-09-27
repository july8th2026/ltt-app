// Bo chon du lieu (Data picker, `09_TARGET_DESIGN.md` §7) — lan UI-6.
//
// Tab "Dữ liệu vào" cua Inspector V2. Viec cua no la lam THAT mot o dat cho:
// cho nguoi dung thay CAY du lieu dung duoc tu cac buoc DUNG TRUOC trong do
// thi, va bam mot muc de CHEN dung bieu thuc vao mot o tham so — thay vi phai
// go tay `{{ nodes... }}`.
//
// ⛔ KHONG tu tinh quan he to tien o day. `goiY.muc` (may chu,
//    `goi_y._cua_node`) DA loc dung "to tien" cua node dang chon
//    (`bien_dich.cau_truc().to_tien`) — cong publish doc CUNG mot ham. Tu di
//    lai canh bang `edges` o day se co ngay MOT bang thu hai, va no LECH ngay
//    lan dau gap `core.if`/`core.switch` (chinh loi ma `goi_y.py` da canh
//    bao). File nay chi XEP LAI nhung gi may chu da tra, khong doan them.
//
// ⚠️ Kieu cua tung CONG khong hien duoc o day: `goi_y()` chi tra TEN cong
//    (`m.cong`) va KIEU NODE cua chu no (`m.node_type`, vd "image.generate"),
//    khong tra kieu DU LIEU cua rieng cong do. Mo mot cua HTTP moi de lay lai
//    dinh nghia day du cua MOI node to tien la thu brief cam ("⛔ KHONG mo cua
//    HTTP moi"). Nen the "kieu hien canh ten" cua §7, o day chi hien duoc TEN
//    LOAI BUOC cua chu cong — xem bao cao lan UI-6 cho quyet dinh nay.
import { useMemo, useState } from 'react'
import type { CanvasEdge, CanvasNode } from '../workflowApi'
import type { GoiYBieuThuc, MucGoiY } from '../workflowApi'
import type { LuocDo } from '../nodeDefinition'
import { nhanBieuThuc, truongHienThi } from './FormTuLuocDo'

type LaMuc = { duong: string; nhan: string; phu?: string; quaPublish: boolean }
type NhomBuoc = { nodeId: string; nhan: string; con: LaMuc[] }

/** Nhan tieng Viet cho tung goc namespace (`chinh_sach.NAMESPACE`, spec §6.2).
 *  ⛔ Day KHONG phai mot ban sao ten — no chi DICH bay ten CO SAN sang chu
 *    nguoi doc; `goi_y()` van la nguon duy nhat quyet dinh goc nao TON TAI. */
const NHAN_GOC: Record<string, string> = {
  trigger: 'Trigger',
  workflow: 'Đầu vào workflow',
  loop: 'Vòng lặp',
  vars: 'Biến (state)',
  params: 'Tham số',
  run: 'Lượt chạy',
}

const NHAN_MAT: Record<string, string> = { status: 'Trạng thái', error: 'Lỗi' }

function nhomGoc(duong: string): string { return duong.split('.')[0] }

/** Nhan cua MOT la trong nhom goc. `goi_y()` hom nay chi tra dung ten goc
 *  (khong co khoa con — xem ghi chu o `goi_y.py`), nen la duy nhat cua mot
 *  nhom la "chèn cả nhánh"; mai sau may chu tra them `trigger.event` thi dong
 *  nay tu xep no thanh mot la RIENG duoi cung nhom, khong can sua o day. */
function nhanLaGoc(duong: string): string {
  const phan = duong.split('.')
  return phan.length > 1 ? phan.slice(1).join('.') : '(cả mục)'
}

function xayCay(goiY: GoiYBieuThuc | undefined, nhanNode: Map<string, string>) {
  const goc = new Map<string, LaMuc[]>()
  const theoNode = new Map<string, LaMuc[]>()
  const thuTuNode: string[] = []
  for (const m of (goiY?.muc ?? []) as MucGoiY[]) {
    if (m.loai === 'goc') {
      const nhom = nhomGoc(m.duong)
      const list = goc.get(nhom) ?? []
      list.push({ duong: m.duong, nhan: nhanLaGoc(m.duong), quaPublish: m.qua_publish })
      goc.set(nhom, list)
      continue
    }
    const nid = m.node ?? ''
    if (!theoNode.has(nid)) { theoNode.set(nid, []); thuTuNode.push(nid) }
    const nhan = m.loai === 'cong'
      ? (m.cong || m.duong.split('.').pop() || m.duong)
      : (NHAN_MAT[m.duong.split('.').pop() ?? ''] ?? (m.duong.split('.').pop() ?? m.duong))
    theoNode.get(nid)!.push({ duong: m.duong, nhan, phu: m.node_type, quaPublish: m.qua_publish })
  }
  const buocTruoc: NhomBuoc[] = thuTuNode.map(nid =>
    ({ nodeId: nid, nhan: nhanNode.get(nid) ?? nid, con: theoNode.get(nid) ?? [] }))
  return { goc, buocTruoc }
}

function khopLoc(la: LaMuc, loc: string): boolean {
  if (!loc) return true
  return la.nhan.toLocaleLowerCase().includes(loc) || la.duong.toLocaleLowerCase().includes(loc)
}

type Props = {
  buocId: string
  nodes: CanvasNode[]
  edges: CanvasEdge[]
  goiY?: GoiYBieuThuc
  luocDo: LuocDo
  giaTri: Record<string, unknown>
  readOnly?: boolean
  onChen: (ten: string, gia_tri: unknown) => void
}

export function ChonDuLieu({ buocId, nodes, edges, goiY: goiYTho, luocDo, giaTri,
                            readOnly, onChen }: Props) {
  const [timKiem, setTimKiem] = useState('')

  // 🔴 `useExpressionSuggest` (hook dung chung, ⛔ khong phai tep UI-6 duoc
  //    sua) KHONG xoa `goiY` ve `undefined` khi doi node chon — no chi GHI DE
  //    khi ban MOI ve. Chon buoc B (co to tien) roi bam sang buoc A (khong co
  //    to tien) trong luc ban goi-y cua A con dang bay: mot nhip ngan cay VAN
  //    con hien ket qua CUA B — dung do duoc tren trinh duyet that (28/09,
  //    xem bao cao lan UI-6). `GoiYBieuThuc.node_id` DA co san de tu kiem;
  //    coi goi y KHONG khop buoc dang chon la CHUA VE, giong het luc dang tai. */
  const goiY = goiYTho?.node_id === buocId ? goiYTho : undefined

  const dichTruong = useMemo(() =>
    truongHienThi(luocDo, giaTri).filter(([, luat]) => nhanBieuThuc(luat)),
    [luocDo, giaTri])
  const [oDich, setODich] = useState<string>(() => dichTruong[0]?.[0] ?? '')
  // ⭐ Node doi thi doi luon o dich mac dinh — chon buoc B roi lai chon buoc A
  //   ma o dich van tro ve ten tham so cua B se chen nham cho.
  const oDichThatSu = dichTruong.some(([ten]) => ten === oDich) ? oDich : (dichTruong[0]?.[0] ?? '')

  const nhanNode = useMemo(() => {
    const m = new Map<string, string>()
    for (const n of nodes) m.set(n.id, n.label?.trim() || n.id)
    return m
  }, [nodes])

  const { goc, buocTruoc } = useMemo(() => xayCay(goiY, nhanNode), [goiY, nhanNode])

  const coDayVao = edges.some(e => e.target === buocId)
  const coDuLieuBuocTruoc = buocTruoc.length > 0

  function chenVao(duong: string) {
    if (readOnly || !oDichThatSu) return
    const bieuThuc = `{{ ${duong} }}`
    const hienTai = giaTri[oDichThatSu]
    const gia_tri = typeof hienTai === 'string' && hienTai.length > 0
      ? `${hienTai}${/\s$/.test(hienTai) ? '' : ' '}${bieuThuc}`
      : bieuThuc
    onChen(oDichThatSu, gia_tri)
  }

  const loc = timKiem.trim().toLocaleLowerCase()

  // Nhom TU KHOP (ten nhom trung tu tim) thi hien HET con — nguoi go "trigger"
  // muon thay ca nhom, khong chi cac la co chu "trigger" trong ten.
  function locNhom(nhanNhom: string, con: LaMuc[]): LaMuc[] | null {
    if (!loc) return con
    if (nhanNhom.toLocaleLowerCase().includes(loc)) return con
    const conLoc = con.filter(la => khopLoc(la, loc))
    return conLoc.length > 0 ? conLoc : null
  }

  function nhomGocRa(ten: string, con: LaMuc[]) {
    const nhan = NHAN_GOC[ten] ?? ten
    const conLoc = locNhom(nhan, con)
    if (!conLoc) return null
    return <li key={ten} className="chon-du-lieu-nhom">
      <strong>{nhan}</strong>
      <ul>{conLoc.map(la => <LaChon key={la.duong} la={la}
        disabled={readOnly || !oDichThatSu} onChon={chenVao} />)}</ul>
    </li>
  }

  const nhomBuocTruoc = buocTruoc.map(nb => {
    const conLoc = locNhom(nb.nhan, nb.con)
    if (!conLoc) return null
    return <li key={nb.nodeId} className="chon-du-lieu-buoc">
      <strong>{nb.nhan}</strong>
      <ul>{conLoc.map(la => <LaChon key={la.duong} la={la}
        disabled={readOnly || !oDichThatSu} onChon={chenVao} />)}</ul>
    </li>
  }).filter(Boolean)
  // "Bước trước" tu no cung la mot nhom tim duoc bang ten ("bước trước").
  const khopNhomBuocTruoc = !loc || 'bước trước'.includes(loc) || nhomBuocTruoc.length > 0

  return <div className="chon-du-lieu">
    <div className="chon-du-lieu-thanh">
      <input type="search" placeholder="Tìm…" aria-label="Tìm dữ liệu"
        value={timKiem} onChange={e => setTimKiem(e.target.value)} />
    </div>
    {dichTruong.length > 0
      ? <label className="chon-du-lieu-dich">
          Chèn vào ô
          <select aria-label="Chèn vào ô" value={oDichThatSu} disabled={readOnly}
            onChange={e => setODich(e.target.value)}>
            {dichTruong.map(([ten]) => <option key={ten} value={ten}>{ten}</option>)}
          </select>
        </label>
      : <p className="o-trong" role="status">
          Bước này không có ô nào nhận được biểu thức.</p>}

    {/* ⭐ `goiY === undefined` la ĐANG TẢI (debounce 200ms + mot chuyen may chu
     *   cua `useExpressionSuggest`), ⛔ KHONG PHAI "khong co gi de chon". Gop
     *   hai trang thai nay lam MOT se noi "chua co du lieu" trong luc dang
     *   cho, dung hinh dang "hai trang thai gop thanh mot gia tri" da ghi
     *   trong so tay du an — va do duoc tren trinh duyet that (28/09): mot
     *   phep do dem qua SOM se thay 0 trong khi du lieu chi cham mot nhip. */}
    {goiY === undefined
      ? <p className="o-trong" role="status">Đang tải dữ liệu dùng được…</p>
      : <>
          {goiY.loi && <p className="o-loi" role="status">
            Chưa liệt kê được dữ liệu bước trước: {goiY.loi.thong_diep}</p>}

          <ul className="chon-du-lieu-cay" aria-label="Dữ liệu dùng được">
            {[...goc.entries()].map(([ten, con]) => nhomGocRa(ten, con))}
            {coDuLieuBuocTruoc && khopNhomBuocTruoc
              ? <li className="chon-du-lieu-nhom" key="__buoc_truoc">
                  <strong>Bước trước</strong>
                  <ul>{nhomBuocTruoc}</ul>
                </li>
              : !coDuLieuBuocTruoc && !goiY.loi && <li className="chon-du-lieu-trong" key="__trong">
                  <p role="status">
                    {coDayVao
                      ? 'Bước đứng trước chưa có dữ liệu để lấy.'
                      : 'Bước này chưa có bước nào đứng trước — nối một dây vào'
                        + ' cổng vào của bước này để lấy dữ liệu.'}
                  </p>
                </li>}
          </ul>
        </>}
  </div>
}

function LaChon({ la, disabled, onChon }: {
  la: LaMuc; disabled: boolean; onChon: (duong: string) => void }) {
  return <li>
    <button type="button" className={la.quaPublish ? '' : 'chua-publish-duoc'}
      disabled={disabled} title={la.duong}
      onClick={() => onChon(la.duong)}>
      <span className="chon-du-lieu-ten">{la.nhan}</span>
      {la.phu && <span className="chon-du-lieu-phu">{la.phu}</span>}
      {!la.quaPublish && <span className="canh-bao"
        title="Cổng publish hôm nay chưa nhận dạng biểu thức này">
        chưa publish được</span>}
    </button>
  </li>
}
