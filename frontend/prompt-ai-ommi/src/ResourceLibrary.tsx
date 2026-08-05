/**
 * ResourceLibrary.tsx — Kho tài nguyên riêng của từng người dùng.
 *
 * Đây là màn hình mà bản OMMI trước chỉ có đúng một nút `＋ Tài nguyên mô tả`
 * cho phép gõ text. Kho thật cần: lưới ảnh, lọc theo nhóm, tìm kiếm, phân
 * trang, nhiều ảnh biến thể cho mỗi tài nguyên, và sinh ảnh bằng AI.
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import {
  ApiError,
  KIND_LABEL,
  RESOURCE_KINDS,
  type Quote,
  type Resource,
  type ResourcePage,
  type StartedJob,
  type Variant,
  archiveResource,
  attachJobImages,
  createResource,
  deleteImage,
  generateImage,
  getResource,
  imageUrl,
  jobStatus,
  listResources,
  updateResource,
  uploadImage,
} from './ommiApi'

const PAGE_SIZE = 40

/** Ảnh dùng URL có hạn, nên phải lấy theo yêu cầu chứ không lưu sẵn. */
function useImageSrc(resourceId: string, variantId: string): string {
  const [src, setSrc] = useState('')
  useEffect(() => {
    let alive = true
    if (!resourceId || !variantId) return
    imageUrl(resourceId, variantId)
      .then((body) => {
        if (!alive) return
        setSrc(body.url ?? '')
      })
      .catch(() => {
        /* ảnh hỏng không được làm sập cả kho */
      })
    return () => {
      alive = false
    }
  }, [resourceId, variantId])
  return src
}

function Thumb({ resource }: { resource: Resource }) {
  const src = useImageSrc(resource.id, resource.cover_variant_id)
  if (!src) return <div className="ommi-thumb">▨</div>
  return (
    <div className="ommi-thumb">
      <img src={src} alt="" loading="lazy" />
    </div>
  )
}

function VariantTile({
  resourceId,
  variant,
  onRemove,
}: {
  resourceId: string
  variant: Variant
  onRemove: (id: string) => void
}) {
  const src = useImageSrc(resourceId, variant.id)
  return (
    <div className="ommi-variant">
      {src ? <img src={src} alt={variant.label || 'Ảnh tài nguyên'} /> : null}
      <button type="button" aria-label={`Xoá ảnh ${variant.label || variant.id}`}
        onClick={() => onRemove(variant.id)}>
        ×
      </button>
    </div>
  )
}

