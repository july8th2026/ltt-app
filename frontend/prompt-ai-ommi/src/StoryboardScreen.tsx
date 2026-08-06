/**
 * StoryboardScreen.tsx — bảng cảnh và chạy lại từng cảnh.
 *
 * Điều màn này phải làm rõ bằng giao diện, không chỉ bằng backend: **chạy lại
 * một cảnh chỉ tốn tiền một cảnh.** Nên nút chạy nằm trên từng thẻ cảnh, và
 * hộp xác nhận nói rõ đang trả cho cảnh nào.
 */
import { useCallback, useEffect, useState } from 'react'
import {
  ApiError,
  type Project,
  type Scene,
  type SceneJob,
  type SceneQuote,
  type Storyboard,
  addScene,
  attachSceneRender,
  createStoryboard,
  deleteScene,
  getStoryboard,
  jobStatus,
  listProjects,
  listStoryboards,
  renderScene,
  restoreSceneVersion,
  compareSceneVersions,
  sceneVersions,
  updateScene,
} from './ommiApi'
import type { SceneCompare } from './ommiApi'

function SceneImage({ imageKey }: { imageKey: string }) {
  // Ảnh cảnh do `taoanh.generate` sinh nên nằm trong namespace của app Tạo ảnh
  // và được chính app đó phục vụ, có kiểm sở hữu theo khoá.
  if (!imageKey) return <div className="ommi-thumb">▨</div>
  return (
    <div className="ommi-thumb">
      <img src={`/taoanh/f/${imageKey}`} alt="" loading="lazy" />
    </div>
  )
}

