/**
 * BangNghienCuu.tsx — hoi mot cau, doc mot bao cao CO TRICH DAN. (H44 B6 b5+b6)
 *
 * ## PHAM VI la thu dau tien tren man hinh, khong phai mot dong chan trang
 *
 * §1 cua ke hoach: nen tang nay **khong co kha nang tim web** — do 07/09,
 * khong mot tep nao khai `tavily`/`serper`/`brave`/`searx`. Mot tinh nang ten
 * la *"nghien cuu"* ma im lang ve dieu do la mot loi hua hong: khach hoi mot
 * cau can web, nhan mot cau tra loi tu tin dung tu ba tai lieu ke toan, va
 * khong co gi bao cho ho.
 *
 * ⛔ Nen cau pham vi den TU MAY CHU (`bao_gia.pham_vi`), khong phai mot hang so
 *    o day. Mot ban sao trong bundle la mot ban sao se troi — va no troi ve
 *    phia nguy hiem (bundle cu noi "khong tim Internet" trong khi may chu da mo
 *    `web.tim`).
 *
 * ## Ba con so cua bao cao deu phai hien
 *
 *   so_bi_loai   so cau model viet ra ma KHONG phan giai duoc ve nguon nao
 *   ly_do_dung   cham tran hay da xong
 *   so_vong      chay may vong
 *
 * ⭐ `so_bi_loai` khong phai chi tiet ky thuat. No la thuoc do do tin cua chinh
 *    luot nay: 8 cau bi loai tren 10 nghia la model dang bia va bo kiem trich
 *    dan vua cuu khach mot ban bao cao sai. Giau no di la giau dung thu ho can.
 *
 * ## Hoi lai theo nhip, va nhip DUNG khi tab an
 *
 * Job chay nen. `setTimeout` chu khong `setInterval`: mot lan hoi cham khong
 * duoc phep chong len lan sau — cung ly do `App.tsx` da ghi cho nhip hoi job
 * anh/tieng.
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { LoiApi, type Api } from './api'
import type { BaoCaoNghienCuu, BaoGiaNghienCuu, LyDoDung } from './kieu'

const NHAN_LY_DO: Record<LyDoDung, string> = {
  xong: 'Đã đọc hết tài liệu tìm được',
  tran_vong: 'Dừng ở giới hạn số vòng — có thể còn tài liệu chưa đọc',
  tran_nguon: 'Dừng ở giới hạn số nguồn — có thể còn tài liệu chưa đọc',
  khong_co_nguon: 'Không tìm thấy tài liệu nào khớp câu hỏi',
}

/** Nhịp hỏi lại. 2 giây — cùng nhịp job ảnh/tiếng (Q87). */
const NHIP_MS = 2000

function nhanLoi(e: unknown): string {
  if (e instanceof LoiApi) return e.message || e.code
  return e instanceof Error ? e.message : 'Không chạy được'
}

function DongTrichDan({ td }: { td: { tep_id: string; trang: number } }) {
  // ⛔ `trang === 0` la KHONG BIET, khong phai trang dau. Hien "trang 0" la
  //    hien mot loi cho nguoi doc.
  return (
    <span className="ltc-nc__td">
      {td.tep_id.slice(0, 8)}
      {td.trang > 0 ? ` · trang ${td.trang}` : ''}
    </span>
  )
}