export function ResourceLibrary() {
  const [page, setPage] = useState<ResourcePage | null>(null)
  const [kind, setKind] = useState('')
  const [query, setQuery] = useState('')
  const [offset, setOffset] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState<Resource | null>(null)
  const [busy, setBusy] = useState(false)
  const [quote, setQuote] = useState<Quote | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)

  const reload = useCallback(async () => {
    setLoading(true)
    try {
      setPage(await listResources({ kind, q: query, offset, limit: PAGE_SIZE }))
      setError('')
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : 'Không tải được kho tài nguyên.')
    } finally {
      setLoading(false)
    }
  }, [kind, query, offset])

  useEffect(() => {
    void reload()
  }, [reload])

  const open = async (id: string) => {
    setQuote(null)
    try {
      setSelected(await getResource(id))
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : 'Không mở được tài nguyên.')
    }
  }

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

  const addResource = () =>
    run(async () => {
      const made = await createResource({ kind: kind || 'character', name: 'Tài nguyên mới' })
      await reload()
      await open(made.id)
    })

  const save = (fields: Partial<Resource>) =>
    run(async () => {
      if (!selected) return
      await updateResource(selected.id, fields)
      setSelected(await getResource(selected.id))
      await reload()
    })

  const upload = (files: FileList | null) =>
    run(async () => {
      if (!selected || !files?.length) return
      for (const file of Array.from(files).slice(0, 8)) {
        await uploadImage(selected.id, file)
      }
      setSelected(await getResource(selected.id))
      await reload()
    })

  const removeVariant = (variantId: string) =>
    run(async () => {
      if (!selected) return
      await deleteImage(selected.id, variantId)
      setSelected(await getResource(selected.id))
      await reload()
    })

  /** Báo giá trước. Không có đường nào tiêu credit mà chưa hỏi. */
  const askQuote = () =>
    run(async () => {
      if (!selected) return
      const body = (await generateImage(selected.id, { count: 1 })) as Quote
      setQuote(body)
    })

  const confirmGenerate = () =>
    run(async () => {
      if (!selected) return
      const started = (await generateImage(selected.id, {
        count: quote?.count ?? 1,
        confirmed: true,
      })) as StartedJob
      setQuote(null)
      // Chờ job xong rồi mới gắn ảnh. Job chạy ở worker riêng nên phải hỏi lại.
      for (let attempt = 0; attempt < 60; attempt += 1) {
        const status = await jobStatus(started.id)
        if (status.status === 'done') {
          await attachJobImages(selected.id, started.id)
          setSelected(await getResource(selected.id))
          await reload()
          return
        }
        if (status.status === 'error' || status.status === 'cancelled') {
          throw new ApiError(500, status.error || 'Sinh ảnh thất bại.')
        }
        await new Promise((resolve) => setTimeout(resolve, 2000))
      }
      throw new ApiError(504, 'Job chạy quá lâu — xem lại ở trang Việc của tôi.')
    })

  const counts = page?.counts ?? {}
  const total = page?.total ?? 0

  return (
    <>
      <header className="ommi-head">
        <div>
          <h1>Kho tài nguyên</h1>
          <p>Nhân vật, bối cảnh và đạo cụ dùng lại giữa các dự án. Kho này chỉ của bạn.</p>
        </div>
        <div className="ommi-spacer" />
        <button type="button" className="primary" onClick={addResource} disabled={busy}>
          ＋ Tài nguyên mới
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
            aria-label="Tìm tài nguyên"
            placeholder="Tìm theo tên hoặc mô tả…"
            value={query}
            onChange={(event) => {
              setOffset(0)
              setQuery(event.target.value)
            }}
          />
          <button
            type="button"
            className="ommi-chip"
            aria-pressed={kind === ''}
            onClick={() => {
              setOffset(0)
              setKind('')
            }}
          >
            Tất cả<b>{total}</b>
          </button>
          {RESOURCE_KINDS.map((item) => (
            <button
              key={item}
              type="button"
              className="ommi-chip"
              aria-pressed={kind === item}
              onClick={() => {
                setOffset(0)
                setKind(item)
              }}
            >
              {KIND_LABEL[item]}
              <b>{counts[item] ?? 0}</b>
            </button>
          ))}
        </div>

        {loading ? (
          <p className="ommi-loading">Đang tải kho…</p>
        ) : page && page.items.length === 0 ? (
          <section className="ommi-empty">
            <h2>Kho còn trống</h2>
            <p>
              Thêm nhân vật, bối cảnh hoặc đạo cụ để dùng lại ở mọi dự án. Mỗi tài nguyên giữ
              được nhiều ảnh tham chiếu, giúp AI vẽ nhất quán giữa các cảnh.
            </p>
            <button type="button" className="primary" onClick={addResource} disabled={busy}>
              Tạo tài nguyên đầu tiên
            </button>
          </section>
        ) : (
          <div className="ommi-grid">
            {page?.items.map((item) => (
              <button
                key={item.id}
                type="button"
                className="ommi-card"
                aria-selected={selected?.id === item.id}
                onClick={() => void open(item.id)}
              >
                <Thumb resource={item} />
                <span className="ommi-card-body">
                  <strong>{item.name}</strong>
                  <span>{KIND_LABEL[item.kind] ?? item.kind}</span>
                </span>
              </button>
            ))}
          </div>
        )}

        {page && page.total > PAGE_SIZE ? (
          <div className="ommi-detail-actions" style={{ marginTop: 16 }}>
            <button
              type="button"
              className="ghost"
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            >
              ← Trang trước
            </button>
            <button
              type="button"
              className="ghost"
              disabled={offset + PAGE_SIZE >= page.total}
              onClick={() => setOffset(offset + PAGE_SIZE)}
            >
              Trang sau →
            </button>
          </div>
        ) : null}
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
            <label>
              Tên
              <input
                type="text"
                value={selected.name}
                onChange={(event) => setSelected({ ...selected, name: event.target.value })}
                onBlur={(event) => void save({ name: event.target.value })}
              />
            </label>
            <label>
              Nhóm
              <select
                value={selected.kind}
                onChange={(event) => void save({ kind: event.target.value as Resource['kind'] })}
              >
                {RESOURCE_KINDS.map((item) => (
                  <option key={item} value={item}>
                    {KIND_LABEL[item]}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Mô tả dùng khi ghép prompt
              <textarea
                value={selected.prompt_text}
                onChange={(event) =>
                  setSelected({ ...selected, prompt_text: event.target.value })
                }
                onBlur={(event) => void save({ prompt_text: event.target.value })}
              />
            </label>

            <div>
              <label style={{ marginBottom: 6 }}>Ảnh tham chiếu</label>
              <div className="ommi-variants">
                {(selected.variants ?? []).map((variant) => (
                  <VariantTile
                    key={variant.id}
                    resourceId={selected.id}
                    variant={variant}
                    onRemove={(id) => void removeVariant(id)}
                  />
                ))}
              </div>
            </div>

            <input
              ref={fileInput}
              type="file"
              accept="image/png,image/jpeg,image/webp"
              multiple
              hidden
              aria-label="Chọn ảnh tài nguyên"
              onChange={(event) => void upload(event.target.files)}
            />
            <div className="ommi-detail-actions">
              <button type="button" className="ghost" disabled={busy}
                onClick={() => fileInput.current?.click()}>
                Tải ảnh lên
              </button>
              <button type="button" className="ghost" disabled={busy} onClick={askQuote}>
                Sinh ảnh bằng AI
              </button>
              <button
                type="button"
                className="ghost"
                disabled={busy}
                onClick={() => void run(async () => {
                  await archiveResource(selected.id, !selected.archived)
                  setSelected(null)
                  await reload()
                })}
              >
                {selected.archived ? 'Bỏ lưu trữ' : 'Lưu trữ'}
              </button>
            </div>

            {quote ? (
              <section className="ommi-empty" aria-label="Xác nhận chi phí">
                <h2>{quote.credit} credit</h2>
                <p>
                  Sinh {quote.count} ảnh cho tài nguyên này. Chưa trừ credit nào cho tới khi
                  bạn xác nhận.
                </p>
                <div className="ommi-detail-actions">
                  <button type="button" className="primary" disabled={busy}
                    onClick={confirmGenerate}>
                    Xác nhận và chạy
                  </button>
                  <button type="button" className="ghost" onClick={() => setQuote(null)}>
                    Huỷ
                  </button>
                </div>
              </section>
            ) : null}
          </div>
        </aside>
      ) : null}
    </>
  )
}
