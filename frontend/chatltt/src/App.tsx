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
import { BangGhiNho } from './BangGhiNho'
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

//: Hội thoại đang mở nằm ở `#<id>` của URL.
//
// 🔴 VÌ SAO CẦN. Không có nó thì **mỗi lần tải lại trang là mất chỗ đang đứng**:
//    danh sách hội thoại còn nguyên (cây lưu trong CSDL, `current_leaf_id` giữ
//    đúng nhánh), nhưng màn hình rơi về "Bắt đầu bằng một câu hỏi". Đo trong
//    hành trình A của Phase 13.
//
// ⭐ Và mất chỗ đứng chỉ là triệu chứng dễ thấy nhất. Thứ thực sự thiếu là
//    **hội thoại không có địa chỉ**: không đánh dấu trang được, không gửi link
//    cho người khác được, và Back/Forward của trình duyệt không đi lại được
//    giữa các hội thoại. Đó là ba thao tác người ta làm hàng ngày với một sản
//    phẩm chat, và MVP đòi "LibreChat-class core ergonomics".
//
// ⛔ Dùng `hash` chứ không phải một route `/chatltt/c/<id>`. Một route mới là
//    một đường máy chủ mới — phải khai, phải kiểm quyền, phải sinh HTML, và
//    phải nhớ rằng `I18nMiddleware` chèn tiền tố ngôn ngữ vào **mọi** đường.
//    Hash không đi tới máy chủ nên nó không mua thêm bề mặt nào cả, và nó cho
//    đủ ba thao tác trên.
function docHash(): string | null {
  if (typeof window === 'undefined') return null
  const h = window.location.hash.replace(/^#/, '').trim()
  return h || null
}

//: Go hash NGAY, khong doi vong ve cua React.
//
// ⛔ Ban dau cho hieu ung dong bo lo viec nay: `datConvId(null)` roi de hieu ung
//    `[convId]` xoa hash. No SAI, va cai sai chi lo ra khi do: neu component
//    gan lai vi bat ky ly do gi truoc khi hieu ung kip chay, `useState(docHash)`
//    doc lai hash CU va id hong quay tro lai — mot vong lap giua trang thai
//    React va thanh dia chi trinh duyet, hai nguon chan ly danh nhau.
//
// ⭐ Nen thu tac dung phu (URL) duoc lam TRUOC, dong bo, roi moi den trang thai.
//    Sau do hieu ung `[convId]` chi con viec giu chung khop nhau.
function xoaHash(): void {
  if (typeof window === 'undefined') return
  window.history.replaceState(null, '',
    window.location.pathname + window.location.search)
}


/* ⭐ `khiHien` — chay `viec` theo nhip, nhung KHONG chay khi tab dang an, va
 *    chay lai NGAY khi tab hien lai.
 *
 *    Do 05/09: nam vong hoi trang thai job trong kho, khong vong nao biet tab
 *    dang an. Tren dien thoai do la pin va dung luong 3G cua khach chay trong
 *    khi ho dang lam viec khac — con job thi van chay o may chu du khong ai hoi.
 *
 * ⚠️ CO Y khong dung mot hook dung chung: hai app React o kho nay la hai goi
 *    npm rieng, khong co thu muc nguon chung. Mot "hook dung chung" o day se la
 *    HAI BAN CHEP — dung cai da sinh ra nam ban Range trong `apps/`. Muoi dong
 *    lap lai, khong co truu tuong nao de troi.
 *
 * ⛔ Trang thai job o MAY CHU la chan ly. Tab an chi GIAM nhip hoi. */
function khiHien(viec: () => void, nhip: number): () => void {
  const chay = () => { if (!document.hidden) viec() }
  const h = window.setInterval(chay, nhip)
  const lai = () => { if (!document.hidden) viec() }
  document.addEventListener('visibilitychange', lai)
  window.addEventListener('online', lai)
  return () => {
    window.clearInterval(h)
    document.removeEventListener('visibilitychange', lai)
    window.removeEventListener('online', lai)
  }
}

export function App({ api }: AppProps) {
  const [nangLuc, datNangLuc] = useState<NangLuc[]>([])
  const [dsHoiThoai, datDsHoiThoai] = useState<HoiThoai[]>([])
  const [tim, datTim] = useState('')
  const [convId, datConvId] = useState<string | null>(docHash)
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
  /**
   * Lần đổi hội thoại sắp tới có phải do NGƯỜI DÙNG chủ động không.
   *
   * 🔴 Đo trên production 03/09: bấm Back **rời khỏi trang** thay vì về hội
   *    thoại trước. Vì mọi lần đổi đều `replaceState`, nên lịch sử chỉ có đúng
   *    một mục — không có gì để lùi về.
   *
   * ⭐ Ranh giới đúng: **người dùng chủ động đổi chỗ ⇒ một bước lịch sử**; máy
   *    chủ vừa cấp địa chỉ cho chỗ đang đứng ⇒ **không** phải một bước. Gửi tin
   *    đầu tiên không đưa họ đi đâu cả — nó chỉ làm chỗ họ đang đứng có tên.
   *
   * ⛔ Và đây là lý do KHÔNG `pushState` cho mọi thứ: bản đầu của tệp này ghi
   *    rõ vì sao dùng `replaceState` — mười lần bấm quanh thanh bên thì phải
   *    bấm Back mười lần mới rời được trang. Cả hai lo ngại đều thật; chúng chỉ
   *    thuộc hai loại thay đổi khác nhau.
   */
  const dayLichSu = useRef(false)

  /** Đổi hội thoại theo ý người dùng — có một bước lịch sử. */
  const chonHoiThoai = useCallback((id: string | null) => {
    dayLichSu.current = true
    datConvId(id)
    if (id === null) datSuThat(null)
  }, [])

  const nangLucText = useMemo(
    () => nangLuc.find((n) => n.ten === 'text.chat'), [nangLuc],
  )
  const aliasCoThe = useMemo(
    () => Object.keys(nangLucText?.models ?? {}), [nangLucText],
  )

  const [coGhiNho, datCoGhiNho] = useState(false)
  const [moGhiNho, datMoGhiNho] = useState(false)

  const napDanhMuc = useCallback(() => api.danhMuc()
    .then((d) => {
      datNangLuc(d.nang_luc)
      // ⛔ Vang => TAT. Mot may chu cu hon frontend khong khai `co_v3`, va doan
      //    "khong khai tuc la co" se hien mot nut dan thang toi 404.
      datCoGhiNho(!!d.co_v3?.ghi_nho)
      const text = d.nang_luc.find((n) => n.ten === 'text.chat')
      // ⛔ `model_mac_dinh` chu KHONG `Object.keys(models)[0]`. Ban cu lay
      //    phan tu dau cua mot dict, tuc mac dinh la THU TU KHAI trong
      //    `apps/ltt_llm/manifest.py`. No dung — mot cach tinh co. Dao hai
      //    dong ben do la ca san pham lang le chuyen sang `ltt_llm_vision`,
      //    model co ngu canh 28K thay vi 89K.
      const dau = text?.model_mac_dinh || Object.keys(text?.models ?? {})[0] || ''
      datAlias((a) => a || dau)
      return d.nang_luc
    }), [api])

  useEffect(() => { napDanhMuc().catch((e) => datLoi(nhanLoi(e))) }, [napDanhMuc])

  // ── Nang luc chua san sang thi HOI LAI, dung doi F5 ──────────────────────
  //
  // 🔴 VI SAO CAN. Danh muc truoc day chi duoc nap **mot lan** luc gan component.
  //    Model anh/tieng nam o may B va nap sau vai phut; ai mo trang truoc do se
  //    thay nut "Tao giong" vo hieu **vinh vien** — khong co gi bao, khong co gi
  //    doi, va cach duy nhat thoat ra la bam F5 ma khong ai noi cho ho biet.
  //
  // ⭐ Do 04/09 tren production, va no lo ra tu chinh dong bo qua cua bo kiem:
  //    *"model tieng chua nap — may chu noi speech.ltt=san_sang"*. Mot cau tu
  //    mau thuan: nut vo hieu suot 210 giay trong khi may chu bao san sang. Bo
  //    kiem khong bat duoc loi nay, no chi ghi lai du kien; thu bat duoc la
  //    **doc ky mot dong BOQUA thay vi hai long vi no khong do**.
  //
  // ⛔ Chi hoi lai KHI CON THIEU, va dung ngay khi du. Mot vong lap chay mai la
  //    mot vong lap se bi ai do tat di vi ton, roi mang theo ca cai nay.
  useEffect(() => {
    const thieu = nangLuc.some((n) => n.san_sang !== 'san_sang')
    if (!nangLuc.length || !thieu) return undefined
    return khiHien(() => { void napDanhMuc().catch(() => {}) }, 20_000)
  }, [nangLuc, napDanhMuc])

  const napSoDu = useCallback(() => {
    api.soDu().then((d) => datSoDu(d.credit)).catch(() => {})
  }, [api])

  useEffect(() => { napSoDu() }, [napSoDu])

  const napDs = useCallback(() => {
    api.lietKe(tim).then((d) => datDsHoiThoai(d.hoi_thoai)).catch(() => {})
  }, [api, tim])

  useEffect(() => { napDs() }, [napDs])

  /**
   * Nạp sự thật của một hội thoại.
   *
   * 🔴 `dongBoAlias` MẶC ĐỊNH `false`, VÀ ĐÓ LÀ CẢ BẢN VÁ.
   *
   *    Bản cũ đặt lại `alias` ở **mọi** lời gọi. Mà hàm này được gọi từ **bảy**
   *    chỗ: sau khi gửi lượt, sau khi luồng kết thúc, sau khi tạo media… Nên
   *    người dùng chọn một model rồi bất kỳ lần làm mới nào cũng **âm thầm trả
   *    về model cũ**.
   *
   * ⛔ Đo 04/09 trên production: chọn `ltt_llm_vision`, ô chọn quay lại
   *    `ltt_llm` sau ~16 giây, không một thông báo nào. Khách nghĩ mình đang
   *    dùng model đọc ảnh, trả tiền cho một model khác, và không có cách nào
   *    biết. Lỗi tiền + lỗi tin cậy, im lặng cả hai.
   *
   * ⭐ Đồng bộ alias chỉ có nghĩa khi ta **vừa mở một hội thoại** — lúc đó model
   *    của hội thoại là sự thật. Ở mọi lời gọi khác, thứ đúng là **lựa chọn
   *    người dùng vừa làm**, không phải giá trị cũ trong CSDL.
   */
  const napSuThat = useCallback(async (id: string,
                                       { dongBoAlias = false } = {}) => {
    const st = await api.suThat(id)
    datSuThat(st)
    if (dongBoAlias && st.conversation.model_alias) datAlias(st.conversation.model_alias)
    return st
  }, [api])

  useEffect(() => {
    api.convHienTai = convId ?? ''
    if (!convId) { datSuThat(null); return }
    // ⭐ CHO DUY NHAT truyen `dongBoAlias: true` — day la luc VUA MO mot hoi
    //    thoai, nen model cua no la su that. Xem docstring `napSuThat`.
    napSuThat(convId, { dongBoAlias: true }).catch((e) => {
      datLoi(nhanLoi(e))
      // ⛔ VA TRA VE MAN HINH TRONG, khong dung o mot man hinh loi.
      //
      //    Tu khi URL mang `#<id>`, mot id co the den tu mot dau trang cu, tu
      //    mot hoi thoai da xoa, hay tu link cua NGUOI KHAC (may chu tra 404 —
      //    dung). Neu chi hien loi thi trang do dung yen, va tai lai van the:
      //    nguoi dung mac ket o mot man hinh khong co loi thoat nao.
      //
      //    Xoa `convId` vua bao loi vua go hash, nen lan tai sau la mot trang
      //    sach. Thong bao van con — ho biet chuyen gi da xay ra.
      xoaHash()
      datConvId(null)
    })
  }, [api, convId, napSuThat])

  // ── URL <-> hội thoại đang mở, hai chiều ────────────────────────────────
  //
  // ⛔ `replaceState` chứ KHÔNG gán `location.hash`. Gán thẳng đẩy một mục vào
  //    lịch sử cho **mỗi** lần chọn, nên sau mười lần bấm quanh sidebar thì nút
  //    Back phải bấm mười lần mới rời được trang. Ở đây URL là để **mô tả** chỗ
  //    đang đứng, không phải để ghi lại từng thao tác.
  useEffect(() => {
    if (typeof window === 'undefined') return
    const muon = convId ? `#${convId}` : ''
    if (window.location.hash === muon) return
    const duong = window.location.pathname + window.location.search + muon
    if (dayLichSu.current) {
      dayLichSu.current = false
      window.history.pushState(null, '', duong)
    } else {
      window.history.replaceState(null, '', duong)
    }
  }, [convId])

  // Back/Forward của trình duyệt, và người dán một link vào thanh địa chỉ.
  useEffect(() => {
    if (typeof window === 'undefined') return
    const nghe = () => datConvId(docHash())
    window.addEventListener('hashchange', nghe)
    return () => window.removeEventListener('hashchange', nghe)
  }, [])

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
    const huy = khiHien(() => { void (async () => {
      if (dung) return
      try {
        await Promise.all(dangCho.map((m) => api.trangThai(m.execution!.id)))
        await napSuThat(convId)
        napSoDu()
      } catch {
        // Mot nhip hong khong lam hong ca man hinh; nhip sau thu lai.
      }
    })() }, 2000)
    return () => { dung = true; huy() }
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
        chonHoiThoai(null)
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

  // Model dang chon co doc anh khong — theo `constraints.reads_images` DA KHAI
  // trong hop dong, khong suy tu ten alias. Xem `luot.doc_anh_duoc` phia may
  // chu: hai ben phai doc CUNG mot cho, neu khong o chon tep se hien cho mot
  // model se tu choi anh.
  const docAnh = useMemo(
    () => Boolean(
      (nangLucText?.models?.[alias] as { constraints?: { reads_images?: boolean } }
        | undefined)?.constraints?.reads_images,
    ),
    [nangLucText, alias],
  )

  const taiAnh = useCallback(
    async (tep: File) => {
      const kq = await api.taiAnh(tep)
      return { key: kq.key, ten: tep.name }
    },
    [api],
  )

  const guiLuot = useCallback(async (than: {
    text?: string; parentId?: string | null; taoLaiCua?: string; anh?: string[]
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
      // 🔴 NAP LAI DANH SACH. Thieu dong nay thi hoi thoai moi KHONG hien trong
      //    thanh ben cho toi khi mot thu khac tinh co lam moi no — nguoi dung
      //    vua tao mot hoi thoai va no khong o dau ca.
      //
      // ⛔ Va do dung la issue DANG MO cua LibreChat: *New chat has no label
      //    until page refresh*. `bat_dau` phia may chu DA dat `hoi.title` tu
      //    tin nhan dau, nen tieu de co san — chi la khong ai di lay.
      //
      // ⭐ Do bang dot 2 tren production: doi 25 giay ma thanh ben khong bao gio
      //    co muc moi. Toi da TUONG minh thay no hien o hanh trinh A hom nay;
      //    phep do noi khac, va phep do dung.
      napDs()
      void theoDoi(kq.execution_id, cid)
    } catch (e) {
      datLoi(nhanLoi(e))
    }
  }, [api, alias, convId, napSuThat, napDs, theoDoi])

  // ── Nối lại luồng text sau khi tải lại trang ────────────────────────────
  //
  // 🔴 ĐO ĐƯỢC TRÊN PRODUCTION 03/09. F5 giữa lúc model đang trả lời:
  //
  //        giao diện          máy chủ
  //     t+ 0s   chữ = 0       streaming, partial =    0
  //     t+ 8s   chữ = 0       streaming, partial =  796
  //     t+25s   chữ = 0       streaming, partial = 3429   ← vẫn đang sinh
  //
  //    Máy chủ chạy hoàn hảo. Giao diện không hiện gì: không chữ, không nút
  //    Dừng, không nút Tạo lại. Người dùng ngồi nhìn một hộp trắng cho tới khi
  //    họ tự F5 **lần nữa**.
  //
  // ⭐ Và phía máy chủ ĐÃ dựng sẵn cho việc này từ Phase 08a: `dang_chay` là
  //    một sổ fan-out nhiều người nghe, và docstring của route viết thẳng
  //    "Nối lại = mở lại `stream?after=<seq>` — snapshot đầu tiên mang đủ phần
  //    đã có". Thiếu đúng một chỗ: **client chưa bao giờ gọi**.
  //
  // ⛔ `theoDoi` trước đó chỉ chạy trên đường GỬI. Một luồng chỉ được theo dõi
  //    bởi chính cú bấm sinh ra nó là một luồng mất hút sau mọi lần tải lại,
  //    mọi lần đổi hội thoại, mọi lần mở từ một link.
  //
  // ⚠️ Điều kiện `dangChayEx !== ex.id` là bắt buộc, không phải tối ưu: thiếu
  //    nó thì mỗi delta làm `suThat` đổi, hiệu ứng chạy lại, `theoDoi` huỷ
  //    chính kết nối đang chạy rồi mở lại — một vòng lặp huỷ-mở vô tận.
  useEffect(() => {
    if (!convId || !suThat) return
    const dangSong = suThat.messages.find(
      (m) => m.role === 'assistant' && m.status === 'streaming'
        && m.execution?.mode === 'stream' && m.execution.id,
    )
    if (!dangSong?.execution) return
    if (dangChayEx === dangSong.execution.id) return
    void theoDoi(dangSong.execution.id, convId)
  }, [convId, suThat, dangChayEx, theoDoi])

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
          onClick={() => chonHoiThoai(null)}
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
                onClick={() => chonHoiThoai(h.id)}
              >
                {h.title || 'Hội thoại mới'}
              </button>
            </li>
          ))}
        </ul>

        {/*
          ⛔ Nut nay chi hien khi co `LTT_CHATLTT_V3_MEMORY` BAT. Hien no khi co
             tat la dan nguoi dung toi mot route tra 404 — mot loi hua hong, va
             la dung ly do `cong_ghi_nho` tra 404 chu khong 403.
        */}
        {coGhiNho && (
          <button
            type="button"
            className="ltc-nut ltc-nut--ghinho"
            onClick={() => datMoGhiNho(true)}
          >
            Máy nhớ gì về bạn
          </button>
        )}
      </aside>

      {moGhiNho && (
        <BangGhiNho api={api} onDong={() => datMoGhiNho(false)} />
      )}

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
          onGui={(chu, anh) => guiLuot({ text: chu, anh })}
          dangChay={dangChayEx != null}
          onDung={dung}
          vohieu={chuaSanSang}
          goiY={chuaSanSang ? 'Model chưa sẵn sàng' : undefined}
          docAnh={docAnh}
          onTaiAnh={taiAnh}
          hoiThoai={convId}
        />
      </main>
    </div>
  )
}
