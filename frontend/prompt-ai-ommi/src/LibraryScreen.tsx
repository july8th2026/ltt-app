/**
 * LibraryScreen.tsx — một component cho cả ba màn thư viện.
 *
 * Prompt Library, Phong cách và Meta Director khác nhau ở nội dung nhưng giống
 * nhau ở thao tác: liệt kê bản riêng, xem mẫu chung, "Dùng mẫu này" để clone,
 * sửa, lưu trữ. Ba bản sao giao diện là ba chỗ để lệch nhau về sau.
 */
import { useCallback, useEffect, useState } from 'react'
import {
  ApiError,
  type LibraryItem,
  type LibraryKind,
  archiveLibraryItem,
  cloneLibraryItem,
  createLibraryItem,
  getLibraryItem,
  listLibrary,
  updateLibraryItem,
} from './ommiApi'

type Copy = {
  title: string
  lead: string
  newLabel: string
  emptyTitle: string
  emptyBody: string
  bodyLabel: string
}

export const LIBRARY_COPY: Record<LibraryKind, Copy> = {
  meta: {
    title: 'Meta Director',
    lead: 'Bộ chỉ dẫn điều khiển cách AI dựng prompt. Mỗi người một bộ riêng.',
    newLabel: '＋ Meta prompt mới',
    emptyTitle: 'Chưa có meta prompt nào',
    emptyBody:
      'Meta prompt quyết định giọng và cấu trúc AI dùng khi phân cảnh. Bắt đầu từ một mẫu có sẵn rồi sửa cho hợp với bạn.',
    bodyLabel: 'Nội dung chỉ dẫn',
  },
  snippet: {
    title: 'Prompt Library',
    lead: 'Đoạn prompt dùng lại, có lịch sử sửa để quay về bản cũ.',
    newLabel: '＋ Đoạn prompt mới',
    emptyTitle: 'Thư viện còn trống',
    emptyBody:
      'Lưu những đoạn mô tả bạn hay dùng lại — ánh sáng, góc máy, hậu kỳ — thay vì gõ lại mỗi lần.',
    bodyLabel: 'Nội dung',
  },
  style: {
    title: 'Phong cách',
    lead: 'Phong cách hình ảnh dùng lại giữa các dự án.',
    newLabel: '＋ Phong cách mới',
    emptyTitle: 'Chưa có phong cách riêng',
    emptyBody:
      'Phong cách gom mô tả thị giác và cả negative prompt vào một chỗ, để mọi cảnh trong dự án nhìn cùng một hệ.',
    bodyLabel: 'Mô tả phong cách',
  },
}

