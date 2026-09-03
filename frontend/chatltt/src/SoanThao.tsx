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

export type SoanThaoProps = {
  /** Cho phim tat "ve o soan" (Shift+Esc) va cho luc mo hoi thoai moi. */
  oRef?: React.RefObject<HTMLTextAreaElement | null>
  onGui: (chu: string) => void
  dangChay: boolean
  onDung: () => void
  vohieu?: boolean
  goiY?: string
}

export function SoanThao({
  oRef, onGui, dangChay, onDung, vohieu, goiY,
}: SoanThaoProps) {
  const [chu, datChu] = useState('')
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
    if (!t || dangChay || vohieu) return
    onGui(t)
    datChu('')
  }, [chu, dangChay, vohieu, onGui])

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
