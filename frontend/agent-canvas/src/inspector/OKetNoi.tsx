// O KET NOI cua tab "Cấu hình" — va o TAO duoc mot ket noi TAI CHO.
//
// 🔴 VI SAO "+ Tạo kết nối" la DONG DAU CUA CHINH DROPDOWN, khong phai mot nut
//    o trang khac (chep luong Activepieces, MIT — `04_N8N_ACTIVEPIECES_
//    BENCHMARK.md` §9):
//
//    Do duoc 28/09: 34 node doi mot ket noi, 33 trong so do bi publish TU CHOI
//    vi thieu `credential_ref`, va khong mot cua nao cho khach tao mot ket noi.
//    Huy hieu "Cần kết nối" tren node noi dung su that va chi vao mot canh cua
//    khong ton tai.
//
//    Mot nut dan sang mot trang khac thi nguoi dung MAT ngu canh dang cau hinh
//    (bo do thi, buoc dang chon, cac o vua go). Form o day dung ngay duoi o
//    chon, va ⛔ khong mot lan dieu huong nao.
//
// ⛔ `credential_ref` ghi o MUC TREN CUNG cua buoc (`node.credential_ref`),
//    KHONG duoi `data`: `bien_dich._node_tu_dinh_nghia` doc `n["credential_ref"]`
//    o muc tren cung. Ghi sai cho thi publish van bao "chua gan ket noi" trong
//    khi giao dien hien mot ket noi da chon — mot bat dong im lang.
import { useCallback, useEffect, useMemo, useState } from 'react'
import type { KetNoi, NhaCungCap, OBiMat, SoNhaCungCap } from './ketNoiApi'
import { LoiKetNoi, taiKetNoi, taiSoNhaCungCap, taoKetNoi } from './ketNoiApi'

/** Gia tri `value` cua dong dau dropdown. Mot chuoi KHONG THE la mot id thuc
 *  (id la uuid), nen no khong bao gio dung do voi mot ket noi that. */
const MO_FORM = '\u0000tao-ket-noi'

const TANG_SELF = 'self'
const TANG_CLOUD = 'cloud'

type Props = {
  /** `NodeDefinition.credential` — cac `kieu` buoc nay nhan. Rong ⇒ ⛔ o nay
   *  KHONG duoc hien (buoc khong goi ra ngoai). */
  kieuChoPhep: string[]
  /** `type` cua buoc, de tra ra nha cung cap. Tra o MAY CHU, khong o day. */
  buocType: string
  /** `credential_ref` dang gan, hoac chuoi rong. */
  giaTri: string
  csrf: string
  readOnly?: boolean
  onChange: (ref: string) => void
}

function nhanKetNoi(k: KetNoi): string {
  const ten = k.ten || k.nha_cung_cap || k.kieu
  const duoi = k.preview ? ` (…${k.preview})` : ''
  return k.thu_hoi_luc ? `${ten} — đã thu hồi` : `${ten}${duoi}`
}

/** Nha cung cap cua buoc nay, theo bang `node_type` MAY CHU tra ve.
 *  ⛔ Khong suy tu `buocType` bang cach cat chuoi o frontend: hai cho suy cung
 *     mot dieu thi co ngay chung lech nhau (bai hoc "hai chỗ khai một điều"). */
function timNhaCungCap(so: SoNhaCungCap | null,
                       buocType: string): NhaCungCap | null {
  if (!so) return null
  return so.nha_cung_cap.find(n => n.node_type.includes(buocType)) ?? null
}

