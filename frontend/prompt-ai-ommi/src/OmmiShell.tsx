/**
 * OmmiShell.tsx — vỏ workspace: sidebar phân nhóm + vùng nội dung.
 *
 * Sidebar theo kiến trúc thông tin ở
 * `docs/APP_AUDIT/prompt-ai-ommi/2026-08-05/02_THIET_KE_GIAO_DIEN.md`.
 *
 * Màn nào CHƯA xây thì để `built: false` — nút vô hiệu, gắn nhãn "đang xây".
 * Không ẩn đi, vì người dùng cần thấy sản phẩm sẽ đi tới đâu; cũng không cho
 * bấm, vì một nút không làm gì làm G4 "Honest UI" trượt.
 */
import { useState } from 'react'
import './ommi.css'
import { setCsrfToken } from './ommiApi'
import { CreditScreen, SettingsScreen } from './AccountScreens'
import { LibraryScreen } from './LibraryScreen'
import { OverviewScreen } from './OverviewScreen'
import { ProjectScreen } from './ProjectScreen'
import { ResourceLibrary } from './ResourceLibrary'
import { StoryboardScreen } from './StoryboardScreen'

type Screen = { key: string; label: string; icon: string; built: boolean }
type Group = { title: string; items: Screen[] }

const GROUPS: Group[] = [
  {
    title: 'WORKSPACE',
    items: [
      { key: 'overview', label: 'Tổng quan', icon: '▦', built: true },
      { key: 'projects', label: 'Dự án', icon: '▤', built: true },
    ],
  },
  {
    title: 'LÀM VIỆC',
    items: [
      { key: 'resources', label: 'Kho tài nguyên', icon: '◈', built: true },
      { key: 'brief', label: 'Brief & Director', icon: '✎', built: true },
      { key: 'storyboard', label: 'Storyboard', icon: '▩', built: true },
    ],
  },
  {
    title: 'THƯ VIỆN',
    items: [
      { key: 'snippet', label: 'Prompt Library', icon: '❐', built: true },
      { key: 'style', label: 'Phong cách', icon: '◐', built: true },
      { key: 'meta', label: 'Meta Director', icon: '✦', built: true },
    ],
  },
  {
    title: 'TÀI KHOẢN',
    items: [
      { key: 'credit', label: 'Chi phí & credit', icon: '◇', built: true },
      { key: 'settings', label: 'Cài đặt', icon: '⚙', built: true },
    ],
  },
]

export function OmmiShell({ csrfToken }: { csrfToken: string }) {
  setCsrfToken(csrfToken)
  const [screen, setScreen] = useState('overview')

  return (
    <div className="ommi">
      <nav className="ommi-rail" aria-label="Điều hướng Prompt AI">
        <div className="ommi-brand">
          <b>✦</b>
          <div>
            <span>Prompt AI</span>
            <small>STORY & PROMPT STUDIO</small>
          </div>
        </div>
        {GROUPS.map((group) => (
          <div key={group.title}>
            <div className="ommi-group">{group.title}</div>
            {group.items.map((item) => (
              <button
                key={item.key}
                type="button"
                disabled={!item.built}
                aria-current={screen === item.key ? 'page' : undefined}
                onClick={() => setScreen(item.key)}
              >
                <span aria-hidden="true">{item.icon}</span>
                {item.label}
                {item.built ? null : <em>đang xây</em>}
              </button>
            ))}
          </div>
        ))}
      </nav>

      <main className="ommi-main">
        {screen === 'overview' ? <OverviewScreen onGo={setScreen} /> : null}
        {screen === 'projects' || screen === 'brief' ? (
          <ProjectScreen key={screen} mode={screen} />
        ) : null}
        {screen === 'credit' ? <CreditScreen /> : null}
        {screen === 'settings' ? <SettingsScreen /> : null}
        {screen === 'resources' ? <ResourceLibrary /> : null}
        {screen === 'storyboard' ? <StoryboardScreen /> : null}
        {screen === 'snippet' || screen === 'style' || screen === 'meta' ? (
          <LibraryScreen key={screen} kind={screen} />
        ) : null}
      </main>
    </div>
  )
}
