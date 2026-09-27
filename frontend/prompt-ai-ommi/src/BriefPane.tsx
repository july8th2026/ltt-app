/**
 * BriefPane.tsx — cột trái của Studio Kịch bản (Q-3, spec §6.4).
 *
 * Danh sách Brief, tìm theo tên, tạo mới, nhân bản. Tự quản lý việc tải danh
 * sách — cột phải (`StudioShell`) chỉ cần biết brief nào đang được chọn qua
 * `selectedId`/`onSelect`, giống cách `LibraryScreen` tách danh sách khỏi chi
 * tiết để hai bên không giẫm lên trạng thái của nhau.
 *
 * ⚠️ Nhân bản đặt `free_iterations_used` về 0 ở backend (`services/briefs.py::nhan_ban`)
 * — đây là brief MỚI, không phải bản sao dùng chung bộ đếm miễn phí.
 */
import { useCallback, useEffect, useState } from 'react'
import { ApiError, type Brief, cloneBrief, createBrief, listBriefs } from './ommiApi'

export function BriefPane({
  selectedId,
  onSelect,
  reloadToken,
}: {
  selectedId: string
  onSelect: (id: string) => void
  reloadToken: number
}) {
  const [briefs, setBriefs] = useState<Brief[]>([])
  const [query, setQuery] = useState('')
  const [archived, setArchived] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const reload = useCallback(async () => {
    setLoading(true)
    try {
      setBriefs((await listBriefs({ q: query, archived })).briefs)
      setError('')
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : 'Không tải được danh sách brief.')
    } finally {
      setLoading(false)
    }
  }, [query, archived])

  useEffect(() => {
    void reload()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reload, reloadToken])

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

  const create = () =>
    run(async () => {
      const made = await createBrief({ title: 'Kịch bản mới' })
      await reload()
      onSelect(made.brief.id)
    })

  const clone = (id: string) =>
    run(async () => {
      const made = await cloneBrief(id)
      await reload()
      onSelect(made.brief.id)
    })

  return (
    <aside
      className="ommi-brief-pane"
      aria-label="Danh sách brief"
      style={{ overflowY: 'auto', minHeight: 0, borderRight: '1px solid var(--border-subtle)', padding: '16px 14px' }}
    >
      <header className="ommi-head">
        <div>
          <h1>Kịch bản</h1>
          <p>Chọn một brief để soạn, hoặc tạo brief mới.</p>
        </div>
      </header>

      <div className="ommi-filters">
        <input
          type="search"
          aria-label="Tìm brief"
          placeholder="Tìm theo tên…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <button type="button" className="ommi-chip" aria-pressed={!archived} onClick={() => setArchived(false)}>
          Đang soạn
        </button>
        <button type="button" className="ommi-chip" aria-pressed={archived} onClick={() => setArchived(true)}>
          Lưu trữ
        </button>
      </div>

      <button type="button" className="primary" onClick={create} disabled={busy} style={{ margin: '0 0 10px' }}>
        ＋ Brief mới
      </button>

      {error ? (
        <p className="ommi-error" role="alert">
          {error}
        </p>
      ) : null}

      {loading ? (
        <p className="ommi-loading">Đang tải…</p>
      ) : briefs.length === 0 ? (
        <section className="ommi-empty">
          <h2>{archived ? 'Chưa lưu trữ brief nào' : 'Chưa có brief nào'}</h2>
          <p>Tạo một brief để bắt đầu soạn kịch bản.</p>
        </section>
      ) : (
        <ul className="ommi-history" aria-label="Brief">
          {briefs.map((brief) => (
            <li key={brief.id}>
              <button
                type="button"
                className="ommi-card"
                aria-selected={selectedId === brief.id}
                aria-current={selectedId === brief.id ? 'true' : undefined}
                onClick={() => onSelect(brief.id)}
                style={{ flex: 1, textAlign: 'left' }}
              >
                <span className="ommi-card-body">
                  <strong>{brief.title || 'Chưa đặt tên'}</strong>
                  <span>
                    {brief.target_scenes} cảnh · {brief.status}
                  </span>
                </span>
              </button>
              <button
                type="button"
                className="ghost"
                disabled={busy}
                onClick={() => void clone(brief.id)}
                aria-label={`Nhân bản ${brief.title}`}
              >
                Nhân bản
              </button>
            </li>
          ))}
        </ul>
      )}
    </aside>
  )
}
