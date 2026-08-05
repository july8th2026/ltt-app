/**
 * ProjectScreen.tsx — Dự án và Brief & Director trong một luồng.
 *
 * Hai màn này tách ra thì người dùng phải nhớ mình đang ở dự án nào; gộp lại thì
 * chọn dự án xong là thấy ngay brief của nó. Đây cũng là phần bản OMMI cũ làm
 * đúng — brief và director của nó vẫn chạy, nên ở đây gọi lại chính API đó thay
 * vì viết lại một luồng thứ hai.
 */
import { useCallback, useEffect, useState } from 'react'
import {
  ApiError,
  type DirectorQuote,
  type Project,
  type ProjectDetail,
  applyJob,
  createProject,
  exportUrl,
  generateProject,
  getProject,
  jobStatus,
  listProjects,
  quoteProject,
  saveProject,
} from './ommiApi'

type Brief = {
  title?: string
  story?: string
  goal?: string
  audience?: string
  scene_count?: number
  aspect_ratio?: string
  language?: string
  style?: string
}

function brief(project: ProjectDetail | null): Brief {
  const payload = (project?.payload ?? {}) as Record<string, unknown>
  return (payload.brief as Brief) ?? {}
}

export function ProjectScreen({ mode }: { mode: 'projects' | 'brief' }) {
  const [projects, setProjects] = useState<Project[]>([])
  const [project, setProject] = useState<ProjectDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [quote, setQuote] = useState<DirectorQuote | null>(null)
  const [progress, setProgress] = useState('')

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
      setQuote(null)
      setProject(await getProject(id))
    })

  const add = () =>
    run(async () => {
      const made = await createProject('Dự án mới')
      await reload()
      setProject(await getProject(made.id))
    })

  const saveBrief = (fields: Brief) =>
    run(async () => {
      if (!project) return
      const payload = { ...(project.payload as Record<string, unknown>) }
      payload.brief = { ...brief(project), ...fields }
      setProject(
        await saveProject(project.id, { revision: project.revision, payload }),
      )
      await reload()
    })

  const askQuote = () =>
    run(async () => {
      if (!project) return
      setQuote(await quoteProject(project.id, { operation: 'director' }))
    })

  const confirmRun = () =>
    run(async () => {
      if (!project) return
      const started = await generateProject(project.id, { operation: 'director' })
      setQuote(null)
      setProgress('Đang chạy…')
      try {
        for (let attempt = 0; attempt < 90; attempt += 1) {
          const status = await jobStatus(started.id)
          if (status.status === 'done') {
            await applyJob(project.id, started.id)
            setProject(await getProject(project.id))
            setProgress('')
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

  const current = brief(project)
  const showBrief = mode === 'brief'

  return (
    <>
      <header className="ommi-head">
        <div>
          <h1>{showBrief ? 'Brief & Director' : 'Dự án'}</h1>
          <p>
            {showBrief
              ? 'Khóa câu chuyện rồi để AI phân cảnh. Luôn xem giá trước khi chạy.'
              : 'Mỗi dự án giữ brief, storyboard và bản xuất của riêng nó.'}
          </p>
        </div>
        <div className="ommi-spacer" />
        {project ? (
          <button type="button" className="ghost" onClick={() => setProject(null)}>
            ← Danh sách
          </button>
        ) : null}
        <button type="button" className="primary" onClick={add} disabled={busy}>
          ＋ Dự án mới
        </button>
      </header>

      <div className="ommi-body">
        {error ? (
          <p className="ommi-error" role="alert">
            {error}
          </p>
        ) : null}
        {progress ? <p className="ommi-loading">{progress}</p> : null}

        {loading ? (
          <p className="ommi-loading">Đang tải…</p>
        ) : project ? (
          <>
            <div className="ommi-form">
              <label>
                Tên dự án
                <input
                  type="text"
                  value={current.title ?? project.name}
                  onChange={(event) =>
                    setProject({
                      ...project,
                      payload: {
                        ...(project.payload as Record<string, unknown>),
                        brief: { ...current, title: event.target.value },
                      },
                    })
                  }
                  onBlur={(event) => void saveBrief({ title: event.target.value })}
                />
              </label>
              <label>
                Nội dung / câu chuyện
                <textarea
                  value={current.story ?? ''}
                  placeholder="Mô tả bối cảnh, nhân vật, hành động và kết quả mong muốn…"
                  onChange={(event) =>
                    setProject({
                      ...project,
                      payload: {
                        ...(project.payload as Record<string, unknown>),
                        brief: { ...current, story: event.target.value },
                      },
                    })
                  }
                  onBlur={(event) => void saveBrief({ story: event.target.value })}
                />
              </label>
              <label>
                Số cảnh
                <input
                  type="number"
                  min={1}
                  max={20}
                  value={current.scene_count ?? 6}
                  onChange={(event) =>
                    void saveBrief({ scene_count: Number(event.target.value) })
                  }
                />
              </label>
            </div>

            <div className="ommi-detail-actions" style={{ marginTop: 14 }}>
              <button type="button" className="primary" onClick={askQuote} disabled={busy}>
                Báo giá AI Director
              </button>
              <a className="ommi-download" href={exportUrl(project.id, 'json')}>
                Tải .json
              </a>
              <a className="ommi-download" href={exportUrl(project.id, 'md')}>
                Tải .md
              </a>
              <a className="ommi-download" href={exportUrl(project.id, 'zip')}>
                Tải .zip
              </a>
            </div>

            {quote ? (
              <section className="ommi-empty" aria-label="Xác nhận chi phí Director"
                style={{ marginTop: 16 }}>
                <h2>{quote.credit} credit</h2>
                <p>
                  Phân {quote.scene_count} cảnh bằng {quote.model}. Chưa trừ credit nào
                  cho tới khi bạn xác nhận.
                </p>
                <div className="ommi-detail-actions">
                  <button type="button" className="primary" onClick={confirmRun}
                    disabled={busy}>
                    Xác nhận và chạy
                  </button>
                  <button type="button" className="ghost" onClick={() => setQuote(null)}>
                    Huỷ
                  </button>
                </div>
              </section>
            ) : null}
          </>
        ) : projects.length ? (
          <div className="ommi-grid">
            {projects.map((item) => (
              <button key={item.id} type="button" className="ommi-card"
                onClick={() => void open(item.id)}>
                <span className="ommi-card-body">
                  <strong>{item.name}</strong>
                  <span>revision {item.revision}</span>
                </span>
              </button>
            ))}
          </div>
        ) : (
          <section className="ommi-empty">
            <h2>Chưa có dự án nào</h2>
            <p>
              Dự án là nơi giữ brief, storyboard và bản xuất. Tạo một dự án để bắt đầu.
            </p>
            <button type="button" className="primary" onClick={add} disabled={busy}>
              ＋ Dự án mới
            </button>
          </section>
        )}
      </div>
    </>
  )
}
