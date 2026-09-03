/**
 * ThongDiepView.tsx — mot luot noi: chu, suy luan, trang thai, chuyen nhanh.
 *
 * 🔴 XSS. `react-markdown` v10 **escape raw HTML thanh chu** khi khong bat
 *    `rehype-raw` — va ta khong bat. Day dung la mo hinh cua LibreChat: kiem o
 *    Phase 01 §12, `DOMPurify` **khong** nam trong duong render chat cua ho,
 *    an toan den tu viec khong bat plugin do (`splitMarkdown.ts:122`).
 *
 * ⛔ Nen: dung them `rehype-raw` la mo lai ca lop lo hong ay. Neu ngay nao can
 *    HTML tho thi phai co DOMPurify TRUOC no, khong phai thay vi no.
 *
 * ⭐ Khoi suy luan: `aria-expanded` + `aria-controls` tro dung id vung noi dung,
 *    nhan doi "Dang suy nghi" ↔ "Suy luan" khi xong (AC-13, muon tu
 *    `Parts/Reasoning.tsx:83-87,104-117`).
 */
import { useId, useState } from 'react'
import Markdown from 'react-markdown'
import remarkBreaks from 'remark-breaks'
import remarkGfm from 'remark-gfm'
import { anhEm, chuCuaThongDiep, suyLuanCuaThongDiep } from './cay'
import type { Khoi, ThongDiep } from './kieu'
import { TrangThaiLuot } from './TrangThaiLuot'

const NHAN_TRANG_THAI: Record<string, string> = {
  cancelled: 'Đã dừng',
  length: 'Bị cắt ở trần độ dài',
}

function KhoiSuyLuan({ chu, dangChay }: { chu: string; dangChay: boolean }) {
  const [mo, datMo] = useState(false)
  const id = useId()
  if (!chu.trim()) return null
  return (
    <div className="ltc-suyluan">
      <button
        type="button"
        className="ltc-suyluan__nut"
        aria-expanded={mo}
        aria-controls={id}
        onClick={() => datMo((x) => !x)}
      >
        <span aria-hidden="true">{mo ? '▾' : '▸'}</span>{' '}
        {dangChay ? 'Đang suy nghĩ…' : 'Suy luận'}
      </button>
      <div id={id} role="group" aria-label="Suy luận" hidden={!mo}>
        <pre className="ltc-suyluan__chu">{chu}</pre>
      </div>
    </div>
  )
}

/**
 * Khoi tai san. `duongTaiSan` di qua cua CO KIEM SO HUU cua app, khong phai
 * `/static` — anh cua khach khong bao gio la tep tinh cong khai.
 */
function KhoiTaiSan({ khoi, duongTaiSan, cuaNguoiDung }: {
  khoi: Khoi[]; duongTaiSan: (k: string) => string; cuaNguoiDung?: boolean
}) {
  const media = khoi.filter((k) => k.type === 'image' || k.type === 'audio')
  if (!media.length) return null
  return (
    <div className="ltc-taisan">
      {media.map((k, i) => (k.type === 'image' ? (
        <a key={i} href={duongTaiSan(String(k.key))} target="_blank" rel="noreferrer">
          {/*
            ⛔ `alt` phai noi dung AI tao ra anh. Ban dau dung mot chuoi cho ca
               hai chieu ("Anh N do ChatLTT tao"), va hau qua chi lo ra khi
               nghe: nguoi dung dinh ANH CUA CHINH HO va trinh doc man hinh
               doc "Anh 1 do ChatLTT tao". Mot cau sai, noi rat tu tin, va chi
               nhung nguoi phu thuoc vao no moi nghe thay.
          */}
          <img className="ltc-taisan__anh" src={duongTaiSan(String(k.key))}
            alt={cuaNguoiDung ? `Ảnh ${i + 1} bạn đã gửi`
                              : `Ảnh ${i + 1} do ChatLTT tạo`} loading="lazy" />
        </a>
      ) : (
        <audio key={i} className="ltc-taisan__am" controls preload="none"
          src={duongTaiSan(String(k.key))}>
          Trình duyệt không phát được tệp âm thanh này.
        </audio>
      )))}
    </div>
  )
}

export type ThongDiepViewProps = {
  m: ThongDiep
  phang: readonly ThongDiep[]
  onChuyenNhanh: (m: ThongDiep, idx: number) => void
  onTaoLai: (m: ThongDiep) => void
  onSuaGuiLai: (m: ThongDiep) => void
  duongTaiSan?: (k: string) => string
  /** Doc to chinh cau tra loi nay. Vang mat = nang luc tieng khong san sang. */
  onDocTo?: (m: ThongDiep, chu: string) => void
}

