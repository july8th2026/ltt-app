/**
 * BangGhiNho.tsx — nguoi dung XEM, SUA, XOA thu may nho ve minh. (H44 B4 buoc 6)
 *
 * ## Day la ly do B4 ton tai, khong phai mot man hinh phu
 *
 * Ke hoach B4 tu noi: bai toan khong phai *"ghi nho ngu nghia"* (mem0/zep giai
 * bai do bang embedding) ma la **quyen va giao dien** — *"nguoi dung thay va
 * sua duoc"*. Bon buoc truoc dung KHO; buoc nay la thu duy nhat bien no thanh
 * mot loi hua giu duoc.
 *
 * ⛔ Va no la dieu kien **M2** de bat `LTT_CHATLTT_V3_MEMORY`. Bat duong tiem
 *    truoc khi co cho xem/xoa la cho mot kho ghi nho chay ma chu cua no khong
 *    mo ra duoc.
 *
 * ## Ba thu bay ra man hinh, va ca ba deu can
 *
 *   noi dung   thu may nho
 *   pham vi    no anh huong toi luot NAO
 *   nguon      AI viet — nguoi hay may
 *
 * ⭐ `nguon` khong phai trang tri. Mot mau do MAY suy ra co the SAI, va nguoi
 *    dung can biet cai nao la loi minh tu dan, cai nao la suy doan cua may —
 *    hai thu do dang tin khac han nhau.
 *
 * ## Trần hiện TRUOC khi go, khong phai sau khi bi tu choi
 *
 * `KhoDay` tra ve 409. Nhung mot nguoi go xong mot mau roi moi biet kho day la
 * mot nguoi vua mat cong — nen thanh do luon hien, va no doi mau ngay khi con
 * cho hep lai.
 */
import { useCallback, useEffect, useState } from 'react'
import { LoiApi, type Api } from './api'
import type { GhiNho } from './kieu'

const NHAN_PHAM_VI: Record<GhiNho['pham_vi'], string> = {
  nguoi_dung: 'Mọi cuộc trò chuyện',
  du_an: 'Trong một dự án',
  hoi_thoai: 'Chỉ trong một cuộc trò chuyện',
}

const NHAN_NGUON: Record<GhiNho['nguon'], string> = {
  nguoi: 'Bạn tự ghi',
  model: 'Trợ lý tự ghi',
}

/** Thu tu bay: rong truoc, hep sau — cung thu tu backend tiem vao ngu canh. */
const THU_TU: readonly GhiNho['pham_vi'][] = ['nguoi_dung', 'du_an', 'hoi_thoai']

