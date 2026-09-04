/**
 * TaoMedia.tsx — nut Tao anh / Tao giong, va o XAC NHAN GIA.
 *
 * 🔴 KHONG BAO GIO nop ma khong hoi. Mot luot anh la 3-12 credit, mot luot
 *    tieng tinh theo giay. Nguoi dung phai thay SO TRUOC khi tien roi khoi tai
 *    khoan — va so gui len phai la so ho da nhin (`credit`), de may chu tu choi
 *    neu gia doi giua chung.
 *
 * 🔴 GIONG LAY TU KHO DUNG CHUNG (`tuy_chon.preset`), KHONG theo tai khoan.
 *    Chu du an chot 04/09: *"su dung voice trong kho su dung chung, khong theo
 *    tai khoan ca nhan"*.
 *
 * ⛔ Ban truoc doc `tuy_chon.voice_id` — giong NHAN BAN cua chinh nguoi dung. Hai
 *    hau qua, va ca hai deu do duoc:
 *
 *      · mot tai khoan chua nhan ban giong nao thi danh sach RONG, nen o chon
 *        **khong hien ra**. Do la trang thai cua gan nhu moi khach moi;
 *      · giong nhan ban la **du lieu sinh trac** cua mot con nguoi, va no thuoc
 *        ve app `ltt_voice`. ChatLTT khong phai cho de moi no ra.
 *
 * ⭐ Kho chung co 20 giong gan nhan gioi/vung/phong cach, va `speech.ltt` da
 *    nhan `preset` tu lau. Thu thieu chua bao gio la nang luc — chi la khong ai
 *    moi chung ra man hinh.
 */
import { useEffect, useState } from 'react'
import type { Api } from './api'
import type { NangLuc } from './kieu'

export type TaoMediaProps = {
  api: Api
  nangLuc: NangLuc[]
  onXong: () => void
  onLoi: (chu: string) => void
  /** Van ban do "Doc to" dat vao — mo san o tieng voi noi dung ay. */
  chuDocTo?: string
  onDaNhanChuDocTo?: () => void
}

type Giong = { preset: string; nguon: string; ton_credit: number }
type Cho = { nang_luc: string; credit: number; tham_so: Record<string, unknown>
             giong?: Giong } | null

