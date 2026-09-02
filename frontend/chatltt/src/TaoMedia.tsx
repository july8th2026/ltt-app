/**
 * TaoMedia.tsx — nut Tao anh / Tao giong, va o XAC NHAN GIA.
 *
 * 🔴 KHONG BAO GIO nop ma khong hoi. Mot luot anh la 3-12 credit, mot luot
 *    tieng tinh theo giay. Nguoi dung phai thay SO TRUOC khi tien roi khoi tai
 *    khoan — va so gui len phai la so ho da nhin (`credit`), de may chu tu choi
 *    neu gia doi giua chung.
 *
 * ⭐ Danh sach giong lay tu `NangLuc.tuy_chon.voice_id` — do la giong CUA CHINH
 *    ho, may chu tra ve qua `ToolSpec.tuy_chon_dong`. Giao dien khong biet
 *    giong nao ton tai; no chi hien thu duoc moi.
 */
import { useState } from 'react'
import type { Api } from './api'
import type { NangLuc } from './kieu'

export type TaoMediaProps = {
  api: Api
  nangLuc: NangLuc[]
  onXong: () => void
  onLoi: (chu: string) => void
}

type Cho = { nang_luc: string; credit: number; tham_so: Record<string, unknown> } | null

export function TaoMedia({ api, nangLuc, onXong, onLoi }: TaoMediaProps) {
  const anh = nangLuc.find((n) => n.phuong_thuc === 'image')
  const tieng = nangLuc.find((n) => n.phuong_thuc === 'audio')
  const [mo, datMo] = useState<'image' | 'audio' | null>(null)
  const [chu, datChu] = useState('')
  const [giong, datGiong] = useState('')
  const [cho, datCho] = useState<Cho>(null)
  const [dangNop, datDangNop] = useState(false)

  const giongCoThe = tieng?.tuy_chon?.voice_id ?? []

  async function hoiGia(ten: string, tham_so: Record<string, unknown>) {
    try {
      const bg = await api.baoGia(ten, tham_so)
      datCho({ nang_luc: ten, credit: bg.credit, tham_so: bg.tham_so })
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
          {mo === 'audio' && giongCoThe.length > 0 && (
            <label className="ltc-media__giong">
              <span>Giọng</span>
              <select value={giong} aria-label="Chọn giọng"
                onChange={(e) => datGiong(e.target.value)}>
                <option value="">Giọng dựng sẵn</option>
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
                ? { prompt: chu.trim() }
                : { text: chu.trim(), ...(giong ? { voice_id: giong } : {}) },
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