export function BangGhiNho({ api, onDong }: { api: Api; onDong: () => void }) {
  const [ds, datDs] = useState<GhiNho[]>([])
  const [tran, datTran] = useState(0)
  const [tranMotBan, datTranMotBan] = useState(500)
  const [dangTai, datDangTai] = useState(true)
  const [loi, datLoi] = useState('')
  // ⛔ TACH khoi `loi`. Ban dau `bo_qua` dung chung o `loi`, va `tai()`
  //    xoa `loi` ngay sau do — nen cau *"may da nho dieu nay roi"* bien
  //    mat truoc khi ai kip doc. Mot thong bao BINH THUONG va mot loi la
  //    hai thu co vong doi khac nhau; dung chung mot o la mot cai bug cho san.
  const [nhac, datNhac] = useState('')
  const [moi, datMoi] = useState('')
  const [dangSua, datDangSua] = useState<string | null>(null)
  const [chuSua, datChuSua] = useState('')

  const tai = useCallback(async () => {
    datDangTai(true)
    try {
      const r = await api.ghiNhoLietKe()
      datDs(r.ghi_nho)
      datTran(r.tran_moi_pham_vi)
      datTranMotBan(r.tran_mot_ban)
      datLoi('')
      datNhac('')
    } catch (e) {
      // ⛔ Mot bang rong vi LOI trong y het mot bang rong vi CHUA CO GI. Phai
      //    noi ra, khong duoc de nguoi dung ket luan may da quen het.
      datLoi(e instanceof LoiApi ? e.message || e.code : 'Không tải được')
    } finally {
      datDangTai(false)
    }
  }, [api])

  useEffect(() => { void tai() }, [tai])

  const daDung = ds
    .filter((m) => m.pham_vi === 'nguoi_dung')
    .reduce((t, m) => t + m.noi_dung.length, 0)

  async function them(e: React.FormEvent) {
    e.preventDefault()
    const van = moi.trim()
    if (!van) return
    try {
      const r = await api.ghiNhoThem({ noi_dung: van, pham_vi: 'nguoi_dung' })
      datMoi('')
      await tai()
      // ⭐ `bo_qua` (da co san) KHONG phai loi — noi ra bang mot cau, khong bang
      //    mot thong bao do. Va dat SAU `tai()`, vi `tai()` don thong bao.
      datNhac(r.trang_thai === 'bo_qua' ? 'Máy đã nhớ điều này rồi.' : '')
    } catch (e) {
      datLoi(e instanceof LoiApi ? e.message || e.code : 'Không lưu được')
    }
  }

  async function luuSua(id: string) {
    try {
      await api.ghiNhoSua(id, chuSua)
      datDangSua(null)
      await tai()
    } catch (e) {
      datLoi(e instanceof LoiApi ? e.message || e.code : 'Không sửa được')
    }
  }

  async function xoa(id: string) {
    try {
      await api.ghiNhoXoa(id)
      await tai()
    } catch (e) {
      datLoi(e instanceof LoiApi ? e.message || e.code : 'Không xoá được')
    }
  }

  return (
    <section className="ltc-ghinho" aria-label="Ghi nhớ về bạn">
      <header className="ltc-ghinho__dau">
        <h2 className="ltc-ghinho__tieude">Máy nhớ gì về bạn</h2>
        <button type="button" className="ltc-ghinho__dong" onClick={onDong}>
          Đóng
        </button>
      </header>

      <form className="ltc-ghinho__them" onSubmit={them}>
        <label className="ltc-ghinho__nhan" htmlFor="ghinho-moi">
          Dặn máy nhớ một điều
        </label>
        <input
          id="ghinho-moi"
          className="ltc-ghinho__o"
          value={moi}
          maxLength={tranMotBan}
          onChange={(e) => datMoi(e.target.value)}
          placeholder="Ví dụ: tôi làm về kế toán, hãy trả lời ngắn gọn"
        />
        <button type="submit" disabled={!moi.trim()}>Lưu</button>
      </form>

      {/* Trần hiện TRUOC khi go — xem docstring. */}
      {tran > 0 && (
        <p className="ltc-ghinho__tran">
          Đã dùng {daDung}/{tran} ký tự cho phạm vi mọi cuộc trò chuyện.
        </p>
      )}

      {loi && <p className="ltc-ghinho__loi" role="alert">{loi}</p>}
      {nhac && <p className="ltc-ghinho__nhac" role="status">{nhac}</p>}
      {dangTai && <p className="ltc-ghinho__cho">Đang tải…</p>}

      {/*
        🔴 `&& !loi` KHONG phai chi tiet. Mot bang rong vi LOI trong y het mot
           bang rong vi CHUA CO GI, va cau "May chua nho gi ve ban" la mot
           **khang dinh** — no noi rang ta da hoi va cau tra loi la khong co.
           Khi lan hoi ay that bai, khang dinh ay sai, va nguoi dung khong co
           cach nao biet.
      */}
      {!dangTai && !loi && ds.length === 0 && (
        <p className="ltc-ghinho__rong">
          Máy chưa nhớ gì về bạn. Bạn có thể tự dặn ở ô trên.
        </p>
      )}

      {THU_TU.map((pv) => {
        const nhom = ds.filter((m) => m.pham_vi === pv)
        if (!nhom.length) return null
        return (
          <div className="ltc-ghinho__nhom" key={pv}>
            <h3 className="ltc-ghinho__nhomten">{NHAN_PHAM_VI[pv]}</h3>
            <ul className="ltc-ghinho__ds">
              {nhom.map((m) => (
                <li className="ltc-ghinho__mau" key={m.id} data-nguon={m.nguon}>
                  {dangSua === m.id ? (
                    <>
                      <input
                        className="ltc-ghinho__o"
                        value={chuSua}
                        maxLength={tranMotBan}
                        aria-label="Sửa nội dung ghi nhớ"
                        onChange={(e) => datChuSua(e.target.value)}
                      />
                      {/* ⛔ Ba nut "Luu" giong het nhau la ba cau "Luu"
                          giong het nhau voi trinh doc man hinh — cung loi da
                          sua o nut "Xoa". */}
                      <button type="button" aria-label={`Lưu sửa: ${m.noi_dung}`}
                        onClick={() => void luuSua(m.id)}>
                        Lưu
                      </button>
                      <button type="button" aria-label={`Thôi sửa: ${m.noi_dung}`}
                        onClick={() => datDangSua(null)}>
                        Thôi
                      </button>
                    </>
                  ) : (
                    <>
                      <span className="ltc-ghinho__chu">{m.noi_dung}</span>
                      {/* ⭐ Nguoi dung sua duoc CA mau do may ghi — do la loi hua. */}
                      <span className="ltc-ghinho__nguon">{NHAN_NGUON[m.nguon]}</span>
                      <button
                        type="button"
                        aria-label={`Sửa: ${m.noi_dung}`}
                        onClick={() => { datDangSua(m.id); datChuSua(m.noi_dung) }}
                      >
                        Sửa
                      </button>
                      <button
                        type="button"
                        aria-label={`Xoá: ${m.noi_dung}`}
                        onClick={() => void xoa(m.id)}
                      >
                        Xoá
                      </button>
                    </>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )
      })}
    </section>
  )
}
