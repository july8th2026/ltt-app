/**
 * StudioShell.tsx — Studio Kịch bản, lối vào mặc định (Q-3, spec §6.4).
 *
 * Hai cột: `BriefPane` (trái, danh sách brief) + khung soạn (phải, brief +
 * cảnh + Preflight/Bundle/Báo giá/Chạy + lịch sử iterate). Dùng lại đúng
 * token màu/khuôn CSS của `ommi.css` (`.ommi-*`) — không thêm thư viện UI mới.
 *
 * ⛔ Không hàm nào ở đây tự tính lại credit: `quoteBrief`/`generateBrief` trả
 * số, ta chỉ hiển thị. `verdict="rejected"` không hoàn credit — nút "Từ chối"
 * gọi thẳng `setVerdict`, không có đường "hoàn tiền" nào ở tầng UI.
 */
import { useCallback, useEffect, useState } from 'react'
import { BriefPane } from './BriefPane'
import { useEscape } from './useEscape'
import {
  ApiError,
  type Background,
  type Bundle,
  type Canh,
  type Character,
  type Preflight,
  type BriefQuote,
  type Brief,
  bundleBrief,
  generateBrief,
  getBrief,
  listBackgrounds,
  listCharacters,
  listIterations,
  preflightBrief,
  quoteBrief,
  setVerdict,
  type Iteration,
  updateBrief,
} from './ommiApi'

/**
 * Trần số cảnh kịch bản. Giá trị THẬT nằm ở backend
 * (`apps/prompt_ai_ommi/project_schema.py::MAX_SCENES = 20`) — đã đọc
 * `routes/briefs.py`, `routes/projects.py`, `routes/_shared.py`: KHÔNG endpoint
 * nào trả số này ra cho frontend hôm nay. Đặt hằng số có tên ở đây theo đúng
 * luật §4.4 của `DIEU_HUONG_AGENT.md` thay vì gõ số 20 rải rác trong JSX.
 * ⭐ BÁO ĐIỀU PHỐI: cần nối hằng số này với `project_schema.MAX_SCENES`, ví dụ
 * thêm vào response của `GET /api/briefs/{bid}` hoặc một endpoint cấu hình
 * riêng, để đổi trần ở một chỗ là đủ.
 */
/** Luoi cuoi khi backend khong truyen `data-max-scenes`. ⛔ KHONG phai ban khai
 *  thu hai: tran THAT la `project_schema.MAX_SCENES`, di ra qua
 *  `_render_workspace` -> template `data-max-scenes` -> `main.tsx`. */
const TRAN_MAC_DINH = 20

/**
 * Ngưỡng cảnh báo (quyết định Q-17, 27/09/2026, `docs/PROMPT_AI/QUYET_DINH_26-09.md`).
 * Trần BÁN vẫn là `TRAN_SO_CANH` (không hạ) — kịch bản trên ngưỡng này CÓ
 * THỂ phải chạy lại từng cảnh, vì đo thật 2 lần ở `scene_count=20` chỉ trả
 * 19/20 cảnh, và độ dài `prompt` co dần theo thứ tự cảnh dù chưa chạm trần
 * token. Đây chỉ là cảnh báo hiển thị, không phải một trần mới.
 */
const NGUONG_CANH_BAO = 15

type Draft = Pick<
  Brief,
  | 'title'
  | 'story_vi'
  | 'goal'
  | 'audience'
  | 'target_duration_sec'
  | 'target_scenes'
  | 'aspect_ratio'
  | 'language'
  | 'character_id'
  | 'background_id'
>

function draftOf(brief: Brief): Draft {
  return {
    title: brief.title,
    story_vi: brief.story_vi,
    goal: brief.goal,
    audience: brief.audience,
    target_duration_sec: brief.target_duration_sec,
    target_scenes: brief.target_scenes,
    aspect_ratio: brief.aspect_ratio,
    language: brief.language,
    character_id: brief.character_id,
    background_id: brief.background_id,
  }
}

