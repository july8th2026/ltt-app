/**
 * TheDuyet.tsx — cua CUOI truoc khi mot lenh tieu tien cua khach chay.
 * (H44 P09)
 *
 * ## Truoc the nay, backend duyet la mot cua khong ai bam duoc
 *
 * `_p_duyet.py` co du hai cua (`dang-cho`, `POST /{id}`), `ChatlttApproval` ben
 * qua F5/restart, `bo_chay_tool` doc `doi_so_cuoi()` de chay dung ban da sua.
 * Ca duong day hoan chinh — tru mot dieu: **giao dien khong co mot cai nut
 * nao**. Do 07/09: `grep "Duyệt|Từ chối"` tren `src/` ra **0**.
 *
 * ⛔ Va mot luot dang cho duyet hien ra chu `cho_duyet` — nguyen ma, vi
 *    `NHAN_TRANG_THAI` khong khai no. Dung cai chu thich trong chinh
 *    `ThongDiepView` canh bao: *"Khong co nhan thi no do NGUYEN MA ra man
 *    hinh… khong vo, va vi the khong ai bao loi"*.
 *
 * ## Bon thu ke hoach doi the nay phai noi
 *
 *     y dinh   ten tool -> cau nguoi doc hieu
 *     doi so   se chay VOI cai gi
 *     chi phi  ton bao nhieu credit          <- khoi `tool_call` KHONG noi duoc
 *     he qua   lop chinh sach -> mot cau
 *
 * ⭐ Cot **chi phi** la ly do the nay khong gop duoc vao `KhoiTool`: khoi
 *    `tool_call` khong mang `bao_gia_credit`, chi phieu duyet mang. Sang 07/09
 *    toi da ghi thieu sot ay ra; the nay la cho no duoc tra loi.
 *
 * ## \U0001f534 Sua doi so -> PHAI bao gia lai truoc khi cho bam Duyet
 *
 * `_nop_job` gui `credit_da_bao = p.bao_gia_credit` — **so khach da nhin thay**
 * — va `tao_media.tao` tinh lai roi **tu choi neu lech**. Nen neu khach sua
 * `count: 1 -> 4` roi bam Duyet, lenh se bi tu choi, va ho chi biet dieu do khi
 * doc cau tra loi cua model vai giay sau.
 *
 * ⭐ Muon tu `assistant-ui` (MIT, doc 07/09, KHONG cham ma): `useToolArgsStatus`
 *    ton tai de *"tranh hien mot gia tri doi so chua hoan tat nhu the da cuoi
 *    cung"*. Cung nguyen tac, doi tuong khac: **mot cai gia chua bao lai khong
 *    duoc ve nhu mot cai gia**.
 *
 * ## Han 30 phut — va "het han" khac "khong biet"
 *
 * `duyet.HAN_CHO_PHUT = 30`. Het han thi may chu tra **409**, nen mot the con
 * nut sau khi het han la mot the day nguoi dung vao mot loi. Dem nguoc, va het
 * gio thi tat nut + noi ly do.
 *
 * ⚠️ `het_han_luc` khong doc duoc (chuoi la, dong ho lech) thi hien
 *    **"khong ro"**, KHONG hien "0 phut". Cung luat `trang = 0` cua trich dan:
 *    khong biet khac khong.
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { LoiApi, type Api } from './api'
import { doiSoCoNhan, khoaCoNhan, nhanCuaKhoa, nhanTool } from './KhoiTool'
import type { PhieuDuyet } from './kieu'

/** Lop chinh sach -> HE QUA, bang tieng nguoi. */
const NHAN_HE_QUA: Record<string, string> = {
  PAID: 'Việc này tiêu credit của bạn.',
  EXTERNAL_WRITE: 'Việc này ghi ra một hệ thống bên ngoài.',
  DESTRUCTIVE: 'Việc này có thể xoá hoặc ghi đè dữ liệu.',
}
const HE_QUA_LA = 'Việc này cần bạn xác nhận trước khi chạy.'