export function ThongDiepView({
  m, phang, onChuyenNhanh, onTaoLai, onSuaGuiLai, duongTaiSan, onDocTo,
}: ThongDiepViewProps) {
  const ds = anhEm(phang, m)
  const idx = ds.findIndex((x) => x.id === m.id)
  const dangChay = m.status === 'streaming' || m.status === 'queued'
  const chu = chuCuaThongDiep(m)
  const suyLuan = suyLuanCuaThongDiep(m)
  const loi = m.blocks.find((k) => k.type === 'error')
  const trangThai = m.blocks.find((k) => k.type === 'status')
  const dangTaoMedia = dangChay && m.execution?.mode === 'job'
  const tienDo = (m.execution?.usage as { progress?: number } | undefined)?.progress ?? null

  return (
    <article
      className={`ltc-tin ltc-tin--${m.role}`}
      data-trang-thai={m.status}
      aria-label={`${m.role === 'user' ? 'Bạn' : 'ChatLTT'} nói`}
    >
      <div className="ltc-tin__vai" aria-hidden="true">
        {m.role === 'user' ? 'Bạn' : 'ChatLTT'}
      </div>

      {m.role === 'assistant' && (
        <KhoiSuyLuan chu={suyLuan} dangChay={dangChay} />
      )}

      {/*
        🔴 `remarkBreaks` KHONG PHAI mot lua chon tham my. Do 03/09 tren
           PRODUCTION: hoi "liet ke 3 mau, moi mau mot dong" thi model tra ve
           dung ba dong, va giao dien ve ra MOT doan lien "Do Xanh duong Vang"
           — mot `<p>`, khong mot `<br>` nao.

           Nguyen nhan la CommonMark: mot xuong dong DON la soft break, hien
           thi thanh dau CACH. Dung theo dac ta, va sai theo ky vong cua moi
           nguoi dung mot san pham chat.

        ⛔ Va no khong hiem. Model xuong dong don o khap noi: danh sach khong
           gach dau dong, dia chi, tho, cac buoc lam theo thu tu. Tat ca deu
           dinh thanh mot doan chay dai.

        ⭐ Day cung la cach LibreChat lam. `remark-breaks` CHI doi soft break
           thanh `<br>`; no khong bat HTML tho, nen mo hinh chong XSS o dau tep
           nay khong doi mot chut nao. `test_ThongDiepView` chot ca hai ve.
      */}
      <div className="ltc-tin__chu">
        {m.role === 'user' ? (
          <p className="ltc-tin__tho">{chu}</p>
        ) : (
          <Markdown remarkPlugins={[remarkGfm, remarkBreaks]}>{chu}</Markdown>
        )}
        {/*
          ⛔ Thay cho mot cham nhip cam. Mot cham tra loi duoc "con song khong";
             no khong tra loi duoc "dang lam gi" — va do moi la cau nguoi dung
             thuc su hoi sau ba giay im lang. Xem `TrangThaiLuot.tsx`.
        */}
        {!dangTaoMedia && (
          <TrangThaiLuot ex={m.execution} daCoChu={!!chu} dangChay={dangChay} />
        )}
      </div>

      {dangTaoMedia && (
        <p className="ltc-tin__nhan" role="status">
          Đang tạo… {tienDo != null ? `${tienDo}%` : ''}
        </p>
      )}
      {duongTaiSan && <KhoiTaiSan khoi={m.blocks} duongTaiSan={duongTaiSan}
        cuaNguoiDung={m.role === 'user'} />}

      {loi && (
        <p className="ltc-tin__loi" role="alert">
          {String(loi.text || loi.code || 'Có lỗi xảy ra.')}
        </p>
      )}
      {trangThai && (
        <p className="ltc-tin__nhan">
          {NHAN_TRANG_THAI[String(trangThai.code)] ?? String(trangThai.code)}
        </p>
      )}

      <div className="ltc-tin__thanhcong">
        {ds.length > 1 && (
          <nav className="ltc-nhanh" aria-label="Chuyển nhánh">
            <button
              type="button"
              aria-label="Nhánh trước"
              disabled={idx <= 0}
              onClick={() => onChuyenNhanh(m, idx - 1)}
            >
              ‹
            </button>
            <span role="status" aria-live="polite" aria-atomic="true">
              {idx + 1} / {ds.length}
            </span>
            <button
              type="button"
              aria-label="Nhánh sau"
              disabled={idx >= ds.length - 1}
              onClick={() => onChuyenNhanh(m, idx + 1)}
            >
              ›
            </button>
          </nav>
        )}
        {m.role === 'assistant' && !dangChay && m.execution?.mode !== 'job' && (
          <button type="button" className="ltc-nut--nho" onClick={() => onTaoLai(m)}>
            Tạo lại
          </button>
        )}
        {/* Doc to CHINH cau tra loi nay — khac nut "Tao giong" o thanh chung,
            von bat nguoi dung go lai van ban. Van phai qua o xac nhan gia. */}
        {m.role === 'assistant' && !dangChay && onDocTo && chu.trim() && (
          <button type="button" className="ltc-nut--nho"
            onClick={() => onDocTo(m, chu)}>
            Đọc to
          </button>
        )}
        {m.role === 'user' && (
          <button type="button" className="ltc-nut--nho" onClick={() => onSuaGuiLai(m)}>
            Sửa và gửi lại
          </button>
        )}
      </div>
    </article>
  )
}