export function TaoMedia({
  api, nangLuc, onXong, onLoi, chuDocTo, onDaNhanChuDocTo,
}: TaoMediaProps) {
  const anh = nangLuc.find((n) => n.phuong_thuc === 'image')
  const tieng = nangLuc.find((n) => n.phuong_thuc === 'audio')
  const [mo, datMo] = useState<'image' | 'audio' | null>(null)
  const [chu, datChu] = useState('')
  const [giong, datGiong] = useState('')
  // Anh THAM CHIEU cho `mode=edit`. Khac han anh dinh kem cua o soan chat: cai
  // kia la NGU CANH cho model doc, cai nay la DAU VAO cua mot lan tao anh.
  const [thamChieu, datThamChieu] = useState<{ key: string; ten: string }[]>([])
  const [dangTai, datDangTai] = useState(false)
  const [cho, datCho] = useState<Cho>(null)
  const [dangNop, datDangNop] = useState(false)

  const giongCoThe = tieng?.tuy_chon?.preset ?? []

  // "Doc to" tren mot cau tra loi: mo san o tieng, dien san van ban. Nguoi dung
  // VAN phai bam "Xem gia" roi "Dong y" — mot lan doc to la mot lan tra tien.
  useEffect(() => {
    if (!chuDocTo) return
    datMo('audio')
    datChu(chuDocTo)
    datCho(null)
    onDaNhanChuDocTo?.()
  }, [chuDocTo, onDaNhanChuDocTo])

  async function themThamChieu(ds: FileList | null) {
    if (!ds || !ds.length) return
    datDangTai(true)
    try {
      for (const tep of Array.from(ds).slice(0, 2 - thamChieu.length)) {
        // ⛔ Tung tep mot, va bat loi RIENG tung tep. Mot tep hong khong duoc
        //    giet ca lo — cung bai hoc da chot o `4.1` cua bo kiem giao dien.
        try {
          const kq = await api.taiAnh(tep)
          datThamChieu((cu2) => [...cu2, { key: kq.key, ten: tep.name }])
        } catch (e) {
          onLoi(`Không tải được ${tep.name}: `
            + (e instanceof Error ? e.message : 'lỗi không rõ'))
        }
      }
    } finally {
      datDangTai(false)
    }
  }

  async function hoiGia(ten: string, tham_so: Record<string, unknown>) {
    try {
      const bg = await api.baoGia(ten, tham_so)
      datCho({ nang_luc: ten, credit: bg.credit, tham_so: bg.tham_so, giong: bg.giong })
    } catch (e) {
      onLoi(e instanceof Error ? e.message : 'Không báo giá được.')
    }
  }

  async function xacNhan() {
    if (!cho) return
    datDangNop(true)
    try {
      await api.taoMedia(cho.nang_luc, cho.tham_so, cho.credit)
      datCho(null)
      datMo(null)
      datChu('')
      datThamChieu([])
      onXong()
    } catch (e) {
      onLoi(e instanceof Error ? e.message : 'Không tạo được.')
    } finally {
      datDangNop(false)
    }
  }

  const tat = (n?: NangLuc) => n?.san_sang !== 'san_sang'

  return (
    <div className="ltc-media">
      <button
        type="button"
        className="ltc-nut--nho"
        disabled={!anh || tat(anh)}
        title={tat(anh) ? 'Model ảnh chưa sẵn sàng' : undefined}
        onClick={() => { datMo(mo === 'image' ? null : 'image'); datCho(null) }}
      >
        Tạo ảnh
      </button>
      <button
        type="button"
        className="ltc-nut--nho"
        disabled={!tieng || tat(tieng)}
        title={tat(tieng) ? 'Model giọng nói chưa sẵn sàng' : undefined}
        onClick={() => { datMo(mo === 'audio' ? null : 'audio'); datCho(null) }}
      >
        Tạo giọng
      </button>
      {tieng && (
        <a className="ltc-lien" href={tieng.duong_dan_app}>
          Quản lý giọng của tôi ↗
        </a>
      )}

      {mo && !cho && (
        <div className="ltc-media__o">
          <textarea
            rows={2}
            aria-label={mo === 'image' ? 'Mô tả ảnh' : 'Văn bản cần đọc'}
            placeholder={mo === 'image' ? 'Mô tả ảnh muốn tạo…' : 'Văn bản cần đọc…'}
            value={chu}
            onChange={(e) => datChu(e.target.value)}
          />
          {mo === 'image' && (
            <div className="ltc-media__ref">
              <label className="ltc-nut--nho">
                {dangTai ? 'Đang tải…' : '+ Ảnh tham chiếu'}
                <input
                  type="file" accept="image/png,image/jpeg,image/webp" multiple
                  aria-label="Ảnh tham chiếu"
                  style={{ display: 'none' }}
                  disabled={dangTai || thamChieu.length >= 2}
                  onChange={(e) => { void themThamChieu(e.target.files); e.target.value = '' }}
                />
              </label>
              {thamChieu.map((a, i) => (
                <span key={a.key} className="ltc-chip">
                  {a.ten}
                  <button type="button" aria-label={`Bỏ ${a.ten}`}
                    onClick={() => datThamChieu((cu2) => cu2.filter((_, j) => j !== i))}>
                    ×
                  </button>
                </span>
              ))}
            </div>
          )}
          {mo === 'audio' && giongCoThe.length > 0 && (
            <label className="ltc-media__giong">
              <span>Giọng</span>
              <select value={giong} aria-label="Chọn giọng"
                onChange={(e) => datGiong(e.target.value)}>
                <option value="">Để model tự chọn theo nội dung</option>
                {giongCoThe.map((g) => (
                  <option key={g.value} value={g.value}>{g.label}</option>
                ))}
              </select>
            </label>
          )}
          <button
            type="button"
            className="ltc-nut--nho"
            disabled={!chu.trim()}
            onClick={() => hoiGia(
              mo === 'image' ? (anh?.ten ?? '') : (tieng?.ten ?? ''),
              mo === 'image'
                // ⭐ Co anh tham chieu ⇒ `edit`; khong co ⇒ `t2i`. Khong de
                //    nguoi dung tu chon che do: `anhnoibo` TU CHOI `t2i` kem
                //    anh va tu choi `edit` khong anh, nen mot o chon che do chi
                //    tao ra mot cach bam sai.
                ? (thamChieu.length
                  ? { prompt: chu.trim(), mode: 'edit',
                      image_keys: thamChieu.map((a) => a.key) }
                  : { prompt: chu.trim(), mode: 't2i' })
                // ⛔ `preset` (kho chung), KHONG `voice_id` (giong nhan ban).
                //    Bo trong ⇒ may chu de model tu chon theo noi dung.
                : { text: chu.trim(), ...(giong ? { preset: giong } : {}) },
            )}
          >
            Xem giá
          </button>
        </div>
      )}

      {cho && (
        <div className="ltc-media__gia" role="group" aria-label="Xác nhận giá">
          <span>
            Lượt này tốn <strong>{cho.credit}</strong> credit.
            {cho.giong && (
              <>
                {' '}Giọng <strong>{cho.giong.preset}</strong>
                {cho.giong.nguon === 'model' && ' (model chọn theo nội dung)'}
                {cho.giong.nguon === 'nho' && ' (như lượt trước)'}
                {cho.giong.ton_credit > 0
                  && ` — chọn giọng tốn thêm ${cho.giong.ton_credit} credit.`}
              </>
            )}
          </span>
          <button type="button" className="ltc-nut" disabled={dangNop} onClick={xacNhan}>
            {dangNop ? 'Đang gửi…' : 'Đồng ý, tạo'}
          </button>
          <button type="button" className="ltc-nut--nho" onClick={() => datCho(null)}>
            Huỷ
          </button>
        </div>
      )}
    </div>
  )
}
