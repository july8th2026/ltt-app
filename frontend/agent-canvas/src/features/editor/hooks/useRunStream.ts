import { useCallback, useEffect, useRef, useState } from 'react'
import { RUN_V3_KET_THUC, theoDoiRunV3, type RunV3 } from '../../../workflowApi'
import { nhapRun } from '../graph'

/** Giãn cách NỐI LẠI luồng SSE, và do LUI DAN khi cua doc hong.
 *  LUI chu khong DUNG: man hinh nay theo doi mot luot chay DANG TIEU TIEN, nen
 *  bo cuoc nghia la de nguoi dung nhin mot anh chup cu ma tuong la that. Va
 *  khong im lang — moi nhip hong deu hien ngay o dong loi cua ngan keo, va
 *  dong ay tu bien mat khi mot nhip thanh cong. "Thu lai vo han trong im lang"
 *  moi la noi doi; thu lai CO NOI thi khong.
 *
 *  ⭐ P9b task 3: cua doc doi tu POLL sang SSE, nhung ba con so nay O LAI y
 *     nguyen. `EventSource` co san mot co che noi lai — co dinh ~3 s, khong
 *     lui dan, khong noi gi voi nguoi dung — nen dung no la MAT chong-ngap
 *     (mot may chu dang sap bi go cua deu dan mai mai, va man hinh im lang).
 *     `workflowApi.theoDoiRunV3` vi vay DONG luong ngay o `onerror`, va viec
 *     noi lai do khoi nay cam. */
const NHIP_POLL_MS = 1500
const LUI_TOI_DA = 3                       //: 1,5s -> 3s -> 6s -> 12s roi giu 12s
export const LOI_POLL = 'Không đọc được lượt chạy — đang thử lại…'
const nhipCho = (soHong: number) => NHIP_POLL_MS * 2 ** Math.min(soHong, LUI_TOI_DA)

/** NGHE một lượt chạy qua SSE, có lùi dần và có nối lại.
 *
 *  🔴 `soHong` và `lanNoiLai` là HAI bộ đếm KHÁC LOẠI, ⛔ đừng gộp:
 *
 *     · `soHong` — số nhịp HỎNG LIÊN TIẾP. Vừa làm thời gian chờ lùi dần, vừa
 *       là thứ DUY NHẤT làm effect chạy lại sau một cú ngã (`run` không đổi khi
 *       request hỏng, nên không có nó thì không còn `setTimeout` nào cả).
 *     · `lanNoiLai` — mở lại luồng SAU KHI đã nhận được gói, tức mốc 90 s của
 *       máy chủ. Nó KHÔNG phải một nhịp hỏng: không được lùi dần, không được
 *       hiện dòng lỗi.
 *
 *  Đặc tả cả hai: `tests/CanvasShell.test.tsx` — "luong dong sau khi DA nhan
 *  goi thi noi lai NGAY, khong hien loi" và "hong lien tiep thi LUI DAN".
 */
export function useRunStream(run: RunV3 | null,
                             setRun: React.Dispatch<React.SetStateAction<RunV3 | null>>,
                             setRunError: React.Dispatch<React.SetStateAction<string>>) {
  const [soHong, setSoHong] = useState(0)
  const [lanNoiLai, setLanNoiLai] = useState(0)

  // ⭐ Con tro su kien nam trong mot `ref`, KHONG trong deps cua effect duoi.
  //    Neu effect phu thuoc `run` thi moi goi SSE (mot giay mot goi) se thao
  //    va mo lai ca luong — dat hon han vong poll no thay the.
  const conTro = useRef<{ id: string; seq: number }>({ id: '', seq: 0 })
  const runRef = useRef<RunV3 | null>(null)
  useEffect(() => { runRef.current = run }, [run])

  const runId = run?.id ?? ''
  const runDangSong = !!run && !RUN_V3_KET_THUC.has(run.status)
  useEffect(() => {
    if (!runId || !runDangSong) return
    // `active` = phan hoi nay con dung voi man hinh nao khong. Khong co no,
    // mot goi ve MUON de nguoc CANCELLED -> RUNNING (nut "Huy chay" hien lai
    // cho mot luot da chet), hoac lam song lai mot run vua `setRun(null)`.
    let active = true
    if (conTro.current.id !== runId)
      conTro.current = { id: runId, seq: runRef.current?.seq_cuoi ?? 0 }
    // ⭐ Theo TUNG ket noi, khong theo ca man hinh: mot luong DA gui duoc goi
    //    roi dong la moc 90 s cua may chu (`_SSE_DONG_SAU_S`, duoi tran 100 s
    //    cua Cloudflare) — NOI LAI NGAY, khong phai loi, khong hien gi. Mot
    //    luong dong ma CHUA gui gi la hong that ⇒ lui dan + noi ra.
    let daNhan = false
    let dong: (() => void) | null = null
    // ⛔ CHO TRUOC khi mo, khong mo roi moi cho. Day la cho chong-ngap song:
    //    `soHong > 0` nghia la lan mo TRUOC da hong ma chua nhan duoc gi, nen
    //    lan nay phai lui `nhipCho(soHong - 1)` (1,5s -> 3s -> 6s -> 12s).
    //    `soHong === 0` (lan dau, hoac vua noi lai sau moc 90 s) thi mo NGAY:
    //    mot man hinh dang tieu tien khong duoc doi 1,5 giay de biet no chay.
    const timer = window.setTimeout(() => {
      if (!active) return
      dong = theoDoiRunV3(runId, conTro.current.seq, {
      onGoi: next => {
        if (!active) return
        daNhan = true
        conTro.current = { id: next.id, seq: next.seq_cuoi }
        setSoHong(0)
        // Chi xoa thong diep cua CHINH cua doc: mot loi huy/chay dang hien
        // khong phai viec cua no.
        setRunError(cu => cu === LOI_POLL ? '' : cu)
        // Su kien ve theo lo tang dan — NOI, khong thay. Thay la mat lich su
        // moi goi, va dong thoi gian chi con mot dong.
        setRun(truoc => truoc && truoc.id === next.id ? nhapRun(truoc, next) : truoc)
      },
      onLoi: () => {
        if (!active) return
        // `soHong`/`lanNoiLai` doi => effect chay lai => CO lan noi lai ke
        // tiep. Day moi la duong song: nhanh nay khong dung toi `run`, nen
        // neu chi `setRunError` thi man hinh dung han sau mot blip mang.
        if (daNhan) { setSoHong(0); setLanNoiLai(n => n + 1); return }
        setSoHong(soHong + 1)
        setRunError(LOI_POLL)
      },
      })
    }, soHong > 0 ? nhipCho(soHong - 1) : 0)
    return () => { active = false; window.clearTimeout(timer); dong?.() }
  }, [runId, runDangSong, soHong, lanNoiLai]) // eslint-disable-line react-hooks/exhaustive-deps

  /** Bắt đầu một lượt NGHE mới: bộ đếm hỏng về 0 nên luồng mở NGAY. */
  const datLaiSoHong = useCallback(() => setSoHong(0), [])

  return { datLaiSoHong }
}