/** Phut con lai, hoac `null` khi KHONG DOC DUOC (khac voi 0). */
export function phutConLai(hetHanLuc: string, bayGio = Date.now()): number | null {
  const t = Date.parse(hetHanLuc)
  if (!Number.isFinite(t)) return null
  return Math.floor((t - bayGio) / 60_000)
}

export function cauHetHan(phut: number | null): string {
  if (phut === null) return 'Không rõ hạn'
  if (phut < 0) return 'Đã hết hạn'
  if (phut === 0) return 'Hết hạn trong dưới một phút'
  return `Còn ${phut} phút để quyết`
}

type Props = {
  api: Api
  phieu: PhieuDuyet
  /** Goi sau khi quyet xong — App tai lai danh sach va su that hoi thoai. */
  onXong: () => void
}

export function TheDuyet({ api, phieu, onXong }: Props) {
  const [sua, datSua] = useState<Record<string, string> | null>(null)
  const [giaMoi, datGiaMoi] = useState<number | null>(null)
  const [dangBaoGia, datDangBaoGia] = useState(false)
  const [dangGui, datDangGui] = useState(false)
  const [loi, datLoi] = useState('')
  const [nhip, datNhip] = useState(0)

  // Dem nguoc moi 30 giay. `setInterval` o day an toan: no khong goi mang.
  useEffect(() => {
    const t = window.setInterval(() => datNhip((n) => n + 1), 30_000)
    return () => window.clearInterval(t)
  }, [])

  const phut = useMemo(
    () => phutConLai(phieu.het_han_luc), [phieu.het_han_luc, nhip])
  const hetHan = phut !== null && phut < 0

  const khoaSua = useMemo(() => khoaCoNhan(phieu.doi_so), [phieu.doi_so])
  const daSua = sua !== null

  const dong = useMemo(() => {
    if (!daSua) return doiSoCoNhan(phieu.doi_so)
    return khoaSua.map((k) => [nhanCuaKhoa(k), sua[k] ?? ''] as const)
  }, [daSua, sua, phieu.doi_so, khoaSua])

  const batDauSua = useCallback(() => {
    const o: Record<string, string> = {}
    for (const k of khoaSua) o[k] = String(phieu.doi_so[k] ?? '')
    datSua(o)
    datGiaMoi(null)
    datLoi('')
  }, [khoaSua, phieu.doi_so])

  /** Ghep doi so da sua, giu KIEU cua ban goc cho so. */
  const doiSoDaSua = useCallback((): Record<string, unknown> => {
    const ra: Record<string, unknown> = { ...phieu.doi_so }
    for (const [k, v] of Object.entries(sua ?? {})) {
      ra[k] = typeof phieu.doi_so[k] === 'number' && v.trim() !== ''
        && Number.isFinite(Number(v)) ? Number(v) : v
    }
    return ra
  }, [sua, phieu.doi_so])

  const baoGiaLai = useCallback(() => {
    datLoi('')
    datDangBaoGia(true)
    api.baoGia(phieu.tool_name, doiSoDaSua())
      .then((r) => datGiaMoi(r.credit))
      .catch((e) => datLoi(e instanceof LoiApi ? (e.message || e.code) : 'Không báo giá lại được'))
      .finally(() => datDangBaoGia(false))
  }, [api, phieu.tool_name, doiSoDaSua])

  const quyet = useCallback((qd: 'duyet' | 'tu_choi') => {
    datLoi('')
    datDangGui(true)
    api.duyetQuyet(phieu.approval_id, qd, qd === 'duyet' && daSua ? doiSoDaSua() : undefined)
      .then(() => onXong())
      .catch((e) => {
        // ⭐ 409 = ai do (hoac han) da quyet truoc. Do la mot cau tra loi, khong
        //    phai mot loi cua nguoi bam — noi dung the va tai lai.
        const ma = e instanceof LoiApi ? e.code : ''
        if (ma === 'da_quyet') { onXong(); return }
        datLoi(e instanceof LoiApi ? (e.message || e.code) : 'Không gửi được quyết định')
        datDangGui(false)
      })
  }, [api, phieu.approval_id, daSua, doiSoDaSua, onXong])

  // 🔴 Sua roi ma CHUA bao gia lai thi khong duoc bam Duyet — xem docstring.
  const chuaBaoGiaLai = daSua && giaMoi === null
  const khoaDuyet = hetHan || dangGui || dangBaoGia || chuaBaoGiaLai

  return (
    <section className="ltc-duyet" aria-label="Cần bạn duyệt">
      <header className="ltc-duyet__dau">
        <h3 className="ltc-duyet__tieude">{nhanTool(phieu.tool_name)}</h3>
        <span className="ltc-duyet__han">{cauHetHan(phut)}</span>
      </header>

      <p className="ltc-duyet__hequa">
        {NHAN_HE_QUA[String(phieu.policy_class)] ?? HE_QUA_LA}
      </p>

      {dong.length > 0 && (
        <dl className="ltc-duyet__doiso">
          {daSua
            ? khoaSua.map((k) => (
              <div className="ltc-duyet__dong" key={k}>
                <dt>{nhanCuaKhoa(k)}</dt>
                <dd>
                  <input
                    value={sua[k] ?? ''}
                    aria-label={nhanCuaKhoa(k)}
                    onChange={(e) => {
                      datSua({ ...sua, [k]: e.target.value })
                      // Sua tiep thi gia cu het nghia ngay lap tuc.
                      datGiaMoi(null)
                    }}
                  />
                </dd>
              </div>
            ))
            : dong.map(([nhan, v]) => (
              <div className="ltc-duyet__dong" key={nhan}>
                <dt>{nhan}</dt><dd>{v}</dd>
              </div>
            ))}
        </dl>
      )}

      <p className="ltc-duyet__gia">
        {chuaBaoGiaLai
          ? (
            <>
              {/*
                ⛔ KHONG hien gia cu o day. Doi so da doi nen gia cu khong con
                   mo ta viec sap chay — ve no ra la ve mot con so SAI mot cach
                   tu tin.
              */}
              <span className="ltc-duyet__chuagia">
                Đã sửa — cần báo giá lại trước khi duyệt.
              </span>
              <button type="button" className="ltc-duyet__baogia"
                      disabled={dangBaoGia} onClick={baoGiaLai}>
                {dangBaoGia ? 'Đang tính…' : 'Báo giá lại'}
              </button>
            </>
          )
          : <>Tốn <strong>{giaMoi ?? phieu.credit} credit</strong></>}
      </p>

      {loi && <p className="ltc-duyet__loi" role="alert">{loi}</p>}
      {hetHan && (
        <p className="ltc-duyet__loi" role="alert">
          Phiếu đã hết hạn. Hãy hỏi lại để có báo giá mới.
        </p>
      )}

      <div className="ltc-duyet__nut">
        {/*
          ⭐ "Tu choi" dung TRUOC va cung co chu voi "Duyet". Mot the ma noi
             "khong" kho hon noi "co" la mot the day nguoi ta bam dong y.
        */}
        <button type="button" className="ltc-duyet__tuchoi"
                disabled={dangGui} onClick={() => quyet('tu_choi')}>
          Từ chối
        </button>
        <button type="button" className="ltc-duyet__dongy"
                disabled={khoaDuyet} onClick={() => quyet('duyet')}>
          {dangGui ? 'Đang gửi…' : 'Duyệt'}
        </button>
        {!daSua && !hetHan && khoaSua.length > 0 && (
          <button type="button" className="ltc-duyet__sua" onClick={batDauSua}>
            Sửa
          </button>
        )}
      </div>
    </section>
  )
}
