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
import { useEffect, useRef, useState } from 'react'
import './ommi.css'
import { setCsrfToken } from './ommiApi'
import { CreditScreen, SettingsScreen } from './AccountScreens'
import { LibraryScreen } from './LibraryScreen'
import { OverviewScreen } from './OverviewScreen'
import { ProjectScreen } from './ProjectScreen'
import { ResourceLibrary } from './ResourceLibrary'
import { StoryboardScreen } from './StoryboardScreen'
import { StudioShell } from './StudioShell'

type Screen = { key: string; label: string; icon: string; built: boolean }
type Group = { title: string; items: Screen[] }

const GROUPS: Group[] = [
  {
    title: 'KHÔNG GIAN',
    items: [
      // Lối vào mặc định (Q-3, 26/09): 2-pane Studio Kịch bản. Đứng đầu danh
      // sách vì `MAN_MAC_DINH` bên dưới trỏ vào đúng khoá này.
      { key: 'studio', label: 'Studio Kịch bản', icon: '✎', built: true },
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
      { key: 'snippet', label: 'Thư viện prompt', icon: '❐', built: true },
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

/* Moi khoa man DA XAY. Dung de loc hash — mot hash la duong vao tu ngoai,
 * nen khong duoc tin. `#/khong-co-that` phai roi ve `MAN_MAC_DINH`, khong duoc
 * render mot vung trong. ⚠️ Dung go ten man vao chu thich nay: mac dinh da
 * doi mot lan (Q-3: overview -> studio) va chu thich cu o lai noi sai. */
const KHOA_HOP_LE = new Set(
  GROUPS.flatMap((g) => g.items.filter((i) => i.built).map((i) => i.key)),
)

/** Loi vao mac dinh (Q-3). XUAT ra de phep kiem doc duoc thay vi go ten man:
 *  mot phep kiem go 'Tong quan' da DO ngay khi mac dinh doi sang 'studio'. */
export const MAN_MAC_DINH = 'studio'

/** Nhan hien thi cua mot khoa man. Xuat ra vi phep kiem phai tim nut tren rail
 *  theo nhan, ma nhan la thu chi GROUPS biet. */
export function nhanMan(khoa: string): string {
  for (const g of GROUPS) {
    for (const i of g.items) if (i.key === khoa) return i.label
  }
  throw new Error(`khoa man khong co that: ${khoa}`)
}

function docHash(): string {
  const h = (window.location.hash || '').replace(/^#\/?/, '')
  return KHOA_HOP_LE.has(h) ? h : MAN_MAC_DINH
}

export function OmmiShell(
  { csrfToken, maxScenes = 20 }: { csrfToken: string; maxScenes?: number },
) {
  setCsrfToken(csrfToken)

  /* 🔴 VI SAO CO DINH TUYEN O DAY. Truoc 07/09 man hinh chi nam trong
   *    `useState`, va do la BA loi nguoi dung that, khong phai mot chi tiet
   *    ky thuat:
   *
   *      tai lai trang  -> ve `overview`, mat cho dang xem
   *      nut Back       -> THOAT khoi app thay vi ve man truoc
   *      chia se link   -> khong the tro toi mot man cu the
   *
   *    Cai thu hai nang nhat tren di dong: Back la cu chi dieu huong chinh, va
   *    mot nguoi dang o `storyboard` bam Back se bi van ra ngoai.
   *
   * ⭐ Dung HASH chu khong `pushState` duong dan: hash khong can may chu biet
   *    gi ca, nen tai lai `#/storyboard` khong the ra 404. Doi sang duong dan
   *    that se can them mot route bat-tat-ca o server.
   */
  const [screen, setScreen] = useState(docHash)

  useEffect(() => {
    const dong_bo = () => setScreen(docHash())
    window.addEventListener('hashchange', dong_bo)
    return () => window.removeEventListener('hashchange', dong_bo)
  }, [])

  /* ⛔ BO QUA lan chay dau. Ghi hash ngay khi mount la sai hai kieu:
   *
   *    1. No day them mot muc lich su cho TRANG THAI BAN DAU, nen lan bam Back
   *       dau tien khong lam gi ca — dung kieu "nut Back dam chan tai cho" ma
   *       nguoi dung khong bao gio bao cao duoc thanh loi.
   *
   *    2. No ban `hashchange` -> render lai ngay giua lan mount. Do 07/09:
   *       viec do lam DO hai phep kiem co san cua `ResourceLibrary.test.tsx`
   *       (chung dang `waitFor` du lieu bat dong bo). Bo test cu bat duoc, va
   *       no bat mot loi THAT chu khong phai mot va cham vo tinh.
   */
  const da_mount = useRef(false)
  useEffect(() => {
    if (!da_mount.current) {
      da_mount.current = true
      /* Hash BAY BA thi chuan hoa ngay, nhung bang `replaceState` — no khong
       * them mot muc lich su, nen nut Back van ve dung cho nguoi dung vua roi
       * khoi. Thieu buoc nay thi URL noi `#/khong-co-that` trong khi man dang
       * hien la Tong quan: dung ve hanh vi, sai ve thu URL KHANG DINH. */
      const h = window.location.hash
      if (h && h !== '#/' + screen) {
        window.history.replaceState(null, '', '#/' + screen)
      }
      return
    }
    const mong = '#/' + screen
    // Chi ghi khi KHAC: ghi lai cung mot hash van day them mot muc lich su.
    if (window.location.hash !== mong) window.location.hash = mong
  }, [screen])

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

      <section className="ommi-main">
        {screen === 'studio' ? <StudioShell maxScenes={maxScenes} /> : null}
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
      </section>
    </div>
  )
}