export function BangNghienCuu(
  { api, convId, onDong }: { api: Api; convId: string; onDong: () => void },
) {
  const [bg, datBg] = useState<BaoGiaNghienCuu | null>(null)
  const [cauHoi, datCauHoi] = useState('')
  const [jobId, datJobId] = useState('')
  const [dangChay, datDangChay] = useState(false)
  const [bc, datBc] = useState<BaoCaoNghienCuu | null>(null)
  const [loi, datLoi] = useState('')
  const [phamVi, datPhamVi] = useState('')
  const hen = useRef<number | null>(null)

  useEffect(() => {
    api.nghienCuuBaoGia()
      .then((r) => { datBg(r); datPhamVi(r.pham_vi) })
      .catch((e) => datLoi(nhanLoi(e)))
  }, [api])

  const hoiLai = useCallback((id: string) => {
    api.nghienCuuXem(id).then((r) => {
      if (r.pham_vi) datPhamVi(r.pham_vi)
      if (r.trang_thai === 'done') {
        datBc(r.bao_cao ?? null)
        datDangChay(false)
        return
      }
      if (r.trang_thai === 'failed') {
        // ⭐ Ly do ra man hinh. Mot luot hong im lang la mot luot khach cho mai.
        datLoi(r.ly_do || 'Lượt nghiên cứu không chạy được')
        datDangChay(false)
        return
      }
      hen.current = window.setTimeout(() => hoiLai(id), NHIP_MS)
    }).catch((e) => { datLoi(nhanLoi(e)); datDangChay(false) })
  }, [api])

  useEffect(() => () => {
    if (hen.current !== null) window.clearTimeout(hen.current)
  }, [])

  const chay = useCallback(() => {
    const q = cauHoi.trim()
    if (!q) return
    // ⛔ Xoa loi TRUOC khi goi, khong phai sau: dat `datLoi('')` sau `await`
    //    da hai lan xoa mat mot thong bao vua hien (BangGhiNho, BangDuAn).
    datLoi('')
    datBc(null)
    datDangChay(true)
    api.nghienCuuChay(convId, q)
      .then((r) => {
        datJobId(r.job_id)
        if (r.pham_vi) datPhamVi(r.pham_vi)
        hen.current = window.setTimeout(() => hoiLai(r.job_id), NHIP_MS)
      })
      .catch((e) => { datLoi(nhanLoi(e)); datDangChay(false) })
  }, [api, convId, cauHoi, hoiLai])

  return (
    <section className="ltc-nc" aria-label="Nghiên cứu">
      <header className="ltc-nc__dau">
        <h2 className="ltc-nc__tieude">Nghiên cứu</h2>
        <button type="button" className="ltc-nc__dong" onClick={onDong}>
          Đóng
        </button>
      </header>

      {/*
        🔴 PHAM VI dung day, TRUOC o nhap — khong phai duoi ket qua. Mot cau
           canh bao doc SAU khi da tin la mot cau khong con tac dung.
      */}
      {phamVi && <p className="ltc-nc__phamvi" role="note">{phamVi}</p>}

      {bg && (
        <p className="ltc-nc__gia">
          Ước khoảng <strong>{bg.uoc_credit} credit</strong> cho tối đa{' '}
          {bg.tran_vong} vòng. Số dư của bạn: {bg.so_du} credit.
          {!bg.du_credit && (
            <span className="ltc-nc__thieu"> Chưa đủ để chạy.</span>
          )}
        </p>
      )}

      <label className="ltc-nc__nhap">
        <span>Câu hỏi</span>
        <textarea
          value={cauHoi}
          rows={3}
          disabled={dangChay}
          placeholder="Ví dụ: điều khoản thanh toán trong hợp đồng là gì?"
          onChange={(e) => datCauHoi(e.target.value)}
        />
      </label>

      <button
        type="button"
        className="ltc-nc__chay"
        disabled={dangChay || !cauHoi.trim() || (bg ? !bg.du_credit : false)}
        onClick={chay}
      >
        {dangChay ? 'Đang đọc tài liệu…' : 'Nghiên cứu'}
      </button>

      {loi && <p className="ltc-nc__loi" role="alert">{loi}</p>}
      {dangChay && jobId && (
        <p className="ltc-nc__cho" role="status">
          Đang chạy — có thể mất vài phút.
        </p>
      )}

      {bc && (
        <div className="ltc-nc__bc">
          <p className="ltc-nc__lydo" role="status">
            {NHAN_LY_DO[bc.ly_do_dung]} · {bc.so_vong} vòng
            {/*
              ⭐ `so_bi_loai` la thuoc do DO TIN cua chinh luot nay, khong phai
                 chi tiet ky thuat. Giau no la giau dung thu khach can.
            */}
            {bc.so_bi_loai > 0 && (
              <span className="ltc-nc__loai">
                {' '}· đã bỏ {bc.so_bi_loai} câu không chỉ được nguồn
              </span>
            )}
          </p>

          {bc.khang_dinh.length === 0 ? (
            <p className="ltc-nc__rong">
              Không có câu nào chỉ được về tài liệu của bạn. Thử đính thêm tài
              liệu vào cuộc trò chuyện này, hoặc hỏi hẹp hơn.
            </p>
          ) : (
            <ol className="ltc-nc__ds">
              {bc.khang_dinh.map((k, i) => (
                <li key={`${i}-${k.chu.slice(0, 24)}`}>
                  {k.chu}
                  <span className="ltc-nc__nguon">
                    {k.nguon.map((td) => (
                      <DongTrichDan key={td.doan_id} td={td} />
                    ))}
                  </span>
                </li>
              ))}
            </ol>
          )}
        </div>
      )}
    </section>
  )
}
