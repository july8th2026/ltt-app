/**
 * App.tsx — vo ChatLTT: thanh ben (hoi thoai) + luong chinh + o soan.
 *
 * ⭐ MAY CHU LA NGUON CHAN LY. Sau moi luot, sau moi lan chuyen nhanh, sau moi
 *    F5, giao dien doc lai `su_that()` va ve theo do. Trinh duyet chi giu hai
 *    thu tam: chu dang go, va cac su kien delta cua luot dang chay.
 *
 * ⛔ Do la ly do khong co "optimistic update" phuc tap o day. Mot ban sao lac
 *    quan cua cay la mot nguon chan ly thu hai, va no se lech — dung cai
 *    `docs/CHATLTT/00_PHUONG_AN_VA_LO_TRINH.md` D6 chon cach tranh.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Api, docSSE, LoiApi } from './api'
import { duongToiLa, laKhiChuyenNhanh } from './cay'
import { SoanThao } from './SoanThao'
import { TaoMedia } from './TaoMedia'
import { ThongDiepView } from './ThongDiepView'
import type { HoiThoai, NangLuc, SuThat, ThongDiep } from './kieu'

const MA_LOI: Record<string, string> = {
  ban: 'Model đang bận. Thử lại sau ít giây.',
  het_credit: 'Không đủ credit cho lượt này.',
  qua_dai: 'Hội thoại vượt trần ngữ cảnh. Bắt đầu hội thoại mới hoặc rút ngắn câu hỏi.',
  khong_mo_duoc: 'Không gọi được model lúc này.',
  khong_tim_thay: 'Không tìm thấy.',
  csrf: 'Phiên đã cũ. Tải lại trang.',
  tham_so: 'Nội dung không hợp lệ.',
}

function nhanLoi(e: unknown): string {
  if (e instanceof LoiApi) return MA_LOI[e.code] ?? e.message ?? e.code
  return 'Có lỗi xảy ra.'
}

export type AppProps = { api: Api }

export function App({ api }: AppProps) {
  const [nangLuc, datNangLuc] = useState<NangLuc[]>([])
  const [dsHoiThoai, datDsHoiThoai] = useState<HoiThoai[]>([])
  const [tim, datTim] = useState('')
  const [convId, datConvId] = useState<string | null>(null)
  const [suThat, datSuThat] = useState<SuThat | null>(null)
  const [alias, datAlias] = useState('')
  const [loi, datLoi] = useState('')
  const [dangChayEx, datDangChayEx] = useState<string | null>(null)
  const [soDu, datSoDu] = useState<number | null>(null)
  const [chuDocTo, datChuDocTo] = useState('')
  const oSoan = useRef<HTMLTextAreaElement | null>(null)
  const dungRef = useRef<(() => Promise<void>) | null>(null)
  const huy = useRef<AbortController | null>(null)
  const cuoiLuong = useRef<HTMLDivElement | null>(null)
  const nguoiDungDaCuon = useRef(false)

  const nangLucText = useMemo(
    () => nangLuc.find((n) => n.ten === 'text.chat'), [nangLuc],
  )
  const aliasCoThe = useMemo(
    () => Object.keys(nangLucText?.models ?? {}), [nangLucText],
  )

  useEffect(() => {
    api.danhMuc()
      .then((d) => {
        datNangLuc(d.nang_luc)
        const text = d.nang_luc.find((n) => n.ten === 'text.chat')
        const dau = Object.keys(text?.models ?? {})[0] ?? ''
        datAlias((a) => a || dau)
      })
      .catch((e) => datLoi(nhanLoi(e)))
  }, [api])

  const napSoDu = useCallback(() => {
    api.soDu().then((d) => datSoDu(d.credit)).catch(() => {})
  }, [api])

  useEffect(() => { napSoDu() }, [napSoDu])

  const napDs = useCallback(() => {
    api.lietKe(tim).then((d) => datDsHoiThoai(d.hoi_thoai)).catch(() => {})
  }, [api, tim])

  useEffect(() => { napDs() }, [napDs])

  const napSuThat = useCallback(async (id: string) => {
    const st = await api.suThat(id)
    datSuThat(st)
    if (st.conversation.model_alias) datAlias(st.conversation.model_alias)
    return st
  }, [api])

  useEffect(() => {
    api.convHienTai = convId ?? ''
    if (!convId) { datSuThat(null); return }
    napSuThat(convId).catch((e) => datLoi(nhanLoi(e)))
  }, [api, convId, napSuThat])

  // ── Nhip hoi cho job anh/tieng (Q87: 2 giay khi khoe) ────────────────────
  //
  // ⭐ Job KHONG day su kien sang web (khac stream text): worker chay o tien
  //    trinh khac. Nen tien do den tu viec HOI, va `dong_bo()` phia may chu la
  //    ham an toan goi nhieu lan.
  useEffect(() => {
    const dangCho = (suThat?.messages ?? []).filter(
      (m) => m.execution?.mode === 'job'
        && (m.status === 'queued' || m.status === 'streaming'),
    )
    if (!dangCho.length || !convId) return
    let dung = false
    const h = window.setInterval(async () => {
      if (dung) return
      try {
        await Promise.all(dangCho.map((m) => api.trangThai(m.execution!.id)))
        await napSuThat(convId)
        napSoDu()
      } catch {
        // Mot nhip hong khong lam hong ca man hinh; nhip sau thu lai.
      }
    }, 2000)
    return () => { dung = true; window.clearInterval(h) }
  }, [api, convId, suThat, napSuThat, napSoDu])

  // ── Phim tat ────────────────────────────────────────────────────────────
  //
  // ⭐ Tap TOI THIEU, va moi phim deu co ly do: hai viec lam nhieu nhat (mo hoi
  //    thoai moi, quay ve o soan) va mot viec KHAN (dung mot luot dang chay).
  //    Bang phim tat dai la bang khong ai nho — bao cao Phase 01 §11.3 liet ke
  //    12 phim cua LibreChat, va phan lon chung khong ai dung.
  //
  // ⛔ Khong `preventDefault` khi khong lam gi: chan mot phim goc ma khong thay
  //    the no la lay mat mot thao tac cua trinh duyet, im lang.
  useEffect(() => {
    const nghe = (e: KeyboardEvent) => {
      const mod = e.ctrlKey || e.metaKey
      if (mod && e.shiftKey && (e.key === 'o' || e.key === 'O')) {
        e.preventDefault()
        datConvId(null); datSuThat(null)
        oSoan.current?.focus()
        return
      }
      if (mod && e.shiftKey && (e.key === 'x' || e.key === 'X')) {
        if (!dangChayEx) return               // khong co gi de dung: de phim di
        e.preventDefault()
        void dungRef.current?.()
        return
      }
      // Shift+Esc: ve o soan. Cung phim LibreChat dung (`focusChat`).
      if (e.shiftKey && e.key === 'Escape') {
        e.preventDefault()
        oSoan.current?.focus()
      }
    }
    window.addEventListener('keydown', nghe)
    return () => window.removeEventListener('keydown', nghe)
  }, [dangChayEx])

  // Cuon xuong khi co chu moi — TRU khi nguoi dung da tu cuon len.
  // (Ky thuat `abortScroll` cua LibreChat, `useMessageHelpers.tsx:37-53`.)
  useEffect(() => {
    if (nguoiDungDaCuon.current) return
    cuoiLuong.current?.scrollIntoView({ behavior: 'instant', block: 'end' })
  }, [suThat])

  const theoDoi = useCallback(async (executionId: string, cid: string) => {
    huy.current?.abort()
    const ac = new AbortController()
    huy.current = ac
    datDangChayEx(executionId)
    nguoiDungDaCuon.current = false
    try {
      await docSSE(api.duongStream(executionId), (sk) => {
        if (sk.type === 'snapshot' || sk.type === 'end') return
        // Delta: cap nhat tai cho de chu chay muot, khong doi mot vong mang.
        datSuThat((cu) => {
          if (!cu) return cu
          const ms = cu.messages.map((m) => {
            if (m.execution_id !== executionId || !m.execution) return m
            const ex = { ...m.execution }
            if (sk.type === 'response.delta') {
              ex.partial_text += String((sk.data as { text?: string }).text ?? '')
            } else if (sk.type === 'reasoning.delta') {
              ex.reasoning_text += String((sk.data as { text?: string }).text ?? '')
            }
            return { ...m, execution: ex }
          })
          return { ...cu, messages: ms }
        })
      }, ac.signal)
    } catch (e) {
      if (!ac.signal.aborted) datLoi(nhanLoi(e))
    } finally {
      datDangChayEx(null)
      // Luon doc lai su that: delta o tren chi de nhin, khong phai de tin.
      await napSuThat(cid).catch(() => {})
      napDs()
      napSoDu()
    }
  }, [api, napSuThat, napDs, napSoDu])

  const guiLuot = useCallback(async (than: {
    text?: string; parentId?: string | null; taoLaiCua?: string
  }) => {
    datLoi('')
    let cid = convId
    try {
      if (!cid) {
        const h = await api.taoHoiThoai(alias)
        cid = h.id
        datConvId(h.id)
      }
      const kq = await api.guiLuot(cid, { ...than, modelAlias: alias })
      await napSuThat(cid)
      void theoDoi(kq.execution_id, cid)
    } catch (e) {
      datLoi(nhanLoi(e))
    }
  }, [api, alias, convId, napSuThat, theoDoi])

  const dung = useCallback(async () => {
    if (!dangChayEx) return
    try { await api.dung(dangChayEx) } catch (e) { datLoi(nhanLoi(e)) }
    huy.current?.abort()
  }, [api, dangChayEx])

  useEffect(() => { dungRef.current = dung }, [dung])

  const chuyenNhanh = useCallback(async (m: ThongDiep, idx: number) => {
    if (!convId || !suThat) return
    const la = laKhiChuyenNhanh(suThat.messages, m, idx)
    if (!la) return
    try {
      await api.chonLa(convId, la)
      await napSuThat(convId)
    } catch (e) { datLoi(nhanLoi(e)) }
  }, [api, convId, suThat, napSuThat, napSoDu])

  const duong = useMemo(
    () => (suThat ? duongToiLa(suThat.messages, suThat.conversation.current_leaf_id) : []),
    [suThat],
  )
  const chuaSanSang = nangLucText?.san_sang !== 'san_sang'
  const coTieng = nangLuc.some(
    (n) => n.phuong_thuc === 'audio' && n.san_sang === 'san_sang',
  )

  return (
    <div className="ltc">
      <aside className="ltc-ben" aria-label="Hội thoại">
        <button
          type="button"
          className="ltc-nut ltc-nut--moi"
          onClick={() => { datConvId(null); datSuThat(null) }}
        >
          + Hội thoại mới
        </button>
        <input
          className="ltc-tim"
          type="search"
          value={tim}
          placeholder="Tìm hội thoại…"
          aria-label="Tìm hội thoại"
          onChange={(e) => datTim(e.target.value)}
        />
        <ul className="ltc-ds">
          {dsHoiThoai.map((h) => (
            <li key={h.id}>
              <button
                type="button"
                className={`ltc-ds__muc${h.id === convId ? ' la-dang-xem' : ''}`}
                aria-current={h.id === convId ? 'true' : undefined}
                onClick={() => datConvId(h.id)}
              >
                {h.title || 'Hội thoại mới'}
              </button>
            </li>
          ))}
        </ul>
      </aside>

      <main className="ltc-chinh">
        <header className="ltc-dinh">
          <label className="ltc-model">
            <span>Model</span>
            <select
              value={alias}
              aria-label="Chọn model"
              onChange={(e) => datAlias(e.target.value)}
            >
              {aliasCoThe.map((a) => (
                <option key={a} value={a}>{a}</option>
              ))}
            </select>
          </label>
          {chuaSanSang && (
            <span className="ltc-chip ltc-chip--tat" role="status">
              Model chưa sẵn sàng
            </span>
          )}
          {soDu != null && (
            <span className="ltc-sodu" role="status" aria-live="polite"
              aria-label={`Số dư ${soDu} credit`}>
              💎 {soDu.toLocaleString('vi-VN')} credit
            </span>
          )}
        </header>

        <div
          className="ltc-luong"
          onScroll={(e) => {
            const el = e.currentTarget
            nguoiDungDaCuon.current =
              el.scrollHeight - el.scrollTop - el.clientHeight > 120
          }}
        >
          {duong.length === 0 && (
            <p className="ltc-trong">Bắt đầu bằng một câu hỏi.</p>
          )}
          {duong.map((m) => (
            <ThongDiepView
              key={m.id}
              m={m}
              phang={suThat?.messages ?? []}
              onChuyenNhanh={chuyenNhanh}
              duongTaiSan={(k) => api.duongTaiSan(k)}
              onDocTo={coTieng ? (_m, c) => datChuDocTo(c) : undefined}
              onTaoLai={(x) => guiLuot({ taoLaiCua: x.id })}
              onSuaGuiLai={(x) => {
                const chu = window.prompt('Sửa câu hỏi',
                  x.blocks.filter((k) => k.type === 'text').map((k) => k.text).join('\n'))
                if (chu != null && chu.trim()) {
                  guiLuot({ text: chu, parentId: x.parent_id })
                }
              }}
            />
          ))}
          <div ref={cuoiLuong} />
        </div>

        {convId && (
          <TaoMedia
            api={api}
            nangLuc={nangLuc}
            onXong={() => { napSuThat(convId).catch(() => {}); napSoDu() }}
            onLoi={datLoi}
            chuDocTo={chuDocTo}
            onDaNhanChuDocTo={() => datChuDocTo('')}
          />
        )}

        {loi && <p className="ltc-loi" role="alert">{loi}</p>}

        <SoanThao
          oRef={oSoan}
          onGui={(chu) => guiLuot({ text: chu })}
          dangChay={dangChayEx != null}
          onDung={dung}
          vohieu={chuaSanSang}
          goiY={chuaSanSang ? 'Model chưa sẵn sàng' : undefined}
        />
      </main>
    </div>
  )
}