export function StoryboardScreen() {
  const [projects, setProjects] = useState<Project[]>([])
  const [boards, setBoards] = useState<Storyboard[]>([])
  const [board, setBoard] = useState<Storyboard | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [quote, setQuote] = useState<SceneQuote | null>(null)
  const [openScene, setOpenScene] = useState<Scene | null>(null)
  const [history, setHistory] = useState<
    Array<{ version: number; image_key: string; feedback?: string }>
  >([])

  const reload = useCallback(async () => {
    setLoading(true)
    try {
      const [found, made] = await Promise.all([listProjects(), listStoryboards()])
      setProjects(found)
      setBoards(made.items)
      setError('')
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : 'Không tải được storyboard.')
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

  const openBoard = (id: string) =>
    run(async () => {
      setBoard(await getStoryboard(id))
    })

  const makeBoard = () =>
    run(async () => {
      if (!projects.length) {
        throw new ApiError(400, 'Tạo một dự án trước khi dựng storyboard.')
      }
      const made = await createStoryboard({
        project_id: projects[0].id,
        name: 'Storyboard mới',
      })
      await reload()
      setBoard(await getStoryboard(made.id))
    })

  const newScene = () =>
    run(async () => {
      if (!board) return
      await addScene(board.id, { title: `Cảnh ${(board.scenes?.length ?? 0) + 1}` })
      setBoard(await getStoryboard(board.id))
    })

  const saveScene = (scene: Scene, fields: Partial<Scene>) =>
    run(async () => {
      if (!board) return
      await updateScene(scene.id, fields)
      setBoard(await getStoryboard(board.id))
    })

  const removeScene = (scene: Scene) =>
    run(async () => {
      if (!board) return
      await deleteScene(scene.id)
      setOpenScene(null)
      setBoard(await getStoryboard(board.id))
    })

  // Góp ý cho lần chạy lại. Giữ ở đây (không trong ô prompt) vì nó là chỉnh
  // sửa MỘT LẦN, không phải sửa vĩnh viễn mô tả cảnh.
  const [feedback, setFeedback] = useState('')
  const [compare, setCompare] = useState<SceneCompare | null>(null)
  const [pickLeft, setPickLeft] = useState<number | null>(null)

  const askQuote = (scene: Scene) =>
    run(async () => {
      setQuote((await renderScene(scene.id, { feedback })) as SceneQuote)
    })

  const confirmRender = () =>
    run(async () => {
      if (!quote || !board) return
      const sceneId = quote.scene_id
      const started = (await renderScene(sceneId, { confirmed: true, feedback })) as SceneJob
      setQuote(null)
      for (let attempt = 0; attempt < 60; attempt += 1) {
        const status = await jobStatus(started.id)
        if (status.status === 'done') {
          await attachSceneRender(sceneId, started.id, feedback)
          setFeedback('')
          setBoard(await getStoryboard(board.id))
          return
        }
        if (status.status === 'error' || status.status === 'cancelled') {
          throw new ApiError(500, status.error || 'Sinh ảnh thất bại.')
        }
        await new Promise((resolve) => setTimeout(resolve, 2000))
      }
      throw new ApiError(504, 'Job chạy quá lâu — xem ở trang Việc của tôi.')
    })

  const showHistory = (scene: Scene) =>
    run(async () => {
      setOpenScene(scene)
      setHistory((await sceneVersions(scene.id)).items)
    })

  const soSanh = (scene: Scene, right: number) =>
    run(async () => {
      if (pickLeft === null || pickLeft === right) return
      setCompare(await compareSceneVersions(scene.id, pickLeft, right))
    })

  const restore = (scene: Scene, version: number) =>
    run(async () => {
      if (!board) return
      await restoreSceneVersion(scene.id, version)
      setBoard(await getStoryboard(board.id))
      setOpenScene(null)
    })

  return (
    <>
      <header className="ommi-head">
        <div>
          <h1>Storyboard</h1>
          <p>
            Mỗi cảnh chạy lại độc lập — sửa một khung không phải trả tiền dựng lại cả bộ.
          </p>
        </div>
        <div className="ommi-spacer" />
        {board ? (
          <>
            <button type="button" className="ghost" onClick={() => setBoard(null)}>
              ← Danh sách
            </button>
            <button type="button" className="primary" onClick={newScene} disabled={busy}>
              ＋ Cảnh mới
            </button>
          </>
        ) : (
          <button type="button" className="primary" onClick={makeBoard} disabled={busy}>
            ＋ Storyboard mới
          </button>
        )}
      </header>

      <div className="ommi-body">
        {error ? (
          <p className="ommi-error" role="alert">
            {error}
          </p>
        ) : null}

        {loading ? (
          <p className="ommi-loading">Đang tải…</p>
        ) : board ? (
          board.scenes?.length ? (
            <div className="ommi-grid">
              {board.scenes.map((scene) => (
                <article key={scene.id} className="ommi-card ommi-scene">
                  <SceneImage imageKey={scene.image_key} />
                  <div className="ommi-card-body">
                    <input
                      type="text"
                      aria-label={`Tiêu đề cảnh ${scene.position + 1}`}
                      value={scene.title}
                      onChange={(event) => {
                        const next = { ...scene, title: event.target.value }
                        setBoard({
                          ...board,
                          scenes: board.scenes?.map((s) => (s.id === scene.id ? next : s)),
                        })
                      }}
                      onBlur={(event) => void saveScene(scene, { title: event.target.value })}
                    />
                    <textarea
                      aria-label={`Mô tả cảnh ${scene.position + 1}`}
                      placeholder="Mô tả cảnh này…"
                      value={scene.prompt}
                      onChange={(event) => {
                        const next = { ...scene, prompt: event.target.value }
                        setBoard({
                          ...board,
                          scenes: board.scenes?.map((s) => (s.id === scene.id ? next : s)),
                        })
                      }}
                      onBlur={(event) => void saveScene(scene, { prompt: event.target.value })}
                    />
                    <div className="ommi-detail-actions">
                      <button type="button" className="primary" disabled={busy}
                        onClick={() => void askQuote(scene)}>
                        Sinh ảnh
                      </button>
                      <button type="button" className="ghost" disabled={busy}
                        onClick={() => void showHistory(scene)}>
                        Lịch sử · v{scene.version}
                      </button>
                      <button type="button" className="ghost" disabled={busy}
                        onClick={() => void removeScene(scene)}>
                        Xoá
                      </button>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <section className="ommi-empty">
              <h2>Storyboard chưa có cảnh</h2>
              <p>
                Thêm cảnh rồi mô tả từng khung. Gắn tài nguyên vào cảnh để nhân vật
                giữ nguyên diện mạo giữa các cảnh.
              </p>
              <button type="button" className="primary" onClick={newScene} disabled={busy}>
                ＋ Cảnh mới
              </button>
            </section>
          )
        ) : boards.length ? (
          <div className="ommi-grid">
            {boards.map((item) => (
              <button key={item.id} type="button" className="ommi-card"
                onClick={() => void openBoard(item.id)}>
                <span className="ommi-card-body">
                  <strong>{item.name}</strong>
                  <span>{item.aspect_ratio}</span>
                </span>
              </button>
            ))}
          </div>
        ) : (
          <section className="ommi-empty">
            <h2>Chưa có storyboard nào</h2>
            <p>
              {projects.length
                ? 'Storyboard gom các cảnh của một dự án và cho chạy lại từng cảnh riêng.'
                : 'Tạo một dự án ở trang PROMPT AI OMMI trước, rồi quay lại đây dựng storyboard.'}
            </p>
            {projects.length ? (
              <button type="button" className="primary" onClick={makeBoard} disabled={busy}>
                ＋ Storyboard mới
              </button>
            ) : null}
          </section>
        )}

        {quote ? (
          <section className="ommi-empty" aria-label="Xác nhận chi phí cảnh"
            style={{ marginTop: 16 }}>
            <h2>{quote.credit} credit</h2>
            <p>
              Chỉ sinh ảnh cho <b>một cảnh</b> này. Các cảnh khác không bị đụng tới và
              không bị tính tiền. Chưa trừ credit nào cho tới khi bạn xác nhận.
            </p>
            <div className="ommi-detail-actions">
              <button type="button" className="primary" disabled={busy}
                onClick={confirmRender}>
                Xác nhận và chạy
              </button>
              <button type="button" className="ghost" onClick={() => setQuote(null)}>
                Huỷ
              </button>
            </div>
          </section>
        ) : null}
      </div>

      {openScene ? (
        <aside className="ommi-detail" aria-label={`Lịch sử ${openScene.title}`}>
          <header>
            <h2>Lịch sử · {openScene.title}</h2>
            <div className="ommi-spacer" />
            <button type="button" className="ghost" aria-label="Đóng lịch sử"
              onClick={() => setOpenScene(null)}>
              ×
            </button>
          </header>
          <div className="ommi-detail-body">
            {history.length ? (
              <ul className="ommi-history">
                {history.map((entry) => (
                  <li key={entry.version}>
                    <b>v{entry.version}</b>
                    {entry.feedback ? (
                      <em className="ommi-history-why" title={entry.feedback}>
                        {entry.feedback}
                      </em>
                    ) : null}
                    <span className="ommi-spacer" />
                    <button type="button"
                      className={pickLeft === entry.version ? 'chip on' : 'chip'}
                      aria-pressed={pickLeft === entry.version}
                      onClick={() =>
                        setPickLeft(pickLeft === entry.version ? null : entry.version)}>
                      {pickLeft === entry.version ? 'Đang chọn' : 'Chọn để so'}
                    </button>
                    <button type="button" className="ghost" disabled={busy || pickLeft === null || pickLeft === entry.version}
                      onClick={() => void soSanh(openScene, entry.version)}>
                      So với v{pickLeft ?? '…'}
                    </button>
                    <button type="button" className="ghost" disabled={busy}
                      onClick={() => void restore(openScene, entry.version)}>
                      Dùng lại bản này
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="ommi-loading">Cảnh này chưa chạy lần nào.</p>
            )}

            <label className="ommi-field">
              <span>Muốn đổi gì so với bản hiện tại?</span>
              <textarea rows={2} value={feedback} maxLength={600}
                placeholder="vd: trời mưa, bỏ cái cây bên trái"
                onChange={(e) => setFeedback(e.target.value)} />
              <small>
                Chỉ áp dụng cho lần chạy tới — mô tả gốc của cảnh không đổi.
              </small>
            </label>

            {compare ? (
              <section className="ommi-compare" aria-label="So hai bản">
                <h3>v{compare.left.version} ↔ v{compare.right.version}</h3>
                {compare.cung_anh ? (
                  <p className="ommi-warn">
                    Hai bản ra <b>cùng một ảnh</b> — lần chạy lại không đổi gì.
                  </p>
                ) : null}
                <div className="ommi-compare-grid">
                  {[compare.left, compare.right].map((ban) => (
                    <figure key={ban.version}>
                      <figcaption>v{ban.version}</figcaption>
                      {ban.image_key ? (
                        <img src={`/prompt-ai-ommi/f/${ban.image_key}`}
                          alt={`Bản ${ban.version}`} loading="lazy" />
                      ) : (
                        <p className="ommi-loading">Bản này chưa có ảnh.</p>
                      )}
                      {ban.feedback ? <p><em>{ban.feedback}</em></p> : null}
                    </figure>
                  ))}
                </div>
                {compare.prompt_khac_nhau.length ? (
                  <pre className="ommi-diff">
                    {compare.prompt_khac_nhau.join('\n')}
                  </pre>
                ) : (
                  <p className="ommi-loading">Prompt hai bản giống hệt nhau.</p>
                )}
                <button type="button" className="ghost" onClick={() => setCompare(null)}>
                  Đóng so sánh
                </button>
              </section>
            ) : null}
          </div>
        </aside>
      ) : null}
    </>
  )
}
