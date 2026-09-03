/**
 * SoanThao.tsx — o soan tin. Cho tieng Viet, phan kho nhat khong phai bo cuc.
 *
 * 🔴 IME. Go Telex/VNI sinh ra mot chuoi phim TRONG khi tu chua xong ("ddaay"
 *    -> "đây"), va trong khoang do trinh duyet van ban Enter. Gui luc ay la cat
 *    tu lam doi — nguoi dung khong lam gi sai ma cau bi hong.
 *
 *    Ky thuat muon tu LibreChat v0.8.7 @ 9e74cc0 (MIT),
 *    `client/src/hooks/Input/useTextarea.ts:186-187`, va **ca ba** dieu kien
 *    deu can:
 *
 *      isComposing   — co cua ta, dat boi compositionstart/end
 *      e.key === 'Process'  — Firefox/Edge bao IME bang ten phim nay
 *      e.keyCode === 229     — Safari KHONG dat `isComposing` dung luc; day la
 *                              duong duy nhat con lai, va no la ly do `keyCode`
 *                              (da bi khai tu) van phai co mat o day.
 *
 * ⭐ Shift+Enter xuong dong. Enter gui — tru khi dang go IME.
 */
import { useCallback, useEffect, useRef, useState } from 'react'

export type AnhDinh = { key: string; ten: string }

/**
 * Mã lỗi của máy chủ → một câu người đọc được.
 *
 * ⛔ Đo trên production: người dùng chọn một tệp hỏng và nhận đúng chuỗi
 *    `http_400`. Đó là mã trạng thái HTTP đặt trước mặt một người đang cố gửi
 *    một bức ảnh — nó không nói họ làm sai gì, cũng không nói phải làm gì tiếp.
 */
function doiLoiAnh(e: unknown): string {
  const ma = (e as { code?: string } | null)?.code ?? ''
  const theoMa: Record<string, string> = {
    tham_so: 'tệp không phải ảnh hợp lệ',
    http_400: 'tệp không phải ảnh hợp lệ',
    http_413: 'ảnh quá lớn',
    csrf: 'phiên đã cũ, tải lại trang',
  }
  if (theoMa[ma]) return theoMa[ma]
  const tin = e instanceof Error ? e.message : ''
  return tin && !/^http_\d+$/.test(tin) ? tin : 'không tải lên được'
}

export type SoanThaoProps = {
  /** Cho phim tat "ve o soan" (Shift+Esc) va cho luc mo hoi thoai moi. */
  oRef?: React.RefObject<HTMLTextAreaElement | null>
  onGui: (chu: string, anh: string[]) => void
  dangChay: boolean
  onDung: () => void
  vohieu?: boolean
  goiY?: string
  /**
   * Model dang chon co doc anh khong — tu `constraints.reads_images` cua hop
   * dong, KHONG suy tu ten alias.
   *
   * ⛔ Khong co co nay thi o chon tep hien voi MOI model, va nguoi dung dinh
   *    anh vao `ltt_llm` (text-only) roi cho mot cau tra loi ve buc anh ma
   *    model chua bao gio thay. May chu se tu choi (`bat_dau` kiem lai), nhung
   *    moi loi tot nhat la loi khong the bam ra duoc.
   */
  docAnh?: boolean
  /**
   * Hội thoại đang mở. Đổi giá trị này ⇒ bỏ mọi ảnh đang đính.
   *
   * 🔴 Đo trên production: bấm "+ Hội thoại mới" mà ảnh đính **vẫn còn**. Lượt
   *    sau người dùng gõ một câu chẳng liên quan và bức ảnh của hội thoại
   *    trước lặng lẽ đi theo — họ trả tiền cho một ngữ cảnh họ không hề chọn.
   */
  hoiThoai?: string | null
  /** Tai mot tep len, tra ve khoa kho. Nem loi thi o soan hien thong bao. */
  onTaiAnh?: (tep: File) => Promise<AnhDinh>
  /** Tran so anh moi luot — may chu chot lai, day chi de bao som. */
  toiDaAnh?: number
}

