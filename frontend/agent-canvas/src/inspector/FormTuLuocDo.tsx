// Form sinh TU LUOC DO (spec §13.3). ⛔ Khong mot bang `fieldLabels` nao o
// day: nhan la ten tham so cua app, va mo ta den tu `description` cua luoc do.
// Mot bang nhan thu hai la thu `test_967` dang dem hang chet.
//
// Nguon hinh dang: `platform_core/workflow/luoc_do.py` (`sang_json_schema`).
import { useState } from 'react'
import type { ReactNode } from 'react'
import type { LuocDo, TruongLuocDo } from '../nodeDefinition'

type Props = {
  luocDo: LuocDo
  giaTri: Record<string, unknown>
  readOnly?: boolean
  onChange: (ten: string, gia_tri: unknown) => void
}

const laBieuThuc = (v: unknown) => typeof v === 'string' && v.includes('{{')

function ChuThich({ luat }: { luat: TruongLuocDo }) {
  const dong = luat['x-ltt-dong']
  return <>
    {luat['x-ltt-loi'] && <small className="o-loi-tuy-chon" role="status">
      Chưa tải được lựa chọn</small>}
    {dong && <small className="o-dong">Tuỳ theo: {dong.prop}</small>}
    {luat.description && <small className="o-mo-ta">{luat.description}</small>}
  </>
}

function OJson({ ten, gia, readOnly, onChange }: {
  ten: string; gia: unknown; readOnly?: boolean
  onChange: (v: unknown) => void }) {
  const [tho, setTho] = useState(() =>
    gia === undefined ? '' : typeof gia === 'string' ? gia : JSON.stringify(gia))
  const [loi, setLoi] = useState(false)
  return <>
    <textarea id={ten} disabled={readOnly} value={tho} rows={4}
      onChange={e => {
        const v = e.target.value
        setTho(v)
        if (laBieuThuc(v)) { setLoi(false); onChange(v); return }
        // ⛔ JSON hong thi KHONG goi `onChange`: nuot loi o day nghia la nguoi
        //    dung go xong, thay o van sang, va tham so cu im lang o lai.
        try { onChange(JSON.parse(v)); setLoi(false) } catch { setLoi(true) }
      }} />
    {loi && <small className="o-loi">JSON không hợp lệ</small>}
  </>
}

function MotO({ ten, luat, bat_buoc, gia, readOnly, onChange }: {
  ten: string; luat: TruongLuocDo; bat_buoc: boolean; gia: unknown
  readOnly?: boolean; onChange: (v: unknown) => void }) {
  // ⭐ MAT XICH CUOI cua "palette la catalogue": `palette_v3._tham_so_co_dau`
  //    danh dau truong chua tai duoc lua chon dong, va luoc do con lai la ban
  //    TINH. Tinh ra, `voice_id` la mot `string` TU DO — mot o chu binh thuong
  //    trong y het mot tham so khoe manh. Khong khoa o day thi ca duong day
  //    kia chi de trang tri: nguoi dung go bua, publish qua, hong LUC CHAY.
  const khongTaiDuoc = Boolean(luat['x-ltt-loi'])
  const khoa = readOnly || luat.readOnly === true || khongTaiDuoc
  const nhan = `${ten}${bat_buoc ? ' *' : ''}`
  // ⭐ Cong tac "dung bieu thuc" cho o SO. Khong co no, nhanh `laBieuThuc`
  //    chi voi toi khi gia tri DA LUU la bieu thuc — va `<input type="number">`
  //    khong nhan duoc `{`, nen khong co duong nao BIEN mot o so thanh bieu
  //    thuc tu giao dien. Bat san khi gia tri hien tai da la bieu thuc.
  const [moBieuThuc, setMoBieuThuc] = useState(false)
  const boc = (con: ReactNode) => <div className="o-truong">
    <label htmlFor={ten}>{nhan}</label>{con}<ChuThich luat={luat} /></div>

  // ⭐ `Array.isArray` chu KHONG phai `luat.enum?.length`: mot `enum` RONG
  //    nghia la *"ban chua co lua chon nao"* (vd giong nhan ban cua chinh
  //    khach), KHAC HAN mot chuoi tu do. Roi xuong o chu tu do o day la dung
  //    cai GENERIC_GAP D10 sinh ra de dong — va khach go duoc `voice_id` cua
  //    nguoi khac (spec §4.6, `luoc_do.py`: `"values" in rule`).
  if (Array.isArray(luat.enum)) {
    if (luat.enum.length === 0) {
      return boc(<>
        <select id={ten} disabled value="">
          <option value="">— chưa có lựa chọn nào —</option>
        </select>
        <small className="o-trong">Chưa có lựa chọn nào</small>
      </>)
    }
    const soHoc = luat.type === 'integer' || luat.type === 'number'
    return boc(
      <select id={ten} disabled={khoa} value={String(gia ?? luat.default ?? '')}
        onChange={e => onChange(soHoc ? Number(e.target.value) : e.target.value)}>
        <option value="">— chọn —</option>
        {luat.enum.map(v => <option key={String(v)} value={String(v)}>
          {luat['x-ltt-nhan']?.[String(v)] ?? String(v)}</option>)}
      </select>)
  }

  if (luat.type === 'boolean') {
    return boc(<input id={ten} type="checkbox" disabled={khoa}
      checked={Boolean(gia ?? luat.default ?? false)}
      onChange={e => onChange(e.target.checked)} />)
  }

  if (luat.type === 'object' || luat.type === 'array') {
    return boc(<OJson ten={ten} gia={gia ?? luat.default} readOnly={khoa}
      onChange={onChange} />)
  }

  if (luat['x-ltt-control'] === 'textarea') {
    return boc(<textarea id={ten} disabled={khoa} rows={3}
      value={String(gia ?? luat.default ?? '')}
      onChange={e => onChange(e.target.value)} />)
  }

  const so = luat.type === 'integer' || luat.type === 'number'
  const bieuThuc = so && (moBieuThuc || laBieuThuc(gia))
  return boc(<>
    <input id={ten} disabled={khoa}
      type={so && !bieuThuc ? 'number' : 'text'}
      min={luat.minimum} max={luat.maximum} maxLength={luat.maxLength}
      value={String(gia ?? luat.default ?? '')}
      onChange={e => {
        const v = e.target.value
        // ⭐ Mot o SO van phai nhan duoc `{{ ... }}` (spec §4.6: moi gia tri
        //    co the la literal HOAC bieu thuc). Ep `Number()` o day bien mot
        //    tham chieu hop le thanh `NaN` — im lang.
        if (!so || bieuThuc || laBieuThuc(v)) { onChange(v); return }
        onChange(luat.type === 'integer' ? Number.parseInt(v, 10) : Number(v))
      }} />
    {so && <button type="button" className="o-cong-tac-bieu-thuc"
      aria-label={`Dùng biểu thức cho ${ten}`} disabled={khoa}
      aria-pressed={bieuThuc}
      onClick={() => setMoBieuThuc(m => !m)}>{'{{ }}'}</button>}
  </>)
}

export function FormTuLuocDo({ luocDo, giaTri, readOnly, onChange }: Props) {
  const muc = Object.entries(luocDo.properties ?? {})
  if (!muc.length) return <p className="form-trong">Node này không có tham số.</p>
  return <div className="form-luoc-do">
    {muc.map(([ten, luat]) => <MotO key={ten} ten={ten} luat={luat}
      bat_buoc={(luocDo.required ?? []).includes(ten)} gia={giaTri[ten]}
      readOnly={readOnly} onChange={v => onChange(ten, v)} />)}
  </div>
}
