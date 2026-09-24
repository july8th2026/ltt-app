// O BIEU THUC co autocomplete — P2 Task 8.
//
// ⛔ KHONG mot ten ham / ten cong / ten namespace nao trong tep nay. Ca danh
//    sach den tu `GoiYBieuThuc` cua may chu, noi no duoc SINH tu `NHOM_HAM` va
//    tu do thi × registry. Go tay mot bang o day la dung cai benh ma
//    `test_967` dang dem hang chet — va te hon: mot ten node KHONG phai to
//    tien go o day se publish khong duoc, tuc la ta moi nguoi dung viet mot
//    bieu thuc bi tu choi.
//
// ⭐ Chi mo khi con tro dang o TRONG mot `{{` chua dong. Ngoai do, o nay la
//    mot o chu binh thuong: cong tac `{{ }}` cua o SO (phase 2) khong bi dong
//    them mot hop nao che mat.
import { useRef, useState } from 'react'
import type { GoiYBieuThuc } from '../workflowApi'

export type Props = {
  id: string
  gia: string
  goiY?: GoiYBieuThuc
  disabled?: boolean
  soHoc?: boolean
  maxLength?: number
  onChange: (v: string) => void
}

type Ung = { chen: string; nhan: string; phu: string; qua_publish: boolean }

/** Doan dang go sau `{{` gan nhat CHUA dong, hoac `null`. */
export function dangGoBieuThuc(chuoi: string, caret: number):
    { batDau: number; tu: string } | null {
  const truoc = chuoi.slice(0, caret)
  const mo = truoc.lastIndexOf('{{')
  if (mo < 0) return null
  if (truoc.slice(mo).includes('}}')) return null
  // `\{{` la chu thuong (spec §6.1) — khong phai mot bieu thuc dang mo.
  if (mo > 0 && chuoi[mo - 1] === '\\') return null
  return { batDau: mo + 2, tu: truoc.slice(mo + 2).trimStart() }
}

// ⛔ `?? []` khong phai phong thu thua: than 200 cua cua nay co the la mot
//    hinh dang KHAC (loi da bi mot lop giua viet lai, mot ban may chu cu).
//    `undefined.map` o day lam DEN ca trinh soan — mot hop goi y khong duoc
//    phep giet canvas.
function ungVien(goiY: GoiYBieuThuc | undefined): Ung[] {
  if (!goiY) return []
  return [
    ...(goiY.muc ?? []).map(m => ({ chen: m.duong, nhan: m.duong,
      phu: m.node_type ?? '', qua_publish: m.qua_publish })),
    ...(goiY.ham ?? []).map(h => ({ chen: `${h.ten}(`, nhan: h.ten,
      phu: h.chu_ky, qua_publish: h.qua_publish })),
  ]
}

export function OBieuThuc({ id, gia, goiY, disabled, soHoc, maxLength,
                           onChange }: Props) {
  const o = useRef<HTMLInputElement>(null)
  const [mo, setMo] = useState(false)
  const [tu, setTu] = useState('')
  const [chon, setChon] = useState(0)

  const loc = tu.trim().toLocaleLowerCase()
  const ung = ungVien(goiY).filter(u => !loc ||
    u.nhan.toLocaleLowerCase().includes(loc)).slice(0, 12)
  const hien = mo && ung.length > 0

  function doi(v: string, caret: number) {
    onChange(v)
    const dang = dangGoBieuThuc(v, caret)
    setMo(dang !== null)
    setTu(dang ? dang.tu : '')
    setChon(0)
  }

  function chenVao(u: Ung) {
    const caret = o.current?.selectionStart ?? gia.length
    const dang = dangGoBieuThuc(gia, caret)
    if (!dang) return
    const moi = `${gia.slice(0, dang.batDau)} ${u.chen}${gia.slice(caret)}`
    onChange(moi)
    setMo(false)
    o.current?.focus()
  }

  return <div className="o-bieu-thuc">
    <input ref={o} id={id} type="text" disabled={disabled} value={gia}
      role="combobox" aria-expanded={hien} aria-autocomplete="list"
      aria-controls={`${id}-goi-y`}
      data-so={soHoc ? '1' : undefined} maxLength={maxLength}
      onChange={e => doi(e.target.value, e.target.selectionStart ?? e.target.value.length)}
      onKeyDown={e => {
        if (!hien) return
        if (e.key === 'ArrowDown') { e.preventDefault(); setChon(i => (i + 1) % ung.length) }
        else if (e.key === 'ArrowUp') { e.preventDefault(); setChon(i => (i - 1 + ung.length) % ung.length) }
        else if (e.key === 'Enter') { e.preventDefault(); chenVao(ung[chon]) }
        else if (e.key === 'Escape') { e.preventDefault(); setMo(false) }
      }}
      onBlur={() => window.setTimeout(() => setMo(false), 120)} />
    {hien && <ul className="goi-y-bieu-thuc" id={`${id}-goi-y`} role="listbox"
      aria-label="Gợi ý biểu thức">
      {ung.map((u, i) => <li key={u.nhan} role="option" aria-selected={i === chon}
        className={u.qua_publish ? '' : 'chua-publish-duoc'}
        // ⚠️ `onMouseDown` chu khong `onClick`: `onBlur` cua o chu chay truoc
        //    `onClick` va se dong hop mat truoc khi cu bam toi noi.
        onMouseDown={e => { e.preventDefault(); chenVao(u) }}>
        <strong>{u.nhan}</strong>{u.phu && <small>{u.phu}</small>}
        {!u.qua_publish && <small className="canh-bao"
          title="Cổng publish hôm nay chưa nhận dạng biểu thức này">chưa publish được</small>}
      </li>)}
    </ul>}
    {goiY?.loi && <small className="o-loi" role="status">
      Chưa liệt kê được node đọc được: {goiY.loi.ma}</small>}
  </div>
}