export function SoanThao({
  oRef, onGui, dangChay, onDung, vohieu, goiY,
  docAnh, onTaiAnh, toiDaAnh = 4, hoiThoai,
}: SoanThaoProps) {
  const [chu, datChu] = useState('')
  const [anh, datAnh] = useState<AnhDinh[]>([])
  const [dangTai, datDangTai] = useState(false)
  const [loiAnh, datLoiAnh] = useState('')
  const oTep = useRef<HTMLInputElement | null>(null)
  const dangGoIME = useRef(false)
  const oTrong = useRef<HTMLTextAreaElement | null>(null)
  const o = oRef ?? oTrong

  // Cao tu dong: dat lai ve `auto` truoc khi do `scrollHeight`, neu khong o chi
  // to ra chu khong bao gio nho lai.
  useEffect(() => {
    const el = o.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 320)}px`
  }, [chu])

  const gui = useCallback(() => {
    const t = chu.trim()
    if (!t || dangChay || vohieu || dangTai) return
    onGui(t, anh.map((a) => a.key))
    datChu('')
    datAnh([])
    datLoiAnh('')
  }, [chu, dangChay, vohieu, dangTai, anh, onGui])

  const themTep = useCallback(async (ds: FileList | null) => {
    if (!ds || !ds.length || !onTaiAnh) return
    datLoiAnh('')
    // ⛔ Cat theo cho CON LAI, khong theo so tep vua chon: nguoi dung co the
    //    dinh hai lan lien tiep, va tran la tran cua ca luot.
    const con = toiDaAnh - anh.length
    if (con <= 0) { datLoiAnh(`Tối đa ${toiDaAnh} ảnh mỗi lượt.`); return }
    const lay = Array.from(ds).slice(0, con)
    if (lay.length < ds.length) datLoiAnh(`Tối đa ${toiDaAnh} ảnh mỗi lượt.`)
    datDangTai(true)
    // 🔴 TRY NAM TRONG VONG LAP, KHONG BAO NGOAI NO.
    //
    //    Ban dau `try` bao ca vong: tep thu hai hong thi `await` nem, vong lap
    //    thoat, va tep thu BA khong bao gio duoc thu. Do tren production 03/09:
    //    chon 3 anh, mot cai hong ⇒ chi con **1/3**.
    //
    // ⛔ Va day dung la loi LibreChat da dinh: *Uploading multiple files fails
    //    ENTIRELY if any single file exceeds fileSizeLimit*. Nguoi dung chon
    //    muoi anh, mot cai qua co, mat het — va khong biet cai nao co loi.
    //
    // ⭐ Nen: moi tep mot `try`, gom loi lai, va noi TEN tep hong. Nhung tep
    //    tot van len.
    const hong: string[] = []
    try {
      for (const tep of lay) {
        try {
          const a = await onTaiAnh(tep)
          datAnh((cu2) => [...cu2, a])
        } catch (e) {
          hong.push(`${tep.name}: ${doiLoiAnh(e)}`)
        }
      }
      if (hong.length) datLoiAnh(`Không tải được ${hong.length} ảnh — ${hong.join('; ')}`)
    } finally {
      datDangTai(false)
      // Do lai o chon: khong reset thi chon LAI dung tep vua bo di se khong
      // sinh su kien `change` nao ca, va giao dien trong nhu bi treo.
      if (oTep.current) oTep.current.value = ''
    }
  }, [anh.length, onTaiAnh, toiDaAnh])

  // Đổi hội thoại ⇒ ảnh của hội thoại cũ không được đi theo.
  useEffect(() => { datAnh([]); datLoiAnh('') }, [hoiThoai])

  // ⛔ Đổi sang model KHÔNG đọc ảnh ⇒ bỏ ảnh, VÀ NÓI RA.
  //
  //    Đo trên production: ảnh vẫn đính, ô chọn tệp biến mất, và không một
  //    cảnh báo nào. Máy chủ từ chối đúng (`tham_so: model nay khong doc anh`)
  //    nên tiền không mất — nhưng người dùng nhận một lỗi kỹ thuật cho một
  //    việc họ không biết mình đã làm.
  useEffect(() => {
    if (docAnh) return
    datAnh((cu2) => {
      if (cu2.length) datLoiAnh('Model này không đọc ảnh — đã bỏ ảnh đính kèm.')
      return []
    })
  }, [docAnh])

  const phim = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    const dangGo =
      dangGoIME.current ||
      e.key === 'Process' ||
      (e as unknown as { keyCode?: number }).keyCode === 229
    if (e.key !== 'Enter' || e.shiftKey || dangGo) return
    e.preventDefault()
    gui()
  }

  return (
    <div className="ltc-soan">
      {anh.length > 0 && (
        <ul className="ltc-soan__anh" aria-label="Ảnh đã đính">
          {anh.map((a) => (
            <li key={a.key} className="ltc-soan__anh-mot">
              <span className="ltc-soan__anh-ten">{a.ten}</span>
              <button
                type="button"
                className="ltc-soan__anh-bo"
                aria-label={`Bỏ ảnh ${a.ten}`}
                onClick={() => datAnh((c) => c.filter((x) => x.key !== a.key))}
              >×</button>
            </li>
          ))}
        </ul>
      )}
      {loiAnh && <p className="ltc-soan__loi" role="alert">{loiAnh}</p>}
      {docAnh && onTaiAnh && (
        <>
          <input
            ref={oTep}
            type="file"
            className="ltc-soan__tep"
            accept="image/png,image/jpeg,image/webp"
            multiple
            aria-label="Đính ảnh"
            disabled={vohieu || dangTai}
            onChange={(e) => { void themTep(e.target.files) }}
          />
          <button
            type="button"
            className="ltc-nut ltc-nut--anh"
            onClick={() => oTep.current?.click()}
            disabled={vohieu || dangTai || anh.length >= toiDaAnh}
            title="Đính ảnh cho model đọc"
          >{dangTai ? 'Đang tải…' : '📎 Ảnh'}</button>
        </>
      )}
      <textarea
        ref={o}
        className="ltc-soan__o"
        rows={1}
        value={chu}
        placeholder={goiY ?? 'Nhắn cho ChatLTT…'}
        aria-label="Nội dung tin nhắn"
        disabled={vohieu}
        onChange={(e) => datChu(e.target.value)}
        onCompositionStart={() => { dangGoIME.current = true }}
        onCompositionEnd={() => { dangGoIME.current = false }}
        onKeyDown={phim}
      />
      {dangChay ? (
        <button type="button" className="ltc-nut ltc-nut--dung" onClick={onDung}>
          Dừng
        </button>
      ) : (
        <button
          type="button"
          className="ltc-nut ltc-nut--gui"
          onClick={gui}
          disabled={!chu.trim() || vohieu}
        >
          Gửi
        </button>
      )}
    </div>
  )
}