export function OKetNoi({ kieuChoPhep, buocType, giaTri, csrf, readOnly,
                          onChange }: Props) {
  const [ds, setDs] = useState<KetNoi[]>([])
  const [so, setSo] = useState<SoNhaCungCap | null>(null)
  const [moForm, setMoForm] = useState(false)
  const [loi, setLoi] = useState('')
  const [dangTai, setDangTai] = useState(true)

  const kieuKhoa = kieuChoPhep.join(',')
  const nap = useCallback(async () => {
    setDangTai(true)
    try {
      const [a, b] = await Promise.all([
        taiKetNoi(kieuKhoa ? kieuKhoa.split(',') : []),
        taiSoNhaCungCap(),
      ])
      setDs(a); setSo(b); setLoi('')
    } catch (e) {
      // ⛔ KHONG nuot: mot danh sach rong vi loi mang trong y het mot khach
      //    chua co ket noi nao — va nguoi dung se di tao cai thu hai.
      setLoi(e instanceof Error ? e.message : String(e))
    } finally {
      setDangTai(false)
    }
  }, [kieuKhoa])

  useEffect(() => { void nap() }, [nap])

  const ncc = useMemo(() => timNhaCungCap(so, buocType), [so, buocType])

  return <section className="o-ket-noi" aria-label="Kết nối của bước">
    <label htmlFor="o-ket-noi-chon">Kết nối *</label>
    <select id="o-ket-noi-chon" disabled={readOnly || dangTai}
      value={giaTri || ''}
      onChange={e => {
        if (e.target.value === MO_FORM) { setMoForm(true); return }
        onChange(e.target.value)
      }}>
      {/* 🔴 DONG DAU, ngay trong dropdown (Activepieces). ⛔ Khong phai mot nut
          o trang khac — nguoi dung khong roi ngu canh dang cau hinh. */}
      <option value={MO_FORM}>+ Tạo kết nối</option>
      <option value="">— chưa chọn —</option>
      {ds.map(k => <option key={k.id} value={k.id}
        disabled={Boolean(k.thu_hoi_luc)}>{nhanKetNoi(k)}</option>)}
    </select>
    {!dangTai && ds.length === 0 && !moForm &&
      <small className="o-ket-noi-trong">Chưa có kết nối nào — tạo một cái
        ngay tại đây.</small>}
    {loi && <small className="o-loi" role="status">{loi}</small>}
    {moForm && so && <FormTaoKetNoi so={so} ncc={ncc} kieuChoPhep={kieuChoPhep}
      csrf={csrf}
      onHuy={() => setMoForm(false)}
      onXong={async ref => { setMoForm(false); await nap(); onChange(ref) }} />}
  </section>
}

function OMotBiMat({ o, gia, onChange }: {
  o: OBiMat; gia: string; onChange: (v: string) => void }) {
  const id = `o-bi-mat-${o.ten}`
  return <div className="o-truong">
    <label htmlFor={id}>{o.nhan}</label>
    {o.nhieu_dong
      ? <textarea id={id} rows={4} value={gia} autoComplete="off"
          spellCheck={false} onChange={e => onChange(e.target.value)} />
      : <input id={id} value={gia} autoComplete="off" spellCheck={false}
          type={o.che ? 'password' : 'text'}
          onChange={e => onChange(e.target.value)} />}
  </div>
}

