/**
 * BangDuAn.tsx — xem, tao, doi ten, xoa du an. (H44 B5 buoc 6)
 *
 * ## 🔴 Cau khang dinh nguy hiem nhat cua man hinh nay la nut XOA
 *
 * Nguoi dung nghi minh dang don mot cai NHAN. Neu thao tac ay dot luon noi
 * dung thi khong co cach nao lay lai, va ho chi phat hien SAU KHI da bam.
 *
 * ⇒ Nut xoa noi thang so hoi thoai se **o lai**, ngay tren nut. Khong phai mot
 *   hop thoai "ban co chac khong" — mot cau hoi chung chung khong noi duoc
 *   dieu gi se xay ra, va nguoi ta bam Yes theo phan xa.
 *
 * ## Khoa lac quan di RA giao dien, khong bi giau
 *
 * `revision` cua loi di kem moi hang va duoc gui lai nguyen ven khi doi ten.
 * Hai tab sua cung luc thi tab thu hai nhan **409**, va man hinh noi ra roi
 * tai lai — thay vi ghi de im lang.
 *
 * ## Bang rong vi LOI khac bang rong vi CHUA CO GI
 *
 * Cung bai hoc da tra gia o `BangGhiNho`: cau *"Chua co du an nao"* la mot
 * **khang dinh** — no noi ta DA hoi va cau tra loi la khong co. Khi lan hoi
 * that bai, khang dinh ay sai.
 */
import { useCallback, useEffect, useState } from 'react'
import { LoiApi, type Api } from './api'
import type { DuAn } from './kieu'

