import { useId, useRef } from 'react'
import { useFocusTrap } from '../hooks/useFocusTrap'
import type { KetQuaDiffThietKe } from './diff'
import '../../../styles/designer-diff.css'

type Props = {
  diff: KetQuaDiffThietKe
  apDung: () => void
  huy: () => void
}

const NHAN_TRANG_THAI: Record<KetQuaDiffThietKe['nodes'][number]['trangThai'], string> = {
  them: 'Thêm', xoa: 'Xoá', doi_tham_so: 'Đổi tham số',
}

/** Lớp XEM TRƯỚC cho "Soạn bằng AI" (UI-8b, vá khiếm khuyết B7).
 *
 *  ⭐ Hiển thị thuần từ `diff` đã tính sẵn (`diff.ts`, thuần — dễ kiểm riêng).
 *     Component này chỉ có MỘT việc: vẽ diff ra và chạy đúng một trong hai
 *     hành động `apDung`/`huy` — ⛔ KHÔNG tự gọi `napTaiLieu`/mạng, đó là việc
 *     của `useWorkflowRun`.
 *
 *  ⭐ Trợ năng theo chuẩn UI-10b đã đặt (`CommandPalette.tsx`,
 *     `useFocusTrap.ts`): `role="dialog"` + `aria-labelledby`, bẫy focus, và
 *     — khác `CommandPalette` — `Escape` xử lý NGAY TẠI ĐÂY (`onKeyDown` trên
 *     khung ngoài) thay vì qua `useEditorShortcuts`/`dongHet` toàn cục: lớp
 *     này là dữ liệu CHƯA áp dụng, đóng nó tuyệt đối ⛔ không được chạm
 *     `document`, và giữ hành vi tự trị ở component thì kiểm được ĐỘC LẬP với
 *     `EditorShell`, không cần dựng cả cây trình soạn để viết một bài test. */
export function DesignerDiff(p: Props) {
  const hopThoai = useRef<HTMLElement>(null)
  useFocusTrap(hopThoai)
  const tieuDeId = useId()

  const onKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === 'Escape') { event.preventDefault(); p.huy() }
  }

  const { soNodeThem, soNodeXoa, soNodeDoiThamSo, soEdgeThem, soEdgeXoa } = p.diff
  const tomTatBuoc = `+${soNodeThem} bước, −${soNodeXoa} bước`
    + (soNodeDoiThamSo ? `, ${soNodeDoiThamSo} bước đổi tham số` : '')
  const coCanh = soEdgeThem > 0 || soEdgeXoa > 0

  return <div className="designer-diff-backdrop" role="presentation"
      onMouseDown={event => event.target === event.currentTarget && p.huy()}>
    <section ref={hopThoai} className="designer-diff" role="dialog" aria-modal="true"
        aria-labelledby={tieuDeId} onKeyDown={onKeyDown}>
      <header>
        <h2 id={tieuDeId}>Xem trước thay đổi từ AI</h2>
        <p className="designer-diff-tomtat">{tomTatBuoc}
          {coCanh && ` · +${soEdgeThem} đường nối, −${soEdgeXoa} đường nối`}</p>
      </header>
      {!p.diff.coThayDoi
        ? <p>AI trả lại đúng đồ thị hiện có — không có gì để áp dụng.</p>
        : <ul className="designer-diff-list" aria-label="Các bước thay đổi">
            {p.diff.nodes.map(muc => <li key={muc.id}
                className={`designer-diff-item is-${muc.trangThai}`}>
              <span className="designer-diff-badge">{NHAN_TRANG_THAI[muc.trangThai]}</span>
              <span className="designer-diff-ten">{muc.ten}</span>
            </li>)}
          </ul>}
      <footer>
        <button type="button" onClick={p.huy}>Huỷ</button>
        <button type="button" className="is-primary" onClick={p.apDung}>Áp dụng</button>
      </footer>
    </section>
  </div>
}