function FormTaoKetNoi({ so, ncc, kieuChoPhep, csrf, onHuy, onXong }: {
  so: SoNhaCungCap
  ncc: NhaCungCap | null
  kieuChoPhep: string[]
  csrf: string
  onHuy: () => void
  onXong: (ref: string) => Promise<void> | void
}) {
  // ⭐ Chi moi nhung `kieu` mà BUOC NAY nhan VA may chu biet hinh dang bi mat
  //    cua chung. Mot `kieu` khong co o `khoa_bi_mat` la mot `kieu` khong ai
  //    dung form nay tao duoc — hien no ra la moi nguoi dung vao mot ngo cut.
  const kieuDung = kieuChoPhep.filter(k => (so.khoa_bi_mat[k] ?? []).length > 0)
  const [kieu, setKieu] = useState(kieuDung[0] ?? '')
  const [tang, setTang] = useState(TANG_SELF)
  const [ten, setTen] = useState('')
  const [biMat, setBiMat] = useState<Record<string, string>>({})
  const [loi, setLoi] = useState('')
  const [bien, setBien] = useState<string[]>([])
  const [dangGui, setDangGui] = useState(false)

  const oCanDien = so.khoa_bi_mat[kieu] ?? []
  const cloudSanSang = Boolean(ncc?.co_tang_cloud && ncc.san_sang)
  const cloudChuaCauHinh = Boolean(ncc?.co_tang_cloud && !ncc.san_sang)

  if (!kieuDung.length) {
    return <p className="o-ket-noi-form o-loi" role="status">
      Bước này cần một loại kết nối mà giao diện chưa tạo được. Hãy báo quản
      trị.</p>
  }

  const gui = async () => {
    setDangGui(true); setLoi(''); setBien([])
    try {
      const k = await taoKetNoi({
        kieu, ten, tang, nha_cung_cap: ncc?.ma ?? '',
        // ⛔ Chi gui DUNG cac khoa may chu doi: mot khoa la bi tu choi 422, va
        //    do la dung — mot khoa go sai ten la mot bi mat khach TUONG da dat.
        bi_mat: Object.fromEntries(oCanDien.map(o => [o.ten, biMat[o.ten] ?? ''])),
      }, csrf)
      await onXong(k.id)
    } catch (e) {
      setLoi(e instanceof Error ? e.message : String(e))
      if (e instanceof LoiKetNoi) setBien(e.bienMoiTruong)
    } finally {
      setDangGui(false)
    }
  }

  return <form className="o-ket-noi-form" aria-label="Tạo kết nối mới"
    onSubmit={e => { e.preventDefault(); void gui() }}>
    <div className="o-truong">
      <label htmlFor="o-ket-noi-ten">Tên kết nối</label>
      <input id="o-ket-noi-ten" value={ten} maxLength={120}
        onChange={e => setTen(e.target.value)} />
    </div>
    {kieuDung.length > 1 && <div className="o-truong">
      <label htmlFor="o-ket-noi-kieu">Cách xác thực</label>
      <select id="o-ket-noi-kieu" value={kieu}
        onChange={e => { setKieu(e.target.value); setBiMat({}) }}>
        {kieuDung.map(k => <option key={k} value={k}>{k}</option>)}
      </select>
    </div>}
    {/* ⭐ HAI TANG (Q4 = C). Tang `cloud` chi hien khi nha cung cap nay THAT SU
        co the co mot OAuth app cua LTT; va neu LTT chua cau hinh thi noi THANG
        ra, ⛔ khong mo mot luong gia vo hoat dong. */}
    {ncc?.co_tang_cloud && <fieldset className="o-ket-noi-tang">
      <legend>Ứng dụng dùng để xác thực</legend>
      <label><input type="radio" name="tang" value={TANG_SELF}
        checked={tang === TANG_SELF} onChange={() => setTang(TANG_SELF)} />
        Ứng dụng của tôi</label>
      <label><input type="radio" name="tang" value={TANG_CLOUD}
        checked={tang === TANG_CLOUD} disabled={!cloudSanSang}
        onChange={() => setTang(TANG_CLOUD)} />
        Ứng dụng do LTT quản lý</label>
      {cloudChuaCauHinh && <small className="o-mo-ta" role="status">
        LTT chưa cấu hình cho nhà cung cấp này. Hãy tự mang ứng dụng của
        bạn.</small>}
    </fieldset>}
    {oCanDien.map(o => <OMotBiMat key={o.ten} o={o} gia={biMat[o.ten] ?? ''}
      onChange={v => setBiMat(c => ({ ...c, [o.ten]: v }))} />)}
    {loi && <small className="o-loi" role="status">{loi}</small>}
    {bien.length > 0 && <small className="o-mo-ta">
      Quản trị cần đặt: {bien.join(', ')}</small>}
    <div className="o-ket-noi-nut">
      <button type="submit" disabled={dangGui}>Lưu kết nối</button>
      <button type="button" onClick={onHuy}>Hủy</button>
    </div>
  </form>
}
