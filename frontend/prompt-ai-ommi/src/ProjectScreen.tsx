import { useEscape } from './useEscape'
import { useCallback, useEffect, useState } from 'react'
import {
  ApiError,
  type DirectorQuote,
  type LibraryItem,
  type Project,
  type ProjectDetail,
  type ProjectPreview,
  applyJob,
  createProject,
  exportUrl,
  generateProject,
  getProject,
  jobStatus,
  listLibrary,
  listProjects,
  previewProject,
  quoteProject,
  saveProject,
} from './ommiApi'

type Brief = {
  title: string
  story: string
  goal: string
  audience: string
  duration_seconds: number
  scene_count: number
  aspect_ratio: string
  language: string
  style_id: string
  style_custom: string
  meta_prompt_id: string
  snippet_ids: string[]
}

const EMPTY_BRIEF: Brief = {
  title: 'Dự án mới',
  story: '',
  goal: '',
  audience: '',
  duration_seconds: 30,
  scene_count: 6,
  aspect_ratio: '16:9',
  language: 'vi',
  style_id: 'cinematic',
  style_custom: '',
  meta_prompt_id: '',
  snippet_ids: [],
}

function projectBrief(project: ProjectDetail | null): Brief {
  const payload = (project?.payload ?? {}) as Record<string, unknown>
  const value = (payload.brief ?? {}) as Partial<Brief>
  return { ...EMPTY_BRIEF, ...value, snippet_ids: value.snippet_ids ?? [] }
}

function projectPayload(project: ProjectDetail, draft: Brief): Record<string, unknown> {
  return { ...(project.payload as Record<string, unknown>), brief: draft }
}

function mergeItems(...groups: LibraryItem[][]): LibraryItem[] {
  const rows = new Map<string, LibraryItem>()
  groups.flat().forEach((item) => rows.set(item.id, item))
  return [...rows.values()].sort((a, b) => a.name.localeCompare(b.name, 'vi'))
}

