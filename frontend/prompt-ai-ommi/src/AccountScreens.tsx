/**
 * AccountScreens.tsx — Chi phí & credit, và Cài đặt.
 *
 * Chi phí ĐỌC từ sổ credit của nền tảng, không dựng sổ thứ hai. Đơn vị là
 * credit chứ không phải tiền: Q31 chốt 1 credit = 100đ ở đúng một chỗ, và quy
 * đổi lại ở đây là tạo cách tính giá thứ hai.
 */
import { useEffect, useState } from 'react'
import {
  ApiError,
  type CreditSummary,
  type Preferences,
  getCredit,
  getPreferences,
  savePreferences,
} from './ommiApi'

export function CreditScreen() {
  const [data, setData] = useState<CreditSummary | null>(null)
  const [days, setDays] = useState(30)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let alive = true
    setLoading(true)
    getCredit(days)
      .then((body) => alive && setData(body))
      .catch((reason) =>
        alive &&
        setError(reason instanceof ApiError ? reason.message : 'Không tải được chi phí.'),
      )
      .finally(() => alive && setLoading(false))
    return () => {
      alive = false
    }
  }, [days])

  return (
    <>
      <header className="ommi-head">
        <div>
          <h1>Chi phí &amp; credit</h1>
          <p>Chi tiêu của riêng bạn, đọc thẳng từ sổ credit của nền tảng.</p>
        </div>
        <div className="ommi-spacer" />
        <a className="ommi-download" href="/nap">
          Nạp thêm
        </a>
      </header>

      <div className="ommi-body">
        {error ? (
          <p className="ommi-error" role="alert">
            {error}
          </p>
        ) : null}

        <div className="ommi-filters">
          {[7, 30, 90].map((option) => (
            <button key={option} type="button" className="ommi-chip"
              aria-pressed={days === option} onClick={() => setDays(option)}>
              {option} ngày
            </button>
          ))}
        </div>

        {loading ? (
          <p className="ommi-loading">Đang tải…</p>
        ) : data ? (
          <>
            <div className="ommi-tiles">
              <div className="ommi-tile">
                <b>{data.balance}</b>
                <span>Số dư</span>
              </div>
              <div className="ommi-tile">
                <b>{data.spent}</b>
                <span>Đã dùng {data.days} ngày</span>
              </div>
              <div className="ommi-tile">
                <b>{data.added}</b>
                <span>Đã nạp {data.days} ngày</span>
              </div>
            </div>

            <h2 className="ommi-section">Bút toán gần đây</h2>
            {data.entries.length ? (
              <ul className="ommi-history">
                {data.entries.map((entry, index) => (
                  <li key={`${entry.created_at}-${index}`}>
                    <b>
                      {entry.delta > 0 ? '+' : ''}
                      {entry.delta}
                    </b>
                    <span>{entry.note || entry.kind}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="ommi-loading">Chưa có bút toán nào trong khoảng này.</p>
            )}
          </>
        ) : null}
      </div>
    </>
  )
}

export function SettingsScreen() {
  const [prefs, setPrefs] = useState<Preferences | null>(null)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState('')

  useEffect(() => {
    let alive = true
    getPreferences()
      .then((body) => alive && setPrefs(body))
      .catch((reason) =>
        alive &&
        setError(reason instanceof ApiError ? reason.message : 'Không tải được cài đặt.'),
      )
    return () => {
      alive = false
    }
  }, [])

  const change = async (theme: string) => {
    if (!prefs) return
    try {
      setPrefs(await savePreferences({ theme, revision: prefs.revision }))
      setSaved('Đã lưu.')
      setError('')
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : 'Không lưu được cài đặt.')
    }
  }

  return (
    <>
      <header className="ommi-head">
        <div>
          <h1>Cài đặt</h1>
          <p>Tuỳ chọn hiển thị, lưu theo tài khoản của bạn.</p>
        </div>
      </header>

      <div className="ommi-body">
        {error ? (
          <p className="ommi-error" role="alert">
            {error}
          </p>
        ) : null}
        {saved ? <p className="ommi-loading">{saved}</p> : null}

        <div className="ommi-form">
          <label>
            Nền
            <select value={prefs?.theme ?? 'dark'}
              onChange={(event) => void change(event.target.value)}>
              <option value="dark">Tối (mặc định)</option>
              <option value="light">Sáng</option>
            </select>
          </label>
        </div>

        {/* Khoá API và nhà cung cấp KHÔNG nằm ở đây: nền tảng quản lý tập trung
            qua APIKEYS. Dựng lại một trang nhập khoá trong app là tạo chỗ thứ
            hai giữ bí mật. */}
        <section className="ommi-empty" style={{ marginTop: 18 }}>
          <h2>Khoá API và model</h2>
          <p>
            Khoá nhà cung cấp do nền tảng quản lý tập trung, không khai trong app.
            Model dùng cho từng lần chạy chọn ngay tại chỗ chạy.
          </p>
        </section>
      </div>
    </>
  )
}