export function BangDuAn({ api, onDong, onChon }: {
  api: Api
  onDong: () => void
  /** Mo mot du an ra xem. Vang mat = bang chi de quan ly. */
  onChon?: (d: DuAn) => void
}) {
  const [ds, datDs] = useState<DuAn[]>([])
  const [dangTai, datDangTai] = useState(true)
  const [loi, datLoi] = useState('')
  const [moi, datMoi] = useState('')
  const [dangSua, datDangSua] = useState<string | null>(null)
  const [chuSua, datChuSua] = useState('')
  const [soHoiThoai, datSoHoiThoai] = useState<Record<string, number>>({})

  const tai = useCallback(async () => {
    datDangTai(true)
    try {
      const r = await api.duAnLietKe()
      datDs(r.du_an)
      datLoi('')
    } catch (e) {
      datLoi(e instanceof LoiApi ? e.message || e.code : 'Không tải được')
    } finally {
      datDangTai(false)
    }
  }, [api])

  useEffect(() => { void tai() }, [tai])

  async function tao(e: React.FormEvent) {
    e.preventDefault()
    const ten = moi.trim()
    if (!ten) return
    try {
      await api.duAnTao(ten)
      datMoi('')
      await tai()
    } catch (e) {
      datLoi(e instanceof LoiApi ? e.message || e.code : 'Không tạo được')
    }
  }

  async function luuSua(d: DuAn) {
    try {
      await api.duAnDoiTen(d.id, chuSua, d.revision)
      datDangSua(null)
      await tai()
    } catch (e) {
      // ⭐ 409 la mot cau khac han 400: co nguoi sua truoc, khong phai ban go sai.
      if (e instanceof LoiApi && e.status === 409) {
        datDangSua(null)
        // ⛔ `tai()` don `loi` khi no thanh cong, nen dat cau nay SAU no. Toi da
        //    mac dung loi nay o `BangGhiNho` (buoc 6 cua B4) va mac lai o day
        //    mot man hinh sau — hai lan, cung mot hinh dang: mot thong bao dat
        //    TRUOC mot lan tai lai la mot thong bao khong ai kip doc.
        await tai()
        datLoi('Dự án này vừa được sửa ở nơi khác. Đã tải lại danh sách.')
        return
      }
      datLoi(e instanceof LoiApi ? e.message || e.code : 'Không sửa được')
    }
  }

  /** Xoá theo **HAI NHỊP**: nhịp một hỏi số hội thoại và nói ra, nhịp hai xoá.
   *
   * ⚠️ Bản đầu gắn con số vào `onMouseEnter`/`onFocus`. Kiểm trên trình duyệt
   *    thật thì lộ ra hai điều: cử chỉ ấy khó kích hoạt, và — quan trọng hơn —
   *    **người dùng cảm ứng không bao giờ hover**. Cảnh báo quan trọng nhất của
   *    màn hình này lại nằm sau một cử chỉ mà một nửa số người không có.
   *
   * ⭐ Hai nhịp bấm thì ai cũng đi qua được, và nó nói **điều gì sẽ xảy ra** —
   *    khác hẳn một hộp thoại *"bạn có chắc không"*, thứ không nói được gì và
   *    người ta bấm Yes theo phản xạ.
   *
   * ⛔ Vẫn KHÔNG đếm sẵn cho cả danh sách: một bộ đếm bày ở mọi hàng là thứ sẽ
   *    đẻ ra một cột phi chuẩn hoá để cho nhanh — đúng thứ `services/du_an.py`
   *    cố ý không có. Con số chỉ cần đúng **một** lúc: lúc sắp xoá.
   */
  async function xoa(d: DuAn) {
    if (soHoiThoai[d.id] === undefined) {
      try {
        const r = await api.duAnHoiThoai(d.id)
        datSoHoiThoai((x) => ({ ...x, [d.id]: r.hoi_thoai.length }))
      } catch {
        // Khong dem duoc thi van cho xoa — mot con so khong doc duoc khong
        // duoc lam hong ca thao tac. Danh dau bang -1 de nhip hai di tiep.
        datSoHoiThoai((x) => ({ ...x, [d.id]: -1 }))
      }
      return
    }
    try {
      await api.duAnXoa(d.id)
      datSoHoiThoai((x) => { const y = { ...x }; delete y[d.id]; return y })
      await tai()
    } catch (e) {
      datLoi(e instanceof LoiApi ? e.message || e.code : 'Không xoá được')
    }
  }

  function nhanXoa(d: DuAn): string {
    const n = soHoiThoai[d.id]
    if (n === undefined) return `Xoá dự án: ${d.ten}`
    if (n < 0) return `Bấm lần nữa để xoá dự án: ${d.ten}`
    return `Bấm lần nữa để xoá dự án: ${d.ten} — ${n} cuộc trò chuyện sẽ ở lại`
  }

  return (
    <section className="ltc-duan" aria-label="Dự án">
      <header className="ltc-duan__dau">
        <h2 className="ltc-duan__tieude">Dự án</h2>
        <button type="button" className="ltc-duan__dong" onClick={onDong}>
          Đóng
        </button>
      </header>

      <form className="ltc-duan__them" onSubmit={tao}>
        <label className="ltc-duan__nhan" htmlFor="duan-moi">Tên dự án mới</label>
        <input
          id="duan-moi"
          className="ltc-duan__o"
          value={moi}
          maxLength={160}
          onChange={(e) => datMoi(e.target.value)}
          placeholder="Ví dụ: Quyết toán thuế 2026"
        />
        <button type="submit" disabled={!moi.trim()}>Tạo</button>
      </form>

      {loi && <p className="ltc-duan__loi" role="alert">{loi}</p>}
      {dangTai && <p className="ltc-duan__cho">Đang tải…</p>}

      {!dangTai && !loi && ds.length === 0 && (
        <p className="ltc-duan__rong">
          Chưa có dự án nào. Dự án gom các cuộc trò chuyện liên quan lại một chỗ.
        </p>
      )}

      <ul className="ltc-duan__ds">
        {ds.map((d) => (
          <li className="ltc-duan__muc" key={d.id}>
            {dangSua === d.id ? (
              <>
                <input
                  className="ltc-duan__o"
                  value={chuSua}
                  maxLength={160}
                  aria-label="Sửa tên dự án"
                  onChange={(e) => datChuSua(e.target.value)}
                />
                <button type="button" aria-label={`Lưu tên: ${d.ten}`}
                  onClick={() => void luuSua(d)}>Lưu</button>
                <button type="button" aria-label={`Thôi sửa: ${d.ten}`}
                  onClick={() => datDangSua(null)}>Thôi</button>
              </>
            ) : (
              <>
                <button
                  type="button"
                  className="ltc-duan__ten"
                  aria-label={`Mở dự án: ${d.ten}`}
                  onClick={() => onChon?.(d)}
                >
                  {d.ten}
                </button>
                <button type="button" aria-label={`Đổi tên: ${d.ten}`}
                  onClick={() => { datDangSua(d.id); datChuSua(d.ten) }}>
                  Đổi tên
                </button>
                {/*
                  🔴 Nut xoa noi thang dieu gi se xay ra. Mot hop thoai "ban co
                     chac khong" khong noi duoc dieu do, va nguoi ta bam Yes
                     theo phan xa.
                */}
                <button
                  type="button"
                  aria-label={nhanXoa(d)}
                  data-nhip={soHoiThoai[d.id] === undefined ? '1' : '2'}
                  onClick={() => void xoa(d)}
                >
                  {soHoiThoai[d.id] === undefined ? 'Xoá' : 'Xoá thật'}
                </button>
                {soHoiThoai[d.id] !== undefined && soHoiThoai[d.id] >= 0 && (
                  <span className="ltc-duan__ghi">
                    {soHoiThoai[d.id]} cuộc trò chuyện sẽ ở lại
                  </span>
                )}
              </>
            )}
          </li>
        ))}
      </ul>
    </section>
  )
}