export function StudioShell({ maxScenes = TRAN_MAC_DINH }:
                            { maxScenes?: number } = {}) {
  const TRAN_SO_CANH = maxScenes
  const [selectedId, setSelectedId] = useState('')
  const [reloadToken, setReloadToken] = useState(0)

  const [brief, setBrief] = useState<Brief | null>(null)
  const [canh, setCanh] = useState<Canh[]>([])
  const [draft, setDraft] = useState<Draft | null>(null)
  const [dirty, setDirty] = useState(false)

  const [characters, setCharacters] = useState<Character[]>([])
  const [backgrounds, setBackgrounds] = useState<Background[]>([])

  const [preflight, setPreflight] = useState<Preflight | null>(null)
  const [bundle, setBundle] = useState<Bundle | null>(null)
  const [quote, setQuote] = useState<BriefQuote | null>(null)
  const [feedback, setFeedback] = useState('')
  const [iterations, setIterations] = useState<Iteration[]>([])
  const [freeLeft, setFreeLeft] = useState<number | null>(null)
  const [runResult, setRunResult] = useState<string>('')

  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEscape(bundle !== null, () => setBundle(null))

  useEffect(() => {
    void listCharacters()
      .then((res) => setCharacters(res.characters))
      .catch(() => undefined)
    void listBackgrounds()
      .then((res) => setBackgrounds(res.backgrounds))
      .catch(() => undefined)
  }, [])

  const loadIterations = useCallback(async (briefId: string) => {
    const res = await listIterations(briefId)
    setIterations(res.iterations)
    setFreeLeft(res.free_left)
  }, [])

  const select = useCallback(
    (id: string) => {
      setSelectedId(id)
      setPreflight(null)
      setBundle(null)
      setQuote(null)
      setFeedback('')
      setRunResult('')
      setError('')
      if (!id) {
        setBrief(null)
        setCanh([])
        setDraft(null)
        setIterations([])
        setFreeLeft(null)
        return
      }
      setLoading(true)
      Promise.all([getBrief(id), listIterations(id)])
        .then(([detail, its]) => {
          setBrief(detail.brief)
          setCanh(detail.canh)
          setDraft(draftOf(detail.brief))
          setDirty(false)
          setIterations(its.iterations)
          setFreeLeft(its.free_left)
        })
        .catch((reason) => {
          setError(reason instanceof ApiError ? reason.message : 'Không tải được brief.')
        })
        .finally(() => setLoading(false))
    },
    [],
  )

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

  const updateDraft = (fields: Partial<Draft>) => {
    setDraft((current) => (current ? { ...current, ...fields } : current))
    setDirty(true)
    setPreflight(null)
    setBundle(null)
    setQuote(null)
  }

  const save = () =>
    run(async () => {
      if (!brief || !draft) return
      const saved = await updateBrief(brief.id, draft)
      setBrief(saved.brief)
      setDraft(draftOf(saved.brief))
      setDirty(false)
      setReloadToken((n) => n + 1)
    })

  const saveCanh = (updated: Canh) =>
    run(async () => {
      if (!brief) return
      const next = canh.map((item) => (item.id === updated.id ? updated : item))
      setCanh(next)
      const saved = await updateBrief(brief.id, { canh: next })
      setBrief(saved.brief)
      const detail = await getBrief(brief.id)
      setCanh(detail.canh)
    })

  const doPreflight = () =>
    run(async () => {
      if (!brief) return
      setPreflight(await preflightBrief(brief.id))
    })

  const doBundle = () =>
    run(async () => {
      if (!brief) return
      setBundle(await bundleBrief(brief.id, { meta_prompt_id: brief.meta_prompt_id || undefined }))
    })

  const doQuote = () =>
    run(async () => {
      if (!brief) return
      setQuote(await quoteBrief(brief.id))
    })

  const doGenerate = () =>
    run(async () => {
      if (!brief) return
      const result = await generateBrief(brief.id, { confirmed: true, feedback: feedback || undefined })
      setRunResult(
        result.was_free
          ? 'Lượt miễn phí — không trừ credit.'
          : `Đã chạy — trừ ${result.credit ?? 0} credit.`,
      )
      setQuote(null)
      setFeedback('')
      await loadIterations(brief.id)
    })

  const doVerdict = (iterationId: string, verdict: 'kept' | 'rejected') =>
    run(async () => {
      await setVerdict(iterationId, verdict)
      if (brief) await loadIterations(brief.id)
    })

  const frozen = busy || loading

  return (
    <div
      className="ommi-studio"
      style={{ display: 'grid', gridTemplateColumns: '300px minmax(0, 1fr)', flex: 1, minHeight: 0 }}
    >
      <BriefPane selectedId={selectedId} onSelect={select} reloadToken={reloadToken} />

      <section className="ommi-main">
        {!selectedId || !brief || !draft ? (
          <section className="ommi-empty">
            <h2>Chưa chọn brief</h2>
            <p>Chọn một brief bên trái, hoặc tạo brief mới để bắt đầu soạn kịch bản.</p>
          </section>
        ) : (
          <>
            <header className="ommi-head">
              <div>
                <h1>{draft.title || 'Chưa đặt tên'}</h1>
                <p>
                  Brief · {iterations.length} lượt đã chạy
                  {freeLeft !== null ? ` · còn ${freeLeft} lượt miễn phí` : ''}
                </p>
              </div>
              <div className="ommi-spacer" />
            </header>

            <div className="ommi-body">
              {error ? (
                <p className="ommi-error" role="alert">
                  {error}
                </p>
              ) : null}
              {runResult ? <p className="ommi-loading">{runResult}</p> : null}

              <div className="ommi-form ommi-brief-form">
                <label>
                  Tên brief
                  <input
                    type="text"
                    value={draft.title}
                    disabled={frozen}
                    onChange={(event) => updateDraft({ title: event.target.value })}
                  />
                </label>
                <label className="ommi-field-wide">
                  Nội dung / câu chuyện
                  <textarea
                    value={draft.story_vi}
                    disabled={frozen}
                    onChange={(event) => updateDraft({ story_vi: event.target.value })}
                  />
                </label>
                <label>
                  Mục tiêu
                  <input
                    type="text"
                    value={draft.goal}
                    disabled={frozen}
                    onChange={(event) => updateDraft({ goal: event.target.value })}
                  />
                </label>
                <label>
                  Khán giả
                  <input
                    type="text"
                    value={draft.audience}
                    disabled={frozen}
                    onChange={(event) => updateDraft({ audience: event.target.value })}
                  />
                </label>
                <label>
                  Thời lượng (giây)
                  <input
                    type="number"
                    inputMode="numeric"
                    min={3}
                    max={600}
                    value={draft.target_duration_sec}
                    disabled={frozen}
                    onChange={(event) => updateDraft({ target_duration_sec: Number(event.target.value) })}
                  />
                </label>
                <label>
                  Số cảnh
                  <input
                    type="number"
                    inputMode="numeric"
                    min={1}
                    max={TRAN_SO_CANH}
                    value={draft.target_scenes}
                    disabled={frozen}
                    onChange={(event) => updateDraft({ target_scenes: Number(event.target.value) })}
                  />
                </label>
                <label>
                  Tỉ lệ khung hình
                  <select
                    value={draft.aspect_ratio}
                    disabled={frozen}
                    onChange={(event) => updateDraft({ aspect_ratio: event.target.value })}
                  >
                    {['16:9', '9:16', '1:1', '4:3', '3:4', '21:9'].map((value) => (
                      <option key={value}>{value}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Ngôn ngữ đầu ra
                  <select
                    value={draft.language}
                    disabled={frozen}
                    onChange={(event) => updateDraft({ language: event.target.value })}
                  >
                    <option value="vi">Tiếng Việt</option>
                    <option value="en">English</option>
                  </select>
                </label>
                <label>
                  Nhân vật khoá
                  <select
                    value={draft.character_id}
                    disabled={frozen}
                    onChange={(event) => updateDraft({ character_id: event.target.value })}
                  >
                    <option value="">— không chọn —</option>
                    {characters.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Bối cảnh khoá
                  <select
                    value={draft.background_id}
                    disabled={frozen}
                    onChange={(event) => updateDraft({ background_id: event.target.value })}
                  >
                    <option value="">— không chọn —</option>
                    {backgrounds.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.name}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              {draft.target_scenes > NGUONG_CANH_BAO ? (
                <p className="ommi-warn" role="alert">
                  Kịch bản trên {NGUONG_CANH_BAO} cảnh có thể phải chạy lại từng cảnh — AI Director
                  suy giảm chất lượng dần ở các cảnh cuối khi kịch bản dài.
                </p>
              ) : null}

              <div className="ommi-detail-actions" style={{ marginTop: 14 }}>
                <button type="button" className="ghost" onClick={save} disabled={frozen || !dirty}>
                  {dirty ? 'Lưu brief' : 'Đã lưu'}
                </button>
                <button type="button" className="primary" onClick={doPreflight} disabled={frozen}>
                  Preflight
                </button>
                <button type="button" className="primary" onClick={doBundle} disabled={frozen}>
                  Bundle
                </button>
                <button type="button" className="primary" onClick={doQuote} disabled={frozen}>
                  Báo giá
                </button>
                <button type="button" className="primary" onClick={doGenerate} disabled={frozen}>
                  Chạy
                </button>
              </div>

              {canh.length ? (
                <section aria-label="Cảnh kịch bản" style={{ marginTop: 16 }}>
                  <h2 style={{ fontSize: 14 }}>Cảnh ({canh.length})</h2>
                  <div className="ommi-grid">
                    {canh.map((item) => (
                      <article key={item.id} className="ommi-card ommi-scene">
                        <div className="ommi-card-body">
                          <input
                            type="text"
                            aria-label={`Tiêu đề cảnh ${item.position + 1}`}
                            value={item.title}
                            disabled={frozen}
                            onChange={(event) =>
                              setCanh((rows) =>
                                rows.map((r) => (r.id === item.id ? { ...r, title: event.target.value } : r)),
                              )
                            }
                            onBlur={(event) => void saveCanh({ ...item, title: event.target.value })}
                          />
                          <textarea
                            aria-label={`Prompt cảnh ${item.position + 1}`}
                            value={item.prompt}
                            disabled={frozen}
                            onChange={(event) =>
                              setCanh((rows) =>
                                rows.map((r) => (r.id === item.id ? { ...r, prompt: event.target.value } : r)),
                              )
                            }
                            onBlur={(event) => void saveCanh({ ...item, prompt: event.target.value })}
                          />
                        </div>
                      </article>
                    ))}
                  </div>
                </section>
              ) : null}

              {preflight ? (
                <section className="ommi-preview" aria-label="Kết quả Preflight" style={{ marginTop: 16 }}>
                  <div className="ommi-preview-head">
                    <h2>Preflight</h2>
                    <span className={preflight.passed ? 'ommi-pass' : 'ommi-fail'}>
                      {preflight.passed ? 'PASS' : 'CHƯA PASS'}
                    </span>
                  </div>
                  <ul>
                    {preflight.checklist.map((item) => (
                      <li key={item.id}>
                        {item.passed ? '✓' : '×'} {item.label}
                      </li>
                    ))}
                  </ul>
                </section>
              ) : null}

              {bundle ? (
                <section className="ommi-preview" aria-label="Bundle meta-prompt" style={{ marginTop: 16 }}>
                  <div className="ommi-preview-head">
                    <h2>Bundle (miễn phí — copy để dán sang LLM riêng)</h2>
                  </div>
                  {bundle.missing_placeholders.length ? (
                    <p className="ommi-warn">
                      Còn {bundle.missing_placeholders.length} placeholder chưa có giá trị:{' '}
                      {bundle.missing_placeholders.join(', ')}
                    </p>
                  ) : null}
                  <pre>{bundle.rendered}</pre>
                </section>
              ) : null}

              {quote ? (
                <section className="ommi-empty" aria-label="Xác nhận chi phí" style={{ marginTop: 16 }}>
                  <h2>{quote.credit} credit</h2>
                  <p>Còn {quote.free_left} lượt miễn phí cho kịch bản này.</p>
                  <label className="ommi-field-wide">
                    Góp ý cho lượt tiếp theo (bỏ trống nếu là lượt đầu)
                    <textarea value={feedback} onChange={(event) => setFeedback(event.target.value)} />
                  </label>
                  <div className="ommi-detail-actions">
                    <button type="button" className="primary" onClick={doGenerate} disabled={busy}>
                      Xác nhận và chạy
                    </button>
                    <button type="button" className="ghost" onClick={() => setQuote(null)}>
                      Huỷ
                    </button>
                  </div>
                </section>
              ) : null}

              {iterations.length ? (
                <section aria-label="Lịch sử iterate" style={{ marginTop: 16 }}>
                  <h2 style={{ fontSize: 14 }}>Lịch sử</h2>
                  <ul className="ommi-history">
                    {iterations.map((it) => (
                      <li key={it.id}>
                        <b>#{it.seq}</b>
                        <span>
                          {it.was_free ? 'miễn phí' : `${it.credit_charged} credit`}
                          {it.feedback ? ` · ${it.feedback}` : ''}
                        </span>
                        {it.verdict ? (
                          <span>{it.verdict}</span>
                        ) : (
                          <span className="ommi-spacer" />
                        )}
                        {!it.verdict ? (
                          <>
                            <button type="button" className="ghost" onClick={() => void doVerdict(it.id, 'kept')}>
                              Giữ lại
                            </button>
                            <button
                              type="button"
                              className="ghost"
                              onClick={() => void doVerdict(it.id, 'rejected')}
                            >
                              Từ chối
                            </button>
                          </>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                </section>
              ) : null}
            </div>
          </>
        )}
      </section>
    </div>
  )
}
