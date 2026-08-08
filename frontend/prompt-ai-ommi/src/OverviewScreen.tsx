/**
 * OverviewScreen.tsx — Tổng quan.
 *
 * Ảnh tham chiếu của chủ sản phẩm hiển thị "Tổng chi phí team hôm nay" bằng USD
 * và một nhật ký "toàn team". Không sao chép cả ba: nền tảng chưa có khái niệm
 * team, Q31 chốt đơn vị là credit, và dữ liệu gộp nhiều người là chính kiểu
 * chia sẻ chéo mà app này được xây để tránh. Ở đây mọi con số là của bạn.
 */
import { useEffect, useState } from 'react'
import { ApiError, type Overview, getOverview } from './ommiApi'

const KIND_LABEL: Record<string, string> = {
  character: 'Nhân vật',
  background: 'Bối cảnh',
  prop: 'Đạo cụ',
  vehicle: 'Phương tiện',
  misc: 'Khác',
}

const TILES: Array<{ key: keyof Overview['counts']; label: string }> = [
  { key: 'projects', label: 'Dự án' },
  { key: 'resources', label: 'Tài nguyên' },
  { key: 'storyboards', label: 'Storyboard' },
  { key: 'scenes', label: 'Cảnh' },
  { key: 'meta_prompts', label: 'Meta prompt' },
  { key: 'styles', label: 'Phong cách' },
]

export function OverviewScreen({ onGo }: { onGo: (screen: string) => void }) {
  const [data, setData] = useState<Overview | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let alive = true
    getOverview()
      .then((body) => alive && setData(body))
      .catch((reason) =>
        alive &&
        setError(reason instanceof ApiError ? reason.message : 'Không tải được tổng quan.'),
      )
      .finally(() => alive && setLoading(false))
    return () => {
      alive = false
    }
  }, [])

  const empty = data && data.counts.projects === 0 && data.counts.resources === 0

  return (
    <>
      <header className="ommi-head">
        <div>
          <h1>Tổng quan</h1>
          <p>Toàn bộ số liệu dưới đây là của riêng tài khoản bạn.</p>
        </div>
        <div className="ommi-spacer" />
        {data ? (
          <span className="ommi-balance">💎 {data.credit_balance} credit</span>
        ) : null}
      </header>

      <div className="ommi-body">
        {error ? (
          <p className="ommi-error" role="alert">
            {error}
          </p>
        ) : null}

        {loading ? <p className="ommi-loading">Đang tải…</p> : data ? (
          <>
            <section className="ommi-credit-strip" aria-label="Chi tiêu credit cá nhân">
              <div>
                <span>Chi tiêu hôm nay</span>
                <strong>{data.credit_spent_today} credit</strong>
              </div>
              <div className="ommi-credit-track" aria-hidden="true">
                <span style={{ width: `${Math.min(100, data.credit_spent_today)}%` }} />
              </div>
              <small>{data.credit_spent_month} credit trong tháng</small>
            </section>

            {empty ? (
              /* Người mới không cần nhìn sáu ô số 0 — họ cần biết bắt đầu từ đâu. */
              <section className="ommi-empty ommi-start">
                <h2>Bắt đầu từ ba bước</h2>
                <p>
                  1. Thêm nhân vật và bối cảnh vào <b>Kho tài nguyên</b>. 2. Dựng
                  <b> Storyboard</b> và mô tả từng cảnh. 3. Sinh ảnh cho từng cảnh,
                  xem giá trước khi chạy.
                </p>
                <button type="button" className="primary"
                  onClick={() => onGo('resources')}>Mở Kho tài nguyên</button>
              </section>
            ) : (
              <>
                <div className="ommi-tiles">
                  {TILES.map((tile) => (
                    <div key={tile.key} className="ommi-tile">
                      <b>{data.counts[tile.key]}</b>
                      <span>{tile.label}</span>
                    </div>
                  ))}
                </div>

                <div className="ommi-dashboard-grid">
                  <section className="ommi-panel">
                    <h2>Phân loại tài nguyên</h2>
                    <div className="ommi-kind-grid">
                      {Object.entries(data.resource_kinds).map(([kind, total]) => (
                        <button key={kind} type="button" className="ommi-kind"
                          onClick={() => onGo('resources')}>
                          <b>{total}</b><span>{KIND_LABEL[kind] ?? kind}</span>
                        </button>
                      ))}
                    </div>
                  </section>

                  <section className="ommi-panel">
                    <h2>Dự án gần đây</h2>
                    {data.recent_projects.length ? (
                      <ul className="ommi-history">
                        {data.recent_projects.map((project) => (
                          <li key={project.id}>
                            <b>{project.name}</b><span>revision {project.revision}</span>
                          </li>
                        ))}
                      </ul>
                    ) : <p className="ommi-loading">Chưa có dự án nào.</p>}
                    <button type="button" className="ghost"
                      onClick={() => onGo('projects')}>Xem dự án</button>
                  </section>

                  <section className="ommi-panel ommi-panel-activity">
                    <h2>Hoạt động của tôi</h2>
                    {data.recent_jobs.length ? (
                      <ul className="ommi-history">
                        {data.recent_jobs.map((job) => (
                          <li key={job.id}>
                            <b>{job.status}</b><span>{job.error || job.operation}</span>
                          </li>
                        ))}
                      </ul>
                    ) : <p className="ommi-loading">Chưa chạy việc nào.</p>}
                  </section>
                </div>
              </>
            )}
          </>
        ) : null}
      </div>
    </>
  )
}