export function LibraryScreen({ kind }: { kind: LibraryKind }) {
  const copy = LIBRARY_COPY[kind]
  const [items, setItems] = useState<LibraryItem[]>([])
  const [catalog, setCatalog] = useState(false)
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState<LibraryItem | null>(null)
  const [busy, setBusy] = useState(false)

  const reload = useCallback(async () => {
    setLoading(true)
    try {
      setItems((await listLibrary(kind, { q: query, catalog })).items)
      setError('')
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : 'Không tải được thư viện.')
    } finally {
      setLoading(false)
    }
  }, [kind, query, catalog])

  useEffect(() => {
    setSelected(null)
    void reload()
  }, [reload])

  const run = async (task: () => Promise<void>) => {
    setBusy(true)
    try {
      await task()
      setError('')
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : 'Thao tác thất bại.')
    } finally {
      setBusy(false)
    }
  }

  const open = (id: string) =>
    run(async () => {
      setSelected(await getLibraryItem(kind, id))
    })

  const add = () =>
    run(async () => {
      const made = await createLibraryItem(kind, { name: 'Mục mới', body: '' })
      await reload()
      setSelected(await getLibraryItem(kind, made.id))
    })

  const save = (fields: { name?: string; body?: string }) =>
    run(async () => {
      if (!selected) return
      await updateLibraryItem(kind, selected.id, fields)
      setSelected(await getLibraryItem(kind, selected.id))
      await reload()
    })

  const useTemplate = (id: string) =>
    run(async () => {
      const copied = await cloneLibraryItem(kind, id)
      // Sau khi clone, chuyển sang danh sách riêng — bản vừa tạo nằm ở đó, và
      // để nguyên tab mẫu thì người dùng tưởng chẳng có gì xảy ra.
      setCatalog(false)
      setSelected(await getLibraryItem(kind, copied.id))
    })

  return (
    <>
      <header className="ommi-head">
        <div>
          <h1>{copy.title}</h1>
          <p>{copy.lead}</p>
        </div>
        <div className="ommi-spacer" />
        <button type="button" className="primary" onClick={add} disabled={busy}>
          {copy.newLabel}
        </button>
      </header>

      <div className="ommi-body">
        {error ? (
          <p className="ommi-error" role="alert">
            {error}
          </p>
        ) : null}

        <div className="ommi-filters">
          <input
            type="search"
            aria-label={`Tìm trong ${copy.title}`}
            placeholder="Tìm theo tên hoặc nội dung…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <button type="button" className="ommi-chip" aria-pressed={!catalog}
            onClick={() => setCatalog(false)}>
            Của tôi
          </button>
          <button type="button" className="ommi-chip" aria-pressed={catalog}
            onClick={() => setCatalog(true)}>
            Mẫu có sẵn
          </button>
        </div>

        {loading ? (
          <p className="ommi-loading">Đang tải…</p>
        ) : items.length === 0 ? (
          <section className="ommi-empty">
            <h2>{catalog ? 'Chưa có mẫu nào' : copy.emptyTitle}</h2>
            <p>
              {catalog
                ? 'Quản trị viên chưa publish mẫu nào cho mục này.'
                : copy.emptyBody}
            </p>
            {catalog ? null : (
              <button type="button" className="primary" onClick={add} disabled={busy}>
                {copy.newLabel}
              </button>
            )}
          </section>
        ) : (
          <div className="ommi-grid">
            {items.map((item) => (
              <button
                key={item.id}
                type="button"
                className="ommi-card"
                aria-selected={selected?.id === item.id}
                onClick={() => void open(item.id)}
              >
                <span className="ommi-card-body">
                  <strong>{item.name}</strong>
                  <span>
                    {item.is_catalog
                      ? 'Mẫu có sẵn · chỉ đọc'
                      : `Bản của tôi${item.version ? ` · v${item.version}` : ''}`}
                  </span>
                </span>
              </button>
            ))}
          </div>
        )}
      </div>

      {selected ? (
        <aside className="ommi-detail" aria-label={`Chi tiết ${selected.name}`}>
          <header>
            <h2>{selected.name}</h2>
            <div className="ommi-spacer" />
            <button type="button" className="ghost" aria-label="Đóng chi tiết"
              onClick={() => setSelected(null)}>
              ×
            </button>
          </header>
          <div className="ommi-detail-body">
            {selected.is_catalog ? (
              /* Mẫu chung chỉ đọc. Hiện ô nhập rồi từ chối lưu là lừa người
                 dùng gõ xong mới báo không được. */
              <>
                <p className="ommi-loading">
                  Đây là mẫu có sẵn, chỉ đọc. Bấm “Dùng mẫu này” để tạo một bản
                  riêng rồi sửa thoải mái.
                </p>
                <label>
                  {copy.bodyLabel}
                  <textarea value={selected.body} readOnly />
                </label>
                <div className="ommi-detail-actions">
                  <button type="button" className="primary" disabled={busy}
                    onClick={() => void useTemplate(selected.id)}>
                    Dùng mẫu này
                  </button>
                </div>
              </>
            ) : (
              <>
                <label>
                  Tên
                  <input
                    type="text"
                    value={selected.name}
                    onChange={(event) =>
                      setSelected({ ...selected, name: event.target.value })
                    }
                    onBlur={(event) => void save({ name: event.target.value })}
                  />
                </label>
                <label>
                  {copy.bodyLabel}
                  <textarea
                    value={selected.body}
                    onChange={(event) =>
                      setSelected({ ...selected, body: event.target.value })
                    }
                    onBlur={(event) => void save({ body: event.target.value })}
                  />
                </label>
                <div className="ommi-detail-actions">
                  <button
                    type="button"
                    className="ghost"
                    disabled={busy}
                    onClick={() =>
                      void run(async () => {
                        await archiveLibraryItem(kind, selected.id, !selected.archived)
                        setSelected(null)
                        await reload()
                      })
                    }
                  >
                    {selected.archived ? 'Bỏ lưu trữ' : 'Lưu trữ'}
                  </button>
                </div>
                {selected.versions?.length ? (
                  <div>
                    <label style={{ marginBottom: 6 }}>Lịch sử sửa</label>
                    <ul className="ommi-history">
                      {selected.versions.map((entry) => (
                        <li key={entry.version}>
                          <b>v{entry.version}</b>
                          <span>{entry.note || 'không ghi chú'}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </>
            )}
          </div>
        </aside>
      ) : null}
    </>
  )
}