export function ProjectScreen({ mode }: { mode: 'projects' | 'brief' }) {
  const [projects, setProjects] = useState<Project[]>([])
  const [project, setProject] = useState<ProjectDetail | null>(null)
  const [draft, setDraft] = useState<Brief>(EMPTY_BRIEF)
  const [dirty, setDirty] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [quote, setQuote] = useState<DirectorQuote | null>(null)
  const [preview, setPreview] = useState<ProjectPreview | null>(null)
  const [progress, setProgress] = useState('')
  const [styles, setStyles] = useState<LibraryItem[]>([])
  const [metas, setMetas] = useState<LibraryItem[]>([])
  const [snippets, setSnippets] = useState<LibraryItem[]>([])

  useEscape(quote !== null, () => setQuote(null))

  const reload = useCallback(async () => {
    setLoading(true)
    try {
      setProjects(await listProjects())
      setError('')
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : 'Không tải được dự án.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void reload()
    void Promise.all([
      listLibrary('style', { catalog: true }),
      listLibrary('style'),
      listLibrary('meta', { catalog: true }),
      listLibrary('meta'),
      listLibrary('snippet', { catalog: true }),
      listLibrary('snippet'),
    ]).then(([styleCatalog, ownStyles, metaCatalog, ownMetas, snippetCatalog, ownSnippets]) => {
      setStyles(mergeItems(styleCatalog.items, ownStyles.items))
      setMetas(mergeItems(metaCatalog.items, ownMetas.items))
      setSnippets(mergeItems(snippetCatalog.items, ownSnippets.items))
    }).catch((reason) => {
      setError(reason instanceof ApiError ? reason.message : 'Không tải được thư viện prompt.')
    })
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

  const selectProject = (value: ProjectDetail) => {
    setProject(value)
    setDraft(projectBrief(value))
    setDirty(false)
    setPreview(null)
    setQuote(null)
  }

  const open = (id: string) => run(async () => selectProject(await getProject(id)))

  const add = () => run(async () => {
    const made = await createProject('Dự án mới')
    await reload()
    selectProject(await getProject(made.id))
  })

  const updateDraft = (fields: Partial<Brief>) => {
    setDraft((current) => ({ ...current, ...fields }))
    setDirty(true)
    setPreview(null)
  }

  const persist = async (): Promise<ProjectDetail> => {
    if (!project) throw new ApiError(400, 'Chưa chọn dự án.')
    const saved = await saveProject(project.id, {
      revision: project.revision,
      payload: projectPayload(project, draft),
    })
    setProject(saved)
    setDraft(projectBrief(saved))
    setDirty(false)
    await reload()
    return saved
  }

  const saveBrief = () => run(async () => { await persist() })

  const buildPreview = () => run(async () => {
    const saved = await persist()
    setPreview(await previewProject(saved.id, saved.payload))
  })

  const askQuote = () => run(async () => {
    const saved = await persist()
    const checked = await previewProject(saved.id, saved.payload)
    setPreview(checked)
    if (!checked.valid) throw new ApiError(422, 'Brief chưa đạt kiểm tra trước khi chạy.')
    setQuote(await quoteProject(saved.id, { payload: saved.payload, operation: 'director' }))
  })

  const confirmRun = () => run(async () => {
    if (!project) return
    const revisionToApply = project.revision
    const started = await generateProject(project.id, {
      payload: project.payload,
      operation: 'director',
    })
    setQuote(null)
    setProgress('Đang chạy…')
    try {
      for (let attempt = 0; attempt < 90; attempt += 1) {
        const status = await jobStatus(started.id)
        if (status.status === 'done') {
          selectProject(await applyJob(project.id, started.id, revisionToApply))
          return
        }
        if (status.status === 'error' || status.status === 'cancelled') {
          throw new ApiError(500, status.error || 'AI Director thất bại.')
        }
        setProgress(status.progress_msg || `Đang chạy… ${status.progress}%`)
        await new Promise((resolve) => setTimeout(resolve, 2000))
      }
      throw new ApiError(504, 'Job chạy quá lâu — xem ở trang Việc của tôi.')
    } finally {
      setProgress('')
    }
  })

  const toggleSnippet = (id: string) => {
    const selected = draft.snippet_ids.includes(id)
      ? draft.snippet_ids.filter((value) => value !== id)
      : [...draft.snippet_ids, id].slice(0, 8)
    updateDraft({ snippet_ids: selected })
  }

  const showBrief = mode === 'brief'
  const frozen = busy || quote !== null

  return (
    <>
      <header className="ommi-head">
        <div>
          <h1>{showBrief ? 'Brief & Director' : 'Dự án'}</h1>
          <p>{showBrief
            ? 'Viết brief, chọn công thức đã lưu, kiểm tra prompt miễn phí rồi mới báo giá.'
            : 'Mỗi dự án giữ brief, storyboard và bản xuất của riêng nó.'}</p>
        </div>
        <div className="ommi-spacer" />
        {project ? <button type="button" className="ghost" onClick={() => setProject(null)}>
          ← Danh sách
        </button> : null}
        <button type="button" className="primary" onClick={add} disabled={busy}>
          ＋ Dự án mới
        </button>
      </header>

      <div className="ommi-body">
        {error ? <p className="ommi-error" role="alert">{error}</p> : null}
        {progress ? <p className="ommi-loading">{progress}</p> : null}

        {loading ? <p className="ommi-loading">Đang tải…</p> : project ? (
          <>
            <div className="ommi-form ommi-brief-form">
              <label>Tên dự án
                <input type="text" value={draft.title} disabled={frozen}
                  onChange={(event) => updateDraft({ title: event.target.value })} />
              </label>
              <label className="ommi-field-wide">Nội dung / câu chuyện
                <textarea value={draft.story} disabled={frozen}
                  placeholder="Mô tả bối cảnh, nhân vật, hành động và kết quả mong muốn…"
                  onChange={(event) => updateDraft({ story: event.target.value })} />
              </label>
              <label>Mục tiêu
                <input type="text" value={draft.goal} disabled={frozen}
                  placeholder="Video này cần đạt điều gì?"
                  onChange={(event) => updateDraft({ goal: event.target.value })} />
              </label>
              <label>Khán giả
                <input type="text" value={draft.audience} disabled={frozen}
                  placeholder="Ai sẽ xem nội dung này?"
                  onChange={(event) => updateDraft({ audience: event.target.value })} />
              </label>
              <label>Thời lượng (giây)
                <input type="number" min={3} max={600} value={draft.duration_seconds}
                  disabled={frozen}
                  onChange={(event) => updateDraft({ duration_seconds: Number(event.target.value) })} />
              </label>
              <label>Số cảnh
                <input type="number" min={1} max={20} value={draft.scene_count}
                  disabled={frozen}
                  onChange={(event) => updateDraft({ scene_count: Number(event.target.value) })} />
              </label>
              <label>Tỉ lệ khung hình
                <select value={draft.aspect_ratio} disabled={frozen}
                  onChange={(event) => updateDraft({ aspect_ratio: event.target.value })}>
                  {['16:9', '9:16', '1:1', '4:3', '3:4', '21:9'].map((value) =>
                    <option key={value}>{value}</option>)}
                </select>
              </label>
              <label>Ngôn ngữ đầu ra
                <select value={draft.language} disabled={frozen}
                  onChange={(event) => updateDraft({ language: event.target.value })}>
                  <option value="vi">Tiếng Việt</option>
                  <option value="en">English</option>
                </select>
              </label>
              <label>Phong cách
                <select value={draft.style_id} disabled={frozen}
                  onChange={(event) => updateDraft({ style_id: event.target.value, style_custom: '' })}>
                  <option value="cinematic">Điện ảnh mặc định</option>
                  {styles.filter((item) => item.id !== 'cinematic').map((item) =>
                    <option key={item.id} value={item.id}>{item.name}</option>)}
                </select>
              </label>
              <label>Meta Director
                <select value={draft.meta_prompt_id} disabled={frozen}
                  onChange={(event) => updateDraft({ meta_prompt_id: event.target.value })}>
                  <option value="">Director mặc định</option>
                  {metas.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                </select>
              </label>
              <fieldset className="ommi-field-wide ommi-snippet-list" disabled={frozen}>
                <legend>Khối prompt bổ sung (tối đa 8)</legend>
                {snippets.map((item) => <label key={item.id}>
                  <input type="checkbox" checked={draft.snippet_ids.includes(item.id)}
                    onChange={() => toggleSnippet(item.id)} />
                  <span><strong>{item.name}</strong><small>{item.body}</small></span>
                </label>)}
              </fieldset>
            </div>

            <div className="ommi-detail-actions" style={{ marginTop: 14 }}>
              <button type="button" className="ghost" onClick={saveBrief} disabled={frozen || !dirty}>
                {dirty ? 'Lưu brief' : 'Đã lưu'}
              </button>
              <button type="button" className="primary" onClick={buildPreview} disabled={frozen}>
                Xem trước prompt
              </button>
              <button type="button" className="primary" onClick={askQuote} disabled={frozen}>
                Báo giá AI Director
              </button>
              <a className="ommi-download" href={exportUrl(project.id, 'json')}>Tải .json</a>
              <a className="ommi-download" href={exportUrl(project.id, 'md')}>Tải .md</a>
              <a className="ommi-download" href={exportUrl(project.id, 'zip')}>Tải .zip</a>
            </div>

            {preview ? <section className="ommi-preview" aria-label="Xem trước prompt">
              <div className="ommi-preview-head">
                <h2>{preview.valid ? 'Brief sẵn sàng' : 'Brief cần bổ sung'}</h2>
                <span className={preview.valid ? 'ommi-pass' : 'ommi-fail'}>
                  {preview.valid ? 'PASS' : 'CHƯA PASS'}
                </span>
              </div>
              <ul>{preview.checklist.map((item) =>
                <li key={item.id}>{item.passed ? '✓' : '×'} {item.label}</li>)}</ul>
              <p>Style: <strong>{preview.selections.style}</strong> · Meta: <strong>{preview.selections.meta}</strong>
                {preview.selections.snippets.length
                  ? ` · Khối prompt: ${preview.selections.snippets.join(', ')}` : ''}</p>
              <pre>{preview.master_prompt}</pre>
            </section> : null}

            {quote ? <section className="ommi-empty" aria-label="Xác nhận chi phí Director"
              style={{ marginTop: 16 }}>
              <h2>{quote.credit} credit</h2>
              <p>Phân {quote.scene_count} cảnh bằng {quote.model}. Các trường đã khóa để giá và
                dữ liệu chạy luôn khớp với nhau.</p>
              <div className="ommi-detail-actions">
                <button type="button" className="primary" onClick={confirmRun} disabled={busy}>
                  Xác nhận và chạy
                </button>
                <button type="button" className="ghost" onClick={() => setQuote(null)}>Huỷ</button>
              </div>
            </section> : null}
          </>
        ) : projects.length ? (
          <div className="ommi-grid">{projects.map((item) =>
            <button key={item.id} type="button" className="ommi-card" onClick={() => void open(item.id)}>
              <span className="ommi-card-body"><strong>{item.name}</strong><span>revision {item.revision}</span></span>
            </button>)}</div>
        ) : (
          <section className="ommi-empty">
            <h2>Chưa có dự án nào</h2>
            <p>Dự án là nơi giữ brief, storyboard và bản xuất. Tạo một dự án để bắt đầu.</p>
            <button type="button" className="primary" onClick={add} disabled={busy}>＋ Dự án mới</button>
          </section>
        )}
      </div>
    </>
  )
}
